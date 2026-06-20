# Phase 70 Research — Admin Application Log Controls

**Phase:** 70 Admin Application Log Controls  
**Date:** 2026-06-20  
**Status:** Complete

## Research Question

What do we need to know to plan Pause/Start live-feed controls and Clear Log Messages safely on the existing admin Application Logs page?

## Relevant Existing Implementation

### Admin Logs Page

- `templates/admin/logs.html` renders the full Application Logs page.
- The Recent Logs card currently has a simple header with title and `#logs-live-status` badge set to `LIVE`.
- The same template owns all client-side live behavior:
  - `EventSource('/admin/ui/logs/events')` for SSE.
  - `source.addEventListener('app_log', ...)` for immediate row insertion.
  - `window.setInterval(refreshLogsTable, 5000)` for near-live polling fallback.
  - `refreshLogsTable()` uses `htmx.ajax('GET', '/admin/ui/logs?' + logsQuery(), { target: '#logs-table', swap: 'outerHTML' })`.
  - `openDetailKeys()` and `restoreOpenDetails()` preserve expanded metadata/error details across polling refreshes.
- `templates/admin/logs_table.html` owns the `#logs-table` partial, `#logs-table-body`, empty state, and Previous/Next links.
- `templates/admin/log_row.html` owns the canonical row markup for server-rendered and fetched live rows.

### Admin Routes

- `app/admin/ui_router.py` provides:
  - `GET /admin/ui/logs` full page or `logs_table.html` partial when HTMX.
  - `POST /admin/ui/logs/settings` for settings updates.
  - `GET /admin/ui/logs/events` SSE stream.
  - `GET /admin/ui/logs/{log_id}/row` canonical row partial fetch for live inserts.
- Admin routes use `require_admin_cookie`.
- Existing destructive admin QSO clear modal routes return HTTP 200 fragments because HTMX 2.x does not swap 4xx response bodies reliably.
- Existing modals use `modal-backdrop`, `modal-box`, `modal-title`, `modal-body`, and `modal-actions`.

### Internal Log Storage

- `ApplicationLog` collection name: `application_logs`.
- `ApplicationLogSettings` collection name: `application_log_settings`.
- `app_logger` is failure-isolated and returns `None` if storage/broadcast fails.
- `app_logger.info(..., force=True)` can save important admin audit events regardless of active severity threshold.
- `query_logs()` already supports level/source/search/date pagination.
- `log_to_dict()` and `_log_row_context()` are the two relevant serialization paths.

## Implementation Findings

### Pause/Start

The safest implementation is entirely client-side in `templates/admin/logs.html`:

- Add a local boolean such as `logsLivePaused`.
- Gate `source.addEventListener('app_log', ...)` before it inserts a row.
- Gate the polling interval callback so it only calls `refreshLogsTable()` when not paused.
- Do not gate `refreshLogsTable()` itself. That preserves explicit filter/pagination refresh behavior and lets Start call it immediately.
- Add a `setLivePaused(paused)` helper that updates:
  - button label/text
  - `aria-pressed`
  - status badge text/classes: `LIVE` vs `PAUSED`
- Keep `source.onerror` able to show `OFFLINE` when not paused. If paused, `PAUSED` should remain the intentional state.

### Clear Log Messages

The safest backend shape is a small service/helper plus admin UI routes:

- Add helper such as `clear_application_logs()` in `app/internal_logs/service.py`.
- It should delete from `ApplicationLog` only.
- It must not touch `ApplicationLogSettings`.
- After deletion, route should attempt a forced audit log:
  - message: `Application logs cleared`
  - source: `admin.logs`
  - event_type: `application_logs_cleared`
  - transport: `admin`
  - metadata: admin username and deleted count
  - force: `True`
- Because `app_logger` is failure-isolated, audit failure will naturally return `None`. The route can still report success and include a status note if no audit row was returned.

### Clear UI Flow

- Put `Pause`/`Start` and `Clear Log Messages` in the Recent Logs header with the status badge.
- Add a modal placeholder at the bottom of `templates/admin/logs.html`.
- Add a modal template for confirmation.
- Header Clear button should use HTMX `hx-get` to fetch the modal; it must not delete directly.
- Modal confirm button should post to a clear route and target both modal/status/table as needed.
- Two viable refresh patterns:
  - Return a small success fragment and use `HX-Trigger` or inline JS to call `refreshLogsTable()`.
  - Return an updated table partial and empty the modal separately.
- Prefer the simplest pattern that keeps table refresh deterministic and easy to test. Existing route patterns already support returning fragments and letting client script refresh the table.

## Test Strategy

Add/extend tests in `tests/test_internal_logs.py`:

- Source-level script test:
  - `logsLivePaused` or equivalent state exists.
  - SSE handler exits when paused.
  - polling interval respects paused state.
  - Start/Resume calls `refreshLogsTable()`.
  - `refreshLogsTable()` itself remains callable independent of pause, preserving filters/pagination.
- Route/helper tests:
  - clear helper deletes from `ApplicationLog`.
  - clear route is admin-protected by dependency signature.
  - clear execution preserves `ApplicationLogSettings` by not referencing or deleting it.
  - clear audit event uses `force=True`, `event_type="application_logs_cleared"`, and includes deleted count.
  - confirmation modal contains the required safety wording.
- Existing pagination/detail tests should continue to pass.

## Documentation

Update `docs/admin-guide/application-logs.md`:

- Explain Pause/Start controls.
- State Pause is current-browser only and does not stop log capture.
- Explain Clear Log Messages clears all stored application log messages, not filtered/displayed rows.
- State QSO records, users, log settings, and future logging are not affected.

## Risks and Mitigations

- **Accidentally deleting settings or other data:** keep deletion helper scoped to `ApplicationLog` and test that settings model is not referenced by clear logic.
- **Pause hides explicit admin actions:** gate only automatic SSE/polling paths, not the shared refresh function or HTMX filter/pagination controls.
- **Audit row gets deleted by the clear:** delete first, then force-save audit record.
- **Live state becomes confusing after SSE error:** keep `OFFLINE` for connection errors while running; keep `PAUSED` when pause is intentional.
- **Mobile header crowding:** use flex-wrap and compact buttons; do not alter table layout.

## Research Complete

Phase 70 can be implemented as one focused plan touching:

- `app/internal_logs/service.py`
- `app/admin/ui_router.py`
- `templates/admin/logs.html`
- new admin clear modal/status partials as needed
- `docs/admin-guide/application-logs.md`
- `tests/test_internal_logs.py`
- `static/css/input.css` and `static/css/output.css` only if a reusable danger-outline class is added
