# Phase 16: UDP Infrastructure - Research

**Researched:** 2026-04-05
**Domain:** Python asyncio UDP / FastAPI lifespan / Docker Compose networking
**Confidence:** HIGH

---

## Summary

Phase 16 binds a UDP listener socket and lifecycle-manages it alongside the existing FastAPI lifespan that already manages MongoDB and a change-stream watcher task. The implementation uses only stdlib `asyncio.DatagramProtocol` — no new production dependencies. The lifespan pattern is already established in `app/main.py`; the UDP transport slots in immediately after the watcher task startup and closes immediately before `close_db()`.

A prerequisite refactor must move the size-limit guard out of `process_import()` in `app/adif/router.py` — currently it raises `HTTPException` — into a new `app/qso/service.py` function that raises `ValueError`. Both `app/adif/router.py` and `app/qso/ui_router.py` import `process_import`; after the refactor they both call the service function. Phase 17 (UDP QSO parsing) then calls the same service function from an async task with no HTTP context.

**Primary recommendation:** Implement `QSODatagramProtocol(asyncio.DatagramProtocol)` in `app/udp/server.py`, start/stop it in the existing `lifespan()` in `app/main.py`, guard with `settings.udp_enabled`, and store the transport on module state so it can be closed on shutdown.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `asyncio` (stdlib) | Python 3.14 | UDP socket lifecycle | Locked decision — no new prod deps |
| `asyncio.DatagramProtocol` | stdlib | Datagram receive callbacks | Official stdlib protocol interface |
| `pydantic_settings` | already in project | 4 new config fields | Already used in `app/config.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `logging` (stdlib) | stdlib | Startup banner, receipt log | Already used project-wide |
| `nc` (netcat) | system tool | Manual smoke-test without Docker | Testing only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `asyncio.DatagramProtocol` | `asyncio-dgram` PyPI package | Third-party adds dependency; stdlib is sufficient for a receive-only listener |

**Installation:**
No new packages required. All dependencies already present.

---

## Architecture Patterns

### Recommended Project Structure
```
app/
├── udp/
│   ├── __init__.py          # empty marker
│   └── server.py            # QSODatagramProtocol + start_udp_listener()
├── config.py                # + 4 new fields: udp_enabled, udp_port, udp_bind_host, udp_operator
├── main.py                  # lifespan: UDP start after watcher_task, stop before close_db()
└── qso/
    └── service.py           # + insert_qso_from_dict() (extracted from process_import)
```

### Pattern 1: asyncio.DatagramProtocol skeleton

**What:** A class inheriting `asyncio.DatagramProtocol` with `connection_made`, `datagram_received`, `error_received`, and `connection_lost`. The transport reference is stored on the instance in `connection_made`.

**When to use:** Any time you need a UDP server socket that integrates with the running asyncio event loop.

**Example (verified from Python 3.14 official docs):**
```python
# Source: https://docs.python.org/3/library/asyncio-protocol.html
import asyncio
import logging

logger = logging.getLogger(__name__)


class QSODatagramProtocol(asyncio.DatagramProtocol):
    """Skeleton UDP listener — Phase 16 only receives and logs datagrams."""

    def __init__(self) -> None:
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:  # type: ignore[override]
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        logger.info("UDP datagram received from %s:%s (%d bytes)", addr[0], addr[1], len(data))

    def error_received(self, exc: Exception) -> None:
        logger.warning("UDP error received: %s", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        logger.info("UDP transport closed")
```

### Pattern 2: start_udp_listener() factory coroutine

**What:** A module-level coroutine that calls `loop.create_datagram_endpoint()` and returns `(transport, protocol)`. The lifespan stores the transport for cleanup.

**When to use:** Keeps `app/udp/server.py` self-contained; lifespan only calls `start_udp_listener()` and `transport.close()`.

```python
# Source: https://docs.python.org/3/library/asyncio-eventloop.html
async def start_udp_listener(
    host: str,
    port: int,
) -> tuple[asyncio.DatagramTransport, QSODatagramProtocol]:
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        QSODatagramProtocol,
        local_addr=(host, port),
    )
    logger.info("UDP listener bound to %s:%s", host, port)
    return transport, protocol
```

### Pattern 3: Lifespan integration in app/main.py

**What:** The existing lifespan already follows start-everything / yield / cancel-and-close pattern. UDP slots in exactly the same place as `watcher_task` — started after DB init, stopped before `close_db()`.

**Critical ordering:** UDP transport must close BEFORE `close_db()`. If Phase 17 dispatches async tasks that touch the DB, closing the transport first drains in-flight work before the DB connection drops.

```python
# Source: existing app/main.py + asyncio docs pattern
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _bootstrap_admin()

    # Change-stream watcher (already exists)
    client = get_client()
    watcher_task = None
    if client is not None:
        from app.feed.manager import manager as feed_manager, watch_qsos
        collection = client[settings.mongodb_db]["qsos"]
        watcher_task = asyncio.create_task(
            watch_qsos(collection, feed_manager, _templates)
        )

    # UDP listener (new in Phase 16)
    udp_transport = None
    if settings.udp_enabled:
        from app.udp.server import start_udp_listener
        udp_transport, _ = await start_udp_listener(
            settings.udp_bind_host, settings.udp_port
        )

    yield

    # Shutdown — reverse order: UDP first, then watcher, then DB
    if udp_transport is not None:
        udp_transport.close()

    if watcher_task is not None:
        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass

    await close_db()
```

**Note:** `transport.close()` is synchronous (not a coroutine). It signals the OS to close the socket. There is no `await transport.close()`.

### Pattern 4: _background_tasks strong reference set

**What:** Phase 16 only logs datagrams (no background tasks yet). Phase 17 will dispatch `asyncio.create_task()` from `datagram_received`. The `_background_tasks` set must be established in Phase 16's `QSODatagramProtocol` so Phase 17 has the infrastructure ready.

**Why needed:** The event loop holds only a weak reference to tasks created with `create_task()`. Without a strong reference in a `set`, tasks can be garbage-collected before they complete (documented Python behavior since 3.12 warning).

```python
# Source: https://docs.python.org/3/library/asyncio-task.html
# In QSODatagramProtocol.__init__:
self._background_tasks: set[asyncio.Task] = set()

# In datagram_received (Phase 17 pattern — establish the plumbing in Phase 16):
# task = asyncio.create_task(self._handle_datagram(data, addr))
# self._background_tasks.add(task)
# task.add_done_callback(self._background_tasks.discard)
```

### Anti-Patterns to Avoid
- **`asyncio.get_event_loop()` in a coroutine:** Use `asyncio.get_running_loop()`. `get_event_loop()` is deprecated in coroutine/callback context since Python 3.10 and raises `DeprecationWarning`; in Python 3.14 it may raise `RuntimeError` when no current event loop is set.
- **`await transport.close()`:** `transport.close()` is synchronous. Awaiting it is a `TypeError`.
- **Calling `create_datagram_endpoint` before the event loop is running:** Must be called from within a coroutine (inside lifespan, not at module import time).
- **Catching `HTTPException` from a background task:** `HTTPException` is a Starlette class that only works inside the HTTP request/response cycle. A `datagram_received` callback has no HTTP context; any function it calls must raise plain Python exceptions (`ValueError`, `RuntimeError`, etc.).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UDP socket lifecycle | Custom `socket.socket()` setup | `loop.create_datagram_endpoint()` | Handles address resolution, socket options, event loop integration, and OS cleanup |
| Config parsing | Manual `os.environ.get()` | `pydantic_settings.BaseSettings` fields | Already the project pattern; type coercion and `.env` file loading are free |
| Task GC prevention | Custom reference tracking | `set` + `add_done_callback(set.discard)` | Documented stdlib pattern; handles cleanup automatically |

**Key insight:** `asyncio.DatagramProtocol` is a thin callback shell. All the hard work (socket creation, selector registration, buffer management) is done by the event loop's `create_datagram_endpoint`. The protocol class only needs to implement the three or four callbacks.

---

## Common Pitfalls

### Pitfall 1: HTTPException raised inside an async background task
**What goes wrong:** `process_import()` currently raises `HTTPException` for the 10 MB size guard. If Phase 17 calls `process_import()` from a `datagram_received`-dispatched task, the exception propagates into the event loop with no HTTP handler — it surfaces as an unhandled task exception and is silently swallowed or logged at WARNING with no user-visible error.
**Why it happens:** `HTTPException` is a Starlette response shortcut, not a real exception class with semantics. It only works inside a route handler's request/response lifecycle.
**How to avoid:** Extract the core of `process_import()` into a new `app/qso/service.py` function (`insert_qso_from_adif_bytes()` or similar) that raises `ValueError` for the size check and other validation errors. Keep `process_import()` in `app/adif/router.py` as a thin wrapper that converts `ValueError` to `HTTPException`. The UI router (`app/qso/ui_router.py`) already catches `HTTPException` from `process_import()` — after the refactor it catches `ValueError` from the service function.
**Warning signs:** If `process_import` is imported directly in Phase 17's handler, the 10 MB guard path will silently fail.

### Pitfall 2: UDP port not exposed in Docker Compose
**What goes wrong:** Docker Compose port mappings default to TCP. `"2399:2399"` maps only TCP/2399. UDP datagrams from the host to port 2399 are silently dropped by Docker.
**Why it happens:** Docker's port mapping is protocol-specific; TCP is the default.
**How to avoid:** Use `"2399:2399/udp"` in the short syntax. If both TCP and UDP are needed on the same port, list both: `"2399:2399/tcp"` and `"2399:2399/udp"`.

### Pitfall 3: Binding to 0.0.0.0 in Docker vs 127.0.0.1 locally
**What goes wrong:** Default `UDP_BIND_HOST=127.0.0.1` works for local development (loopback). Inside Docker, the app container must bind `0.0.0.0` to receive datagrams forwarded by the Docker UDP proxy.
**Why it happens:** Docker's userland UDP proxy forwards packets to the container's `0.0.0.0` interface, not loopback.
**How to avoid:** The default stays `127.0.0.1` per the locked decision. Docker deployments set `UDP_BIND_HOST=0.0.0.0` via environment variable in `docker-compose.yml` or `.env`.

### Pitfall 4: transport.close() not called on shutdown
**What goes wrong:** If the lifespan `yield` block raises or the app is killed with SIGTERM, the UDP socket may leak. On restart, `bind()` can fail with `Address already in use` (though less common for UDP than TCP due to lack of TIME_WAIT).
**Why it happens:** Exception in lifespan yield path skips the cleanup code if not in a try/finally block.
**How to avoid:** The lifespan cleanup code (after `yield`) runs unconditionally in FastAPI's `asynccontextmanager` implementation because FastAPI wraps it in a try/finally. No extra try/finally needed in user code. Verify with a SIGTERM test.

### Pitfall 5: UDP_OPERATOR setting vs operator identity in Phase 17
**What goes wrong:** Phase 16 introduces `UDP_OPERATOR` config but doesn't use it yet. If Phase 17 forgets to look up the `User` document by callsign before inserting QSOs, it will either fail to stamp profile fields or insert records without operator isolation.
**Why it happens:** Config value is a callsign string, but `build_qso_dict` optionally takes a `User` profile object for auto-stamping.
**How to avoid:** Phase 16 should cache the `User` document at startup (the locked decision says "Operator User document cached at startup"). Add the cache lookup in lifespan after `_bootstrap_admin()`, store the `User` (or `None`) in a module-level variable in `app/udp/server.py`. Phase 17 uses that cached reference.

---

## Code Examples

### config.py — 4 new fields

```python
# Source: pydantic_settings docs + existing app/config.py pattern
class Settings(BaseSettings):
    # ... existing fields ...

    # UDP listener (Phase 16)
    udp_enabled: bool = False
    udp_port: int = 2399
    udp_bind_host: str = "127.0.0.1"
    udp_operator: str | None = None
```

All four fields use Pydantic's automatic env-var mapping: `UDP_ENABLED`, `UDP_PORT`, `UDP_BIND_HOST`, `UDP_OPERATOR`. The `bool` type coerces `"true"/"false"` strings from environment variables automatically in pydantic-settings.

### docker-compose.yml — UDP port exposure

```yaml
# Source: https://docs.docker.com/reference/compose-file/services/
api:
  build: .
  ports:
    - "8000:8000"
    - "2399:2399/udp"   # UDP listener for N1MM+/WSJTX/etc.
  environment:
    - UDP_BIND_HOST=0.0.0.0   # must be 0.0.0.0 inside Docker
    - UDP_ENABLED=false        # operator opts in
```

### Smoke test without Docker (loopback)

```bash
# Terminal 1 — start the app with UDP enabled
UDP_ENABLED=true uvicorn app.main:app --reload

# Terminal 2 — send a test datagram
echo -n "TEST" | nc -u -w1 127.0.0.1 2399
# or on macOS/BSD:
printf "TEST" | nc -u -c 127.0.0.1 2399
```

Expected log output:
```
INFO     app.udp.server: UDP listener bound to 127.0.0.1:2399
INFO     app.udp.server: UDP datagram received from 127.0.0.1:XXXXX (4 bytes)
```

### process_import() extraction — what moves and what stays

**Current state (`app/adif/router.py`):**
- `process_import(raw: bytes, operator: str) -> dict` — raises `HTTPException` for size guard

**Two callers today:**
1. `app/adif/router.py` `import_adif()` — HTTP route, can catch `HTTPException`
2. `app/qso/ui_router.py` line 483 — catches `HTTPException` explicitly (line 484)

**What moves to `app/qso/service.py`:**
```python
async def import_qsos_from_bytes(raw: bytes, operator: str) -> dict:
    """Core import logic — raises ValueError, not HTTPException.

    Callable from HTTP routes AND async background tasks (UDP handler).
    """
    if len(raw) > _MAX_BYTES:
        raise ValueError("File exceeds 10 MB limit")
    # ... rest of process_import body unchanged ...
```

**What stays in `app/adif/router.py`:**
```python
async def process_import(raw: bytes, operator: str) -> dict:
    """Thin HTTP wrapper — converts ValueError to HTTPException."""
    try:
        return await import_qsos_from_bytes(raw, operator)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        )
```

**`app/qso/ui_router.py` change:**
```python
# Before:
from app.adif.router import _qso_to_adif_dict, process_import
# ...
try:
    report = await process_import(raw, callsign)
except HTTPException as exc:

# After:
from app.adif.router import _qso_to_adif_dict
from app.qso.service import import_qsos_from_bytes
# ...
try:
    report = await import_qsos_from_bytes(raw, callsign)
except ValueError as exc:
```

**Constants (`_REQUIRED_FIELDS`, `_MAX_BYTES`) and models (`ADIFRecordAccepted`, etc.):**  
`_REQUIRED_FIELDS` and `_MAX_BYTES` must move with the logic to `app/qso/service.py` (or a shared `app/adif/` constants module). The Pydantic response models (`ADIFImportReport`, etc.) stay in `app/adif/router.py` since they are HTTP-response-specific.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `asyncio.get_event_loop()` | `asyncio.get_running_loop()` | Python 3.10 deprecation; error in 3.12+ | Code using old form may raise RuntimeError in Python 3.14 |
| Manual `socket` + `selector` | `loop.create_datagram_endpoint()` | Python 3.4+ | Zero boilerplate for event-loop-integrated UDP |
| Ignoring task GC | `_background_tasks` set + `add_done_callback(discard)` | Python 3.12 warning formalized | Tasks no longer silently drop without the strong reference |

**Deprecated/outdated:**
- `asyncio.get_event_loop()` in coroutine context: raises `DeprecationWarning` in 3.10–3.11, `RuntimeError` may occur in 3.12+ when called outside a running loop.

---

## Open Questions

1. **UDP_OPERATOR validation at startup**
   - What we know: `UDP_OPERATOR` is a callsign string in config; the `User` document must exist in MongoDB for QSO insertion in Phase 17.
   - What's unclear: Should Phase 16 fail startup (raise on missing user) or log a warning and disable UDP? The phase description says "cached at startup" but does not specify failure behavior.
   - Recommendation: Log a WARNING if `UDP_OPERATOR` is set but no matching User exists; do not fail startup. Phase 17 can enforce the hard requirement.

2. **`nc -u` flag portability**
   - What we know: `nc -u -w1` works on Linux; macOS `nc` uses `-c` for UDP close behavior.
   - What's unclear: The CI environment (if any) and whether smoke tests are scripted.
   - Recommendation: Document both forms in the task. No CI UDP test needed for Phase 16 (infrastructure only).

---

## Sources

### Primary (HIGH confidence)
- [Python 3.14 asyncio Transports and Protocols](https://docs.python.org/3/library/asyncio-protocol.html) — `DatagramProtocol` methods, echo server example, lifecycle semantics
- [Python 3.14 asyncio Event Loop](https://docs.python.org/3/library/asyncio-eventloop.html) — `create_datagram_endpoint` signature, `get_running_loop()` description
- [Python 3.14 asyncio Tasks](https://docs.python.org/3/library/asyncio-task.html) — `create_task` GC warning, `_background_tasks` set pattern
- [Docker Compose services reference](https://docs.docker.com/reference/compose-file/services/) — ports `/udp` syntax

### Secondary (MEDIUM confidence)
- [cpython issue #91887 — strong references for free-flying tasks](https://github.com/python/cpython/issues/91887) — confirms GC behavior change and recommended pattern
- [Ruff RUF006 asyncio-dangling-task rule](https://docs.astral.sh/ruff/rules/asyncio-dangling-task/) — confirms `_background_tasks` set is the canonical fix

### Tertiary (LOW confidence)
- [Andrei Pöhlmann — asyncio TCP/UDP servers](https://andrei.poehlmann.dev/post/async-python-server/) — blog post illustrating the pattern; confirms official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, confirmed against Python 3.14 official docs
- Architecture: HIGH — lifespan pattern directly observable in `app/main.py`; DatagramProtocol pattern is official docs example
- `process_import` extraction: HIGH — both call sites read directly from codebase; refactor scope is unambiguous
- Docker UDP syntax: HIGH — Docker official docs
- Pitfalls: HIGH for HTTPException issue (directly observable in code); HIGH for Docker bind host (well-documented Docker behavior)

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable Python stdlib; 30 days)
