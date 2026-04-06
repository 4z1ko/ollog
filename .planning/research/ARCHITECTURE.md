# Architecture Research: UDP Listener Integration

**Domain:** Adding a UDP listener to an existing FastAPI/asyncio/Beanie application
**Researched:** 2026-04-05
**Confidence:** HIGH — based on direct codebase inspection, Python 3.11+ official asyncio documentation, and verified patterns

---

## Summary

A UDP listener integrates cleanly into the existing ollog FastAPI app as an `asyncio.DatagramProtocol` started inside the `lifespan` context manager. Uvicorn runs its own asyncio event loop, and any async code called from within the lifespan coroutine runs on that same loop — so `asyncio.get_running_loop()` inside `lifespan` returns uvicorn's loop. The transport is held in a module-level variable and closed in the shutdown half of the lifespan. The UDP handler calls `asyncio.create_task()` for each datagram to avoid blocking the protocol callback, and the resulting QSO insert flows through the same MongoDB collection as HTTP-submitted QSOs, which means the existing SSE change stream watcher picks it up automatically — no SSE code changes required.

---

## asyncio UDP Pattern

### How `asyncio.DatagramProtocol` Works

`asyncio.DatagramProtocol` is a callback-based protocol. The event loop calls its methods synchronously on receipt of datagrams. Because the callbacks are synchronous (not `async def`), any async work must be dispatched with `asyncio.create_task()` — you cannot `await` inside `datagram_received`.

**Lifecycle methods:**

| Method | When Called | Notes |
|--------|-------------|-------|
| `connection_made(transport)` | Once, when endpoint is bound | Store the transport for later `sendto()` and `close()` |
| `datagram_received(data, addr)` | Each incoming datagram | `data` is `bytes`; `addr` is `(host, port)` tuple |
| `error_received(exc)` | OSError on send/recv | Log and discard; not fatal |
| `connection_lost(exc)` | Once, on close | Cleanup if needed |

### `loop.create_datagram_endpoint()` — How It Works

`loop.create_datagram_endpoint(protocol_factory, local_addr=...)` binds a UDP socket and returns `(transport, protocol)`. It is a coroutine (must be awaited). The transport's `close()` method shuts down the socket and triggers `connection_lost`.

### Uvicorn's Event Loop — The Key Fact

Uvicorn creates and runs its own asyncio event loop. The `lifespan` coroutine is awaited by uvicorn on that loop. Therefore:

- `asyncio.get_running_loop()` called inside `lifespan` returns uvicorn's loop — this is correct and idiomatic in Python 3.10+.
- Do NOT use the deprecated `asyncio.get_event_loop()` — in Python 3.10+ this emits a DeprecationWarning when called outside a running loop, and in Python 3.12+ it is an error.
- Do NOT call `asyncio.run()` inside the lifespan — that creates a second loop inside the running loop, which raises `RuntimeError: This event loop is already running`.

The UDP socket created via `loop.create_datagram_endpoint()` inside the lifespan runs on uvicorn's loop. HTTP handlers and UDP handlers share the same event loop, which is what makes `asyncio.create_task()` work to hand off datagram processing from the protocol callback.

### Exact Lifespan Integration Pattern

```python
# app/udp/server.py
import asyncio
import logging
from asyncio import DatagramTransport
from typing import Optional

logger = logging.getLogger(__name__)

_transport: Optional[DatagramTransport] = None


class QSODatagramProtocol(asyncio.DatagramProtocol):
    """UDP datagram receiver for ADIF QSO submissions."""

    def connection_made(self, transport: DatagramTransport) -> None:
        global _transport
        _transport = transport
        logger.info("UDP listener bound: %s", transport.get_extra_info("sockname"))

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        # datagram_received is synchronous — dispatch async work immediately
        asyncio.create_task(_handle_datagram(data, addr))

    def error_received(self, exc: Exception) -> None:
        logger.warning("UDP error received: %s", exc)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        logger.info("UDP listener closed")


async def start_udp_listener(host: str, port: int) -> None:
    """Bind the UDP listener on the running event loop."""
    loop = asyncio.get_running_loop()
    await loop.create_datagram_endpoint(
        QSODatagramProtocol,
        local_addr=(host, port),
    )
    logger.info("UDP listener started on %s:%d", host, port)


def stop_udp_listener() -> None:
    """Close the UDP transport — called from lifespan shutdown."""
    global _transport
    if _transport is not None and not _transport.is_closing():
        _transport.close()
        _transport = None
        logger.info("UDP listener stopped")
```

```python
# app/main.py — lifespan additions
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _bootstrap_admin()

    # Start change stream watcher
    client = get_client()
    watcher_task = None
    if client is not None:
        from app.feed.manager import manager as feed_manager, watch_qsos
        collection = client[settings.mongodb_db]["qsos"]
        watcher_task = asyncio.create_task(
            watch_qsos(collection, feed_manager, _templates)
        )

    # Start UDP listener if enabled
    if settings.udp_enabled:
        from app.udp.server import start_udp_listener
        await start_udp_listener(settings.udp_host, settings.udp_port)

    yield

    # Shutdown
    from app.udp.server import stop_udp_listener
    stop_udp_listener()

    if watcher_task is not None:
        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass

    await close_db()
```

### Why `asyncio.create_task()` in `datagram_received` Needs a Strong Reference

The Python asyncio documentation states the event loop holds only a weak reference to tasks. A task created with `create_task()` can be garbage-collected before it completes if nothing else holds a reference to it. For short-lived parse+insert tasks this is rarely a problem in practice, but the safe pattern is to collect task references:

```python
# In QSODatagramProtocol — safe create_task pattern
_background_tasks: set[asyncio.Task] = set()

def datagram_received(self, data: bytes, addr: tuple) -> None:
    task = asyncio.create_task(_handle_datagram(data, addr))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
```

This keeps a strong reference until the task completes and auto-cleans via the done callback.

---

## Module Structure

### New Module: `app/udp/`

```
app/
└── udp/
    ├── __init__.py        (empty)
    └── server.py          (DatagramProtocol class + start/stop functions + _handle_datagram)
```

No other sub-modules needed. The UDP path is simple enough to live entirely in one file.

### Why `app/udp/server.py` and Not Elsewhere

- `app/udp/` follows the established pattern: `app/qso/`, `app/auth/`, `app/feed/` — each concern owns its directory.
- Keeping the protocol class, transport management, and the async handler in one file avoids cross-module state sharing for a single-concern module.
- The module is imported inside the lifespan function body (not at module top level), which is already the pattern used in `app/main.py` for `app.feed.manager` — this avoids startup import side effects.

### Circular Import Prevention

The existing codebase already handles this correctly: heavy imports (especially those with Beanie models) are done inside the lifespan function body, not at module top level in `main.py`. The UDP module must follow the same rule.

**Safe import pattern for `app/udp/server.py`:**

```python
# app/udp/server.py — top of file
import asyncio
import logging
from asyncio import DatagramTransport
from typing import Optional

# Do NOT import Beanie models or services at module top level.
# Import them inside _handle_datagram to avoid circular import chains
# and premature Beanie initialization errors.

async def _handle_datagram(data: bytes, addr: tuple) -> None:
    # Imports here — safe because Beanie is initialized before any datagram arrives
    from app.adif.parser import parse_adi
    from app.auth.service import decode_access_token
    from app.auth.models import User
    from app.qso.service import build_qso_dict, find_duplicate
    from app.qso.models import QSO
    from app.config import settings
    from jwt import InvalidTokenError
    ...
```

This is acceptable because `_handle_datagram` is called at runtime, not at import time. Python caches module imports so the `from app.x import y` on repeated calls has negligible overhead after the first call.

Alternatively, all imports can be placed at the top of `server.py` after module-level constants (not inside the async function) — this is fine as long as `server.py` is itself imported lazily (inside the lifespan body), which it is.

**Recommended:** import `app.adif.parser`, `app.auth.service`, `app.qso.service`, and `app.qso.models` at the top of `server.py`. Import `app.config.settings` at the top. Do not import `app.auth.models.User` at the top if it causes circular import issues (test empirically — Beanie models are sometimes finicky). Use function-local imports as a fallback for any model that causes issues.

---

## Data Flow

### Full Datagram Processing Pipeline

```
UDP datagram arrives (bytes, addr)
    │
    ▼ QSODatagramProtocol.datagram_received() [synchronous]
    │   └── asyncio.create_task(_handle_datagram(data, addr))
    │
    ▼ _handle_datagram(data, addr) [async task, runs on uvicorn's event loop]
    │
    ├─ 1. DECODE BYTES
    │       text = data.decode("utf-8")
    │       (on UnicodeDecodeError: log warning, return)
    │
    ├─ 2. PARSE ADIF
    │       records, errors = parse_adi(text)
    │       (existing app/adif/parser.py — unchanged)
    │       (on parse error / empty records: log warning, return)
    │
    ├─ 3. AUTH — extract token from datagram
    │       Datagram format (proposed): first line is "TOKEN:<jwt>\n", rest is ADIF
    │       token = extract_token_from_datagram(text)
    │       payload = decode_access_token(token)
    │       callsign = payload["callsign"]
    │       user = await User.find_one({"username": payload["sub"]})
    │       (on InvalidTokenError, missing user, disabled user: log warning, return)
    │
    ├─ 4. VALIDATE — reuse QSOCreateRequest
    │       For each record in records:
    │           try:
    │               req = QSOCreateRequest(**record)
    │           except ValidationError as e:
    │               log warning with field errors, continue to next record
    │
    ├─ 5. BUILD + DEDUPLICATE
    │       merged = {**req.model_dump(), **(req.model_extra or {})}
    │       qso_dict = build_qso_dict(merged, callsign, profile=user)
    │       dup = await find_duplicate(...)
    │       if dup: log info ("duplicate suppressed"), continue
    │
    └─ 6. INSERT
            qso = QSO(**qso_dict)
            await qso.insert()
            log info ("UDP QSO inserted: CALL=..., BAND=..., MODE=...")
```

### UDP Datagram Wire Format

The datagram format is not standardised across the ham radio ecosystem. The existing app uses JWT Bearer tokens for auth. UDP datagrams have no HTTP headers, so the token must be embedded in the payload.

**Recommended format — newline-delimited prefix:**

```
TOKEN:<jwt_string>\n
<CALL:4>W1AW<BAND:3>20m<MODE:2>CW<QSO_DATE:8>20260405<TIME_ON:4>1430<EOR>
```

The first line is `TOKEN:` followed by the JWT. The remainder is a standard ADIF record stream. The `parse_adi` function already handles ADIF without a header (no `<EOH>` needed — the existing parser skips header detection when `<EOH>` is absent).

**Alternative — JSON format:**

```json
{"token": "eyJ...", "CALL": "W1AW", "BAND": "20m", "MODE": "CW", "QSO_DATE": "20260405", "TIME_ON": "1430"}
```

JSON is easier to generate from scripting languages and easier to parse. The downside: not compatible with standard ADIF-emitting loggers (N1MM+, WSJT-X, etc.) without a translation layer.

**Recommendation:** Implement both. Detect format by attempting JSON parse first; fall back to the TOKEN-prefix ADIF format. This enables both scripted integrations and future N1MM+-compatible adapters.

### SSE Feed Integration

The SSE feed works via a MongoDB change stream watcher (`app/feed/manager.py` — `watch_qsos`). The watcher watches for `operationType: "insert"` on the `qsos` collection. UDP-submitted QSOs call `qso.insert()` on the same `QSO` Beanie document, which writes to the same MongoDB collection, which triggers the same change stream event.

**No changes are needed to `app/feed/manager.py`, `app/feed/router.py`, or any SSE-related code.** UDP inserts flow into the SSE feed automatically.

---

## Error Handling

### Strategy: Log-and-Discard

UDP is connectionless and inherently fire-and-forget. There is no reliable way to send an error back to the sender at the application layer (the sender may not even be listening for a response). The strategy is:

1. Log all errors with enough context to diagnose (client IP:port, truncated raw data, exception type and message).
2. Discard the datagram and continue.
3. Never raise an unhandled exception from `_handle_datagram` — the task exception would be silently lost unless a done callback logs it.

### Error Categories

| Error | Handling | Log Level |
|-------|----------|-----------|
| UTF-8 decode failure | Discard | WARNING (include hex dump of first 64 bytes) |
| ADIF parse yields no records | Discard | WARNING (include raw text truncated to 200 chars) |
| Token missing from datagram | Discard | WARNING (include addr) |
| JWT invalid / expired | Discard | WARNING (include addr, exception message) |
| User not found / disabled | Discard | WARNING (include callsign from token) |
| Pydantic validation error | Discard this record, continue others | WARNING (include field errors) |
| Duplicate QSO | Skip (same as HTTP path) | INFO |
| MongoDB insert error | Discard | ERROR (include exception, this is infrastructure) |
| OSError in transport | Log from `error_received` | WARNING |

### Should There Be ACK/NACK Datagrams?

No, for v1. Reasons:
- Adds complexity on both sender and receiver.
- Most logging software (N1MM+, WSJT-X) does not expect or use ACKs from log aggregators.
- Duplicate detection already handles the most common failure mode (re-sent datagram).

If a future requirement demands confirmed delivery, switch to a streaming protocol (TCP/WebSocket) rather than bolting ACK/NACK onto UDP.

### Exception Guarding in `_handle_datagram`

```python
async def _handle_datagram(data: bytes, addr: tuple) -> None:
    try:
        await _process(data, addr)
    except Exception:
        logger.exception("Unhandled exception in UDP datagram handler (addr=%s)", addr)
```

This top-level try/except ensures that any unexpected exception is logged with full traceback rather than silently swallowed by the event loop's task garbage collector.

---

## Config

### Additions to `app/config.py`

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # UDP listener
    udp_enabled: bool = False
    udp_host: str = "0.0.0.0"
    udp_port: int = 2237

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }
```

**Field rationale:**

| Field | Default | Rationale |
|-------|---------|-----------|
| `udp_enabled` | `False` | Opt-in. Existing deployments are unaffected by default. The UDP port exposes an auth surface; it should be explicitly enabled. |
| `udp_host` | `"0.0.0.0"` | Bind all interfaces so Docker port forwarding works without extra config. |
| `udp_port` | `2237` | Matches the WSJT-X default UDP broadcast port — the de facto standard for ham radio UDP logging. If running alongside WSJT-X on the same host, operators need to pick a different port. |

**Environment variables (in `.env` or Docker Compose):**

```
UDP_ENABLED=true
UDP_HOST=0.0.0.0
UDP_PORT=2237
```

Pydantic BaseSettings auto-maps `UDP_ENABLED` → `udp_enabled`, `UDP_PORT` → `udp_port`, etc.

### Docker Compose Addition

```yaml
api:
  build: .
  ports:
    - "8000:8000"
    - "2237:2237/udp"     # UDP listener — add this line
  environment:
    - UDP_ENABLED=true
    - UDP_PORT=2237
```

The `/udp` suffix on the port mapping is required for Docker to forward UDP traffic (not just TCP). Without it, Docker forwards only TCP and UDP datagrams are silently dropped.

---

## Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `app/udp/__init__.py` | Empty — makes `app/udp` a package |
| `app/udp/server.py` | `QSODatagramProtocol` class, `start_udp_listener()`, `stop_udp_listener()`, `_handle_datagram()` |

### Modified Files

| File | Change Required |
|------|----------------|
| `app/config.py` | Add `udp_enabled: bool = False`, `udp_host: str = "0.0.0.0"`, `udp_port: int = 2237` to `Settings` |
| `app/main.py` | In `lifespan`: add `start_udp_listener` call (startup) and `stop_udp_listener` call (shutdown), both guarded by `settings.udp_enabled` |
| `docker-compose.yml` | Add `- "2237:2237/udp"` to `api.ports`; add `UDP_ENABLED`, `UDP_PORT` to `environment` |

### Unchanged Files

Everything else. In particular:
- `app/adif/parser.py` — reused as-is
- `app/auth/service.py` — `decode_access_token()` reused as-is
- `app/qso/service.py` — `build_qso_dict()`, `find_duplicate()` reused as-is
- `app/qso/models.py` — `QSO.insert()` called as-is
- `app/feed/manager.py` — unchanged; SSE feed picks up UDP inserts automatically
- `app/qso/router.py` — `QSOCreateRequest` imported into `server.py` for validation reuse

---

## Integration Points Summary

```
app/udp/server.py
  imports from:
    app/config.py          (settings.udp_port, settings.udp_host)
    app/adif/parser.py     (parse_adi)
    app/auth/service.py    (decode_access_token)
    app/auth/models.py     (User.find_one)
    app/qso/router.py      (QSOCreateRequest — for validation)
    app/qso/service.py     (build_qso_dict, find_duplicate)
    app/qso/models.py      (QSO.insert)
  called from:
    app/main.py            (lifespan: start_udp_listener, stop_udp_listener)

MongoDB collection "qsos"
  ← written by: app/udp/server.py (_handle_datagram → QSO.insert)
  ← written by: app/qso/router.py (HTTP POST /api/qsos)
  → watched by: app/feed/manager.py (watch_qsos change stream)
  → drives SSE: app/feed/router.py (no changes needed)
```

---

## Architectural Decisions

### Decision 1: DatagramProtocol + create_datagram_endpoint, Not a Third-Party Library

**Alternatives considered:** `asyncio-dgram` (higher-level wrapper), `aiohttp` UDP, a separate UDP process via multiprocessing.

**Chosen:** stdlib `asyncio.DatagramProtocol`.

**Rationale:** The stdlib pattern is 15-20 lines of code and has zero additional dependencies. `asyncio-dgram` adds a dependency for marginal ergonomic benefit. A separate process would require inter-process communication (queue, socket, or shared memory) to call `create_qso` — unnecessary complexity.

### Decision 2: Token in Datagram Payload, Not a Separate Auth Handshake

**Rationale:** UDP is stateless. A pre-shared auth handshake would require session state on the server (not appropriate for a stateless listener). JWT is already the app's auth mechanism; embedding it in each datagram is consistent and stateless.

**Trade-off:** JWT tokens have expiry. Long-running loggers must refresh their token. Operators should set `jwt_expire_minutes` appropriately (1440 = 24 hours is reasonable for logging sessions).

### Decision 3: `udp_enabled=False` Default

**Rationale:** Opening a UDP port in a production app should be an explicit operator decision. The default-off setting protects existing deployments that upgrade.

### Decision 4: Reuse `QSOCreateRequest` for Validation

**Rationale:** Pydantic validation via `QSOCreateRequest` catches the same field-level errors for UDP datagrams as for HTTP submissions. Code reuse and consistent validation behavior.

### Decision 5: No Response Datagram (ACK/NACK)

**Rationale:** See Error Handling section. Ham radio logging software (the primary sender) does not expect UDP acknowledgements. The added complexity is not justified for v1.

---

## Confidence Assessment

| Area | Confidence | Source |
|------|------------|--------|
| `asyncio.DatagramProtocol` API | HIGH | Python 3.11+ official documentation (docs.python.org/3/library/asyncio-protocol.html) |
| `loop.create_datagram_endpoint()` pattern | HIGH | Official docs + direct code inspection of existing asyncio usage in app |
| Uvicorn shares event loop with lifespan | HIGH | Uvicorn architecture docs + verified in ASGI event loop discussion (rob-blackbourn.medium.com) |
| `asyncio.get_running_loop()` in lifespan is correct | HIGH | Python 3.10+ official docs — this is the documented approach |
| SSE feed picks up UDP inserts automatically | HIGH | Direct inspection of `app/feed/manager.py` — watches `operationType: "insert"` on `qsos` collection; any QSO insert triggers it |
| `create_task` strong reference pattern | HIGH | Official CPython docs + cpython issue #104091 |
| Docker UDP port mapping syntax | HIGH | Docker Compose documentation |
| WSJT-X default UDP port 2237 | MEDIUM | Ham radio community documentation (N1MM+ docs, WSJT-X protocol docs) |

---

## Sources

**HIGH confidence:**
- [Python asyncio Transports and Protocols](https://docs.python.org/3/library/asyncio-protocol.html) — `DatagramProtocol`, `datagram_received`, `create_datagram_endpoint`
- [Python asyncio Event Loop](https://docs.python.org/3/library/asyncio-eventloop.html) — `get_running_loop()`, `create_datagram_endpoint()`
- [ASGI Event Loop Gotcha](https://rob-blackbourn.medium.com/asgi-event-loop-gotcha-76da9715e36d) — confirms ASGI apps (uvicorn) share their event loop with lifespan context

**MEDIUM confidence:**
- [N1MM Logger+ External UDP Messages](https://n1mmwp.hamdocs.com/appendices/external-udp-broadcasts/) — UDP datagram format reference for ham radio logging software
- [High-level UDP endpoints for asyncio (gist)](https://gist.github.com/vxgmichel/e47bff34b68adb3cf6bd4845c4bed448) — community-verified high-level wrapper pattern

**Direct codebase inspection (HIGH confidence):**
- `app/main.py` — existing lifespan pattern; how watcher_task is managed
- `app/feed/manager.py` — `watch_qsos` change stream subscription; confirms automatic pickup of any collection insert
- `app/config.py` — Pydantic BaseSettings structure; confirms where to add UDP fields
- `app/adif/parser.py` — `parse_adi` is pure, stateless, reusable
- `app/auth/service.py` — `decode_access_token` is synchronous, reusable
- `app/qso/service.py` — `build_qso_dict`, `find_duplicate` are async, reusable
- `app/qso/router.py` — `QSOCreateRequest` is the canonical validation model
- `docker-compose.yml` — existing port mapping structure

---

*Architecture research for: UDP listener integration milestone — ollog FastAPI + Beanie + MongoDB*
*Researched: 2026-04-05*
