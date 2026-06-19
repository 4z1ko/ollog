---
status: testing
phase: 69-core-flow-instrumentation-and-documentation
source:
  - .planning/phases/69-core-flow-instrumentation-and-documentation/69-01-SUMMARY.md
started: 2026-06-19T11:44:04Z
updated: 2026-06-19T21:09:24Z
---

## Current Test

number: 1
name: ADIF Import Completion Logging
expected: |
  Importing an ADIF file records route-level internal application logs (`qso_import_started` and `qso_import_request_completed`) plus the shared service `qso_import_completed` log. The logs include the operator callsign and total/accepted/duplicate/error counts where relevant. They do not include raw ADIF file contents or full imported record payloads.
awaiting: user response

## Tests

### 1. ADIF Import Completion Logging
expected: Importing an ADIF file records route-level internal application logs (`qso_import_started` and `qso_import_request_completed`) plus the shared service `qso_import_completed` log. The logs include the operator callsign and total/accepted/duplicate/error counts where relevant. They do not include raw ADIF file contents or full imported record payloads.
result: [pending]

### 2. Manual ACLog Sync Logging
expected: Running manual ACLog sync records internal application logs for sync start, records received, processed accepted/duplicate QSOs, skipped records, failures, and completion summary using `bridge_sync_*` event types with bridge and ACLog context.
result: [pending]

### 3. Auth And Token Log Safety
expected: Operator/OAuth login and API-token create/revoke actions emit safe internal logs. Logs include safe identifiers such as username, callsign, token id/name/prefix, and do not include passwords, plaintext tokens, token hashes, cookies, or authorization headers.
result: [pending]

### 4. UDP Callback Event Logging
expected: UDP protocol callbacks emit internal log events for datagram received, transport error, and transport closed while preserving existing UDP ingest/routing behavior.
result: [pending]

### 5. Application Logs Documentation Coverage
expected: The admin Application Logs guide lists representative event names for lifecycle, QSO import, UDP, ACLog live/manual sync, auth/token, admin, and log-settings flows, and explains that `CALL` is contacted station, `MYCALL` or ACLog setup Call is local station, and `OPERATOR` is operator value.
result: [pending]

### 6. Regression Verification
expected: Focused tests and checks pass: internal log/ACLog/UDP tests, token tests, Python compile check, MkDocs strict build, and `git diff --check`. Existing QSO import, duplicate, UDP, token, and ACLog sync behavior remains unchanged aside from failure-isolated logging.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps

None.
