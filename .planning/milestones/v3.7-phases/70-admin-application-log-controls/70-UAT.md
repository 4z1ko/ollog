---
status: complete
phase: 70-admin-application-log-controls
source:
  - .planning/phases/70-admin-application-log-controls/70-01-SUMMARY.md
started: 2026-06-20T10:10:00Z
updated: 2026-06-20T10:16:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Recent Logs Header Controls
expected: Open Admin > Logs. The Recent Logs card header shows the LIVE status badge, a Pause button, and a Clear Log Messages button. The controls sit in the Recent Logs header, wrap cleanly if space is narrow, and the rest of the log table/filter UI remains unchanged.
result: pass

### 2. Pause Suppresses Automatic Live Updates
expected: Click Pause. The badge changes to PAUSED and the button changes to Start. New log events do not automatically insert rows and the near-live polling fallback does not refresh the table, but Apply Filters, Reset, Previous, and Next still refresh intentionally.
result: pass

### 3. Start Resumes And Reconciles Logs
expected: Click Start. The badge returns to LIVE, the button returns to Pause, the table immediately refreshes/reconciles missed recent rows without a full page reload, and live/polling updates continue afterward.
result: pass

### 4. Clear Log Messages Confirmation
expected: Click Clear Log Messages. A confirmation modal opens before deletion and says: "Clear all application log messages from the database. QSO records, users, and log settings are not affected." Cancel closes the modal without clearing logs.
result: pass

### 5. Confirmed Clear Preserves Unrelated Data
expected: Confirm Clear Log Messages. Existing application log records are removed, a fresh "Application logs cleared" audit message appears when audit logging succeeds, future logs can appear again, and QSO records, users, API tokens, backups, log settings, retention, filters, and pagination behavior are not affected.
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
