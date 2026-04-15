# Research Summary: v2.3 Operator Statistics

**Project:** ollog — Ham Radio Online Logbook
**Milestone:** v2.3 Operator Statistics
**Researched:** 2026-04-15
**Confidence:** HIGH

---

## Stack Additions

No new Python dependencies. The only net-new technology is **Chart.js 4.5.1**, loaded via jsDelivr CDN `<script>` tag inside `templates/log/stats.html` only — never in `base.html`. Use the UMD bundle (`dist/chart.umd.min.js`) because Chart.js v4 also ships an ESM-only build that cannot be loaded via a plain `<script>` tag and silently fails with "Chart is not defined."

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
```

All aggregation is done with `QSO.get_motor_collection().aggregate([...])` — no new Python package, no change to `requirements.txt`. DXCC entity resolution uses the existing `lookup_prefix()` (already in `app/callsign/prefixes.py`) and `pycountry` (already a project dependency imported in `ui_router.py`). The Tailwind build does not change — Chart.js color values are hardcoded hex in JS config, not Tailwind class names.

**Why CDN-only:** `npm` in this project exists exclusively to build Tailwind CSS. Adding Chart.js to `package.json` would require a JS bundler. The CDN delivery path is Chart.js's documented primary installation method for non-bundled use and is consistent with how HTMX and htmx-ext-sse are already loaded in this codebase.

---

## Feature Table Stakes

These are required for the page to feel complete. Missing any of these at launch makes the page feel broken or half-built.

| Feature | Why Required | Notes |
|---------|-------------|-------|
| QSO count by band — pie chart | First question every operator asks | `$group` on `BAND` field |
| QSO count by mode — pie chart | Second most common question | `$group` on `MODE` field |
| Top 8 DXCC entities by QSO count — pie chart | Core DX question; QScope and QSL Buddy both lead with this | Python-side callsign rollup via `lookup_prefix()` |
| Total unique DXCC entities worked — scalar | The number operators track obsessively | Count distinct ISO codes before top-8 truncation |
| Data scoped to authenticated operator | The entire premise of ollog | `$match: {_operator: callsign}` first in every pipeline |
| Sidebar nav link | Operators will not find the page otherwise | Bar-chart Heroicon + "Statistics" label in `base_app.html` |
| Empty-state for zero QSOs | New operators get a broken-looking blank chart without it | `{% if stats.total_qsos == 0 %}` guard in template |

**Defer to v2.x or later:** date range filtering, per-band DXCC matrix, QSO rate/activity charts, continent breakdown, award progress indicators, LoTW confirmation status, PDF/CSV export, gridsquare map, distance calculations.

**The "Other" bucket convention:** When the operator has worked more than 8 DXCC entities, the remainder are summed into a single "Other" slice. Only append "Other" when there are actually remaining entities — a guard in service.py prevents a zero-value "Other" slice from appearing on logs with 8 or fewer entities.

---

## Architecture Pattern

The stats page is a minimal extension of the existing request flow. No new router, no new module, no new collection.

```
GET /log/stats  (HttpOnly cookie JWT)
        |
        v
get_current_operator_callsign_cookie(request)   [exists]
        |  -> returns operator callsign string
        v
get_stats(operator)   [NEW -- app/qso/service.py]
        |
        |  Pipeline 1: $match _operator + $group BAND -> band_counts dict
        |  Pipeline 2: $match _operator + $group MODE -> mode_counts dict
        |  Pipeline 3: $match _operator + $group CALL -> per-callsign cursor
        |      -> Python loop: lookup_prefix(call) + pycountry -> entity_counts dict
        |      -> sort, take top 8, sum rest into "Other"
        |      -> unique_dxcc = len(entity_counts) before truncation
        |
        |  Returns: {band_counts, mode_counts, dxcc_counts, unique_dxcc, total_qsos}
        v
stats_page route   [NEW -- app/qso/ui_router.py]
        |  TemplateResponse("log/stats.html", {"stats": stats_data})
        v
templates/log/stats.html   [NEW]
        |  var bandData = {{ stats.band_counts | tojson }};
        |  var modeData = {{ stats.mode_counts | tojson }};
        |  var dxccData = {{ stats.dxcc_counts | tojson }};
        |  -> Chart.js initializes three pie charts from inline JSON
        v
Browser renders three pie charts + DXCC count scalar
```

**Files changed:**
- `app/qso/service.py` — add `get_stats(operator: str) -> dict`
- `app/qso/ui_router.py` — add `GET /log/stats` route (two lines of logic)
- `templates/base_app.html` — add Stats nav item to sidebar block
- `templates/log/stats.html` — new file; extends `base_app.html`
- `templates/base.html` — add `{% block extra_scripts %}{% endblock %}` before `</body>`

No changes to `app/main.py` — `ui_router` is already mounted at `/log`.

**DXCC aggregation is Python-side, not MongoDB-side.** `lookup_prefix()` is a pure-Python bisect function. It cannot run inside a MongoDB aggregation expression. The correct pattern is: aggregate by `CALL` in MongoDB (returning per-callsign counts), then resolve DXCC in Python, then re-aggregate by entity name. At typical log scales (hundreds of unique callsigns) this runs in under 5 ms.

**Beanie aggregation access:** Use `QSO.get_motor_collection().aggregate([...])` with `await cursor.to_list(length=None)`. Beanie does not expose `aggregate()` as a Document class method; `get_motor_collection()` returns the underlying Motor collection directly, which is the established pattern in this codebase (see `app/feed/manager.py`).

---

## Critical Pitfalls

**1. Stale canvas — "Canvas is already in use"**
Chart.js registers chart instances against canvas elements. On bfcache restore or HTMX re-swap, calling `new Chart(canvas, ...)` on an already-owned canvas throws a silent JS error and the chart disappears. Prevention: guard every `new Chart(...)` with `Chart.getChart(canvas)?.destroy()` before creating the new instance. Hook `htmx:afterSettle` to re-init if the stats page content re-enters the DOM.

**2. ESM vs UMD bundle confusion**
Chart.js v4 ships `dist/chart.js` (ESM only) and `dist/chart.umd.min.js` (CDN-safe). Loading the wrong file produces `Chart is not defined` with no useful error. Always use `chart.umd.min.js` and pin the exact semver (`@4.5.1`), never `@latest`.

**3. Canvas sizing collapses to zero inside Tailwind flex/grid**
Chart.js derives canvas dimensions from its parent container. In Tailwind flex/grid layouts, the parent may report zero width during the first render frame. Prevention: wrap each `<canvas>` in `<div class="relative h-64 w-full">` and set `maintainAspectRatio: false` in Chart.js options.

**4. $match must be first in every aggregation pipeline**
If `$group` precedes `$match`, MongoDB performs a full collection scan across all operators' data. The compound index (`_operator`, `_deleted`) is only used when `$match` is the first pipeline stage. Every stats pipeline must begin with `{"$match": {"_operator": callsign, "_deleted": False}}`.

**5. Use `| tojson` — never `| safe` — for inline JSON in `<script>` tags**
`| safe` on raw Python dict output passes literal `<script>` to the browser (XSS). With autoescaping on, direct substitution turns `"` into `&quot;`, producing invalid JavaScript. `| tojson` calls `json.dumps` with HTML-escaping and marks the result as `Markup`. It is the only correct filter for this pattern. No exceptions.

**Bonus — dark mode colors are baked in at Chart.js creation time.** Read `document.documentElement.classList.contains('dark')` at chart init to pick legend/tooltip colors. When `toggleTheme()` is called, destroy and recreate the charts with the correct color set.

---

## Build Order

Dependency-ordered. Each step is independently testable before moving to the next.

1. **`app/qso/service.py` — write `get_stats()`**
   Hardest part: DXCC rollup logic, pipeline correctness, edge cases. Write and test in isolation. Validate: `$match` is first, null/empty-string BAND/MODE map to "Unknown" via `$cond`, "Other" is only appended when more than 8 entities exist, `unique_dxcc` is computed before top-8 truncation.

2. **`app/qso/ui_router.py` — add `GET /log/stats` route**
   Two lines: call `get_stats(callsign)`, return `TemplateResponse`. Unblocks template work immediately.

3. **`templates/log/stats.html` — build the template**
   Extend `base_app.html`. Set `{% block active_page %}stats{% endblock %}`. Three `<canvas>` wrappers (`<div class="relative h-64 w-full">`). Inline JSON via `| tojson`. Chart.js CDN `<script>` before chart init script. Empty-state guard. Dark mode color detection at init time.

4. **`templates/base_app.html` — add Stats nav item**
   Bar-chart Heroicon at `w-6 h-6`. Active class conditional on `ap == 'stats'`. One block, one link, one icon.

5. **`templates/base.html` — add `{% block extra_scripts %}`**
   Insert `{% block extra_scripts %}{% endblock %}` immediately before `</body>`. Does not affect any existing page.

---

## Watch Out For

**The `| tojson` filter is the single most dangerous omission.** Every implementation of server-rendered Chart.js data skips it "just this once" because the data looks safe. It is never safe — entity names like "Korea, Republic of" contain commas and quotes; pathological callsigns have slash-separated suffixes. Omitting `| tojson` will either produce a JavaScript syntax error (breaking all three charts silently) or, if `| safe` is used as a workaround, an XSS vector. Use `| tojson` on every single inline data variable. No exceptions.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Chart.js 4.5.1 confirmed from CDN; UMD vs ESM confirmed from v4 migration docs; CDN pattern consistent with existing codebase |
| Features | HIGH | Cross-referenced QScope, QSL Buddy; direct codebase audit of `lookup_prefix()` and pycountry imports; PROJECT.md v2.3 requirements confirmed |
| Architecture | HIGH | Fully code-verified against live codebase; route, service, template, and auth dependency patterns all confirmed |
| Pitfalls | HIGH (Chart.js API, MongoDB) / MEDIUM (HTMX bfcache) | Stale-canvas and sizing confirmed from official docs and GitHub issues; ollog uses plain `<a href>` nav so bfcache risk is lower than full HTMX-boosted apps |

**Overall confidence:** HIGH

**Gaps to address during implementation:**
- Confirm the exact name and location of `toggleTheme()` in `base_app.html` before wiring the dark mode re-init wrapper.
- Confirm the exact closing tag structure of `templates/base.html` before adding `{% block extra_scripts %}` to avoid a double-closing `</body>`.

---

## Sources

**Primary (HIGH confidence):**
- `/Users/royco/ollog/app/qso/ui_router.py` — route patterns, `_qso_to_view_dict`, cookie auth dependency (code verified)
- `/Users/royco/ollog/app/qso/service.py` — service layer conventions (code verified)
- `/Users/royco/ollog/app/callsign/prefixes.py` — `lookup_prefix()` returns ISO alpha-2 or None (code verified)
- `/Users/royco/ollog/templates/base_app.html` — sidebar nav pattern, `{% block active_page %}` (code verified)
- `/Users/royco/ollog/.planning/PROJECT.md` — v2.3 requirements confirmed
- `https://cdn.jsdelivr.net/npm/chart.js@latest/package.json` — version 4.5.1 confirmed
- `https://www.chartjs.org/docs/latest/getting-started/installation.html` — CDN UMD bundle
- `https://www.chartjs.org/docs/latest/migration/v4-migration.html` — ESM vs UMD split
- `https://www.chartjs.org/docs/latest/developers/api.html` — `.destroy()`, `.getChart()`
- `https://www.mongodb.com/docs/manual/core/aggregation-pipeline-optimization/` — `$match` first for index
- Context7 `/beanieodm/beanie` — `.aggregate()`, `get_motor_collection()`

**Secondary (MEDIUM confidence):**
- `https://github.com/chartjs/Chart.js/discussions/9214` — maintainer confirmed no native dark mode
- `https://www.qscope.org/public/` — band/mode/entity pie charts as table stakes
- `https://www.qslbuddy.com/features` — top countries / band/mode distribution pattern

---

*Research completed: 2026-04-15*
*Ready for roadmap: yes*
