---
status: complete
phase: 66-aclog-operator-identity-routing
source:
  - .planning/phases/66-aclog-operator-identity-routing/66-01-SUMMARY.md
started: 2026-06-16T20:00:00Z
updated: 2026-06-16T20:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. ACLog Operator Identity Detection
expected: |
  ACLog full-record data with `OPERATOR` is normalized by trimming and uppercasing,
  matching values are accepted, blank or missing values are treated as missing, and
  different values are treated as unmatched.
result: pass
evidence: |
  `.venv/bin/python -m pytest tests/test_aclog_identity.py tests/test_aclog_client.py tests/test_profile_ui.py`
  passed the identity helper coverage, including matched, blank, missing, unmatched,
  and station-callsign safety cases.

### 2. Manual Sync Filters Shared Remote Records
expected: |
  Manual ACLog sync imports only records whose ACLog `OPERATOR` matches the signed-in
  ollog operator, counts duplicate matching records as already present, and reports
  missing or unmatched operator records without importing them.
result: pass
evidence: |
  `tests/test_aclog_client.py::test_manual_sync_filters_missing_and_unmatched_operator_records`
  passed. The fixture included matching, duplicate matching, missing-operator, and
  unmatched-operator records; only the matching records reached `ingest_qso_record`.

### 3. Live Bridge Blocks Identity-Less Fallback Imports
expected: |
  Live ACLog bridge ingestion imports a matched enriched full record, skips unmatched
  full records, and does not import the base `ENTEREVENT` record when no matching
  full record with operator identity is available.
result: pass
evidence: |
  `tests/test_aclog_client.py` passed the live bridge cases for matched full-record
  identity, unmatched full-record identity, and full-record mismatch with no
  `ENTEREVENT` fallback import.

### 4. Profile Sync Report Shows Operator Filter Counts
expected: |
  The Profile Settings sync result keeps existing received/imported/already-present/error
  counts and also shows separate Missing operator and Unmatched operator counts.
result: pass
evidence: |
  `tests/test_profile_ui.py::test_profile_aclog_sync_saved_bridge_renders_report`
  passed in the non-Mongo rendering path and confirmed the report includes
  `Missing operator: 1` and `Unmatched operator: 1`.

### 5. Matching Records Preserve Existing ACLog Import Behavior
expected: |
  Matching ACLog records still preserve full-record fields, Other/custom-field mapping
  remains downstream of the identity gate, duplicate handling remains intact, and writes
  continue through the existing per-user QSO ingest path.
result: pass
evidence: |
  Focused tests passed for enriched full-record preservation, duplicate counting, timeout
  behavior, and the existing ingest path. Source inspection confirms identity checks run
  before `_map_other_slots_to_custom_fields()` and before `ingest_qso_record()`.

### 6. Operator Documentation Explains Shared ACLog Behavior
expected: |
  Operator documentation explains how shared ACLog remote computers are handled, that
  `OPERATOR` is the required record-level import gate, and why missing or unmatched
  operator identity is skipped.
result: pass
evidence: |
  `docs/operator-guide/aclog-bridges.md` contains the Shared ACLog Computers section,
  the sync report count descriptions, and troubleshooting guidance for missing or
  unmatched `OPERATOR` values.

### 7. Real Shared ACLog Remote Smoke Test
expected: |
  With two real ollog operators pointing saved bridges at the same live ACLog API endpoint,
  each operator only imports ACLog records whose record-level `OPERATOR` matches their
  own callsign, and missing/unmatched records are skipped and counted.
result: skipped
reason: |
  This environment does not have a live ACLog host or two real operator profiles connected
  to a shared remote ACLog database. The behavior is covered by deterministic simulated
  ACLog API tests; a live shack setup can run this as an extra confidence smoke test.

## Summary

total: 7
passed: 6
issues: 0
pending: 0
skipped: 1
blocked: 0

## Gaps

[]
