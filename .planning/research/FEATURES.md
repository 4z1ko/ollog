# Features Research

**Domain:** Operator statistics page — ham radio logbook (ollog v2.3)
**Researched:** 2026-04-15
**Confidence:** HIGH (cross-referenced QScope, QSL Buddy, Ham Radio Deluxe, ADIF spec, and direct codebase audit of existing `app/callsign/prefixes.py`)

---

## Table Stakes

Features that every ham radio stats page provides. An operator loading `/log/stats` for the first time expects all of these. Missing any of these makes the page feel incomplete or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| QSO count by band (pie chart) | First question every operator asks: "Which band have I used most?" QScope, QSL Buddy, and Logger32 all lead with band distribution. | LOW | MongoDB `$group` on `BAND` field with `$sum: 1`. BAND values are ADIF-standard lowercase strings ("20m", "40m", etc.). Render as pie chart. |
| QSO count by mode (pie chart) | Second most common: "Do I mostly do FT8 or SSB?" All survey tools show mode breakdown. | LOW | MongoDB `$group` on `MODE` field. Modes are ADIF uppercase strings: FT8, SSB, CW, FM, etc. Render as pie chart. |
| Top N DXCC entities by QSO count (pie chart) | "Who have I contacted most internationally?" is the core DX question. QScope's entity distribution chart and QSL Buddy's "top countries" are both table stakes in the genre. | MEDIUM | Requires `lookup_prefix(CALL)` at query time OR a MongoDB aggregation that post-processes CALL values. See domain notes below. |
| Total unique DXCC entities worked (scalar) | Single number: "I've worked 47 DXCC entities." This is the ham radio equivalent of a leaderboard number — operators track this obsessively. Every logging app displays it prominently. | MEDIUM | Count of distinct resolved entity names (or ISO codes) across operator's log. Unresolvable calls (None from lookup_prefix) are excluded. |
| Data scoped to authenticated operator | Log isolation is the entire premise of ollog. Stats must filter by `_operator == callsign` exactly as QSO queries do. | LOW | Use same `get_current_operator_callsign_cookie` dependency already used in all UI routes. Pass operator callsign into MongoDB `$match` at the start of each aggregation pipeline. |
| Page linked from sidebar nav | No operator will find a stats page by guessing the URL. It must be in the nav alongside Log and Profile. | LOW | Add a nav item in `base_app.html` sidebar block pointing to `/log/stats`. Use a bar-chart Heroicon at `w-6 h-6` to match existing nav icon sizing. |

---

## Differentiators

Features found in better ham radio logging tools that set them apart. Not expected by a new user, but valued by experienced operators. These improve the page without being required for v2.3 MVP.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Total QSO count scalar | Headline number — "You have 1,247 QSOs." Provides context for all the charts. Trivial to add alongside the DXCC count. | LOW | Single `$match` + `$count` aggregation. Display at top of page before charts. |
| "Other" bucket for DXCC entities beyond top N | When showing top 8 entities, grouping the remainder as "Other" prevents the pie from becoming unreadable. QScope does this natively for entity charts. Without it, a 47-entity operator gets a 47-slice pie chart. | LOW | Already in PROJECT.md as a target feature. Aggregate top 8 by count, sum the rest into a single "Other" slice. |
| Empty log state | A new operator with zero QSOs gets a blank pie chart, which looks broken. A friendly message ("No QSOs yet — log a contact to see your stats") is expected. | LOW | Check total QSO count first; if 0, render an empty-state template instead of chart JS. |
| Country name display (not ISO code) | Showing "United States" or "Germany" next to a pie slice is far more readable than "US" or "DE". Ham radio culture is callsign-country-aware — operators recognize entity names. | LOW | `lookup_prefix` returns an ISO alpha-2 code. Use `pycountry` (already a project dependency per `ui_router.py` imports) to convert ISO code → country name. For None-ISO entities (non-country ITU entities like 4U1ITU), show "Non-Country Entity" or skip. |
| Bands ordered by frequency (not count) | Band charts are more readable when ordered by wavelength (160m → 10m → 6m → 2m → 70cm) rather than by QSO count. The former matches the mental model operators use. QScope uses this ordering. | LOW | Sort aggregation results client-side or server-side using a fixed ordered list matching ADIF BAND enumeration order before rendering. |
| Responsive layout for mobile/tablet | Operators check stats from their phone. Pie charts at full desktop width are unreadable at 375px width. | LOW | Tailwind responsive grid (already used throughout the app) — stack charts vertically on mobile using `md:grid-cols-2` or similar. Chart.js charts are inherently responsive via `maintainAspectRatio: false` + container sizing. |

---

## Anti-Features

Features that seem natural for a ham radio stats page but are wrong for this project's scope, scale, and complexity budget.

| Anti-Feature | Why It Seems Natural | Why to Avoid | What to Do Instead |
|--------------|---------------------|--------------|-------------------|
| Per-band DXCC matrix (band × entity grid) | Log4OM and QScope show a band/entity matrix for DXCC Challenge tracking | Requires a 2D aggregation (band × entity), far more complex rendering, and is only useful to operators pursuing the DXCC Challenge award. Project scope explicitly defers award tracking. | Show entity totals across all bands. Per-band entity breakdown is a v3+ feature when award tracking is addressed. |
| Award progress indicators (DXCC, WAS, WAZ) | "You need 53 more entities for DXCC" is a natural next step | Award tracking requires a reference list (CTY.DAT or ARRL DXCC entity list), confirmation status (LoTW), and significant business logic. PROJECT.md explicitly defers this to v2+. | Display raw worked count only — no progress bars, no "X more needed." |
| Real-time stats refresh via SSE | The live log table already uses SSE — extending it to stats seems consistent | Stats aggregations are expensive relative to a log table row fetch. Running a full DXCC aggregation on every QSO insert would cause visible latency under burst logging (e.g. FT8 sessions). Stats are inherently a snapshot, not a stream. | Stats page is a static render on page load. Operator manually reloads to refresh. If wanted later, add a manual "Refresh" button. |
| Date range filtering on stats | "Show me stats for just this year" or "stats for this contest weekend" | Adds filter state, URL params, and significantly more complex UI and query logic. Scope creep for v2.3. | Stats always cover the operator's entire log. Date filtering is a v3+ consideration. |
| QSO rate charts (QSOs per hour/day) | QScope shows hourly rate charts; useful for contest operators | Contest analysis is not the use case for ollog. The app targets club station / multi-operator casual logging. Rate charts require time-series aggregation and a time-series chart type (not pie), adding rendering complexity. | Defer to a future "activity insights" phase if operators request it. |
| Interactive/clickable pie slices | "Click this slice to see all 20m QSOs" — drill-down navigation | Requires deep linking into the QSO log with pre-set filters, which the filter system would need to support as URL params. Significant plumbing for modest UX gain. | Charts are display-only. The existing QSO log has its own filter controls. |
| Gridsquare map / worked grids | QSL Buddy shows a gridsquare map; visually impressive | Requires a mapping library (Leaflet or similar) — a new dependency. Gridsquare data is rarely present in QSOs logged via this app's web UI (no MY_GRIDSQUARE capture per QSO, only MY_GRIDSQUARE on operator profile). Most QSOs would be unplotted. | Gridsquare stats require first building a gridsquare capture workflow, which is not part of v2.3. |
| DX distance calculation | "Longest contact: 12,000 km to VK2ABC" | Requires lat/lon for both stations. Operator's lat/lon is derived from their gridsquare (profile), but the worked station's location is not stored — would require a callsign lookup API (QRZ/HamQTH). PROJECT.md explicitly defers callsign lookup to v2+. | Omit. No external API calls in v2.3. |
| Export stats as PDF or CSV | QScope provides stats export | Significant rendering complexity (PDF generation in Python). QSO export to ADIF already exists for operators who want to analyze in external tools. | Document the ADIF export path as the way to run external analysis. |
| Continent breakdown | QScope shows QSOs by continent (AF, AS, EU, NA, OC, SA, AN) | Continent → ITU entity mapping is a separate lookup from the existing prefix resolver. The existing `prefixes.py` resolves to ISO country code, not continent. Deriving continent from ISO code requires a second mapping table not present in the codebase. | DXCC entity breakdown already serves the geographic insight need. Continent breakdown adds a new dependency for marginal extra value. |

---

## Ham Radio Domain Notes

### What "Worked DXCC Entity" Means in ollog Context

The formal DXCC program (ARRL) requires confirmed two-way contacts and uses the official ARRL DXCC entity list (340 current entities). ollog does NOT implement the formal DXCC award program — that is explicitly deferred.

For the v2.3 stats page, "DXCC entity worked" means: **a unique resolved entity name derived from the CALL field of a QSO using the existing `lookup_prefix()` function.** Specifically:

- `lookup_prefix(CALL)` returns an ISO 3166-1 alpha-2 code (e.g. "DE"), or `None`
- ISO code `None` means the callsign resolved to a non-country ITU entity (4U1ITU, UN, etc.) or was unresolvable (maritime mobile, parse failure)
- For stats purposes: count distinct non-None ISO codes as unique entities
- Unresolvable calls (None) are excluded from the DXCC entity pie and count — they represent real contacts but cannot be attributed to an entity
- The "unique entity count" scalar = count of distinct ISO codes (not distinct country names, since one country can have multiple ITU Series Ranges)

This approach is intentionally simpler than CTY.DAT-based resolution (which the formal DXCC program uses). It is the correct trade-off for v2.3 because the callsign prefix resolver already exists, is tested, and is already used in the log table (flags). No new dependency is introduced.

### What Counts as "Worked" vs "Confirmed"

The stats page shows worked counts only (any QSO with a resolved entity = worked). Confirmed (QSL received, LoTW match) is not tracked in ollog. PROJECT.md defers LoTW integration to v2+. Do not add QSL status language to the stats page — it implies a confirmation workflow that does not exist.

### DXCC "Top N + Other" Convention

QScope uses this pattern. The convention in ham radio stats is:

- Show the top 8 entities by QSO count (or whatever N fits the chart)
- Group all remaining entities as "Other" with a combined count
- If the operator has worked fewer than 8 entities, show all of them with no "Other"
- The "Other" slice is typically rendered in a neutral gray

PROJECT.md specifies "top 8 DXCC entities." This is a reasonable number — most pie chart libraries become unreadable beyond 8-10 slices.

### Band Display Order

ADIF band values are case-insensitive strings. The standard ordering in ham radio software (QScope, N1MM, Logger32, WSJT-X) goes from longest wavelength to shortest: 160m, 80m, 60m, 40m, 30m, 20m, 17m, 15m, 12m, 10m, 6m, 4m, 2m, 1.25m, 70cm, 33cm, 23cm, and microwave bands beyond. For a pie chart, sorting by QSO count descending (largest slice first) is more visually useful than wavelength order. The legend alongside the pie chart can list bands in wavelength order if implemented, but this is a low-priority detail.

### DXCC Aggregation Implementation Strategy

The existing `lookup_prefix()` is a pure Python function — it cannot run inside a MongoDB aggregation pipeline. Two implementation approaches:

**Option A — Python-side resolution (recommended for v2.3):**
1. `$match` by `_operator` and `_deleted: false`
2. `$group` by `CALL` to get unique callsigns and their counts
3. Fetch the result set in Python (typically a few hundred unique callsigns at most)
4. Call `lookup_prefix(call)` for each unique callsign
5. Aggregate counts by ISO code
6. Sort and take top 8, sum remainder as "Other"

This avoids storing derived DXCC data in documents and keeps the resolver as the single source of truth. At typical ham radio logbook scale (hundreds to low thousands of QSOs, dozens to a few hundred unique callsigns), Python-side resolution is fast enough — sub-100ms for 500 unique callsigns.

**Option B — Store resolved entity on QSO document:**
Stamp a `_dxcc_iso` field at QSO insert time (REST API + UDP paths). Then aggregate directly in MongoDB. Risk: the prefix resolver can be updated; stored values become stale. Also requires a migration for existing QSOs. Avoid for v2.3.

**Recommendation:** Use Option A. Do not modify the QSO data model for stats.

### Dependency Map

```
Stats page (/log/stats)
    └── GET /log/stats  (new route in app/qso/ui_router.py)
        ├── get_current_operator_callsign_cookie  (exists)
        ├── MongoDB aggregation ($match _operator + $group BAND, $group MODE)  (new)
        ├── MongoDB aggregation ($match _operator + $group CALL)  (new)
        ├── lookup_prefix(CALL)  (exists in app/callsign/prefixes.py)
        ├── pycountry.countries.get(alpha_2=iso)  (pycountry already a dependency)
        └── Chart.js (new JS dependency — CDN or bundled)
            └── Note: Chart.js is the standard for lightweight browser charting
                in HTMX/Jinja2 stacks. No npm build step needed if loaded from CDN.
                Tailwind build does not need to change.
```

### Chart Library Choice

Chart.js is the correct choice for this project:

- No npm build pipeline change — load from CDN in the stats template (or copy to `static/js/`)
- Pie chart type is built-in: `new Chart(ctx, { type: 'pie', data: {...} })`
- Responsive out of the box — works with Tailwind container sizing
- Dark mode support: pass `color` options via Chart.js `plugins.legend.labels.color` keyed on the existing `dark` class detection logic (already present in the app's theme toggle JS)
- Well-documented, stable, widely used — not an exotic choice

Avoid D3.js (too complex for three pie charts), Highcharts (commercial license), ApexCharts (heavier than needed).

---

## Feature Dependencies

```
All stats features
    └── require: GET /log/stats route (new)
        └── require: operator callsign from cookie (exists)

DXCC pie chart + unique entity count
    └── require: lookup_prefix() (exists in app/callsign/prefixes.py)
    └── require: pycountry.countries.get() for country name display (exists as project dep)
    └── note: NO new dependencies — existing resolver is sufficient

Band pie chart, Mode pie chart
    └── require: MongoDB $group aggregation by BAND / MODE
    └── no new dependencies

Chart rendering
    └── require: Chart.js (new JS dep — CDN load in stats template only)
    └── no Tailwind build change required if loaded from CDN

Sidebar nav link
    └── require: base_app.html sidebar block edit (1 line)
    └── require: Heroicon bar-chart SVG at w-6 h-6

Country name display (differentiator)
    └── require: pycountry (already a project dependency)
    └── note: pycountry.countries.get(alpha_2=iso) — returns None for ITU non-country entities where iso is None (already handled by Option A pipeline)
```

---

## MVP Definition

### v2.3 Launch With

- [ ] `/log/stats` route rendering a Jinja2 template (new endpoint in `app/qso/ui_router.py`)
- [ ] Band pie chart (QSO count by BAND)
- [ ] Mode pie chart (QSO count by MODE)
- [ ] DXCC entities pie chart (top 8 + "Other")
- [ ] Total unique DXCC entities worked scalar
- [ ] All data scoped to authenticated operator via `_operator` field
- [ ] Sidebar nav link to `/log/stats`
- [ ] Empty-state handling when operator has zero QSOs

### Defer to v2.x

- [ ] Total QSO count scalar (trivial addition, low priority)
- [ ] Continent breakdown (requires a new ISO-to-continent mapping table)
- [ ] Date range filtering
- [ ] Per-band DXCC matrix
- [ ] QSO rate / activity over time charts

### Out of Scope (v3+ or never for this project)

- Award progress tracking (deferred in PROJECT.md to v2+)
- LoTW confirmation status in stats
- Map/gridsquare visualization
- Export to PDF/CSV

---

## Sources

- Codebase audit: `/Users/royco/ollog/app/callsign/prefixes.py` (confirmed `lookup_prefix()` returns ISO alpha-2 or None), `/Users/royco/ollog/app/qso/ui_router.py` (confirmed pycountry already imported)
- PROJECT.md v2.3 requirements: active requirements list at lines 169-174
- QScope.org feature set: https://www.qscope.org/public/ (confirmed band/mode/entity pie charts are table stakes in ham radio log analysis tools)
- QSL Buddy features: https://www.qslbuddy.com/features (confirmed "top countries, band/mode distribution charts" pattern)
- ADIF 3.1.6 BAND field enumeration: https://adif.org/316/ADIF_316.htm (confirmed band values are lowercase strings; case-insensitive per spec)
- DXCC rules and entity definition: https://arrl.org/dxcc-rules (340 current entities; "worked" = two-way communication established; formal award program requires confirmation — intentionally not implemented in v2.3)
- Club Log DXCC discrepancy explanation: https://clublog.freshdesk.com/support/solutions/articles/53208 (confirmed why prefix-based counting differs from formal DXCC — ollog's simpler approach is correct for non-award-tracking stats)
- Chart.js: https://www.chartjs.org/ (confirmed pie chart type, CDN availability, responsive design, no build step required)

---
*Feature research for: operator statistics page — ollog ham radio logbook v2.3*
*Researched: 2026-04-15*
