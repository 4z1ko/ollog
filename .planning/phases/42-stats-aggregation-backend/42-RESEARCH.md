# Phase 42: Stats Aggregation Backend - Research

**Researched:** 2026-04-15
**Domain:** FastAPI service layer + MongoDB aggregation + Python-side DXCC rollup
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use `pycountry` to resolve ISO alpha-2 codes to full country names for chart labels (e.g. "Germany", "Japan", "United States"). `pycountry` is already a project dependency imported in `ui_router.py`.
- **D-02:** QSOs where `lookup_prefix(CALL)` returns `None` (maritime mobile /MM, non-country ITU entities like 4U, unrecognized prefixes) are grouped under a single **"Unknown"** bucket in the DXCC chart data. Nothing is silently excluded — the operator sees all QSOs reflected.

### Claude's Discretion
- Module placement: follow the existing domain-per-module pattern — new `app/stats/` module with `service.py` and a router. The stats route is mounted at `/log/stats` via the existing `ui_router` prefix or a new router registered in `app/main.py`.
- Aggregation pipeline architecture (1 consolidated pipeline vs 3 separate): choose whichever is cleaner given the `get_motor_collection().aggregate()` pattern already established in the codebase.
- Template data shape keys: follow conventions from existing router context dicts (snake_case). Suggested shape: `{"band_counts": {...}, "mode_counts": {...}, "entity_counts": [...top-8 dicts...], "unique_entity_count": int, "total_qsos": int}`. Adjust as implementation requires — Phase 43 consumes whatever shape is returned.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STATS-06 | All statistics are scoped to the authenticated operator's log (JWT-isolated, filtered by `_operator`) | `$match {"_operator": callsign, "_deleted": False}` as first pipeline stage; `get_current_operator_callsign_cookie` dependency on the route handler enforces JWT isolation |
| STATS-07 | Stats page shows an empty-state message when the operator has no QSOs logged | `get_stats()` must return the same dict shape with `total_qsos == 0` and empty dicts/lists; the route must not raise when the collection is empty for this operator |
</phase_requirements>

---

## Summary

Phase 42 builds a new `app/stats/` module: a `get_stats(callsign)` service function and a `GET /log/stats` route handler. The service runs MongoDB aggregation pipelines against the `qsos` collection using the established `QSO.get_motor_collection().aggregate()` pattern. DXCC entity resolution is purely Python-side: aggregate by CALL in MongoDB, then call `lookup_prefix()` on each CALL in the result, group by the resolved ISO code, resolve ISO codes to country names via `pycountry`, and finally sort and truncate to top-8 with an optional "Other" bucket.

The implementation is entirely within the existing project stack — no new dependencies. Two patterns already in the codebase cover everything: Motor aggregation access (from `app/feed/manager.py` and STATE.md architecture decisions) and the `lookup_prefix()` + `pycountry` combination (already used in `app/qso/ui_router.py`). The route is a standard cookie-auth Jinja2 `TemplateResponse` with `templates/log/stats.html` as a stub (template content is Phase 43 scope).

**Primary recommendation:** Create `app/stats/service.py` with `get_stats()` and `app/stats/router.py` with the route; register the router in `app/main.py`; use 3 separate aggregation pipelines for clarity (band, mode, CALL-counts), each guarded by the same `$match` stage.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| JWT-isolated aggregation | API / Backend (FastAPI service) | Database / Storage (MongoDB $match) | Operator isolation is a backend security property; the pipeline guard enforces it at the DB layer but the service owns the invariant |
| DXCC entity resolution | API / Backend (Python service) | — | `lookup_prefix()` is pure-Python bisect — cannot run inside MongoDB |
| Country name display labels | API / Backend (Python service) | — | `pycountry` lookup is Python-side, result is passed into template context |
| Route auth / cookie handling | Frontend Server (FastAPI cookie auth) | — | `get_current_operator_callsign_cookie` dependency, consistent with all other `/log/*` routes |
| Template rendering | Frontend Server (Jinja2) | — | `TemplateResponse` pattern; Phase 43 fills the stub |
| Data persistence (qsos) | Database / Storage (MongoDB) | — | `qsos` collection; no changes to schema |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (project-pinned) | Route handler, Depends() injection | Existing app framework |
| Motor (via Beanie) | (project-pinned) | `QSO.get_motor_collection().aggregate()` | Established aggregation access pattern per STATE.md |
| pycountry | (project-pinned) | ISO alpha-2 → country name | Already installed, already imported in `ui_router.py` |
| Jinja2 (via FastAPI) | (project-pinned) | `TemplateResponse` for stats page | Consistent with all other UI routes |

[VERIFIED: codebase grep — `pycountry` import in `app/qso/ui_router.py` line 24; Motor aggregation pattern in STATE.md and referenced in `app/feed/manager.py`]

### No New Dependencies

Per STATE.md architecture decisions: "No new Python dependencies — all aggregation uses existing Motor collection access and existing `lookup_prefix()` + `pycountry`. `requirements.txt` does not change." [VERIFIED: STATE.md §v2.3 Architecture Decisions]

---

## Architecture Patterns

### System Architecture Diagram

```
Browser GET /log/stats
        |
        v
[FastAPI route: GET /log/stats]
        |
        v (Depends)
[get_current_operator_callsign_cookie]
  — decode JWT cookie → callsign
        |
        v
[get_stats(callsign)]  ← app/stats/service.py
        |
        +---> Pipeline A: $match + $group by BAND
        |         ↓ Motor aggregate
        |     band_counts: {BAND: count, ...}
        |
        +---> Pipeline B: $match + $group by MODE
        |         ↓ Motor aggregate
        |     mode_counts: {MODE: count, ...}
        |
        +---> Pipeline C: $match + $group by CALL + $count total
        |         ↓ Motor aggregate
        |     call_counts: [{CALL, count}, ...]
        |     total_qsos: int
        |
        +---> Python-side DXCC rollup
              for each (CALL, count):
                iso = lookup_prefix(CALL)  → str|None
                entity = pycountry name or "Unknown"
              aggregate by entity → {entity: total_count}
              unique_entity_count = len(distinct ISOs, excl. None)
              sort desc → top-8 + optional "Other"
                  |
                  v
[TemplateResponse "log/stats.html"]
  context: {
    band_counts: dict,
    mode_counts: dict,
    entity_counts: [{"name": str, "count": int}, ...],
    unique_entity_count: int,
    total_qsos: int,
    callsign: str,
  }
```

### Recommended Project Structure

```
app/stats/
├── __init__.py        # empty (follow project convention)
├── service.py         # get_stats(callsign: str) -> dict
└── router.py          # stats_router: GET /log/stats

templates/log/
└── stats.html         # stub only in Phase 42

app/main.py            # add: app.include_router(stats_router, include_in_schema=False)
```

### Pattern 1: MongoDB Aggregation via Motor

**What:** Access the raw Motor collection through Beanie's `get_motor_collection()`, execute an async aggregation pipeline, await the full result list.

**When to use:** Any aggregation that Beanie's query builder doesn't support natively (group-by, count, $sum).

**Example:**
```python
# Source: STATE.md §v2.3 Architecture Decisions + app/feed/manager.py Motor access pattern
from app.qso.models import QSO

async def get_band_counts(callsign: str) -> dict[str, int]:
    pipeline = [
        {"$match": {"_operator": callsign, "_deleted": False}},  # FIRST stage — required
        {"$group": {"_id": "$BAND", "count": {"$sum": 1}}},
    ]
    collection = QSO.get_motor_collection()
    cursor = collection.aggregate(pipeline)
    results = await cursor.to_list(length=None)
    return {doc["_id"]: doc["count"] for doc in results if doc["_id"]}
```

[VERIFIED: STATE.md §v2.3 Architecture Decisions — `QSO.get_motor_collection().aggregate([...])` with `await cursor.to_list(length=None)` is the confirmed pattern]

### Pattern 2: Python-Side DXCC Rollup

**What:** Aggregate by CALL in MongoDB (cheap — hits compound index), then resolve each CALL to an ISO alpha-2 in Python, then re-sum counts by entity. "Unknown" bucket absorbs all `None` returns.

**When to use:** Any entity-level grouping that requires `lookup_prefix()`.

**Example:**
```python
# Source: app/callsign/prefixes.py (lookup_prefix), app/qso/ui_router.py (pycountry usage)
import pycountry
from app.callsign.prefixes import lookup_prefix

def _build_entity_counts(
    call_counts: list[dict],  # [{"_id": "W1AW", "count": 5}, ...]
) -> tuple[dict[str, int], int]:
    """Return (entity_name -> total_count, unique_entity_count).

    unique_entity_count counts distinct ISO codes (excludes "Unknown").
    """
    entity_totals: dict[str, int] = {}
    iso_seen: set[str] = set()

    for doc in call_counts:
        call = doc["_id"]
        count = doc["count"]
        iso = lookup_prefix(call)
        if iso is None:
            name = "Unknown"
        else:
            iso_seen.add(iso)
            country = pycountry.countries.get(alpha_2=iso)
            name = country.name if country else iso  # fallback to ISO code

        entity_totals[name] = entity_totals.get(name, 0) + count

    return entity_totals, len(iso_seen)
```

### Pattern 3: Top-8 Truncation with "Other" Guard

**What:** Sort entity dict by count descending, take top 8, sum remainder into "Other" only if non-empty.

**Example:**
```python
# Source: CONTEXT.md §Specific Ideas + STATE.md "Other" bucket guard
def _truncate_to_top8(entity_totals: dict[str, int]) -> list[dict]:
    """Return sorted list of {"name": str, "count": int} dicts, capped at 8.

    Appends "Other" slice only when more than 8 distinct entities exist.
    "Unknown" bucket participates in sort like any other entity.
    """
    sorted_entities = sorted(entity_totals.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_entities) <= 8:
        return [{"name": k, "count": v} for k, v in sorted_entities]
    top8 = sorted_entities[:8]
    remainder = sum(v for _, v in sorted_entities[8:])
    result = [{"name": k, "count": v} for k, v in top8]
    result.append({"name": "Other", "count": remainder})
    return result
```

### Pattern 4: Router Registration in main.py

**What:** Add stats router with `include_in_schema=False` (UI route, not REST API). Follows the exact pattern used for `qso_ui_router`.

**Example:**
```python
# Source: app/main.py lines 111-113 (ui_router registration pattern)
from app.stats.router import stats_router  # noqa: E402
app.include_router(stats_router, include_in_schema=False)
```

### Pattern 5: Route Handler Structure

**What:** Cookie-auth protected GET route returning `TemplateResponse`. Mirrors `log_view` and `about_page` in `app/qso/ui_router.py`.

**Example:**
```python
# Source: app/qso/ui_router.py — about_page and form_page patterns
@stats_router.get("/log/stats", response_class=HTMLResponse)
async def stats_page(
    request: Request,
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    data = await get_stats(callsign)
    return templates.TemplateResponse(
        request,
        "log/stats.html",
        {**data, "callsign": callsign},
    )
```

Note: The stats router should NOT use the `/log` prefix if mounted standalone (it already has `/log/stats` as its full path), OR it can use `prefix="/log"` and declare the endpoint as `/stats`. Follow the `qso_ui_router` model which uses `prefix="/log"` in `APIRouter(prefix="/log")`.

### Anti-Patterns to Avoid

- **Pipeline without `$match` first:** A pipeline that groups without a leading `$match` scans all operators' QSOs. Every pipeline in `get_stats()` must begin with `{"$match": {"_operator": callsign, "_deleted": False}}`. [VERIFIED: STATE.md §v2.3 Architecture Decisions — "pipeline guard requirement"]
- **Computing `unique_entity_count` after truncation:** The count of distinct DXCC entities must be computed from the full entity map before taking the top-8 subset. Truncation discards entities — counting after truncation produces the wrong number. [VERIFIED: STATE.md §v2.3 — "unique_dxcc computed before truncation"]
- **Zero-count "Other" slice:** Only append the "Other" bucket when the remainder is non-empty (when `len(sorted_entities) > 8`). [VERIFIED: STATE.md §v2.3 — `Other` bucket guard]
- **Raising on empty log:** When `total_qsos == 0`, return the same dict shape with empty values — never `raise`, never `None`. The route handler must not throw on an empty collection for this operator. [VERIFIED: STATS-07 + CONTEXT.md §Specific Ideas]
- **`| safe` for inline chart data in templates:** Entity names can contain commas and quotes. Always use `| tojson` in templates. (Phase 43 concern, but the data shape from `get_stats()` must be JSON-serializable.) [VERIFIED: STATE.md §v2.3 — "Inline JSON safety"]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Callsign → country resolution | Custom prefix table | `lookup_prefix()` in `app/callsign/prefixes.py` | 500+ ITU ranges already handled, tested, handles /MM, /P, non-country entities |
| ISO → country name | Manual dict | `pycountry.countries.get(alpha_2=iso).name` | Already installed, full ISO 3166-1 coverage, already used in `ui_router.py` |
| Async MongoDB aggregation | pymongo cursors directly | `QSO.get_motor_collection().aggregate()` | Motor async driver already initialised by Beanie; direct pymongo would bypass the ODM setup |
| Cookie auth | Custom cookie parsing | `Depends(get_current_operator_callsign_cookie)` | Established auth dep used across all UI routes |

**Key insight:** The DXCC rollup requires two passes — MongoDB groups by CALL, Python groups by entity. Attempting to do country resolution inside MongoDB is impossible because `lookup_prefix()` is pure-Python bisect with no MongoDB equivalent.

---

## Common Pitfalls

### Pitfall 1: Missing `_deleted: False` in Pipeline Match

**What goes wrong:** Soft-deleted QSOs are included in band/mode/entity counts, inflating all stats.

**Why it happens:** The model's `is_deleted` Python attribute serialises to `_deleted` in MongoDB. Forgetting the guard on an aggregation pipeline (where Beanie's document-level filtering is bypassed) includes deleted records.

**How to avoid:** Every `$match` stage must include both `"_operator": callsign` AND `"_deleted": False`.

**Warning signs:** Stats counts don't match the visible log row count.

### Pitfall 2: Returning Different Dict Shapes for Empty vs Non-Empty Logs

**What goes wrong:** Template raises `KeyError` or `UndefinedError` when operator has zero QSOs, because the route returns `{}` or `None` instead of the full shape with empty values.

**Why it happens:** Service function short-circuits with an early return before building the full shape.

**How to avoid:** Always return the complete shape:
```python
{"band_counts": {}, "mode_counts": {}, "entity_counts": [], "unique_entity_count": 0, "total_qsos": 0}
```

**Warning signs:** `/log/stats` works for operators with QSOs but throws 500 for new operators.

### Pitfall 3: Counting Unique Entities After Truncation

**What goes wrong:** `unique_entity_count` returns 8 (or fewer) for any operator with more than 8 entities, because the count is taken from the truncated top-8 list.

**Why it happens:** Forgetting that the top-8 truncation happens after the entity map is fully built.

**How to avoid:** Store `len(iso_seen)` before calling `_truncate_to_top8()`.

**Warning signs:** An operator who worked 45 DXCC entities sees "8 entities" on the stats page.

### Pitfall 4: Router Prefix Collision

**What goes wrong:** `/log/stats` returns 404 because the router's prefix + endpoint path combines incorrectly.

**Why it happens:** If `stats_router = APIRouter(prefix="/log")` and endpoint is `/log/stats`, the actual path becomes `/log/log/stats`.

**How to avoid:** Either use `APIRouter(prefix="/log")` with endpoint `@stats_router.get("/stats")`, or use `APIRouter()` with endpoint `@stats_router.get("/log/stats")`. The `qso_ui_router` uses `prefix="/log"` — match this convention.

**Warning signs:** GET `/log/stats` returns 404 even after router is registered.

### Pitfall 5: `get_motor_collection()` Called Before Beanie Init

**What goes wrong:** `AttributeError` or `RuntimeError` if `get_motor_collection()` is called at import time (module-level) rather than inside the async route/service function.

**Why it happens:** Beanie initialisation happens in `lifespan()` — before that, `get_motor_collection()` has no bound database.

**How to avoid:** Only call `QSO.get_motor_collection()` inside `async def` function bodies, never at module level or in a class-level constant.

---

## Code Examples

### Full `get_stats()` Sketch

```python
# Source: synthesised from STATE.md patterns + CONTEXT.md canonical refs
import pycountry
from app.callsign.prefixes import lookup_prefix
from app.qso.models import QSO


async def get_stats(callsign: str) -> dict:
    """Compute band counts, mode counts, DXCC entity counts for one operator.

    Returns same dict shape for empty and non-empty logs (STATS-07).
    All pipelines begin with $match guard (STATS-06).
    """
    collection = QSO.get_motor_collection()
    match_stage = {"$match": {"_operator": callsign, "_deleted": False}}

    # --- Band counts ---
    band_pipeline = [
        match_stage,
        {"$group": {"_id": "$BAND", "count": {"$sum": 1}}},
    ]
    band_results = await collection.aggregate(band_pipeline).to_list(length=None)
    band_counts = {doc["_id"]: doc["count"] for doc in band_results if doc["_id"]}

    # --- Mode counts ---
    mode_pipeline = [
        match_stage,
        {"$group": {"_id": "$MODE", "count": {"$sum": 1}}},
    ]
    mode_results = await collection.aggregate(mode_pipeline).to_list(length=None)
    mode_counts = {doc["_id"]: doc["count"] for doc in mode_results if doc["_id"]}

    # --- CALL-level counts for DXCC rollup ---
    call_pipeline = [
        match_stage,
        {"$group": {"_id": "$CALL", "count": {"$sum": 1}}},
    ]
    call_results = await collection.aggregate(call_pipeline).to_list(length=None)
    total_qsos = sum(doc["count"] for doc in call_results)

    # Early return for empty log
    if total_qsos == 0:
        return {
            "band_counts": {},
            "mode_counts": {},
            "entity_counts": [],
            "unique_entity_count": 0,
            "total_qsos": 0,
        }

    # --- Python-side DXCC rollup ---
    entity_totals: dict[str, int] = {}
    iso_seen: set[str] = set()
    for doc in call_results:
        iso = lookup_prefix(doc["_id"])
        if iso is None:
            name = "Unknown"
        else:
            iso_seen.add(iso)
            country = pycountry.countries.get(alpha_2=iso)
            name = country.name if country else iso
        entity_totals[name] = entity_totals.get(name, 0) + doc["count"]

    unique_entity_count = len(iso_seen)  # BEFORE truncation

    # Sort and truncate to top-8 + optional "Other"
    sorted_entities = sorted(entity_totals.items(), key=lambda x: x[1], reverse=True)
    if len(sorted_entities) <= 8:
        entity_counts = [{"name": k, "count": v} for k, v in sorted_entities]
    else:
        top8 = sorted_entities[:8]
        remainder = sum(v for _, v in sorted_entities[8:])
        entity_counts = [{"name": k, "count": v} for k, v in top8]
        entity_counts.append({"name": "Other", "count": remainder})

    return {
        "band_counts": band_counts,
        "mode_counts": mode_counts,
        "entity_counts": entity_counts,
        "unique_entity_count": unique_entity_count,
        "total_qsos": total_qsos,
    }
```

### Stub Template (`templates/log/stats.html`)

```html
{# Phase 42 stub — charts added in Phase 43 #}
{% extends "base_app.html" %}
{% block content %}
<div>Stats coming soon. Total QSOs: {{ total_qsos }}</div>
{% endblock %}
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (project root) |
| Quick run command | `uv run pytest tests/test_stats.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STATS-06 | `get_stats()` returns only queried operator's data | unit/integration | `uv run pytest tests/test_stats.py::test_stats_operator_isolation -x` | Wave 0 |
| STATS-06 | Route `/log/stats` returns 401 without auth cookie | integration | `uv run pytest tests/test_stats.py::test_stats_route_requires_auth -x` | Wave 0 |
| STATS-07 | `get_stats()` returns `total_qsos=0` and empty shape for empty log | unit/integration | `uv run pytest tests/test_stats.py::test_stats_empty_log -x` | Wave 0 |
| STATS-07 | Route `/log/stats` returns 200 for operator with zero QSOs | integration | `uv run pytest tests/test_stats.py::test_stats_route_empty_log -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_stats.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_stats.py` — covers STATS-06 (isolation) and STATS-07 (empty-state)
- [ ] Shared fixtures: `conftest.py` already provides `test_db` fixture (includes only `QSO` model); stats tests may need the same `isolation_test_db` pattern from `test_operator_isolation.py` which includes `User` model

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `get_current_operator_callsign_cookie` — cookie JWT auth |
| V3 Session Management | no | Existing session mechanism unchanged |
| V4 Access Control | yes | Operator isolation enforced via `$match {"_operator": callsign}` in every pipeline |
| V5 Input Validation | no | No user-supplied filter inputs in this phase |
| V6 Cryptography | no | No new crypto |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-operator data leakage (missing `_operator` filter) | Information Disclosure | `$match {"_operator": callsign, "_deleted": False}` as FIRST stage in every pipeline |
| Unauthenticated access to `/log/stats` | Elevation of Privilege | `Depends(get_current_operator_callsign_cookie)` on route; app-level exception handler redirects 401/403 on `/log/*` to `/log/login` |

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — phase is pure Python/MongoDB code changes using existing installed packages).

---

## Runtime State Inventory

Step 2.5: SKIPPED — Phase 42 is a greenfield feature addition, not a rename/refactor/migration.

---

## Open Questions

1. **Router prefix strategy: standalone router vs extending `qso_ui_router`**
   - What we know: CONTEXT.md says "mounted at `/log/stats` via the existing `ui_router` prefix or a new router registered in `app/main.py`". Claude's discretion.
   - What's unclear: Whether to add the route to the existing `qso_ui_router` (saves a router file) or create a separate `app/stats/router.py` (follows domain-per-module convention).
   - Recommendation: Create a separate `app/stats/router.py` with `APIRouter(prefix="/log", tags=["stats-ui"])`. This follows the domain-per-module convention (profile, tokens, feed all have their own module) and avoids growing `ui_router.py` further. Register in `main.py` after the other routers.

2. **`test_all_qso_routes_inject_callsign_from_jwt` test update**
   - What we know: `test_operator_isolation.py` audits all routes under `QSO_PATH_PREFIXES` and verifies they have a callsign dep. `/log/stats` starts with `/log/` which is NOT in `QSO_PATH_PREFIXES` (the prefix list is `/api/qsos`, `/log/qsos`, `/log/view`, etc.) — so the new route won't be checked by that test.
   - What's unclear: Whether the planner should add `/log/stats` to `QSO_PATH_PREFIXES` in the test.
   - Recommendation: Add a targeted test in `test_stats.py` that verifies the stats route has the cookie-auth dependency directly, rather than modifying the existing isolation audit.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `QSO.get_motor_collection()` returns a Motor `AsyncCollection` with `.aggregate()` that returns an async cursor supporting `.to_list(length=None)` | Code Examples | Pipeline would fail; need to check Motor API docs — but this is confirmed in STATE.md |

**Note:** A1 is backed by STATE.md which records this as a pre-confirmed architecture decision from prior research. Risk is very low.

---

## Sources

### Primary (HIGH confidence)

- `app/qso/models.py` — QSO Beanie document, field aliases, compound index (VERIFIED: read directly)
- `app/qso/service.py` — Service layer pattern, query structure (VERIFIED: read directly)
- `app/qso/ui_router.py` — `pycountry` usage pattern, `TemplateResponse` pattern, cookie auth dep (VERIFIED: read directly)
- `app/callsign/prefixes.py` — `lookup_prefix()` public API, `None` return for non-country entities (VERIFIED: read directly)
- `app/auth/dependencies.py` — `get_current_operator_callsign_cookie` signature (VERIFIED: read directly)
- `app/main.py` — Router registration pattern, include_in_schema=False convention (VERIFIED: read directly)
- `.planning/STATE.md` §v2.3 Architecture Decisions — Motor aggregation pattern, pipeline guard, DXCC rollup strategy, "Other" bucket guard, unique_dxcc before truncation (VERIFIED: read directly)
- `.planning/phases/42-stats-aggregation-backend/42-CONTEXT.md` — All locked decisions and module placement guidance (VERIFIED: read directly)

### Secondary (MEDIUM confidence)

- `tests/test_operator_isolation.py` — Confirms test infrastructure patterns (pytest-asyncio, `isolation_test_db` fixture, `init_beanie` with `User` model when needed) (VERIFIED: read directly)
- `tests/conftest.py` — `test_db` fixture pattern (VERIFIED: read directly)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already project dependencies, verified in codebase
- Architecture: HIGH — patterns are established in existing codebase and confirmed in STATE.md
- Pitfalls: HIGH — derived directly from STATE.md architecture decisions and CONTEXT.md
- Test infrastructure: HIGH — pattern derived from existing tests

**Research date:** 2026-04-15
**Valid until:** Stable indefinitely (internal codebase — no external dependency drift)
