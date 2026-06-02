---
phase: 57-qso-rowhash-dedup-adif-review
plan: "01"
subsystem: qso
tags: [mongodb, deduplication, adif, rowhash]
requirements:
  - DEDUP-01
  - DEDUP-02
  - DEDUP-03
  - DEDUP-04
  - DEDUP-05
  - DEDUP-06
  - ADIF-REVIEW-01
  - ADIF-REVIEW-02
  - ADIF-REVIEW-03
  - ADIF-REVIEW-04
key_files:
  created:
    - app/hashing.py
    - app/qso/row_hash_migration.py
    - tests/test_hashing.py
    - tests/test_adif_duplicate_review.py
  modified:
    - app/main.py
    - app/qso/models.py
    - app/qso/router.py
    - app/qso/service.py
    - app/qso/ui_router.py
    - templates/log/import_report.html
    - tests/test_qso_schema.py
    - tests/test_watcher.py
metrics:
  tests_passed: 42
  completed_date: "2026-06-02"
---

# Phase 57 Plan 01 Summary

**One-liner:** Added canonical QSO `rowHash` deduplication, a unique MongoDB index/backfill path, explicit duplicate insert handling, soft-delete hash updates, and ADIF duplicate review with selectable import.

## Completed

- Added `app/hashing.py` with deterministic SHA-256 hashing over canonicalized document values.
- Added `rowHash` to the QSO model and configured a unique sparse MongoDB index.
- Added idempotent rowHash backfill/reporting in `app/qso/row_hash_migration.py` and startup wiring in `app/main.py`.
- Routed QSO insert paths through explicit duplicate handling instead of silent overwrite.
- Updated soft-delete and update flows so rowHash changes when effective values change.
- Updated ADIF import reporting so new records import by default and existing records appear in a checkbox review table.
- Added focused unit/integration coverage for hashing, MongoDB schema/index behavior, backfill safety, soft-delete hash updates, and ADIF duplicate review.

## Validation

- `.venv/bin/python -m pytest tests/test_adif_duplicate_review.py tests/test_hashing.py tests/test_qso_schema.py tests/test_watcher.py` -> 42 passed
- `.venv/bin/python -m ruff check app/hashing.py app/main.py app/qso/models.py app/qso/router.py app/qso/service.py app/qso/ui_router.py app/qso/row_hash_migration.py tests/test_adif_duplicate_review.py tests/test_hashing.py tests/test_qso_schema.py tests/test_watcher.py` -> passed
- `.venv/bin/python -m compileall app tests` -> passed

## Ship Notes

- Full pytest remains blocked by pre-existing Mongo fixture URI issues in older tests that still use `mongodb://localhost:27017` without `directConnection=true`, plus unrelated legacy failures previously observed.
- `gh` CLI is not installed in this environment, so PR creation cannot be completed from here.
