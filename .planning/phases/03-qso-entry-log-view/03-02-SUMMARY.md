---
phase: 03-qso-entry-log-view
plan: 02
subsystem: api
tags: [fastapi, beanie, mongodb, pydantic, adif, qso, duplicate-detection]

# Dependency graph
requires:
  - phase: 03-01
    provides: QSO REST API, build_qso_dict, QSO model with _operator/_deleted aliases
  - phase: 01-04
    provides: JWT auth, get_current_operator_callsign dependency
provides:
  - find_duplicate service function: CALL/BAND/MODE/+/-2min window, operator-scoped, excludes deleted
  - POST /api/qsos/ wired to return 409 with duplicate info when match found
  - force=true query param bypasses duplicate check on POST
  - 10 duplicate detection tests covering all specified scenarios
affects: [03-03, 03-04, 04-01]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Duplicate detection via find_one with $gte/$lte on qso_date_utc within timedelta(minutes=2)"
    - "409 response body returns duplicate=true, existing_id, call/band/mode/date for UI display"
    - "force=true query param pattern: passes Query(False) default, bypasses app-level check when True"

key-files:
  created:
    - tests/test_duplicate_detection.py
  modified:
    - app/qso/service.py
    - app/qso/router.py
    - app/qso/models.py

key-decisions:
  - "Compound unique index dropped (unique=True removed): app-level duplicate detection is the enforcement mechanism; unique index blocked soft-deleted QSO re-insertion and force=true use cases"
  - "find_duplicate uses raw MongoDB field names (_operator, _deleted) matching index key order for correct hits"
  - "409 detail is a dict (not string) so UI can extract existing_id for confirmation flow"

patterns-established:
  - "Pattern: find_duplicate() called before insert in POST; skipped entirely when force=True (not checked-then-overridden)"
  - "Pattern: Duplicate response includes existing_id, existing_call/band/mode/date — enough for UI confirmation dialog"

# Metrics
duration: 4min
completed: 2026-04-03
---

# Phase 3 Plan 02: Duplicate Detection Summary

**find_duplicate service function with +/-2min CALL/BAND/MODE window returning 409, operator-scoped, soft-delete-aware, with force=true override — all 10 tests pass**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-03T11:47:11Z
- **Completed:** 2026-04-03T11:51:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `find_duplicate()` added to service.py: queries MongoDB for matching CALL/BAND/MODE within +/-2 min window, scoped to operator, excludes soft-deleted QSOs
- POST endpoint wired to call find_duplicate before insert; returns HTTP 409 with full duplicate info; force=true skips check entirely
- 10 duplicate detection tests: 3 expect 409 (within window, exact time, boundary), 6 expect 201 (outside window, different call/band/mode, deleted QSO, other operator), 1 force override
- Fixed pre-existing bug: compound unique index blocked valid use cases (re-inserting after soft-delete, force insert); replaced with non-unique compound index

## Task Commits

Each task was committed atomically:

1. **Task 1: find_duplicate service function and POST endpoint integration** - `fe04721` (feat)
2. **Task 2: Duplicate detection tests and unique index fix** - `523c057` (feat)

**Plan metadata:** TBD (docs commit)

## Files Created/Modified
- `app/qso/service.py` - Added find_duplicate() function with timedelta window query
- `app/qso/router.py` - Imported find_duplicate; wired into POST before insert with 409 response
- `app/qso/models.py` - Removed unique=True from operator_qso compound index (renamed to operator_qso_compound)
- `tests/test_duplicate_detection.py` - 10 tests for all duplicate detection scenarios

## Decisions Made
- Removed `unique=True` from the compound index on `{_operator, CALL, qso_date_utc, BAND, MODE}`: the plan requires soft-deleted QSOs to not block re-insertion and force=true to allow identical QSO inserts — both are impossible with a MongoDB unique constraint. App-level duplicate detection is the authoritative enforcement mechanism.
- 409 `detail` field is a dict (not a string) so API clients can extract `existing_id` for a "force save?" confirmation flow rather than needing to parse error text.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unique constraint from compound QSO index**
- **Found during:** Task 2 (test_no_duplicate_deleted_qso and test_force_skips_duplicate_check failing)
- **Issue:** The compound unique index `{_operator, CALL, qso_date_utc, BAND, MODE}` with `unique=True` prevented: (a) re-inserting a QSO with the same key values after soft-delete, and (b) inserting with `force=true` when an identical active QSO already exists. Both are required by the plan spec.
- **Fix:** Changed `unique=True` to non-unique in `IndexModel`; renamed index `operator_qso_unique` → `operator_qso_compound` to signal the change. App-level `find_duplicate()` is now the enforcement mechanism.
- **Files modified:** app/qso/models.py
- **Verification:** All 10 duplicate detection tests pass; all 23 existing QSO API tests still pass
- **Committed in:** 523c057

---

**Total deviations:** 1 auto-fixed (Rule 1 bug)
**Impact on plan:** Fix essential for plan spec correctness. The unique index contradicted the explicit requirements for deleted QSO exclusion and force override. No scope creep.

## Issues Encountered
- The pre-existing `operator_qso_unique` index was documented in STATE.md decisions as providing "concurrent duplicate safety". With app-level duplicate detection now in place, the unique constraint became redundant and contradictory to the spec. Removing it is the correct resolution.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Duplicate detection complete and tested — 03-03 (web form) can POST to /api/qsos/ and handle 409 responses for user confirmation
- 03-04 (log view) unaffected — uses GET /api/qsos/ endpoint, no changes there
- All 33 tests pass (10 new + 23 existing)

---
*Phase: 03-qso-entry-log-view*
*Completed: 2026-04-03*

## Self-Check: PASSED

- app/qso/service.py: FOUND
- app/qso/router.py: FOUND
- app/qso/models.py: FOUND
- tests/test_duplicate_detection.py: FOUND
- commit fe04721: FOUND
- commit 523c057: FOUND
