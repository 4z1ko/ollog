---
phase: 60
plan: 60-01
status: complete
completed: 2026-06-07
---

# Phase 60 Plan 01 Summary

## Objective

Add a copy-only, idempotent migration from the legacy shared `qsos` collection into username-derived per-user collections named `<username>_qsos`.

## Implemented

- Added `app/qso/collection_migration.py` with a callable migration function and CLI entry point.
- Migration reads raw documents from the shared `qsos` collection.
- Migration resolves `_operator` callsign to exactly one user and targets that user's `<username>_qsos` collection.
- Missing, unknown, and ambiguous callsign ownership is reported instead of guessed.
- Target per-user indexes are created before writes.
- Target writes are insert-only upserts, preserving existing target documents on reruns.
- Raw QSO document data is preserved, including `_id`, `_operator`, `_deleted`, `_created_at`, `rowHash`, ADIF extras, profile fields, and custom fields.
- Duplicate-key conflicts such as rowHash collisions are reported without overwriting or deleting data.
- Added `--dry-run` and `--report` support for explicit operator-run reports.
- Wired startup to run the idempotent migration after rowHash backfill.
- Added focused fake-collection tests that do not require live MongoDB.

## Verification

- `.venv/bin/python -m pytest tests/test_qso_collection_migration.py tests/test_qso_collections.py` - 33 passed.
- `.venv/bin/python -m ruff check app/qso/collection_migration.py app/main.py tests/test_qso_collection_migration.py` - passed.
- `.venv/bin/python -m compileall app/qso/collection_migration.py tests/test_qso_collection_migration.py` - passed.

## Notes

- The shared `qsos` collection is left intact for Phase 61, where runtime CRUD paths will be moved to per-user collections.
- `User.callsign` is not unique in the current model, so duplicate callsign matches are intentionally treated as ambiguous.

