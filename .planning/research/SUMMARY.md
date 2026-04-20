# Project Research Summary

**Project:** ollog v2.5 QSO Sorting & Entry Timestamp
**Domain:** Server-rendered HTMX/FastAPI/MongoDB log table enhancement
**Researched:** 2026-04-20
**Confidence:** HIGH

## Executive Summary

v2.5 is a focused, surgical enhancement to an existing, working system. The milestone adds two related capabilities: a `_created_at` system timestamp field on every QSO document, and expanded sort column support in the log table UI. All required capabilities are fully available in the current stack (FastAPI, Beanie, pymongo, HTMX, Jinja2, Heroicons) — no new dependencies are needed. The implementation scope is tightly bounded: 4 files require changes, the rest of the codebase is untouched.

The recommended approach follows the existing patterns in the codebase precisely. The `_created_at` field belongs on the Beanie `QSO` model with a `default_factory`, using the same `alias`/`serialization_alias` dual-alias pattern already used for `_operator` and `_deleted`. Sort expansion for MODE and `_created_at` uses the existing HTMX URL-parameter + Jinja2 state toggle pattern that already works for date, callsign, and band. The only genuinely new work is a sort allowlist guard in `get_qso_page()` (currently missing) and a semantic decision about whether the `_created_at` sort header needs a matching empty `<td>` in each row.

The key risks are minor implementation traps, not architectural unknowns. Double-stamping `_created_at` on edits (if not added to the protected fields strip list in update handlers), incorrect use of the Python attribute name vs the MongoDB alias name in sort strings, and the table column count mismatch from a headerless `<td>` are all avoidable with a short checklist. FREQ sort is explicitly excluded because MongoDB lexicographic string sort produces wrong numeric ordering — this is a known dead end for v2.5.

## Key Findings

### Recommended Stack

No new packages. All v2.5 features are achievable with the existing installed stack. The existing alias pattern, default_factory, IndexModel, HTMX hx-get + hx-push-url, and Jinja2 conditional logic are all battle-tested within this codebase already.

**Core technologies (unchanged from v2.4):**
- **Beanie 2.1+**: `default_factory` fields, `IndexModel` in `Settings.indexes`, `.sort("-field")` string syntax — all confirmed against Context7 docs
- **pymongo 4.16+**: stores `datetime` as BSON UTC milliseconds, returns naive UTC on read — consistent with existing `qso_date_utc` convention; do NOT add `tz_aware=True` to `init_db()`
- **HTMX 2.0.4**: `hx-get` with query params, `hx-push-url="true"`, `hx-swap="innerHTML"` — URL-parameter sort state pattern confirmed correct and already in use
- **Jinja2**: `{% if sort == '-FIELD' %}` / `{% elif sort == 'FIELD' %}` toggle logic — already working for 3 columns, extend to MODE and `_created_at`
- **Heroicons (inline SVG)**: `chevron-up-down` (neutral), `chevron-down` (desc), `chevron-up` (asc) — all 3 states available; `chevron-up-down` SVG path confirmed from heroicons.com
- **Python 3.12+**: `datetime.now(tz=timezone.utc)` — avoids `utcnow()` DeprecationWarning

### Expected Features

**Must have (table stakes) — v2.5 launch:**
- `_created_at: Optional[datetime]` field on `QSO` Beanie document with `default_factory`
- `(_operator, _created_at)` compound index in `QSO.Settings.indexes`
- Sort allowlist in `get_qso_page()` — `_SORTABLE_FIELDS` set with fallback to `-qso_date_utc`
- MODE column becomes sortable in `log_table.html` (same pattern as CALL/BAND — zero backend changes)
- `_created_at` sort icon in `<thead>` (clock/timestamp icon, cycles `-_created_at` to `_created_at`)
- `_created_at` added to protected fields strip list in both `qso_update()` and `patch_qso()`

**Should have (differentiators) — v2.5 stretch:**
- Hollow/outline `chevron-up-down` icon on all sortable-but-unsorted columns (improves discoverability)
- `aria-sort` attribute on active `<th>` elements (WCAG 2.2 AA compliance)

**Defer to v2.6+:**
- FREQ sort with numeric coercion — requires `FREQ_numeric: float` derived field, migration of existing records; excluded from v2.5 because MongoDB string sort produces lexicographically incorrect numeric ordering
- Multi-column sort — significant URL and service complexity, no practical ham log use case
- Sort preference in localStorage — URL state via `hx-push-url` is sufficient and shareable

### Architecture Approach

The implementation has a strict model → service → view dict → template dependency chain. The `_created_at` stamp belongs exclusively in the model `default_factory` (not in `build_qso_dict()`), ensuring all four insert paths (REST API, UI form, UDP, ADIF import) get the timestamp automatically without any caller changes. The sort allowlist belongs in `service.py::get_qso_page()`. The view dict enrichment (`d["created_at"] = qso.created_at`) belongs in `_qso_to_view_dict()`. Template changes are the final layer.

**Modified components (4 files only):**
1. `app/qso/models.py` — add `created_at` field with `alias="_created_at"`, `default_factory`, and `operator_created_idx` IndexModel
2. `app/qso/service.py` — add `_SORTABLE_FIELDS` allowlist guard at top of `get_qso_page()`; add `"_created_at"` to protected fields in `patch_qso()`
3. `app/qso/ui_router.py` — add `d["created_at"] = qso.created_at` to `_qso_to_view_dict()`; add `"_created_at"` to protected fields in `qso_update()`
4. `templates/log/log_table.html` — add MODE sort header, `_created_at` sort icon, optional hollow chevrons

**Unchanged (confirmed by code audit):**
- `app/qso/router.py`, `app/udp/server.py`, `app/adif/router.py`, `app/adif/service.py` — `QSO(**qso_dict)` already picks up model defaults
- `templates/log/log.html` — filter form already threads `sort` via hidden input; untouched
- `app/feed/manager.py` — SSE auto-refresh sentinel already gates on `sort == '-qso_date_utc'`; no change needed

### Critical Pitfalls

1. **`_created_at` overwritten on edit if not in protected fields** — add `"_created_at"` to the protected fields strip list in both `qso_update()` (ui_router.py) and `patch_qso()` (router.py). The `default_factory` fires at every `QSO()` construction — the only protection against update paths overwriting the original stamp is the strip list.

2. **Sort string must use MongoDB alias name, not Python attribute** — Beanie `.sort("-_created_at")` uses the MongoDB field name (the alias). Using `"-created_at"` (no underscore) silently sorts by a non-existent field, returning results in natural order with no error. Always use the alias with underscore prefix in sort strings.

3. **FREQ string sort is lexicographically wrong** — `"9.0"` sorts after `"144.200"` in MongoDB string sort. FREQ is explicitly excluded from the sort allowlist. Users who need frequency grouping use the Band filter.

4. **`<th>` without `<td>` breaks table column count semantics** — the `_created_at` sort icon adds a `<th>` to `<thead>` with no corresponding data column. Fix: add empty `<td></td>` in each `<tr>` in `qso_row.html` and `qso_row_edit.html` (zero-width, zero-padding), or place the sort control outside the `<table>` entirely.

5. **Sort field injection is currently unguarded** — `get_qso_page()` passes raw `?sort=` query param directly to `.sort()` with no validation. The allowlist must be added before exposing new sort icons in the template.

## Implications for Roadmap

All v2.5 work is tightly interconnected and the dependency chain is strict. Phases should follow the model → service → view dict → template order.

### Phase 1: Model Foundation

**Rationale:** Everything else depends on the `_created_at` field existing on the Beanie document. The model change must land first so the service allowlist can include it and inserts can be verified in MongoDB.

**Delivers:** `_created_at` auto-stamped on all new QSO inserts via all 4 insert paths; compound index for efficient sort; field accessible as `qso.created_at` in Python

**Addresses:** Table stakes item — `_created_at` field + index

**Avoids:** Double-stamp pitfall (use `default_factory` on model, not in `build_qso_dict()`); alias mismatch pitfall (follow `_operator`/`_deleted` dual-alias pattern exactly); datetime timezone pitfall (use `lambda: datetime.now(timezone.utc)`, not `datetime.utcnow`)

**Verification:** Insert a QSO via each path; inspect MongoDB document; confirm `_created_at` field present with timestamp near insert time; confirm Beanie reads it back as `qso.created_at`

### Phase 2: Service Allowlist + View Dict

**Rationale:** The sort allowlist must be in place before the template exposes new sort icons (otherwise injecting `sort=_deleted` via URL is possible). The view dict enrichment is a one-line change that can land alongside the allowlist.

**Delivers:** `get_qso_page()` validates sort values against allowlist; `_qso_to_view_dict()` exposes `created_at` to templates; `_created_at` protected in both update handlers

**Addresses:** Table stakes — sort allowlist; anti-pattern prevention — double-stamp on update

**Avoids:** Sort field injection pitfall; `_created_at` overwritten-on-edit pitfall; missing view dict key causing Jinja2 UndefinedError

**Verification:** Call `get_qso_page(sort_by="_deleted")`; confirm fallback to `-qso_date_utc`. Edit a QSO; confirm `_created_at` is unchanged in MongoDB after edit.

### Phase 3: Template — Sort Headers

**Rationale:** With model and service in place, the template changes are pure UI work. MODE sort is trivial (zero backend dependencies). The `_created_at` sort icon requires the semantic column count decision (empty `<td>` vs out-of-band control).

**Delivers:** MODE column becomes sortable; `_created_at` sort icon in `<thead>` with correct three-state icons; all filter params threaded correctly in sort URLs; auto-refresh sentinel decision documented in template comment

**Addresses:** Table stakes — MODE sort, `_created_at` sort icon; differentiator — hollow chevrons on unsorted columns, `aria-sort` attributes

**Avoids:** Table column count mismatch (add empty `<td>` to `qso_row.html` + `qso_row_edit.html`); filter params dropped on sort click (copy full URL template from existing sort icons); auto-refresh sentinel ambiguity (explicitly comment the decision in the template)

**Verification:** Apply band filter + mode filter, click each sort icon, confirm filters preserved in URL. Apply `_created_at` sort, insert a new QSO, confirm badge behavior matches the documented sentinel decision.

### Phase Ordering Rationale

- Model before service because the allowlist must reference valid field names that actually exist in MongoDB
- Service before template because exposing sort icons without the allowlist creates an injection vector — even if minor, it is correct to close it first
- Template last because it is the consumer of everything above; any change to model field name or sort string naming would require re-touching the template
- All three phases are small enough to complete in a single work session; splitting them enforces the dependency chain and makes each step independently verifiable

### Research Flags

Phases with well-documented patterns (no further research needed):
- **Phase 1 (Model):** Beanie `default_factory`, `alias`/`serialization_alias`, `IndexModel` — fully documented and confirmed against Context7. Exact pattern to follow already exists in `_operator`/`_deleted` fields in the codebase.
- **Phase 2 (Service):** Allowlist is a straightforward Python set guard. Protected fields strip list pattern already exists in both update handlers.
- **Phase 3 (Template):** HTMX sort URL pattern already implemented for 3 columns. Jinja2 `{% if sort == '-FIELD' %}` toggle logic already in use. Heroicons SVG paths confirmed.

No phases require additional research. The entire v2.5 scope is covered by this research with HIGH confidence.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All changes use existing pinned packages. No new dependencies. Verified against Context7 (Beanie, HTMX) and pymongo official docs. |
| Features | HIGH | Grounded in direct codebase inspection and ham radio domain research. Anti-features (FREQ sort, multi-column sort) are well-reasoned exclusions. |
| Architecture | HIGH | Based on direct reading of all 7 relevant source files. Build order derived from actual dependency chain in existing code. |
| Pitfalls | HIGH | All pitfalls verified against live codebase patterns (protected fields strip list, model_extra access, alias conventions). Recovery paths documented. |

**Overall confidence:** HIGH

### Gaps to Address

- **Auto-refresh sentinel decision:** Whether `-_created_at` sort should also enable SSE auto-refresh (alongside `-qso_date_utc`) is a product decision not resolved by research. Default recommendation: keep sentinel restricted to `-qso_date_utc` only (existing behavior, no template logic change needed). Override to include `-_created_at` if UX testing shows users expect live refresh while viewing entry-order sort.

- **`_created_at` sort header placement:** Two valid options — (a) empty `<td>` in each row (table semantic validity) or (b) sort control outside the `<table>` (cleaner UX for a hidden column). Recommendation: option (a), empty `<td>`, because it is the minimal change and avoids redesigning the sort control area.

- **Hollow chevron scope:** Whether to apply `chevron-up-down` retroactively to existing columns (date, callsign, band) alongside new v2.5 columns is a UX consistency question. Recommendation: apply to all sortable columns in a single commit for visual consistency.

## Sources

### Primary (HIGH confidence)
- Context7 `/beanieodm/beanie` — `default_factory`, `IndexModel` in `Settings.indexes`, `.sort("-field")` string syntax, `@before_event(Insert)`
- Context7 `/bigskysoftware/htmx` — `hx-push-url`, `hx-get` query string pattern, `hx-include` (confirmed not needed)
- Direct codebase audit: `app/qso/models.py`, `app/qso/service.py`, `app/qso/ui_router.py`, `app/qso/router.py`, `app/udp/server.py`, `templates/log/log_table.html`, `templates/log/log.html` (2026-04-20)
- W3C WAI-ARIA sortable table: https://www.w3.org/WAI/ARIA/apg/patterns/table/examples/sortable-table/
- MDN aria-sort: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-sort

### Secondary (MEDIUM confidence)
- PyMongo datetime handling: https://www.mongodb.com/docs/languages/python/pymongo-driver/current/data-formats/dates-and-times/
- MongoDB compound index sort rules: https://www.mongodb.com/docs/manual/tutorial/sort-results-with-indexes/
- Heroicons `chevron-up-down` SVG path: https://heroicons.com/
- HTMX sortable table pattern: https://vladkens.cc/htmx-table-sorting/

### Tertiary (MEDIUM confidence — community sources)
- Ham radio logging sort field priority: https://hamradioplayground.com/digital-modes-tech/logging-software/log-organize-qso-contacts
- Ham Radio Deluxe QSO field reference: https://support.hamradiodeluxe.com/support/solutions/articles/51000052691-creating-and-managing-qsos

---
*Research completed: 2026-04-20*
*Ready for roadmap: yes*
