# Phase 43: Stats UI - Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 3 (templates/base.html, templates/base_app.html, templates/log/stats.html)
**Analogs found:** 3 / 3

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `templates/base.html` | layout-base | request-response | self (1-line insertion) | exact |
| `templates/base_app.html` | layout-app | request-response | self (sidebar nav + script patch) | exact |
| `templates/log/stats.html` | page-template | request-response | `templates/log/profile.html` + `templates/log/about.html` | role-match |

---

## Pattern Assignments

### `templates/base.html` — add `extra_scripts` block

**Analog:** self (the file being modified)

**Current state** (`templates/base.html` lines 38–41):
```html
<body class="antialiased">
  {% block body %}{% endblock %}
</body>
</html>
```

**Insertion target:** line 40 — immediately before `</body>`, after `{% block body %}{% endblock %}`.

**Pattern to apply** (line to insert before `</body>`):
```html
{% block extra_scripts %}{% endblock %}
```

**Result after patch:**
```html
<body class="antialiased">
  {% block body %}{% endblock %}
  {% block extra_scripts %}{% endblock %}
</body>
</html>
```

**Constraints from CLAUDE.md + RESEARCH.md:**
- The FOUC-prevention IIFE in `<head>` (lines 16–33) must not be moved, deferred, or made async — untouched by this change.
- The two existing CDN `<script>` tags for htmx (lines 35–36) remain unchanged.
- `{% block extra_scripts %}{% endblock %}` must be INSIDE `<body>`, AFTER `{% block body %}{% endblock %}`, so child template script overrides come after the page content.

---

### `templates/base_app.html` — sidebar nav link + toggleTheme() patch

**Analog:** self (the file being modified)

#### Sidebar nav — insertion pattern

**Existing nav block** (`templates/base_app.html` lines 36–90), key structure excerpt:
```html
{% block sidebar_nav %}
<!-- Log QSO -->
<a href="/log/"
   class="nav-item {{ 'nav-item-active' if ap == 'form' else '' }}">
  <svg class="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M8.288 15.038..." />
  </svg>
  Log QSO
</a>

<!-- Log View -->
<a href="/log/view"
   class="nav-item {{ 'nav-item-active' if ap == 'view' else '' }}">
  <svg class="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 6.75h12..." />
  </svg>
  Log View
</a>

<!-- Import -->            ← INSERT STATS BLOCK HERE (between Log View and Import)
<a href="/log/import"
   class="nav-item {{ 'nav-item-active' if ap == 'import' else '' }}">
```

**Block to insert** (after Log View `</a>`, before `<!-- Import -->`):
```html
<!-- Stats -->
<a href="/log/stats"
   class="nav-item {{ 'nav-item-active' if ap == 'stats' else '' }}">
  <svg class="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round"
          d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z" />
  </svg>
  Stats
</a>
```

**Pattern rules extracted from codebase:**
- All nav `<a>` elements use class `"nav-item {{ 'nav-item-active' if ap == '<page_key>' else '' }}"`.
- `ap` is set per page via `{% block active_page %}<page_key>{% endblock %}` in the child template.
- The phase 42 stub already declares `{% block active_page %}stats{% endblock %}` — no change to the stub's active_page block needed.
- Icon: Heroicons outline, 24×24, `fill="none"`, `stroke-width="1.5"`, `stroke="currentColor"`, `class="w-6 h-6 flex-shrink-0"`.
- Icon SVG path for Stats (ChartBarSquare / presentation-chart-bar, Heroicons outline): `d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z"`.

#### toggleTheme() — CustomEvent patch

**Current function** (`templates/base_app.html` lines 176–180):
```javascript
function toggleTheme() {
  var isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  updateThemeIcons(isDark);
}
```

**After patch** — insert one line before the closing `}` (line 180):
```javascript
function toggleTheme() {
  var isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
  updateThemeIcons(isDark);
  window.dispatchEvent(new CustomEvent('themechange'));
}
```

**Constraint:** The insertion must be INSIDE the `toggleTheme()` function body, before the closing `}`. The `<script>` block continues at lines 181–205 with `updateThemeIcons()`, `DOMContentLoaded` listener, and `htmx:afterSettle` listener — those are not touched.

---

### `templates/log/stats.html` — full replacement of Phase 42 stub

**Analog:** `templates/log/profile.html` (page header + multiple `.card` sections, `max-w-3xl mx-auto`) and `templates/log/about.html` (read-only data display page)

**Template inheritance pattern** (from `templates/log/profile.html` lines 1–4, `templates/log/about.html` lines 1–4):
```html
{% extends "base_app.html" %}
{% block title %}ollog — {Page Title}{% endblock %}
{% block active_page %}{page_key}{% endblock %}

{% block content %}
<div class="max-w-{size} mx-auto space-y-6">
  <!-- Page header -->
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">{Page Name}</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
      {Page subtitle}
    </p>
  </div>
  <!-- ... cards ... -->
</div>
{% endblock %}
```

**Stats-specific header** (keep from Phase 42 stub, line 3 preserved, width changed from `max-w-2xl` to `max-w-5xl`):
```html
{% extends "base_app.html" %}
{% block title %}ollog -- Stats{% endblock %}
{% block active_page %}stats{% endblock %}

{% block content %}
<div class="max-w-5xl mx-auto space-y-6">
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">Statistics</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
      Operator log statistics for {{ callsign }}
    </p>
  </div>
```

**Empty state pattern** (from Phase 42 stub lines 15–19 and UI-SPEC):
```html
{% if total_qsos == 0 %}
<div class="card">
  <div class="p-6 text-center text-gray-500 dark:text-gray-400">
    No data yet. Start logging QSOs to see your statistics here.
  </div>
</div>
{% else %}
```

**Summary card pattern** (from `templates/log/profile.html` `.card` + `.card-header` + `.card-body` pattern, lines 20–27):
```html
<div class="card">
  <div class="card-header">
    <h2 class="card-title">Summary</h2>
  </div>
  <div class="card-body">
    <p class="text-gray-700 dark:text-gray-300">Total QSOs: {{ total_qsos }}</p>
  </div>
</div>
```

**Chart grid pattern** (from UI-SPEC §Layout Contract):
```html
<!-- Top row: 2-column grid for Band + Mode -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">By Band</h2>
    </div>
    <div class="card-body">
      <div class="relative h-64 w-full">
        <canvas id="chart-band" role="img" aria-label="QSO count by band — pie chart"></canvas>
      </div>
    </div>
  </div>
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">By Mode</h2>
    </div>
    <div class="card-body">
      <div class="relative h-64 w-full">
        <canvas id="chart-mode" role="img" aria-label="QSO count by mode — pie chart"></canvas>
      </div>
    </div>
  </div>
</div>

<!-- Bottom row: DXCC Entity chart full-width -->
<div class="mt-6">
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">By DXCC Entity &middot; {{ unique_entity_count }} entities</h2>
    </div>
    <div class="card-body">
      <div class="relative h-64 w-full">
        <canvas id="chart-entity" role="img" aria-label="QSO count by DXCC entity — pie chart"></canvas>
      </div>
    </div>
  </div>
</div>
{% endif %}
```

**extra_scripts block pattern** (new — no codebase analog exists; follows RESEARCH.md Pattern 1):
```html
{% if total_qsos > 0 %}
{% block extra_scripts %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
<script>
  const PALETTES = {
    dark:  ['#818cf8','#34d399','#fbbf24','#60a5fa','#f472b6','#a78bfa','#2dd4bf','#fb923c'],
    light: ['#4f46e5','#059669','#d97706','#2563eb','#db2777','#7c3aed','#0d9488','#ea580c'],
  };

  const bandData   = {{ band_counts   | tojson }};
  const modeData   = {{ mode_counts   | tojson }};
  const entityData = {{ entity_counts | tojson }};

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

  function initCharts() {
    const isDark = document.documentElement.classList.contains('dark');
    const palette = isDark ? PALETTES.dark : PALETTES.light;
    const textColor = isDark ? '#9ca3af' : '#6b7280';

    makeChart('chart-band',
      Object.keys(bandData), Object.values(bandData), palette, textColor);
    makeChart('chart-mode',
      Object.keys(modeData), Object.values(modeData), palette, textColor);
    makeChart('chart-entity',
      entityData.map(e => e.name), entityData.map(e => e.count), palette, textColor);
  }

  function reinitCharts() { initCharts(); }

  document.addEventListener('DOMContentLoaded', initCharts);
  window.addEventListener('themechange', reinitCharts);
</script>
{% endblock %}
{% endif %}
```

**Note on block/if ordering:** Jinja2 evaluates `{% block %}` declarations at template-parse time, not at render time. The `{% if total_qsos > 0 %}{% block extra_scripts %}...{% endblock %}{% endif %}` pattern works in Jinja2 because the parent block is declared unconditionally in `base.html` (it renders empty by default), and the child override is guarded by the `if` at render time.

---

## Shared Patterns

### nav-item / nav-item-active CSS classes
**Source:** `static/css/input.css` lines 126–133
**Apply to:** The Stats `<a>` element in `base_app.html`
```css
.nav-item {
  @apply flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium
         text-sidebar-text hover:bg-sidebar-hover hover:text-white
         transition-colors duration-150 cursor-pointer;
}
.nav-item-active {
  @apply bg-sidebar-active text-white;
}
```

### card / card-header / card-title / card-body CSS classes
**Source:** `static/css/input.css` lines 73–84
**Apply to:** All card containers in `stats.html`
```css
.card       { @apply bg-surface-light dark:bg-surface-dark rounded-xl border border-gray-200 dark:border-gray-800 shadow-card dark:shadow-none; }
.card-header { @apply px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between; }
.card-title  { @apply text-sm font-semibold text-gray-700 dark:text-gray-200; }
.card-body   { @apply px-6 py-5; }
```

### Page heading typography
**Source:** `templates/log/profile.html` lines 9–13, `templates/log/about.html` lines 9–13
**Apply to:** `stats.html` page header section
```html
<h1 class="text-xl font-bold text-gray-900 dark:text-white">{Title}</h1>
<p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{Subtitle}</p>
```

### Jinja2 tojson inline data injection
**Source:** RESEARCH.md Pattern 2 (enforced by STATE.md architecture decisions)
**Apply to:** All three `const` variable assignments in `stats.html` script block
```javascript
const bandData   = {{ band_counts   | tojson }};
const modeData   = {{ mode_counts   | tojson }};
const entityData = {{ entity_counts | tojson }};
```
Never use `| safe` or bare `{{ var }}` — entity names contain quotes, commas, apostrophes that break JS string literals and are XSS vectors.

### Dark mode class pattern
**Source:** `tailwind.config.js` line 3 (`darkMode: 'class'`), all existing templates
**Apply to:** Every Tailwind class that changes between themes in `stats.html`
- Text: `text-gray-900 dark:text-white`, `text-gray-500 dark:text-gray-400`, `text-gray-700 dark:text-gray-300`
- All `dark:` class strings must appear as complete literal strings in the HTML template for Tailwind v3 purge scanner — never in JavaScript strings or dynamically constructed values.

---

## No Analog Found

None. All three files have clear analogs in the codebase. The `extra_scripts` block mechanism is new but is a straightforward Jinja2 pattern with no analog needed (it is a one-line insertion).

---

## Key Technical Constraints (from CLAUDE.md + RESEARCH.md)

| Constraint | Source | Impact |
|------------|--------|--------|
| `npm run build` required after any template change adding new Tailwind classes | CLAUDE.md | Run after `stats.html` and `base.html` edits |
| `npm run verify` required to assert dark mode classes present | CLAUDE.md | Run after build |
| FOUC IIFE in `base.html` `<head>` must not be moved or deferred | CLAUDE.md | Do not touch lines 16–33 of `base.html` |
| Chart.js must use UMD build (`chart.umd.min.js`), not ESM | RESEARCH.md Pitfall 2 | CDN URL: `https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js` |
| `Chart.getChart(canvas)?.destroy()` before every `new Chart()` | RESEARCH.md Pattern 3 | Applied in `makeChart()` function |
| CustomEvent dispatch must be INSIDE `toggleTheme()` closing brace | RESEARCH.md Pitfall 6 | Insert before line 180 `}` in `base_app.html` |
| No new Python dependencies | RESEARCH.md | Confirmed: zero Python changes in phase 43 |

---

## Metadata

**Analog search scope:** `templates/` directory (all `.html` files), `static/css/input.css`, `tailwind.config.js`
**Files scanned:** 17 template files + 2 CSS/config files
**Pattern extraction date:** 2026-04-16
