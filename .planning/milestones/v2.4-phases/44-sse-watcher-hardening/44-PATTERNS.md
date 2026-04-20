# Phase 44: SSE Watcher Hardening - Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 4 (2 modified, 1 modified template, 1 new test)
**Analogs found:** 4 / 4

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/feed/manager.py` | service (background task) | event-driven | `app/udp/server.py` (`_handle_datagram`) | role-match: both are background pipeline processors with exception isolation |
| `app/main.py` | config / lifespan | request-response | `app/main.py` itself (backup_scheduler/backup_task pattern in same file) | exact: same file, identical lifespan lifecycle variable pattern |
| `templates/log/log.html` | template (JS state machine) | event-driven | `templates/log/log.html` itself (existing `htmx:sseMessage` handler) | exact: same file, extending the existing IIFE |
| `tests/test_watcher.py` | test | event-driven (mock) | `tests/test_udp_pipeline.py` | exact: same pattern — async unit tests, no live DB, AsyncMock + patch for internal async functions |

---

## Pattern Assignments

### `app/feed/manager.py` (service, event-driven)

**Analog:** `app/udp/server.py` — `_handle_datagram` uses the same structure: background async function that must not die on a single-event exception, with a try/except that logs and continues.

**Current state (lines 32-54) — the gap to fix:**

```python
while True:
    try:
        async with await collection.watch(pipeline, full_document="updateLookup") as stream:
            async for change in stream:
                doc = change.get("fullDocument", {})
                if doc:
                    ctx = {
                        "call": doc.get("CALL", ""),
                        "band": doc.get("BAND", ""),
                        "mode": doc.get("MODE", ""),
                        "freq": doc.get("FREQ", ""),
                        "operator": doc.get("_operator", ""),
                        "qso_date_utc": doc.get("qso_date_utc"),
                    }
                    # Render HTML partial — no Request object needed
                    html = templates.get_template("log/feed_row.html").render(ctx)
                    await mgr.broadcast(html)
    except PyMongoError as e:
        logger.warning("Change stream error, reconnecting: %s", e)
        await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Change stream watcher cancelled")
        break
    # BUG: any other exception (Jinja2, AttributeError, TypeError) escapes the while loop
```

**Exception isolation pattern to apply** (from RESEARCH.md Pattern 2):

- Move the `if doc:` guard to `if not doc: continue` (guard-and-continue style, matching the codebase's existing pattern in `_handle_datagram`).
- Wrap only the `templates.get_template(...).render(ctx)` + `await mgr.broadcast(html)` calls in a nested `try/except Exception`.
- Add `except asyncio.CancelledError: raise` before `except Exception` as defensive documentation (not mechanically required since `CancelledError` is a `BaseException`, not an `Exception`).
- On `except Exception`, `logger.error(...)` and `continue`. Watcher loop survives.

**Fixed inner-loop pattern:**

```python
async with await collection.watch(pipeline, full_document="updateLookup") as stream:
    async for change in stream:
        doc = change.get("fullDocument", {})
        if not doc:
            continue
        ctx = {
            "call": doc.get("CALL", ""),
            "band": doc.get("BAND", ""),
            "mode": doc.get("MODE", ""),
            "freq": doc.get("FREQ", ""),
            "operator": doc.get("_operator", ""),
            "qso_date_utc": doc.get("qso_date_utc"),
        }
        try:
            html = templates.get_template("log/feed_row.html").render(ctx)
            logger.debug("SSE broadcast call=%s operator=%s", ctx["call"], ctx["operator"])
            await mgr.broadcast(html)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("feed_row render/broadcast failed: %s", e)
            continue
```

**Outer except blocks** (lines 49-54) are NOT changed. `PyMongoError` and `CancelledError` handling at the `while True` level stays exactly as-is.

**No new imports needed.** `asyncio` is already imported (line 1). `logger` is already defined (line 6).

---

### `app/main.py` (lifespan config, strong-reference fix)

**Analog:** The `backup_scheduler` variable in the same file (lines 62-93). `backup_scheduler` is stored as a local variable in the lifespan and referenced in the shutdown section. The watcher fix follows the exact same local-variable-in-lifespan pattern — the only change is the storage target.

**Current state (lines 25-31 startup, lines 80-85 shutdown):**

```python
# Startup (line 25)
watcher_task = None
if client is not None:
    from app.feed.manager import manager as feed_manager, watch_qsos  # noqa: E402
    collection = client[settings.mongodb_db]["qsos"]
    watcher_task = asyncio.create_task(
        watch_qsos(collection, feed_manager, _templates)
    )

# Shutdown (lines 80-85)
if watcher_task is not None:
    watcher_task.cancel()
    try:
        await watcher_task
    except asyncio.CancelledError:
        pass
```

**Fixed pattern — two-site change:**

```python
# Startup: replace watcher_task = None with app.state.watcher_task = None
# and replace the create_task assignment target
app.state.watcher_task = None
if client is not None:
    from app.feed.manager import manager as feed_manager, watch_qsos  # noqa: E402
    collection = client[settings.mongodb_db]["qsos"]
    app.state.watcher_task = asyncio.create_task(
        watch_qsos(collection, feed_manager, _templates)
    )

# Shutdown: replace every reference to watcher_task with app.state.watcher_task
if app.state.watcher_task is not None:
    app.state.watcher_task.cancel()
    try:
        await app.state.watcher_task
    except asyncio.CancelledError:
        pass
```

**The local variable `watcher_task` is removed entirely.** No new imports needed. `app` is the `FastAPI` instance defined at line 97 — it is accessible in the lifespan because `lifespan` is a closure over the module scope where `app` is defined. Note: `app.state` is available on the FastAPI instance as a `State` object from the moment the `FastAPI(...)` call at line 97 runs. Since the lifespan generator runs after the `FastAPI` instance is created, `app.state` is always accessible inside `lifespan`.

---

### `templates/log/log.html` (template, LIVE indicator state machine)

**Analog:** The same file's existing `htmx:sseMessage` handler (lines 144-150). The fix extends the existing IIFE by adding two boolean state variables and reorganizing the `htmx:sseOpen` handler.

**Current IIFE (lines 114-152):**

```javascript
(function () {
    var indicator = document.getElementById('live-indicator');

    document.body.addEventListener('htmx:sseOpen', function (e) {
      if (e.detail.elt && e.detail.elt.id === 'log-table') {
        indicator.classList.remove('hidden');
        indicator.classList.add('flex');
        indicator.querySelector('span:last-child').textContent = 'LIVE';
        // BUG: sets green on bare connection open
        indicator.className = indicator.className
          .replace('bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-400', '')
          + ' bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400';
      }
    });

    document.body.addEventListener('htmx:sseError', function (e) {
      if (e.detail.elt && e.detail.elt.id === 'log-table') {
        indicator.classList.remove('hidden');
        indicator.classList.add('flex');
        indicator.querySelector('span:last-child').textContent = 'OFFLINE';
      }
    });

    document.body.addEventListener('htmx:sseClose', function (e) {
      if (e.detail.elt && e.detail.elt.id === 'log-table') {
        indicator.classList.add('hidden');
        indicator.classList.remove('flex');
      }
    });

    document.body.addEventListener('htmx:sseMessage', function (e) {
      if (!e.detail || !e.detail.elt || e.detail.elt.id !== 'log-table') return;
      if (e.detail.type !== 'new_qso') return;
      if (!document.getElementById('auto-refresh-ok')) return;
      if (document.querySelector('#log-table input')) return;
      htmx.ajax('GET', '/log/view', { target: '#log-table', swap: 'innerHTML' });
    });
  })();
```

**Fixed state machine pattern (complete IIFE replacement):**

```javascript
(function () {
    var indicator = document.getElementById('live-indicator');
    var eventsFlowing = false;  // true only after first new_qso message received

    document.body.addEventListener('htmx:sseOpen', function (e) {
      if (e.detail.elt && e.detail.elt.id === 'log-table') {
        // Connection opened — do NOT set green. Wait for first actual event.
        // NOTE: a dead watcher keeps the HTTP connection alive but sends no events.
      }
    });

    document.body.addEventListener('htmx:sseMessage', function (e) {
      if (!e.detail || !e.detail.elt || e.detail.elt.id !== 'log-table') return;
      // Only count named new_qso events — not SSE comments or other frames
      if (e.detail.type !== 'new_qso') return;
      // Set LIVE on first message (proves watcher is alive and sending)
      if (!eventsFlowing) {
        eventsFlowing = true;
        indicator.classList.remove('hidden');
        indicator.classList.add('flex');
        indicator.querySelector('span:last-child').textContent = 'LIVE';
        indicator.classList.remove('bg-rose-100', 'text-rose-700');
        indicator.classList.add('bg-emerald-100', 'dark:bg-emerald-900/40',
                                'text-emerald-700', 'dark:text-emerald-400');
      }
      // Auto-refresh guard: only swap when on page 1 with no active filters
      if (!document.getElementById('auto-refresh-ok')) return;
      if (document.querySelector('#log-table input')) return;
      htmx.ajax('GET', '/log/view', { target: '#log-table', swap: 'innerHTML' });
    });

    document.body.addEventListener('htmx:sseError', function (e) {
      if (e.detail.elt && e.detail.elt.id === 'log-table') {
        eventsFlowing = false;
        indicator.classList.remove('hidden');
        indicator.classList.add('flex');
        indicator.querySelector('span:last-child').textContent = 'OFFLINE';
      }
    });

    document.body.addEventListener('htmx:sseClose', function (e) {
      if (e.detail.elt && e.detail.elt.id === 'log-table') {
        eventsFlowing = false;
        indicator.classList.add('hidden');
        indicator.classList.remove('flex');
      }
    });
  })();
```

**Tailwind class note:** The dark-mode classes `dark:bg-emerald-900/40` and `dark:text-emerald-400` are already present as complete literal strings in the existing `log.html` file (line 20 of the HTML, inside the `live-indicator` span's initial class attribute). They do not need to be added to a new scanned location — they already appear in the template. Run `npm run verify` after the change to confirm.

**Key behavioral changes:**
- `htmx:sseOpen` handler body becomes a no-op comment (connection open no longer sets green).
- `htmx:sseMessage` gains the `eventsFlowing` sentinel and calls `setLive` logic inline before the existing auto-refresh guard.
- `htmx:sseError` and `htmx:sseClose` both reset `eventsFlowing = false`.
- `classList.remove()`/`classList.add()` replaces the string `replace()` manipulation to avoid stale class accumulation (RESEARCH.md Pitfall 4).

---

### `tests/test_watcher.py` (test, event-driven mock)

**Analog:** `tests/test_udp_pipeline.py` — exact match. Both test background async pipeline functions using `pytest.mark.asyncio`, `MagicMock`, `AsyncMock`, `patch`, no live MongoDB dependency.

**Imports pattern** (copy from `tests/test_udp_pipeline.py` lines 1-16):

```python
"""Unit tests for watch_qsos watcher hardening (Phase 44).

Tests LIVE-01a (exception isolation), LIVE-01b (app.state strong reference),
LIVE-01c (null qso_date_utc does not kill watcher).

No live MongoDB connection required — change stream is fully mocked.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.feed.manager import ConnectionManager, watch_qsos
```

**Async context manager mock pattern** — how to mock `async with await collection.watch(...)`:

The `watch()` call returns an object used as an async context manager AND an async iterator. The mock must satisfy:
1. `await collection.watch(...)` returns an object `X`
2. `async with X as stream` works (X is an async context manager)
3. `async for change in stream` yields the test change events

```python
def _make_mock_collection(changes: list[dict]):
    """Build a mock AsyncCollection whose watch() yields the given change dicts."""
    # The stream object must be an async context manager and async iterator
    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)

    # __aiter__ returns self; __anext__ pops from the changes list then raises StopAsyncIteration
    async def _anext_impl():
        if changes:
            return changes.pop(0)
        raise StopAsyncIteration

    mock_stream.__aiter__ = MagicMock(return_value=mock_stream)
    mock_stream.__anext__ = _anext_impl

    mock_collection = MagicMock()
    # watch() is async def — must be an AsyncMock so `await collection.watch(...)` works
    mock_collection.watch = AsyncMock(return_value=mock_stream)
    return mock_collection
```

**Core test structure for LIVE-01a (exception isolation):**

```python
@pytest.mark.asyncio
async def test_watcher_survives_render_exception():
    """LIVE-01a: render exception on change 1 does not kill watcher; change 2 broadcasts."""
    mgr = ConnectionManager()
    q = await mgr.connect()

    call_count = 0

    def _render_side_effect(ctx):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("simulated Jinja2 render error")
        return "<tr>ok</tr>"

    mock_template = MagicMock()
    mock_template.render.side_effect = _render_side_effect

    mock_templates = MagicMock()
    mock_templates.get_template.return_value = mock_template

    change1 = {"fullDocument": {"CALL": "W1AW", "BAND": "20M", "MODE": "FT8",
                                 "FREQ": "", "_operator": "VK2ABC", "qso_date_utc": None}}
    change2 = {"fullDocument": {"CALL": "VK2QQ", "BAND": "40M", "MODE": "SSB",
                                 "FREQ": "7.150", "_operator": "VK2ABC", "qso_date_utc": None}}

    collection = _make_mock_collection([change1, change2])

    # Cancel the watcher after it processes both changes
    task = asyncio.create_task(watch_qsos(collection, mgr, mock_templates))
    await asyncio.sleep(0)  # yield to let the task run
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert call_count == 2, "render() must be called for both changes"
    assert q.get_nowait() == "<tr>ok</tr>", "second change must broadcast successfully"
```

**Core test structure for LIVE-01b (app.state strong reference):**

```python
@pytest.mark.asyncio
async def test_watcher_task_stored_in_app_state():
    """LIVE-01b: after lifespan startup, app.state.watcher_task is an asyncio.Task."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    # Use httpx lifespan context to run startup/shutdown
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert hasattr(app.state, "watcher_task"), "app.state.watcher_task must exist after startup"
        # watcher_task may be None if MongoDB is unavailable in CI — that is acceptable
        if app.state.watcher_task is not None:
            assert isinstance(app.state.watcher_task, asyncio.Task)
```

**Core test structure for LIVE-01c (null qso_date_utc):**

```python
@pytest.mark.asyncio
async def test_watcher_null_date_does_not_kill():
    """LIVE-01c: qso_date_utc=None in a change doc does not propagate an exception."""
    mgr = ConnectionManager()
    q = await mgr.connect()

    mock_template = MagicMock()
    mock_template.render.return_value = "<tr>null-date-ok</tr>"
    mock_templates = MagicMock()
    mock_templates.get_template.return_value = mock_template

    change = {"fullDocument": {"CALL": "W1AW", "BAND": "20M", "MODE": "SSB",
                                "FREQ": "", "_operator": "VK2ABC", "qso_date_utc": None}}
    collection = _make_mock_collection([change])

    task = asyncio.create_task(watch_qsos(collection, mgr, mock_templates))
    await asyncio.sleep(0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert q.get_nowait() == "<tr>null-date-ok</tr>"
```

**File header pattern** (from `test_udp_pipeline.py` lines 1-11):

```python
"""Unit tests for ... (Phase N).

All tests are async, use pytest-asyncio, and mock ... so
no live database connection is required.
"""
from __future__ import annotations
```

**Decorator pattern:** `@pytest.mark.asyncio` on each async test function (no global asyncio_mode=auto — project uses per-test decoration as seen in all existing test files).

**Section separator pattern** (from `test_udp_pipeline.py`):

```python
# ---------------------------------------------------------------------------
# Section name
# ---------------------------------------------------------------------------
```

---

## Shared Patterns

### asyncio Task Lifecycle (Strong Reference)
**Source:** `app/main.py` lines 62-93 — `backup_scheduler` and `backup_task` local variables follow the same lifespan pattern. The fix mirrors this exact structure: initialize to `None` before the conditional, set inside the `if`, cancel/await in the shutdown block.
**Apply to:** `app/main.py` `watcher_task` → `app.state.watcher_task`.

### Exception-Swallowing Loop with `logger.error` + `continue`
**Source:** `tests/test_udp_pipeline.py` line 254 — `test_handle_datagram_exception_does_not_raise` tests the equivalent pattern: an internal exception must be caught and must not propagate. The test asserts "must not raise."
**Apply to:** `app/feed/manager.py` inner try/except in `watch_qsos`.

### `@pytest.mark.asyncio` per-test, no global mode
**Source:** All test files in `tests/` — `test_udp_pipeline.py`, `test_udp_token.py`, `test_stats.py`, etc. Every async test uses `@pytest.mark.asyncio` explicitly. No `asyncio_mode = "auto"` in `pyproject.toml`.
**Apply to:** `tests/test_watcher.py` — all three test functions.

### Mock patch target: module where name is resolved at call time
**Source:** `tests/test_udp_pipeline.py` lines 7-11 — patches target `app.qso.service.find_duplicate`, not `app.udp.server.find_duplicate`, because `_handle_datagram` resolves the name in the `app.qso.service` namespace.
**Apply to:** `tests/test_watcher.py` — patch `app.feed.manager` module-level names (e.g., `app.feed.manager.ConnectionManager`).

---

## No Analog Found

All four files have close analogs. No files lack a pattern match.

---

## Metadata

**Analog search scope:** `/Users/royco/ollog/app/`, `/Users/royco/ollog/tests/`, `/Users/royco/ollog/templates/log/`
**Files read directly:** `app/feed/manager.py`, `app/main.py`, `templates/log/log.html`, `tests/test_udp_pipeline.py`, `tests/test_udp_token.py`, `tests/conftest.py`
**Pattern extraction date:** 2026-04-16
