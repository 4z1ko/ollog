# Phase 43: Stats UI - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the Phase 42 stub `templates/log/stats.html` with a fully functional statistics page containing three Chart.js pie charts (By Band, By Mode, By DXCC Entity), a unique DXCC entity scalar, a sidebar nav link, and correct dark/light theme support — all without a page reload on theme toggle.

**Not in scope:** New Python services or aggregation pipelines (those are complete in Phase 42), new database queries, external API lookups, date/year filtering, award tracking.

</domain>

<decisions>
## Implementation Decisions

### Sidebar Nav Link
- **D-01:** Add the "Stats" nav link **after "Log View"** and before "Import". New sidebar order: Log QSO → Log View → Stats → Import → Export → Profile → About. This groups Stats with the two "viewing your log" actions before the data import/export tools.

### Claude's Discretion
- **Chart grid layout:** Use a 2-column responsive grid for Band + Mode charts (top row), with the DXCC Entity chart spanning full width below. Rationale: DXCC has up to 8 labeled slices and benefits from more horizontal space; Band and Mode charts typically have 3–6 slices each. On mobile, all three stack vertically.
- **Page width:** Use `max-w-5xl mx-auto` (wider than the `max-w-2xl` stub and the `max-w-3xl` profile page) to accommodate three charts comfortably.
- **Summary metrics placement:** Keep "Total QSOs: N" in a compact summary row at the top of the page (above the charts). Render "Unique DXCC entities: M" inline with the DXCC chart title as a subtitle (e.g. "By DXCC Entity · 42 entities") rather than in a separate card — this keeps the chart and its scalar co-located.
- **Dark mode hook:** Modify `toggleTheme()` in `templates/base_app.html` to dispatch `window.dispatchEvent(new CustomEvent('themechange'))` after updating the theme class. In `stats.html`'s `{% block extra_scripts %}`, listen with `window.addEventListener('themechange', reinitCharts)`. This is a clean extension point that doesn't require overriding `toggleTheme()` from within a child template.
- **Chart color palettes:** Dark mode — indigo/violet/emerald/amber/sky/rose/teal/orange family (muted/pastel). Light mode — same hues but slightly saturated. Use a single `PALETTES` object with `dark` and `light` arrays; select at chart-init time based on `document.documentElement.classList.contains('dark')`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pre-decided Architecture (Phase 43 is constrained by these)
- `.planning/STATE.md` §"v2.3 Architecture Decisions" — Chart.js CDN delivery (UMD bundle, jsDelivr), `| tojson` safety requirement, canvas sizing (`h-64 w-full` wrapper + `maintainAspectRatio: false`), stale canvas guard, `{% block extra_scripts %}` insertion point, dark mode re-init requirement

### Templates to Modify
- `templates/base.html` — must add `{% block extra_scripts %}{% endblock %}` immediately before `</body>` (currently has no such block; line 40 is `</body>`)
- `templates/base_app.html` — sidebar nav (`{% block sidebar_nav %}`), `toggleTheme()` function (must dispatch CustomEvent for dark mode re-init), `nav-item` and `nav-item-active` CSS classes
- `templates/log/stats.html` — Phase 42 stub to be fully replaced (currently renders only total_qsos and unique_entity_count scalars, no charts)

### Phase 42 Deliverables (data shape provider)
- `app/stats/router.py` — template context keys: `band_counts` (dict), `mode_counts` (dict), `entity_counts` (list of `{name, count}`), `unique_entity_count` (int), `total_qsos` (int), `callsign` (str)
- `.planning/phases/42-stats-aggregation-backend/42-01-SUMMARY.md` — what was built, confirmed data shape, test coverage

### Requirements
- `.planning/REQUIREMENTS.md` §STATS-01, STATS-02, STATS-03, STATS-04, STATS-05, STATS-08 — phase 43 requirements (sidebar link, band chart, mode chart, DXCC chart with top-8 + Other, unique entity scalar, dark/light theme support)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `nav-item` / `nav-item-active` CSS classes (defined in Tailwind `@layer components`): used by every sidebar link in `base_app.html`. Stats link must use the same classes with the same `{{ 'nav-item-active' if ap == 'stats' else '' }}` pattern.
- `{% block active_page %}stats{% endblock %}` is already set in the Phase 42 stub — the sidebar active-state mechanism is wired.
- `card`, `card-header`, `card-title` component classes: available for the summary metrics row and any content cards on the stats page.
- `toggleTheme()` function in `base_app.html` `<script>` block (lines ~158–164): toggles `dark` class on `document.documentElement`, saves to `localStorage`, calls `updateThemeIcons()`. Adding `window.dispatchEvent(new CustomEvent('themechange'))` to the end of this function is the extension point.

### Established Patterns
- Template inheritance: `stats.html` extends `base_app.html` which extends `base.html`. Chart.js script tag and chart init JS go in `{% block extra_scripts %}` (to be added to `base.html`).
- All UI routes pass `callsign` to the template context — `base_app.html` uses `{{ callsign }}` in the user info section.
- Inline JSON injection: `{{ band_counts | tojson }}`, `{{ mode_counts | tojson }}`, `{{ entity_counts | tojson }}` — the `tojson` Jinja2 filter produces safe JSON-encoded strings for `<script>` variable assignment.
- Dark mode detection: `document.documentElement.classList.contains('dark')` — correct at chart-init time.

### Integration Points
- `templates/base.html:40` — insert `{% block extra_scripts %}{% endblock %}` before `</body>`
- `templates/base_app.html` sidebar nav block — insert Stats `<a>` after the Log View `<a>` block
- `templates/base_app.html` `toggleTheme()` — append CustomEvent dispatch
- `templates/log/stats.html` — full replacement of stub

</code_context>

<specifics>
## Specific Ideas

- The Phase 42 stub already has `{% block active_page %}stats{% endblock %}` set — no change needed to the active-state detection logic, just need the nav link added with `ap == 'stats'` check.
- Chart.js bar-chart Heroicon for the Stats nav link: `M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z` (Heroicons `ChartBarIcon`, solid variant) — consistent with other nav icons which are 24x24 outline stroke SVGs. Use the outline variant `M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z` to match existing nav icons.
- Chart.js CDN URL from STATE.md: `https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js` — load only in `stats.html`'s extra_scripts block, not in base.html.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 43-stats-ui*
*Context gathered: 2026-04-16*
