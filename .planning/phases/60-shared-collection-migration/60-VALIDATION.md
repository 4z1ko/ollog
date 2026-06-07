# Phase 60 Validation Strategy

**Date:** 2026-06-07
**Phase:** 60 - Shared Collection Migration

## Scope Under Test

Phase 60 verifies data migration behavior only:

- source `qsos` documents are copied into username-derived target collections
- user resolution is safe and reportable
- raw document fields are preserved
- repeated runs are idempotent
- target indexes exist before writes
- startup/CLI entry points are wired safely

Runtime QSO CRUD routing remains Phase 61.

## Nyquist Sample Points

1. **Normal migration**
   - Shared QSOs for two known callsigns land in the corresponding `<username>_qsos` collections.

2. **Idempotent rerun**
   - Rerunning migration does not duplicate documents.
   - Existing target documents with the same `_id` are not overwritten.

3. **Unresolved rows**
   - Missing/blank/unknown `_operator` rows are reported and left out of target collections.

4. **Ambiguous rows**
   - Multiple users with the same callsign produce an ambiguity report and no guessed target write.

5. **Preservation**
   - `_id`, `_operator`, `_deleted`, `_created_at`, `rowHash`, ADIF extras, profile-stamped fields, and custom fields survive byte-for-byte where MongoDB allows.

6. **Index order**
   - Target per-user indexes are created before write operations.

7. **Operational entry points**
   - CLI produces JSON output/report.
   - Startup integration is idempotent and logs a compact summary.

## Verification Commands

```bash
.venv/bin/python -m pytest tests/test_qso_collection_migration.py tests/test_qso_collections.py
.venv/bin/python -m ruff check app/qso/collection_migration.py app/main.py tests/test_qso_collection_migration.py
.venv/bin/python -m compileall app/qso/collection_migration.py tests/test_qso_collection_migration.py
```

## Acceptance

Phase 60 passes when the migration can be rerun safely, preserves legacy QSO data, reports every row it cannot safely route, and leaves existing shared-collection behavior available for Phase 61 refactoring.

