# Phase 17: QSO Processing Pipeline - Research

**Researched:** 2026-04-06
**Domain:** asyncio background tasks / ADIF parsing / QSO insertion / SSE live feed
**Confidence:** HIGH

---

## Summary

Phase 17 completes the UDP processing pipeline by wiring `_handle_datagram()` into the existing `QSODatagramProtocol` skeleton from Phase 16. The heavy-lifting functions already exist: `parse_adi()` in `app/adif/parser.py`, `build_qso_dict()` and `find_duplicate()` in `app/qso/service.py`, and the `QSO` Beanie document in `app/qso/models.py`. The SSE change-stream watcher in `app/feed/manager.py` already reacts to any MongoDB insert — no changes needed there.

The only new code required is (a) a `_handle_datagram()` async coroutine in `app/udp/server.py` that orchestrates parse → validate → build → dedup → insert, (b) caching the operator `User` document at startup so `build_qso_dict()` receives a profile for auto-stamping, and (c) wiring `asyncio.create_task(_handle_datagram(...))` into `datagram_received()` with the existing `_background_tasks` strong-reference set. Additionally, `app/main.py` lifespan must fetch and cache the `User` document during startup and pass it to the protocol.

The validation requirement (QSO-02) uses `_REQUIRED_FIELDS` already defined in `app/qso/service.py`. Profile auto-stamping (QSO-04) uses the `profile` parameter of `build_qso_dict()` — already tested in `tests/test_qso_stamping.py`. Duplicate detection (QSO-05) uses `find_duplicate()` — already tested in `tests/test_duplicate_detection.py`. The SSE live feed (QSO-06) requires zero changes.

**Primary recommendation:** Implement `_handle_datagram(data, addr, operator_str, user_profile)` as a standalone async function in `app/udp/server.py`, pass operator and cached `User` into the protocol at construction, and dispatch via `create_task` from `datagram_received`. Lifespan fetches `User` by callsign once after `_bootstrap_admin()`.

---

## Standard Stack

### Core (all already in project — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `asyncio` (stdlib) | Python 3.14 | `create_task`, `get_running_loop` | Locked decision; no new prod deps |
| `beanie` | already in project | `QSO.insert()`, `User.find_one()` | Project ORM for MongoDB |
| `app.adif.parser.parse_adi` | project | Parse raw ADIF text into records | Already handles header/body split, UTF-8 byte lengths |
| `app.qso.service.build_qso_dict` | project | Build QSO dict with operator + profile | Handles normalisation, date parsing, profile stamping |
| `app.qso.service.find_duplicate` | project | +/-2 min dedup query | Same logic as REST API |
| `app.qso.service._REQUIRED_FIELDS` | project | `{"CALL", "QSO_DATE", "TIME_ON", "BAND", "MODE"}` | Already imported by `import_qsos_from_bytes` |
| `app.qso.models.QSO` | project | Beanie document for insert | Already indexed |
| `app.auth.models.User` | project | Profile source for auto-stamping | Fetched once at startup |

### No New Packages Required

```bash
# No installation needed — all dependencies already present
```

---

## Architecture Patterns

### Recommended File Changes

```
app/
├── udp/
│   └── server.py          # ADD: _handle_datagram(), QSODatagramProtocol.__init__ takes operator+user
├── main.py                # ADD: User lookup after _bootstrap_admin(), pass to start_udp_listener()
└── tests/
    └── test_udp_pipeline.py  # NEW: unit + integration tests for UDP QSO path
```

No other files need modification.

### Pattern 1: Operator User Cached at Startup

**What:** After `_bootstrap_admin()` in `app/main.py` lifespan, look up the `User` document for `settings.udp_operator`. Cache as a local variable and pass to `start_udp_listener()` which passes it to the protocol constructor.

**Why:** The locked decision requires no MongoDB round-trip per datagram. A single `await User.find_one({"callsign": settings.udp_operator.upper()})` at startup satisfies this.

**Failure cases:**
- `settings.udp_operator` is `None` — log WARNING "UDP_OPERATOR not set; UDP QSO insertion disabled" and pass `None` as user; `_handle_datagram` rejects all datagrams with a log message if `_operator` is unset.
- `settings.udp_operator` is set but no matching `User` — log WARNING "UDP_OPERATOR callsign not found in DB; UDP QSO insertion disabled" and pass `None`.
- Both cases leave the socket bound (operators can still smoke-test the socket), but datagrams are logged and discarded without DB writes.

```python
# In app/main.py lifespan, AFTER _bootstrap_admin(), BEFORE start_udp_listener():
udp_user: "User | None" = None
if settings.udp_enabled and settings.udp_operator:
    from app.auth.models import User
    udp_user = await User.find_one({"callsign": settings.udp_operator.upper()})
    if udp_user is None:
        logger.warning(
            "UDP_OPERATOR callsign %r not found in DB — datagrams will be discarded",
            settings.udp_operator,
        )

# Then pass udp_user to start_udp_listener:
udp_transport, _ = await start_udp_listener(
    settings.udp_bind_host, settings.udp_port,
    operator=settings.udp_operator,
    user=udp_user,
)
```

### Pattern 2: QSODatagramProtocol Constructor Takes Operator + User

**What:** Change `QSODatagramProtocol.__init__` to accept `operator: str | None` and `user: User | None`. Store as instance attributes. `datagram_received` dispatches `_handle_datagram(data, addr, self._operator, self._user)`.

**Why:** Avoids module-level globals; makes the dependency explicit and testable.

```python
# Source: existing app/udp/server.py + asyncio docs pattern
class QSODatagramProtocol(asyncio.DatagramProtocol):
    def __init__(
        self,
        operator: str | None = None,
        user: "User | None" = None,
    ) -> None:
        self.transport: asyncio.DatagramTransport | None = None
        self._background_tasks: set[asyncio.Task] = set()
        self._operator = operator
        self._user = user

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        logger.info(
            "UDP datagram received from %s:%s (%d bytes)",
            addr[0], addr[1], len(data),
        )
        task = asyncio.create_task(
            _handle_datagram(data, addr, self._operator, self._user)
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
```

### Pattern 3: _handle_datagram() Coroutine

**What:** Async coroutine that owns the full parse → validate → build → dedup → insert pipeline. Logs and returns (does not raise) so that exceptions in one datagram never crash the event loop.

**Why:** `create_task` creates a fire-and-forget task. If it raises, the exception is stored on the task object and only re-raised if the task is awaited. Without `try/except`, unhandled task exceptions produce a "Task exception was never retrieved" warning in Python 3.12+.

```python
async def _handle_datagram(
    data: bytes,
    addr: tuple[str, int],
    operator: str | None,
    user: "User | None",
) -> None:
    """Full UDP QSO processing pipeline. Logs errors; never raises."""
    from app.adif.parser import parse_adi
    from app.qso.models import QSO
    from app.qso.service import _REQUIRED_FIELDS, build_qso_dict, find_duplicate

    if operator is None:
        logger.warning("UDP_OPERATOR not configured — datagram discarded")
        return

    try:
        text = data.decode("utf-8", errors="replace")
        records, parse_errors = parse_adi(text)

        if parse_errors:
            logger.warning("UDP parse errors from %s:%s: %s", addr[0], addr[1], parse_errors)

        if not records:
            logger.warning(
                "UDP datagram from %s:%s yielded no ADIF records — discarded",
                addr[0], addr[1],
            )
            return

        # Process first record only (one QSO per datagram per spec)
        record = records[0]

        # Required field validation (QSO-02)
        missing = sorted(_REQUIRED_FIELDS - set(record))
        if missing:
            logger.warning(
                "UDP datagram from %s:%s missing required field(s): %s — discarded",
                addr[0], addr[1], ", ".join(missing),
            )
            return

        # Build QSO dict — operator injected from config (QSO-03), profile auto-stamped (QSO-04)
        qso_dict = build_qso_dict(record, operator, profile=user)

        # Duplicate detection (QSO-05)
        dup = await find_duplicate(
            operator=operator,
            call=qso_dict["CALL"],
            band=qso_dict["BAND"],
            mode=qso_dict["MODE"],
            qso_date_utc=qso_dict["qso_date_utc"],
        )
        if dup is not None:
            logger.info(
                "UDP datagram from %s:%s is duplicate of QSO %s — discarded",
                addr[0], addr[1], dup.id,
            )
            return

        # Insert (QSO-01, triggers SSE via change stream — QSO-06)
        qso = QSO(**qso_dict)
        await qso.insert()
        logger.info(
            "UDP QSO inserted: id=%s call=%s band=%s mode=%s operator=%s",
            qso.id, qso_dict["CALL"], qso_dict["BAND"], qso_dict["MODE"], operator,
        )

    except Exception:
        logger.exception(
            "Unhandled exception processing UDP datagram from %s:%s",
            addr[0], addr[1],
        )
```

### Pattern 4: SSE Live Feed — No Changes Needed

**What:** `app/feed/manager.py::watch_qsos()` uses a MongoDB change stream with `{"$match": {"operationType": "insert"}}`. Any insert to the `qsos` collection triggers a broadcast — regardless of whether the insert came from REST or UDP.

**Why:** The change stream is already live; UDP inserts are indistinguishable from REST inserts at the MongoDB level.

**Verification:** Success criterion 5 (QSO appears in SSE within 2 seconds) is satisfied automatically by the existing watcher.

### Pattern 5: Multiple ADIF Records in One Datagram

**What:** The ADIF parser (`parse_adi`) handles multi-record ADIF text. A single UDP datagram could theoretically contain multiple `<EOR>`-terminated records.

**Decision:** Process only `records[0]` — the first record. UDP datagrams from N1MM+, WSJT-X, and similar tools send exactly one QSO per datagram. Processing multiple records per datagram adds complexity with no stated requirement.

**Alternative:** Use `import_qsos_from_bytes` directly — it already handles multi-record ADIF. Trade-off: it uses a different code path (no profile auto-stamping, uses `build_qso_dict(..., profile=None)`). The phase requires profile auto-stamping (QSO-04), so call `build_qso_dict` with `profile=user` directly rather than delegating to `import_qsos_from_bytes`.

### Anti-Patterns to Avoid

- **Calling `import_qsos_from_bytes` from `_handle_datagram`:** That function calls `build_qso_dict(record, operator)` without a `profile` argument, so profile auto-stamping (QSO-04) would NOT happen. Build the pipeline inline in `_handle_datagram` using `build_qso_dict(..., profile=user)`.
- **Raising exceptions inside `_handle_datagram`:** Any unhandled exception becomes a task exception. Wrap the entire body in `try/except Exception: logger.exception(...)`.
- **Storing `User` as a module-level global in `server.py`:** Makes the module stateful and harder to test. Store as instance attributes on `QSODatagramProtocol` instead.
- **Re-fetching `User` on every datagram:** Violates the locked decision (no MongoDB round-trip per datagram). Cache at startup.
- **Using `asyncio.get_event_loop()` inside `datagram_received`:** `datagram_received` is called by the event loop, inside a running loop — `asyncio.get_running_loop()` is correct. However, `create_task` does not need a loop reference; `asyncio.create_task()` works directly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ADIF parsing | Custom tag scanner | `parse_adi()` in `app/adif/parser.py` | Handles EOH, byte-length counting, multi-byte UTF-8, APP_ fields |
| Required field check | Custom set logic | `_REQUIRED_FIELDS` + set subtraction | Already in `app/qso/service.py`; same logic as import path |
| QSO dict construction | Manual dict building | `build_qso_dict(record, operator, profile=user)` | Handles BAND/MODE uppercase, `qso_date_utc` parsing, profile stamping, operator injection |
| Duplicate detection | Custom query | `find_duplicate()` | Handles +/-2 min window, operator isolation, soft-delete exclusion |
| QSO insert | Raw pymongo | `QSO(**qso_dict).insert()` | Beanie validates schema, stores ADIF extra fields, triggers change stream |
| SSE broadcasting | Manual socket push | `watch_qsos` change stream (already running) | Zero changes needed — inserts appear automatically |

**Key insight:** All domain logic already exists and is tested. Phase 17 is primarily glue code connecting the existing pieces.

---

## Common Pitfalls

### Pitfall 1: Calling import_qsos_from_bytes Instead of build_qso_dict

**What goes wrong:** `import_qsos_from_bytes` calls `build_qso_dict(record, operator)` without a `profile` argument. Profile fields (OPERATOR, STATION_CALLSIGN, MY_GRIDSQUARE, etc.) are NOT stamped. QSO-04 fails silently.

**Why it happens:** `import_qsos_from_bytes` is the obvious "reuse existing logic" candidate. But its signature predates profile auto-stamping for the UDP path.

**How to avoid:** Call `build_qso_dict(record, operator, profile=user)` directly in `_handle_datagram`. Keep `import_qsos_from_bytes` for the HTTP import path.

**Warning signs:** Test `test_udp_qso_has_profile_fields` — check that inserted QSO document has `OPERATOR` field set.

### Pitfall 2: operator Sourced From ADIF Content Instead of Config

**What goes wrong:** ADIF records often contain an `OPERATOR` field. If `_operator` (the MongoDB isolation field) is accidentally populated from the datagram instead of `settings.udp_operator`, operator isolation breaks.

**Why it happens:** `build_qso_dict` takes `operator` as the second argument — this is the `_operator` field. If someone passes `record.get("OPERATOR", settings.udp_operator)` as the operator argument, a crafted datagram could hijack insertion into another operator's log.

**How to avoid:** Always pass `settings.udp_operator` (or the cached string from `self._operator`) — never touch `record.get("OPERATOR")` for the `_operator` field. The `OPERATOR` ADIF field inside the record is a separate, harmless field that `build_qso_dict` stamps from the profile anyway.

**Warning signs:** Test `test_udp_operator_from_config_not_datagram` — send datagram with `<OPERATOR:5>W1XXX` in ADIF body; verify `_operator` in DB is `settings.udp_operator`, not `W1XXX`.

### Pitfall 3: Unhandled Exception Crashes the Task Silently

**What goes wrong:** If `_handle_datagram` raises an unhandled exception, Python logs a "Task exception was never retrieved" warning (Python 3.12+) but the event loop continues. The operator has no visible error, and the QSO is silently dropped.

**Why it happens:** Background tasks from `create_task` are fire-and-forget. Exceptions don't propagate to `datagram_received`.

**How to avoid:** Wrap the full body of `_handle_datagram` in `try/except Exception: logger.exception(...)`. Never let it raise.

**Warning signs:** If logs show "Task exception was never retrieved", an exception path is unhandled.

### Pitfall 4: User Document Not Found at Startup — Silent Failure

**What goes wrong:** If `UDP_OPERATOR` is set to a callsign that doesn't exist in the DB (e.g., wrong case, not yet bootstrapped), `User.find_one()` returns `None`. If this is not handled, every datagram fails silently when `build_qso_dict` is called with `user=None` (no profile stamping) or crashes if operator is `None`.

**Why it happens:** Config values are not validated against DB contents at startup.

**How to avoid:** In lifespan, after `User.find_one()`, log a WARNING if `udp_user is None` and the setting is not `None`. Pass `None` as `user` but keep `operator` set (so `build_qso_dict` still works — it accepts `profile=None`). QSO-04 requires profile stamping, so a WARNING here is important for operators to notice.

**Warning signs:** Inserted QSOs missing `OPERATOR` field when UDP_OPERATOR is set but no matching user.

### Pitfall 5: Task GC Before Completion Under Load

**What goes wrong:** If many datagrams arrive in rapid succession, tasks created by `create_task` may be garbage-collected before they complete if not held by a strong reference.

**Why it happens:** The event loop holds only a weak reference to tasks. Documented Python behavior since 3.12.

**How to avoid:** The `_background_tasks` set is already established in Phase 16's `QSODatagramProtocol`. Always use:
```python
task = asyncio.create_task(...)
self._background_tasks.add(task)
task.add_done_callback(self._background_tasks.discard)
```

**Warning signs:** Ruff lint rule `RUF006` (asyncio-dangling-task) fires if `create_task` result is not stored.

### Pitfall 6: start_udp_listener Signature Change Breaks Existing Call Site

**What goes wrong:** `app/main.py` currently calls `start_udp_listener(settings.udp_bind_host, settings.udp_port)` with two positional args. If Phase 17 changes the function signature to add `operator` and `user` params without defaults, the existing call site becomes a `TypeError`.

**Why it happens:** Signature change is easy to forget when refactoring.

**How to avoid:** Add `operator` and `user` as keyword arguments with defaults (`None`). Update the call site in `main.py` at the same time.

---

## Code Examples

### Minimal _handle_datagram (verified pattern from codebase analysis)

```python
# Source: synthesised from app/qso/service.py, app/adif/parser.py, app/qso/models.py
async def _handle_datagram(
    data: bytes,
    addr: tuple[str, int],
    operator: str | None,
    user: "User | None",
) -> None:
    from app.adif.parser import parse_adi
    from app.qso.models import QSO
    from app.qso.service import _REQUIRED_FIELDS, build_qso_dict, find_duplicate

    if operator is None:
        logger.warning("UDP_OPERATOR not configured — datagram from %s:%s discarded", *addr)
        return

    try:
        text = data.decode("utf-8", errors="replace")
        records, _errors = parse_adi(text)
        if not records:
            logger.warning("UDP datagram from %s:%s: no ADIF records found — discarded", *addr)
            return

        record = records[0]
        missing = sorted(_REQUIRED_FIELDS - set(record))
        if missing:
            logger.warning(
                "UDP datagram from %s:%s missing %s — discarded", *addr, missing
            )
            return

        qso_dict = build_qso_dict(record, operator, profile=user)

        dup = await find_duplicate(
            operator=operator,
            call=qso_dict["CALL"],
            band=qso_dict["BAND"],
            mode=qso_dict["MODE"],
            qso_date_utc=qso_dict["qso_date_utc"],
        )
        if dup is not None:
            logger.info("UDP duplicate of %s — discarded", dup.id)
            return

        qso = QSO(**qso_dict)
        await qso.insert()
        logger.info("UDP QSO inserted: %s id=%s", qso_dict["CALL"], qso.id)

    except Exception:
        logger.exception("Error processing UDP datagram from %s:%s", *addr)
```

### datagram_received with _background_tasks (correct pattern)

```python
# Source: https://docs.python.org/3/library/asyncio-task.html (task GC warning)
def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
    logger.info(
        "UDP datagram received from %s:%s (%d bytes)", addr[0], addr[1], len(data)
    )
    task = asyncio.create_task(
        _handle_datagram(data, addr, self._operator, self._user)
    )
    self._background_tasks.add(task)
    task.add_done_callback(self._background_tasks.discard)
```

### Lifespan: User lookup before start_udp_listener

```python
# In app/main.py lifespan, after _bootstrap_admin():
udp_transport = None
if settings.udp_enabled:
    from app.auth.models import User as UserModel
    from app.udp.server import start_udp_listener

    udp_user: UserModel | None = None
    if settings.udp_operator:
        udp_user = await UserModel.find_one({"callsign": settings.udp_operator.upper()})
        if udp_user is None:
            logger.warning(
                "UDP_OPERATOR callsign %r not found in DB — profile stamping disabled",
                settings.udp_operator,
            )

    udp_transport, _ = await start_udp_listener(
        settings.udp_bind_host,
        settings.udp_port,
        operator=settings.udp_operator,
        user=udp_user,
    )
```

### Test: Unit test for _handle_datagram (no MongoDB)

```python
# Approach: mock find_duplicate to return None, mock QSO.insert
# Use User.model_construct() to build a User without DB (pattern from test_qso_stamping.py)
import asyncio
from unittest.mock import AsyncMock, patch
from app.udp.server import _handle_datagram
from app.auth.models import User

_SAMPLE_ADIF = (
    "<CALL:5>W1AW<BAND:3>20m<MODE:3>SSB"
    "<QSO_DATE:8>20240101<TIME_ON:4>1200<EOR>"
)

async def test_handle_datagram_inserts_qso():
    user = User.model_construct(
        callsign="VK2ABC",
        username="vk2abc",
        hashed_password="x",
        role="operator",
        enabled=True,
    )
    with patch("app.qso.service.find_duplicate", new_callable=AsyncMock, return_value=None):
        with patch("app.qso.models.QSO.insert", new_callable=AsyncMock):
            await _handle_datagram(
                _SAMPLE_ADIF.encode(), ("127.0.0.1", 9999), "VK2ABC", user
            )
```

### Test: Integration test (live MongoDB)

```python
# Pattern from tests/test_duplicate_detection.py and tests/test_qso_stamping.py
# Use a fresh "ollog_udp_test" database with User + QSO models
# Call _handle_datagram directly with a real User fetched from DB
# Verify QSO inserted with correct _operator and OPERATOR fields
```

### Smoke test with netcat (same as Phase 16 but with valid ADIF)

```bash
# Start app with UDP_ENABLED=true, UDP_OPERATOR=W1AW (must exist in DB)
printf '<CALL:5>W1AW<BAND:3>20m<MODE:3>SSB<QSO_DATE:8>20240101<TIME_ON:4>1200<EOR>' \
  | nc -u -w1 127.0.0.1 2399
# Expected log: "UDP QSO inserted: W1AW id=..."
# Expected: QSO appears in SSE live feed within 2 seconds
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `get_event_loop()` | `get_running_loop()` | Python 3.10 deprecation | Must use `get_running_loop()` in coroutine context |
| Module-level `User` global | Instance attribute on protocol | Phase 17 design decision | Testable, no hidden state |
| `import_qsos_from_bytes` for all paths | Direct `build_qso_dict` with `profile=user` for UDP | Phase 17 (UDP needs profile stamping) | Profile auto-stamping works correctly on UDP path |
| `process_import()` raising `HTTPException` | `import_qsos_from_bytes` raising `ValueError` | Phase 16 complete | Background tasks can call service layer safely |

**Deprecated/outdated:**
- `process_import()` in `app/adif/router.py`: removed in Phase 16. `import_qsos_from_bytes` is the canonical function. Do NOT reference `process_import` anywhere in Phase 17.
- `asyncio.get_event_loop()`: Do not use in any new code; raises `DeprecationWarning` in 3.10-3.11, potential `RuntimeError` in 3.12+.

---

## Implementation Scope Summary

| File | Change | Type |
|------|--------|------|
| `app/udp/server.py` | Add `_handle_datagram()` coroutine; update `QSODatagramProtocol.__init__` to accept `operator` + `user`; wire `create_task` in `datagram_received`; update `start_udp_listener` signature | MODIFY |
| `app/main.py` | Add `User.find_one` call after `_bootstrap_admin()`; pass `operator`/`user` to `start_udp_listener` | MODIFY |
| `tests/test_udp_pipeline.py` | Unit + integration tests for `_handle_datagram` | CREATE |

No other files need changes. `app/feed/manager.py`, `app/qso/service.py`, `app/qso/models.py`, `app/adif/parser.py`, `app/config.py` — all unchanged.

---

## Open Questions

1. **Multi-record datagrams**
   - What we know: `parse_adi` returns all records; N1MM+ and WSJT-X send one QSO per datagram.
   - What's unclear: Should multi-record datagrams process all records or only the first?
   - Recommendation: Process `records[0]` only. Log a WARNING if `len(records) > 1`. This is conservative, avoids unexpected bulk insertions, and matches the "one contact per UDP send" UX model.

2. **UDP_OPERATOR callsign casing**
   - What we know: `settings.udp_operator` is a raw string from environment. Callsigns in the DB are stored uppercase (`callsign.upper()` enforced in `_bootstrap_admin`).
   - What's unclear: Is `udp_operator` guaranteed uppercase at config load time?
   - Recommendation: Apply `.upper()` in the `User.find_one({"callsign": settings.udp_operator.upper()})` lookup. Also apply `.upper()` when passing `operator` to `_handle_datagram`. Matches existing pattern in `_bootstrap_admin`.

3. **Test isolation for _handle_datagram**
   - What we know: The function imports from `app.adif.parser`, `app.qso.models`, and `app.qso.service` inside the function body to avoid circular imports.
   - What's unclear: Whether lazy imports inside async functions cause issues with mock patching in pytest.
   - Recommendation: Use `unittest.mock.patch` with the full module path (`"app.qso.service.find_duplicate"`, `"app.qso.models.QSO.insert"`). The lazy import pattern is used in `import_qsos_from_bytes` already (`from app.adif.parser import parse_adi`), so it's established and works.

---

## Sources

### Primary (HIGH confidence)

- `/Users/royco/ollog/app/udp/server.py` — Phase 16 skeleton; `_background_tasks` set, `datagram_received` comment "Phase 17: dispatch async processing here via create_task"
- `/Users/royco/ollog/app/qso/service.py` — `build_qso_dict`, `find_duplicate`, `import_qsos_from_bytes`, `_REQUIRED_FIELDS` — all available and tested
- `/Users/royco/ollog/app/adif/parser.py` — `parse_adi` signature and behavior
- `/Users/royco/ollog/app/qso/models.py` — `QSO` Beanie document, `QSO(**dict).insert()` pattern
- `/Users/royco/ollog/app/auth/models.py` — `User` document with all profile fields
- `/Users/royco/ollog/app/feed/manager.py` — `watch_qsos` change stream; reacts to all inserts, no code change needed
- `/Users/royco/ollog/app/main.py` — existing lifespan structure; `_bootstrap_admin` placement, `watcher_task` pattern
- `/Users/royco/ollog/app/config.py` — `settings.udp_operator: str | None`
- `/Users/royco/ollog/tests/test_qso_stamping.py` — `User.model_construct()` pattern for unit tests without DB
- `/Users/royco/ollog/tests/test_duplicate_detection.py` — integration test pattern with `AsyncMongoClient` + `init_beanie`
- [Python 3.14 asyncio tasks — create_task GC](https://docs.python.org/3/library/asyncio-task.html) — `_background_tasks` set + `add_done_callback(discard)` is documented canonical pattern

### Secondary (MEDIUM confidence)

- [Ruff RUF006 asyncio-dangling-task](https://docs.astral.sh/ruff/rules/asyncio-dangling-task/) — confirms lint rule fires when `create_task` result is not stored; `_background_tasks` set is the fix
- [cpython issue #91887](https://github.com/python/cpython/issues/91887) — task GC behavior, strong reference requirement

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all existing project code, directly read from filesystem
- Architecture (what files change and how): HIGH — directly inferred from Phase 16 skeleton + existing service layer
- Pipeline logic: HIGH — `build_qso_dict`, `find_duplicate`, `QSO.insert()` are directly observable and tested
- SSE integration: HIGH — `watch_qsos` change stream confirmed to fire on all inserts; zero changes confirmed
- Pitfalls: HIGH — each pitfall derived from reading actual code, not assumptions
- Test patterns: HIGH — `User.model_construct()` and `AsyncMongoClient`+`init_beanie` patterns confirmed in existing tests

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable stdlib + project codebase; 30 days)
