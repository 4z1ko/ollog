# Architecture Research

**Domain:** Operator statistics page — FastAPI/Jinja2/HTMX integration
**Researched:** 2026-04-15
**Confidence:** HIGH (fully code-verified against live codebase)

---

## Summary

The stats page is a straightforward extension of the existing request flow. One new route in `app/qso/ui_router.py`, one new service function in `app/qso/service.py`, and one new template `templates/log/stats.html`. No new routers, no new modules, no new dependencies except Chart.js loaded via CDN `<script>` tag in the template.

The only technically non-obvious decision is DXCC entity aggregation: MongoDB cannot resolve callsign → DXCC entity natively. The aggregation pipeline groups by `CALL`, returns per-callsign counts, and Python post-processes each callsign through the existing `lookup_prefix()` + `pycountry` stack (identical to `_qso_to_view_dict`). The result is a `dict[str, int]` of entity label → count, built in Python before template rendering.

JSON injection into Chart.js uses `tojson` (Jinja2's built-in, output is HTML-escaped) in a `<script>` block. This is XSS-safe and is the established pattern for server-rendered chart data.

---

## New Files

| File | Purpose |
|------|---------|
| `templates/log/stats.html` | Stats page — extends `base_app.html`, contains three `<canvas>` elements and a `<script>` block that initializes Chart.js pie charts from server-rendered JSON |

---

## Modified Files

| File | Change |
|------|--------|
| `app/qso/service.py` | Add `get_stats(operator: str) -> dict` — runs three MongoDB aggregation pipelines, post-processes DXCC entities in Python, returns structured data dict |
| `app/qso/ui_router.py` | Add `GET /log/stats` route — cookie-auth, calls `get_stats()`, passes result to `templates/log/stats.html` |
| `templates/base_app.html` | Add "Stats" nav item to `{% block sidebar_nav %}` with `ap == 'stats'` active check |

No new router file, no new module, no changes to `app/main.py` (route is inside the existing `ui_router` which is already mounted at `/log`).

---

## Data Flow

### MongoDB Aggregation → Python Post-Processing → Template → Chart.js

```
GET /log/stats  (cookie: access_token=<JWT>)
        │
        ▼
get_current_operator_callsign_cookie(request)
        │  reads HttpOnly cookie, decodes JWT
        │  returns: operator callsign string  (e.g. "W1AW")
        │
        ▼
get_stats(operator="W1AW")  [app/qso/service.py]
        │
        │  Pipeline 1 — band counts:
        │    db.qsos.aggregate([
        │      {"$match": {"_operator": "W1AW", "_deleted": False, "BAND": {"$ne": None}}},
        │      {"$group": {"_id": "$BAND", "count": {"$sum": 1}}},
        │      {"$sort": {"count": -1}}
        │    ])
        │    → [{"_id": "20M", "count": 412}, {"_id": "40M", "count": 307}, ...]
        │    → dict: {"20M": 412, "40M": 307, ...}
        │
        │  Pipeline 2 — mode counts:
        │    db.qsos.aggregate([
        │      {"$match": {"_operator": "W1AW", "_deleted": False, "MODE": {"$ne": None}}},
        │      {"$group": {"_id": "$MODE", "count": {"$sum": 1}}},
        │      {"$sort": {"count": -1}}
        │    ])
        │    → dict: {"FT8": 891, "SSB": 203, "CW": 87, ...}
        │
        │  Pipeline 3 — per-callsign counts (for DXCC):
        │    db.qsos.aggregate([
        │      {"$match": {"_operator": "W1AW", "_deleted": False, "CALL": {"$ne": None}}},
        │      {"$group": {"_id": "$CALL", "count": {"$sum": 1}}}
        │    ])
        │    → [{"_id": "DL1ABC", "count": 3}, {"_id": "JA1YWX", "count": 1}, ...]
        │
        │  Python post-processing — DXCC entity rollup:
        │    entity_counts: dict[str, int] = {}
        │    for doc in per_callsign_results:
        │        iso = lookup_prefix(doc["_id"])          # existing app/callsign/prefixes.py
        │        if iso:
        │            country = pycountry.countries.get(alpha_2=iso)
        │            label = country.name if country else iso
        │        else:
        │            label = "Unknown"
        │        entity_counts[label] = entity_counts.get(label, 0) + doc["count"]
        │
        │    Top 8 + "Other" rollup:
        │    sorted_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)
        │    top8 = sorted_entities[:8]
        │    other_count = sum(count for _, count in sorted_entities[8:])
        │    if other_count > 0:
        │        top8.append(("Other", other_count))
        │    dxcc_counts = dict(top8)
        │
        │    unique_dxcc = len(entity_counts)  -- count BEFORE the top-8 truncation
        │
        │  Returns:
        │    {
        │      "band_counts":   {"20M": 412, "40M": 307, ...},
        │      "mode_counts":   {"FT8": 891, "SSB": 203, ...},
        │      "dxcc_counts":   {"United States": 412, "Germany": 87, ..., "Other": 23},
        │      "unique_dxcc":   47,
        │      "total_qsos":    1181,
        │    }
        │
        ▼
stats_page route handler  [app/qso/ui_router.py]
        │  ctx = {"callsign": callsign, "stats": stats_data}
        │  return templates.TemplateResponse(request, "log/stats.html", ctx)
        │
        ▼
templates/log/stats.html
        │  Jinja2 renders:
        │    var bandData = {{ stats.band_counts | tojson }};
        │    var modeData = {{ stats.mode_counts | tojson }};
        │    var dxccData = {{ stats.dxcc_counts | tojson }};
        │  (tojson calls json.dumps with HTML escaping — XSS-safe)
        │
        │  Chart.js (CDN) initialises three PieChart instances
        │  using these inline JSON objects as data sources
        │
        ▼
Browser renders three pie charts + stat cards
```

### Operator Isolation

`get_stats(operator=callsign)` passes `callsign` from the JWT directly into every `$match` filter as `"_operator": operator`. The compound index `operator_active_idx` (`_operator`, `_deleted`) is hit by all three pipelines. Isolation is enforced at the aggregation layer — identical to how `get_qso_page` works.

---

## Build Order

Steps are sequenced by dependency. Each step is a complete, testable unit.

**Step 1 — `app/qso/service.py`: add `get_stats()`**

The aggregation logic has no UI dependency. Write and unit-test this function first. It is the hardest part of this feature (DXCC rollup logic). Testable with a mock MongoDB or a real test DB.

Key implementation note: use `QSO.get_motor_collection().aggregate([...])` or equivalently call raw pymongo via Beanie's `get_motor_collection()` — Beanie does not wrap `aggregate()` directly, but `Document.get_motor_collection()` returns the raw Motor collection where `aggregate()` is available. Alternatively, inject the MongoDB collection via `get_client()[settings.mongodb_db]["qsos"]` as done in `feed/manager.py`. Either pattern is consistent with the codebase.

**Step 2 — `app/qso/ui_router.py`: add `GET /log/stats` route**

Import `get_stats` from service. The route is two lines of logic: call `get_stats(callsign)`, return `TemplateResponse`. This unblocks template work.

```python
@ui_router.get("/stats", response_class=HTMLResponse)
async def stats_page(
    request: Request,
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    stats = await get_stats(callsign)
    return templates.TemplateResponse(
        request,
        "log/stats.html",
        {"callsign": callsign, "stats": stats},
    )
```

**Step 3 — `templates/log/stats.html`: build the template**

Extend `base_app.html`. Set `{% block active_page %}stats{% endblock %}`. Use three `<canvas>` elements (one per chart). Initialize Chart.js in a `<script>` block at the bottom of `{% block content %}`. Load Chart.js via CDN `<script src>` tag in a `{% block extra_scripts %}` block (or inline in the template's content block — the base template has no extra_scripts block so inline is simplest).

**Step 4 — `templates/base_app.html`: add Stats nav item**

Insert the Stats nav link between "Log View" and "Import" (or between "Import" and "Export" — position is a UX preference). Add a chart/bar-chart Heroicon at `w-6 h-6`. Use the same `nav-item` + active class pattern as every other nav item.

**Step 5 — Integration smoke test**

Navigate to `/log/stats` with a seeded operator account. Verify three charts render, DXCC "Other" bucket works, total count matches, dark mode applies correctly.

---

## Integration Notes

### XSS-Safe JSON Injection into Chart.js

Jinja2's `tojson` filter calls `json.dumps` with HTML-escaping enabled by default in Jinja2's `Environment`. This means `<`, `>`, `&`, `'`, and `"` inside string values are escaped as `\u003c`, `\u003e`, etc. These are valid JSON escape sequences — JavaScript's JSON parser handles them correctly. The output is safe to embed directly in a `<script>` block.

**Correct pattern:**
```html
<script>
  var bandData = {{ stats.band_counts | tojson }};
  new Chart(document.getElementById('band-chart'), {
    type: 'pie',
    data: {
      labels: Object.keys(bandData),
      datasets: [{ data: Object.values(bandData) }]
    }
  });
</script>
```

**What not to do:** Do not use `| safe` on raw Python dicts serialized with `str()`. `str({"<script>": 1})` produces literal `<script>` in output — XSS. Always use `tojson`.

**Confidence:** HIGH — this is Jinja2's documented pattern for safe JSON injection. The `tojson` filter is available in Jinja2 2.x and above (used in this project). FastAPI's `Jinja2Templates` uses the standard Jinja2 `Environment` which enables HTML autoescaping for `.html` templates.

### Chart.js CDN Loading

Chart.js is not in `package.json` (Tailwind is the only NPM dependency). Load via CDN `<script>` tag inside `templates/log/stats.html`. Do not add Chart.js to `package.json` — the build pipeline is Tailwind-only and adding a bundler would be over-engineering for a single-page library inclusion.

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
```

Place this `<script>` before the chart initialization `<script>` block. Both must be in the page body (after DOMContentLoaded) or the canvas elements must exist before initialization.

Because `base.html` uses `<script src="https://unpkg.com/htmx.org@2.0.4">` in `<head>` without `defer`, adding Chart.js inline in the template content block (which renders after `<body>` is parsed) is fine — canvas elements exist in DOM when Chart.js initializes.

**Confidence:** HIGH — Chart.js is the standard browser charting library, CDN delivery is its documented primary install path for non-bundled use.

### Dark Mode Compatibility

The `stats.html` template renders inside `base_app.html`'s main content area which already has `bg-canvas-light dark:bg-canvas-dark`. Chart.js uses canvas elements which do not inherit CSS color. Chart colors must be set explicitly in Chart.js config.

Use light-neutral colors for chart segments that work on both light and dark backgrounds. The chart background and grid lines can be transparent. The canvas element should have an explicit background (`bg-white dark:bg-gray-800` via Tailwind, applied as a `class` on the `<canvas>` wrapper `<div>`, not the canvas itself — canvas does not support Tailwind via CSS class the same way).

Alternatively, wrap each canvas in a `.card` div (existing Apple-design-system component) — cards already handle dark mode background correctly.

### DXCC Aggregation: Why Python, Not MongoDB

MongoDB's `$group` can only group on fields that exist in the document. The DXCC entity name is not stored in the QSO document — only the raw `CALL` field is. Computing entity names requires the ITU prefix resolver (`lookup_prefix`), which is a Python function wrapping a bisect lookup over 313 ITU ranges. There is no practical way to replicate this in a MongoDB `$addFields` expression.

The correct approach: aggregate by `CALL` (MongoDB handles efficiently — uses `_operator` leading index), then post-process in Python. For a typical ham radio logbook (hundreds to low-thousands of unique callsigns), this is fast. A 1,000-callsign post-process loop runs in under 5ms in Python.

### Empty Log Edge Case

If an operator has no QSOs, all three aggregation pipelines return empty cursors. `get_stats()` returns `{"band_counts": {}, "mode_counts": {}, "dxcc_counts": {}, "unique_dxcc": 0, "total_qsos": 0}`. The template must handle empty dicts — Chart.js renders an empty pie chart without error when given empty data arrays. Add a conditional `{% if stats.total_qsos == 0 %}` guard in the template to show a friendly "No QSOs logged yet" message instead of three empty charts.

### Beanie Aggregation Access Pattern

Beanie's `Document` class does not expose a `.aggregate()` method as a class method (it wraps Motor's `find`, `find_one`, `insert`, `save`, etc. but not raw aggregation). Use `QSO.get_motor_collection().aggregate([...])` to access the underlying Motor collection. This is the established internal pattern — `watch_qsos` in `app/feed/manager.py` uses `collection` directly obtained from `get_client()[settings.mongodb_db]["qsos"]`, which is equivalent.

The recommended call inside `get_stats`:
```python
from app.qso.models import QSO

collection = QSO.get_motor_collection()
cursor = collection.aggregate([...])
results = await cursor.to_list(length=None)
```

`length=None` on Motor aggregation cursors returns all results — appropriate since band/mode result sets are bounded (tens of distinct values at most) and callsign result sets are bounded by the operator's unique-CALL count (typically hundreds to low thousands).

---

## Sources

- `/Users/royco/ollog/app/qso/ui_router.py` — existing route patterns, `_qso_to_view_dict` DXCC enrichment logic, cookie auth dependency usage (code verified, HIGH confidence)
- `/Users/royco/ollog/app/qso/service.py` — service layer conventions, `get_qso_page` pattern for operator-isolated queries (code verified, HIGH confidence)
- `/Users/royco/ollog/app/qso/models.py` — QSO field structure, `_operator`/`_deleted` aliases, compound indexes (code verified, HIGH confidence)
- `/Users/royco/ollog/app/callsign/prefixes.py` — `lookup_prefix()` signature and return type (ISO alpha-2 or None), `_ITU_NAME_TO_ISO` mapping (code verified, HIGH confidence)
- `/Users/royco/ollog/app/main.py` — router mounting (ui_router at `/log`, `include_in_schema=False`), exception handler for 401/403 on `/log/` (code verified, HIGH confidence)
- `/Users/royco/ollog/templates/base_app.html` — sidebar nav pattern, `{% block active_page %}` convention, `{% block content %}`, no `extra_scripts` block (code verified, HIGH confidence)
- `/Users/royco/ollog/templates/log/about.html` — confirmed template extension pattern, `card`/`card-header`/`card-body` component usage (code verified, HIGH confidence)
- `/Users/royco/ollog/templates/base.html` — HTMX + SSE CDN `<script>` tags in `<head>`, FOUC prevention inline script (code verified, HIGH confidence)
- `/Users/royco/ollog/.planning/PROJECT.md` — v2.3 active requirements: band pie, mode pie, DXCC top-8 pie, unique DXCC count, JWT isolation (code verified, HIGH confidence)
- [Jinja2 `tojson` docs](https://jinja.palletsprojects.com/en/3.1.x/templates/#tojson) — HTML-safe JSON serialization in templates (HIGH confidence)
- [Chart.js installation docs](https://www.chartjs.org/docs/latest/getting-started/installation.html) — CDN delivery pattern for non-bundled use (HIGH confidence)

---

*Architecture research for: v2.3 Operator Statistics page*
*Researched: 2026-04-15*
