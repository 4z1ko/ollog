# Phase 52: TIME_ON DB Migration - Context

**Gathered:** 2026-04-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Backend-only startup migration: pad all existing 4-digit HHMM `TIME_ON` values in the `qsos` MongoDB collection to HHMM00 (6 digits). Also confirm server-side validation already accepts both HHMM and HHMMSS formats (DB-02 — no new code needed, covered by existing `parse_adif_datetime()`).

No frontend changes. No new dependencies.

</domain>

<decisions>
## Implementation Decisions

### Migration mechanism
- **D-01:** Use a single `update_many` call with a MongoDB aggregation pipeline — no cursor iteration, no Python-side loop.
  - Filter: `{"TIME_ON": {"$regex": r"^\d{4}$"}}` — anchored regex matches exactly 4-digit strings, preventing double-padding.
  - Update: aggregation pipeline `[{"$set": {"TIME_ON": {"$concat": ["$TIME_ON", "00"]}}}]`
  - This departs from the `backfill_created_at` cursor pattern but is simpler and maps directly to the STATE.md research recommendation.
- **D-02:** Function named `normalize_time_on()`, placed in `app/main.py`, called in the `lifespan` function immediately after `backfill_created_at()`.
- **D-03:** No `_operator` filter — this is an admin-level startup migration operating across all operators' records.

### Logging
- **D-04:** Follow `backfill_created_at` logging style: log count with two branches.
  - When records updated: `logger.info("TIME_ON migration: %d documents updated", result.modified_count)`
  - When nothing to do: `logger.info("TIME_ON migration: 0 documents — already up to date")`

### DB-02 disposition
- **D-05:** `parse_adif_datetime()` in `app/qso/service.py` already accepts both HHMM (4-digit) and HHMMSS (6-digit) — no new code needed. Write a test in `tests/test_migration.py` that explicitly asserts both formats are accepted via the service layer, making DB-02 verifiably green rather than assumed.

### Test coverage
- **D-06:** Integration test hitting real MongoDB (consistent with existing test suite style — requires MongoDB on localhost:27017).
- **D-07:** Test file: `tests/test_migration.py` (new file, groups startup migration tests; if `backfill_created_at` ever gets a test it belongs here too).
- **D-08:** Test cases:
  1. Insert QSO docs with 4-digit `TIME_ON` values, run `normalize_time_on()`, assert all values are now 6-digit HHMM00.
  2. Run `normalize_time_on()` a second time on the same data — assert no additional changes (idempotency).
  3. Assert `parse_adif_datetime()` accepts `"1430"` (HHMM) and `"143000"` (HHMMSS) without raising (DB-02 confirmation).

### Claude's Discretion
- Exact pymongo async API calls (e.g., whether `update_many` with aggregation pipeline uses `Motor` async client or raw pymongo — use whichever the existing `backfill_created_at` collection handle gives access to).
- Whether to call `get_pymongo_collection()` (as `backfill_created_at` does) or use the Motor client directly. Either is fine — follow what's simpler given the aggregation pipeline call.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §DB — DB-01 and DB-02 requirements with exact acceptance criteria

### Existing migration pattern
- `app/main.py` — `backfill_created_at()` function (lines 22–47): the established idempotent startup migration pattern; logging style, pymongo collection access, and lifespan call site

### DB-02 confirmation target
- `app/qso/service.py` — `parse_adif_datetime()` (lines 29–44): already accepts both HHMM (len==4) and HHMMSS (len==6); this is where DB-02 is satisfied

### Existing test style reference
- `tests/` — all tests require real MongoDB on localhost:27017; no mocking pattern exists in this codebase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backfill_created_at()` in `app/main.py:22-47`: exact pattern for idempotent startup migrations — use as structural template (but switch cursor+bulk_write to single update_many+aggregation pipeline per D-01)
- `QSO.get_pymongo_collection()` — access pattern for raw pymongo collection used by existing migration

### Established Patterns
- Lifespan startup order: `init_db()` → `_bootstrap_admin()` → `backfill_created_at()` → watcher/UDP/backup. New `normalize_time_on()` call goes immediately after `backfill_created_at()`.
- `logger = logging.getLogger(__name__)` — module-level logger already present in `app/main.py`

### Integration Points
- `app/main.py` `lifespan()` function (line 51) — the only place to add the migration call
- `app/qso/service.py` `parse_adif_datetime()` — no changes needed; test targets this function directly

</code_context>

<specifics>
## Specific Ideas

- STATE.md research explicitly called out the aggregation pipeline approach to prevent double-padding: `[{$set: {TIME_ON: {$concat: ["$TIME_ON", "00"]}}}]` with anchored regex `^\d{4}$`. Use exactly this.
- "readonly not disabled" and FOUC prevention are Phase 53 concerns — out of scope for Phase 52.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 52-time-on-db-migration*
*Context gathered: 2026-04-26*
