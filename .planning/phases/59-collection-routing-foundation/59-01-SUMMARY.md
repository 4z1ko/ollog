---
phase: 59
plan: 59-01
status: complete
completed: 2026-06-07
---

# Phase 59 Plan 01 Summary

## Objective

Create the shared foundation for username-routed QSO collections named exactly `<username>_qsos`, without migrating data or refactoring the full QSO workflow yet.

## Implemented

- Added `app/qso/collections.py` as the single collection-routing helper module.
- Added `qso_collection_name(username)` with exact `<username>_qsos` naming for safe usernames.
- Added strict username validation that rejects empty values, whitespace-padded values, separators, dots, `$`, null bytes, spaces, and non-string inputs.
- Added raw MongoDB collection access through the existing `app.database.get_client()` and configured MongoDB database name.
- Added convenience routing for `User`-like objects through their `username` attribute.
- Added per-user QSO index definitions mirroring the current shared `QSO` index intent.
- Added idempotent `create_indexes(...)` helpers for raw per-user QSO collections.
- Added focused unit tests for naming, invalid usernames, collection access, and index setup.

## Verification

- `.venv/bin/python -m pytest tests/test_qso_collections.py tests/test_qso_schema.py` — 40 passed, 16 skipped.
- `.venv/bin/python -m ruff check app/qso/collections.py tests/test_qso_collections.py` — passed.

## Notes

- `QSO.Settings.name` remains `qsos` in this phase so the existing Beanie model stays available as a validation/serialization shape.
- No production CRUD call sites were moved yet; that work remains assigned to Phase 61 after Phase 60 migration support exists.

