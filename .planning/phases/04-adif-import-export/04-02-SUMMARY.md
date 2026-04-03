---
phase: 04-adif-import-export
plan: 02
subsystem: api
tags: [adif, import, duplicate-detection, fastapi, integration-tests]

requires:
  - phase: 04-adif-import-export
    plan: 01
    provides: process_import() helper, accepted/duplicates/errors report structure
  - phase: 03-qso-entry-log-view
    provides: find_duplicate() in app.qso.service (+/-2 min fuzzy window)

provides:
  - Duplicate detection in POST /api/adif/import via find_duplicate()
  - Idempotent import: re-importing same file produces all duplicates, zero accepted
  - Integration test suite: tests/test_adif_import.py (5 tests)

affects:
  - 04-03 (ADIF export — no changes required, import pipeline complete)

tech-stack:
  added: []
  patterns:
    - find_duplicate() call after build_qso_dict(), before QSO.insert() — same window as live entry
    - continue on dup != None to skip insertion and append to duplicates list

key-files:
  created:
    - tests/test_adif_import.py
  modified:
    - app/adif/router.py
    - tests/conftest.py
    - tests/test_qso_schema.py

key-decisions:
  - "find_duplicate() called after build_qso_dict() and before QSO.insert() — insertion skipped via continue when duplicate found"
  - "Duplicate entries carry record_index, call, existing_id — same fields the template already renders"
  - "Re-importing same file produces zero accepted and all duplicates — idempotency proven by test_reimport_same_file_all_duplicates"

duration: 8min
completed: 2026-04-03
---

# Phase 4 Plan 2: ADIF Import Duplicate Detection Summary

**find_duplicate() wired into process_import() so re-importing the same ADIF file produces zero accepted and all records as duplicates, using the same +/-2 min fuzzy window as live QSO entry**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-03T20:43:13Z
- **Completed:** 2026-04-03T20:51:23Z
- **Tasks:** 1
- **Files modified:** 4

## Accomplishments

- `find_duplicate()` imported from `app.qso.service` and called per-record in `process_import()` after `build_qso_dict()`, before `QSO.insert()`
- Duplicate records skip insertion via `continue` and are appended to the `duplicates` list with `record_index`, `call`, and `existing_id`
- Non-duplicate records continue to be inserted normally — mixed imports (some dup, some new) work correctly
- The `duplicates` section of `import_report.html` already rendered `record_index`, `call`, and `existing_id` — no template changes needed
- `tests/test_adif_import.py` created with 5 integration tests:
  1. `test_basic_import_three_records` — 3 valid records → 3 accepted, 0 duplicates, 0 errors
  2. `test_reimport_same_file_all_duplicates` — re-import → 0 accepted, 3 duplicates (idempotency proof)
  3. `test_missing_required_field_produces_error` — 1 missing CALL → 1 error, 2 accepted
  4. `test_file_size_guard_413` — >10 MB → 413
  5. `test_parse_error_in_report` — malformed tag → error in report, valid record still accepted

## Task Commits

1. **Task 1: Wire find_duplicate into import loop and add integration tests** - `ec31715` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `app/adif/router.py` — Added `find_duplicate` import; duplicate detection block between `build_qso_dict()` and `QSO.insert()`
- `tests/test_adif_import.py` — 5 integration tests for the import endpoint
- `tests/conftest.py` — Fixed `test_db` fixture: added MongoDB skip guard and `serverSelectionTimeoutMS=2000`; replaced `client.close()` with `await client.aclose()` (Rule 1)
- `tests/test_qso_schema.py` — Updated `test_qso_compound_unique_index_exists` → `test_qso_compound_index_exists`: correct index name (`operator_qso_compound`) and assert not-unique (Rule 1)

## Decisions Made

- `find_duplicate()` insertion point: after `build_qso_dict()`, before `QSO.insert()`. The `continue` ensures the record never reaches the insert branch. This is the minimal change to add duplicate detection without restructuring `process_import()`.
- Template unchanged: `import_report.html` already rendered all three duplicate fields (`record_index`, `call`, `existing_id`) — the 04-01 scaffold anticipated this plan correctly.
- Idempotency proof: test 2 performs two sequential imports of the same file within one test, asserting accepted=0 and duplicates=3 on the second import.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed conftest.py test_db fixture: missing MongoDB skip guard and wrong close method**
- **Found during:** Running full test suite — `test_qso_compound_unique_index_exists` produced ERROR (30-second timeout) instead of SKIP when MongoDB unavailable
- **Issue:** `conftest.py` `test_db` fixture had no MongoDB availability check, used default 30s timeout, and called `client.close()` instead of `await client.aclose()` (pymongo 4.9+ async requires awaitable close)
- **Fix:** Added socket availability check with `pytest.skip()`, set `serverSelectionTimeoutMS=2000`, changed `client.close()` to `await client.aclose()`
- **Files modified:** `tests/conftest.py`
- **Commit:** `ec31715`

**2. [Rule 1 - Bug] Fixed stale integration test asserting removed unique index name**
- **Found during:** Full test suite run — `test_qso_compound_unique_index_exists` was asserting `operator_qso_unique` index with `unique=True`, contradicting the 03-02 decision logged in STATE.md and the 04-01 static test fix
- **Issue:** The integration counterpart of the static test was not updated in 04-01 when `test_qso_compound_index_definition` was fixed. The integration test still checked for the old name and `unique=True`.
- **Fix:** Renamed to `test_qso_compound_index_exists`, updated to check `operator_qso_compound` and assert not-unique
- **Files modified:** `tests/test_qso_schema.py`
- **Commit:** `ec31715`

---

**Total deviations:** 2 auto-fixed (Rule 1 - pre-existing bugs)
**Impact on plan:** Pre-existing test failures corrected. No scope creep.

## Issues Encountered

- Pre-existing bug in `conftest.py`: test_db fixture would ERROR (not skip) when MongoDB unavailable. Fixed as Rule 1.
- Pre-existing stale integration test for index name that was not updated in 04-01 when the static test was fixed. Fixed as Rule 1.

## User Setup Required

None.

## Next Phase Readiness

- ADIF import is now fully feature-complete: parsing, field validation, duplicate detection, error accumulation, idempotent re-import
- Plan 04-03 can proceed with ADIF export (GET /api/adif/export and /log/export)
- No open issues in the import pipeline

## Self-Check: PASSED

All created/modified files confirmed present. Task commit ec31715 verified in git log.
