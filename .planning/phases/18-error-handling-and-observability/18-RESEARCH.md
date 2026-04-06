# Phase 18: Error Handling and Observability - Research

**Researched:** 2026-04-06
**Domain:** Python stdlib `logging`, pytest `caplog`, asyncio error handling
**Confidence:** HIGH

---

## Summary

Phase 18 is a targeted refinement of existing log lines in `app/udp/server.py`. The full UDP pipeline already works correctly (Phases 16 + 17 complete, all 8 unit tests passing). The requirement is to make every datagram outcome observable via structured log lines that include a `disposition=` token (`accepted`, `rejected`, or `duplicate`) alongside the source IP:port, and to add tests that assert on log content.

No new production dependencies are needed. The entire implementation is `app/udp/server.py` log-line edits plus new test cases in `tests/test_udp_pipeline.py` that use pytest's built-in `caplog` fixture. The existing `try/except Exception: logger.exception(...)` block in `_handle_datagram` already handles OBS-02. The existing `error_received()` already handles OBS-03. The only real work is reformatting the INFO/WARNING log strings to contain the required fields.

**Primary recommendation:** Edit the four `logger.*` call sites in `_handle_datagram` that handle accepted/rejected/duplicate outcomes so each line contains `src=%s:%s`, `callsign=%s` (where parsed), and `disposition=accepted|rejected|duplicate`. Then write 5 new `caplog` tests in `tests/test_udp_pipeline.py` that assert on these exact tokens.

---

## Standard Stack

### Core (all already in project — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `logging` (stdlib) | Python 3.14 | Structured log output | Already the project logger; `logging.getLogger(__name__)` pattern used everywhere |
| `pytest` | >=8.0 (project constraint) | Test runner | Already in `pyproject.toml` dev deps |
| `pytest-asyncio` | >=0.23 (project constraint) | `@pytest.mark.asyncio` support | Already used in `tests/test_udp_pipeline.py` |
| `caplog` (pytest built-in) | bundled with pytest | Log record capture in tests | No install needed — built into pytest; zero new deps |

### No New Packages Required

```bash
# No installation needed — all dependencies already present
```

---

## Architecture Patterns

### What Changes and What Stays the Same

```
app/
└── udp/
    └── server.py      # MODIFY: reformat 4 log-line call sites in _handle_datagram

tests/
└── test_udp_pipeline.py  # MODIFY: add 5 caplog-asserting test functions
```

No other files change. `app/main.py`, `app/qso/service.py`, `app/adif/parser.py`, `app/config.py` — all untouched.

### Pattern 1: Structured Log Line Format

**What:** Each log line in `_handle_datagram` that represents a datagram outcome includes three tokens in a consistent order: `src=IP:PORT`, optionally `call=CALLSIGN`, and `disposition=DISPOSITION`. This makes the lines `grep`-able by operators.

**Disposition values:**
- `accepted` — QSO was parsed and inserted successfully
- `rejected` — QSO was discarded for a stated reason (parse failure, missing field)
- `duplicate` — QSO matched an existing record within the dedup window

**Format conventions used in this project:** stdlib `%`-style formatting, positional args. No JSON logging library, no structured-logging library. Format string carries the field names as literal tokens.

**Required log lines:**

```python
# Source: Success criteria in phase description + analysis of app/udp/server.py

# accepted (currently logs id/band/mode/operator — needs disposition= token + callsign explicit)
logger.info(
    "UDP datagram src=%s:%s call=%s disposition=accepted",
    addr[0], addr[1], qso_dict["CALL"],
)

# rejected — parse failure (currently: no clear rejection log after parse_errors check)
logger.warning(
    "UDP datagram src=%s:%s disposition=rejected reason=parse-failure",
    addr[0], addr[1],
)

# rejected — missing required field  (currently missing 'disposition=' token)
logger.warning(
    "UDP datagram src=%s:%s disposition=rejected reason=\"missing required field: %s\"",
    addr[0], addr[1], sorted(missing)[0],   # per success criterion: name ONE field
)

# duplicate (currently lacks 'disposition=' token and callsign)
logger.info(
    "UDP datagram src=%s:%s call=%s disposition=duplicate",
    addr[0], addr[1], qso_dict["CALL"],
)
```

**Log level summary:**
| Outcome | Level | Reason |
|---------|-------|--------|
| accepted | INFO | Normal operation |
| rejected | WARNING | Operator should investigate |
| duplicate | INFO | Expected operation, not an error |
| parse failure (OBS-02) | WARNING | Malformed input |
| transport error (OBS-03) | WARNING | OS-level anomaly, already done |

### Pattern 2: pytest caplog Fixture for Log Assertions

**What:** `caplog` is a built-in pytest fixture that captures log records emitted during a test. It requires `propagate=True` on the logger (the default) — no special configuration needed.

**Critical detail:** `caplog` only captures logs at or above the level set on the fixture. The default capture level is `WARNING`. To capture `INFO` records, the test must set `caplog.set_level(logging.INFO)` or use the `caplog.at_level(logging.INFO)` context manager. The logger name must match; use `caplog.set_level(logging.INFO, logger="app.udp.server")` to scope it.

**Fixture signature:**
```python
# Source: https://docs.pytest.org/en/stable/how-to/logging.html
# caplog is injected by pytest; no import needed

@pytest.mark.asyncio
async def test_accepted_datagram_log(caplog, udp_user):
    with caplog.at_level(logging.INFO, logger="app.udp.server"):
        # ... call _handle_datagram ...
    assert "disposition=accepted" in caplog.text
    assert "127.0.0.1:9999" in caplog.text
    assert "W1AW" in caplog.text
```

**Assertion patterns:**
```python
# caplog.text — concatenated string of all captured log lines (simplest)
assert "disposition=accepted" in caplog.text

# caplog.records — list of logging.LogRecord objects (for level assertions)
assert any(r.levelno == logging.INFO for r in caplog.records)
assert any(r.levelno == logging.WARNING for r in caplog.records)

# Filter to specific logger
server_records = [r for r in caplog.records if r.name == "app.udp.server"]
```

**Important:** `caplog` is NOT available to `asyncio.create_task()` dispatched tasks by default if the test doesn't await completion. Since `_handle_datagram` is tested directly (called directly with `await`, not via `create_task`), `caplog` captures its output correctly. The existing 8 tests call `_handle_datagram` directly — continue this pattern.

### Pattern 3: Testing error_received() Continuation

**What:** Success criterion 5 requires that a simulated transport error is logged at WARNING and the listener continues running. Since `error_received` is a synchronous method, it can be tested by instantiating `QSODatagramProtocol` directly and calling `error_received(OSError("simulated"))`.

**What "continues running" means for the test:** The protocol does not set a stopped-state flag, does not call `self.transport.close()`, and the `datagram_received` method remains callable after `error_received` is called. This is testable without a real socket.

```python
# Source: analysis of app/udp/server.py + asyncio.DatagramProtocol docs
@pytest.mark.asyncio
async def test_error_received_logs_warning_and_continues(caplog):
    protocol = QSODatagramProtocol(operator="VK2ABC", user=None)
    with caplog.at_level(logging.WARNING, logger="app.udp.server"):
        protocol.error_received(OSError("ICMP unreachable"))
    assert any("WARNING" in r.levelname for r in caplog.records)
    # Protocol is not in a stopped state — it can still receive datagrams
    assert protocol.transport is None  # never started — that's fine, still alive
```

### Pattern 4: Testing Binary Garbage Input (OBS-02)

**What:** Sending a binary garbage datagram (e.g., `b"\x00\xFF\xFE"`) must produce exactly one WARNING and not crash. This is already handled by the `try/except Exception: logger.exception(...)` block — the decode step uses `errors="replace"` so it doesn't raise on bad bytes, but `parse_adi` returns no records, producing a WARNING.

**The test:** Use `caplog` to assert exactly one log record at WARNING or above, and assert the `_handle_datagram` coroutine completes without raising.

```python
@pytest.mark.asyncio
async def test_garbage_datagram_single_warning_no_crash(caplog, udp_user):
    with caplog.at_level(logging.WARNING, logger="app.udp.server"):
        await _handle_datagram(
            b"\x00\xFF\xFE\xAB garbage bytes",
            ("127.0.0.1", 9999),
            operator="VK2ABC",
            user=udp_user,
        )
    warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warning_records) == 1
    assert "disposition=rejected" in caplog.text
```

**Caveat:** The current log-after-parse-errors path (lines 53-55) logs a WARNING for parse errors, then line 58-60 logs another WARNING for "no records found". For garbage input, both may fire — that would be 2 WARNINGs. The Phase 18 plan must consolidate these into one: either suppress the parse-errors log when there are no records (combine into a single WARNING), or only emit the "no records" WARNING and skip the parse-errors detail. Success criterion 4 says "exactly one WARNING log line." This is the main non-trivial decision in Phase 18.

### Anti-Patterns to Avoid

- **Using `logging.disable()` to test log suppression:** Don't touch the global log level; use `caplog.at_level()` scoped to the test.
- **Asserting `caplog.records` length across the full test function without scoping:** If setUp code or fixtures also log, the count will be wrong. Scope captures with `caplog.at_level()` context manager, and filter by `r.name == "app.udp.server"`.
- **Calling `logger.exception()` for rejected/duplicate cases:** `logger.exception()` logs at ERROR and includes a traceback. Rejected and duplicate are expected operations — use `logger.warning()` and `logger.info()` respectively. Only genuine unhandled exceptions use `logger.exception()`.
- **Separate parse-errors and no-records WARNING lines for garbage input:** Success criterion 4 requires exactly one WARNING for garbage input. Consolidate the two existing WARNING paths (parse_errors and no-records) into a single log when garbage causes parse failure.
- **Putting `disposition=` only in the message body but not matching the callsign:** Success criteria 1-3 all require callsign in the log line. For `rejected` cases where the callsign was never parsed, omit the callsign token or use `call=<unknown>`.

---

## The Exact Gap: Current vs Required Log Lines

This is the core of Phase 18. Every other piece is already working.

| Outcome | Current log line | Phase 18 required | Gap |
|---------|-----------------|-------------------|-----|
| accepted | `"UDP QSO inserted: id=%s call=%s band=%s mode=%s operator=%s"` at INFO | `src=IP:PORT call=CALLSIGN disposition=accepted` at INFO | Missing `src=` and `disposition=` tokens |
| rejected — missing field | `"UDP datagram from %s rejected — missing required field(s): %s"` at WARNING | `src=IP:PORT disposition=rejected reason="missing required field: BAND"` at WARNING | Missing `disposition=` token; reason must name ONE field not a list |
| rejected — no records | `"UDP datagram from %s: no ADIF records found"` at WARNING | `src=IP:PORT disposition=rejected reason=parse-failure` at WARNING | Missing `disposition=` token |
| duplicate | `"UDP datagram from %s: duplicate of existing QSO %s — skipped"` at INFO | `src=IP:PORT call=CALLSIGN disposition=duplicate` at INFO | Missing `disposition=` and callsign tokens |
| parse errors warning | `"UDP datagram from %s had parse errors: %s"` at WARNING | Must NOT produce separate WARNING for garbage; consolidate with no-records | Two warnings become one for garbage input (success criterion 4) |
| transport error | `"UDP transport error: %s"` at WARNING in `error_received()` | Already at WARNING — no change needed | None |

**Line count for the change:** 6 `logger.*` call sites in `_handle_datagram`, all in `app/udp/server.py` lines 43-110.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Log capture in tests | Custom logging handler in test setup | `pytest caplog` fixture | Built into pytest, zero setup, scoped to test function, thread-safe |
| Structured log format | JSON logging library (`structlog`, `python-json-logger`) | stdlib `logging` with `%`-style key=value tokens | Project already uses stdlib logging; new library would be a new production dependency — locked out by the "no new prod deps" principle from Phase 16 |
| Log level filtering | Global `logging.disable()` | `caplog.set_level()` or `caplog.at_level()` context manager | Global changes affect all tests in the session |

**Key insight:** Phase 18 is a log-line editing task. There is no new framework, no new library, no architectural change. All the complexity is in getting the log format exactly right and writing tests that assert on it.

---

## Common Pitfalls

### Pitfall 1: caplog Misses INFO Records

**What goes wrong:** Test asserts `"disposition=accepted" in caplog.text` but the assertion fails even though the INFO log fires, because `caplog` defaults to capturing only WARNING+ records.

**Why it happens:** pytest's `caplog` fixture default level is `WARNING`. INFO records are emitted but not captured.

**How to avoid:** Every test that asserts on INFO records must use `caplog.set_level(logging.INFO, logger="app.udp.server")` or `caplog.at_level(logging.INFO, logger="app.udp.server")`.

**Warning signs:** Test fails with `AssertionError: assert "disposition=accepted" in ""` — empty `caplog.text` is the giveaway.

### Pitfall 2: Two WARNINGs for Garbage Input (Fails Criterion 4)

**What goes wrong:** The existing code logs `parse_errors` at WARNING (line 53) and then logs "no ADIF records found" at WARNING (line 58) when garbage input causes `parse_adi` to return no records and non-empty errors. This produces two WARNINGs for a single garbage datagram, failing success criterion 4 ("exactly one WARNING log line").

**Why it happens:** The two conditions are independent checks; both fire for the same garbage input.

**How to avoid:** Merge them. When `parse_errors` is non-empty AND `records` is empty, emit one WARNING: `"disposition=rejected reason=parse-failure"`. Only emit the "no records" WARNING when `parse_errors` is empty (e.g., well-formed ADIF header with no `<EOR>` tags).

**Warning signs:** Test `test_garbage_datagram_single_warning_no_crash` counting `warning_records` finds 2 instead of 1.

### Pitfall 3: Missing Callsign in Duplicate and Accepted Log Lines

**What goes wrong:** Duplicate log currently uses `addr` and `dup.id` but not the callsign. Accepted log uses `qso_dict["CALL"]` but buries it after `id=` and `band=`. Success criteria 1 and 3 explicitly require callsign in the log line.

**Why it happens:** Old log lines were designed for debugging (`id=`, `band=`, `mode=`) rather than observability (`call=`, `disposition=`).

**How to avoid:** Both `accepted` and `duplicate` log lines must include `call=%s` formatted with `qso_dict["CALL"]`. Since `qso_dict` is built before the duplicate check, the callsign is available in both branches.

### Pitfall 4: addr Format — `%s` vs `%s:%s`

**What goes wrong:** `addr` is a `tuple[str, int]`. Using `%s` with the tuple produces `('127.0.0.1', 9999)` in the log. Success criteria say `source IP:port` format. Test assertions on `"127.0.0.1:9999"` would fail.

**Why it happens:** `addr` is a tuple; `%s` with a tuple prints the repr.

**How to avoid:** Use two positional args: `addr[0], addr[1]` with `src=%s:%s` in the format string. This is already done in some existing log lines (`datagram_received` at line 136-140) but not consistently in `_handle_datagram`. Audit all `logger.*` calls in `_handle_datagram` after editing.

### Pitfall 5: error_received() Already Correct — Don't Break It

**What goes wrong:** Overzealous refactoring changes `error_received()` when it already satisfies OBS-03. The current implementation at line 148-149 logs at WARNING with the exception message. It does NOT call `transport.close()`, so the listener continues running.

**Why it happens:** Phase 18 appears to require changes to error handling; developer assumes `error_received` needs work.

**How to avoid:** Read the current `error_received` implementation before touching it. It already conforms to OBS-03. Only add a test; do not change the code.

---

## Code Examples

### Consolidated accepted log line

```python
# Source: analysis of app/udp/server.py + phase 18 success criteria
# Replaces lines 100-107 in server.py (the insert-success logger.info)
logger.info(
    "UDP datagram src=%s:%s call=%s disposition=accepted",
    addr[0], addr[1], qso_dict["CALL"],
)
```

### Consolidated rejected — missing required field

```python
# Replaces lines 74-79 in server.py
# Success criterion 2: "missing required field: BAND" — name one field
# sorted(missing)[0] gives the first alphabetically when multiple fields missing
logger.warning(
    "UDP datagram src=%s:%s disposition=rejected reason=\"missing required field: %s\"",
    addr[0], addr[1], sorted(missing)[0],
)
return
```

### Consolidated rejected — parse failure (merges lines 53-60)

```python
# Replace the existing two-branch WARNING with a single check:
if parse_errors or not records:
    logger.warning(
        "UDP datagram src=%s:%s disposition=rejected reason=parse-failure",
        addr[0], addr[1],
    )
    return
```

### Consolidated duplicate log line

```python
# Replaces lines 91-95 in server.py
logger.info(
    "UDP datagram src=%s:%s call=%s disposition=duplicate",
    addr[0], addr[1], qso_dict["CALL"],
)
return
```

### caplog test: accepted datagram

```python
# Source: https://docs.pytest.org/en/stable/how-to/logging.html
import logging
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.udp.server import _handle_datagram

@pytest.mark.asyncio
async def test_accepted_datagram_log(caplog, udp_user):
    mock_qso = MagicMock()
    mock_qso.insert = AsyncMock()
    mock_qso.id = "abc123"
    with caplog.at_level(logging.INFO, logger="app.udp.server"):
        with (
            patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=None)),
            patch("app.qso.models.QSO", return_value=mock_qso),
        ):
            await _handle_datagram(
                _SAMPLE_ADIF.encode(), ("127.0.0.1", 9999), "VK2ABC", udp_user
            )
    assert "disposition=accepted" in caplog.text
    assert "127.0.0.1:9999" in caplog.text
    assert "W1AW" in caplog.text
    info_records = [r for r in caplog.records if r.levelno == logging.INFO and "disposition=accepted" in r.message]
    assert len(info_records) == 1
```

### caplog test: rejected — missing field

```python
@pytest.mark.asyncio
async def test_rejected_missing_field_log(caplog, udp_user):
    adif_no_band = "<CALL:4>W1AW<MODE:3>SSB<QSO_DATE:8>20260406<TIME_ON:4>1200<EOR>"
    with caplog.at_level(logging.WARNING, logger="app.udp.server"):
        await _handle_datagram(
            adif_no_band.encode(), ("127.0.0.1", 9999), "VK2ABC", udp_user
        )
    assert "disposition=rejected" in caplog.text
    assert "missing required field" in caplog.text
    assert "127.0.0.1:9999" in caplog.text
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) == 1
```

### caplog test: duplicate

```python
@pytest.mark.asyncio
async def test_duplicate_datagram_log(caplog, udp_user):
    existing = MagicMock()
    existing.id = "dup123"
    with caplog.at_level(logging.INFO, logger="app.udp.server"):
        with patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=existing)):
            await _handle_datagram(
                _SAMPLE_ADIF.encode(), ("127.0.0.1", 9999), "VK2ABC", udp_user
            )
    assert "disposition=duplicate" in caplog.text
    assert "W1AW" in caplog.text
    assert "127.0.0.1:9999" in caplog.text
```

### caplog test: garbage datagram — exactly one WARNING

```python
@pytest.mark.asyncio
async def test_garbage_datagram_single_warning_no_crash(caplog, udp_user):
    with caplog.at_level(logging.WARNING, logger="app.udp.server"):
        await _handle_datagram(
            b"\x00\xFF\xFE\xAB garbage bytes",
            ("127.0.0.1", 9999),
            operator="VK2ABC",
            user=udp_user,
        )
    warning_records = [
        r for r in caplog.records
        if r.levelno >= logging.WARNING and r.name == "app.udp.server"
    ]
    assert len(warning_records) == 1
    assert "disposition=rejected" in caplog.text
```

### caplog test: transport error continuation

```python
@pytest.mark.asyncio
async def test_error_received_logs_warning_and_continues(caplog):
    from app.udp.server import QSODatagramProtocol
    protocol = QSODatagramProtocol(operator="VK2ABC", user=None)
    with caplog.at_level(logging.WARNING, logger="app.udp.server"):
        protocol.error_received(OSError("ICMP unreachable"))
    assert any(r.levelno == logging.WARNING for r in caplog.records)
    # Protocol has not stopped — still accepts datagrams
    # (no stopped_flag attribute, transport still None from never being started)
    assert protocol.transport is None
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Ad-hoc log messages for debugging | Structured `key=value` tokens for observability | Phase 18 | Log lines become `grep`-able by operators |
| Two separate WARNINGs for parse failure | Single WARNING with `disposition=rejected` | Phase 18 | Exactly one log line per bad datagram |
| Accepted log buries callsign among `id=`/`band=`/`mode=` details | `call=CALLSIGN disposition=accepted` as primary tokens | Phase 18 | Callsign is immediately visible without parsing |

**Deprecated/outdated after Phase 18:**
- The `"UDP QSO inserted: id=%s call=%s band=%s mode=%s operator=%s"` log format: replace with `disposition=accepted` format. The extra fields (`id`, `band`, `mode`, `operator`) may be dropped or kept as secondary tokens — the success criteria only require `src`, `callsign`, and `disposition`.

---

## Open Questions

1. **Format for missing-field reason when multiple fields are missing**
   - What we know: Success criterion 2 says "the specific reason (e.g., `missing required field: BAND`)" — singular. But `_REQUIRED_FIELDS` has 5 fields; a datagram could be missing all of them.
   - What's unclear: Should the log name only the first alphabetically, or list all of them?
   - Recommendation: Log only the first missing field (`sorted(missing)[0]`). This satisfies "specific reason" per the example given. If multiple fields are missing, the operator will fix the most fundamental issue first.

2. **Preserving existing detail in accepted log line**
   - What we know: Current accepted log includes `id=`, `band=`, `mode=`, `operator=` — useful for correlation but not required by Phase 18.
   - What's unclear: Whether the planner should preserve these as secondary tokens or drop them.
   - Recommendation: Keep `id=` as secondary: `"UDP datagram src=%s:%s call=%s disposition=accepted id=%s"`. Operators benefit from the QSO ID for follow-up queries. Drop `band=`, `mode=`, `operator=` to keep the line scannable.

3. **caplog and pytest-asyncio interaction**
   - What we know: `caplog` is a synchronous fixture; `@pytest.mark.asyncio` is used for all existing UDP tests; they interact without issues.
   - What's unclear: Whether `caplog.at_level()` as a context manager inside an async test function captures logs from awaited coroutines correctly.
   - Recommendation: Use `caplog.set_level(logging.INFO, logger="app.udp.server")` at the top of the test function body (not as a context manager) to avoid any edge cases. The existing tests call `_handle_datagram` directly with `await` — this is synchronous-enough for `caplog` to work. Confirmed pattern: `caplog` captures logs from awaited coroutines in the same task.

---

## Sources

### Primary (HIGH confidence)

- `/Users/royco/ollog/app/udp/server.py` — current log lines, line numbers, exact format strings (read directly)
- `/Users/royco/ollog/tests/test_udp_pipeline.py` — existing test structure, `udp_user` fixture, mock patterns (read directly)
- `/Users/royco/ollog/pyproject.toml` — confirms `pytest>=8.0`, `pytest-asyncio>=0.23` (read directly)
- `/Users/royco/ollog/tests/conftest.py` — confirms no `asyncio_mode` config; tests use `@pytest.mark.asyncio` explicitly (read directly)
- [pytest logging documentation](https://docs.pytest.org/en/stable/how-to/logging.html) — `caplog` fixture API, `set_level`, `at_level`, `records`, `text` attributes

### Secondary (MEDIUM confidence)

- [Python 3.14 logging HOWTO](https://docs.python.org/3/howto/logging.html) — stdlib `logging` module; `%`-style formatting; no structural changes needed
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/) — async test fixtures and `caplog` interaction; confirmed compatible

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib + already-installed packages, confirmed from pyproject.toml
- Architecture (what files change): HIGH — directly read current server.py and confirmed gap
- Log line format: HIGH — success criteria are explicit; gap from current format is unambiguous
- caplog patterns: HIGH — verified against official pytest docs; same pattern used in many projects
- Pitfalls: HIGH — each pitfall derived from reading actual code, not assumptions; "two WARNINGs for garbage" is a concrete observable fact in the current code

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable stdlib + project codebase; 30 days)
