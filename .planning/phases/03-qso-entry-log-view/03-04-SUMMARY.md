---
phase: 03-qso-entry-log-view
plan: 04
subsystem: ui
tags: [fastapi, jinja2, htmx, qso, log-view, pagination, sorting, filtering, inline-edit, soft-delete, cookie-auth]

# Dependency graph
requires:
  - phase: 03-03
    provides: ui_router.py, HTMX QSO entry form, operator login
  - phase: 03-02
    provides: get_qso_page(), find_duplicate(), service layer
  - phase: 01-04
    provides: JWT auth, get_current_operator_callsign_cookie
  - phase: 02-02
    provides: base.html, HTMX 2.0.4, inline CSS, cookie auth exception handler
provides:
  - Paginated QSO log view at /log/view with filter bar and sortable columns
  - HTMX inline edit via /log/qsos/{id}/edit (outerHTML swap)
  - HTMX Cancel (view row restore) via /log/qsos/{id} GET
  - HTMX PATCH save via /log/qsos/{id} PATCH (form-encoded from hx-include)
  - HTMX soft-delete via /log/qsos/{id} DELETE (empty 200 removes row)
  - _qso_to_view_dict() helper for extracting model_extra ADIF fields in templates
affects: [04-adif-import, 05-multi-operator-live]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HTMX HX-Request header detection for partial vs full page response (same endpoint serves both)"
    - "_qso_to_view_dict() converts Beanie model_extra fields to plain dict for Jinja2 templates"
    - "Beanie $set update with raw MongoDB field names (_deleted, not is_deleted)"
    - "Empty Response(content='', status_code=200) for HTMX outerHTML swap deletion"
    - "parse_adif_datetime() reused in PATCH for recalculating qso_date_utc when date/time fields change"
    - "Jinja2 min() via [a, b]|min filter for pagination display"

key-files:
  created:
    - templates/log/log.html
    - templates/log/log_table.html
    - templates/log/qso_row.html
    - templates/log/qso_row_edit.html
  modified:
    - app/qso/ui_router.py

key-decisions:
  - "_qso_to_view_dict() converts QSO to plain dict before template rendering: Beanie model_extra fields (FREQ, RST_SENT, RST_RCVD, QSO_DATE, TIME_ON) are not accessible as direct attributes in Jinja2 — extracting them from model_extra in Python is simpler than template workarounds"
  - "HX-Request header check for partial/full response: same /log/view endpoint serves both HTMX partial swaps and full page loads — no separate route needed"
  - "Empty 200 response for DELETE: HTMX outerHTML swap with empty content removes the <tr> from the DOM; no template needed"
  - "Sort toggle in column headers uses inline Jinja2 ternary in hx-get URL: avoids extra template variables while preserving current filter params on sort change"

# Metrics
duration: ~8min
completed: 2026-04-03
---

# Phase 3 Plan 04: Log View with Filtering, Sorting, Inline Edit, and Soft-Delete Summary

**Paginated QSO log view at /log/view with HTMX filter bar, sortable column headers, inline row editing, and soft-delete — all without page reloads**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-03
- **Completed:** 2026-04-03
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- `app/qso/ui_router.py`: added 5 new endpoints to existing router
  - GET /log/view: paginated/filtered/sorted list, HTMX partial or full page based on HX-Request header
  - GET /log/qsos/{id}/edit: editable row partial (outerHTML swap)
  - GET /log/qsos/{id}: view-mode row partial (Cancel button restores this)
  - PATCH /log/qsos/{id}: form-encoded update, recalculates qso_date_utc if date/time changed, strips protected fields
  - DELETE /log/qsos/{id}: soft-delete via `{"$set": {"_deleted": True}}`, returns empty 200
- `_qso_to_view_dict()` helper: extracts model_extra ADIF fields (FREQ, RST_SENT, RST_RCVD, QSO_DATE, TIME_ON) into a plain dict for safe Jinja2 template access
- `templates/log/log.html`: full page extending base.html, filter bar with callsign/band/mode/date range inputs, HTMX filter form targeting #log-table, Clear button with JS to reset fields
- `templates/log/log_table.html`: HTMX partial — sortable column headers with toggle direction indicators, tbody includes qso_row.html per row, pagination controls (showing X-Y of N, prev/next with filter params preserved)
- `templates/log/qso_row.html`: single `<tr>` with Edit and Delete HTMX buttons, hx-confirm dialog on Delete
- `templates/log/qso_row_edit.html`: edit `<tr>` with plain text inputs for all ADIF fields, Save (hx-patch + hx-include="closest tr") and Cancel buttons

## Task Commits

Each task was committed atomically:

1. **Task 1: Log view UI routes** - `03fbedc` (feat)
2. **Task 2: Log view templates** - `8813022` (feat)

## Files Created/Modified

- `app/qso/ui_router.py` - Modified: added 5 log view endpoints + _qso_to_view_dict() helper
- `templates/log/log.html` - New: full log view page with filter bar (82 lines)
- `templates/log/log_table.html` - New: paginated table partial with sortable headers (67 lines)
- `templates/log/qso_row.html` - New: view-mode row with Edit/Delete HTMX buttons (18 lines)
- `templates/log/qso_row_edit.html` - New: edit-mode row with inline inputs (24 lines)

## Decisions Made

- `_qso_to_view_dict()` extracts Beanie model_extra fields: FREQ, RST_SENT, RST_RCVD, QSO_DATE, TIME_ON live in `qso.model_extra` (set via `extra="allow"`) — not direct attributes — so extracting them in Python before passing to Jinja2 is simpler and more reliable than attribute-access workarounds in templates.
- Same /log/view endpoint for full page and HTMX partial: checking `HX-Request` header selects the template; no route duplication needed.
- Empty Response(content="", status_code=200) for soft-delete: HTMX outerHTML swap with empty content removes the `<tr>` cleanly.
- Sort toggle embedded directly in column header hx-get URLs as Jinja2 ternary: preserves all current filter params on column sort changes without extra round trips.

## Deviations from Plan

None - plan executed exactly as written.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 is complete: QSO entry form (03-03) and log view (03-04) both operational
- Phase 4 (ADIF import): `_qso_to_view_dict()` and the log view provide the foundation for showing imported QSOs in the existing table
- All prior tests continue to pass (no changes to service.py, models.py, or REST API router)

---
*Phase: 03-qso-entry-log-view*
*Completed: 2026-04-03*

## Self-Check: PASSED

- app/qso/ui_router.py: FOUND
- templates/log/log.html: FOUND
- templates/log/log_table.html: FOUND
- templates/log/qso_row.html: FOUND
- templates/log/qso_row_edit.html: FOUND
- .planning/phases/03-qso-entry-log-view/03-04-SUMMARY.md: FOUND
- commit 03fbedc: FOUND
- commit 8813022: FOUND
