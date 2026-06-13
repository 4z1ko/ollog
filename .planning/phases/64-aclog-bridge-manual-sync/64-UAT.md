---
status: complete
phase: 64-aclog-bridge-manual-sync
source:
  - 64-01-SUMMARY.md
started: 2026-06-12T21:50:00Z
updated: 2026-06-13T14:55:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Saved Bridge Sync Button
expected: Open Profile Settings. A saved ACLog bridge row shows a Sync button beside the remove action. The blank new bridge row does not show a Sync button.
result: pass

### 2. Manual Sync Imports Missing QSOs
expected: Pressing Sync on a saved bridge contacts that bridge, requests all ACLog records with `LIST INCLUDEALL`, and the inline result reports `Missing QSOs imported: N` for QSOs that were not already in ollog.
result: pass

### 3. Repeat Sync Skips Existing QSOs
expected: Pressing Sync again against the same ACLog bridge reports the same records as already present instead of inserting duplicate QSOs.
result: pass

### 4. Inline Error For Unreachable ACLog
expected: If the selected ACLog bridge is offline or unreachable, the Profile page shows `ACLog sync failed` plus the hint to confirm ACLog is running and the API port is reachable. The app stays on the Profile page.
result: pass

### 5. Existing Profile Save Still Works
expected: Saving Operator Details, Custom QSO Fields, and ACLog Bridges still updates the profile and shows the normal `Profile updated successfully` message.
result: pass

### 6. Existing Live Bridge Behavior Still Works
expected: Normal live ACLog bridge ingestion still works after this change; saved ACLog events continue to arrive in ollog without needing to press Sync.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
