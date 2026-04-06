# Stack Research: UDP ADIF Listener

**Domain:** UDP listener for ADIF datagrams — FastAPI asyncio integration
**Researched:** 2026-04-05
**Confidence:** HIGH for core asyncio approach (official Python docs); HIGH for Docker UDP syntax (official Docker docs); MEDIUM for asyncio-dgram assessment (PyPI + GitHub verified, 3.0.0 Jan 2026 release confirmed); LOW for WSJT-X / N1MM wire format specifics (community sources only)

---

## Context: What Already Exists (Do Not Re-Research)

Existing validated stack: Python 3.12+, FastAPI 0.135+, Beanie 2.1+, pymongo 4.16+ (AsyncMongoClient), uvicorn, Docker Compose, MongoDB 7 replica set, pydantic-settings, uv package manager.

`app/main.py` already uses `@asynccontextmanager async def lifespan(app)` with `asyncio.create_task()` for the change-stream watcher. The pattern for launching a background task in FastAPI's lifespan is already established and proven in this codebase.

`app/adif/parser.py` has `parse_adi(text: str)` — pure function, zero dependencies, ready to use.

`app/qso/service.py` has `build_qso_dict()` and `find_duplicate()` — both async-capable, Beanie-based.

---

## The Core Approach: stdlib Only

**Verdict: No new production dependencies are needed. Use `asyncio.DatagramProtocol` + `loop.create_datagram_endpoint()` from the Python standard library.**

This is not a gap in the ecosystem where a third-party library fills a missing capability. Python's asyncio has first-class UDP support via `asyncio.DatagramProtocol` and `loop.create_datagram_endpoint()`. The API is stable, well-documented, and runs on the same event loop as the FastAPI/uvicorn HTTP server. Adding a library for this would be over-engineering.

---

## Specific Question Answers

### Q1: asyncio.DatagramProtocol vs asyncio-dgram vs other third-party libs?

**Use `asyncio.DatagramProtocol` directly.** Here is why each option was evaluated:

| Option | Assessment | Verdict |
|--------|------------|---------|
| `asyncio.DatagramProtocol` | stdlib, Python 3.4+, stable API, zero deps, runs on the exact same event loop as uvicorn, full Python docs coverage | **USE THIS** |
| `asyncio-dgram` (jsbronder) | Wraps `DatagramProtocol` in a `StreamReader`-style async interface. v3.0.0 released January 2026, healthy per Snyk, requires Python >=3.9. Useful when you need `await stream.recv()` in a `while True` loop rather than callbacks. For a server that receives unsolicited datagrams and has no send requirement, it adds abstraction overhead with negligible benefit. | Skip for this use case |
| `aiohttp` UDP | `aiohttp` is an HTTP framework / client library. Its UDP support is for internal use (DNS resolver). Not appropriate here. | Do not use |
| `uvloop` | Drop-in asyncio event loop replacement (libuv-based). **Already installed in this project** (uvloop-0.22.1 is in the venv). It fully supports `create_datagram_endpoint()` and has UDP tests in its test suite. It is not a UDP library — it is an event loop. If uvicorn is already configured to use uvloop (or will be), UDP just works. | No action needed |
| Separate process / threading | Would break the requirement to share the asyncio event loop and Beanie's MongoDB connection. | Do not use |

**Why `asyncio.DatagramProtocol` is sufficient:** A UDP listener for ADIF is inherently callback-driven — datagrams arrive, you decode, parse, validate, and insert. There is no bidirectional stream to manage. The `datagram_received(data, addr)` callback is the entire interface needed.

### Q2: How does a UDP server integrate with FastAPI's lifespan?

The pattern is identical to the change-stream watcher already in `app/main.py`: create the endpoint during startup, store the transport, close it on shutdown.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- existing startup ---
    await init_db()
    await _bootstrap_admin()

    # --- UDP listener startup ---
    loop = asyncio.get_event_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: AdifUdpProtocol(),
        local_addr=("0.0.0.0", settings.udp_adif_port),
    )

    # --- existing change-stream watcher ---
    watcher_task = asyncio.create_task(watch_qsos(...))

    yield

    # --- UDP listener shutdown ---
    transport.close()

    # --- existing watcher teardown ---
    watcher_task.cancel()
    try:
        await watcher_task
    except asyncio.CancelledError:
        pass

    await close_db()
```

`create_datagram_endpoint()` is a coroutine that resolves immediately once the OS binds the socket — it does not block the event loop. The protocol's `datagram_received()` method is called by the event loop whenever a UDP packet arrives, on the same event loop thread as the HTTP request handlers. Because Beanie's `AsyncMongoClient` is already bound to this event loop, all `await QSO.insert()` calls inside the protocol handler work without any additional wiring.

**Important:** `asyncio.get_event_loop()` works correctly inside lifespan because uvicorn runs the application in an asyncio event loop. No `loop` parameter is needed on `create_datagram_endpoint` in Python 3.10+ (the `loop` parameter was deprecated in 3.8 and removed in 3.10 — use `asyncio.get_event_loop()` or `asyncio.get_running_loop()` before calling the endpoint creation).

### Q3: Any libraries that make UDP + asyncio cleaner?

For this use case: **No.** The stdlib approach is six lines of integration code. The `asyncio-dgram` library is worth knowing about for bidirectional or client-side UDP patterns, but the callback model of `DatagramProtocol` is a perfect fit for a receive-only listener that processes each datagram independently.

`uvloop` is already installed. If uvicorn is launched with `--loop uvloop` (or via uvloop's install hook), the UDP endpoint runs on the uvloop event loop transparently. No code change needed.

### Q4: How to expose a UDP port in Docker Compose?

Docker Compose defaults all port mappings to TCP. UDP requires an explicit `/udp` suffix or a long-syntax `protocol: udp` field.

**Short syntax (add to existing `api` service):**

```yaml
services:
  api:
    ports:
      - "8000:8000"          # existing HTTP (TCP)
      - "2237:2237/udp"      # UDP ADIF listener
```

**Long syntax (equivalent, more explicit):**

```yaml
services:
  api:
    ports:
      - target: 8000
        published: 8000
        protocol: tcp
      - target: 2237
        published: 2237
        protocol: udp
```

**Port number note:** Port 2237 is the conventional WSJT-X / N1MM Logger+ UDP broadcast port (standard in the amateur radio ecosystem). The port must be configurable via env var (`UDP_ADIF_PORT`) so operators can change it without rebuilding. Default to `2237`.

**If TCP and UDP are needed on the same port number:** They must be listed as two separate entries — one per protocol. Docker does not combine them.

### Q5: Python version constraints or asyncio UDP gotchas?

| Gotcha | Severity | Details | Mitigation |
|--------|----------|---------|------------|
| Windows ProactorEventLoop does not support UDP | HIGH (Windows only) | The default event loop on Windows (Python 3.8+) is `ProactorEventLoop`, which does not implement `create_datagram_endpoint()`. | Not relevant — this app runs in Docker on Linux. No action needed. |
| `loop` parameter removed in Python 3.10 | HIGH | `loop.create_datagram_endpoint(loop=loop)` was deprecated in 3.8 and removed in 3.10. Do not pass the `loop` keyword argument. | Use `asyncio.get_running_loop().create_datagram_endpoint(...)` inside a coroutine. |
| `error_received()` is called, not an exception | MEDIUM | When an ICMP Port Unreachable arrives (e.g., client sent to a dead port then ollog replies), asyncio calls `protocol.error_received(exc)` instead of raising. If not implemented, the default silently ignores it. | Implement `error_received(self, exc)` with a log warning. Do not let it crash. |
| Datagram size limit | LOW | asyncio UDP reads are bounded by the OS socket buffer. ADIF files as UDP datagrams will typically be < 4 KB (single QSO). The default asyncio receive buffer (65535 bytes) is sufficient. If datagrams exceed ~8 KB, IP fragmentation occurs — fragmented UDP datagrams can be silently dropped by intermediate routers. | ADIF QSO datagrams from WSJT-X / N1MM are small (< 1 KB typically). Not a concern in practice, but document the limit. |
| `datagram_received` is synchronous | LOW | `DatagramProtocol.datagram_received()` is a synchronous callback. You cannot `await` directly inside it. | Schedule async work with `asyncio.ensure_future()` or `asyncio.get_event_loop().create_task()`. The protocol handler parses the datagram synchronously, then dispatches an async coroutine for the DB write. |
| SO_REUSEADDR is set automatically | INFO | `create_datagram_endpoint()` sets `SO_REUSEADDR` before binding. This allows restart without "address already in use" errors. `SO_REUSEPORT` (multi-process load sharing) is not set and not needed here. | No action needed. |

---

## New Stack Additions

### Production Dependencies

**None.** The entire UDP listener is implemented with stdlib `asyncio`. No new packages are needed in `[project]` dependencies.

### Configuration Change (pydantic-settings)

Add one field to `app/config.py` — `Settings` already uses `pydantic_settings.BaseSettings`:

```python
udp_adif_port: int = 2237
```

This reads from `UDP_ADIF_PORT` environment variable automatically (pydantic-settings lowercases field names to find env vars). The default `2237` matches the WSJT-X / N1MM Logger+ convention.

### Dev/Test Dependencies

`pytest-asyncio` is already a dev dependency. No additions needed for testing the UDP protocol handler, because `DatagramProtocol` is a plain Python class that can be unit-tested by calling `datagram_received()` directly without binding a real socket.

---

## Integration Points

| Component | How It Integrates |
|-----------|------------------|
| `app/main.py` lifespan | `await loop.create_datagram_endpoint(...)` before the `yield`; `transport.close()` after the `yield`. Follows the existing watcher task pattern. |
| `app/config.py` `Settings` | Add `udp_adif_port: int = 2237`. Reads `UDP_ADIF_PORT` env var automatically. |
| `app/adif/parser.py` `parse_adi()` | Called synchronously inside `datagram_received()`. Pure function, no I/O, safe to call from a sync callback. |
| `app/qso/service.py` | `build_qso_dict()` and `find_duplicate()` are called inside an async task dispatched from `datagram_received()` via `asyncio.create_task()`. |
| Beanie / MongoDB | The async task dispatched by the protocol runs on the same event loop where Beanie's `AsyncMongoClient` was initialized. No additional wiring needed. |
| Auth (`app/auth/service.py`) | UDP is unauthenticated by design — source IP is the only identity signal. The operator callsign must come from configuration or from the ADIF record's `OPERATOR` field, not from a JWT. This is a feature design decision, not a stack limitation. |

---

## Docker Compose Changes

Add `/udp` port mapping to the `api` service in `docker-compose.yml`:

```yaml
services:
  api:
    ports:
      - "8000:8000"
      - "2237:2237/udp"    # UDP ADIF listener (WSJT-X / N1MM default port)
    environment:
      - UDP_ADIF_PORT=2237  # optional override
```

The `environment` entry for `UDP_ADIF_PORT` is optional (default is `2237`). Include it explicitly so the port mapping and the env var are visually co-located in the compose file — this prevents the port and the config from drifting apart.

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `asyncio-dgram` | Adds abstraction over `DatagramProtocol` that is useful for bidirectional or stream-style UDP. This is a receive-only listener — the callback model is a perfect fit and needs no wrapping. | `asyncio.DatagramProtocol` (stdlib) |
| `aiohttp` | HTTP framework / client. Its UDP support is internal (DNS). Wrong tool for a UDP socket server. | `asyncio.DatagramProtocol` (stdlib) |
| Separate worker process / threading | Would break the shared asyncio event loop requirement. Beanie's MongoDB connection is bound to the event loop — a separate thread/process cannot access it directly. | Single-process asyncio coroutine dispatched from `datagram_received()` |
| Motor (MongoDB async driver) | Already using Beanie 2.1+ which wraps Motor 3.x. Do not add Motor directly — Beanie is the correct ORM layer. | Beanie `QSO.insert()` |
| WebSockets | Unrelated to UDP. Different transport, different use case. | UDP socket |
| A separate UDP microservice | Adds deployment complexity, inter-process communication, and an additional auth surface. The existing asyncio event loop can handle this feature directly. | Lifespan-managed `DatagramProtocol` |
| `python-osc` | OSC-over-UDP library. ADIF datagrams are plain text, not OSC. | `asyncio.DatagramProtocol` + `parse_adi()` |
| `uvloop` (add separately) | Already in the venv (`uvloop-0.22.1`). No action needed. | Already present |

---

## Wire Format Notes (LOW Confidence — Verify Before Implementing)

The intended datagrams come from amateur radio logging software. The wire format affects parsing logic, not the stack choice — the stack (`DatagramProtocol` + `parse_adi()`) is the same regardless.

| Software | Default Port | Format | Notes |
|----------|-------------|--------|-------|
| WSJT-X "UDP Server" | 2237 | Binary QMessage protocol (not ADIF) — NOT raw ADIF text | WSJT-X sends structured binary messages. An "ADIF" log UDP message exists (type 12) but it wraps binary-encoded ADIF inside the protocol, not raw ADIF text. Requires separate deserialization before `parse_adi()`. |
| N1MM Logger+ UDP | 12060 | XML `<contactinfo>` — NOT ADIF | N1MM broadcasts XML, not ADIF. Requires XML parsing, not `parse_adi()`. |
| Ham Radio Deluxe "QSO Forwarding" | configurable | ADIF text over UDP | Sends raw ADIF text datagrams. `parse_adi()` works directly. |
| Custom / homebrew loggers | configurable | Varies | If the intent is a custom ADIF-over-UDP protocol (ollog as the receiver, user writes the sender), raw ADIF text is the correct design. `parse_adi()` works directly. |

**The phase plan should clarify which sending software is the target.** If the intent is WSJT-X, the binary protocol requires a separate decoder. If the intent is a custom/homebrew UDP sender or HRD-style raw ADIF text, `parse_adi()` works without modification. **This is a critical design decision that affects implementation scope, not stack selection.**

---

## Recommended `pyproject.toml` Change

```toml
# No changes to [project] dependencies — all new capability is stdlib.

# If integration tests for the UDP listener are added:
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",   # already present
    "httpx>=0.27",             # already present
]
```

No new production or dev dependencies.

---

## Sources

- [Python asyncio — Transports and Protocols (official docs, Python 3.14)](https://docs.python.org/3/library/asyncio-protocol.html) — `DatagramProtocol`, `create_datagram_endpoint()`, `error_received()`. HIGH confidence.
- [asyncio-dgram on PyPI](https://pypi.org/project/asyncio-dgram/) — v3.0.0, January 2026, Python >=3.9. MEDIUM confidence.
- [asyncio-dgram GitHub (jsbronder)](https://github.com/jsbronder/asyncio-dgram) — `bind()` / `connect()` API, active repository. MEDIUM confidence.
- [FastAPI Lifespan Events (official docs)](https://fastapi.tiangolo.com/advanced/events/) — `@asynccontextmanager` lifespan, `asyncio.create_task()` pattern. HIGH confidence.
- [Docker port publishing docs](https://docs.docker.com/engine/network/port-publishing/) — `/udp` suffix and long-syntax `protocol: udp`. HIGH confidence.
- [Python issue #81409 — UDP sockets and SO_REUSEADDR](https://github.com/python/cpython/issues/81409) — automatic SO_REUSEADDR behavior. MEDIUM confidence.
- [Python issue #23295 — Windows ProactorEventLoop UDP](https://bugs.python.org/issue23295) — confirmed no UDP on ProactorEventLoop. HIGH confidence (not relevant for Linux Docker).
- [uvloop GitHub — tests/test_udp.py](https://github.com/MagicStack/uvloop/blob/master/tests/test_udp.py) — UDP test coverage confirming `create_datagram_endpoint` support. MEDIUM confidence.
- [N1MM External UDP Broadcasts](https://n1mmwp.hamdocs.com/appendices/external-udp-broadcasts/) — N1MM sends XML, not ADIF, on port 12060. MEDIUM confidence (official N1MM docs).
- [WSJT-X User Guide 2.7.0](https://wsjt.sourceforge.io/wsjtx-doc/wsjtx-main-2.7.0.html) — UDP server protocol details, port 2237. MEDIUM confidence (official WSJT-X docs).

---

*Stack research for: UDP ADIF listener milestone (ollog)*
*Researched: 2026-04-05*
