# Phase 68: Admin Log Configuration and Viewer - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 68 delivers the admin-facing application log configuration and viewer experience: minimum level and retention settings, recent log browsing, filtering, pagination controls, live updates, and readable log detail display.

Phase 67 already implemented much of this surface while building the logging foundation. Phase 68 should reconcile that shipped work against ADMINLOG-01 through ADMINLOG-06 and add only the missing acceptance-criteria polish.

</domain>

<decisions>
## Implementation Decisions

### Scope Reconciliation
- **D-01:** Treat Phase 68 as a reconcile-gaps phase. Verify existing admin log viewer/configuration work from commit `a821a65`, avoid duplicate implementation, and add only missing or incomplete acceptance-criteria items.
- **D-02:** Existing settings, filter, SSE, admin-auth, and documentation work should be reused unless validation finds a concrete gap.

### Pagination Controls
- **D-03:** Add simple Previous/Next pagination controls to the admin Logs page. This should use the existing `page` and `page_size` backend behavior and remain compact for the operational "recent logs" use case.
- **D-04:** Do not add numbered page navigation unless planning discovers it is necessary. Current preference is simple movement through older/newer pages.

### Live Update Behavior
- **D-05:** Keep immediate insertion for new matching live log events. If filters are active, matching logs should appear right away according to the current client-side filter checks.
- **D-06:** Preserve the existing live-first behavior rather than adding a "new logs available" prompt. The viewer is primarily for operational visibility, so immediacy matters more than table stability.

### Log Detail Display
- **D-07:** Metadata and error details should stay collapsed by default, but render as readable formatted JSON rather than raw Python-style dictionary text.
- **D-08:** Do not expand scope into a larger redesign of log detail chips. Existing event/correlation/QSO/bridge/remote context text can remain unless formatting work naturally makes a tiny improvement.

### the agent's Discretion
- Use existing admin card/table/form styling and HTMX/SSE patterns.
- Keep the UI dense and operational, not marketing-like.
- Add focused tests around the Phase 68 gap(s), especially pagination controls and JSON formatting if implemented.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and Phase Scope
- `.planning/PROJECT.md` — v3.6 active requirements and validated Phase 67 logging foundation requirements.
- `.planning/ROADMAP.md` — Phase 68 goal, success criteria, and note that Phase 67 already overlaps Phase 68.
- `.planning/STATE.md` — current project state, Phase 67 completion context, known blockers, and pending Phase 68 reconciliation note.

### Phase 67 Evidence to Reconcile Against
- `.planning/phases/67-logging-foundation/67-01-SUMMARY.md` — implementation summary listing admin log API/UI, live stream, filters, and docs already shipped.
- `.planning/phases/67-logging-foundation/67-UAT.md` — verified behavior for logging foundation and broad admin viewer plumbing.
- `.planning/phases/67-logging-foundation/67-SECURITY.md` — admin-only access, masking, TTL retention, settings validation, and forced audit logging evidence.
- `.planning/phases/67-logging-foundation/67-VALIDATION.md` — automated coverage map for LOG-01 through LOG-06.

### Admin Log UI/API Code
- `templates/admin/logs.html` — existing admin Logs page with settings form, filters, live SSE client, and level help text.
- `templates/admin/logs_table.html` — current table partial, total count text, and missing visible pagination controls.
- `templates/admin/log_row.html` — current collapsed metadata/error display using raw dict rendering.
- `templates/admin/logs_settings_result.html` — settings update HTMX result partial.
- `app/admin/ui_router.py` — admin UI routes for logs page, settings update, and SSE events.
- `app/internal_logs/router.py` — admin JSON API for list/settings endpoints.
- `app/internal_logs/service.py` — query filtering, pagination, serialization, settings, thresholding, and masking.
- `app/internal_logs/manager.py` — live log broadcast queue manager.
- `tests/test_internal_logs.py` — existing focused tests for thresholding, masking, broadcast, and paginated JSON API output.

### Documentation
- `docs/admin-guide/application-logs.md` — current admin documentation for log levels, fields, masking, retention, and ADIF call-sign terminology.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `templates/admin/logs.html`: already provides settings, filters, live status, and EventSource handling.
- `templates/admin/logs_table.html`: table partial can host Previous/Next controls without changing the full page.
- `templates/admin/log_row.html`: row partial is the right place to improve collapsed metadata/error detail rendering.
- `query_logs()` in `app/internal_logs/service.py`: already supports `page`, `page_size`, filters, and total count.
- `tests/test_internal_logs.py`: existing test file can be extended for viewer API and formatting/helper behavior.

### Established Patterns
- Admin UI routes use `require_admin_cookie`; JSON admin log routes use `require_admin`.
- HTMX partial refreshes target a contained table wrapper, matching existing admin patterns.
- SSE uses `EventSource` and inserts new matching rows immediately.
- Error fragments in HTMX routes should return HTTP 200 when response body must be swapped; preserve existing project rule.
- Tailwind classes must be literal strings in templates and verified when styling changes affect generated CSS.

### Integration Points
- `/admin/ui/logs` renders full page or `admin/logs_table.html` for HTMX filter/page requests.
- `/admin/ui/logs/settings` updates minimum level and retention days.
- `/admin/ui/logs/events` streams new application logs.
- `/admin/logs/` provides JSON list API with page/page_size/filter support.
- Sidebar links already include Logs across admin templates.

</code_context>

<specifics>
## Specific Ideas

- Phase 68 should be a small, surgical planning pass: "find what Phase 67 already did, close the remaining admin viewer gaps."
- Add Previous/Next instead of numbered pagination.
- Keep live inserts immediate.
- Improve detail readability by formatting collapsed metadata/error as JSON.

</specifics>

<deferred>
## Deferred Ideas

- Numbered page navigation is intentionally deferred unless future usage shows admins need direct page jumps.
- Context chips beyond the existing inline event/correlation/QSO/bridge/remote text are deferred to avoid turning Phase 68 into a UI redesign.

</deferred>

---

*Phase: 68-Admin Log Configuration and Viewer*
*Context gathered: 2026-06-19*
