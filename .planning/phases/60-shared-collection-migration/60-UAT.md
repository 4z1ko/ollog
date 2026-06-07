---
status: complete
phase: 60-shared-collection-migration
source:
  - 60-01-SUMMARY.md
started: 2026-06-07T00:00:00Z
updated: 2026-06-07T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Copy Shared QSOs To User Collections
expected: The migration copies legacy documents from shared `qsos` into the correct `<username>_qsos` collection by resolving `_operator` callsign to exactly one user.
result: pass

### 2. Idempotent Reruns
expected: Rerunning the migration does not duplicate documents and does not overwrite an existing target document with the same `_id`.
result: pass

### 3. Unsafe Ownership Reporting
expected: Missing, unknown, duplicate, or ambiguous `_operator` ownership is reported and not silently copied into a guessed collection.
result: pass

### 4. Raw QSO Data Preservation
expected: Migrated documents preserve `_id`, `_operator`, `_deleted`, `_created_at`, `rowHash`, ADIF extras, profile-stamped fields, and custom fields.
result: pass

### 5. Index And Operational Wiring
expected: Target collection indexes are initialized before writes, dry-run/report CLI support exists, and startup runs the idempotent migration after rowHash backfill without deleting the shared `qsos` collection.
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None.
