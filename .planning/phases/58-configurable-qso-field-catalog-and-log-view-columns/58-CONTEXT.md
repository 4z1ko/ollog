# Phase 58: Configurable QSO Field Catalog and Log View Columns - Context

**Gathered:** 2026-06-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn the existing Log View column configuration menu from an eight-field hard-coded toggle into a selector for all supported, known QSO/ADIF display fields. The table should render whichever fields the operator selects while preserving the existing default columns, localStorage persistence, HTMX partial swaps, SSE refresh behavior, pagination, filtering, inline edit/delete actions, and the always-visible Actions column.

This phase does not add dynamic discovery of arbitrary fields from current database contents, user-defined column ordering, drag/reorder support, or broad new sorting capabilities.

</domain>

<decisions>
## Implementation Decisions

### Field Catalog Boundaries
- **D-01:** The selectable catalog is limited to **known ADIF/common fields**. Do not dynamically discover field names from currently stored QSOs in this phase.
- **D-02:** Include safe display fields that are part of the QSO/logging domain, such as core QSO fields, common ADIF fields, profile-stamped fields, app-specific fields, and safe internal display values.
- **D-03:** Exclude implementation/security fields that should never be displayed, including raw MongoDB IDs, `_deleted`, authentication/password/token data, and other non-QSO internals.

### Column Menu Shape
- **D-04:** Keep the current gear-menu concept, but make the menu a **single scrollable checklist** that can handle the larger known field catalog.
- **D-05:** No grouped sections or search/filter input are required in this phase.
- **D-06:** The checklist must remain usable in light and dark themes and must be bounded so it does not overflow mobile or desktop viewports.

### Column Order Behavior
- **D-07:** Preserve the current default columns for fresh browsers: Date / Time, Callsign, Band, Mode, Frequency, and RST.
- **D-08:** Additional selected fields should **append after the default columns** rather than allowing arbitrary user ordering.
- **D-09:** Do not implement drag/reorder support in this phase.
- **D-10:** The Actions column remains always visible and outside the configurable QSO field list.

### Value Formatting Rules
- **D-11:** Render **humanized display values**, not raw internal values, when the field has an established display convention.
- **D-12:** Existing special displays should be preserved: Date / Time should remain readable UTC text, Callsign should keep country flag enrichment, and RST should remain the paired sent/received presentation for the default RST column.
- **D-13:** Individual selected ADIF fields should still use their native field names and values where no special display convention exists.
- **D-14:** Missing or absent field values should render as blank cells without template or JavaScript errors.

### Sorting Scope
- **D-15:** Only the current sortable fields keep sort controls: Date / Time (`qso_date_utc`), entry timestamp (`_created_at` clock icon), Callsign, Band, and Mode.
- **D-16:** Newly selectable ADIF/common fields do not become sortable in this phase. Non-sortable selected fields render plain headers.

### the agent's Discretion
- Exact known-field catalog contents, as long as it covers common ADIF/QSO fields and remains scoped to known safe display fields.
- Exact Python module/function structure for the catalog and value extraction.
- Exact label wording for fields, provided labels are human-readable and stable.
- Exact implementation of localStorage normalization and stale-key handling, provided invalid keys are ignored and an empty valid selection falls back to defaults.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope
- `.planning/REQUIREMENTS.md` — v3.0 requirements FIELDS-01..04, COLUMNS-01..05, TABLE-01..05, VERIFY-01..03.
- `.planning/ROADMAP.md` — Phase 58 goal, success criteria, and planned plan file.
- `.planning/STATE.md` — Current milestone state, carried-forward constraints, and build rules.

### Existing Log View Implementation
- `templates/log/log.html` — Existing page shell, gear button, hard-coded column checklist, `ollog.log.columns` localStorage logic, and HTMX/SSE event handling.
- `templates/log/log_table.html` — Existing hard-coded table headers, sort links, auto-refresh sentinel, and pagination controls.
- `templates/log/qso_row.html` — Existing hard-coded row cells, flag display, RST pair display, and always-visible Actions column.
- `app/qso/ui_router.py` — `_qso_to_view_dict()` conversion, `log_view()` context construction, HTMX partial/full-page behavior, and inline edit/delete routes.
- `app/qso/models.py` — QSO document declared fields, extra ADIF field storage via `extra="allow"`, safe/internal field aliases, and rowHash/created_at fields.

### Related Existing Behavior
- `app/qso/service.py` — Existing allowed sort fields and `get_qso_page()` sorting/filtering behavior that must remain intact.
- `tests/test_service_sort.py` — Existing sort allowlist expectations.
- `tests/test_sse_sentinel.py` — Existing SSE auto-refresh sentinel expectations.
- `tests/test_view_dict.py` — Existing view dict expectations that should evolve with field extraction tests.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `templates/log/log.html` already owns the column configuration menu and browser persistence under `ollog.log.columns`; this storage contract should be preserved unless a migration guard is needed.
- `templates/log/log_table.html` already centralizes the table header, active sort indicators, and HTMX pagination links.
- `templates/log/qso_row.html` already centralizes row rendering and row actions.
- `_qso_to_view_dict()` in `app/qso/ui_router.py` is the current extraction point for declared fields, selected model extras, flag enrichment, and safe display values.

### Established Patterns
- HTMX full-page vs partial behavior is route-driven: full `/log/view` renders `log.html`; HX requests return `log/log_table.html`.
- Column visibility is currently applied client-side by toggling `hidden` on matching `[data-column]` and `[data-column-toggle]` values, then reapplied after HTMX settles.
- Sort links are plain HTMX anchors with preserved filter parameters; invalid sort fields are rejected in the service layer.
- Tailwind purge requires literal `dark:` classes in scanned templates when new styles are introduced.

### Integration Points
- The field catalog can be introduced near the log-view conversion layer and passed into both `log.html` and `log_table.html`.
- Headers and row cells should be generated from the same catalog/selected-field list to avoid drift.
- The catalog should provide stable field keys for localStorage, human labels for menu/header display, and value extraction/formatting for row cells.
- The Actions column should stay outside the catalog-rendered field loop.

</code_context>

<specifics>
## Specific Ideas

- Keep the menu visually compact: the existing gear button remains the entry point.
- Use one scrollable checklist rather than groups or search.
- Fresh browsers keep the same visible table as today.
- When an operator selects additional fields, they appear after the default columns in catalog order.
- Humanized display matters more than raw storage representation for user-facing cells.

</specifics>

<deferred>
## Deferred Ideas

- Dynamic discovery of field names from existing QSO documents.
- User-controlled column ordering, drag/reorder, or saved custom order.
- Search/filter inside the column configuration menu.
- Making every selected ADIF/common field sortable.

</deferred>

---

*Phase: 58-configurable-qso-field-catalog-and-log-view-columns*
*Context gathered: 2026-06-03*
