# Stack Research: v2.3 Operator Statistics Page

**Project:** ollog — Ham Radio Online Logbook
**Milestone:** v2.3 Operator Statistics
**Researched:** 2026-04-15
**Overall confidence:** HIGH

---

## Current Stack (relevant to this milestone)

| Component | Technology | Version | Notes |
|-----------|-----------|---------|-------|
| Backend framework | FastAPI | 0.135+ | Already in use |
| Async ODM | Beanie | 2.1+ | Already in use; supports raw aggregation pipelines |
| Database | MongoDB 7 | single-node replica set | Already in use |
| Templates | Jinja2 | — | Already in use; rendered server-side |
| Frontend interactivity | HTMX | 2.0.4 | Already in use; loaded from unpkg CDN in base.html |
| CSS | Tailwind CSS v3 | — | Already in use; dark mode classes required |
| Charting | None | — | NOT yet in stack; Chart.js is the addition |

The existing render pipeline for operator UI pages is: FastAPI route handler (ui_router.py) -> Beanie query -> Jinja2 template -> HTMX partial swap where needed. The stats page fits this pattern exactly with one addition: a Chart.js script tag.

---

## New Additions Needed

### Chart.js via CDN

**Recommendation:** Chart.js 4.5.1, loaded from jsDelivr CDN, pinned to the exact version.

**Confidence:** HIGH — version confirmed directly from `https://cdn.jsdelivr.net/npm/chart.js@latest/package.json` returning `4.5.1`. Context7 docs and Chart.js official docs both confirm the CDN pattern.

**CDN tag to add in the stats template (not base.html):**

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
```

**Why this specific URL:**
- `chart.umd.min.js` is the UMD bundle — no module bundler required, registers `Chart` as a global. This is what the Chart.js getting-started guide recommends for non-bundled usage.
- `@4.5.1` is pinned, not `@latest`. Unpinned CDN tags break on major version bumps (v4 to v5 will be a breaking change). The existing htmx tag in base.html (`htmx.org@2.0.4`) and sse tag (`@2.2.4`) follow this same pinned pattern.
- jsDelivr is already used in this codebase (htmx-ext-sse). Consistent CDN vendor.

**Where to add the tag:**
- Add inside a `{% block extra_scripts %}{% endblock %}` block placed at the bottom of `base.html` just before `</body>`, then override in the stats template.
- Do NOT add to `base.html` globally — Chart.js is ~200 KB min and only needed on the stats page. Load it only where used.
- Chart.js has no FOUC-equivalent constraint — it can load at the bottom of the page body after the canvas elements exist.

**Pie chart data flow:**
- FastAPI handler computes aggregation, serializes result to a JSON-safe Python dict.
- Jinja2 renders the dict inline as a JavaScript variable using the `tojson` filter.
- Chart.js reads the variable at page load — no async fetch needed, no separate JSON endpoint needed.
- This is simpler and correct: the data is operator-scoped, already computed on the server, and a page refresh to see updated stats is acceptable (stats are a point-in-time snapshot, not a live feed).

### MongoDB Aggregation Pipelines (no new Python dependency)

**Recommendation:** Use Beanie's `.aggregate()` method on `QSO` directly. No additional Python packages needed.

**Confidence:** HIGH — Beanie 2.x `.aggregate()` is documented and takes a raw MongoDB aggregation pipeline list with an optional `projection_model`. Confirmed via Context7 for `/beanieodm/beanie`.

**Pattern for band and mode breakdowns:**

```python
from pydantic import BaseModel, Field

class BucketResult(BaseModel):
    id: str = Field(alias="_id")
    count: int

band_stats = await QSO.find(
    {"_operator": operator, "_deleted": False}
).aggregate(
    [
        {"$group": {"_id": "$BAND", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ],
    projection_model=BucketResult,
).to_list()
```

Mode stats follow the identical pattern, changing `"$BAND"` to `"$MODE"`.

**Pattern for DXCC top-8 + "Other":**
DXCC entity name is derived at render time via `lookup_prefix(qso.CALL)` -> `pycountry.countries.get()` -> country name. This is computed in Python, not stored in the QSO document, consistent with the existing "render-time enrichment, not stored" decision.

Approach: aggregate by `CALL` field in MongoDB (one `$group` stage), then in Python iterate the results calling `lookup_prefix()` on each unique callsign and accumulate counts per country name. Slice top 8, sum remainder into "Other". `len(unique_countries)` before slicing gives the unique DXCC count.

No new Python library is needed. `lookup_prefix` and `pycountry` are already imported in `ui_router.py`.

The number of unique CALLs per operator is bounded (hundreds to low thousands in a typical log) — a Python-side grouping step after the MongoDB aggregation is not a performance concern.

---

## What NOT to Add

| Candidate | Decision | Reason |
|-----------|----------|--------|
| Separate `/api/stats` JSON endpoint | Do not add | Data is operator-scoped and auth-required. Inline server-side rendering avoids a second authenticated request and matches the existing HTMX page pattern. Add a JSON endpoint only if a future mobile client needs it. |
| Chart.js in base.html globally | Do not add | ~200 KB loaded on every page (login, form, log view, profile, tokens, import) with no benefit. Stats page only. |
| chart.js npm package in package.json | Do not add | npm is used only for the Tailwind CSS build. No JS bundler is in the project. CDN is the correct delivery method. |
| Alpine.js for chart reactivity | Do not add | Charts render a point-in-time snapshot. No reactive state management is needed. |
| Server-Sent Events on stats page | Do not add | Stats are a snapshot. Wiring SSE to update pie charts on new QSOs adds significant complexity for marginal value. |
| D3.js | Do not add | Substantially higher complexity for pie charts. Chart.js covers the requirement with no custom SVG math. |
| Victory, Recharts, or other React-based libraries | Do not add | No React in this project. |
| Any data-cube or OLAP middleware | Do not add | Three simple `$group` aggregations run directly on MongoDB. No intermediate data layer warranted. |

---

## Integration Notes

### Script loading in Jinja2 template

`base.html` currently closes `</body>` immediately after `{% block body %}{% endblock %}` with no extension point for page-specific scripts. Add a `{% block extra_scripts %}{% endblock %}` block in `base.html` just before `</body>`:

```html
{% block extra_scripts %}{% endblock %}
</body>
```

In `stats.html`, override it:

```html
{% block extra_scripts %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
<script>
  // chart initialization
</script>
{% endblock %}
```

This is clean Jinja2 template inheritance and does not affect any other page.

### Dark mode compatibility

Chart.js canvas does not automatically respect Tailwind dark mode. Pie chart slice colors must be explicit hex values in the JS config, not Tailwind class references. Use the existing Apple design token palette from the project (indigo-500 and family). The canvas element background is transparent by default and inherits the page background (`bg-canvas-light dark:bg-canvas-dark`), which is correct.

To detect dark mode for conditional label/legend colors: `document.documentElement.classList.contains('dark')` reads the class applied by the FOUC-prevention inline script in `base.html`. Chart.js initialization code at the bottom of the page body runs after the FOUC script, so the dark class is always present before any Chart constructor call.

### Data serialization from Python to Chart.js

Pass aggregation results through the Jinja2 template context as Python dicts/lists. Use the Jinja2 `tojson` filter for safe inline serialization:

```html
<script>
const bandData  = {{ band_data  | tojson }};
const modeData  = {{ mode_data  | tojson }};
const dxccData  = {{ dxcc_data  | tojson }};
const uniqueDxcc = {{ unique_dxcc_count | tojson }};
</script>
```

`tojson` escapes `<`, `>`, and `&`, which prevents XSS from crafted callsigns in the aggregation output.

### Sidebar nav link

Add a Statistics entry in `base_app.html`'s `{% block sidebar_nav %}` following the existing pattern: a Heroicon SVG (`chart-pie` or `chart-bar`) + "Statistics" label + `nav-item-active` conditional on `ap == 'stats'`.

### Router placement

The `/log/stats` GET route belongs in `app/qso/ui_router.py` alongside the other `/log/*` UI routes. Aggregation helper functions belong in `app/qso/service.py`, following the existing router -> service -> Beanie model layering.

---

## Sources

- Chart.js current version confirmed: `https://cdn.jsdelivr.net/npm/chart.js@latest/package.json` (4.5.1, HIGH confidence)
- Chart.js CDN and UMD bundle: `https://www.chartjs.org/docs/latest/getting-started/installation.html` (official docs, HIGH confidence)
- Chart.js pie chart config: Context7 `/websites/chartjs`, HIGH confidence
- Beanie `.aggregate()` with projection_model: Context7 `/beanieodm/beanie`, HIGH confidence
- MongoDB `$group` / `$sort` pipeline: `https://www.mongodb.com/docs/languages/python/pymongo-driver/current/aggregation/` (official, MEDIUM confidence — Beanie wraps this)
