---
phase: 03-qso-entry-log-view
plan: 01
subsystem: api
tags: [fastapi, beanie, mongodb, jwt, pydantic, adif, qso, rest-api]

# Dependency graph
requires:
  - phase: 01-04
    provides: JWT auth, get_current_operator_callsign dependency
  - phase: 01-03
    provides: QSO Beanie Document model with extra=allow and compound unique index
provides:
  - REST API at /api/qsos/ with POST, GET (list+by-id), PATCH, DELETE (soft-delete)
  - QSO service layer: parse_adif_datetime, build_qso_dict, get_qso_page
  - Cookie-auth callsign dependency for /log/ UI routes
  - Exception handler extended to redirect /log/ 401/403 to /log/login
affects: [03-02, 03-03, 03-04, 04-01]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Raw $set with MongoDB alias names (_operator, _deleted) for QSO update/delete"
    - "model_dump(by_alias=True) + pop(_id) + isoformat(qso_date_utc) for API response serialization"
    - "ObjectId validation with try/except before QSO.get() to return 404 on bad IDs"
    - "Beanie field requires alias= (not just serialization_alias=) for correct MongoDB field name storage"

key-files:
  created:
    - app/qso/service.py
    - app/qso/router.py
    - tests/test_qso_api.py
  modified:
    - app/qso/models.py
    - app/auth/dependencies.py
    - app/main.py

key-decisions:
  - "Beanie alias vs serialization_alias: alias= is required for Beanie to store MongoDB field names correctly; serialization_alias alone does not affect storage"
  - "Response serialization: _qso_to_dict() strips _id, converts PydanticObjectId to string, isoformats datetime to avoid FastAPI PydanticSerializationError"
  - "GET list date_to uses 2359 (23:59) for end-of-day inclusion when filtering by date range"
  - "PATCH recalculates qso_date_utc using existing document values for whichever of QSO_DATE/TIME_ON is not provided in the patch body"

patterns-established:
  - "Pattern: QSO ownership check — qso.operator_callsign != operator or qso.is_deleted → 404 (no information leakage)"
  - "Pattern: All raw $set dicts use MongoDB alias names: _deleted not is_deleted, _operator not operator_callsign"
  - "Pattern: ADIF passthrough via QSOCreateRequest extra=allow + merge body.model_dump() | body.model_extra"

# Metrics
duration: 12min
completed: 2026-04-03
---

# Phase 3 Plan 01: QSO REST API Summary

**FastAPI REST API at /api/qsos/ with JWT operator isolation, ADIF field passthrough, paginated list with filters, and soft-delete — backed by a fixed Beanie model that now correctly stores _operator/_deleted as MongoDB field names**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-03T11:31:47Z
- **Completed:** 2026-04-03T11:44:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- QSO REST API with 5 endpoints (POST, GET list, GET by-id, PATCH, DELETE/soft-delete) at /api/qsos/
- Service layer with parse_adif_datetime, build_qso_dict, get_qso_page (pagination + filters)
- All 23 QSO API tests pass: operator isolation, ADIF extra fields, pagination, filtering, protected field stripping, datetime recalculation
- Fixed pre-existing QSO model bug where `serialization_alias` alone didn't cause Beanie to use alias names for MongoDB storage

## Task Commits

Each task was committed atomically:

1. **Task 1: QSO service layer and REST API router** - `c398a01` (feat)
2. **Task 2: QSO API tests + bug fixes** - `9a0ac05` (feat)

**Plan metadata:** TBD (docs commit)

## Files Created/Modified
- `app/qso/service.py` - parse_adif_datetime, build_qso_dict, get_qso_page service functions
- `app/qso/router.py` - 5 QSO REST API endpoints with JWT operator isolation
- `app/qso/models.py` - Fixed alias= on operator_callsign and is_deleted fields
- `app/auth/dependencies.py` - Added get_current_operator_callsign_cookie for /log/ UI routes
- `app/main.py` - Include QSO router; extend exception handler for /log/ prefix
- `tests/test_qso_api.py` - 23 tests for all endpoints

## Decisions Made
- `alias=` (not `serialization_alias=`) is required for Beanie to store MongoDB field names correctly — Beanie's `_iter_model_items` uses `field_info.alias or key` when building the document dict for MongoDB
- Response serialization via custom `_qso_to_dict()` helper that pops `_id`, adds string `id`, and isoformats datetimes — necessary because FastAPI cannot serialize PydanticObjectId objects
- GET list `date_to` uses HHMM=2359 for end-of-day inclusion in date range filters

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed PydanticSerializationError on API response serialization**
- **Found during:** Task 2 (test_create_qso_success failing)
- **Issue:** `model_dump(by_alias=True)` includes `_id` as PydanticObjectId which FastAPI cannot serialize; also datetime objects need isoformat for JSON
- **Fix:** Updated `_qso_to_dict()` to pop `_id`, set string `id`, and isoformat `qso_date_utc`
- **Files modified:** app/qso/router.py
- **Verification:** test_create_qso_success passes
- **Committed in:** 9a0ac05

**2. [Rule 1 - Bug] Fixed QSO model: serialization_alias alone doesn't set MongoDB field names**
- **Found during:** Task 2 (list/filter/delete tests returning wrong results)
- **Issue:** Beanie stores documents using `field_info.alias or field_name`. With only `serialization_alias="_operator"` (no `alias`), Beanie stored the Python names `operator_callsign` and `is_deleted` in MongoDB. All queries using `{"_operator": ..., "_deleted": False}` hit non-existent fields and returned 0 results. Also caused `$set: {"_deleted": True}` to create a new field instead of updating the stored `is_deleted` field.
- **Fix:** Added `alias="_operator"` to `operator_callsign` field and `alias="_deleted"` to `is_deleted` field in QSO model (keeping `serialization_alias` for API responses)
- **Files modified:** app/qso/models.py
- **Verification:** 23/23 QSO API tests pass; test_qso_operator_field_in_mongodb, test_qso_deleted_field_in_mongodb, test_find_active_excludes_deleted all now pass
- **Committed in:** 9a0ac05
- **Side effect:** `test_qso_soft_delete_flag` in test_qso_schema.py (owned by phase 01-03, not modifiable) now fails because it uses `qso.set({"is_deleted": True})` which was only correct when the field was stored as `is_deleted`. With the alias fix, the MongoDB field is `_deleted` — the test should use `qso.update({"$set": {"_deleted": True}})`. The test file has an internal contradiction: it asserts `_deleted` must be in MongoDB (line 226) but uses `set({"is_deleted"})` to update it. Net result: 3 schema tests that were failing now pass; 1 schema test that relied on incorrect model behavior now fails.

---

**Total deviations:** 2 auto-fixed (both Rule 1 bugs)
**Impact on plan:** Both fixes essential for correctness. The model alias fix was a pre-existing bug affecting all QSO operations. No scope creep.

## Issues Encountered
- The pre-existing `test_qso_soft_delete_flag` test in `tests/test_qso_schema.py` (unmodifiable) has an internal contradiction: it documents that `_deleted` should be the MongoDB field name, but uses `qso.set({"is_deleted": True})` to test it. Fixing the model makes this test fail. Net impact: 3 previously-failing schema tests now pass; 1 schema test (with incorrect assertion mechanism) now fails.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- QSO REST API complete and tested — 03-02 (duplicate detection) can layer on top via `force=True` query param (already wired in POST endpoint)
- 03-03 (web form) can POST to /api/qsos/ directly — ADIF passthrough confirmed working
- 03-04 (log view) can use get_qso_page() service function and GET /api/qsos/ endpoint
- get_current_operator_callsign_cookie dependency ready for /log/ UI routes

---
*Phase: 03-qso-entry-log-view*
*Completed: 2026-04-03*

## Self-Check: PASSED

- app/qso/service.py: FOUND
- app/qso/router.py: FOUND
- tests/test_qso_api.py: FOUND
- commit c398a01: FOUND
- commit 9a0ac05: FOUND
