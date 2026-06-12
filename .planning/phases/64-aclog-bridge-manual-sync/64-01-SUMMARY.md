# Phase 64 Plan 01 Summary: ACLog Bridge Manual Sync

**Completed:** 2026-06-12
**Status:** Implementation complete; UAT pending

## Delivered

- Added a manual ACLog sync helper that sends `<CMD><LIST><INCLUDEALL></CMD>` to a saved bridge, parses all returned full-record QSOs, and imports only addable records.
- Preserved the existing live ACLog bridge enrichment flow and its `<VALUE>5</VALUE>` recent-record request.
- Routed manual sync writes through the logged-in user's username-derived QSO collection using existing QSO ingest, duplicate, rowHash, and custom Other-field mapping behavior.
- Added an authenticated Profile Settings route for saved bridge IDs only, returning HTMX-friendly HTTP 200 fragments for both success and errors.
- Added a saved-row-only Sync button beside configured ACLog bridges; the blank `new-0` row has no Sync action.
- Added a compact sync report fragment with received, missing imported, already-present, error, and example rejection counts.
- Updated operator documentation for manual sync behavior and repeat-sync duplicate handling.

## Code Touchpoints

- `app/aclog/sync.py`
- `app/aclog/parser.py`
- `app/qso/ui_router.py`
- `templates/log/profile.html`
- `templates/log/aclog_sync_result.html`
- `static/css/output.css`
- `tests/test_aclog_client.py`
- `tests/test_profile_ui.py`
- `docs/operator-guide/aclog-bridges.md`

## Notes

- Manual sync uses a fixed timeout and returns a failure report rather than surfacing connection errors into HTMX.
- Records are collected before import, so a timeout while waiting for the ACLog response does not import partial data.
- `aclog_records_match()` now normalizes date and time values during comparison, which keeps ACLog records with `2024-06-01` / `12:30` compatible with ADIF-style `20240601` / `123000`.
