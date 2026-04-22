# Phase 49: Service Layer - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a sort-parameter allowlist to `get_qso_page()` in `app/qso/service.py`, expose `created_at` in the Jinja2 view dict via `_qso_to_view_dict()`, and extend the server-side `#auto-refresh-ok` SSE sentinel to also fire on `sort == '-_created_at'`.

This is a pure service/backend phase. No new UI components, no new routes, no schema changes. Phase 50 builds the sort UI on top of what this phase provides.

</domain>

<decisions>
## Implementation Decisions

### Invalid Sort Fallback (SORT-04)

- **D-01:** When `get_qso_page()` receives a `sort_by` value not in `_ALLOWED_SORT_FIELDS`, log a `WARNING` and fall back to the default sort (`-qso_date_utc`). Do NOT pass the unrecognized field to MongoDB.
- **D-02:** The WARNING log message must include both the rejected field name AND the operator callsign: e.g., `"Invalid sort field '%s' for operator '%s', falling back to default"`. This supports per-operator log monitoring.
- **D-03:** `_ALLOWED_SORT_FIELDS` should be declared as a module-level constant (frozenset or set) in `app/qso/service.py`. It must include all 10 currently sortable values: `-qso_date_utc`, `qso_date_utc`, `-CALL`, `CALL`, `-BAND`, `BAND`, `-MODE`, `MODE`, `-_created_at`, `_created_at` (per roadmap success criterion 2).

### Claude's Discretion

- **`created_at` key in view dict:** User did not select this area — planner may choose `"created_at"` (Python attr) or `"_created_at"` (MongoDB alias) for the `_qso_to_view_dict()` key. Prefer `"created_at"` (no leading underscore) for clean Jinja2 template access in Phase 50. Whichever is chosen must be consistent with how Phase 50 references it in templates.
- **`created_at` format in view dict:** A raw `datetime` object (consistent with `qso_date_utc`) is acceptable — Phase 50 will format it as needed for the tooltip display.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above and roadmap.

### Source Files (read before implementing)
- `app/qso/service.py` — `get_qso_page()` at line 183; current `sort_by` param has no validation
- `app/qso/ui_router.py` — `_qso_to_view_dict()` at line 219; add `created_at` here
- `templates/log/log_table.html` — auto-refresh sentinel at line 1; extend condition to include `-_created_at`
- `.planning/REQUIREMENTS.md` — SORT-03 and SORT-04 are the requirements for this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `logger = logging.getLogger(__name__)` — already set up in `app/qso/service.py`; use it for the WARNING log
- `_qso_to_view_dict()` pattern — existing dict-building pattern in `ui_router.py`; add `created_at` to the dict in the same style as other fields

### Established Patterns
- `_REQUIRED_FIELDS` frozenset in `service.py` — existing module-level constant pattern to follow for `_ALLOWED_SORT_FIELDS`
- Auto-refresh sentinel: `{% if page == 1 and sort == '-qso_date_utc' and not filters.* %}` — extend with `or sort == '-_created_at'`
- `qso.created_at` is the Python attribute on the Beanie `QSO` model (added in Phase 48, `alias="_created_at"`)

### Integration Points
- `get_qso_page()` is called from `log_view()` in `ui_router.py` line 286 — the allowlist check happens inside `get_qso_page()`, not at the call site
- `_qso_to_view_dict()` is called in 4 places: `log_view`, `qso_edit_row`, `qso_view_row`, and the inline edit PATCH handler — all inherit the `created_at` addition automatically

</code_context>

<specifics>
## Specific Ideas

- No specific UI or aesthetic references — this is a backend-only phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 49-service-layer*
*Context gathered: 2026-04-22*
