# Phase 43: Stats UI - Research

**Researched:** 2026-04-16
**Domain:** Chart.js 4.x pie charts, Jinja2 template inheritance, Tailwind dark mode, browser CustomEvent
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (Sidebar order):** Add "Stats" nav link after "Log View" and before "Import". New order: Log QSO → Log View → Stats → Import → Export → Profile → About.
- **D-02 (Chart.js delivery):** CDN UMD bundle `chart.umd.min.js@4.5.1` via jsDelivr, loaded only in `stats.html` `{% block extra_scripts %}`, never in `base.html`.
- **D-03 (Data safety):** `| tojson` filter on all inline JSON variables — never `| safe`, never bare substitution. XSS vector for entity names.
- **D-04 (Canvas sizing):** Each `<canvas>` in `<div class="relative h-64 w-full">` + `maintainAspectRatio: false`.
- **D-05 (Stale canvas guard):** `Chart.getChart(canvas)?.destroy()` before every `new Chart(...)`.
- **D-06 (Dark mode hook):** Append `window.dispatchEvent(new CustomEvent('themechange'))` to `toggleTheme()` in `base_app.html`. In `stats.html`, listen with `window.addEventListener('themechange', reinitCharts)`.
- **D-07 (extra_scripts block):** Add `{% block extra_scripts %}{% endblock %}` to `base.html` immediately before `</body>` (line 40).
- **D-08 (Page width):** `max-w-5xl mx-auto`.
- **D-09 (Summary placement):** "Total QSOs: N" in a compact summary card above charts. "Unique DXCC entities: M" inline with DXCC chart title as subtitle.
- **D-10 (DXCC chart layout):** Band + Mode in 2-column responsive grid (top row); DXCC Entity chart full-width below.

### Claude's Discretion

- Chart grid layout, page width, summary placement, dark mode hook implementation — all decided (listed above, carried from CONTEXT.md Claude's Discretion section which the user agreed on).
- Color palettes (defined in UI-SPEC): dark = `['#818cf8','#34d399','#fbbf24','#60a5fa','#f472b6','#a78bfa','#2dd4bf','#fb923c']`, light = `['#4f46e5','#059669','#d97706','#2563eb','#db2777','#7c3aed','#0d9488','#ea580c']`.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STATS-01 | Operator can access a statistics page at `/log/stats` via a "Stats" link in the sidebar nav | Sidebar nav modification in `base_app.html` — nav-item pattern verified, `ap == 'stats'` already wired in stub |
| STATS-02 | Stats page displays a pie chart of QSO count by band | Chart.js `type: 'pie'` with `band_counts` dict from service; CDN URL verified 200 OK |
| STATS-03 | Stats page displays a pie chart of QSO count by mode | Chart.js `type: 'pie'` with `mode_counts` dict from service |
| STATS-04 | Stats page displays a pie chart of top 8 DXCC entities; remaining grouped as "Other" (only if non-empty) | `entity_counts` list from service already implements top-8 + conditional "Other" guard |
| STATS-05 | Stats page displays scalar count of unique DXCC entities worked | Rendered inline in DXCC chart title: "By DXCC Entity · N entities" using `unique_entity_count` from context |
| STATS-08 | Charts adapt to dark/light theme toggle without page reload | CustomEvent pattern from `toggleTheme()` → `reinitCharts` listener verified against Chart.js `.destroy()` + recreation |
</phase_requirements>

---

## Summary

Phase 43 is a pure frontend/template phase. All backend work (aggregation pipelines, DXCC rollup, route, tests) is complete from Phase 42. The template context already provides five keys: `band_counts` (dict), `mode_counts` (dict), `entity_counts` (list of `{name, count}`), `unique_entity_count` (int), `total_qsos` (int).

The work is confined to four files: `templates/base.html` (add extra_scripts block), `templates/base_app.html` (add Stats nav link + CustomEvent dispatch), and `templates/log/stats.html` (full replacement of Phase 42 stub). No Python changes, no new dependencies, no database changes.

The highest-risk integration point is Tailwind's purge scanner — any new `dark:` Tailwind classes must appear as complete literal strings in the scanned template files. The project already uses `npm run build` + `npm run verify` to catch this. Chart.js color palette hex values are used as JavaScript string literals, not as Tailwind classes, so they don't risk purge.

**Primary recommendation:** Implement as three tasks: (1) base.html extra_scripts block, (2) base_app.html sidebar + toggleTheme patch, (3) stats.html full replacement. Run `npm run build` and `uv run pytest tests/test_stats.py` after task 3 to verify.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Data aggregation | API/Backend (Phase 42, complete) | — | Already done; `get_stats()` service returns all data |
| Template rendering | Frontend Server (Jinja2/FastAPI) | — | Router passes context dict to TemplateResponse |
| Chart initialization | Browser/Client | — | Chart.js runs in browser; reads inline JSON injected by Jinja2 |
| Dark mode re-init | Browser/Client | — | `CustomEvent` dispatch from `toggleTheme()` triggers chart teardown/recreation |
| Tailwind class purge | CDN/Static (build step) | — | `npm run build` compiles output.css; new dark: classes must be present as literals |
| Nav active state | Frontend Server (Jinja2) | Browser/Client | `ap == 'stats'` evaluated server-side; `.nav-item-active` class applied in HTML |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Chart.js (UMD) | 4.5.1 | Pie charts with legend, responsive canvas | Pre-decided in STATE.md; ESM build silently fails; CDN verified 200 OK |
| Tailwind CSS | 3.x (project) | Styling and dark mode classes | Project standard; `darkMode: 'class'` config |
| Jinja2 (FastAPI/Starlette) | project version | Template inheritance, `tojson` filter | Project standard; `| tojson` is the XSS-safe inline data injection pattern |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Chart.js `getChart()` static | 4.5.1 | Retrieve existing chart instance by canvas element | Stale canvas guard before every `new Chart(...)` |
| Browser `CustomEvent` | Web standard | Theme change broadcast | Appended to `toggleTheme()` to decouple theme toggle from chart re-init |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CDN UMD bundle | npm install + bundler | No bundler in this project; CDN is the correct delivery method |
| `| tojson` | `| safe` or bare `{{ var }}` | `| safe` is an XSS vector for entity names with commas/quotes; `tojson` is required |
| CustomEvent pattern | Override `toggleTheme()` from child | Child template cannot reliably override a function defined in parent `<script>`; event dispatch is a clean extension point |

**Installation:** No new packages. Chart.js loaded via CDN `<script>` tag in stats.html.

**Version verification:** `npm view chart.js version` returns `4.5.1` [VERIFIED: npm registry]. CDN URL `https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js` returns HTTP 200 [VERIFIED: curl probe, 2026-04-16].

---

## Architecture Patterns

### System Architecture Diagram

```
Browser request GET /log/stats
        |
        v
[FastAPI stats_router] ← cookie auth (get_current_operator_callsign_cookie)
        |
        v
[get_stats(callsign)] → MongoDB aggregation (Phase 42, complete)
        |                Returns: band_counts, mode_counts, entity_counts,
        |                         unique_entity_count, total_qsos
        v
[TemplateResponse "log/stats.html"]
        |
        v
[Jinja2 renders HTML] → inline JSON via | tojson
        |                template context injected into <script> variables
        v
[Browser receives HTML]
        |
        ├── [Chart.js CDN script loaded] (in extra_scripts block)
        |
        ├── [DOMContentLoaded] → initCharts()
        |       ├── Read dark/light from documentElement.classList
        |       ├── Pick PALETTES.dark or PALETTES.light
        |       ├── Chart.getChart(canvas)?.destroy() × 3
        |       └── new Chart(canvas, config) × 3
        |
        └── [themechange event] → reinitCharts()
                ├── dispatched by toggleTheme() in base_app.html
                └── destroys + recreates all 3 charts with new palette
```

### Recommended Project Structure

No new files or directories. Changes confined to:

```
templates/
├── base.html                  # ADD: {% block extra_scripts %}{% endblock %} before </body>
├── base_app.html              # MODIFY: sidebar nav + toggleTheme() CustomEvent
└── log/
    └── stats.html             # REPLACE: Phase 42 stub → full Chart.js implementation
```

### Pattern 1: Jinja2 extra_scripts Block

**What:** A Jinja2 block placed immediately before `</body>` in `base.html` that child templates can override to inject page-specific scripts.

**When to use:** Any child template needing scripts that must run after the DOM is ready, but scoped only to that page (e.g., Chart.js — not loaded on every page).

**Example:**
```html
<!-- base.html — immediately before </body> (line 40) -->
{% block extra_scripts %}{% endblock %}
</body>
```

```html
<!-- stats.html — override to inject Chart.js -->
{% block extra_scripts %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
<script>
  // chart initialization
</script>
{% endblock %}
```

[VERIFIED: base.html read confirms line 40 is `</body>` with no existing extra_scripts block]

### Pattern 2: Inline JSON Safety via `| tojson`

**What:** Jinja2's `tojson` filter encodes Python dicts/lists as safe JSON strings, escaping quotes and special characters.

**When to use:** Any time template variables containing user-controlled or arbitrary-string data are injected into a `<script>` block as JavaScript literals.

**Example:**
```javascript
// Source: STATE.md §v2.3 Architecture Decisions
const bandData   = {{ band_counts   | tojson }};
const modeData   = {{ mode_counts   | tojson }};
const entityData = {{ entity_counts | tojson }};
```

`band_counts` is a dict (e.g., `{"20M": 15, "40M": 8}`). `entity_counts` is a list of `{name, count}` dicts. Entity names can contain commas, apostrophes, and quotes (e.g., "Côte d'Ivoire", "United States") — `tojson` handles all of these safely.

### Pattern 3: Chart.js Pie Chart with Stale Canvas Guard

**What:** Destroy any existing Chart instance before creating a new one on the same canvas element.

**When to use:** Every `new Chart(...)` call — required on bfcache restore and theme re-init.

**Example:**
```javascript
// Source: [CITED: https://www.chartjs.org/docs/latest/developers/api.html]
function makeChart(canvasId, labels, values, palette, textColor) {
  const canvas = document.getElementById(canvasId);
  Chart.getChart(canvas)?.destroy();  // stale canvas guard
  return new Chart(canvas, {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: palette.slice(0, values.length),
        borderWidth: 2,
        borderColor: 'transparent',
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: { color: textColor }
        }
      }
    }
  });
}
```

### Pattern 4: Theme Re-init via CustomEvent

**What:** Dispatch a named CustomEvent from `toggleTheme()` so child-template scripts can re-initialize theme-sensitive components without coupling the parent template to specific chart instances.

**When to use:** Any page with dark/light-sensitive JavaScript components (charts, custom color renderers).

**Example:**
```javascript
// In base_app.html — append to end of toggleTheme() body:
function toggleTheme() {
  var isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  updateThemeIcons(isDark);
  window.dispatchEvent(new CustomEvent('themechange'));  // ADD THIS LINE
}

// In stats.html extra_scripts:
window.addEventListener('themechange', reinitCharts);
```

[VERIFIED: base_app.html read confirms toggleTheme() at lines 176-180; exact text confirmed]

### Pattern 5: Data Transformation from Template Context to Chart.js

**What:** The service returns `band_counts` as a Python dict and `entity_counts` as a list of `{name, count}` objects. Chart.js `data.labels` and `data.datasets[0].data` need parallel arrays.

**Example:**
```javascript
// band_counts = {"20M": 15, "40M": 8, "10M": 3}
const bandData = {{ band_counts | tojson }};
const bandLabels = Object.keys(bandData);
const bandValues = Object.values(bandData);

// entity_counts = [{"name": "United States", "count": 42}, ...]
const entityData = {{ entity_counts | tojson }};
const entityLabels = entityData.map(e => e.name);
const entityValues = entityData.map(e => e.count);
```

### Anti-Patterns to Avoid

- **Loading Chart.js in base.html:** Loads the 220KB UMD bundle on every page, not just stats. Load only in stats.html's extra_scripts block.
- **Using `| safe` for entity names:** Entity names contain quotes and commas that break JavaScript string literals and are XSS vectors. Always use `| tojson`.
- **Skipping stale canvas guard:** Without `Chart.getChart(canvas)?.destroy()`, navigating back to the page via bfcache (browser forward-back cache) creates a second Chart instance on an already-registered canvas, causing a console error and visual corruption.
- **Creating charts before DOMContentLoaded:** `document.getElementById()` returns null if the DOM is not ready. Wrap initialization in `document.addEventListener('DOMContentLoaded', ...)`.
- **Putting dark: classes only in JavaScript strings:** Tailwind's purge scanner reads template HTML, not JS runtime values. Dark mode classes must appear as complete literal strings in `.html` template files or `input.css`.
- **Setting `maintainAspectRatio: true` (default) in Tailwind grid:** Tailwind grid/flex containers give canvas zero width at first render; `maintainAspectRatio: false` + fixed-height wrapper (`h-64`) is the required pattern.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pie chart rendering | Custom SVG pie chart | Chart.js `type: 'pie'` | Canvas scaling, legend, tooltip, responsive behavior are complex |
| JSON encoding for inline scripts | Manual escaping of quotes/commas | `{{ var \| tojson }}` Jinja2 filter | Entity names with apostrophes and Unicode would break manual escaping |
| Chart instance registry | Custom `window.chartInstances` dict | `Chart.getChart(canvasElement)` | Chart.js maintains its own registry; double-registration causes errors |

**Key insight:** Chart.js 4.x already solves canvas lifecycle, responsive sizing, legend rendering, and tooltip formatting. The only custom code needed is palette selection and the CustomEvent listener.

---

## Common Pitfalls

### Pitfall 1: Missing extra_scripts Block in base.html

**What goes wrong:** `{% block extra_scripts %}` in `stats.html` silently renders as empty string. No error — Chart.js CDN script and init code are swallowed.

**Why it happens:** Jinja2 child-template block overrides only work if the parent template declares the block. `base.html` currently has no `{% block extra_scripts %}` block (verified at line 40: bare `</body>`).

**How to avoid:** Task 1 must add `{% block extra_scripts %}{% endblock %}` to `base.html` before `</body>`. Verify by loading stats page and checking if Chart.js is present in browser DevTools Network tab.

**Warning signs:** Stats page loads without charts; browser console shows `Chart is not defined`; Network tab shows no chart.js request.

### Pitfall 2: Chart.js ESM vs UMD Build

**What goes wrong:** Loading the ESM build (e.g., `chart.esm.js` or importing from npm without a bundler) causes `ReferenceError: Chart is not defined` because the global `Chart` variable is not set.

**Why it happens:** ESM modules require `import` syntax or `type="module"` script tags and do not expose global variables. This project has no bundler.

**How to avoid:** Always use `chart.umd.min.js` from the CDN URL. [VERIFIED: STATE.md architecture decisions lock this choice. CDN URL confirmed 200 OK.]

### Pitfall 3: Tailwind Purge Removing New dark: Classes

**What goes wrong:** New dark-mode Tailwind classes (e.g., `dark:text-gray-200`, `dark:border-gray-800`) do not appear in `static/css/output.css`, so dark mode styling is missing.

**Why it happens:** Tailwind v3 scans `templates/**/*.html` for class strings at build time. Classes generated dynamically in JavaScript or added only as partial strings are not picked up.

**How to avoid:** Write complete Tailwind class strings as literals in the `.html` template. Run `npm run build` after any template change. Run `npm run verify` to assert dark mode + color-scheme classes are present in output.css.

**Warning signs:** Dark mode looks wrong; `grep "dark:text-gray-200" static/css/output.css` returns no match.

### Pitfall 4: Empty palette slice assignment

**What goes wrong:** If more slices than palette colors exist (9+ bands or entities), `palette.slice(0, values.length)` falls short and Chart.js repeats the last color for overflow slices.

**Why it happens:** The palette has 8 colors. More than 8 slices are possible for band_counts or mode_counts (rare but possible with active operators).

**How to avoid:** The palette length (8) matches the top-8 DXCC cap. For Band and Mode charts, wrap with a modulo fallback: `values.map((_, i) => palette[i % palette.length])` to cycle colors rather than truncate.

### Pitfall 5: `toggleTheme()` CustomEvent Dispatched Before DOM is Ready

**What goes wrong:** If `themechange` fires before `stats.html`'s listener is registered, reinitCharts is never called.

**Why it happens:** Race between script load order and DOMContentLoaded. Not an issue in practice because `toggleTheme()` is called by user interaction (button click), which always happens after DOMContentLoaded. No special ordering required — document this as a non-issue.

**How to avoid:** Register `window.addEventListener('themechange', reinitCharts)` inside the `extra_scripts` block (synchronous, before user can click the button). This is the established pattern.

### Pitfall 6: `base_app.html` `</script>` Placement When Appending to toggleTheme()

**What goes wrong:** Appending code after the closing `}` of `toggleTheme()` but before the `</script>` tag accidentally adds to the outer function scope rather than inside `toggleTheme()`.

**Why it happens:** `base_app.html` has `toggleTheme()` followed immediately by `updateThemeIcons()`, `DOMContentLoaded` listener, and `htmx:afterSettle` listener — all in the same `<script>` block (lines 163-205). The CustomEvent dispatch must go inside `toggleTheme()`, not appended after line 180.

**How to avoid:** Read the exact closing brace of `toggleTheme()` before editing (confirmed at line 180: `}`). Insert `window.dispatchEvent(new CustomEvent('themechange'));` on a new line before this closing brace.

---

## Code Examples

Verified patterns from official sources and codebase inspection:

### Complete Chart Init Function (Verified Pattern)
```javascript
// Source: [CITED: https://www.chartjs.org/docs/latest/developers/api.html] + STATE.md
const PALETTES = {
  dark:  ['#818cf8','#34d399','#fbbf24','#60a5fa','#f472b6','#a78bfa','#2dd4bf','#fb923c'],
  light: ['#4f46e5','#059669','#d97706','#2563eb','#db2777','#7c3aed','#0d9488','#ea580c'],
};

function initCharts() {
  const isDark = document.documentElement.classList.contains('dark');
  const palette = isDark ? PALETTES.dark : PALETTES.light;
  const textColor = isDark ? '#9ca3af' : '#6b7280';

  // Template injects these via | tojson
  const bandData   = {{ band_counts   | tojson }};
  const modeData   = {{ mode_counts   | tojson }};
  const entityData = {{ entity_counts | tojson }};

  makeChart('chart-band',
    Object.keys(bandData),
    Object.values(bandData),
    palette, textColor);

  makeChart('chart-mode',
    Object.keys(modeData),
    Object.values(modeData),
    palette, textColor);

  makeChart('chart-entity',
    entityData.map(e => e.name),
    entityData.map(e => e.count),
    palette, textColor);
}

function makeChart(canvasId, labels, values, palette, textColor) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  Chart.getChart(canvas)?.destroy();
  return new Chart(canvas, {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: values.map((_, i) => palette[i % palette.length]),
        borderWidth: 2,
        borderColor: 'transparent',
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: { color: textColor, padding: 16 }
        }
      }
    }
  });
}

function reinitCharts() { initCharts(); }

document.addEventListener('DOMContentLoaded', initCharts);
window.addEventListener('themechange', reinitCharts);
```

### Sidebar Nav Link (Verified from codebase)
```html
<!-- Source: base_app.html pattern inspection, lines 46-53 -->
<!-- Insert after Log View block, before Import block -->
<a href="/log/stats"
   class="nav-item {{ 'nav-item-active' if ap == 'stats' else '' }}">
  <svg class="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round"
          d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z" />
  </svg>
  Stats
</a>
```

Icon: Heroicons outline ChartBarSquare (presentation-chart-bar), 24×24, stroke-width="1.5". Matches all other nav icons.

### Canvas Wrapper (Verified from STATE.md + Context7)
```html
<!-- Source: STATE.md §v2.3 Architecture Decisions -->
<div class="relative h-64 w-full">
  <canvas id="chart-band" role="img" aria-label="QSO count by band — pie chart"></canvas>
</div>
```

### toggleTheme() Patch (Exact insertion point verified)
```javascript
// Source: base_app.html lines 176-180 (verified)
// Current:
function toggleTheme() {
  var isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  updateThemeIcons(isDark);
}  // line 180

// After patch — add ONE line before closing brace:
function toggleTheme() {
  var isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  updateThemeIcons(isDark);
  window.dispatchEvent(new CustomEvent('themechange'));
}
```

### Empty State HTML (Verified from UI-SPEC)
```html
<!-- Condition: total_qsos == 0 — no canvas elements, no Chart.js init needed -->
<div class="card">
  <div class="p-6 text-center text-gray-500 dark:text-gray-400">
    No data yet. Start logging QSOs to see your statistics here.
  </div>
</div>
```

### DXCC Chart Title with Inline Scalar
```html
<!-- Source: 43-CONTEXT.md + 43-UI-SPEC.md -->
<h2 class="card-title">By DXCC Entity &middot; {{ unique_entity_count }} entities</h2>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `QSO.get_motor_collection()` | `QSO.get_pymongo_collection()` | May 2025 (Motor EOL) | Phase 42 already uses the correct method |
| Chart.js v3 | Chart.js v4.5.1 | 2023 | `Chart.getChart()` API available in v3+; no API changes affect this phase |

**Deprecated/outdated:**
- Motor (`get_motor_collection`): EOL May 2025; replaced by `get_pymongo_collection` (already fixed in Phase 42)

---

## Open Questions

1. **bfcache restore on back-navigation**
   - What we know: `Chart.getChart(canvas)?.destroy()` runs before every `new Chart()` call, which handles the stale canvas case.
   - What's unclear: Does the browser's pageshow event fire when returning to the page via bfcache, and does Chart.js need re-initialization in that case?
   - Recommendation: The current stale canvas guard (`?.destroy()` before `new Chart()`) combined with `DOMContentLoaded` listener is sufficient for the scope of this phase. If bfcache re-init becomes a problem post-implementation, add `window.addEventListener('pageshow', (e) => { if (e.persisted) initCharts(); })` — leave as a known enhancement, not a blocker.

2. **Empty state and Chart.js script tag**
   - What we know: UI-SPEC says no canvas elements are present in the empty state.
   - What's unclear: Should the Chart.js `<script>` tag still load in the empty state (just no init code runs), or should it be conditionally omitted?
   - Recommendation: Conditionally guard the entire `{% block extra_scripts %}` content with `{% if total_qsos > 0 %}`. This avoids loading 220KB for operators with no data. The `DOMContentLoaded` handler and `themechange` listener are only registered when `total_qsos > 0`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | `npm run build` (Tailwind) | Yes | v25.6.1 | — |
| npm | `npm run build` | Yes | 11.9.0 | — |
| uv | `uv run pytest` | Yes | 0.9.21 | — |
| Chart.js 4.5.1 CDN | Browser chart rendering | Yes (HTTP 200) | 4.5.1 | — |
| MongoDB (localhost:27017) | `uv run pytest tests/test_stats.py` | Unknown (requires running instance) | — | Tests skip automatically if unreachable |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** MongoDB for test execution — tests use `_mongo_available()` check and `pytest.skip()` automatically. Phase 43 tests are template/JS only (no new Python test file needed).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/test_stats.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STATS-01 | Stats nav link renders with `nav-item-active` when `ap == 'stats'` | Manual visual / smoke | Load `/log/stats` in browser, verify link highlighted | N/A (template rendering) |
| STATS-02 | Band pie chart renders with correct labels | Smoke (existing route test) | `uv run pytest tests/test_stats.py::test_stats_route_empty_log -x` | Yes |
| STATS-03 | Mode pie chart renders with correct labels | Smoke (existing route test) | Same as above | Yes |
| STATS-04 | DXCC pie chart renders top-8 + Other | Smoke (existing service tests) | `uv run pytest tests/test_stats.py -x` | Yes |
| STATS-05 | Unique entity scalar in DXCC chart title | Manual visual | Load `/log/stats` in browser, verify subtitle text | N/A (template) |
| STATS-08 | Charts re-init on theme toggle | Manual visual | Toggle theme button in browser, verify charts re-render | N/A (browser JS) |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_stats.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work` + `npm run build` + `npm run verify`

### Wave 0 Gaps

None — existing test infrastructure covers all phase requirements. Phase 43 is a template-only phase; all data-layer tests exist in `tests/test_stats.py` (7 tests). No new Python test file is needed. The new template behavior (charts, nav link, dark mode) is verified manually in the browser.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Auth is already enforced in Phase 42 router via `Depends(get_current_operator_callsign_cookie)` |
| V3 Session Management | No | No session changes in this phase |
| V4 Access Control | No | Operator isolation enforced at service layer (Phase 42) |
| V5 Input Validation | Yes (output encoding) | `\| tojson` filter prevents XSS from entity names in inline script |
| V6 Cryptography | No | No crypto in this phase |

### Known Threat Patterns for Jinja2 + Chart.js CDN Inline Data

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via inline JSON (entity names with quotes/commas) | Tampering | `\| tojson` Jinja2 filter — verified pattern, pre-decided in STATE.md |
| CDN script integrity | Tampering | jsDelivr + pinned version (4.5.1) — no SRI hash but version is pinned; acceptable for internal tool |
| Operator data leakage via chart data | Information Disclosure | Template context is already scoped to `callsign` from JWT cookie; no cross-operator data |

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 43 |
|-----------|-------------------|
| Tailwind purge: new `dark:` classes must be complete literal strings in template files | All dark: classes in stats.html must appear as full literal strings; run `npm run build` + `npm run verify` after template changes |
| FOUC prevention: base.html IIFE in `<head>` is load-bearing — never move, add defer/async, or extract | Do NOT add `defer`/`async` to the Chart.js `<script>` tag or any script in extra_scripts block; however Chart.js itself is fine to load without defer since it's at end of body |
| `npm run build` to compile output.css | Required after any template modification that adds new Tailwind classes |
| `npm run verify` to assert dark mode + color-scheme classes present | Run after template changes |
| `uv run pytest tests/` for test execution | Use `uv run` not `python -m pytest` |
| No new Python dependencies | Confirmed: this phase adds zero Python dependencies |
| APScheduler `<4` upper bound is load-bearing | Not relevant to this phase |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Chart.js 4.5.1 CDN URL will be available at runtime in the target browser environment | Standard Stack | Low — CDN pinned to exact version; jsDelivr has 99.9%+ uptime |

All other claims in this research were verified via tool calls (codebase reads, npm registry, CDN probe) or cited from official documentation.

---

## Sources

### Primary (HIGH confidence)
- `/Users/royco/ollog/templates/base.html` — confirmed no existing extra_scripts block; line 40 is bare `</body>`
- `/Users/royco/ollog/templates/base_app.html` — confirmed `toggleTheme()` at lines 176-180; sidebar nav block structure confirmed
- `/Users/royco/ollog/templates/log/stats.html` — Phase 42 stub contents confirmed; `{% block active_page %}stats{% endblock %}` already set
- `/Users/royco/ollog/app/stats/service.py` — confirmed return dict shape: band_counts (dict), mode_counts (dict), entity_counts (list[{name,count}]), unique_entity_count (int), total_qsos (int)
- `/Users/royco/ollog/app/stats/router.py` — confirmed template context keys passed to stats.html
- `/Users/royco/ollog/static/css/input.css` — confirmed `.card`, `.card-header`, `.card-title`, `.card-body`, `.nav-item`, `.nav-item-active` component class definitions
- `/Users/royco/ollog/tailwind.config.js` — confirmed `darkMode: 'class'`, custom color tokens
- `npm view chart.js version` — returns `4.5.1` [VERIFIED: npm registry, 2026-04-16]
- `curl CDN URL` — HTTP 200 [VERIFIED: curl probe, 2026-04-16]
- Context7 `/websites/chartjs` — `Chart.getChart()` static method, responsive container pattern, legend options [CITED: https://www.chartjs.org/docs/latest/developers/api.html, https://www.chartjs.org/docs/latest/configuration/responsive.html]
- `.planning/STATE.md` §v2.3 Architecture Decisions — all pre-decided technical choices [VERIFIED: file read]
- `.planning/phases/43-stats-ui/43-CONTEXT.md` — locked decisions [VERIFIED: file read]
- `.planning/phases/43-stats-ui/43-UI-SPEC.md` — design contract [VERIFIED: file read]
- `.planning/phases/42-stats-aggregation-backend/42-01-SUMMARY.md` — confirmed Phase 42 deliverables and exact API correction (`get_pymongo_collection`) [VERIFIED: file read]

### Secondary (MEDIUM confidence)
- Context7 `/websites/chartjs` multi-series pie chart config — legend `generateLabels` pattern [CITED: https://www.chartjs.org/docs/latest/samples/other-charts/multi-series-pie.html]

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Chart.js 4.5.1 version verified via npm registry and CDN probe; no assumptions on library choice (pre-decided in STATE.md)
- Architecture: HIGH — all template files read; exact line numbers confirmed; data shapes verified from Phase 42 service code
- Pitfalls: HIGH — derived from actual codebase constraints (Tailwind purge rules from CLAUDE.md, base.html FOUC IIFE, UMD vs ESM from STATE.md) and Phase 42 SUMMARY.md deviations log

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (stable Chart.js API; CDN URL pinned to exact version)
