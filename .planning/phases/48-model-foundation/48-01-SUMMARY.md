---
phase: 48-model-foundation
plan: "01"
subsystem: qso-model
tags: [model, migration, index, security, beanie]
dependency_graph:
  requires: []
  provides: [_created_at field on QSO, operator_created_at_idx index, backfill migration]
  affects: [app/qso/models.py, app/qso/router.py, app/qso/ui_router.py, app/adif/router.py, app/main.py]
tech_stack:
  added: []
  patterns: [Beanie default_factory for immutable insert timestamps, bulk_write backfill migration, model_construct() in unit tests requiring no DB init]
key_files:
  created: []
  modified:
    - app/qso/models.py
    - app/qso/router.py
    - app/qso/ui_router.py
    - app/adif/router.py
    - app/main.py
    - tests/test_qso_schema.py
    - tests/test_watcher.py
decisions:
  - "Used model_construct() in test_qso_created_at_default_factory because Beanie's __init__ calls get_pymongo_collection() requiring DB init in this version — established pattern per key decisions"
  - "Normalized datetime comparison to naive UTC in backfill test because MongoDB test client (tz_aware=False) returns naive datetimes while ObjectId.generation_time returns FixedOffset-aware datetimes"
  - "Patched backfill_created_at in test_watcher.py lifespan mock test (Rule 1 fix) — new lifespan call broke pre-existing watcher test that mocked init_db but not backfill"
metrics:
  duration: ~25 minutes
  completed: 2026-04-22
  tasks_completed: 3
  files_changed: 7
requirements: [TS-01, TS-02, TS-03]
---

# Phase 48 Plan 01: _created_at Field, Index, and Backfill Summary

**One-liner:** Added `_created_at` UTC timestamp field to QSO model with Beanie `default_factory`, compound index `operator_created_at_idx`, PATCH mutation protection in both handlers, API/ADIF exclusion, and idempotent startup backfill from ObjectId timestamps.

## What Was Built

All four insert paths (REST API, UI form, UDP datagram, ADIF import) now automatically stamp every QSO document with `_created_at` at construction time via Pydantic's `default_factory`. No service-layer changes were needed. The field is protected from mutation and hidden from API consumers and ADIF exports.

### Files Modified

**app/qso/models.py**
- Added `timezone` to `datetime` import
- Added `created_at: datetime` field with `alias="_created_at"`, `serialization_alias="_created_at"`, `default_factory=lambda: datetime.now(timezone.utc)`
- Added 4th `IndexModel` for `(_operator ASC, _created_at DESC)` named `operator_created_at_idx`

**app/qso/router.py**
- `_qso_to_dict`: added `d.pop("_created_at", None)` after `d.pop("_id", None)` (D-06)
- PATCH handler: extended protected fields tuple with `"_created_at", "created_at"` (D-03)

**app/qso/ui_router.py**
- PATCH handler: extended protected fields tuple with `"_created_at", "created_at"` (D-03)

**app/adif/router.py**
- `_SKIP_FIELDS`: added `"_created_at"` (D-07)

**app/main.py**
- Added `from datetime import datetime, timezone`, `from bson import ObjectId`, `from pymongo import UpdateOne` imports
- Added `async def backfill_created_at()` function using cursor iteration + `bulk_write` with `UpdateOne` ops, reading `ObjectId.generation_time.replace(tzinfo=timezone.utc)` per document
- Wired `await backfill_created_at()` in `lifespan` after `await _bootstrap_admin()`

**tests/test_qso_schema.py**
- Updated `test_qso_has_three_indexes` → `test_qso_has_four_indexes` (assert == 4)
- Added `test_qso_created_at_field_has_serialization_alias` (static)
- Added `test_qso_created_at_default_factory` (static, using `model_construct()`)
- Added `test_created_at_in_mongodb` (integration)
- Added `test_operator_created_at_index_exists` (integration)
- Added `test_patch_does_not_overwrite_created_at` (integration)
- Added `test_backfill_stamps_missing_created_at` (integration)
- Added `test_backfill_is_idempotent` (integration)

**tests/test_watcher.py**
- Added `patch.object(_main, "backfill_created_at", new=AsyncMock())` to lifespan mock test (Rule 1 regression fix)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 14bfc3b | feat(48-01): add _created_at field and compound index to QSO model |
| 2 | 13e3b08 | feat(48-01): protect _created_at from mutation and exclude from API/ADIF output |
| 3 | 21a845e | feat(48-01): add startup backfill migration and integration tests |

## Requirements Satisfied

| Req ID | Description | Verified |
|--------|-------------|---------|
| TS-01 | QSO records stamped with `_created_at` on insert across all four paths | Yes — default_factory fires for every QSO(**kwargs) construction |
| TS-02 | `_created_at` stripped from all PATCH handlers, excluded from API responses and ADIF exports | Yes — both PATCH handlers, _qso_to_dict pop, _SKIP_FIELDS |
| TS-03 | MongoDB compound index `operator_created_at_idx` declared in Settings.indexes | Yes — 4th IndexModel added, verified by test_operator_created_at_index_exists |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_qso_created_at_default_factory to use model_construct()**
- **Found during:** Task 1 verification
- **Issue:** Plan's test called `QSO(operator_callsign="W1AW", ...)` directly, but this version of Beanie calls `get_pymongo_collection()` in `__init__`, raising `CollectionWasNotInitialized` when Beanie has not been initialized. This is a static test that shouldn't need DB.
- **Fix:** Used `QSO.model_construct(...)` + explicit `default_factory()` call, following the established project pattern documented in key decisions ("User.model_construct() in stamping unit tests").
- **Files modified:** tests/test_qso_schema.py
- **Commit:** 21a845e

**2. [Rule 1 - Bug] Fixed timezone comparison in test_backfill_stamps_missing_created_at**
- **Found during:** Task 3 verification
- **Issue:** MongoDB test client uses `tz_aware=False`, so stored datetimes come back as naive. `ObjectId.generation_time` returns a `FixedOffset`-aware datetime. Direct equality comparison failed.
- **Fix:** Added `_to_naive_utc()` helper to normalize both sides to naive UTC before comparison.
- **Files modified:** tests/test_qso_schema.py
- **Commit:** 21a845e

**3. [Rule 1 - Bug] Fixed test_watcher_task_stored_in_app_state regression**
- **Found during:** Task 3 full-suite verification
- **Issue:** Adding `await backfill_created_at()` to lifespan broke the existing watcher test that mocks `init_db` and `_bootstrap_admin` but not `backfill_created_at`. `QSO.get_pymongo_collection()` raised `CollectionWasNotInitialized` because `init_db` was mocked.
- **Fix:** Added `patch.object(_main, "backfill_created_at", new=AsyncMock())` to the test's mock context.
- **Files modified:** tests/test_watcher.py
- **Commit:** 21a845e

### Pre-existing Failures (Out of Scope)

The following test failures were confirmed pre-existing before any changes and are not caused by this plan:

- `tests/test_qso_schema.py::test_qso_duplicate_rejected` — expects `DuplicateKeyError` on a non-unique index (per the 03-02 decision, unique=True was removed)
- `tests/test_qso_schema.py::test_qso_soft_delete_flag` — Beanie `.set()` behavior change; pre-existing failure unrelated to this plan
- `tests/test_qso_api_key.py::test_admin_endpoint_rejects_api_key` — pre-existing, unrelated
- `tests/test_udp_pipeline.py::test_handle_datagram_operator_from_config_not_datagram` — pre-existing, unrelated

## Known Stubs

None — all changes are complete implementations, no placeholder values.

## Threat Surface

All threat mitigations from the plan's STRIDE register were applied:

| Threat ID | Mitigation Applied |
|-----------|-------------------|
| T-48-01 | `_created_at`/`created_at` stripped from REST PATCH body in app/qso/router.py |
| T-48-02 | `_created_at`/`created_at` stripped from UI PATCH body in app/qso/ui_router.py |
| T-48-03 | `d.pop("_created_at", None)` in `_qso_to_dict` prevents API disclosure |
| T-48-04 | `"_created_at"` added to `_SKIP_FIELDS` in app/adif/router.py |

## Self-Check: PASSED

All files verified present. All commits (14bfc3b, 13e3b08, 21a845e) verified in git log. No unexpected file deletions.
