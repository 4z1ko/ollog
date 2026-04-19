---
phase: 44-sse-watcher-hardening
plan: "01"
subsystem: backend
tags: [sse, watcher, asyncio, exception-isolation, app-state]
dependency_graph:
  requires: []
  provides: [LIVE-01]
  affects: [app/feed/manager.py, app/main.py, tests/test_watcher.py]
tech_stack:
  added: []
  patterns: [exception-isolation, app-state-strong-reference, async-mock-testing]
key_files:
  created:
    - tests/test_watcher.py
  modified:
    - app/feed/manager.py
    - app/main.py
decisions:
  - "All 3 tasks were already committed in a prior session (commits 8b0a9fd, 71b978e, fe5de3c); SUMMARY.md was the only missing artifact"
  - "Extra logger.info lines found in working tree are pre-existing uncommitted additions outside plan scope — not committed"
metrics:
  duration: "prior session"
  completed: "2026-04-19"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 3
status: complete
---

# Phase 44 Plan 01: SSE Watcher Hardening Summary

**One-liner:** Hardened the SSE change-stream watcher with exception isolation in the inner loop and a strong task reference via `app.state.watcher_task`, preventing Python 3.12+ GC from killing it.

## What Was Built

Three targeted fixes make the watcher resilient to runtime failures:

1. **`tests/test_watcher.py`** — 3 pytest tests covering LIVE-01a (exception isolation), LIVE-01b (app.state strong reference), LIVE-01c (null qso_date_utc handling). Fully mocked, no live MongoDB required.

2. **`app/feed/manager.py`** — Wrapped the `html = templates.get_template(...).render(ctx)` + `await mgr.broadcast(html)` calls in `try/except Exception`. A render failure now logs the error and `continue`s to the next change event instead of propagating and killing the watcher task.

3. **`app/main.py`** — Replaced local `watcher_task` variable with `app.state.watcher_task`. The task reference is now stored on the FastAPI `State` object, which lives for the entire application lifetime, preventing Python 3.12+ garbage collection from reclaiming the task between event loop ticks.

## Task Results

| Task | Name | Status | Commit | Files |
|------|------|--------|--------|-------|
| 1 | Create tests/test_watcher.py with Wave 0 test stubs | Complete | 8b0a9fd | tests/test_watcher.py |
| 2 | Fix app/feed/manager.py — exception isolation in watch_qsos inner loop | Complete | 71b978e | app/feed/manager.py |
| 3 | Fix app/main.py — store watcher task in app.state (strong reference) | Complete | fe5de3c | app/main.py |

## Test Results

```
tests/test_watcher.py::test_watcher_survives_render_exception PASSED
tests/test_watcher.py::test_watcher_task_stored_in_app_state PASSED
tests/test_watcher.py::test_watcher_null_date_does_not_kill PASSED
3 passed in 1.54s
```

## Acceptance Criteria Verification

| Criterion | Result |
|-----------|--------|
| `grep "except Exception as e:" app/feed/manager.py` matches | PASS |
| `grep "except asyncio.CancelledError:" app/feed/manager.py` matches ≥2 lines | PASS (inner + outer) |
| `grep "logger.error" app/feed/manager.py` matches | PASS |
| `grep "logger.debug" app/feed/manager.py` matches | PASS |
| `grep "if not doc:" app/feed/manager.py` matches | PASS |
| `grep "app.state.watcher_task = None" app/main.py` matches 1 line | PASS |
| `grep "app.state.watcher_task = asyncio.create_task" app/main.py` matches 1 line | PASS |
| `grep "if app.state.watcher_task is not None:" app/main.py` matches 1 line | PASS |
| `grep -c "watcher_task" app/main.py` returns 5 (all app.state references) | PASS |
| All 3 test_watcher.py tests pass | PASS |

## Deviations from Plan

None — all tasks executed as specified. SUMMARY.md was the only artifact missing when this execution session began (code was already committed in a prior run).

## Known Stubs

None.

## Threat Flags

T-44-01 (logger.error may include QSO field values): Accepted — QSO data (callsigns) is not PII and logs are not user-facing.
T-44-02 (tight error loop): Mitigated by event-rate-bounded inner loop and 1s sleep on outer PyMongoError handler.

## Self-Check: PASSED

- tests/test_watcher.py exists with 3 test functions collected
- app/feed/manager.py has `except Exception as e:` in inner loop
- app/main.py has `app.state.watcher_task` in 5 places (no bare local variable)
- All 3 watcher tests pass
- SUMMARY.md created at `.planning/phases/44-sse-watcher-hardening/44-01-SUMMARY.md`
