---
status: testing
phase: 69-core-flow-instrumentation-and-documentation
source:
  - .planning/phases/69-core-flow-instrumentation-and-documentation/69-01-SUMMARY.md
started: 2026-06-19T11:44:04Z
updated: 2026-06-19T21:39:01Z
---

## Current Test

number: 5
name: Application Logs Documentation Coverage
expected: |
  The admin Application Logs guide lists representative event names for lifecycle, QSO import, UDP, ACLog live/manual sync, auth/token, admin, and log-settings flows, and explains that `CALL` is contacted station, `MYCALL` or ACLog setup Call is local station, and `OPERATOR` is operator value.
awaiting: user response

## Tests

### 1. ADIF Import Completion Logging
expected: Importing an ADIF file records route-level internal application logs (`qso_import_started` and `qso_import_request_completed`) plus the shared service `qso_import_completed` log. The logs include the operator callsign and total/accepted/duplicate/error counts where relevant. They do not include raw ADIF file contents or full imported record payloads.
result: pass

### 2. Manual ACLog Sync Logging
expected: Running manual ACLog sync records internal application logs for sync start, records received, processed accepted/duplicate QSOs, skipped records, failures, and completion summary using `bridge_sync_*` event types with bridge and ACLog context.
result: pass

### 3. Auth And Token Log Safety
expected: Operator/OAuth login and API-token create/revoke actions emit safe internal logs. Logs include safe identifiers such as username, callsign, token id/name/prefix, and do not include passwords, plaintext tokens, token hashes, cookies, or authorization headers.
result: pass

### 4. UDP Callback Event Logging
expected: UDP protocol callbacks emit internal log events for datagram received, transport error, and transport closed while preserving existing UDP ingest/routing behavior.
result: pass

### 5. Application Logs Documentation Coverage
expected: The admin Application Logs guide lists representative event names for lifecycle, QSO import, UDP, ACLog live/manual sync, auth/token, admin, and log-settings flows, and explains that `CALL` is contacted station, `MYCALL` or ACLog setup Call is local station, and `OPERATOR` is operator value.
result: [pending]

### 6. Regression Verification
expected: Focused tests and checks pass: internal log/ACLog/UDP tests, token tests, Python compile check, MkDocs strict build, and `git diff --check`. Existing QSO import, duplicate, UDP, token, and ACLog sync behavior remains unchanged aside from failure-isolated logging.
result: [pending]

## Summary

total: 6
passed: 4
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps

- truth: "New application log rows displayed through the live Recent Logs stream render with the same message, metadata, and detail formatting as rows shown after page refresh."
  status: fixed
  reason: "User reported: the log messages are being displayed correctly only after page refresh"
  severity: major
  test: 2
  root_cause: "The live admin Logs table used a separate JavaScript row renderer while refreshed rows used the server `admin/log_row.html` template, allowing live rows to diverge from refreshed rows."
  artifacts:
    - path: "templates/admin/logs.html"
      issue: "SSE handler inserted rows from client-side HTML instead of the shared row template."
    - path: "app/admin/ui_router.py"
      issue: "No row partial endpoint existed for live events to reuse server row formatting."
  missing:
    - "Add an authenticated `/admin/ui/logs/{log_id}/row` partial endpoint."
    - "Have SSE live inserts fetch the server-rendered row by log id before inserting it."
    - "Add regression tests for server-rendered live row insertion."
  debug_session: ""
- truth: "Manual ACLog sync logs created by the operator/API service appear in the admin Recent Logs view without requiring a manual page refresh."
  status: fixed
  reason: "User reported: still no live log messages update for manual sync operation"
  severity: major
  test: 2
  root_cause: "Admin Logs SSE uses an in-memory queue per process. Manual ACLog sync logs are created by the operator/API process, while the admin Logs page SSE connection is served by the admin process, so those cross-process MongoDB-backed logs did not reach the EventSource stream."
  artifacts:
    - path: "templates/admin/logs.html"
      issue: "The page depended only on the in-process EventSource stream and had no polling fallback for logs written by another process."
  missing:
    - "Add a safe polling fallback that refreshes the first admin Logs page with current filters from MongoDB."
    - "Add regression checks that the polling fallback exists."
  debug_session: ""
- truth: "The near-live polling fallback does not collapse metadata or error detail sections the admin has opened."
  status: fixed
  reason: "User reported: the near-live polling fallback automatically folds any open metadata"
  severity: minor
  test: 2
  root_cause: "Polling refresh replaced the entire Logs table with new HTML, so browser `<details open>` state was discarded during the HTMX swap."
  artifacts:
    - path: "templates/admin/logs.html"
      issue: "Polling refresh did not capture and restore open metadata/error detail state."
    - path: "templates/admin/log_row.html"
      issue: "Rows/details lacked stable identifiers for restoring open detail state after refresh."
  missing:
    - "Include stable log row and detail-kind data attributes."
    - "Capture open detail keys before polling refresh and restore them after the table swap."
    - "Add regression checks for open detail preservation hooks."
  debug_session: ""
