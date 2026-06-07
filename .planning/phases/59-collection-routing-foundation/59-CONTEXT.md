# Phase 59: Collection Routing Foundation - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Create the shared foundation for per-user QSO collections: derive collection names from `User.username`, provide safe access to each user's raw MongoDB QSO collection, initialize required indexes on those dynamic collections, and add focused tests around the helper/access boundary. This phase does not migrate existing data or refactor every QSO workflow; those are explicitly assigned to later phases.

</domain>

<decisions>
## Implementation Decisions

### Collection Naming
- **D-01:** The physical QSO collection name is derived from `User.username`, not callsign.
- **D-02:** The collection name format is exactly `<username>_qsos`; `john_doe` must produce `john_doe_qsos`.
- **D-03:** Valid existing username strings should remain unchanged in collection names. The helper may reject unsafe usernames rather than silently rewriting them in ways that make the name no longer match the requirement.
- **D-04:** Collection-name derivation must live in one shared helper so REST, UI, UDP, migration, stats, admin, and backup code cannot drift.

### QSO Model Boundary
- **D-05:** The existing `QSO` model remains the validation/serialization shape for QSO documents in this phase, but per-user CRUD should not depend on `QSO.Settings.name = "qsos"`.
- **D-06:** Phase 59 should introduce a raw collection/access boundary around `AsyncMongoClient[settings.mongodb_db][collection_name]`; full call-site migration is deferred to Phases 60–62.
- **D-07:** The `_operator` callsign field remains in QSO documents even after routing by username, because ADIF export/import, display, profile stamping, and historical semantics still depend on it.

### Indexes
- **D-08:** Each per-user collection must receive the indexes needed for current behavior, including active/deleted filtering, sort fields, created-at sort, duplicate lookup fields, and rowHash uniqueness.
- **D-09:** Index setup must be idempotent so it is safe during startup, migration, and first-use collection creation.
- **D-10:** Since physical isolation is already per user, indexes may drop `_operator` from leading keys when appropriate, but compatibility with existing query shapes and future migration phases matters more than aggressive index minimization.

### Phase Split
- **D-11:** Existing shared `qsos` migration belongs to Phase 60, not Phase 59.
- **D-12:** REST/UI/ADIF/API-token/UDP service refactoring belongs to Phase 61, not Phase 59.
- **D-13:** Stats, admin clear-log, live feed/SSE, backup/restore, and broad integration verification belong to Phase 62, not Phase 59.

### the agent's Discretion
- Choose module names and function signatures that fit the existing app layout, likely under `app/qso/`.
- Decide whether to expose helpers taking `User`, `username`, or both, provided `User.username` is the canonical source for runtime collection routing.
- Decide whether tests are purely unit-level or use lightweight mocked async collections for index assertions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Scope
- `.planning/PROJECT.md` — v3.1 goal and active requirements.
- `.planning/REQUIREMENTS.md` — COLL-01..05 and VERIFY-01 are Phase 59 scope; later requirements are dependency context only.
- `.planning/ROADMAP.md` — Phase 59 boundary and later phase split.
- `.planning/STATE.md` — current milestone state and carried-forward build rules.

### Existing Database And QSO Model
- `app/database.py` — initializes MongoDB and Beanie models with fixed `QSO` document registration.
- `app/qso/models.py` — current `QSO` Beanie document, fixed `Settings.name = "qsos"`, aliases, rowHash update hooks, and index definitions.
- `app/qso/service.py` — current service functions that use `QSO.find()`, `QSO.find_one()`, and `QSO` construction.
- `app/qso/row_hash_migration.py` — existing rowHash index/backfill pattern on the fixed shared collection.
- `app/main.py` — startup migrations and current live feed watcher collection binding.

### Future Integration Points
- `app/qso/router.py` — REST QSO CRUD currently scoped by operator callsign.
- `app/qso/ui_router.py` — browser QSO entry, Log View, import/export review, inline edit/delete, clear-log count.
- `app/stats/service.py` — stats aggregation currently uses `QSO.get_pymongo_collection()`.
- `app/admin/ui_router.py` — admin clear-log count/delete currently uses `QSO.find()`.
- `app/feed/manager.py` — live watcher currently watches one collection.
- `app/backup/` — backup/restore must eventually include dynamic QSO collections.

### Tests
- `tests/test_qso_schema.py` — current assertions around `QSO.Settings.name`, indexes, aliases, and rowHash behavior.
- `tests/test_service_sort.py` — sort allowlist expectations that Phase 59 index planning must preserve.
- `tests/test_custom_qso_fields.py` and `tests/test_view_dict.py` — examples of focused non-Mongo tests for QSO helpers.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app.database.get_client()` exposes the active `AsyncMongoClient`; a dynamic collection helper can use it without creating a second client.
- `QSO.model_validate()` / `QSO(**doc)` can continue to validate raw documents even if storage moves to raw per-user collections.
- Existing `QSO.Settings.indexes` captures most index intent and can be reused or translated for dynamic collection setup.
- `canonical_document_hash()` and `QSO.refresh_row_hash()` already define rowHash semantics.

### Established Patterns
- Startup migrations are idempotent and live near `app/main.py` or dedicated helper modules.
- Tests often skip live MongoDB-dependent cases and keep pure helper tests fast.
- Existing code relies heavily on raw MongoDB alias names such as `_operator`, `_deleted`, `_created_at`, and `rowHash`.
- Public behavior should remain unchanged; storage routing is the private refactor.

### Integration Points
- Phase 59 should create the helper/access boundary that later phases pass through.
- Later phases will need call sites to pass either the authenticated `User` or a resolved username alongside callsign/operator data.
- Any helper that needs settings or MongoDB client access should fail clearly if called before `init_db()`.

</code_context>

<specifics>
## Specific Ideas

- Candidate helper names: `qso_collection_name(username)`, `get_user_qso_collection(user_or_username)`, `ensure_user_qso_indexes(...)`.
- A narrow `app/qso/collections.py` module would keep collection routing separate from business rules in `service.py`.
- Tests should prove `john_doe` maps to `john_doe_qsos` exactly.

</specifics>

<deferred>
## Deferred Ideas

- Migration from `qsos` to per-user collections — Phase 60.
- Refactor REST/UI/ADIF/API-token/UDP CRUD paths — Phase 61.
- Stats/admin/live-feed/backup/restore integration — Phase 62.
- Username rename support and migration-status admin UI — v2/future requirements.

</deferred>

---

*Phase: 59-collection-routing-foundation*
*Context gathered: 2026-06-07*
