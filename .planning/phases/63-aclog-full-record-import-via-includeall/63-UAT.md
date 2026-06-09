---
status: complete
phase: 63-aclog-full-record-import-via-includeall
source:
  - 63-01-SUMMARY.md
started: 2026-06-08T19:20:10Z
updated: 2026-06-09T03:45:26Z
---

## Current Test

[testing complete]

## Tests

### 1. Full-Record Request After ACLog Save
expected: When ACLog sends an `ENTEREVENT` for a saved QSO, ollog keeps that event pending and immediately writes an ACLog full-record request on the same TCP connection: `<CMD><LIST><INCLUDEALL><VALUE>1</VALUE></CMD>`. The QSO is not ingested early while ollog is waiting for a matching full-record response.
result: pass

### 2. Matched Full Record Enriches Imported QSO
expected: When ACLog returns a matching `LIST`/`LISTRESPONSE` full-record payload for the pending QSO, ollog imports one QSO using the enriched record. Non-empty fields from the full record, such as frequency, reports, references, grids, state/county, and other ADIF-like tags, are preserved.
result: pass

### 3. ACLog Other Fields Are Preserved And Mapped
expected: ACLog `OTHER_1` through `OTHER_8` values from full-record or live-update data are preserved. If the operator has configured a Custom QSO Field for that slot, the value is saved under the configured ADIF name; otherwise it remains as `OTHER_N`.
result: pass

### 4. Fallback Keeps Existing ENTEREVENT Behavior
expected: If a full-record response is missing, nonmatching, or the bridge disconnects before enrichment completes, ollog still imports the original `ENTEREVENT` record with cached live fields such as `FREQ`, `RST_SENT`, `RST_RCVD`, and `OTHER_N` when available.
result: pass

### 5. Deterministic Coverage Exists For Parser And Bridge Flow
expected: The codebase includes deterministic tests for full-record parsing, merge precedence, correlation/mismatch behavior, outbound INCLUDEALL request handling, enriched ingestion, fallback ingestion, and Other field mapping/preservation.
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
