---
phase: 49-service-layer
plan: "01"
subsystem: service-layer
tags: [sort, security, sse, sentinel, input-validation]
dependency_graph:
  requires: [48-01]
  provides: [sort-allowlist, created-at-view-dict, sse-sentinel-extended]
  affects: [app/qso/service.py, app/qso/ui_router.py, templates/log/log_table.html]
tech_stack:
  added: []
  patterns: [frozenset-allowlist, logging-guard-block, jinja2-disjunction-parenthesization]
key_files:
  created:
    - tests/test_view_dict.py
    - tests/test_service_sort.py
    - tests/test_sse_sentinel.py
  modified:
    - app/qso/service.py
    - app/qso/ui_router.py
    - templates/log/log_table.html
decisions:
  - Used model_construct() with explicit created_at in test_view_dict.py (QSO() triggers Beanie collection init which fails without DB)
  - Added _mongo_available() skip guard to sentinel_db fixture (not in reference pattern from test_log_view_notify_sound.py, needed for no-MongoDB test environments)
metrics:
  duration: ~15 min
  completed: "2026-04-23"
  tasks_completed: 2
  files_modified: 3
  files_created: 3
---

# Phase 49 Plan 01: Sort Allowlist, Created-At View Dict, SSE Sentinel Summary

Sort parameter validation via `_ALLOWED_SORT_FIELDS` frozenset (10 values) in service.py, `created_at` exposed in view dict for Phase 50, and SSE auto-refresh sentinel extended to `-_created_at` sort with correct Jinja2 parenthesization.

## What Was Built

### app/qso/service.py
- Added `import logging` and `logger = logging.getLogger(__name__)`
- Added `_DEFAULT_SORT = "-qso_date_utc"` constant
- Added `_ALLOWED_SORT_FIELDS: frozenset[str]` with all 10 permitted sort values
- Updated `get_qso_page()` signature to use `_DEFAULT_SORT` (eliminates duplicated string literal)
- Added guard block as first statement in `get_qso_page()` body: rejects invalid sort fields with `logger.warning()` containing both the field name and operator callsign, falls back to `_DEFAULT_SORT`

### app/qso/ui_router.py
- Added `"created_at": qso.created_at` to `_qso_to_view_dict()` dict immediately after `"qso_date_utc"` — raw datetime, Phase 50 formats it

### templates/log/log_table.html
- Extended sentinel condition from `sort == '-qso_date_utc'` to `(sort == '-qso_date_utc' or sort == '-_created_at')` with load-bearing parentheses around the disjunction (Jinja2 `and` binds tighter than `or`)

### tests/test_view_dict.py (new)
- Unit test: `_qso_to_view_dict()` returns `"created_at"` key with a `datetime` value
- No MongoDB required — uses `QSO.model_construct()` with explicit `created_at`

### tests/test_service_sort.py (new)
- SORT-04 coverage: invalid sort fallback, all 10 allowed values accepted, WARNING content includes field + operator, `_ALLOWED_SORT_FIELDS` has exactly 10 values
- MongoDB-dependent tests skip gracefully via `_mongo_available()` guard

### tests/test_sse_sentinel.py (new)
- SORT-03 coverage: sentinel rendered for `-_created_at` and `-qso_date_utc`, absent for `CALL` sort and when filters are active
- MongoDB-dependent tests skip gracefully via `_mongo_available()` guard

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 5ec6a71 | feat(49-01): add sort allowlist to service.py and created_at to view dict |
| Task 2 | 2cedd25 | feat(49-01): extend SSE sentinel condition and add test coverage |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] QSO() constructor requires Beanie DB init — test_view_dict.py adapted**
- **Found during:** Task 1 verification (test run)
- **Issue:** Plan specified `QSO(...)` for in-memory test construction. Beanie's `Document.__init__()` calls `get_pymongo_collection()` which raises `CollectionWasNotInitialized` without DB init. The RESEARCH.md Pitfall 3 said "use QSO(...) not model_construct()" but this conflicts with the no-MongoDB constraint for the unit test.
- **Fix:** Used `QSO.model_construct(operator_callsign="TESTOP", CALL="W1AW", created_at=now)` with an explicit UTC datetime. This correctly tests that `_qso_to_view_dict()` maps `qso.created_at` → `result["created_at"]` without requiring MongoDB.
- **Files modified:** tests/test_view_dict.py
- **Commit:** 5ec6a71

**2. [Rule 2 - Missing critical functionality] Added _mongo_available() guard to sentinel_db fixture**
- **Found during:** Task 2 verification (test run)
- **Issue:** The `test_log_view_notify_sound.py` reference fixture pattern does not include a MongoDB availability check — it errors if MongoDB is unreachable rather than skipping. The `sentinel_db` fixture initially had the same problem, causing ERROR (not SKIP) in no-MongoDB environments.
- **Fix:** Added `import socket`, `_mongo_available()` helper, and `pytest.skip()` call at the top of `sentinel_db` fixture — matching the pattern from `test_operator_isolation.py` and `test_service_sort.py`.
- **Files modified:** tests/test_sse_sentinel.py
- **Commit:** 2cedd25

## Known Stubs

None. All data flows are wired. `created_at` in the view dict is populated from the Beanie model field (with `default_factory` for new inserts and Phase 48 backfill for existing documents). Phase 50 will consume this key for display.

## Threat Flags

No new network endpoints, auth paths, or trust boundary crossings introduced. The `_ALLOWED_SORT_FIELDS` guard specifically mitigates T-49-01 and T-49-02 from the plan's threat register.

## Self-Check: PASSED

All 7 files exist on disk. Both task commits (5ec6a71, 2cedd25) found in git log. Tests pass: 2 passed, 7 skipped (MongoDB-dependent tests skip correctly when DB is unavailable).
