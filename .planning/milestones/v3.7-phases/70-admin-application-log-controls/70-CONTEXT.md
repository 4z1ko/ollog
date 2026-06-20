# Phase 70: Admin Application Log Controls - Context

**Gathered:** 2026-06-20
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds admin controls to the existing Application Logs Recent Logs table: a current-browser Pause/Start live-feed toggle and a confirmation-gated Clear Log Messages action. It must not change QSO ingestion behavior, application log settings, retention policy, filters, pagination, or existing instrumentation semantics except where needed to support the two controls.

</domain>

<decisions>
## Implementation Decisions

### Pause/Start Behavior
- **D-01:** Pause affects only the current browser tab/session. It stops automatic SSE row insertion and near-live polling refreshes in that tab, but it does not stop server-side log storage, broadcasts, or other browser tabs.
- **D-02:** When an admin clicks Start/Resume, the page should immediately fetch/reconcile missed recent rows so the admin catches up without a full page refresh.
- **D-03:** Pause does not freeze deliberate admin actions. Filter changes, reset links, and pagination clicks should still refresh the table through the existing HTMX behavior.

### Clear Result Behavior
- **D-04:** Confirming Clear Log Messages deletes existing application log records, then creates/shows a fresh "Application logs cleared" audit message that includes the deleted record count.
- **D-05:** If the clear succeeds but the follow-up audit log cannot be saved, the clear still succeeds. The UI should show success and, if practical, a note that the audit message could not be written.
- **D-06:** Logging must continue after clear. Newly generated records should appear normally once live feed is running.

### Button Placement and Visual State
- **D-07:** Put Pause/Start and Clear controls in the Recent Logs card header next to the LIVE/PAUSED badge.
- **D-08:** Clear should use danger-outline styling: visibly destructive, but not visually louder than primary page actions.
- **D-09:** Pause/Start should visibly change the control label/icon/status and the live badge should reflect LIVE versus PAUSED.

### Clear Scope Wording
- **D-10:** The clear confirmation should use this promise: "Clear all application log messages from the database. QSO records, users, and log settings are not affected."
- **D-11:** Avoid wording that implies only currently displayed or filtered rows are cleared. This action clears all application log records.

### the agent's Discretion
- The exact icon choice, button microcopy, and success/error fragment copy may follow the existing admin UI pattern as long as the locked behavior and safety wording are preserved.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and Requirements
- `.planning/REQUIREMENTS.md` — v3.7 LOGCTRL-01 through LOGCTRL-08 requirements and boundaries.
- `.planning/ROADMAP.md` — Phase 70 goal, success criteria, and milestone boundary.
- `.planning/PROJECT.md` — active requirement summary and current milestone context.

### Existing Admin Log Implementation
- `templates/admin/logs.html` — current Application Logs page, filters, SSE handling, row rendering, and polling fallback.
- `templates/admin/logs_table.html` — Recent Logs table, empty state, and Previous/Next HTMX pagination.
- `templates/admin/log_row.html` — server-rendered log row structure and metadata/error detail markup.
- `app/admin/ui_router.py` — admin UI routes, log table context helpers, settings route, log page route, and SSE event endpoint.
- `app/internal_logs/router.py` — admin JSON API for listing logs and updating settings.
- `app/internal_logs/service.py` — logger service, query helpers, formatting, masking, and settings behavior.
- `app/internal_logs/models.py` — `ApplicationLog`, `ApplicationLogSettings`, severity ordering, retention fields, and indexes.
- `docs/admin-guide/application-logs.md` — admin documentation for log settings, viewer behavior, filters, and event coverage.

### Tests
- `tests/test_internal_logs.py` — existing focused tests for logger thresholding, masking, pagination API, live broadcast manager, formatted details, and instrumentation event contracts.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `templates/admin/logs.html`: Already owns `EventSource('/admin/ui/logs/events')`, client-side `matchesFilters()`, `rowHtml()`, `refreshLogsTable()`, and polling fallback behavior. Pause/Start should extend this script rather than introduce a new frontend framework.
- `templates/admin/logs_table.html`: Already has an `#logs-table` wrapper and `#logs-table-body`; clear and resume refreshes can target this existing partial.
- `app_logger`: Existing failure-isolated logger can write the post-clear audit event without making audit-write failure fatal.
- `query_logs()` and `_logs_pagination_context()`: Existing table querying/pagination helpers should be reused for refresh after resume/clear.

### Established Patterns
- Admin UI uses FastAPI + Jinja2 + HTMX partial swaps. Error fragments should return HTML that HTMX can render, following existing admin routes.
- Live application logs use SSE plus a safe polling fallback. Pause must gate both mechanisms in the current browser tab.
- Internal logging is failure-isolated and sensitive metadata is sanitized before storage/broadcast.
- Destructive admin actions elsewhere use modal confirmation patterns and scoped routes protected by `require_admin_cookie`.

### Integration Points
- Add UI controls in the Recent Logs card header in `templates/admin/logs.html`.
- Add a protected admin route for clear confirmation/clear execution under `/admin/ui/logs/...` or an equivalent existing admin namespace.
- Add service/helper behavior to delete `ApplicationLog` records without touching `ApplicationLogSettings`.
- Add tests in or near `tests/test_internal_logs.py` for clear behavior, settings preservation, and client-side pause/resume hooks.

</code_context>

<specifics>
## Specific Ideas

- Resume should catch the admin up immediately, not make them wait for the next poll/SSE event.
- Pause is a live-feed control, not a table lock; intentional filters and pagination still work while paused.
- Clear should leave one fresh audit row when possible so the admin sees that the operation happened and how many records were removed.
- The confirmation copy should explicitly reassure that QSO records, users, and log settings are not affected.

</specifics>

<deferred>
## Deferred Ideas

- Export/download filtered application logs.
- Clear logs by active filter or date range.
- Password-confirmed clear for higher-friction destructive behavior.
- Global live-feed pause across all browser sessions.

</deferred>

---

*Phase: 70-Admin Application Log Controls*
*Context gathered: 2026-06-20*
