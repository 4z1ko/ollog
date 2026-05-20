---
phase: 44-sse-watcher-hardening
reviewed: 2026-04-19T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - app/feed/manager.py
  - app/main.py
  - tests/test_watcher.py
  - templates/log/log.html
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 44: Code Review Report

**Reviewed:** 2026-04-19
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

This phase hardens the SSE change-stream watcher with exception isolation, a strong app.state reference, and null-date tolerance. The core logic in `manager.py` and the lifespan wiring in `main.py` are sound. Three issues require attention before sign-off:

1. The two watcher unit tests use `asyncio.sleep(0)` before `task.cancel()` — this is insufficient to drain the AsyncMock call chain, making the tests structurally flaky on some event-loop schedulers.
2. The OFFLINE indicator in the `htmx:sseError` handler adds `dark:bg-rose-100` and `dark:text-rose-700` via `classList.add()`, but those dark-mode variants are never referenced in static template HTML and are therefore absent from the compiled Tailwind CSS. The indicator will display correctly in light mode but lose dark-mode styling.
3. `backup_task` is declared `None` at line 61 of `main.py` and the shutdown block at line 86 checks it, but it is never assigned a real value (the scheduler is stored in `backup_scheduler`, not `backup_task`). The cancel block is dead code that will never execute.

---

## Warnings

### WR-01: `backup_task` is never assigned — shutdown cancel block is dead code

**File:** `app/main.py:61`
**Issue:** `backup_task = None` is declared at line 61 and the shutdown block at lines 86-91 awaits its cancellation, but `backup_task` is never assigned a `Task` object. The backup job is managed entirely by `backup_scheduler` (an APScheduler instance). The `backup_task.cancel()` / `await backup_task` block at lines 87-90 will never execute because `backup_task` remains `None` at shutdown. This is dead code indicating a structural mismatch — either the scheduler was refactored away from a bare task and the cancellation code was left behind, or the intent was to also cancel a task that was never created.

**Fix:** Remove the dead `backup_task` cancel block since the scheduler is properly shut down via `backup_scheduler.shutdown(wait=False)`:

```python
# Remove lines 61 and 86-91 entirely:
# backup_task = None          <- delete
# if backup_task is not None: <- delete
#     backup_task.cancel()    <- delete
#     try:                    <- delete
#         await backup_task   <- delete
#     except asyncio.CancelledError: <- delete
#         pass                <- delete
```

If a bare asyncio Task is ever needed for backup, assign it explicitly and remove the scheduler path.

---

### WR-02: Flaky tests — `asyncio.sleep(0)` insufficient before `task.cancel()`

**File:** `tests/test_watcher.py:77` and `tests/test_watcher.py:140`
**Issue:** Both `test_watcher_survives_render_exception` and `test_watcher_null_date_does_not_kill` call `asyncio.create_task(watch_qsos(...))` then `await asyncio.sleep(0)` and immediately `task.cancel()`. A single `sleep(0)` yields control to the event loop once, but `watch_qsos` must complete at least two AsyncMock suspensions before processing any changes:
- `await collection.watch(...)` — AsyncMock, suspends once
- `await stream.__aenter__()` — AsyncMock, suspends once

After a single `sleep(0)`, the task is typically still blocked inside the `watch()` call when `cancel()` arrives. The assertions (`call_count == 2`, `q.get_nowait()`) then fail because the changes were never processed. This is a timing-dependent flakiness that may pass or fail depending on the asyncio scheduler version and event-loop state.

**Fix:** Poll until the queue is populated or use a small bounded wait before cancelling:

```python
# Replace:
await asyncio.sleep(0)
task.cancel()

# With: wait until the broadcast arrives (bounded by timeout to avoid hang)
try:
    html = await asyncio.wait_for(q.get(), timeout=1.0)
    assert html == "<tr>ok</tr>"
finally:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

# Remove the duplicate q.get_nowait() assertion below
```

Alternatively, add multiple `await asyncio.sleep(0)` yields (at least 3-4) to advance the task past the AsyncMock chain — but `wait_for` is more robust.

---

### WR-03: Dark-mode OFFLINE indicator classes not compiled into CSS

**File:** `templates/log/log.html:231`
**Issue:** The `htmx:sseError` handler dynamically adds `dark:bg-rose-100` and `dark:text-rose-700` to the live indicator via `classList.add()`. Tailwind scans `./templates/**/*.html` for class names to compile (per `tailwind.config.js`), but it performs static string scanning — classes that only appear in JavaScript expressions are invisible to the scanner. Neither `dark:bg-rose-100` nor `dark:text-rose-700` appears anywhere in static template HTML, so they are absent from `static/css/output.css`. In dark mode, the OFFLINE indicator will display with no background and no text color.

**Fix:** Add the classes to the safelist in `tailwind.config.js`:

```js
// tailwind.config.js
module.exports = {
  // ...
  safelist: [
    'dark:bg-rose-100',
    'dark:text-rose-700',
    // Also consider dark analogues for bg-rose-900/40, text-rose-400
    // if a fully dark-mode-native OFFLINE style is desired
  ],
  // ...
}
```

Or anchor the classes in a comment-only HTML element so Tailwind's scanner picks them up:

```html
<!-- Tailwind safelist anchor: dark:bg-rose-100 dark:text-rose-700 -->
```

Note: `bg-rose-100` and `text-rose-700` (without `dark:`) are already compiled and will apply correctly in light mode. Only the dark variants are missing.

---

## Info

### IN-01: `full_document="updateLookup"` is a no-op for insert-only pipeline

**File:** `app/feed/manager.py:36`
**Issue:** The change stream pipeline at line 32 filters to `operationType: insert` only. The `full_document="updateLookup"` option causes MongoDB to perform an additional read to fetch the current document state for update operations. For inserts, the `fullDocument` is always included in the change event payload directly — no lookup is performed. Passing `updateLookup` here is harmless but carries a misleading implication that update events may arrive.

**Fix:** Use `full_document="required"` (available in pymongo 4.x) which asserts that `fullDocument` is always present, or simply omit the option since insert events always include `fullDocument`:

```python
async with await collection.watch(pipeline) as stream:
```

This is low priority — no correctness impact.

---

### IN-02: No reconnect backoff — rapid reconnect loop on persistent errors

**File:** `app/feed/manager.py:59-61`
**Issue:** The `PyMongoError` handler sleeps 1 second before reconnecting. This is a flat retry interval with no backoff. Under persistent failure conditions (network partition, MongoDB restart taking minutes), the watcher will log a warning every second and attempt to reconnect indefinitely at full rate. This is not a correctness issue but will produce log spam and modest CPU churn under sustained outages.

**Fix:** Add exponential backoff with a cap (e.g., 1s, 2s, 4s, ... up to 60s):

```python
retry_delay = 1
# ...
except PyMongoError as e:
    logger.warning("Change stream error, reconnecting in %ss: %s", retry_delay, e)
    await asyncio.sleep(retry_delay)
    retry_delay = min(retry_delay * 2, 60)
```

Reset `retry_delay = 1` at the top of the `while True` loop body on successful stream open.

---

_Reviewed: 2026-04-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
