# Phase 62 Research: Cross-Feature Integration and Verification

**Date:** 2026-06-08
**Status:** Complete

## Research Question

What needs to change so the remaining cross-feature QSO paths work correctly after the storage split to per-user `<username>_qsos` collections?

## Findings

### Stats

- `app/stats/service.py` still aggregates with `QSO.get_pymongo_collection()`, which points at the legacy shared `qsos` collection.
- `app/stats/router.py` still depends on `get_current_operator_callsign_cookie` and passes only callsign to `get_stats(callsign)`.
- Phase 62 should move the route to `get_current_user_cookie` and pass the authenticated user or its collection to stats.
- The output shape should remain unchanged: `band_counts`, `mode_counts`, `entity_counts`, `unique_entity_count`, and `total_qsos`.
- Existing tests in `tests/test_stats.py` seed Beanie `QSO` documents into the shared collection and should be adapted to per-user collection seeding.

### Admin Clear Log

- `app/admin/ui_router.py` still counts target QSOs with `QSO.find(...)` and deletes via `clear_operator_log(target_user.callsign)` without a target collection.
- Phase 61 already made `clear_operator_log(operator, collection=None)` collection-aware, so admin clear-log can pass `get_user_qso_collection(target_user)`.
- The important security invariant remains unchanged: verify the admin's own password, never the target user's password.
- Existing `tests/test_admin_clear_log.py` seed and count shared `QSO` documents; they should be adapted to target user's per-user collection and made to skip cleanly when MongoDB is unavailable.

### Live Feed / SSE

- `app/main.py` starts a watcher on `client[settings.mongodb_db]["qsos"]`.
- `app/feed/manager.py` watches a single collection via MongoDB change stream and broadcasts rendered `log/feed_row.html` HTML to all SSE clients.
- Phase 62 decision is app-level broadcasting from successful QSO write paths, not dynamic change streams across user collections.
- Existing insert paths are REST create, browser QSO entry, ADIF import/review selected duplicates, UDP ingestion, and ACLog ingestion. Phase 61 already centralized much of this through `insert_qso_dict(...)`, `ingest_qso_record(...)`, and `import_qsos_from_bytes(...)`.
- A small helper such as `broadcast_qso_insert(qso, templates)` or a callback hook in service insert helpers can preserve existing feed row HTML and avoid duplicating render code.
- Startup should no longer start a watcher on the shared `qsos` collection for live feed.

### Backup / Restore

- `app/backup/dump.py` already iterates `sorted(db.list_collection_names())` and writes every document from every collection.
- `app/backup/restore.py` restores every collection found in the backup records using `bson.json_util.loads`.
- The implementation probably needs little or no production code change. The Phase 62 requirement is to protect the contract with tests covering dynamic `<username>_qsos` collections and BSON preservation.

### Isolation / Regression Tests

- Existing route-level Mongo tests often seed the shared `qsos` collection through Beanie. Phase 62 should only convert tests that cover Phase 62-owned paths plus highest-risk isolation behavior.
- Existing fake-collection tests from Phase 61 prove many direct CRUD behaviors without MongoDB; Phase 62 should use the same style where possible.
- Live-Mongo tests should skip explicitly if MongoDB is unavailable.

## Recommended Plan Shape

Use one plan, `62-01`, with four implementation bands:

1. Shared helper and stats/admin routing.
2. App-level live feed broadcast wiring.
3. Backup/restore dynamic collection tests.
4. Layered verification and milestone traceability cleanup.

## Validation Architecture

The validation strategy should combine:

- Unit/fake tests for stats aggregation against a fake async collection and feed broadcast rendering.
- Adapted Mongo integration tests for stats route, admin clear-log, and backup/restore dynamic collection inclusion.
- Existing direct QSO workflow tests from Phase 61 as regression coverage.
- Source search for remaining Phase-62-owned `QSO.find`, `QSO.get_pymongo_collection`, or shared `qsos` watcher assumptions.

## Risks

- Broadcasting from write paths can miss one route if insertion is not centralized enough. Plan should explicitly enumerate all app write paths.
- Tests using FastAPI app state and templates can become brittle; prefer small feed helper tests plus one route-level smoke where practical.
- Backup/restore tests may need synchronous `MongoClient` availability and should skip when MongoDB is unavailable.

## Research Complete

Phase 62 is ready for planning.
