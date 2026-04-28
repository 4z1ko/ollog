---
phase: 52
plan: 01
subsystem: backend/migration
tags: [migration, mongodb, time-on, startup, tdd]
dependency_graph:
  requires: []
  provides: [normalize_time_on, test_migration]
  affects: [app/main.py, tests/test_migration.py, tests/test_watcher.py]
tech_stack:
  added: []
  patterns: [idempotent-startup-migration, aggregation-pipeline-update, anchored-regex-filter]
key_files:
  created:
    - tests/test_migration.py
  modified:
    - app/main.py
    - tests/test_watcher.py
decisions:
  - "Aggregation pipeline [{\$set: {TIME_ON: {\$concat: [\"$TIME_ON\", \"00\"]}}}] used server-side — no Python loop"
  - "Anchored regex ^\\d{4}$ in filter prevents double-padding on repeated runs"
  - "directConnection=true added to migration_db fixture to reach replica set from outside Docker"
  - "app/qso/service.py untouched — DB-02 satisfied by existing parse_adif_datetime() + new test coverage"
metrics:
  duration: "~15 min"
  completed: "2026-04-28"
  tasks_completed: 2
  files_changed: 3
---

# Phase 52 Plan 01: TIME_ON DB Migration Summary

**One-liner:** Idempotent startup migration pads all 4-digit HHMM `TIME_ON` values to HHMM00 using anchored regex + aggregation pipeline; DB-02 confirmed via explicit test coverage of `parse_adif_datetime()`.

## What Was Built

### normalize_time_on() — app/main.py

New async function placed immediately after `backfill_created_at()` in `app/main.py`. Structural twin of the existing migration pattern.

- **Filter:** `{"TIME_ON": {"$regex": r"^\d{4}$"}}` — anchored regex matches only exactly 4-digit strings; 6-digit values are excluded (prevents double-padding)
- **Update:** Aggregation pipeline form `[{"$set": {"TIME_ON": {"$concat": ["$TIME_ON", "00"]}}}]` — server-side concatenation, single network round-trip
- **Logging:** Two-branch INFO log matching `backfill_created_at` style: `"TIME_ON migration: %d documents updated"` and `"TIME_ON migration: 0 documents — already up to date"` (em-dash)
- **Lifespan call site:** `await normalize_time_on()` added on line 74, immediately after `await backfill_created_at()`, before the change-stream watcher block

### tests/test_migration.py — new file

5 tests covering DB-01 and DB-02 requirements:

| Test | Requirement | Type |
|------|-------------|------|
| `test_normalize_time_on_pads_4digit` | DB-01 | Integration (MongoDB) |
| `test_normalize_time_on_idempotent` | DB-01 | Integration (MongoDB) |
| `test_normalize_time_on_skips_already_6digit` | DB-01 | Integration (MongoDB) |
| `test_parse_adif_datetime_accepts_hhmm` | DB-02 | Unit |
| `test_parse_adif_datetime_accepts_hhmmss` | DB-02 | Unit |

Fixture `migration_db` uses isolated database `ollog_migration_test`, drops on teardown. MongoDB integration tests guarded by `mongo_required` (`pytest.mark.skipif`).

### app/qso/service.py — NOT modified

`parse_adif_datetime()` already accepts both HHMM (len==4) and HHMMSS (len==6). DB-02 is satisfied by test coverage alone, no code change required.

## Test Results

```
tests/test_migration.py::test_normalize_time_on_pads_4digit PASSED
tests/test_migration.py::test_normalize_time_on_idempotent PASSED
tests/test_migration.py::test_normalize_time_on_skips_already_6digit PASSED
tests/test_migration.py::test_parse_adif_datetime_accepts_hhmm PASSED
tests/test_migration.py::test_parse_adif_datetime_accepts_hhmmss PASSED

5 passed in 2.00s
```

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 (RED) | `34df66e` | test(52-01): add failing tests for TIME_ON migration and parse_adif_datetime |
| Task 2 (GREEN) | `3e0a1c1` | feat(52-01): implement normalize_time_on() and wire into lifespan |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added directConnection=true to migration_db fixture**
- **Found during:** Task 2 test run
- **Issue:** `migration_db` fixture used `mongodb://localhost:27017` without `directConnection=true`. The MongoDB instance is a replica set with internal hostname `mongodb`; without directConnection, the driver discovers the replica set and tries `mongodb:27017` which is unreachable from outside Docker.
- **Fix:** Changed connection string to `mongodb://localhost:27017/?directConnection=true` — matching the existing pattern used in `tests/conftest.py`.
- **Files modified:** `tests/test_migration.py`
- **Commit:** `3e0a1c1`

**2. [Rule 1 - Bug] Added normalize_time_on to lifespan mock in test_watcher.py**
- **Found during:** Task 2 full test suite run
- **Issue:** `test_watcher_task_stored_in_app_state` mocked all startup functions in the lifespan but did not mock the new `normalize_time_on()`. The test invokes `lifespan()` directly without Beanie initialization, causing `CollectionWasNotInitialized` error in `normalize_time_on()`.
- **Fix:** Added `patch.object(_main, "normalize_time_on", new=AsyncMock())` to the context manager patch list in the test.
- **Files modified:** `tests/test_watcher.py`
- **Commit:** `3e0a1c1`

## TDD Gate Compliance

- RED gate: `test(52-01)` commit `34df66e` — file created with ImportError on collection (normalize_time_on not yet defined)
- GREEN gate: `feat(52-01)` commit `3e0a1c1` — all 5 tests pass

## Self-Check: PASSED

| Item | Status |
|------|--------|
| `app/main.py` exists | FOUND |
| `tests/test_migration.py` exists | FOUND |
| `tests/test_watcher.py` exists | FOUND |
| `.planning/phases/52-time-on-db-migration/52-01-SUMMARY.md` exists | FOUND |
| Commit `34df66e` (RED) exists | FOUND |
| Commit `3e0a1c1` (GREEN + fix) exists | FOUND |
| `normalize_time_on` defined in `app/main.py` | 1 definition |
| `app/qso/service.py` unchanged | confirmed |
