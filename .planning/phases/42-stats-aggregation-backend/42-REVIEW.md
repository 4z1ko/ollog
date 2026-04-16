---
phase: 42-stats-aggregation-backend
reviewed: 2026-04-16T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - app/stats/__init__.py
  - app/stats/service.py
  - app/stats/router.py
  - templates/log/stats.html
  - tests/test_stats.py
  - app/main.py
findings:
  critical: 0
  warning: 3
  info: 1
  total: 4
status: issues_found
---

# Phase 42: Code Review Report

**Reviewed:** 2026-04-16T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 42 introduces the stats aggregation backend: a service layer (`app/stats/service.py`), a cookie-authenticated UI router (`app/stats/router.py`), a stub template (`templates/log/stats.html`), and integration tests (`tests/test_stats.py`). The router registration in `app/main.py` is clean.

The core aggregation logic is sound — operator isolation and soft-delete filtering are correctly applied at the `$match` stage before every pipeline. The double-`await` pattern (`await (await collection.aggregate(...)).to_list(length=None)`) is valid for pymongo 4.x async where both `aggregate()` and `to_list()` are coroutines.

Three logic issues need attention: a `unique_entity_count` under-count for non-country ITU entities, a `total_qsos` inflation for QSOs with null `BAND`/`MODE`, and a fragile test that couples two fixtures through shared Beanie global state.

---

## Warnings

### WR-01: `unique_entity_count` under-counts when QSOs are worked in non-country ITU entities

**File:** `app/stats/service.py:56-66`

**Issue:** `lookup_prefix()` returns `None` for two distinct cases: (1) unresolvable callsigns, and (2) valid non-country ITU entities (4U prefixes for the United Nations, C7 for the World Meteorological Organization, 4Y for ICAO). Both cases are lumped into the `"Unknown"` bucket, and neither adds to `iso_seen`. This means a log containing exclusively UN/ITU special-event QSOs will return `unique_entity_count=0` while `total_qsos > 0`. More commonly, any real non-country QSO is silently excluded from the entity count, making the count a "unique country count" rather than a "unique DXCC entity count".

**Fix:** Distinguish the two `None` cases. Use a sentinel or a secondary function in `lookup_prefix` to differentiate "unresolvable" from "non-country entity". At minimum, treat non-country entities as distinct named entries:

```python
# In service.py — inside the DXCC rollup loop:
for doc in call_results:
    iso = lookup_prefix(doc["_id"])
    if iso is None:
        # lookup_prefix returns None for both /MM callsigns and non-country ITU
        # entities. Treat as a single "Unknown/Other" bucket; do NOT add to iso_seen.
        name = "Unknown"
    else:
        # Non-None iso may still be a valid country code.
        # Add to iso_seen unconditionally (already correct for country codes).
        iso_seen.add(iso)
        country = pycountry.countries.get(alpha_2=iso)
        name = country.name if country else iso
    entity_totals[name] = entity_totals.get(name, 0) + doc["count"]

# If the "Unknown" grouping should count toward unique_entity_count,
# add: if "Unknown" in entity_totals: unique_entity_count += 1
```

A cleaner long-term fix is to expand `lookup_prefix` to return a typed result (e.g., a `LookupResult` with `kind: country | special | unknown`), but the immediate fix is documenting which entities increment `iso_seen`.

---

### WR-02: `total_qsos` is overcounted relative to `band_counts` and `mode_counts` for QSOs with null BAND or MODE

**File:** `app/stats/service.py:24, 32, 40`

**Issue:** `band_pipeline` and `mode_pipeline` filter out documents where `BAND` or `MODE` is null via `if doc["_id"]` guards (lines 24 and 32). The `call_pipeline` has no equivalent guard — every non-deleted QSO for the operator is counted, including those where `BAND=None` or `MODE=None`. Since both `QSO.BAND` and `QSO.MODE` are `Optional[str]`, a QSO created without a band (e.g., via UDP from software that omits it) will increment `total_qsos` but not appear in `band_counts`. This makes `sum(band_counts.values()) < total_qsos`, which will look like a bug to users of the stats page.

**Fix:** Either count total QSOs from band/mode pipelines, or make the discrepancy intentional and document it clearly. The simplest approach is to count from a separate pipeline that does not group (just counts non-deleted QSOs):

```python
# Replace the call_pipeline / total_qsos computation:
count_pipeline = [
    match_stage,
    {"$count": "total"},
]
count_result = await (await collection.aggregate(count_pipeline)).to_list(length=None)
total_qsos = count_result[0]["total"] if count_result else 0
```

The DXCC rollup (which needs per-CALL counts) can then be separated:

```python
# Keep call_pipeline for DXCC rollup only; compute total_qsos independently.
```

If the intent is "total non-deleted QSOs including those with missing fields", the template and docstring should say so explicitly.

---

### WR-03: `test_stats_route_empty_log` relies on implicit Beanie global state shared between two fixtures

**File:** `tests/test_stats.py:181-197`

**Issue:** `test_stats_route_empty_log` uses both `stats_test_db` and `http_client` fixtures. `stats_test_db` calls `init_beanie(database=db, ...)` which sets Beanie's global document registry to `ollog_test`. `http_client` wraps the real ASGI app with `ASGITransport` but does not trigger the app's lifespan — `init_db()` is never called for the ASGI app in this test. The test works only because `stats_test_db` runs first and leaves Beanie pointing at `ollog_test`, and then the route handler's call to `get_stats()` / `User.find_one()` uses that same global state.

This is order-dependent coupling: if pytest changes fixture ordering, or if another test's `init_beanie` call runs between the two fixtures in a concurrent setup, `User.find_one("testop")` will fail with a collection error (Beanie not initialized) or silently query the wrong database, causing the test to return 401 instead of 200.

**Fix:** Either (a) run the ASGI app with lifespan in these integration tests using `httpx.AsyncClient(app=app, base_url="http://test")` with `lifespan="auto"`, or (b) add an explicit `init_beanie` call inside the `http_client` fixture when `stats_test_db` is also in scope, or (c) acknowledge the dependency in a comment:

```python
@pytest_asyncio.fixture(scope="function")
async def http_client(stats_test_db):  # explicit dependency on stats_test_db
    """ASGI test client. Requires stats_test_db to have initialized Beanie first."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

Note: the standalone `test_stats_route_requires_auth` test (which uses only `http_client` without `stats_test_db`) is not affected — it tests the unauthenticated path which raises 401 before any DB access.

---

## Info

### IN-01: Dead code — `backup_task` is always `None` in lifespan shutdown

**File:** `app/main.py:61, 86-91`

**Issue:** `backup_task` is initialized to `None` on line 61 and is never assigned a non-`None` value anywhere in the lifespan function. The `if backup_task is not None:` branch (lines 86-91) that cancels and awaits it is unreachable. The APScheduler-based backup uses `backup_scheduler`, which is correctly shut down on line 92. This appears to be scaffolding left from an earlier asyncio-task-based backup design.

**Fix:** Remove the dead branch:

```python
# Remove lines 86-91 entirely:
# if backup_task is not None:
#     backup_task.cancel()
#     try:
#         await backup_task
#     except asyncio.CancelledError:
#         pass
```

Also remove the `backup_task = None` initialization on line 61 since the variable is no longer used.

---

_Reviewed: 2026-04-16T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
