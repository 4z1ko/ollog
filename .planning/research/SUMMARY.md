# Project Research Summary

**Project:** ollog v1.2 — Callsign Prefix Lookup & Country Flag Display
**Domain:** Ham radio QSO logbook — ITU prefix-to-country resolution + flag icons in log view
**Researched:** 2026-04-04
**Confidence:** HIGH

---

## Executive Summary

This milestone adds a self-contained, display-only feature to ollog: resolve the CALL field of each logged QSO to a country using the ITU prefix range table, then render the country's flag SVG inline in the log table. The feature is purely presentational — no new database schema, no new routes, no stored data. The entire addition reduces to one new Python module, one import, one dict key, and one template change. All major ham radio logging software (Ham Radio Deluxe, Log4OM, CloudLog) treats this as a baseline expectation; users will notice its absence.

The recommended implementation is intentionally minimal: bundle the ITU prefix range table (~340–600 rows) as a static Python list in `app/callsign/prefixes.py`, loaded once at import time. A `lookup_prefix(callsign)` function using a linear range scan (O(n) over < 800 rows = microseconds) returns an ISO 3166-1 alpha-2 code or `None`. This is injected into `_qso_to_view_dict()` as a `flag_iso` key. The flag SVG is already present at `app/static/flags/{iso}.svg` (271 files) but is currently unserved due to a static file mount path discrepancy that must be resolved first. One new dependency is added: `pycountry>=26.2.16` for ITU-name-to-ISO mapping at data build time (not at request time).

The primary risk is correctness, not performance. The ITU prefix model uses overlapping sub-ranges (e.g., `3DA–3DM` vs `3DN–3DZ`) that require longest-match resolution, not a flat scan. Callsigns may include portable suffixes (`/P`, `/MM`, `/AM`) that must be stripped before lookup, with specific rules for `MM` and `AM` which conflict with valid country prefixes. ITU country names use parenthetical forms that `pycountry.lookup()` rejects — a small override dict is required alongside `search_fuzzy()`. All three correctness risks are well-understood and have clear solutions documented in the research.

---

## Key Findings

### Recommended Stack

The existing stack (FastAPI 0.135+, Beanie 2.1+, Jinja2, HTMX 2.0.4, Python 3.12, MongoDB 7) requires only one new addition: `pycountry>=26.2.16`, a pure-Python library used to map ITU country names to ISO alpha-2 codes when building the static prefix table. All other capabilities — CSV parsing, linear/binary search, Jinja2 template rendering, static file serving — use Python stdlib or existing dependencies.

**Core technologies:**
- `pycountry>=26.2.16`: Map ITU country name strings to ISO 3166-1 alpha-2 at data-build time — handles ITU long-form names via `search_fuzzy()` that exact-match libraries like `iso3166` cannot handle
- `bisect` (stdlib): O(log n) range lookup if sorted list is preferred; linear scan is also acceptable at < 800 rows
- `csv` (stdlib): Parse the bundled ITU prefix CSV at module import time
- Jinja2 `<img>` tag (existing): Render flag SVGs — inline `<svg>` must NOT be used due to a confirmed HTMX namespace bug (htmx issue #2761)

**Critical prerequisite — static file path mismatch:** The `StaticFiles` mount in `app/main.py` points to the project root `static/` (currently empty). Flag SVGs live at `app/static/flags/`. Fix: `git mv app/static/flags static/flags` — zero code changes required, aligns with the existing Dockerfile `COPY static/ static/` line. This must be done before any flag rendering works.

### Expected Features

The feature set for v1.2 is small and tightly scoped. Everything beyond the MVP is explicitly deferred.

**Must have (table stakes):**
- Country flag icon next to callsign in log view — every major logger shows this; absence is noticed
- Graceful no-flag fallback — unknown prefix, empty CALL, or missing ISO code renders nothing, not a broken image
- Correct resolution for common DX callsigns — W, K, N, VE, G, DL, F, JA, VK, ZL must resolve correctly
- Portable suffix stripping — `/P`, `/M`, `/QRP`, `/MM`, `/AM`, single-digit call area indicators must be stripped before lookup
- Country name tooltip on flag — `title` attribute on `<img>`; zero JS required; name is already in the prefix table

**Should have (differentiators for v1.x after validation):**
- Flag in SSE live feed rows (`feed_row.html`) — separate template and context path; medium complexity
- Flag in inline-edit row (`qso_row_edit.html`) — prevents flag disappearing during edit/cancel cycle

**Defer to v2+:**
- DXCC "worked before" / new country indicator — requires per-operator worked-entity tracking
- CQ zone / ITU zone derivation — requires cty.dat or equivalent
- Award tracking (DXCC, WAS, WAZ, IOTA) — significant model complexity
- External callbook lookup (QRZ, HamQTH) — subscription APIs, network dependency, out of scope per PROJECT.md

**Anti-features (explicitly do not build):**
- Store `DXCC_COUNTRY` or `ISO_CODE` in the QSO document — ITU allocations change; baking display data into stored records creates stale data and future migration pain
- External CDN for flag images — self-hosted deployment model; CDN dependency breaks offline/air-gapped setups

### Architecture Approach

The architecture is additive with minimal coupling. A new `app/callsign/` package holds the static prefix table and lookup function. The only modifications to existing code are one import and one dict key in `_qso_to_view_dict()` in `ui_router.py`, and one `{% if qso.flag_iso %}<img>{% endif %}` block in `qso_row.html`. All three render paths (full page load, HTMX pagination partial, inline edit save) flow through `_qso_to_view_dict()`, so a single change covers all three automatically. No changes to the QSO model, MongoDB schema, service layer, ADIF import/export, auth, admin, or feed router.

**Major components:**
1. `app/callsign/prefixes.py` — Bundled ITU prefix range table as a Python list literal + `lookup_prefix(call: str) -> str | None` function; loaded once at import, zero I/O per call
2. `_qso_to_view_dict()` in `app/qso/ui_router.py` — Modified to call `lookup_prefix()` and add `flag_iso` key; this is the single correct injection point covering all render paths
3. `static/flags/<iso>.svg` — 271 flag SVGs (already present, needs path fix); served by existing `StaticFiles` mount; referenced via `<img>` tag only (never inline SVG)

**Build order (dependency-driven):**
1. Prefix data + `lookup_prefix()` — pure Python, no dependencies, fully unit-testable in isolation
2. Flag SVG path fix (`git mv app/static/flags static/flags`) — can run parallel to step 1
3. Wire `lookup_prefix()` into `_qso_to_view_dict()` — depends on step 1
4. Update `qso_row.html` template — depends on steps 2 and 3

### Critical Pitfalls

1. **Inline SVG in HTMX-swapped partials breaks rendering** — HTMX parses responses in the HTML namespace; SVG elements are silently mangled (confirmed htmx issue #2761). Use `<img src="/static/flags/{iso}.svg">` exclusively. Flags appear on first page load but vanish after pagination if this rule is violated.

2. **Flat range scan without longest-match fails on sub-ranges** — The ITU has overlapping allocations (e.g., `3DA–3DM` = Eswatini, `3DN–3DZ` = Fiji, sharing the `3D` stem). A flat list scanned in insertion order silently misclassifies callsigns. Always match the most-specific (longest common prefix) range by trying progressively shorter prefix candidates (3-char, then 2-char, then 1-char).

3. **`/MM` and `/AM` suffix stripping conflict** — `MM` is the ITU prefix for Scotland; `AM` is the prefix for Spain. `G3YWX/MM` is British maritime mobile, not a Scottish callsign. Strip these as operating suffixes; never resolve `MM` or `AM` as a country prefix when they follow a slash.

4. **ITU parenthetical country names fail `pycountry.lookup()`** — Names like `Germany (Federal Republic of)` and `Korea (Republic of)` raise `LookupError`. `search_fuzzy()` is not a safe primary method — it has documented silent wrong-results (e.g., `"Niger"` returns Nigeria). Use a static override dict keyed by exact ITU name strings as the primary lookup; `search_fuzzy()` as fallback only.

5. **Flag SVG path mismatch (must fix before rendering works)** — The `StaticFiles` mount serves `static/` at the project root, which is currently empty. Fix with `git mv app/static/flags static/flags`. Without this, all flag `<img>` tags return 404.

---

## Implications for Roadmap

This milestone decomposes into two phases following the architectural dependency chain.

### Phase 1: Prefix Resolver Module

**Rationale:** The prefix lookup function is the foundational dependency for everything else. It is pure Python with no FastAPI, MongoDB, or template coupling — it can be built, tested, and validated in complete isolation before any display work begins. Building it first eliminates the biggest correctness risks (sub-range matching, suffix stripping, ITU name normalization) before they can contaminate the integration layer.

**Delivers:** `app/callsign/prefixes.py` with the complete ITU prefix range table (bundled as a Python list literal or parsed from a bundled CSV), `lookup_prefix(callsign: str) -> str | None` with suffix stripping and longest-match range logic, and a test suite covering: common prefixes (W, K, DL, G, JA), sub-range cases (3DA/3DN), suffix stripping (`/P`, `/M`, `/MM`, `/AM`, single-digit), non-country entities (4U1, C7), and the no-match fallback.

**Addresses:** Correct flag for common DX callsigns, suffix handling, graceful fallback (table stakes)

**Avoids:**
- Pitfall 1: range comparison on raw strings
- Pitfall 2: flat scan without longest-match
- Pitfall 3: structural digit included in prefix
- Pitfall 4: suffixes not stripped before lookup
- Pitfall 5: non-country entities causing exceptions
- Pitfall 6: ITU parenthetical names failing pycountry

### Phase 2: Flag Display Integration

**Rationale:** Once `lookup_prefix()` is verified correct, the display integration is mechanical: fix the static file path, wire the resolver into `_qso_to_view_dict()`, and update the template. All three steps are low-risk additive changes with no structural impact on existing routes, models, or the database.

**Delivers:** Working country flag display in the log view — flag SVG served from `static/flags/`, `flag_iso` key injected via `_qso_to_view_dict()`, `<img>` rendered in `qso_row.html` with `title` tooltip and `onerror="this.style.display='none'"` fallback, `{% if qso.flag_iso %}` guard ensuring no broken images for unresolved callsigns.

**Uses:** `lookup_prefix()` from Phase 1, existing `StaticFiles` mount, existing `Jinja2Templates` instance, `<img>` tag (not inline SVG)

**Implements:** Modified `_qso_to_view_dict()` (architecture component 2) and flag SVG serving (architecture component 3)

**Avoids:**
- Pitfall 7: inline SVG breaks HTMX swap — use `<img>` exclusively
- Pitfall 8: CDN cascade on pagination — self-hosted static files, no external requests
- Pitfall 9: `_qso_to_view_dict()` not updated — this is the explicit implementation target
- Pitfall 10: N+1 DB queries — in-memory lookup from Phase 1, zero DB calls per row
- Pitfall 11: None rendered as string "None" — `{% if qso.flag_iso %}` guard

### Phase Ordering Rationale

- The resolver must exist and be tested before it can be wired into `_qso_to_view_dict()`. Phase 1 before Phase 2 is a hard dependency.
- The static file path fix (`git mv`) is a prerequisite for Phase 2 but is trivially fast — it is the first step of Phase 2, not a standalone phase.
- Both phases are small. Phase 1 carries the correctness complexity (domain knowledge required). Phase 2 is mechanical integration.
- SSE live feed (`feed_row.html`) and inline-edit row (`qso_row_edit.html`) flags are post-MVP and can be added as a Phase 3 or deferred to v1.x maintenance.

### Research Flags

Phases with standard patterns (no additional research needed):
- **Phase 1 (Prefix Resolver):** Algorithm is fully specified in FEATURES.md and ARCHITECTURE.md. Suffix rules, longest-match logic, and ITU name normalization strategy are all documented in detail. Data can be compiled directly from the ITU Appendix 42 table.
- **Phase 2 (Flag Display Integration):** HTMX `<img>` vs inline SVG decision is already resolved. `_qso_to_view_dict()` injection point is identified. Template guard pattern is specified. No unknowns remain.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | One new dependency (`pycountry`). All other tools are stdlib or existing. Static file path discrepancy is identified with a zero-code resolution (`git mv`). |
| Features | HIGH for core; MEDIUM for suffix edge cases | Core ITU allocation model is well-documented via ITU.int and Wikipedia. Suffix handling for geographic overrides (`/KH6`-style) relies on community consensus patterns rather than a single formal spec. The v1.2 scope decision (strip known operating suffixes, graceful fallback for the rest) is correct and pragmatic. |
| Architecture | HIGH | Based on direct codebase inspection. `_qso_to_view_dict()` as the injection point, `app/callsign/prefixes.py` as the new module, and `<img>` over inline SVG are all confirmed against actual code and confirmed HTMX behavior (htmx issue #2761). |
| Pitfalls | HIGH for critical pitfalls | Pitfalls 1–11 (v1.2 specific) are grounded in direct codebase inspection, ITU data format analysis, confirmed htmx issues, and pycountry GitHub issues. Not theoretical. |

**Overall confidence: HIGH**

### Gaps to Address

- **ITU prefix table data completeness:** The algorithm and format are specified but the actual CSV data (~340–600 rows) still needs to be compiled and bundled. Verify correctness by testing a representative sample including rare prefixes and sub-range callsigns (3DA, 3DN) after building the module.
- **pycountry override dict coverage:** The exceptions dict for ITU parenthetical names is specified in principle. The complete list of failing names depends on the actual ITU table content. Build iteratively: run name-to-ISO mapping at startup with logging, capture all `LookupError` and wrong-result cases, add to the override dict.
- **`/KH6`-style geographic suffix handling:** The v1.2 decision is to not attempt geographic-override suffix resolution — graceful no-flag fallback is acceptable. This is a deliberate scope decision, not a gap. Revisit in v1.x if operators frequently log remote operations with geographic suffixes.
- **Flag SVG coverage for edge-case entities:** The 271 existing SVGs cover ISO 3166-1 alpha-2 standard countries. Non-country ITU entities (1A, 4U1ITU, 4U1UN) correctly return `None` from the resolver and show no flag. The `onerror` handler in the template handles any remaining SVG-file gaps silently.

---

## Sources

### Primary (HIGH confidence)

- Direct codebase inspection — `app/qso/ui_router.py`, `templates/log/qso_row.html`, `templates/log/log_table.html`, `app/main.py`, `app/static/flags/` (2026-04-04)
- [ITU Table of International Call Sign Series (Appendix 42)](https://www.itu.int/en/ITU-R/terrestrial/fmd/Pages/call_sign_series.aspx) — authoritative prefix range allocations
- [pycountry on PyPI](https://pypi.org/project/pycountry/) — v26.2.16 API, `search_fuzzy()` behavior
- [Python bisect stdlib](https://docs.python.org/3/library/bisect.html) — O(log n) range lookup
- [htmx GitHub issue #2761](https://github.com/bigskysoftware/htmx/issues/2761) — confirmed SVG namespace break on HTMX partial swap
- [FastAPI Jinja2 custom filters](https://www.slingacademy.com/article/fastapi-jinja-how-to-create-custom-filters/) — `templates.env.filters[name] = fn` pattern

### Secondary (MEDIUM confidence)

- [ITU prefix — Wikipedia](https://en.wikipedia.org/wiki/ITU_prefix) — prefix structure, sub-range examples
- [Amateur radio call signs — Wikipedia](https://en.wikipedia.org/wiki/Amateur_radio_call_signs) — suffix conventions, structural digit
- [pyhamtools GitHub](https://github.com/dh1tw/pyhamtools) — confirms longest-prefix-match is the industry standard; used as counter-example for dependency reasons (DXCC names, lxml — do not use)
- [lipis/flag-icons](https://github.com/lipis/flag-icons) — MIT-licensed ISO alpha-2 SVG flag set, self-hosting reference
- [/MM and /AM conflict — river.cat](https://river.cat/radio/mobile-or-portable.html) — `/MM` vs MM Scotland, `/AM` vs AM Spain documented community pattern

### Tertiary (LOW confidence)

- pycountry GitHub issues #126, #129, #242 — `search_fuzzy()` failure cases for specific country names; behavior may vary by version; validate against `pycountry>=26.2.16` during integration

---

*Research completed: 2026-04-04*
*Ready for roadmap: yes*
