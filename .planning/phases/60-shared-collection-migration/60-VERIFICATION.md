---
phase: 60
slug: shared-collection-migration
status: passed
verified: 2026-06-07
requirements_total: 6
requirements_passed: 6
critical_gaps: 0
non_critical_gaps: 0
---

# Phase 60 Verification - Shared Collection Migration

## Result

PASS - Phase 60 satisfies the planned migration requirements. The migration copies shared `qsos` documents into username-derived collections, preserves raw data, reports unsafe ownership cases, and can rerun safely.

## Automated Checks

- `.venv/bin/python -m pytest tests/test_qso_collection_migration.py tests/test_qso_collections.py` - 33 passed.
- `.venv/bin/python -m ruff check app/qso/collection_migration.py app/main.py tests/test_qso_collection_migration.py` - passed.
- `.venv/bin/python -m compileall app/qso/collection_migration.py tests/test_qso_collection_migration.py` - passed.

## Requirements

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| MIGR-01 | 60-01 | passed | Migration resolves `_operator` callsigns to exactly one user and writes raw docs into `<username>_qsos`. |
| MIGR-02 | 60-01 | passed | Insert-only upserts skip existing target `_id` documents without overwriting them. |
| MIGR-03 | 60-01 | passed | Missing, unknown, and ambiguous operators are reported and not silently copied. |
| MIGR-04 | 60-01 | passed | Focused tests assert preservation of `_id`, `_operator`, `_deleted`, `_created_at`, `rowHash`, extras, profile fields, and custom fields. |
| MIGR-05 | 60-01 | passed | Target index setup runs before target writes and is cached once per username per run. |
| VERIFY-02 | 60-01 | passed | Tests cover normal migration, idempotent rerun, unresolved/ambiguous ownership, soft deletes, raw field preservation, index order, dry run, and rowHash conflicts. |

## Gaps

None for the Phase 60 scope.

