# Phase 60: Shared Collection Migration - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the migration/backfill layer that copies existing documents from the legacy shared `qsos` collection into username-derived per-user collections named `<username>_qsos`. This phase must preserve existing operator-facing behavior by copying data only; it must not delete or rename the shared collection and must not refactor REST, UI, ADIF, UDP, stats, live feed, admin, backup, or restore workflows.

</domain>

<decisions>
## Implementation Decisions

### Source And Target
- **D-01:** The migration source is the existing shared MongoDB collection named `qsos`.
- **D-02:** The migration target is the dynamic collection from Phase 59, derived from `User.username` through `app.qso.collections.qso_collection_name(...)`.
- **D-03:** Migration resolves legacy QSO documents by `_operator` callsign to a user account. `User.username` remains the target collection authority.
- **D-04:** The migration copies documents and leaves the source `qsos` collection intact.

### Resolution Safety
- **D-05:** A legacy QSO whose `_operator` does not match exactly one user must not be migrated silently.
- **D-06:** Missing, blank, unknown, or duplicate/ambiguous callsign mappings are reported.
- **D-07:** Existing `User.callsign` is not unique at the model/index level, so duplicate callsign matches must be treated as ambiguous rather than guessed.
- **D-08:** Callsign lookup should normalize consistently enough to handle existing uppercase expectations, but the copied document's `_operator` field must remain unchanged.

### Idempotence And Preservation
- **D-09:** Migration must be safe to rerun repeatedly.
- **D-10:** If a target collection already contains the same `_id`, migration must skip that document rather than overwrite target-side changes.
- **D-11:** The copied document must preserve `_id` where feasible, `_operator`, `_deleted`, `_created_at`, `rowHash`, declared ADIF fields, model extras, profile-stamped fields, and custom fields.
- **D-12:** Target per-user indexes must exist before target writes rely on `rowHash` uniqueness.

### Startup And CLI
- **D-13:** Provide a callable migration function and a CLI entry point so operators can run/report migration explicitly.
- **D-14:** Startup integration may call the idempotent migration after source backfills/index creation and before later dynamic workflows depend on target collections.
- **D-15:** Startup logging must summarize counts and unresolved/ambiguous operators without requiring interactive input.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before implementing.**

- `.planning/REQUIREMENTS.md` — MIGR-01..05 and VERIFY-02 are Phase 60 scope.
- `.planning/phases/59-collection-routing-foundation/59-01-SUMMARY.md` — dynamic helper foundation from Phase 59.
- `app/qso/collections.py` — collection naming, raw collection access, and per-user index setup helpers.
- `app/database.py` — existing application MongoDB client lifecycle.
- `app/main.py` — current startup migration order and lifespan wiring.
- `app/qso/models.py` — legacy shared `qsos` Beanie document and field aliases.
- `app/qso/row_hash_migration.py` — existing rowHash report/index/backfill style.
- `app/auth/models.py` — `User.username` and `User.callsign` fields.
- `tests/test_qso_collections.py` — Phase 59 helper test style.
- `tests/test_migration.py` and `tests/test_qso_schema.py` — existing migration/schema verification style.

</canonical_refs>

<code_context>
## Existing Code Insights

- `app/main.py` currently runs `backfill_created_at()`, `normalize_time_on()`, and `backfill_row_hash()` against the shared `qsos` collection at startup.
- `QSO.Settings.name` remains `qsos`, so existing runtime behavior still reads/writes the shared collection until Phase 61.
- `app.qso.collections.ensure_user_qso_indexes(...)` can create target collection indexes before migration writes.
- `User.Settings.indexes` only enforces unique username; callsign ambiguity is possible and must be handled explicitly.
- Existing tests often use focused fake objects or Mongo-skipping fixtures, so Phase 60 tests can mix pure fake-collection tests with optional live Mongo checks if useful.

</code_context>

<deferred>
## Deferred To Later Phases

- Refactor QSO CRUD/import/export/API-token/UDP paths to write dynamic collections — Phase 61.
- Stats, admin clear-log, live feed/SSE, and backup/restore integration — Phase 62.
- Dropping, archiving, or renaming the legacy shared `qsos` collection — out of scope for v3.1 unless explicitly planned later.

</deferred>

---

*Phase: 60-shared-collection-migration*
*Context gathered: 2026-06-07*

