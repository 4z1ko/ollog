---
phase: 01-foundation
plan: 03
subsystem: schema
tags: [beanie, pymongo, pydantic, mongodb, indexes, qso, soft-delete]

# Dependency graph
requires: ["01-01"]
provides:
  - QSO Beanie Document model with compound unique index
  - extra='allow' for arbitrary ADIF field storage
  - _operator and _deleted MongoDB field names via serialization_alias
  - find_active() class method excluding soft-deleted QSOs
  - from_mongo_dt() UTC re-attachment utility
  - database.py updated to register QSO in init_beanie
  - Integration tests for schema, indexes, field names, find_active, and from_mongo_dt
affects: [01-04, all phases]

# Tech tracking
tech-stack:
  patterns:
    - serialization_alias + populate_by_name=True for underscore-prefixed MongoDB fields
    - ConfigDict(extra="allow") for schema-less ADIF field passthrough
    - Beanie Settings.indexes with pymongo.IndexModel for compound unique index
    - find_active() classmethod using raw MongoDB field names in query dict
    - from_mongo_dt() utility to re-attach UTC tzinfo after every MongoDB read

key-files:
  created:
    - app/qso/models.py
    - app/utils.py
    - tests/test_qso_schema.py
  modified:
    - app/qso/__init__.py
    - app/database.py

key-decisions:
  - "_operator MongoDB field name enforced via serialization_alias='_operator' on operator_callsign field — no fallback to 'operator' without underscore (locked decision)"
  - "_deleted MongoDB field name enforced via serialization_alias='_deleted' on is_deleted field"
  - "find_active() queries using raw MongoDB field names {'_operator': operator, '_deleted': False} — not Python attribute names"
  - "compound unique index named 'operator_qso_unique' on {_operator, CALL, qso_date_utc, BAND, MODE} — prevents duplicate QSOs under concurrent access"
  - "from_mongo_dt() re-attaches UTC tzinfo only to naive datetimes — already-aware datetimes returned as-is"

patterns-established:
  - "MongoDB underscore fields: use Field(serialization_alias='_fieldname') + ConfigDict(populate_by_name=True)"
  - "Schema-less ADIF pass-through: ConfigDict(extra='allow') stores arbitrary uppercase field names"
  - "Default query pattern: always use find_active() not raw find() for operator QSO queries"
  - "Datetime safety: always wrap MongoDB datetime reads with from_mongo_dt()"

# Metrics
duration: ~10min
completed: 2026-04-03
---

# Phase 1 Plan 03: MongoDB QSO Schema Summary

**QSO Beanie Document model with compound unique index, ADIF extra fields, soft-delete, find_active() method, and UTC datetime utility**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-04-03
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- `app/qso/models.py`: QSO Document with `_operator`/`_deleted` via serialization_alias, `extra='allow'` for ADIF passthrough, compound unique index `operator_qso_unique`, `find_active()` classmethod
- `app/utils.py`: `from_mongo_dt()` utility re-attaches UTC tzinfo to naive datetimes from MongoDB
- `app/qso/__init__.py`: exports QSO
- `app/database.py`: registers QSO in init_beanie document_models list
- `tests/test_qso_schema.py`: 14 tests covering static model verification, MongoDB integration, field name aliasing, find_active(), and from_mongo_dt()

## Task Commits

- Task 1: `feat(01-03): add QSO Beanie document model with compound indexes`
- Task 2: `feat(01-03): add from_mongo_dt utility and find_active method`

NOTE: Git commits pending Bash access.

## Files Created/Modified

- `app/qso/models.py` — QSO Document with indexes, aliases, extra='allow', find_active()
- `app/utils.py` — from_mongo_dt() UTC re-attachment utility
- `app/qso/__init__.py` — exports QSO from models module
- `app/database.py` — QSO added to init_beanie document_models list
- `tests/test_qso_schema.py` — 14 integration + static tests

## Decisions Made

- Used `Field(serialization_alias="_operator")` + `ConfigDict(populate_by_name=True)` for the `_operator` MongoDB field name. This is the correct Pydantic v2 pattern for mapping Python attribute names to MongoDB field names with underscore prefixes.
- `find_active()` queries using raw MongoDB dict `{"_operator": operator, "_deleted": False}` — not Beanie field expressions — to ensure the query hits the correct indexed field names.
- Three indexes defined: `operator_qso_unique` (compound unique), `operator_idx`, `operator_active_idx` — all leading with `_operator` per locked architecture decision.

## Deviations from Plan

None. All locked decisions implemented exactly as specified.

## Issues Encountered

- Bash access denied in this execution environment — git commits and `python -c` verification could not run. Files verified correct via static code review (Read tool). Git commits must be run manually or when Bash access is restored.
- `tests/conftest.py` was already present (created by a prior 01-02 execution), so it was not modified — the instruction "do not modify conftest.py" was followed.

## User Setup Required

None beyond what 01-01 requires.

## Next Phase Readiness

- 01-04 (User/auth model) can proceed — QSO is registered in database.py and the document_models list has a comment noting where User should be added
- 01-02 integration tests (test_qso_schema.py) require live MongoDB at localhost:27017; tests skip automatically if MongoDB unavailable
- All compound index definitions are correct; indexes will be created by init_beanie on first startup

---
*Phase: 01-foundation*
*Completed: 2026-04-03*

## Self-Check: PASSED (static analysis)

All 5 files present on disk. Locked decisions verified:
- `_operator` field name: `serialization_alias="_operator"` on `operator_callsign` ✓
- `_deleted` field name: `serialization_alias="_deleted"` on `is_deleted` ✓
- Compound index name `operator_qso_unique` with 5 fields ✓
- `ConfigDict(extra="allow")` for ADIF passthrough ✓
- `find_active()` queries `{"_operator": operator, "_deleted": False}` ✓
- `from_mongo_dt()` handles naive/aware/None ✓
- `database.py` has `QSO` in document_models ✓
