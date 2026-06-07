---
status: complete
phase: 58-configurable-qso-field-catalog-and-log-view-columns
source: 58-01-SUMMARY.md
started: 2026-06-07T17:43:24Z
updated: 2026-06-07T17:46:06Z
---

## Current Test

[testing complete]

## Tests

### 1. Default Log View Columns
expected: Fresh browser state shows Date / Time, Callsign, Band, Mode, Frequency, and RST as the visible configurable columns, with Actions still visible at the row end.
result: pass
evidence: Focused tests passed and source review confirmed default_column_keys are date, call, band, mode, freq, rst while Actions remains outside the configurable field loop.

### 2. Curated Field Catalog Menu
expected: The gear menu renders a curated known QSO/ADIF checklist with default fields plus non-default fields such as TX Power and Contest ID, without exposing internal/security fields.
result: pass
evidence: Focused catalog tests passed; source review confirmed field_catalog drives data-column-toggle checkboxes and tests exclude _id, revision_id, _deleted, _created_at, and rowHash.

### 3. Catalog-Driven Table Rendering
expected: Headers and row cells render from the shared catalog, missing field values render blank, Callsign keeps flag display, RST keeps paired sent/received display, and non-sortable fields render plain headers.
result: pass
evidence: Focused view/template tests passed and source review confirmed templates/log/log_table.html and templates/log/qso_row.html iterate over field_catalog.

### 4. Persistence, HTMX, SSE, and Sort Preservation
expected: Column selections continue to persist under ollog.log.columns, stale/invalid keys normalize back to defaults, visibility reapplies after HTMX swaps, and sorting remains limited to Date/Time, entry timestamp, Callsign, Band, and Mode.
result: pass
evidence: Focused tests passed; source review confirmed ollog.log.columns, defaultColumns/configurableColumns normalization, htmx:afterSettle reapplication, and exactly 10 allowed sort values.

### 5. Column Menu Viewport Fit
expected: Open /log/view, open the gear menu on desktop and a narrow/mobile viewport, and confirm the menu is bounded, scrollable, readable, and does not overflow or visually overlap the page in a broken way.
result: pass
evidence: User confirmed pass on 2026-06-07.

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]

## Automated Verification

- `.venv/bin/python -m pytest tests/test_view_dict.py tests/test_service_sort.py tests/test_sse_sentinel.py` — 7 passed, 7 skipped. Skips are MongoDB-dependent tests skipped because MongoDB is not available at localhost:27017.
- `.venv/bin/python -m ruff check app/qso/fields.py app/qso/ui_router.py tests/test_view_dict.py tests/test_service_sort.py tests/test_sse_sentinel.py` — passed.
- `npm run build` — passed. Browserslist database is outdated warning only.

## Source Review

- `templates/log/log.html` renders the checklist from `field_catalog` and keeps `columnStorageKey = 'ollog.log.columns'`.
- `templates/log/log.html` normalizes persisted values against `configurableColumns` and falls back to `defaultColumns` when no valid keys remain.
- `templates/log/log_table.html` and `templates/log/qso_row.html` render configurable columns from `field_catalog`.
- `templates/log/qso_row.html` keeps `<td class="actions">` outside the configurable field loop.
- `tests/test_service_sort.py` asserts `_ALLOWED_SORT_FIELDS` remains exactly the existing 10 sort values.
- `tests/test_view_dict.py` asserts unsafe catalog fields are excluded.
