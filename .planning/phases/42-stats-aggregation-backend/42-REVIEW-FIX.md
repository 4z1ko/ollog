---
phase: 42-stats-aggregation-backend
fixed_at: 2026-04-16T00:00:00Z
review_path: .planning/phases/42-stats-aggregation-backend/42-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 42: Code Review Fix Report

**Fixed at:** 2026-04-16T00:00:00Z
**Source review:** .planning/phases/42-stats-aggregation-backend/42-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (WR-01, WR-02, WR-03 — critical_warning scope)
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: `unique_entity_count` under-counts when QSOs are worked in non-country ITU entities

**Files modified:** `app/stats/service.py`
**Commit:** d56f13c
**Applied fix:** After computing `unique_entity_count = len(iso_seen)`, added a check: `if "Unknown" in entity_totals: unique_entity_count += 1`. This ensures the Unknown/Other bucket (which captures both unresolvable callsigns and non-country ITU entities such as 4U/UN, C7/WMO, 4Y/ICAO) counts as one distinct entity rather than being silently excluded from the total. Fixed: requires human verification — the +1 treatment collapses all Unknown callsigns into a single entity; a log with exclusively unknown callsigns will show `unique_entity_count=1`, which is the documented intent.

### WR-02: `total_qsos` overcounted relative to `band_counts`/`mode_counts` for null BAND/MODE QSOs

**Files modified:** `app/stats/service.py`
**Commit:** d56f13c
**Applied fix:** Replaced the `total_qsos = sum(doc["count"] for doc in call_results)` computation (which summed from the CALL-level group pipeline, including QSOs with null BAND/MODE) with a dedicated `$count` pipeline (`[match_stage, {"$count": "total"}]`). The `call_pipeline` is retained for the DXCC rollup only. This makes `total_qsos` semantically "all non-deleted QSOs for this operator" rather than accidentally equal to the DXCC rollup sum.

### WR-03: `test_stats_route_empty_log` relies on implicit Beanie global state shared between fixtures

**Files modified:** `tests/test_stats.py`
**Commit:** e0215df
**Applied fix:** Changed `http_client` fixture signature from `async def http_client()` to `async def http_client(stats_test_db)`, adding an explicit pytest fixture dependency. Added a docstring explaining the dependency. This ensures pytest always initializes Beanie via `stats_test_db` before the ASGI client is created, eliminating the order-dependent coupling. Side effect: `test_stats_route_requires_auth` now also requires MongoDB (it will skip if unavailable), which is acceptable since both route tests share the same infrastructure precondition.

## Skipped Issues

None — all findings were fixed.

---

_Fixed: 2026-04-16T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
