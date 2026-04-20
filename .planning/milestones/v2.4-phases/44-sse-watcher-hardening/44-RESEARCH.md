# Phase 44: SSE Watcher Hardening - Research

**Researched:** 2026-04-16
**Domain:** Python asyncio task lifecycle, pymongo AsyncCollection.watch(), FastAPI SSE, HTMX live indicator JavaScript
**Confidence:** HIGH

---

## Summary

Phase 44 is a targeted bug fix with two tightly-coupled parts: (1) harden the Python-side `watch_qsos` asyncio task in `app/feed/manager.py` so it cannot be killed by an unhandled exception or silently GC'd, and (2) fix the client-side LIVE indicator in `templates/log/log.html` so it turns green only after at least one SSE event has been received rather than on bare SSE connection open.

The root cause of both bugs is already confirmed by the milestone research. The watcher task is currently stored only in a local variable in the lifespan function (`watcher_task = asyncio.create_task(...)`); Python 3.12+ may GC it, and any unhandled exception inside the `async for change in stream:` body (e.g., a Jinja2 render failure from a QSO document with a null `qso_date_utc`) kills the task permanently with no restart. On the client side, the current `htmx:sseOpen` handler immediately sets the indicator green when the HTTP SSE connection opens — before any event has ever flowed — so a dead watcher is invisible to the operator.

Both fixes are code-only changes to two existing files. No new files, no new Python packages, no new npm packages.

**Primary recommendation:** Fix `app/feed/manager.py` first (strong reference + exception isolation); fix `templates/log/log.html` LIVE indicator second. These are independent changes that can land in one commit or two.

---

## Project Constraints (from CLAUDE.md)

- **No new Python packages** — `requirements.txt` and `pyproject.toml` must not change for v2.4.
- **No new JS dependencies** — no npm installs.
- **FOUC prevention** — the inline IIFE in `base.html` `<head>` is load-bearing. Never move it or add `defer`/`async`.
- **Tailwind purge** — new `dark:` classes must appear as complete literal strings in scanned template files. Run `npm run build` + grep verification for any new classes.
- **apscheduler `<4` upper bound is load-bearing** — do not touch `pyproject.toml` APScheduler constraints.
- **FastAPI sub-app StaticFiles** — every sub-app that serves HTML needs its own `/static` mount. Not relevant here, but carry-forward rule.
- **Test command:** `uv run pytest tests/` (requires MongoDB on localhost:27017).

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIVE-01 | UDP-inserted QSOs trigger the SSE live table refresh — the `watch_qsos` watcher task is hardened against unhandled exceptions and Python 3.12+ GC (strong reference stored in `app.state`) | Confirmed by codebase inspection: watcher task currently in a local variable; strong reference to `app.state.watcher_task` is the fix. Exception isolation needs `try/except Exception` around the render call with `continue`. |
| LIVE-02 | The LIVE/OFFLINE indicator stays accurate — green only when events are actually flowing, not just when the SSE HTTP connection is open | Confirmed by JS inspection: current code sets green on `htmx:sseOpen` (connection open), not on first message received. Fix: move green-state trigger to `htmx:sseMessage` handler. |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Change stream watcher restart on exception | API/Backend (`manager.py`) | — | Exception handling is server-side; client has no visibility |
| Strong task reference / GC prevention | API/Backend (`main.py` + `app.state`) | — | asyncio task lifecycle is entirely server-side |
| LIVE indicator state machine | Browser/Client (`log.html` JS) | — | Indicator is pure client-side DOM manipulation driven by SSE events |
| SSE event delivery | API/Backend (`feed/router.py`) | Browser/Client (EventSource) | Server pushes; client receives. Watcher death only affects server side |

---

## Standard Stack

### Core (all already installed — no changes)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pymongo (async) | 4.16.0 [VERIFIED: pyproject.toml + .venv] | AsyncCollection.watch() for change streams | Official MongoDB async driver, used throughout codebase |
| FastAPI | >=0.135.0 [VERIFIED: pyproject.toml] | `app.state` for storing strong task reference | Built-in application state dict on FastAPI instance |
| asyncio | stdlib | `create_task()`, `CancelledError` handling | Python stdlib |
| htmx-ext-sse | 2.2.4 [ASSUMED — version from prior milestone research] | `htmx:sseOpen`, `htmx:sseMessage`, `htmx:sseError`, `htmx:sseClose` events | Already in use; not changing |

### No Supporting Libraries Needed

All changes are within existing infrastructure. No new installs.

---

## Architecture Patterns

### System Architecture Diagram

```
MongoDB oplog write (any insert path: REST, UI form, UDP)
  |
  v
change stream fires in watch_qsos()      [app/feed/manager.py]
  |
  +-- [CURRENTLY] unhandled Jinja2 exception kills watcher permanently
  |      Fix: try/except Exception around render call + continue
  |
  +-- [CURRENTLY] task has no strong reference -- GC risk on Python 3.12+
  |      Fix: app.state.watcher_task = asyncio.create_task(...)
  |
  v
mgr.broadcast(html)                      [ConnectionManager.broadcast()]
  |
  v
all connected queues receive html string
  |
  v
station_feed() yields ServerSentEvent    [app/feed/router.py]
  event="new_qso", data=<rendered HTML>
  |
  v
browser EventSource receives event
  |
  +-- htmx:sseMessage fires               [log.html inline script]
  |     [CURRENTLY] LIVE indicator set green on htmx:sseOpen (too early)
  |     Fix: set green only on first htmx:sseMessage from #log-table
  |
  v
htmx:sseMessage handler checks:
  - e.detail.elt.id === 'log-table'
  - e.detail.type === 'new_qso'
  - #auto-refresh-ok sentinel present (page 1, no filters)
  - no input in #log-table (not in edit mode)
  |
  v
htmx.ajax('GET', '/log/view', {target:'#log-table', swap:'innerHTML'})
  |
  v
log_view() re-renders fresh page 1 data
```

### Recommended Project Structure

No new files. Changes are confined to:

```
app/
└── feed/
    └── manager.py       # watch_qsos: exception isolation + app.state strong reference
app/
└── main.py              # lifespan: store watcher_task in app.state
templates/
└── log/
    └── log.html         # LIVE indicator: trigger on message, not connection open
tests/
└── test_watcher.py      # NEW: unit tests for LIVE-01 and LIVE-02
```

### Pattern 1: asyncio Task Strong Reference via app.state

**What:** Store the watcher task in `app.state` to prevent Python 3.12+ GC from silently collecting it.

**When to use:** Any `asyncio.create_task()` call that must live for the duration of the application.

**Current code in `main.py` (lines 25-31):**
```python
watcher_task = None          # <- local variable only, GC risk
if client is not None:
    from app.feed.manager import manager as feed_manager, watch_qsos
    collection = client[settings.mongodb_db]["qsos"]
    watcher_task = asyncio.create_task(
        watch_qsos(collection, feed_manager, _templates)
    )
```

**Fixed pattern:**
```python
# Source: STATE.md v2.4 Architecture Decisions
app.state.watcher_task = None
if client is not None:
    from app.feed.manager import manager as feed_manager, watch_qsos
    collection = client[settings.mongodb_db]["qsos"]
    app.state.watcher_task = asyncio.create_task(
        watch_qsos(collection, feed_manager, _templates)
    )
```

The shutdown path already references `watcher_task` as a local variable and calls `.cancel()` + `await`. After the fix, it must reference `app.state.watcher_task` instead. The local variable `watcher_task` can be removed.

### Pattern 2: Exception Isolation in watch_qsos Inner Loop

**What:** Wrap the Jinja2 render + broadcast call in `try/except Exception` so any non-cancellation exception logs and continues the loop rather than killing the watcher.

**Current code (manager.py lines 34-52):**
```python
async with await collection.watch(pipeline, full_document="updateLookup") as stream:
    async for change in stream:
        doc = change.get("fullDocument", {})
        if doc:
            ctx = { ... }
            html = templates.get_template("log/feed_row.html").render(ctx)  # can raise
            await mgr.broadcast(html)
```

**Fixed pattern:**
```python
# Source: STATE.md v2.4 Architecture Decisions + ARCHITECTURE.md
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
            raise   # Do not swallow cancellation
        except Exception as e:
            logger.error("feed_row render/broadcast failed: %s", e)
            continue   # Watcher stays alive
```

**Critical:** `asyncio.CancelledError` must be re-raised (or checked before the broad `except Exception`). In Python 3.8+, `CancelledError` is a subclass of `BaseException`, not `Exception`, so `except Exception` does NOT catch it. The explicit `except asyncio.CancelledError: raise` shown above is defensive documentation — it is not actually needed since `except Exception` already excludes `BaseException` subclasses. Including it makes the intent explicit.

### Pattern 3: LIVE Indicator — Message-First State Machine

**What:** The LIVE indicator must not turn green until at least one `htmx:sseMessage` event is received (proving data flows), not just on `htmx:sseOpen` (proving the HTTP connection opened).

**Current code in `log.html` (lines 114-152):**

```javascript
document.body.addEventListener('htmx:sseOpen', function (e) {
  if (e.detail.elt && e.detail.elt.id === 'log-table') {
    indicator.classList.remove('hidden');
    indicator.classList.add('flex');
    // Sets to LIVE green immediately -- bug
  }
});
```

**Fixed state machine:**

```javascript
// Source: STATE.md v2.4 Architecture Decisions
(function () {
  var indicator = document.getElementById('live-indicator');
  var sseConnected = false;   // HTTP connection open
  var eventsFlowing = false;  // at least one message received

  function setLive() {
    indicator.classList.remove('hidden');
    indicator.classList.add('flex');
    // Remove offline classes, add live classes
    indicator.className = indicator.className
      .replace(/bg-rose-\S+/g, '')
      .replace(/text-rose-\S+/g, '');
    if (!indicator.className.includes('bg-emerald')) {
      indicator.className += ' bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400';
    }
    indicator.querySelector('span:last-child').textContent = 'LIVE';
  }

  function setOffline() {
    indicator.classList.remove('hidden');
    indicator.classList.add('flex');
    indicator.querySelector('span:last-child').textContent = 'OFFLINE';
  }

  function setHidden() {
    indicator.classList.add('hidden');
    indicator.classList.remove('flex');
    eventsFlowing = false;
  }

  document.body.addEventListener('htmx:sseOpen', function (e) {
    if (e.detail.elt && e.detail.elt.id === 'log-table') {
      sseConnected = true;
      // Do NOT set green here. Wait for first message.
    }
  });

  document.body.addEventListener('htmx:sseMessage', function (e) {
    if (!e.detail || !e.detail.elt || e.detail.elt.id !== 'log-table') return;
    if (!eventsFlowing) {
      eventsFlowing = true;
      setLive();
    }
    // ... existing new_qso handler below ...
    if (e.detail.type !== 'new_qso') return;
    if (!document.getElementById('auto-refresh-ok')) return;
    if (document.querySelector('#log-table input')) return;
    htmx.ajax('GET', '/log/view', { target: '#log-table', swap: 'innerHTML' });
  });

  document.body.addEventListener('htmx:sseError', function (e) {
    if (e.detail.elt && e.detail.elt.id === 'log-table') {
      eventsFlowing = false;
      setOffline();
    }
  });

  document.body.addEventListener('htmx:sseClose', function (e) {
    if (e.detail.elt && e.detail.elt.id === 'log-table') {
      setHidden();
    }
  });
})();
```

**Key distinction:** `htmx:sseOpen` fires when the EventSource HTTP connection opens (proof: network layer works). `htmx:sseMessage` fires when the server actually sends a frame (proof: watcher is alive and sending). Setting green on `sseOpen` masks a dead watcher. The fix delays green until the first message.

**Note on `htmx:sseClose` vs `htmx:sseError`:** The current code hides the indicator entirely on `sseClose`. The fix retains this behavior. The `htmx:sseError` path shows OFFLINE (not hidden), which is distinct from a clean close.

### Pattern 4: pymongo AsyncCollection.watch() — Double-Await Is Correct

**VERIFIED finding:** In pymongo 4.16.0 (installed version), `AsyncCollection.watch()` is an `async def` method that returns an `AsyncCollectionChangeStream`, which is also an async context manager.

The official pymongo source documentation for this version explicitly shows:

```python
# Source: [VERIFIED: /Users/royco/ollog/.venv/lib/python3.14/site-packages/pymongo/asynchronous/collection.py line 456-458]
async with await db.collection.watch() as stream:
    async for change in stream:
        print(change)
```

This means the current code (`async with await collection.watch(pipeline, ...) as stream:`) is **correct** — the `await` is needed because `watch()` is an `async def`, and `async with` is needed because the returned object is an async context manager. There is no bug to fix here.

### Anti-Patterns to Avoid

- **`async with collection.watch(...)` without `await`:** Missing the `await` would be a `TypeError` at runtime because `watch()` is a coroutine — you must await it first to get the context manager. The current code correctly uses `async with await`.
- **`except BaseException` in the watcher loop:** This would catch `asyncio.CancelledError` and prevent clean shutdown. Use `except Exception` only.
- **Setting indicator green on `htmx:sseOpen`:** This is the exact bug to fix. Connection open does not prove data is flowing.
- **Setting indicator grey on `htmx:sseMessage` error handling:** The `htmx:sseMessage` handler should not change indicator state on `new_qso` processing failures — keep indicator concerns separate from refresh logic.
- **Removing `flex` class from indicator without checking if it was previously `flex`:** The current className manipulation pattern can leave stale class strings. The fixed version uses separate `classList` calls rather than string replacement to avoid CSS class pollution.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Task GC prevention | Custom weak-ref tracking | `app.state.watcher_task` | FastAPI `app.state` is the idiomatic strong-reference store for lifespan-scoped objects |
| Change stream reconnect on MongoDB error | Custom retry loop | Existing `while True` + `except PyMongoError` pattern already in manager.py | Already correct; only the inner-loop exception isolation is missing |
| Detecting SSE event flow vs. connection open | Polling, heartbeat mechanism | `htmx:sseMessage` event | Already available in htmx-ext-sse 2.2.4; no new infrastructure needed |

**Key insight:** Both fixes are 5-10 line changes to existing files. The existing architecture already handles the outer reconnect loop (PyMongoError catch with sleep/retry) and the outer task lifecycle (cancel on shutdown). Only the inner exception isolation and the strong reference are missing.

---

## Runtime State Inventory

Phase 44 is a bug fix, not a rename or migration. No stored data, live service config, OS-registered state, secrets, or build artifacts are affected.

**Nothing found in any category** — verified by reading all modified files and the lifespan. The watcher task is transient (recreated on each startup). No data is persisted by this phase.

---

## Common Pitfalls

### Pitfall 1: CancelledError Is a BaseException, Not an Exception

**What goes wrong:** Developer assumes `except Exception` is insufficient and wraps the loop body in `except BaseException`, which suppresses `asyncio.CancelledError`. Clean shutdown via `watcher_task.cancel()` then hangs or raises confusing errors.

**Why it happens:** Conflating "catch all exceptions" with "catch BaseException."

**How to avoid:** In Python 3.8+, `asyncio.CancelledError` is a `BaseException`, not an `Exception`. `except Exception` is safe — it does not catch `CancelledError`. The explicit `except asyncio.CancelledError: raise` above is defensive but not mechanically necessary.

**Warning signs:** Shutdown takes >1 second and logs "watcher cancelled" does not appear on SIGTERM.

### Pitfall 2: watcher_task Local Variable Still Used in Shutdown Path

**What goes wrong:** After adding `app.state.watcher_task`, the shutdown path still references the old local variable `watcher_task`, which may be `None` if client was `None`.

**Why it happens:** The shutdown code at the bottom of the lifespan generator uses the same local `watcher_task` variable that is being replaced.

**How to avoid:** Replace all references in the shutdown section — `if watcher_task is not None:` and `watcher_task.cancel()` — with `app.state.watcher_task`.

**Warning signs:** Watcher is not cancelled on shutdown; the shutdown hangs waiting for a task cancel that never happens.

### Pitfall 3: LIVE Indicator Goes Green Then Never Returns to Grey If Watcher Dies After Initial Messages

**What goes wrong:** The fix correctly requires at least one message before going green. But if the watcher dies after the first few messages and the SSE connection stays open (the connection is still alive; only the watcher is dead), no `htmx:sseClose` fires. The indicator stays green indefinitely even though no new events will ever arrive.

**Why it happens:** The SSE HTTP connection (client to `/feed/station`) is independent from the watcher task (server-side loop). A dead watcher does not close existing client SSE connections — their queues simply never receive new items.

**Impact on this phase:** This is a fundamental limitation of the architecture that Phase 44 cannot fully solve without a heartbeat mechanism. The LIVE-02 requirement says "turns green only after at least one SSE event has been received in the current browser session" and "returns to grey/offline if the SSE connection drops or the event stream goes silent." The fix fully addresses the first part; the second part (goes silent) is not detectable without a timeout or heartbeat. However, the success criteria for Phase 44 only explicitly requires (a) green after first message, not on open; and (b) grey on disconnect. A silently dead watcher with an open connection is a future hardening concern (heartbeat/timeout), not a LIVE-02 blocker.

**How to handle:** Implement the message-first trigger as specified. Document the silent-dead-watcher limitation as a known gap in a code comment. Do not add a heartbeat mechanism in this phase — it is out of scope.

**Warning signs:** Indicator stays green after watcher dies due to an un-caught error outside the inner try/except.

### Pitfall 4: Existing Class String Manipulation Leaves Stale Classes

**What goes wrong:** The current indicator JavaScript uses string replacement (`indicator.className = indicator.className.replace('bg-rose-...', '') + ' bg-emerald-...'`) to toggle between LIVE/OFFLINE states. If the indicator transitions through multiple states, stale classes accumulate.

**Why it happens:** String concatenation does not check for existing occurrences; `replace()` only removes the first match.

**How to avoid:** Use `classList.remove()` / `classList.add()` for each class individually, or fully rewrite `className`. The simpler approach: keep the LIVE (emerald) classes as the default in the HTML (as they currently are), and only add/remove an `offline` or `hidden` variant class. Since the indicator is hidden by default (`hidden` class) and shown only on SSE events, the state machine is: hidden → live (first message) → offline (error) → hidden (close).

---

## Code Examples

### Verified: pymongo watch() is async def + returns async context manager

```python
# Source: VERIFIED — /Users/royco/ollog/.venv/.../pymongo/asynchronous/collection.py:433-447
# async def watch(...) -> AsyncCollectionChangeStream[_DocumentType]
# Official example from docstring (line 456):
async with await db.collection.watch() as stream:
    async for change in stream:
        print(change)
```

**Conclusion: current code's `async with await collection.watch(...)` is correct. No change needed to the watch() call.**

### Current log.html LIVE indicator trigger (the bug)

```javascript
// Source: VERIFIED — /Users/royco/ollog/templates/log/log.html:118-127
document.body.addEventListener('htmx:sseOpen', function (e) {
  if (e.detail.elt && e.detail.elt.id === 'log-table') {
    indicator.classList.remove('hidden');
    indicator.classList.add('flex');
    indicator.querySelector('span:last-child').textContent = 'LIVE';
    // BUG: sets green on connection open, before any events have flowed
  }
});
```

### Current main.py watcher task creation (the weak-reference bug)

```python
# Source: VERIFIED — /Users/royco/ollog/app/main.py:25-31
watcher_task = None          # local variable — GC risk on Python 3.12+
if client is not None:
    from app.feed.manager import manager as feed_manager, watch_qsos
    collection = client[settings.mongodb_db]["qsos"]
    watcher_task = asyncio.create_task(
        watch_qsos(collection, feed_manager, _templates)
    )
```

### Current manager.py exception handling gap

```python
# Source: VERIFIED — /Users/royco/ollog/app/feed/manager.py:32-54
while True:
    try:
        async with await collection.watch(pipeline, full_document="updateLookup") as stream:
            async for change in stream:
                doc = change.get("fullDocument", {})
                if doc:
                    ctx = { ... }
                    html = templates.get_template("log/feed_row.html").render(ctx)  # BUG: unhandled
                    await mgr.broadcast(html)
    except PyMongoError as e:
        logger.warning("Change stream error, reconnecting: %s", e)
        await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Change stream watcher cancelled")
        break
    # BUG: any other exception (Jinja2, AttributeError, TypeError) propagates out
    # of the while loop, killing the watcher task permanently with no restart
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Motor (async MongoDB driver) | pymongo 4.x native async | pymongo 4.13+ | `get_motor_collection()` → `AsyncMongoClient`; watch() is now `async def` returning async context manager |
| `asyncio.ensure_future()` for background tasks | `asyncio.create_task()` | Python 3.7+ | `create_task()` is the correct API; GC semantics identical — task must be stored in strong reference |
| HTMX SSE indicator on connection open | message-first indicator | This phase | Accurate reflection of watcher state |

**Deprecated/outdated:**
- Motor ODM: this codebase uses `pymongo.AsyncMongoClient` directly (Motor reached EOL/maintenance-only; beanie switched to pymongo native async). All `get_motor_collection()` references in older docs are irrelevant — the collection passed to `watch_qsos` is a pymongo `AsyncCollection`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | htmx-ext-sse 2.2.4 `htmx:sseMessage` event has `e.detail.elt` and `e.detail.type` properties matching the existing code's usage | Code Examples / Architecture Patterns | If properties differ, the existing code is already broken — but since the existing handler works, this is LOW risk |
| A2 | Python 3.12+ GC can collect an `asyncio.create_task()` result stored only in a local variable of a running coroutine | Common Pitfalls | Documented by Python team in asyncio docs; HIGH confidence from prior research [CITED: STATE.md which cites Python asyncio warnings] |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

A1 is LOW risk (existing code works). A2 is HIGH confidence from Python documentation.

---

## Open Questions

1. **htmx:sseOpen fires before vs. after the SSE connection is fully established**
   - What we know: `htmx:sseOpen` fires when `EventSource.onopen` fires (after HTTP 200 received)
   - What's unclear: Whether any SSE framework heartbeat/comment line from FastAPI's `EventSourceResponse` could trigger `htmx:sseMessage` before a real `new_qso` event — which would incorrectly set the indicator green even with a dead watcher
   - Recommendation: Check if `fastapi.sse.EventSourceResponse` sends a keep-alive comment on connect. If it does, `htmx:sseMessage` may fire for comments, not just named events. The existing handler guards with `e.detail.type !== 'new_qso'` — use the same guard before setting the indicator green. Only set green when `e.detail.type === 'new_qso'`.

2. **`app.state` initialization timing**
   - What we know: FastAPI `app.state` is available at module import time (it is a `State` object on the `FastAPI` instance)
   - What's unclear: Whether `app.state.watcher_task = None` should be set before the lifespan yields (to ensure the attribute always exists) or whether it is acceptable for the attribute to be absent before startup completes
   - Recommendation: Set `app.state.watcher_task = None` unconditionally at the top of the lifespan function, before the `if client is not None:` check. This ensures `hasattr(app.state, 'watcher_task')` is always `True` after startup.

---

## Environment Availability

Phase 44 requires no external tools beyond what is already in use. Tests are unit tests with mocks and do not require a live MongoDB connection.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pymongo async | watch_qsos watcher | Yes | 4.16.0 [VERIFIED] | — |
| Python 3.14 | project runtime | Yes [VERIFIED: .venv] | 3.14 | — |
| pytest + pytest-asyncio | test suite | Yes [VERIFIED: pyproject.toml dev deps] | >=8.0 / >=0.23 | — |
| MongoDB 7.x (for change streams) | Integration test only | Conditional | Requires localhost:27017 | Tests skip if unavailable (existing skip pattern in conftest.py) |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | pyproject.toml (pytest-asyncio mode inferred from existing tests) |
| Quick run command | `uv run pytest tests/test_watcher.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIVE-01a | `watch_qsos` survives an unhandled Jinja2 render exception and continues broadcasting on the next change event | unit (mock) | `uv run pytest tests/test_watcher.py::test_watcher_survives_render_exception -x` | Wave 0 |
| LIVE-01b | `app.state.watcher_task` is set (not None) after startup lifespan executes | unit (mock) | `uv run pytest tests/test_watcher.py::test_watcher_task_stored_in_app_state -x` | Wave 0 |
| LIVE-01c | A QSO document with `qso_date_utc=None` does not kill the watcher | unit (mock) | `uv run pytest tests/test_watcher.py::test_watcher_null_date_does_not_kill -x` | Wave 0 |
| LIVE-02a | LIVE indicator JS: green state is NOT set on htmx:sseOpen event | manual / JS unit | N/A — browser-side logic; verify manually in DevTools | manual-only |
| LIVE-02b | LIVE indicator JS: green state IS set after first htmx:sseMessage with type='new_qso' | manual / JS unit | N/A — browser-side logic; verify manually | manual-only |
| LIVE-02c | LIVE indicator: returns to OFFLINE on htmx:sseError | manual / JS unit | N/A — browser-side logic | manual-only |

### Test Scenarios for LIVE-01 (Watcher Hardening)

**Scenario A: Exception isolation**

```python
# tests/test_watcher.py
# Pattern: mock the templates to raise on first call, succeed on second.
# Assert watcher broadcasts the second event successfully.

async def test_watcher_survives_render_exception():
    from app.feed.manager import ConnectionManager, watch_qsos
    from unittest.mock import MagicMock, AsyncMock, patch

    mgr = ConnectionManager()
    q = await mgr.connect()

    call_count = 0
    def template_render_side_effect(ctx):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("simulated Jinja2 render error")
        return "<tr>ok</tr>"

    mock_template = MagicMock()
    mock_template.render.side_effect = template_render_side_effect

    mock_templates = MagicMock()
    mock_templates.get_template.return_value = mock_template

    # Mock change stream: yields two events then StopAsyncIteration
    change1 = {"fullDocument": {"CALL": "W1AW", "BAND": "20M", "MODE": "FT8",
                                 "FREQ": "", "_operator": "VK2ABC", "qso_date_utc": None}}
    change2 = {"fullDocument": {"CALL": "VK2QQ", "BAND": "40M", "MODE": "SSB",
                                 "FREQ": "7.150", "_operator": "VK2ABC", "qso_date_utc": None}}

    mock_stream = MagicMock()
    mock_stream.__aiter__ = AsyncMock(return_value=iter([change1, change2]))
    # ... (full mock of AsyncCollectionChangeStream context manager)

    # After: assert q.get_nowait() == "<tr>ok</tr>"  (second event did broadcast)
    # Assert call_count == 2 (template was called twice; watcher did not die after first error)
```

**Scenario B: Strong reference**

```python
async def test_watcher_task_stored_in_app_state():
    # Use TestClient lifespan context or mock the lifespan
    # Assert: after lifespan startup, app.state.watcher_task is not None
    # Assert: app.state.watcher_task is an asyncio.Task
    pass
```

**Scenario C: Null qso_date_utc (the trigger for the Jinja2 bug)**

```python
async def test_watcher_null_date_does_not_kill():
    # Feed a change event with qso_date_utc=None
    # Assert watcher continues to the next iteration (no exception propagates)
    pass
```

### Test Scenarios for LIVE-02 (Indicator Accuracy)

LIVE-02 tests are browser-side JavaScript logic. Automated pytest cannot exercise them directly. Manual verification protocol:

1. Open `/log/view` in Chrome DevTools.
2. Check Network > EventStream tab: SSE connection to `/feed/station` visible.
3. Confirm LIVE indicator is hidden (not green) before any event arrives.
4. Trigger a QSO insert (REST API POST or UI form).
5. Observe: indicator turns green only after the SSE `new_qso` event frame arrives in the EventStream tab.
6. Kill the watcher (simulate: restart server, or force an unrecoverable error).
7. Observe: indicator shows OFFLINE or goes hidden on `htmx:sseError`/`htmx:sseClose`.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_watcher.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_watcher.py` — covers LIVE-01a, LIVE-01b, LIVE-01c

*(LIVE-02 tests are manual-only — no new pytest file needed for those.)*

---

## Security Domain

Phase 44 makes no changes to authentication, session management, access control, input validation, or cryptography. The watcher reads from an internal MongoDB change stream and renders a static HTML template. No user-supplied data reaches the watcher path.

ASVS categories V2, V3, V4, V6 do not apply. V5 (input validation) is not applicable — the `doc.get(...)` calls with safe defaults already handle missing or unexpected fields without injection risk.

**No security concerns for this phase.**

---

## Sources

### Primary (HIGH confidence)

- `[VERIFIED: codebase]` `/Users/royco/ollog/app/feed/manager.py` — complete watcher implementation, read directly
- `[VERIFIED: codebase]` `/Users/royco/ollog/app/main.py` — lifespan task creation, read directly
- `[VERIFIED: codebase]` `/Users/royco/ollog/templates/log/log.html` — full LIVE indicator JavaScript, read directly
- `[VERIFIED: codebase]` `/Users/royco/ollog/app/database.py` — confirms `AsyncMongoClient` (not Motor)
- `[VERIFIED: .venv source]` `/Users/royco/ollog/.venv/.../pymongo/asynchronous/collection.py:433-479` — `watch()` is `async def`, returns `AsyncCollectionChangeStream`; official docstring confirms `async with await` pattern
- `[VERIFIED: shell]` `uv run python -c "import pymongo; print(pymongo.version)"` → `4.16.0`
- `[VERIFIED: codebase]` `pyproject.toml` — `pymongo>=4.16.0`, no new packages for v2.4
- `[CITED: STATE.md v2.4 Architecture Decisions]` — all pre-decided implementation choices

### Secondary (MEDIUM confidence)

- `[CITED: .planning/research/ARCHITECTURE.md]` — SSE data flow diagram, confirmed against codebase
- `[CITED: .planning/research/PITFALLS.md]` — pitfall inventory, confirmed against codebase
- `[CITED: .planning/research/SUMMARY.md]` — executive summary of root causes

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in .venv and pyproject.toml
- Architecture: HIGH — full source read, no inference
- pymongo watch() double-await: HIGH — verified in installed source code
- LIVE indicator current behavior: HIGH — full JS read, exact lines identified
- Pitfalls: HIGH — derived from direct code reading + prior milestone research
- Test plan: MEDIUM — test structure outlined but exact mock implementation needs authoring in Wave 0

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (stable libraries; pymongo 4.x API is stable)
