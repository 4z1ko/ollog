# Architecture Patterns

**Domain:** Callsign prefix lookup & country flag display — ham radio logbook (v1.2 milestone)
**Researched:** 2026-04-04
**Confidence:** HIGH — based on direct inspection of the live codebase

---

## Context: What Already Exists

| Existing Component | Location | Notes |
|-------------------|----------|-------|
| `QSO` Beanie Document | `app/qso/models.py` | `extra="allow"`, has `CALL` field |
| `_qso_to_view_dict()` | `app/qso/ui_router.py` | Converts Beanie doc → plain dict passed to every template; keys: `id`, `CALL`, `BAND`, `MODE`, `qso_date_utc`, `FREQ`, `RST_SENT`, `RST_RCVD`, `QSO_DATE`, `TIME_ON` |
| `log_view()` + `qso_view_row()` + `qso_update()` | `app/qso/ui_router.py` | All three render `qso_row.html` — touch points for flag display |
| `qso_row.html` | `templates/log/qso_row.html` | Renders one `<tr>` — CALL is in a bare `<td>` |
| `log_table.html` | `templates/log/log_table.html` | Iterates `qsos` list; includes `qso_row.html` via `{% include %}` |
| `Jinja2Templates` instance | `app/qso/ui_router.py` line 31 | `templates = Jinja2Templates(directory="templates")` — this is where custom filters are registered |
| `static/` mount | `app/main.py` line 115 | `app.mount("/static", StaticFiles(directory="static"), name="static")` — empty `.gitkeep` only; no flags yet |

---

## Recommended Architecture

### Decision: In-Memory Python Module for Prefix Data

Do NOT use MongoDB for this. The prefix table is:
- Static — it changes only when ITU publishes new allocations (rare)
- Small — ~600 rows; fits in a Python `list` of `dict` or `list` of `tuple` without measurable memory impact
- Read-only — no operator writes, no per-operator scoping, no concurrency concern
- Pure lookup — no pagination, no aggregation, no cross-collection joins needed

A MongoDB collection adds a round-trip I/O call on every `qso_row.html` render. With 50 rows per page that would be 50 blocking async lookups per page load (or one bulk fetch + Python-side join). Both options are strictly worse than an in-memory dict lookup that costs zero I/O.

**Verdict:** Python module `app/callsign/prefixes.py` — loaded once at import time, stays in process memory. No DB collection, no startup async init required.

---

## System Overview

```
Request path for /log/view (50 QSOs per page):

Browser ──HTMX──> GET /log/view
                       │
                  log_view() in ui_router.py
                       │
              get_qso_page() ──> MongoDB (one query, 50 docs)
                       │
              [_qso_to_view_dict(q) for q in qsos_raw]
                       │  adds "flag_iso" key via call to
                       │  lookup_prefix(qso.CALL)
                       │
              Jinja2Templates.TemplateResponse
                       │  qso list with flag_iso included
                       │
              log_table.html
                       │
              qso_row.html (50x)
                       │  {{ qso.flag_iso }} → <span class="fi fi-xx">
                       │
              <-- HTML partial

No per-row DB calls. Zero I/O beyond the single MongoDB page query.
```

---

## Component Boundaries

### New Components

| Component | Location | Responsibility |
|-----------|----------|---------------|
| Prefix data module | `app/callsign/prefixes.py` | Bundled ITU prefix range table as a Python list literal; `lookup_prefix(call: str) -> str \| None` function that returns ISO alpha-2 code or `None` |
| `app/callsign/__init__.py` | `app/callsign/__init__.py` | Empty package marker |
| Flag SVG assets | `static/flags/<iso>.svg` | One SVG per country, ISO alpha-2 lowercase filename (e.g., `us.svg`, `gb.svg`) |

### Modified Components

| Component | What Changes | Why |
|-----------|-------------|-----|
| `_qso_to_view_dict()` in `app/qso/ui_router.py` | Add `"flag_iso": lookup_prefix(qso.CALL)` to the returned dict | Single place where QSO Beanie docs are converted to template dicts; keeps flag logic out of templates |
| `qso_row.html` | Add flag `<img>` or CSS span next to `{{ qso.CALL }}` inside the callsign `<td>` | The only display change |
| `app/qso/ui_router.py` imports | Add `from app.callsign.prefixes import lookup_prefix` | Wire in the lookup |

No changes to: QSO model, MongoDB queries, service layer, ADIF import/export, auth, admin, feed router, or any other route.

---

## How the ISO Code Reaches the Template

### Approach: Pre-computed in `_qso_to_view_dict()`

**Rationale over alternatives:**

| Option | Verdict | Reason |
|--------|---------|--------|
| Jinja2 filter `{{ qso.CALL \| prefix_flag }}` | Viable but secondary | Filter registration on `Jinja2Templates` is per-instance (`templates.env.filters["x"] = fn`); requires registering in `ui_router.py` on module load; hides the lookup inside template logic rather than Python logic; harder to unit-test |
| Pre-computed in `_qso_to_view_dict()` | **Recommended** | Keeps templates dumb; `flag_iso` is just another string in the dict; testable with a simple dict assertion; no filter registration boilerplate; consistent with how `FREQ`, `RST_SENT` etc. already work |
| Computed at template context (pass lookup fn to ctx) | Not viable | Jinja2 templates cannot call arbitrary Python functions directly; would require passing the function as a context variable which is unusual and obscure |
| Stored in QSO MongoDB document | Wrong layer | Flag display is a presentation concern; it changes when ITU updates allocations, not when the QSO is logged; denormalizing it into QSO documents would require backfill on every ITU update |

**Implementation:**

```python
# In _qso_to_view_dict() — app/qso/ui_router.py
from app.callsign.prefixes import lookup_prefix

def _qso_to_view_dict(qso: QSO) -> dict:
    d = {
        "id": str(qso.id),
        "CALL": qso.CALL,
        "BAND": qso.BAND or "",
        "MODE": qso.MODE or "",
        "qso_date_utc": qso.qso_date_utc,
        "flag_iso": lookup_prefix(qso.CALL),   # str | None
    }
    extra = qso.model_extra or {}
    d["FREQ"] = extra.get("FREQ", "")
    d["RST_SENT"] = extra.get("RST_SENT", "")
    d["RST_RCVD"] = extra.get("RST_RCVD", "")
    d["QSO_DATE"] = extra.get("QSO_DATE", "")
    d["TIME_ON"] = extra.get("TIME_ON", "")
    return d
```

**In `qso_row.html`:**

```html
<td>
  {% if qso.flag_iso %}
    <img src="/static/flags/{{ qso.flag_iso }}.svg"
         alt="{{ qso.flag_iso }}"
         width="20" height="15"
         style="vertical-align:middle;margin-right:4px;">
  {% endif %}
  {{ qso.CALL }}
</td>
```

Graceful fallback is implicit: `flag_iso` is `None` when no prefix matches → the `{% if %}` block is skipped, callsign renders alone, no error.

---

## Prefix Lookup Function Design

### Data Structure

The ITU prefix table has ~600 entries representing range allocations. Each entry is:
- `prefix_start` — first prefix in the allocated range (e.g., `"3DA"`)
- `prefix_end` — last prefix in the allocated range (e.g., `"3DM"`)
- `country_name` — ITU country/entity name
- `iso2` — ISO 3166-1 alpha-2 code (e.g., `"SZ"` for Swaziland/Eswatini)

Range-aware matching is required because ITU allocates blocks, not single prefixes. Example: `3DA–3DM` → Eswatini, `3DN–3DZ` → Fiji. A simple exact-prefix dict would miss these — you must check if the callsign prefix falls between `start` and `end` lexicographically.

### Lookup Algorithm

```
Given callsign "W1AW":

1. Strip any portable designator suffix: "W1AW/M" -> "W1AW"
2. Try progressively shorter prefixes: "W1AW", "W1A", "W1", "W"
3. For each candidate prefix P, check all table rows where prefix_start <= P <= prefix_end
4. Return iso2 of first match (longest match wins — try longest P first)
5. If no match: return None
```

**Data structure choice:** Sort the table once at module load time. For 600 rows, a linear scan with `prefix_start <= candidate <= prefix_end` is O(600) per lookup and completes in microseconds. No trie, no bisect needed at this scale.

```python
# app/callsign/prefixes.py

from __future__ import annotations

_PREFIX_TABLE: list[tuple[str, str, str, str]] = [
    # (prefix_start, prefix_end, country_name, iso2)
    ("3DA", "3DM", "Eswatini", "SZ"),
    ("3DN", "3DZ", "Fiji", "FJ"),
    # ... ~600 rows total ...
]

def lookup_prefix(callsign: str) -> str | None:
    """Return ISO 3166-1 alpha-2 code for the country that issued `callsign`.

    Uses ITU prefix range table. Returns None if no match found.
    Handles portable suffixes (W1AW/M -> strip /M before lookup).
    """
    if not callsign:
        return None
    # Strip portable designator suffix
    call = callsign.upper().split("/")[0]
    # Try progressively shorter prefixes (longest match wins)
    for length in range(len(call), 0, -1):
        candidate = call[:length]
        for start, end, _, iso2 in _PREFIX_TABLE:
            if start <= candidate <= end:
                return iso2
    return None
```

---

## Flag Asset Strategy

**Use lipis/flag-icons SVG files served from `static/flags/`.**

- MIT licensed, 4:3 ratio SVGs for all ISO 3166-1 alpha-2 countries
- Filename convention: `<lowercase-iso2>.svg` (e.g., `us.svg`, `gb.svg`)
- Self-hosted under `static/flags/` — no CDN dependency, works in offline/air-gapped setups
- The existing `app.mount("/static", ...)` already serves this path

**At build time:** Download the SVG collection and place files in `static/flags/`. The ITU covers ~200+ entities; the ISO collection has 250 flags. Not every ITU entity has an ISO code (contested territories, ITU entities without ISO status) — those will have `None` from `lookup_prefix()` and show no flag.

---

## Data Flow

### Full Page Load

```
GET /log/view
  -> log_view() fetches 50 QSOs from MongoDB (one query)
  -> [_qso_to_view_dict(q) for q in qsos_raw]
       each call: lookup_prefix(q.CALL) — in-memory, ~microseconds
  -> Jinja2 renders log.html -> log_table.html -> 50x qso_row.html
  -> Each row: {% if qso.flag_iso %}<img ...>{% endif %}{{ qso.CALL }}
```

### HTMX Partial (pagination/filter)

```
HTMX GET /log/view?page=2
  -> Same log_view() path; HX-Request header detected
  -> Returns log_table.html partial only (same qsos with flag_iso)
```

### Inline Edit Save (HTMX)

```
PATCH /log/qsos/{id}
  -> qso_update() patches MongoDB doc
  -> Refetches updated QSO via QSO.get(oid)
  -> _qso_to_view_dict(updated)  — flag_iso resolved again
  -> Returns qso_row.html partial
```

All three render paths go through `_qso_to_view_dict()`, so adding `flag_iso` there covers them all.

---

## Recommended Project Structure Changes

```
app/
├── callsign/
│   ├── __init__.py         (empty)
│   └── prefixes.py         (PREFIX_TABLE data + lookup_prefix function)
├── qso/
│   └── ui_router.py        (modified: import lookup_prefix, add flag_iso to _qso_to_view_dict)
static/
└── flags/
    ├── us.svg
    ├── gb.svg
    ├── de.svg
    └── ...  (~250 SVG files from lipis/flag-icons)
templates/
└── log/
    └── qso_row.html        (modified: add flag img next to CALL)
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: MongoDB Collection for Prefix Data

**What goes wrong:** Every row render requires an async DB call. With 50 QSOs per page that is 50 coroutine dispatches per page load even with connection pooling. The data is static and tiny; a DB adds I/O overhead with zero benefit.

**Instead:** In-memory Python module. Loaded once at import, zero I/O per lookup.

### Anti-Pattern 2: Jinja2 Filter as the Integration Point

**What goes wrong:** The filter must be registered on the `Jinja2Templates` instance. The `ui_router.py` file has its own `templates = Jinja2Templates(directory="templates")` instance separate from `main.py`'s `_templates`. Forgetting to register the filter on the right instance causes a silent template error. The filter approach also hides logic inside the template layer rather than the Python layer.

**Instead:** Pre-compute `flag_iso` in `_qso_to_view_dict()` before the template sees the data.

### Anti-Pattern 3: Storing `flag_iso` or Country Name in the QSO Document

**What goes wrong:** ITU allocations change (rarely, but they do). If country name is baked into historical QSO records, old QSOs show the wrong country after a re-allocation. The DXCC entity at time-of-contact is a distinct concept (DX chasing) from the current ITU allocation — do not conflate them.

**Instead:** Derive `flag_iso` at display time from the current prefix table. It is presentation data, not logged contact data.

### Anti-Pattern 4: Longest-Match Without Stripping Portable Suffix

**What goes wrong:** `W1AW/M` (mobile portable) would try candidates `W1AW/`, `W1AW`, etc. The `/` breaks the range comparison because ASCII `/` (0x2F) sorts before digits and letters — a candidate containing `/` will match incorrectly or not at all.

**Instead:** Strip the portable suffix (`call.split("/")[0]`) before the prefix scan.

---

## Build Order for This Milestone

Dependencies flow from data inward to display:

```
1. Prefix data + lookup function  (app/callsign/prefixes.py)
      Pure Python. No DB dependency. No FastAPI dependency.
      Fully testable with synchronous unit tests.
      Data entry: compile ~600 ITU range rows into the _PREFIX_TABLE list.

2. Flag SVG assets  (static/flags/*.svg)
      Download from lipis/flag-icons release (MIT, v7+).
      Place lowercase ISO alpha-2 named SVGs in static/flags/.
      No code change; just file addition.
      Can be done in parallel with step 1.

3. Wire lookup_prefix into _qso_to_view_dict()  (app/qso/ui_router.py)
      Add import + one dict key.
      Depends on: step 1 (function must exist).
      Test: _qso_to_view_dict() unit test asserts flag_iso key present.

4. Template update  (templates/log/qso_row.html)
      Add {% if qso.flag_iso %}<img ...>{% endif %} in CALL cell.
      Depends on: step 2 (SVG files must exist to render) + step 3 (flag_iso key).
      Test: integration test or manual browser check.
```

**Critical path:** Step 1 (prefix data + function) unlocks step 3. Step 2 (SVGs) and step 1 are fully parallel. Step 4 depends on both 2 and 3.

Steps 3 and 4 together touch only two files (`ui_router.py` and `qso_row.html`) and add zero new routes, zero new DB calls, and zero new middleware.

---

## Integration Point Risk Summary

| Integration Point | Change Type | Risk |
|-------------------|-------------|------|
| `_qso_to_view_dict()` — add `flag_iso` key | Additive (new dict key) | Low — templates that don't reference `flag_iso` ignore it silently |
| `qso_row.html` — add flag `<img>` | Modified template | Low — `{% if qso.flag_iso %}` guards against None; existing layout unchanged if flag_iso is None |
| `app/callsign/prefixes.py` — new module | New file | Low — pure function, no side effects, no DB |
| `static/flags/` — new directory with SVGs | New static files | Low — served by existing StaticFiles mount; missing flag files cause broken img (not a 500 error) |
| ADIF import/export | No change | None |
| MongoDB schema | No change | None |
| Auth / operator isolation | No change | None — lookup is display-only, not stored |
| Admin UI | No change | None |
| Feed SSE (`feed_row.html`) | No change unless desired | `feed_row.html` has its own template and context; flag display in the live feed is a separate decision for a future sub-task |

---

## Sources

- Live codebase inspection: `/Users/royco/ollog/app/` and `/Users/royco/ollog/templates/` (all relevant files read directly, 2026-04-04)
- lipis/flag-icons SVG collection: https://github.com/lipis/flag-icons (MIT license, ISO alpha-2 naming)
- flag-icons CDN/usage: https://flagicons.lipis.dev/
- ITU Table of International Call Sign Series (Appendix 42 to Radio Regulations): https://www.itu.int/en/ITU-R/terrestrial/fmd/Pages/call_sign_series.aspx
- ITU prefix Wikipedia reference: https://en.wikipedia.org/wiki/ITU_prefix
- FastAPI Jinja2 custom filters: https://www.slingacademy.com/article/fastapi-jinja-how-to-create-custom-filters/ (HIGH confidence — confirmed `templates.env.filters["x"] = fn` pattern)
- Callsign prefix gist (M0LTE): https://gist.github.com/M0LTE/2fe745393d23eefaab9f17bd9b36c37e (format reference)
