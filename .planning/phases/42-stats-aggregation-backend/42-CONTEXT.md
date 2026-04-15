# Phase 42: Stats Aggregation Backend - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the `get_stats()` service function and `GET /log/stats` route handler. The service runs JWT-isolated MongoDB aggregation pipelines against the `qsos` collection to compute band counts, mode counts, DXCC entity counts, and a unique entity total for any operator. The route passes this data dict to the template layer. DXCC entity resolution happens Python-side using the existing `lookup_prefix()` function — no MongoDB-side country resolution.

**Not in scope:** Charts, HTML template (`stats.html`), sidebar nav link — those are Phase 43.

</domain>

<decisions>
## Implementation Decisions

### DXCC Entity Naming
- **D-01:** Use `pycountry` to resolve ISO alpha-2 codes to full country names for chart labels (e.g. "Germany", "Japan", "United States"). `pycountry` is already a project dependency imported in `ui_router.py`.
- **D-02:** QSOs where `lookup_prefix(CALL)` returns `None` (maritime mobile /MM, non-country ITU entities like 4U, unrecognized prefixes) are grouped under a single **"Unknown"** bucket in the DXCC chart data. Nothing is silently excluded — the operator sees all QSOs reflected.

### Claude's Discretion
- Module placement: follow the existing domain-per-module pattern — new `app/stats/` module with `service.py` and a router. The stats route is mounted at `/log/stats` via the existing `ui_router` prefix or a new router registered in `app/main.py`.
- Aggregation pipeline architecture (1 consolidated pipeline vs 3 separate): choose whichever is cleaner given the `get_motor_collection().aggregate()` pattern already established in the codebase.
- Template data shape keys: follow conventions from existing router context dicts (snake_case). Suggested shape: `{"band_counts": {...}, "mode_counts": {...}, "entity_counts": [...top-8 dicts...], "unique_entity_count": int, "total_qsos": int}`. Adjust as implementation requires — Phase 43 consumes whatever shape is returned.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture Decisions (pre-decided from research)
- `.planning/STATE.md` §"v2.3 Architecture Decisions" — MongoDB aggregation access pattern (`QSO.get_motor_collection().aggregate()`), pipeline guard requirement, DXCC Python-side rollup decision

### Codebase Patterns
- `app/qso/models.py` — QSO Beanie document, field aliases (`_operator`, `_deleted`), compound index
- `app/qso/service.py` — Established service layer pattern for this project
- `app/qso/ui_router.py` — Cookie auth dependency (`get_current_operator_callsign_cookie`), template response pattern, pycountry usage
- `app/callsign/prefixes.py` — `lookup_prefix()` public API: callsign → ISO alpha-2 or None
- `app/feed/manager.py` — Reference for `get_motor_collection()` / Motor async pattern (not aggregation, but Motor access pattern)

### Requirements
- `.planning/REQUIREMENTS.md` §STATS-06, §STATS-07 — Data isolation requirement, empty-state requirement

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lookup_prefix(callsign) -> str | None` (`app/callsign/prefixes.py`): resolves CALL to ISO alpha-2. Already handles suffix stripping, /MM maritime mobile, non-country entities.
- `pycountry` (already installed): `pycountry.countries.get(alpha_2=code).name` gives full country name. Used in `ui_router.py` for flag display.
- `get_current_operator_callsign_cookie` dependency (`app/auth/dependencies`): returns operator callsign from JWT cookie. Used consistently across all UI routes.
- `QSO.get_motor_collection().aggregate([...])` with `await cursor.to_list(length=None)`: established aggregation access pattern (confirmed in research, referenced in STATE.md).

### Established Patterns
- Domain-per-module layout: each feature area has `app/<domain>/service.py` + `app/<domain>/router.py`. Stats should follow this as `app/stats/`.
- Cookie auth on all UI routes via `Depends(get_current_operator_callsign_cookie)`.
- Template responses via `templates.TemplateResponse(request, "log/<page>.html", {...})`.
- Soft-delete guard: every query must include `"_deleted": False` alongside `"_operator"`.

### Integration Points
- New router registered in `app/main.py` lifespan or via `app.include_router(...)`.
- Template `templates/log/stats.html` will be created in Phase 43 — Phase 42 only needs the route to return 200 with the data dict; the template can be a stub for now.

</code_context>

<specifics>
## Specific Ideas

- The DXCC top-8 rollup happens Python-side: sort entity counts descending, take top 8 by name, sum remainder into a single "Other" entry (per STATS-04). "Unknown" bucket (for unresolvable callsigns) participates in the sort like any other entity — it can appear in the top 8 or fold into "Other" depending on count.
- Empty-state shape: when `total_qsos == 0`, return the same dict structure with all counts as empty dicts/lists and `total_qsos = 0` — the route must not raise on an empty log (STATS-07).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 42-stats-aggregation-backend*
*Context gathered: 2026-04-15*
