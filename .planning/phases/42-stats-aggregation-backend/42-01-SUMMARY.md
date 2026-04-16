---
phase: 42-stats-aggregation-backend
plan: 01
subsystem: stats
tags: [stats, aggregation, mongodb, dxcc, operator-isolation]
dependency_graph:
  requires: [app/qso/models.py, app/callsign/prefixes.py, app/auth/dependencies.py]
  provides: [app/stats/service.py, app/stats/router.py, GET /log/stats]
  affects: [app/main.py, templates/log/stats.html]
tech_stack:
  added: []
  patterns: [pymongo-async-aggregate, beanie-get_pymongo_collection, cookie-auth-ui-router]
key_files:
  created:
    - app/stats/__init__.py
    - app/stats/service.py
    - app/stats/router.py
    - templates/log/stats.html
    - tests/test_stats.py
  modified:
    - app/main.py
decisions:
  - "Use get_pymongo_collection() (not get_motor_collection()) — Motor was EOL'd May 2025; Beanie now exposes get_pymongo_collection() for raw collection access"
  - "await (await collection.aggregate(pipeline)).to_list() — pymongo AsyncCollection.aggregate() is a coroutine returning a cursor, not a cursor directly"
  - "unique_entity_count computed from iso_seen set before top-8 truncation per architecture decision in STATE.md"
  - "is_deleted (Python field name) used in tests, not _deleted (MongoDB alias) — Beanie ignores dynamic attribute assignment on alias names"
metrics:
  duration_minutes: 62
  completed_date: "2026-04-16"
  tasks_completed: 2
  files_changed: 6
requirements_satisfied: [STATS-06, STATS-07]
---

# Phase 42 Plan 01: Stats Aggregation Backend Summary

**One-liner:** MongoDB aggregation pipeline for band/mode/DXCC counts with JWT-isolated `get_stats()` service and `GET /log/stats` stub route backed by 7 integration tests.

## What Was Built

### `app/stats/service.py` — `get_stats(callsign: str) -> dict`

Three MongoDB aggregation pipelines (band, mode, CALL-level) each guarded by `{"$match": {"_operator": callsign, "_deleted": False}}` as the first stage (STATS-06, T-42-01, T-42-03). Python-side DXCC rollup resolves callsigns via `lookup_prefix()` + `pycountry.countries.get(alpha_2=...)` for full country names (D-01). Unresolvable callsigns group under "Unknown" (D-02). `unique_entity_count` is computed from `len(iso_seen)` before the top-8 truncation. Empty log returns a complete zero-value dict shape (STATS-07).

### `app/stats/router.py` — `stats_router`

`APIRouter(prefix="/log")` with `GET /stats` handler using `Depends(get_current_operator_callsign_cookie)` for cookie-auth enforcement (T-42-02). Registered in `app/main.py` with `include_in_schema=False` after the token router, before static file mounts.

### `templates/log/stats.html` — Phase 42 stub

Extends `base_app.html`, sets `active_page=stats`, renders `total_qsos` and `unique_entity_count`. Empty-state message when `total_qsos == 0`. Phase 43 will add Chart.js pie charts on top of this data pipeline.

### `tests/test_stats.py` — 7 integration tests

All 7 pass: empty-log shape (STATS-07), operator isolation (STATS-06), soft-delete exclusion, DXCC entity resolution, unknown callsign handling, route auth enforcement (302 without cookie), route 200 for authenticated operator with empty log.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `get_motor_collection()` does not exist — renamed to `get_pymongo_collection()`**
- **Found during:** Task 1 verification
- **Issue:** Plan referenced `QSO.get_motor_collection()` but Motor was EOL'd May 2025; Beanie now exposes `get_pymongo_collection()`
- **Fix:** Changed to `QSO.get_pymongo_collection()` in `app/stats/service.py`
- **Files modified:** `app/stats/service.py`
- **Commit:** 0e96f78

**2. [Rule 1 - Bug] `collection.aggregate()` is a coroutine, not a cursor**
- **Found during:** Task 2 test run
- **Issue:** Plan's pattern `await collection.aggregate(pipeline).to_list()` fails because `AsyncCollection.aggregate()` returns a coroutine; you must await it to get the cursor first
- **Fix:** Changed to `(await collection.aggregate(pipeline)).to_list(length=None)` for all 3 pipelines
- **Files modified:** `app/stats/service.py`
- **Commit:** 0e96f78

**3. [Rule 1 - Bug] Test used `_deleted` (MongoDB alias) instead of `is_deleted` (Python field name)**
- **Found during:** Task 2 test run (`test_stats_excludes_soft_deleted` failed — assert 2 == 1)
- **Issue:** `deleted_qso._deleted = True` sets a dynamic Python attribute that Beanie ignores; the correct Python field name is `is_deleted` (alias `_deleted` is only the MongoDB key)
- **Fix:** Changed `deleted_qso._deleted = True` to `deleted_qso.is_deleted = True` in `tests/test_stats.py`
- **Files modified:** `tests/test_stats.py`
- **Commit:** 0e96f78

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| Stats template (no charts) | `templates/log/stats.html` | all | Phase 42 intentional stub — Chart.js pie charts added in Phase 43 |

The stub is intentional and documented in the template comment: `{# Phase 42 stub -- charts and full stats UI added in Phase 43 #}`. The data pipeline is fully wired; `total_qsos` and `unique_entity_count` render correctly.

## Threat Surface Scan

All three STRIDE threats from the plan's threat model are mitigated:

| Threat ID | Mitigation Verified |
|-----------|---------------------|
| T-42-01 | `$match` with `_operator` is first stage in all 3 pipelines; `test_stats_operator_isolation` passes |
| T-42-02 | `Depends(get_current_operator_callsign_cookie)` on route; `test_stats_route_requires_auth` confirms 302 redirect |
| T-42-03 | `_deleted: False` in every `$match`; `test_stats_excludes_soft_deleted` passes |

No new threat surface introduced beyond what the plan declared.

## Verification Results

1. `uv run pytest tests/test_stats.py -x -v` — **7/7 passed**
2. `grep -c "stats_router" app/main.py` — returns **2** (import + include_router)
3. `python -c "from app.stats.service import get_stats; from app.stats.router import stats_router; print('OK')"` — **OK**
4. Pre-existing test failures (4 failures, 63 errors) all involve Docker MongoDB URI (`mongodb:27017` replica set unreachable in local dev) — unrelated to this plan, not introduced by these changes

## Self-Check: PASSED

Files exist:
- `app/stats/__init__.py` — FOUND
- `app/stats/service.py` — FOUND
- `app/stats/router.py` — FOUND
- `templates/log/stats.html` — FOUND
- `tests/test_stats.py` — FOUND

Commits exist:
- `501b90b` (Task 1: service + tests) — FOUND
- `0e96f78` (Task 2: router + template + main.py + bug fixes) — FOUND
