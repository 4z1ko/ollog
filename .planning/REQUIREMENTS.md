# Requirements: ollog v3.1 Per-User QSO Collections

**Defined:** 2026-06-07
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss — now with physical per-user QSO collection isolation.

## v1 Requirements

### Collection Naming And Routing

- [x] **COLL-01:** Every user has a dedicated MongoDB QSO collection named exactly `<username>_qsos`, where `<username>` is `User.username`.
- [x] **COLL-02:** Collection names are derived through one shared helper that validates/sanitizes usernames for MongoDB collection safety without changing valid usernames such as `john_doe`.
- [x] **COLL-03:** QSO collection access does not rely on Beanie's fixed `QSO.Settings.name = "qsos"` for per-user CRUD paths.
- [x] **COLL-04:** Per-user collections receive the indexes required for existing behavior, including date/sort indexes and rowHash uniqueness within each user collection.
- [x] **COLL-05:** The `_operator`/callsign field remains present in QSO documents for ADIF compatibility, display, and historical semantics, even though physical collection routing is username-based.

### Data Migration

- [x] **MIGR-01:** Existing documents from the shared `qsos` collection are copied into the correct `<username>_qsos` collection by resolving each document's `_operator` callsign to a `User.username`.
- [x] **MIGR-02:** The migration is idempotent and can safely rerun without duplicating migrated QSOs or overwriting newer per-user data.
- [x] **MIGR-03:** Documents whose `_operator` cannot be resolved to a user are not silently discarded; they are logged and reported for operator review.
- [x] **MIGR-04:** Existing `rowHash`, `_created_at`, `_deleted`, ADIF extras, profile-stamped fields, and custom QSO fields are preserved byte-for-byte where possible.
- [x] **MIGR-05:** Startup/backfill ordering ensures per-user collection indexes exist before migrated or newly inserted QSOs depend on them.

### QSO Workflows

- [ ] **QSO-01:** REST QSO list/create/read/update/delete routes dynamically target the authenticated user's `<username>_qsos` collection while keeping request/response schemas unchanged.
- [ ] **QSO-02:** Browser QSO entry, Log View pagination/filtering/sorting, inline edit, delete, and clear-log workflows dynamically target the logged-in user's collection.
- [ ] **QSO-03:** ADIF import/export and duplicate review use the user's collection for duplicate checks, inserts, selectable existing-QSO review rows, and exported data.
- [ ] **QSO-04:** Duplicate detection and rowHash uniqueness remain scoped to the user's own QSO collection.
- [ ] **QSO-05:** API-token authenticated requests route to the token owner's username-derived collection.
- [ ] **QSO-06:** UDP logging resolves the destination user from `APP_OLLOG_TOKEN` or `UDP_OPERATOR`, then writes to that user's username-derived collection.

### Cross-Feature Integration

- [ ] **INT-01:** Operator stats aggregate from the logged-in user's QSO collection without changing the `/log/stats` UI.
- [ ] **INT-02:** Admin clear-log counts and deletes from the target user's QSO collection while continuing to verify the admin's own password.
- [ ] **INT-03:** Live feed/SSE behavior still announces new QSOs and preserves existing auto-refresh/new-QSO badge behavior after the physical collection split.
- [ ] **INT-04:** Backup and restore continue to include all QSO data collections, including dynamically named `<username>_qsos` collections.
- [ ] **INT-05:** Existing security boundaries remain intact: one operator cannot read, edit, delete, export, import-review, or clear another operator's QSOs by guessing IDs or collection names.

### Verification

- [x] **VERIFY-01:** Unit tests cover collection-name derivation, invalid username handling, per-user collection helper behavior, and index setup.
- [x] **VERIFY-02:** Migration tests cover normal migration, idempotent reruns, unresolved operators, soft-deleted rows, rowHash preservation, and ADIF extras.
- [ ] **VERIFY-03:** Integration tests cover representative REST, browser/service, ADIF import/export, stats, admin clear-log, API-token, and UDP paths against per-user collections.
- [ ] **VERIFY-04:** Regression tests prove existing API schemas, UI template contexts, duplicate handling, sorting, filtering, pagination, and live-update sentinels remain compatible.

## v2 Requirements

### Future Hardening

- **UCOLL-FUTURE-01:** Optional admin UI to inspect migration status and unresolved legacy operators.
- **UCOLL-FUTURE-02:** Optional support for username renames with explicit collection rename/relink tooling.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Changing public API routes or response schemas | This milestone is a storage refactor; external behavior must remain unchanged. |
| Removing `_operator` from QSO documents | ADIF/profile/display semantics still depend on callsign data. |
| User-controlled collection names | Requirement fixes the convention to `<username>_qsos`. |
| Cross-database tenancy | This milestone uses per-user collections in the existing MongoDB database. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| COLL-01 | Phase 59 | Complete |
| COLL-02 | Phase 59 | Complete |
| COLL-03 | Phase 59 | Complete |
| COLL-04 | Phase 59 | Complete |
| COLL-05 | Phase 59 | Complete |
| MIGR-01 | Phase 60 | Complete |
| MIGR-02 | Phase 60 | Complete |
| MIGR-03 | Phase 60 | Complete |
| MIGR-04 | Phase 60 | Complete |
| MIGR-05 | Phase 60 | Complete |
| QSO-01 | Phase 61 | Pending |
| QSO-02 | Phase 61 | Pending |
| QSO-03 | Phase 61 | Pending |
| QSO-04 | Phase 61 | Pending |
| QSO-05 | Phase 61 | Pending |
| QSO-06 | Phase 61 | Pending |
| INT-01 | Phase 62 | Pending |
| INT-02 | Phase 62 | Pending |
| INT-03 | Phase 62 | Pending |
| INT-04 | Phase 62 | Pending |
| INT-05 | Phase 62 | Pending |
| VERIFY-01 | Phase 59 | Complete |
| VERIFY-02 | Phase 60 | Complete |
| VERIFY-03 | Phase 62 | Pending |
| VERIFY-04 | Phase 62 | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2026-06-07*
*Last updated: 2026-06-07 after Phase 60 UAT completion*
