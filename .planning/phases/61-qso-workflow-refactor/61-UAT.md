---
status: complete
phase: 61-qso-workflow-refactor
source:
  - 61-01-SUMMARY.md
started: 2026-06-08T04:18:14Z
updated: 2026-06-08T04:22:27Z
---

## Current Test

[testing complete]

## Tests

### 1. REST and API Token QSO Routing
expected: REST QSO list/create/read/update/delete requests keep the same public API behavior, while storage is routed from the authenticated JWT or API-token user to that user's `<username>_qsos` collection. Guessing another user's QSO ID should not expose that record through this user's route.
result: pass

### 2. Browser QSO Workflow Routing
expected: Browser QSO entry, log view, inline view/edit/update/delete, pagination, filtering, sorting, custom-field defaults, import duplicate review, export, and operator clear-log continue to behave as before while using the logged-in user's `<username>_qsos` collection.
result: pass

### 3. ADIF Import and Export Routing
expected: REST and browser ADIF import/export workflows use the authenticated user's collection for duplicate checks, inserts, existing-QSO review, and exported records, while preserving the existing ADIF report and stream formats.
result: pass

### 4. UDP and ACLog Resolved User Routing
expected: UDP and ACLog QSO ingestion write to the resolved user's collection from APP_OLLOG_TOKEN, OPERATOR override, or configured fallback user, and APP_OLLOG_TOKEN is not stored in QSO documents.
result: pass

### 5. Duplicate Scope and Preserved QSO Fields
expected: Duplicate detection and rowHash conflicts are scoped to one user's collection, the same effective QSO can exist in another user's collection, and `_operator` remains stored as the callsign on every QSO document.
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
