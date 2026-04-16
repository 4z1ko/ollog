# Pitfalls Research: Chart.js Statistics Page on FastAPI/HTMX/Jinja2

**Domain:** Adding Chart.js pie charts + MongoDB aggregation to an existing HTMX/Jinja2/Tailwind v3 app
**Researched:** 2026-04-15
**Overall confidence:** HIGH (Chart.js API), HIGH (MongoDB aggregation), MEDIUM (HTMX+Chart.js interaction)

---

## Chart.js + HTMX Pitfalls

### Pitfall 1: Stale Canvas — "Canvas is already in use"

**What goes wrong:** Chart.js registers chart instances against canvas elements. When HTMX swaps new content into the DOM that includes a `<canvas>` with the same ID, and then the page navigates back and swaps the same canvas in again, the previous Chart.js instance is still registered. Attempting to `new Chart(canvas, ...)` on an already-owned canvas throws:

```
Error: Canvas is already in use. Chart with ID '0' must be destroyed before the canvas can be reused.
```

**Why it happens:** Chart.js stores a reference to every created chart instance keyed by canvas element. HTMX page transitions using `hx-push-url` or partial swaps do not automatically destroy JS objects — only the DOM is replaced. The canvas may be new DOM but the Chart.js internal registry retains the old binding if cleanup was skipped.

**Consequences:** JS errors that silently kill chart rendering. Second visit to the stats page shows a broken canvas. No error visible to the user.

**Prevention:** Guard every `new Chart(...)` call with a destroy check using `Chart.getChart()` (available Chart.js 3.x+). Store instances so they can be cleaned up:

```javascript
// Store instances at module scope
const charts = {};

function initCharts() {
  ['band-chart', 'mode-chart', 'dxcc-chart'].forEach(function(id) {
    var canvas = document.getElementById(id);
    if (!canvas) return;
    // Destroy any prior instance on this canvas before re-creating
    var existing = Chart.getChart(canvas);
    if (existing) existing.destroy();
    charts[id] = new Chart(canvas, /* config */);
  });
}

// Re-init on HTMX page transitions
document.body.addEventListener('htmx:afterSettle', function() {
  if (document.getElementById('band-chart')) initCharts();
});
```

**Detection:** Open stats page, navigate away to Log View, navigate back. Open browser console and check for "Canvas is already in use" error.

**Note:** `chart.destroy()` is confirmed as the correct cleanup in Chart.js v4.x docs. The `destroy` plugin hook was removed in v4; use `afterDestroy` in plugins instead.

---

### Pitfall 2: Chart.js CDN Bundle Confusion — ESM vs UMD

**What goes wrong:** Chart.js v4 ships two bundles. The ESM build at `dist/chart.js` cannot be loaded via a plain `<script>` tag without a bundler. Loading it via CDN produces `Chart is not defined` with no useful error.

**Why it happens:** In Chart.js v4, the dist files were renamed: `dist/chart.js` is now ESM only; `dist/chart.umd.min.js` is the CDN-safe build. (The old `dist/chart.min.js` was removed.)

**Prevention:** Use the UMD build explicitly and pin a version:

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.9/dist/chart.umd.min.js"></script>
```

Avoid `@latest` — breaking minor versions happen. The last Chart.js version with available SRI hashes via jsdelivr is v3.9.1. For v4.x, pin a semver and skip SRI or compute the hash manually. Either way, pin the exact version in the template.

---

### Pitfall 3: Chart.js Canvas Sizing Fails to Zero Inside Tailwind Flex/Grid Containers

**What goes wrong:** Chart.js uses the parent container's computed dimensions to size the canvas. In a Tailwind `flex` or `grid` layout, the parent may report zero or unconstrained width during the first render frame, causing the chart to render at 0×0 or stretch to full viewport width.

**Why it happens:** Chart.js documentation states: "Chart.js relies on its parent container to update both the canvas render and display sizes. This method requires the container to be relatively positioned and dedicated to the chart canvas only." Flexbox and grid cannot signal the canvas element to shrink via normal CSS resize.

**Consequences:** Chart renders invisibly or at full viewport width. `maintainAspectRatio: true` (the default) will cause height to derive from zero width — resulting in a zero-height chart.

**Prevention (from official docs):**
- Wrap each `<canvas>` in a dedicated `<div>` with `position: relative` and an explicit height.
- Use Tailwind classes that produce explicit dimensions on the wrapper: `relative h-64 w-full`.
- Set `maintainAspectRatio: false` in Chart.js options when the container controls the height.
- Do NOT apply margin or padding directly to the `<canvas>` element — apply it to the wrapper div.

```html
<!-- Correct: wrapper provides dimensions, canvas fills it -->
<div class="relative h-64 w-full">
  <canvas id="band-chart"></canvas>
</div>
```

```javascript
new Chart(canvas, {
  type: 'pie',
  options: {
    responsive: true,
    maintainAspectRatio: false,  // required when container controls height
  }
});
```

---

### Pitfall 4: HTMX Intercepts Navigation Away From Stats Page Without Cleanup

**What goes wrong:** If the stats page uses full-page HTMX navigation (hx-boost style) rather than a hard page load, the `<canvas>` elements and their Chart.js instances persist in memory until garbage collected. There is no automatic "page unload" cleanup event in HTMX partial-swap navigation.

**Why it matters for ollog specifically:** The ollog navigation uses plain `<a href>` links for sidebar nav items (confirmed from `base_app.html`). These trigger full-page navigation, not HTMX swaps. This means browsers DO fire unload events and the canvas IS destroyed. The stale-canvas problem (Pitfall 1) only applies on back-navigation when the browser restores a cached page from bfcache.

**Prevention:** Wrap chart init in the `htmx:afterSettle` listener AND in `DOMContentLoaded` to cover both fresh loads and cached restores. The destroy-before-init guard in Pitfall 1 is sufficient protection.

---

## Dark Mode Pitfalls

### Pitfall 1: Chart.js Colors Are Baked In at Creation Time

**What goes wrong:** Chart.js does not natively observe CSS variables or Tailwind's `dark:` class at render time. Colors in `backgroundColor`, `borderColor`, `color` (legend/tooltip fonts), and grid line colors are evaluated once during `new Chart(...)`. When the user clicks the existing `toggleTheme()` button in `base_app.html`, existing charts do not update.

**Why it happens:** The Chart.js maintainers explicitly confirmed that detecting dark mode dynamically is too slow to be included in the core update cycle. There is no CSS-variable binding mechanism in Chart.js options.

**Consequences in ollog:** The existing `base_app.html` uses class-based dark mode (`darkMode: 'class'` in Tailwind config). The toggle adds/removes the `dark` class on `<html>`. After toggle, chart legend text and tooltip text remain at their creation-time colors — potentially invisible (dark text on dark background).

**Prevention options (in order of preference for ollog):**

**Option A — Read dark state at init, re-create charts on toggle (recommended):**
```javascript
function isDarkMode() {
  return document.documentElement.classList.contains('dark');
}

function getChartDefaults() {
  var dark = isDarkMode();
  return {
    legendColor: dark ? '#e5e7eb' : '#374151',
    tooltipBg:   dark ? '#1c1c1e' : '#ffffff',
    tooltipBody: dark ? '#f2f2f7' : '#111827',
  };
}

// Extend the existing toggleTheme() to also re-init charts
// Wrap, don't override — preserves the existing localStorage logic
(function() {
  var _orig = window.toggleTheme;
  window.toggleTheme = function() {
    _orig.call(this);
    if (document.getElementById('band-chart')) initCharts();
  };
})();
```

**Option B — CSS filter inversion (not recommended for ollog):**
The Chart.js community suggests `filter: invert(1) hue-rotate(180deg)` on canvas elements for dark mode. This inverts the pixel buffer. It is acceptable for monochrome charts but produces incorrect hues for the saturated pie slice colors ollog will use. Not appropriate here.

**Option C — chart.update() with mutated dataset colors:**
For pie charts (no scales), `chart.update()` after mutating `data.datasets[0].backgroundColor` works. However, legend label colors and tooltip colors require updating `options.plugins.legend.labels.color` and `options.plugins.tooltip.bodyColor` before calling `update()`. The destroy+recreate approach (Option A) is simpler and more reliable.

---

### Pitfall 2: Canvas Background Is Transparent; Dark Surface Shows Through Correctly

**What goes wrong:** Chart.js canvas backgrounds are transparent by default. This is actually correct behavior for ollog — the canvas sits on the `bg-surface-light dark:bg-surface-dark` card, so the dark mode card surface (`#1c1c1e`) shows through correctly.

**When it becomes a problem:** If a chart card uses a pure white or pure black card surface, the legend text may be invisible. The ollog surface tokens are `#ffffff` (light) and `#1c1c1e` (dark) — mid-range values that contrast well with both dark and light chart colors.

**Prevention:** No action needed for display. Document for future: if chart PNG export is added, use the `customCanvasBackgroundColor` plugin to bake a background into exports.

---

### Pitfall 3: Tailwind Purge Drops Dynamically Constructed Color Classes

**What goes wrong:** This is a known ollog pitfall documented in PROJECT.md decision log. Any Tailwind class constructed dynamically (via JavaScript or Jinja2 string concatenation) is invisible to the Tailwind scanner and is purged from `output.css`.

**Specific risk for the stats page:** Stat summary numbers styled with conditional color classes. Example:

```html
<!-- Wrong: scanner cannot see "text-green-600" or "text-red-600" -->
<span class="text-{{ 'green' if count > 0 else 'red' }}-600">{{ count }}</span>
```

**Prevention:** Write all Tailwind classes as complete literal strings. Use conditional blocks instead of string construction:

```html
{% if count > 0 %}
<span class="text-green-600 dark:text-green-400">{{ count }}</span>
{% else %}
<span class="text-red-600 dark:text-red-400">{{ count }}</span>
{% endif %}
```

Run `npm run verify` after adding new dark mode classes to confirm they appear in `output.css`.

---

## MongoDB Aggregation Pitfalls

### Pitfall 1: Missing or Null BAND/MODE Fields Collapse Into a Single "null" Bucket

**What goes wrong:** In MongoDB aggregation, `$group` with `_id: "$BAND"` treats both missing fields and explicit `null` values as the same group key: `null`. The ollog `BAND` and `MODE` fields are declared `Optional[str] = None` in the Beanie model. ADIF records imported from other logging software may omit these fields entirely.

**Why it happens:** ADIF import stores only fields present in the source file. Historical imports may have incomplete band/mode data. MongoDB's aggregation treats missing fields as `null` in expression contexts.

**Consequences:** A pie chart slice labeled `null` or `None` appears in the UI, confusing operators. This bucket may be large for imported logs.

**Prevention:** Use `$ifNull` in the `$group _id` expression:

```python
pipeline = [
    {"$match": {"_operator": operator_callsign, "_deleted": False}},
    {"$group": {
        "_id": {"$ifNull": ["$BAND", "Unknown"]},
        "count": {"$sum": 1}
    }},
    {"$sort": {"count": -1}}
]
```

---

### Pitfall 2: Empty String and null Are Different Group Keys

**What goes wrong:** Some logging software exports `BAND=""` (empty string) rather than omitting the field. MongoDB treats `""` and `null` as different group keys. A pipeline using `$ifNull` handles null/missing but leaves empty strings as a separate `""` bucket.

**Prevention:** Use `$cond` to collapse both null and empty string:

```python
"_id": {
    "$cond": {
        "if": {"$and": [
            {"$ne": ["$BAND", None]},
            {"$ne": ["$BAND", ""]}
        ]},
        "then": "$BAND",
        "else": "Unknown"
    }
}
```

---

### Pitfall 3: $match Must Precede $group to Use the Compound Index

**What goes wrong:** If the aggregation pipeline starts with `$group` before `$match`, MongoDB performs a full collection scan and groups ALL documents before filtering by `_operator`. With a shared `qsos` collection (multi-operator), this scans every operator's data regardless of who is requesting.

**Why it happens:** MongoDB's query planner can use an index only when `$match` is the first stage. `$group` is a blocking stage and cannot be pushed earlier by the optimizer.

**The existing indexes in `QSO.Settings.indexes` are:**
- `operator_idx` on `(_operator)` — single field
- `operator_qso_compound` on `(_operator, CALL, qso_date_utc, BAND, MODE)`

Both indexes will be used only if `$match` on `_operator` is the first stage.

**Prevention:** Always start stats pipelines with:
```python
{"$match": {"_operator": operator_callsign, "_deleted": False}}
```

Then `$group`, then `$sort`, then optional `$limit`.

---

### Pitfall 4: DXCC Lookup Performance — Python Loop vs. MongoDB-level Grouping

**What goes wrong:** DXCC entity grouping cannot be done in MongoDB because the ITU prefix resolver (`lookup_prefix()`) is a pure-Python bisect function on an in-memory prefix table. The aggregation must group by `CALL` in MongoDB, then resolve DXCC in Python, then re-aggregate by entity.

**Why it matters:** For a 5,000-QSO log with 1,000 unique callsigns, this is ~1,000 `lookup_prefix()` calls in a Python loop. The function is O(log n) on the ~313-entry prefix table. At ~1 µs per call, 1,000 calls takes ~1 ms — acceptable.

**At what scale does it become a problem:** At 50,000 unique callsigns (unlikely for a self-hosted club log), the loop takes ~50 ms. Not a blocker.

**Prevention:** No caching needed for v2.3. If profiling shows this is slow in a specific deployment, cache the `{CALL: dxcc_entity}` mapping in a dict keyed by callsign for the lifetime of the request. Do not add pre-emptive complexity.

**Fallback labeling:** When `lookup_prefix()` returns no match (maritime mobile `/MM`, aeronautical `/AM`, unknown prefix), use the label `"DX"` or `"Other"` rather than the raw callsign prefix.

---

### Pitfall 5: The "Top 8 + Other" Grouping Has Edge Case Failures

**What goes wrong:** Grouping the top 8 DXCC entities and collapsing the rest into "Other" has three failure modes:
1. Fewer than 8 entities → appending "Other" with count 0 creates a zero-slice in the pie chart.
2. All QSOs unresolvable → all land in "Other," and the top 8 are empty.
3. Zero QSOs total → empty arrays → Chart.js renders an empty pie (no error, but confusing).

**Prevention — guard all edge cases in the service layer:**

```python
sorted_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)
top8 = sorted_entities[:8]
rest = sorted_entities[8:]

labels = [e[0] for e in top8]
values = [e[1] for e in top8]

# Only add "Other" if there are remaining entities to collapse
if rest:
    labels.append("Other")
    values.append(sum(e[1] for e in rest))

# Return empty lists gracefully — Chart.js handles empty pie without error
```

---

## JSON Data Injection Pitfall

### Pitfall 1: Unsafe Jinja2 Variable Embedding in `<script>` Tags

**What goes wrong:** Passing server data to Chart.js via direct Jinja2 variable substitution inside `<script>` blocks breaks in two ways:
- With autoescaping on: `"` becomes `&quot;`, `<` becomes `&lt;` — the JSON is syntactically invalid JavaScript.
- With `| safe` to suppress autoescaping: user-controlled data (e.g., callsign names or DXCC entity names with special characters) can inject `</script>` and break out of the script block (XSS).

**Prevention:** Use the `| tojson` filter. In FastAPI/Jinja2 (Starlette), `tojson` produces a JSON-safe string that is marked as `Markup` (bypasses autoescaping safely) and properly escapes `</script>` sequences:

```html
<script>
  var bandData = {{ band_data | tojson }};
  var modeData = {{ mode_data | tojson }};
  var dxccData = {{ dxcc_data | tojson }};
</script>
```

Where `band_data` is a Python dict like `{"labels": [...], "values": [...]}` returned from the service layer.

**Alternative — data attribute + JSON.parse:**
```html
<div id="chart-data"
     data-bands="{{ band_data | tojson }}"
     data-modes="{{ mode_data | tojson }}">
</div>
<script>
  var el = document.getElementById('chart-data');
  var bandData = JSON.parse(el.dataset.bands);
</script>
```

Both are safe. `| tojson` inline in `<script>` is simpler and standard for FastAPI/Jinja2.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| MongoDB aggregation service | Missing/null BAND or MODE creates "null" bucket | Use `$cond` in `$group._id` to map null and `""` to "Unknown" |
| MongoDB aggregation service | `$match` not first → full collection scan | Always place `$match` on `_operator` as the first pipeline stage |
| MongoDB aggregation service | Empty string distinct from null | Use `$cond` checking both `$ne: null` and `$ne: ""` |
| DXCC entity aggregation service | Python loop over unique CALLs | Acceptable for <50K unique callsigns; no pre-emptive caching |
| DXCC top-8 collapsing | Fewer than 8 entities → zero-value "Other" slice | Guard: only append "Other" if `rest` is non-empty |
| DXCC top-8 collapsing | Zero QSOs → empty arrays | Chart.js handles empty pie gracefully; add a "no data" message in the template |
| Chart.js CDN loading | ESM vs UMD bundle confusion | Use `chart.umd.min.js`; pin exact semver version |
| Chart.js canvas sizing | Zero width in Tailwind flex/grid | Wrap `<canvas>` in `<div class="relative h-64 w-full">`; set `maintainAspectRatio: false` |
| Chart.js dark mode | Colors baked at creation time | Read `isDarkMode()` at init; re-init charts on `toggleTheme()` |
| Chart.js + HTMX navigation | Stale canvas on back-navigation | Use `Chart.getChart(canvas)` + `.destroy()` guard before every `new Chart()` |
| Jinja2 data injection | `| safe` filter + user data → XSS | Use `| tojson` filter exclusively for JSON data in `<script>` tags |
| Tailwind purge | Dynamic class construction in templates | Write all dark-mode and color classes as complete literal strings |

---

## Sources

- Chart.js Responsive Configuration (canvas sizing, container requirements): https://www.chartjs.org/docs/latest/configuration/responsive.html
- Chart.js API (.destroy(), .getChart()): https://www.chartjs.org/docs/latest/developers/api.html
- Chart.js v4 Migration Guide (dist bundle renames, destroy hook removal): https://www.chartjs.org/docs/latest/migration/v4-migration.html
- Chart.js Colors: https://www.chartjs.org/docs/latest/general/colors.html
- Chart.js Canvas Background: https://www.chartjs.org/docs/latest/configuration/canvas-background.html
- Chart.js Dark Mode Discussion (maintainer confirmed no native support): https://github.com/chartjs/Chart.js/discussions/9214
- "Canvas is already in use" error pattern: https://github.com/reactchartjs/react-chartjs-2/issues/1037
- MongoDB $group documentation: https://www.mongodb.com/docs/manual/reference/operator/aggregation/group/
- MongoDB $ifNull documentation: https://www.mongodb.com/docs/manual/reference/operator/aggregation/ifNull/
- MongoDB Aggregation Pipeline Optimization ($match first for index use): https://www.mongodb.com/docs/manual/core/aggregation-pipeline-optimization/
- Jinja2 XSS via script-context variable injection: https://semgrep.dev/docs/cheat-sheets/flask-xss
- HTMX Events reference (htmx:afterSettle, htmx:beforeCleanupElement): https://htmx.org/events/
- jsDelivr SRI usage and version pinning: https://www.jsdelivr.com/using-sri-with-dynamic-files
