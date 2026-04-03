# Phase 5: Multi-Operator & Live Feed - Research

**Researched:** 2026-04-04
**Domain:** Concurrent write safety, operator isolation, SSE live feed with FastAPI + pymongo async + HTMX
**Confidence:** HIGH (SSE, HTMX SSE extension, FastAPI native SSE, concurrent writes), MEDIUM (change stream architecture alternatives)

---

## Summary

Phase 5 has three distinct sub-problems: (1) proving concurrent writes don't produce lost QSOs or incorrect attribution, (2) systematically verifying every QSO endpoint injects callsign from JWT, never from the request, and (3) broadcasting new QSOs to all connected operators in near-real-time without page refresh.

The stack already has everything needed for problems 1 and 2. For problem 1, the compound index on `{_operator, CALL, qso_date_utc, BAND, MODE}` was made non-unique in phase 03-02 by design — duplicate enforcement is app-level. Under concurrent load, two simultaneous inserts of the same QSO can both succeed if the duplicate-detection query runs concurrently before either insert completes. This is a known race and the plan must decide: add a sparse unique index back (safe if the non-unique decision was for import flexibility rather than correctness), or document the race window as acceptable. For problem 2, `app.routes` introspection gives a pytest-friendly way to enumerate all routes and assert callsign injection. For problem 3, a critical infrastructure constraint exists: **the current Docker Compose runs MongoDB standalone, which does not support change streams.** The Compose file must be updated to a single-node replica set before change streams can be used.

The preferred live-feed approach for this stack (HTMX frontend, no npm, FastAPI 0.135+) is **SSE over WebSockets**: SSE is unidirectional (server-to-client, which is all this feature needs), works over standard HTTP/1.1 and through proxies, requires no client-side WebSocket manager, and HTMX 2.x has a first-class SSE extension (`htmx-ext-sse@2.2.4`) that handles DOM injection via `sse-connect`/`sse-swap` attributes. FastAPI 0.135.0 ships native SSE with `from fastapi.sse import EventSourceResponse, ServerSentEvent` — `sse-starlette` is not needed.

**Primary recommendation:** Use FastAPI native SSE (`EventSourceResponse`) + per-client `asyncio.Queue` broadcast manager + pymongo change stream watching the `qsos` collection (after updating Docker Compose to a single-node replica set). Authenticate the SSE endpoint via cookie JWT. Broadcast only INSERT change events, not updates or deletes. Include `_operator` in the broadcast payload so the HTMX template can display attribution.

---

## Standard Stack

### Core (already in pyproject.toml — no new installs required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi[standard] | >=0.135.0 | Native SSE via `fastapi.sse` module | Already pinned; `EventSourceResponse` + `ServerSentEvent` added in 0.135.0 |
| pymongo | >=4.16.0 | `AsyncCollection.watch()` change streams | Already pinned; async change stream API stable since 4.9 |
| beanie | >=2.1.0 | ODM for QSO documents | Already in use; no changes needed for this phase |

### Frontend (CDN additions to base.html)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|-------------|
| htmx-ext-sse | 2.2.4 | SSE extension for HTMX 2.x | Official HTMX extension; replaces removed hx-sse attribute from 1.x |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastAPI native SSE | sse-starlette 3.3.4 | sse-starlette provides more configuration options; native SSE is simpler and already included |
| SSE | WebSockets (FastAPI `websockets`) | WebSockets are bidirectional; unnecessary complexity for broadcast-only; harder HTMX integration |
| SSE | Long polling | Long polling wastes connections; SSE is the correct HTTP primitive for this use case |
| pymongo change stream | In-process event after insert | Change stream is infrastructure-level and catches writes from all sources (e.g. import); in-process approach misses ADIF imports |

**Installation — no new Python packages needed.** Only a CDN script tag in `base.html` or the log template:

```html
<!-- Add after htmx script tag in base.html -->
<script src="https://cdn.jsdelivr.net/npm/htmx-ext-sse@2.2.4/dist/sse.js"></script>
```

---

## Architecture Patterns

### Recommended Project Structure Addition

```
app/
├── feed/
│   ├── __init__.py
│   ├── router.py        # GET /feed/station — SSE endpoint, cookie auth
│   └── manager.py       # ConnectionManager: asyncio.Queue set + broadcast
templates/
└── log/
    └── feed.html        # SSE container partial (hx-ext="sse" div)
```

---

### Pattern 1: FastAPI Native SSE with ConnectionManager

**What:** Each SSE client gets its own `asyncio.Queue`. The `ConnectionManager` holds a set of active queues and has a `broadcast()` method. The SSE generator yields from its queue in a `try/finally` to ensure cleanup.

**When to use:** Always for this feature — single writer (change stream task), multiple readers (browser tabs).

```python
# Source: https://fastapi.tiangolo.com/tutorial/server-sent-events/
import asyncio
from collections.abc import AsyncIterable
from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent
from app.auth.dependencies import get_current_operator_callsign_cookie

class ConnectionManager:
    def __init__(self):
        self._queues: set[asyncio.Queue] = set()

    async def connect(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.add(q)
        return q

    def disconnect(self, q: asyncio.Queue) -> None:
        self._queues.discard(q)

    async def broadcast(self, event: dict) -> None:
        for q in set(self._queues):  # snapshot to avoid mutation during iteration
            await q.put(event)

manager = ConnectionManager()

router = APIRouter(prefix="/feed", tags=["feed"])

@router.get("/station", response_class=EventSourceResponse)
async def station_feed(
    _callsign: str = Depends(get_current_operator_callsign_cookie),
) -> AsyncIterable[ServerSentEvent]:
    q = await manager.connect()
    try:
        while True:
            event = await q.get()
            yield ServerSentEvent(
                data=event,
                event="new_qso",
            )
    finally:
        manager.disconnect(q)
```

**Key:** The `finally` block runs on `asyncio.CancelledError` (client disconnect), so queues are always cleaned up. FastAPI's `EventSourceResponse` automatically sends keep-alive pings every 15 seconds and sets `X-Accel-Buffering: no` to prevent nginx buffering.

---

### Pattern 2: pymongo Async Change Stream — INSERT watcher

**What:** A long-running background task (started in the FastAPI lifespan) watches the `qsos` collection for inserts using `AsyncCollection.watch()`. On each insert, it calls `manager.broadcast()`.

**When to use:** The change stream is the canonical way to react to writes from any source (UI form submit, ADIF import, direct DB write). An in-process hook after `qso.insert()` would miss ADIF bulk imports.

**Requires:** MongoDB replica set (oplog must be enabled). Single-node replica set is sufficient for development and self-hosted production.

```python
# Source: https://pymongo.readthedocs.io/en/stable/api/pymongo/asynchronous/change_stream.html
import asyncio
from pymongo.errors import PyMongoError

async def watch_qsos(collection, manager: ConnectionManager) -> None:
    pipeline = [{"$match": {"operationType": "insert"}}]
    while True:  # reconnect loop
        try:
            async with await collection.watch(pipeline) as stream:
                async for change in stream:
                    doc = change.get("fullDocument", {})
                    event = {
                        "call": doc.get("CALL"),
                        "band": doc.get("BAND"),
                        "mode": doc.get("MODE"),
                        "operator": doc.get("_operator"),
                        "qso_date_utc": str(doc.get("qso_date_utc", "")),
                    }
                    await manager.broadcast(event)
        except PyMongoError:
            await asyncio.sleep(1)  # brief backoff before reconnect
```

Note: `try_next()` (non-blocking poll) is an alternative to `async for`, but `async for` with the reconnect loop is cleaner for a background task that should run for the lifetime of the app.

---

### Pattern 3: Docker Compose Single-Node Replica Set

**What:** MongoDB must run in replica set mode for change streams. A single-node replica set is self-contained and sufficient; no extra nodes needed.

**Critical constraint:** The current `docker-compose.yml` runs `image: mongo:7` without `--replSet`. This must be updated.

```yaml
# Source: https://anthonysimmon.com/the-only-local-mongodb-replica-set-with-docker-compose-guide-youll-ever-need/
services:
  mongodb:
    image: mongo:7
    command: ["--replSet", "rs0", "--bind_ip_all", "--port", "27017"]
    ports:
      - "27017:27017"
    healthcheck:
      test: >
        echo "try { rs.status() } catch (err) {
          rs.initiate({_id:'rs0', members:[{_id:0, host:'mongodb:27017'}]})
        }" | mongosh --port 27017 --quiet
      interval: 5s
      timeout: 30s
      start_period: 0s
      retries: 30
    volumes:
      - mongo-data:/data/db
```

The healthcheck doubles as the replica set initiator — it runs `rs.status()` and, if it fails (not yet initiated), falls back to `rs.initiate()`. This is idempotent and self-healing.

The `MONGODB_URI` environment variable must include `?replicaSet=rs0`:
```
MONGODB_URI=mongodb://mongodb:27017/?replicaSet=rs0
```

---

### Pattern 4: HTMX SSE Subscription in HTML

**What:** The HTMX SSE extension connects to the `/feed/station` endpoint and swaps received HTML partials into the DOM. No JavaScript beyond loading the extension.

```html
<!-- Source: https://htmx.org/extensions/sse/ — version 2.2.4 -->
<!-- In base.html or log/form.html, load the extension -->
<script src="https://cdn.jsdelivr.net/npm/htmx-ext-sse@2.2.4/dist/sse.js"></script>

<!-- In the form page or a shared station feed section -->
<div hx-ext="sse" sse-connect="/feed/station">
  <div id="station-feed"
       sse-swap="new_qso"
       hx-swap="afterbegin">
    <!-- New QSO rows prepended here as they arrive -->
  </div>
</div>
```

The `sse-swap="new_qso"` listens for SSE events named `new_qso`. The `hx-swap="afterbegin"` prepends each new row to the top of `#station-feed`. The server yields `ServerSentEvent(data=rendered_html, event="new_qso")` where `rendered_html` is a Jinja2-rendered row partial.

**Key detail:** The SSE endpoint must render HTML (a QSO row partial), not raw JSON, to avoid any client-side JavaScript. The change stream handler must call `templates.render("log/qso_row.html", {...})` — which is synchronous and can be called outside request context — or use `Jinja2Templates` directly.

---

### Pattern 5: Operator Isolation Audit via Route Introspection

**What:** Enumerate all FastAPI routes using `app.routes` and check that every route protecting QSO data includes `get_current_operator_callsign` or `get_current_operator_callsign_cookie` in its dependency tree.

**When to use:** Plan 05-02 — systematic proof that no endpoint accepts operator identity from anything other than JWT.

```python
# Source: FastAPI routing system docs — app.routes introspection
from fastapi.routing import APIRoute
from fastapi.dependencies.utils import get_dependant, get_flat_dependant

def collect_dependency_names(route: APIRoute) -> set[str]:
    """Return the set of callable names in the flat dependency tree for a route."""
    dependant = get_dependant(path=route.path, call=route.endpoint)
    flat = get_flat_dependant(dependant)
    names = set()
    for dep in flat.dependencies:
        names.add(dep.call.__name__)
    return names

# In a pytest test:
def test_all_qso_routes_inject_callsign_from_jwt(app):
    CALLSIGN_DEPS = {
        "get_current_operator_callsign",
        "get_current_operator_callsign_cookie",
    }
    QSO_PATH_PREFIXES = ("/api/qsos", "/log/qsos", "/log/view", "/log/import", "/log/export")
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not any(route.path.startswith(p) for p in QSO_PATH_PREFIXES):
            continue
        dep_names = collect_dependency_names(route)
        assert dep_names & CALLSIGN_DEPS, (
            f"Route {route.methods} {route.path} has no callsign injection dependency"
        )
```

This test will also catch any new endpoint added in the future that forgets the dependency.

---

### Anti-Patterns to Avoid

- **Calling `asyncio.Queue.put_nowait()` in `broadcast()`:** If any queue is full (bounded), `put_nowait` raises `QueueFull`. Use `await q.put(event)` or catch the exception. For broadcast, use unbounded queues (default `asyncio.Queue()`) or bounded with discard-on-full.
- **Starting the change stream watcher with `asyncio.create_task()` after `init_db()`:** The task must be cancelled cleanly on shutdown. Store the task in the lifespan and cancel it in the `finally` block.
- **Rendering Jinja2 HTML inside the change stream coroutine without a `Request` object:** `Jinja2Templates.TemplateResponse` requires a `Request`. Use `templates.get_template("log/qso_feed_row.html").render(ctx)` instead (no `Request` required).
- **Passing JSON to HTMX SSE swap target:** HTMX SSE extension directly injects the `data` field as HTML. The server must yield rendered HTML, not JSON, when using `sse-swap`.
- **Not scoping the SSE feed:** The station feed is shared — all operators see all new QSOs (by design per requirements). But the feed endpoint itself still requires auth to prevent unauthenticated connections.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE keep-alive pings | Custom ping loop | FastAPI native `EventSourceResponse` | Already built in (15s interval), also sets correct headers |
| SSE proxy buffering headers | Manual header dict | FastAPI native `EventSourceResponse` | Automatically sets `X-Accel-Buffering: no` and `Cache-Control: no-cache` |
| HTMX SSE DOM injection | Custom `EventSource` JS | `htmx-ext-sse@2.2.4` | No-JS solution consistent with existing HTMX-only frontend |
| Change stream reconnect on error | Custom retry logic | Reconnect loop wrapping `watch()` | `PyMongoError` on stream death; simple `while True` + sleep backoff is correct pattern |
| Operator isolation test | Manual code review | `app.routes` introspection + pytest | Catches future regressions automatically |

**Key insight:** The hardest part of this phase is infrastructure (single-node replica set Docker Compose), not code. The application-level code is straightforward once the DB is in replica set mode.

---

## Common Pitfalls

### Pitfall 1: Change Streams Silently Fail on Standalone MongoDB

**What goes wrong:** `collection.watch()` raises `OperationFailure: The $changeStream stage is only supported on replica sets` immediately. The background task crashes with no visible error in the HTTP layer.

**Why it happens:** Change streams read from the oplog, which only exists on replica set members. A standalone `mongod` has no oplog.

**How to avoid:** Update `docker-compose.yml` to add `--replSet rs0` to the MongoDB command and add the healthcheck-based `rs.initiate()` pattern. Update `MONGODB_URI` to include `?replicaSet=rs0`. Validate with a startup check in the lifespan: `await client.admin.command("replSetGetStatus")`.

**Warning signs:** The SSE feed endpoint connects but never pushes any events; no errors visible in the browser.

---

### Pitfall 2: SSE Extension Not Loaded in Page

**What goes wrong:** The `sse-connect` attribute silently does nothing. HTMX does not warn about unknown extensions.

**Why it happens:** In HTMX 2.x, the old `hx-sse` attribute was removed and replaced by the external `htmx-ext-sse` extension, which must be loaded as a separate `<script>` tag. If only `htmx.org@2.0.4` is loaded (the current `base.html`), SSE is not available.

**How to avoid:** Add `<script src="https://cdn.jsdelivr.net/npm/htmx-ext-sse@2.2.4/dist/sse.js"></script>` after the main HTMX script. Use `hx-ext="sse"` on the container element, `sse-connect="/feed/station"` to specify the stream URL, and `sse-swap="new_qso"` on the target element to listen for the named event.

**Warning signs:** Browser DevTools Network tab shows no connection to `/feed/station`.

---

### Pitfall 3: Change Stream Watcher Task Leaks on Shutdown

**What goes wrong:** The watcher coroutine runs forever; on server shutdown uvicorn's lifespan teardown hangs waiting for it to finish.

**Why it happens:** `asyncio.create_task()` creates a fire-and-forget task. If the task's `while True` loop doesn't check for cancellation, the `CancelledError` propagates through the `async with watch()` context manager, which is correct — but only if the task was actually cancelled.

**How to avoid:** Store the watcher task in the lifespan and cancel it explicitly:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _bootstrap_admin()
    # Start change stream watcher
    collection = get_client()[settings.mongodb_db]["qsos"]
    watcher_task = asyncio.create_task(
        watch_qsos(collection, manager)
    )
    yield
    watcher_task.cancel()
    try:
        await watcher_task
    except asyncio.CancelledError:
        pass
    await close_db()
```

**Warning signs:** `uvicorn` takes more than a few seconds to shut down; Docker `stop` hangs.

---

### Pitfall 4: Concurrent Insert Race Window in Duplicate Detection

**What goes wrong:** Two operators (or two concurrent browser submissions from one operator) POST the same QSO at nearly the same time. Both `find_duplicate()` calls return `None` because neither insert has committed yet. Both inserts succeed and two identical QSOs appear in the log.

**Why it happens:** The compound index on `{_operator, CALL, qso_date_utc, BAND, MODE}` is non-unique (unique=True was dropped in phase 03-02). The `find_duplicate()` + `insert()` sequence is not atomic.

**How to avoid:** This phase (05-01) must explicitly decide the policy:
- **Option A (recommended):** The race window is for identical-operator QSOs only (same operator submitting the same QSO twice within milliseconds). Accept this as tolerable; the multi-operator test (two different operators) is unaffected because `_operator` is part of the compound index key — two different operators logging the same callsign/band/mode/time are never duplicates of each other.
- **Option B:** Re-add a sparse unique index `{_operator, CALL, qso_date_utc, BAND, MODE}` with `unique=True`. Catch `DuplicateKeyError` at the insert site and surface it as a 409. This is the correct fix if same-operator race is a real concern.

**Warning signs:** Integration test with `asyncio.gather()` running two simultaneous POST requests with identical payloads produces two documents instead of one.

---

### Pitfall 5: Jinja2 Rendering Inside Change Stream Task Requires No `Request` Object

**What goes wrong:** `templates.TemplateResponse(request, "template.html", ctx)` is called inside the change stream watcher, but there is no HTTP request in scope. This raises `AttributeError` or `TypeError`.

**Why it happens:** `Jinja2Templates.TemplateResponse` in FastAPI requires a `Request` parameter.

**How to avoid:** Use `templates.get_template("log/qso_feed_row.html").render(ctx)` which returns a plain string. This method requires no `Request` and can be called from any async context.

---

### Pitfall 6: SSE auth with Bearer Token (API) vs Cookie (UI)

**What goes wrong:** The SSE endpoint is mounted under `/feed/` and uses cookie auth. Browser `EventSource` API (used by htmx-ext-sse) does not support custom headers — it cannot send a `Bearer` token. Only cookies work for browser-native EventSource.

**Why it happens:** The `EventSource` API in browsers only supports GET requests with cookies for auth; no way to set `Authorization` header.

**How to avoid:** SSE live-feed endpoints for HTMX browser use must use `get_current_operator_callsign_cookie`, not `get_current_operator_callsign`. The REST API variant (if added) would use Bearer auth but is not needed here.

---

## Code Examples

Verified patterns from official sources:

### FastAPI Native SSE — Basic Setup

```python
# Source: https://fastapi.tiangolo.com/tutorial/server-sent-events/
# FastAPI 0.135.0+
from collections.abc import AsyncIterable
from fastapi.sse import EventSourceResponse, ServerSentEvent

@router.get("/station", response_class=EventSourceResponse)
async def station_feed() -> AsyncIterable[ServerSentEvent]:
    q = await manager.connect()
    try:
        while True:
            event = await q.get()
            yield ServerSentEvent(data=event, event="new_qso")
    finally:
        manager.disconnect(q)
```

### pymongo Async Change Stream — Collection Watch

```python
# Source: https://pymongo.readthedocs.io/en/stable/api/pymongo/asynchronous/change_stream.html
pipeline = [{"$match": {"operationType": "insert"}}]
async with await collection.watch(pipeline) as stream:
    async for change in stream:
        full_doc = change.get("fullDocument", {})
        # ... process insert
```

### HTMX SSE Extension — HTML

```html
<!-- Source: https://htmx.org/extensions/sse/ — htmx-ext-sse 2.2.4 -->
<script src="https://cdn.jsdelivr.net/npm/htmx-ext-sse@2.2.4/dist/sse.js"></script>

<div hx-ext="sse" sse-connect="/feed/station">
  <div id="station-feed" sse-swap="new_qso" hx-swap="afterbegin"></div>
</div>
```

### Docker Compose Single-Node Replica Set

```yaml
# Source: https://anthonysimmon.com/the-only-local-mongodb-replica-set-with-docker-compose-guide-youll-ever-need/
services:
  mongodb:
    image: mongo:7
    command: ["--replSet", "rs0", "--bind_ip_all", "--port", "27017"]
    healthcheck:
      test: >
        echo "try { rs.status() } catch (err) {
          rs.initiate({_id:'rs0',members:[{_id:0,host:'mongodb:27017'}]})
        }" | mongosh --port 27017 --quiet
      interval: 5s
      timeout: 30s
      retries: 30
```

### Operator Isolation pytest Introspection

```python
# Source: FastAPI routing system — app.routes
from fastapi.routing import APIRoute

def test_qso_routes_require_callsign_dep(app):
    CALLSIGN_DEPS = {"get_current_operator_callsign", "get_current_operator_callsign_cookie"}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not (route.path.startswith("/api/qsos") or route.path.startswith("/log/")):
            continue
        # Collect direct dependency names from route endpoint
        import inspect
        sig = inspect.signature(route.endpoint)
        dep_names = {
            param.default.dependency.__name__
            for param in sig.parameters.values()
            if hasattr(param.default, "dependency")
            and hasattr(param.default.dependency, "__name__")
        }
        assert dep_names & CALLSIGN_DEPS, f"Route {route.path} missing callsign dep"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hx-sse` (HTMX 1.x built-in) | `htmx-ext-sse` extension (external) | HTMX 2.0.0 (June 2024) | Must load separate script; attribute syntax changed |
| `sse-starlette` (third-party) | `fastapi.sse.EventSourceResponse` (built-in) | FastAPI 0.135.0 (2025) | No extra package; Pydantic-native serialization |
| Motor (async MongoDB) | pymongo AsyncMongoClient | Motor EOL May 2025; pymongo 4.9+ | Motor must not be installed; use `pymongo.asynchronous` directly |
| `hx-sse="connect:/url"` (v1 syntax) | `sse-connect="/url"` (v2 syntax) | htmx-ext-sse 2.x | Syntax migration required if copying old examples |

**Deprecated/outdated:**
- `hx-sse` attribute: removed in HTMX 2.0; do not use any examples showing `hx-sse=`
- `sse-starlette.ServerSentEvent`: still works but unnecessary since FastAPI 0.135
- Motor: EOL May 2025; already not installed in this project

---

## Open Questions

1. **Concurrent insert race (plan 05-01): accept or fix?**
   - What we know: The unique index was intentionally dropped in phase 03-02; duplicate enforcement is app-level; the race window exists when the same operator submits the same QSO twice concurrently
   - What's unclear: Was the unique index dropped to allow ADIF import flexibility (different operators importing the same contact), or was it dropped for a different reason? A `sparse` unique index on `{_operator, CALL, qso_date_utc, BAND, MODE}` would solve the race while still allowing different operators to log the same contact
   - Recommendation: Plan 05-01 should document the race, characterize it as acceptable (sub-millisecond window, same-operator only), and verify via test that two different operators can log the same contact without conflict

2. **SSE feed scope: all QSOs vs station-only**
   - What we know: Requirements say "shared station feed" — all operators see new QSOs from all operators
   - What's unclear: Should soft-deleted QSOs trigger a feed event to remove the row from watchers' views? Deletes and updates are not INSERT events
   - Recommendation: Plan 05-03 scope is INSERT-only; deletions and edits are out of scope for the live feed

3. **Test environment and change streams: mongomock incompatibility**
   - What we know: `mongomock` does not support change streams (oplog-based feature); existing tests use mongomock or real MongoDB
   - What's unclear: Do the existing tests use mongomock or a test MongoDB instance?
   - Recommendation: The change stream watcher should be tested with a real MongoDB replica set in integration tests, not mongomock; unit tests can mock the `watch()` call

---

## Sources

### Primary (HIGH confidence)
- `https://fastapi.tiangolo.com/tutorial/server-sent-events/` — FastAPI native SSE tutorial; `EventSourceResponse`, `ServerSentEvent`, `asyncio.Queue` ConnectionManager pattern; version 0.135.0 confirmed
- `https://htmx.org/extensions/sse/` — htmx-ext-sse 2.2.4 official docs; `sse-connect`, `sse-swap`, `hx-ext="sse"` attributes; CDN URL confirmed
- `https://pymongo.readthedocs.io/en/stable/api/pymongo/asynchronous/change_stream.html` — pymongo AsyncChangeStream API; `watch()`, `try_next()`, pipeline filtering, resume tokens; pypi.org version 4.16.0
- `https://anthonysimmon.com/the-only-local-mongodb-replica-set-with-docker-compose-guide-youll-ever-need/` — Single-node replica set Docker Compose pattern; exact healthcheck command for self-initiating rs0

### Secondary (MEDIUM confidence)
- `https://deepwiki.com/sysid/sse-starlette/4.2-multiple-consumers` — Multiple consumers broadcast pattern; per-client Queue, set management, disconnect cleanup
- `https://blog.greeden.me/en/2025/10/28/weaponizing-real-time-websocket-sse-notifications-with-fastapi-connection-management-rooms-reconnection-scale-out-and-observability/` — SSE vs WebSocket for broadcast workload; bounded queue backpressure; proxy buffering pitfall

### Tertiary (LOW confidence — needs validation)
- Multiple community sources confirming `mongomock` does not support change streams; needs verification against current mongomock-motor version before finalizing test strategy

---

## Metadata

**Confidence breakdown:**
- Standard stack (SSE, HTMX ext, pymongo change stream): HIGH — verified against official docs and FastAPI release notes
- Architecture (ConnectionManager, broadcast pattern, Docker Compose replica set): HIGH — patterns from official FastAPI SSE tutorial and verified Docker Compose guide
- Concurrent write safety: MEDIUM — MongoDB atomicity at single-document level is documented; specific behavior of app-level duplicate check under concurrent load is reasoned from first principles, not a tested claim
- Operator isolation audit via introspection: MEDIUM — `app.routes` is public API; `get_dependant`/`get_flat_dependant` are internal FastAPI utils that may change; simpler signature inspection approach provided as fallback

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable libraries; FastAPI SSE API unlikely to change within 30 days)
