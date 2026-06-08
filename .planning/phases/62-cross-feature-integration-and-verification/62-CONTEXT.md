# Phase 62: Cross-Feature Integration and Verification - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Finish the v3.1 per-user QSO collection split for features outside direct QSO CRUD. This phase covers stats, admin clear-log, live feed/SSE, backup/restore verification, and broad isolation/regression coverage across dynamic `<username>_qsos` collections.

Phase 62 must preserve existing external behavior while replacing remaining shared `qsos` assumptions with username-derived collection routing where needed.

</domain>

<decisions>
## Implementation Decisions

### Live Feed Strategy
- **D-01:** Use app-level live feed broadcasts from QSO write paths instead of watching every dynamic per-user collection with MongoDB change streams.
- **D-02:** Phase 62 only needs to preserve live updates for app-created QSOs through supported write paths. Manual database inserts, restore operations, and migration/backfill events do not need to generate live feed broadcasts.
- **D-03:** Reuse the existing SSE `ConnectionManager` and feed row template where practical so `/feed/station`, LIVE/OFFLINE state, and Log View auto-refresh/new-QSO badge behavior remain unchanged.

### Backup and Restore Scope
- **D-04:** Backup/restore should remain full-database scoped: include all collections in the configured MongoDB database, including every dynamic `<username>_qsos` collection.
- **D-05:** Do not narrow backup/restore to user-enumerated collections or `*_qsos` pattern-only logic. Full database disaster recovery is safer and matches the current backup model.
- **D-06:** Phase 62 should add/adjust tests to prove dynamically named QSO collections are included and restored with BSON types preserved.

### Admin and Stats Routing
- **D-07:** Add small shared service/helper APIs for cross-feature per-user reads/deletes rather than wiring each route directly or creating a broad repository layer.
- **D-08:** Stats should aggregate from the logged-in user's `<username>_qsos` collection while keeping `/log/stats` UI context and chart data shape unchanged.
- **D-09:** Admin clear-log should count and delete from the target user's `<username>_qsos` collection while preserving the existing security rule: verify the admin's own password, never the target user's password.

### Verification Depth
- **D-10:** Use layered verification: fake/unit tests for collection-aware helpers and broadcast plumbing, existing route tests adapted where practical, and a smaller live-Mongo integration suite for the highest-risk paths.
- **D-11:** Highest-risk live-Mongo paths are stats, admin clear-log, backup/restore dynamic collection inclusion, and cross-user isolation by guessed IDs or usernames.
- **D-12:** Mongo-dependent tests should skip cleanly when local MongoDB is unavailable; core logic should remain testable without live MongoDB.

### the agent's Discretion
- Choose exact helper names and module placement consistent with existing `app/qso/service.py`, `app/qso/collections.py`, and feature service modules.
- Decide whether live feed broadcast helper lives in `app/feed/manager.py`, a new feed service module, or a small QSO service integration point.
- Decide the smallest test set that proves requirements without converting every legacy Mongo-backed test in the suite.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Requirements and State
- `.planning/REQUIREMENTS.md` — v3.1 requirements, especially INT-01..05 and VERIFY-03..04.
- `.planning/ROADMAP.md` — Phase 62 scope, success criteria, and milestone boundary.
- `.planning/STATE.md` — current milestone progress and prior phase decisions.
- `.planning/PROJECT.md` — project purpose, current milestone target features, and behavior-preservation goal.

### Prior Per-User Collection Phases
- `.planning/phases/59-collection-routing-foundation/59-CONTEXT.md` — collection naming/access decisions.
- `.planning/phases/59-collection-routing-foundation/59-01-SUMMARY.md` — implemented collection helpers and index setup.
- `.planning/phases/60-shared-collection-migration/60-CONTEXT.md` — migration ownership and preservation decisions.
- `.planning/phases/60-shared-collection-migration/60-01-SUMMARY.md` — migration behavior and startup integration.
- `.planning/phases/61-qso-workflow-refactor/61-CONTEXT.md` — direct workflow routing decisions and Phase 62 deferrals.
- `.planning/phases/61-qso-workflow-refactor/61-01-SUMMARY.md` — current collection-aware service/router implementation.
- `.planning/phases/61-qso-workflow-refactor/61-VERIFICATION.md` — Phase 61 verification commands, skips, and source review notes.
- `.planning/phases/61-qso-workflow-refactor/61-UAT.md` — accepted Phase 61 behavior and no-gap UAT result.

### Code Anchors
- `app/qso/collections.py` — username-derived collection access and index helpers.
- `app/qso/service.py` — collection-aware QSO service primitives and clear-log fallback.
- `app/stats/service.py` — current stats aggregation still uses `QSO.get_pymongo_collection()`.
- `app/stats/router.py` — `/log/stats` route currently passes callsign to stats service.
- `app/admin/ui_router.py` — admin clear-log currently counts/deletes through shared `QSO.find`/`clear_operator_log`.
- `app/feed/manager.py` — existing SSE connection manager and single-collection change stream watcher.
- `app/main.py` — startup currently starts watcher from `QSO.get_pymongo_collection()` and backup scheduler.
- `app/backup/dump.py` — current full-database backup writes all Mongo collections.
- `app/backup/restore.py` — current restore reads all collections present in backup records and restores BSON via `bson.json_util`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `get_user_qso_collection(user_or_username)` in `app/qso/collections.py`: existing safe entry point for username-derived QSO collections.
- `clear_operator_log(operator, collection=None)` in `app/qso/service.py`: already accepts a collection override from Phase 61 and can support admin target-user deletion.
- `qso_from_mongo_doc(...)` and raw collection helpers in `app/qso/service.py`: useful for test fixtures, feed rendering, and compatibility helpers.
- `ConnectionManager.broadcast(...)` in `app/feed/manager.py`: reusable for app-level live feed broadcasts without MongoDB change streams.
- Backup/restore full collection iteration in `app/backup/dump.py` and `app/backup/restore.py`: likely already supports dynamic collections, but needs tests.

### Established Patterns
- Route handlers should resolve authenticated/target `User` objects, then derive storage from `User.username`.
- QSO documents keep `_operator` as callsign for display/ADIF/history even when physical collection routing is username-based.
- HTMX error fragments return HTTP 200.
- Mongo-backed integration tests should skip cleanly when MongoDB is unavailable in the local environment.
- Full database backup/restore is the existing disaster-recovery contract.

### Integration Points
- Stats: `app/stats/router.py` and `app/stats/service.py`.
- Admin clear-log: `app/admin/ui_router.py`, `templates/admin/clear_log_modal.html`, and `templates/admin/clear_log_success.html`.
- Live feed: QSO insert paths from REST, UI, ADIF import/review, UDP, and ACLog plus `app/feed/router.py`/`app/feed/manager.py`.
- Startup: `app/main.py` should no longer depend on a single shared `qsos` collection watcher if write-path broadcasts replace change stream watching.
- Backup/restore: route handlers call `run_backup()`/`run_restore()`; service behavior should stay full database scoped.

</code_context>

<specifics>
## Specific Ideas

- Prefer app-level live feed broadcast after successful QSO insertion in supported app write paths.
- Preserve current backup/restore semantics: all configured-database collections, not only current users or matching patterns.
- Use small shared helpers for stats/admin rather than a broad repository abstraction.
- Use layered tests: fake/unit coverage where possible, route tests where practical, live-Mongo only for highest-risk integration behavior.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 62 scope.

</deferred>

---

*Phase: 62-cross-feature-integration-and-verification*
*Context gathered: 2026-06-08*
