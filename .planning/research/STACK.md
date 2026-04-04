# Stack Research

**Domain:** Ham radio callsign prefix lookup & country flag display (milestone addition to ollog)
**Researched:** 2026-04-04
**Confidence:** HIGH for storage approach and bisect; HIGH for pycountry; MEDIUM for pycountry edge cases on ITU name variants

---

## Context: What Already Exists (Do Not Re-Research)

Existing validated stack: FastAPI 0.135+, Beanie 2.1+, pymongo 4.16+, Jinja2, HTMX 2.0.4, Python 3.12, Docker Compose, MongoDB 7 replica set.

Flag SVGs are already present at `app/static/flags/{iso_lower}.svg` (271 files, e.g., `us.svg`, `gb.svg`, `jp.svg`).

**Flag path discrepancy (must resolve before rendering works):** The `StaticFiles` mount in `app/main.py` uses `directory="static"`, which points to the project root `static/` directory. That directory is currently empty (only `.gitkeep`). The SVGs live at `app/static/flags/`, which is NOT served. Two resolution options:

- **Option A (recommended):** `git mv app/static/flags static/flags` — zero code changes, aligns with Dockerfile `COPY static/ static/` line.
- **Option B:** Change `StaticFiles(directory="app/static")` and update Dockerfile. More disruptive.

Option A is the right call.

---

## Recommended Stack (New Additions Only)

### New Library

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `pycountry` | `>=26.2.16` | Map ITU country name strings to ISO 3166-1 alpha-2 codes at startup | Handles ITU long-form names via `search_fuzzy()` — e.g., "United States of America" → `US`, "Lao People's Democratic Republic" → `LA`. Pure Python, no C extensions, no external service. Released Feb 2026. |

### No New Libraries Required For

| Capability | Tool | Reason |
|------------|------|--------|
| Prefix range lookup | Python `bisect` (stdlib) | 340-row static table; binary search over sorted list of range tuples gives O(log n) in microseconds. No dependency to add. |
| Flag URL construction | Jinja2 custom filter (built-in pattern) | Single string transform. Register via `templates.env.filters["flag_url"] = fn`. No library needed. |
| CSV parsing of prefix table | Python `csv` (stdlib) | Standard library. Parses the ITU range CSV at module import time. |

---

## Installation

```bash
# Add to pyproject.toml dependencies
uv add pycountry
```

One new package. Everything else uses Python stdlib or the existing Jinja2/FastAPI setup.

---

## Storage Decision: Static Python Module (Not MongoDB)

**Recommendation: In-memory Python module, loaded once at application startup.**

The ITU prefix table (~340 CSV rows of `start-end, country` ranges) is static reference data. It does not change per-user, per-request, or at runtime. Loading it from MongoDB would require:
- A new Beanie Document class and collection
- A startup seeding step (with idempotency logic)
- An async database query on every callsign render

None of these are justified when a module-level data structure gives the same result in microseconds with no infrastructure.

**Recommended data structure:**

```python
# app/callsign/prefix_data.py  — built once at import time from bundled CSV
_RANGES: list[tuple[str, str, str]] = []   # (start_prefix, end_prefix, country_name)
_STARTS: list[str] = []                    # parallel list for bisect

def lookup_callsign(callsign: str) -> str | None:
    """Return ITU country name for callsign prefix, or None if not found.

    Tries 3-char, then 2-char, then 1-char prefix against the range table.
    """
    ...
```

The CSV is bundled as a project asset (e.g., `app/callsign/itu_prefixes.csv`). No network call, no DB query, no startup migration.

---

## ISO Mapping Decision: pycountry With Exceptions Dict

**Recommendation: `pycountry.countries.search_fuzzy()` + a small hardcoded exceptions dict for known failures.**

`pycountry` (v26.2.16) is the correct primary tool:
- `search_fuzzy("United States of America")[0].alpha_2` → `"US"` (confirmed)
- `search_fuzzy("United Kingdom of Great Britain and Northern Ireland")[0].alpha_2` → `"GB"` (confirmed)
- Handles unicode normalization and name variants automatically

**Usage pattern — build at startup, not per-request:**

```python
import pycountry

# Known ITU names that pycountry misresolves (LOW confidence — verify at build time)
_EXCEPTIONS: dict[str, str] = {
    "Korea (Republic of)": "KR",
    "Korea (Democratic People's Republic of)": "KP",
    # add others discovered during integration testing
}

def country_name_to_iso(name: str) -> str | None:
    if name in _EXCEPTIONS:
        return _EXCEPTIONS[name]
    try:
        return pycountry.countries.search_fuzzy(name)[0].alpha_2.lower()
    except LookupError:
        return None
```

Call this once per unique country name from the prefix table (~50 distinct countries). Cache results in a `dict[str, str | None]`. Log warnings for `None` returns — these need exception entries.

**Why not `iso3166` package:** `iso3166` uses exact name matching against its own canonical names. ITU names like "United States of America" will not match `iso3166`'s "United States" entry without preprocessing. `pycountry.search_fuzzy()` eliminates that problem.

**Why not a hand-rolled dict:** Maintainable for ~50 entries, but `pycountry` handles the majority automatically. Reserve the exceptions dict for the handful of ITU edge cases that `search_fuzzy()` gets wrong.

---

## Jinja2 Flag Rendering Decision: Custom Filter

**Recommendation: Register a `flag_url` filter on the existing Jinja2 environment.**

```python
# In shared template setup (e.g., app/callsign/filters.py)
def flag_url(iso_code: str | None) -> str:
    """Convert ISO 3166-1 alpha-2 code to flag SVG URL."""
    if not iso_code:
        return ""
    return f"/static/flags/{iso_code.lower()}.svg"
```

Register once after `Jinja2Templates` is instantiated:

```python
templates.env.filters["flag_url"] = flag_url
```

Template usage:

```html
{% if qso.country_iso %}
  <img src="{{ qso.country_iso | flag_url }}"
       alt="{{ qso.country_iso }}"
       width="20"
       loading="lazy"
       onerror="this.style.display='none'">
{% endif %}
```

The `onerror` handler silently hides the `<img>` if an ISO code has no corresponding SVG (e.g., Antarctica, disputed territories). This avoids broken image icons for edge-case callsigns.

**Why a filter over a Jinja2 macro:** A filter is callable from any template without an `{% import %}` statement. For a pure string transform (code → URL), a filter is the correct abstraction. Use a macro only if the rendering logic grows to include conditional classes, multiple elements, or tooltip text.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Prefix storage | Static Python module + `bisect` | MongoDB collection | Static data, no per-user variation. MongoDB adds collection, seed migration, async query overhead for zero benefit. |
| Prefix storage | Static Python module + `bisect` | In-memory dict (exact prefix keys) | ITU data uses ranges (WAA–WAZ), not individual prefix strings. A dict of exact keys would require expanding ranges to thousands of entries. `bisect` over the compact range list is the correct approach. |
| Prefix lookup library | Custom `bisect` over bundled CSV | `pyhamtools` | pyhamtools returns DXCC-format country names (e.g., "Fed. Rep. of Germany"), not ISO alpha-2. Requires downloading or bundling `cty.plist`. Adds `lxml` dependency (needs `libxml2-dev`, `libxslt-dev` system packages). Version status on PyPI is unclear (0.10.0 on PyPI vs 0.12.0 in docs). Solves a harder problem than needed. |
| Prefix lookup library | Custom `bisect` over bundled CSV | `callsignlookuptools` | Wraps QRZ/callook.info APIs — requires paid API key and internet connection at render time. |
| ISO name mapping | `pycountry` + exceptions dict | `iso3166` package | Exact-match only. ITU names diverge from ISO canonical names. Would require preprocessing every ITU name to match `iso3166`'s internal names. |
| Flag rendering | Jinja2 custom filter | Pass `flag_url` in template context per route | Couples URL scheme to Python router code; requires changes in every router that renders QSOs. Filter centralizes the logic in one place. |
| Flag rendering | Jinja2 custom filter | Jinja2 macro | Macros require `{% import %}` in each template. Filter is simpler for a one-argument string transform. |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pyhamtools` | lxml/libxml2 system dependency, DXCC names not ISO alpha-2, unclear PyPI version status | `bisect` + bundled CSV + `pycountry` |
| MongoDB prefix collection | Static reference data belongs in the codebase, not the database | Bundled Python module loaded at startup |
| Real-time QRZ/HamQTH API | Requires API subscription, adds 100–500ms latency to every log row render, fails offline | Static ITU prefix table |
| Redis or other cache | 340-row in-memory dict lookup is already microseconds. Caching adds infrastructure with no measurable gain. | Module-level dict |
| Country name stored on QSO document | Prefix lookup resolves at render time — no data stored. Avoids data staleness if prefix table is corrected later. | Render-time resolution from `CALL` field |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `pycountry>=26.2.16` | Python 3.12, FastAPI 0.135+, Beanie 2.1+ | Pure Python wheel (8.0 MB, includes ISO data). No C extensions. No known conflicts with existing stack. |
| `bisect` (stdlib) | Python 3.12 | Built-in, no install required. |
| `csv` (stdlib) | Python 3.12 | Built-in, no install required. |

---

## Recommended pyproject.toml Change

```toml
[project]
dependencies = [
    # ... existing deps unchanged ...
    "fastapi[standard]>=0.135.0",
    "beanie>=2.1.0",
    "pymongo>=4.16.0",
    "pyjwt>=2.12.0",
    "pwdlib[argon2]>=0.3.0",
    "pydantic-settings>=2.0",
    "maidenhead>=1.8.0",
    "pydantic[email]>=2.0",
    # NEW for callsign prefix lookup milestone:
    "pycountry>=26.2.16",
]
```

---

## Sources

- [pycountry on PyPI](https://pypi.org/project/pycountry/) — v26.2.16, released Feb 2026. HIGH confidence.
- [pycountry GitHub](https://github.com/pycountry/pycountry) — `search_fuzzy()` API, fuzzy matching behavior. HIGH confidence.
- [Python bisect docs](https://docs.python.org/3/library/bisect.html) — stdlib O(log n) range lookup. HIGH confidence.
- [pyhamtools GitHub](https://github.com/dh1tw/pyhamtools) — DXCC name format, lxml dependency confirmed. MEDIUM confidence (PyPI version 0.10.0 vs docs 0.12.0 discrepancy noted).
- [FastAPI + Jinja2 custom filters](https://www.slingacademy.com/article/fastapi-jinja-how-to-create-custom-filters/) — `templates.env.filters[name] = fn` pattern. HIGH confidence.
- [libraries.io pycountry](https://libraries.io/pypi/pycountry) — version 26.2.16 on PyPI confirmed. HIGH confidence.

---

*Stack research for: callsign prefix lookup & country flag display (ollog milestone)*
*Researched: 2026-04-04*
