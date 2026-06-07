# Phase 61: QSO Workflow Refactor - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Refactor direct QSO workflows so runtime reads and writes target the authenticated user's per-user collection named `<username>_qsos`. Preserve public API contracts, browser behavior, ADIF reports/exports, duplicate handling, rowHash behavior, and UDP/API-token ownership semantics.

This phase covers direct QSO CRUD/logging workflows. Cross-feature integrations such as stats, admin clear-log, live feed/SSE, and backup/restore remain Phase 62 unless needed as a helper dependency.

</domain>

<decisions>
## Implementation Decisions

### Routing Source
- **D-01:** Collection routing uses the authenticated or resolved `User.username`, not callsign.
- **D-02:** `_operator` remains in every QSO document and continues to store the callsign for ADIF/display/history.
- **D-03:** REST JWT/API-key routes should depend on `User`, not callsign-only wrappers, when choosing a collection.
- **D-04:** Browser routes should depend on `get_current_user_cookie` where they need QSO storage access.
- **D-05:** UDP routes must write to the resolved `User` from `APP_OLLOG_TOKEN`, resolved OPERATOR, or configured fallback user. A callsign-only fallback is not enough for per-user collection routing.

### Storage Boundary
- **D-06:** Direct CRUD must stop using Beanie's fixed `QSO.Settings.name = "qsos"` storage path.
- **D-07:** The `QSO` model remains the validation/serialization shape and view/API response object.
- **D-08:** Add service-layer raw MongoDB helpers that read/write per-user collections and hydrate raw documents into `QSO` instances.
- **D-09:** Duplicate checks and `rowHash` uniqueness are scoped to the user's collection.
- **D-10:** Existing public schemas, route paths, template contexts, and HTMX response behavior must remain unchanged.

### Phase Split
- **D-11:** REST API, browser QSO entry/log view/edit/delete/import/export/duplicate review, API-token QSO access, UDP ingestion, custom QSO default lookup, and operator clear-log are Phase 61.
- **D-12:** Stats, admin clear-log, live feed/SSE, backup/restore, and broad isolation verification are Phase 62.
- **D-13:** The legacy shared `qsos` collection should remain available until later cleanup; Phase 61 should not drop it.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before implementing.**

- `.planning/REQUIREMENTS.md` — QSO-01..06 and COLL-05 are Phase 61 scope.
- `.planning/phases/59-collection-routing-foundation/59-01-SUMMARY.md` — per-user collection helper foundation.
- `.planning/phases/60-shared-collection-migration/60-01-SUMMARY.md` — migrated data exists in per-user collections.
- `app/qso/collections.py` — collection naming/access/index helpers.
- `app/qso/models.py` — QSO validation/serialization shape and rowHash hooks.
- `app/qso/service.py` — current service boundary for insert, duplicate, import, pagination, and clear-log.
- `app/qso/router.py` — REST QSO CRUD and API-token support.
- `app/qso/ui_router.py` — browser QSO entry, log view, inline edit/delete, import/export, duplicate review, and clear-log.
- `app/adif/router.py` — REST ADIF import/export.
- `app/qso/custom_fields.py` — previous-QSO custom default lookups.
- `app/udp/server.py` — UDP QSO ingestion.
- `app/auth/dependencies.py` — JWT/cookie/API-key dependencies returning `User`.
- `tests/test_qso_collections.py`, `tests/test_qso_collection_migration.py` — current per-user collection tests.
- Existing workflow tests: `tests/test_qso_api.py`, `tests/test_qso_api_key.py`, `tests/test_adif_import.py`, `tests/test_adif_export.py`, `tests/test_duplicate_detection.py`, `tests/test_udp_token.py`, `tests/test_udp_pipeline.py`, `tests/test_clear_log.py`, `tests/test_custom_qso_fields.py`.

</canonical_refs>

<code_context>
## Existing Code Insights

- `app/qso/service.py` currently constructs `QSO` instances and calls Beanie `.insert()`, `QSO.find_one()`, `QSO.find()`, and `.delete_many()` against the fixed shared `qsos` collection.
- REST create already has full `User`; list/get/delete still use callsign-only dependencies.
- UI entry/log routes often have `User`, but import/export/delete/clear paths still use callsign-only dependencies.
- API-key ownership resolves to `User` in `get_current_user_jwt_or_apikey`; Phase 61 should use that user directly for collection routing.
- UDP `_handle_datagram()` resolves token/operator values to `User` in successful paths, but the fallback path can still have only an operator string if no configured user was loaded.
- `custom_field_defaults()` reads prior QSOs through `QSO.find()` and must move with the browser QSO workflow.
- `QSO` hydration from raw MongoDB docs should preserve aliases and extras so existing serializers/template helpers keep working.

</code_context>

<deferred>
## Deferred To Phase 62

- Stats aggregation from dynamic collections.
- Admin clear-log against a target user's collection.
- Live feed/SSE across dynamic collections.
- Backup/restore inclusion of dynamic QSO collections.
- Broad cross-feature isolation/security tests beyond representative direct QSO workflow tests.

</deferred>

---

*Phase: 61-qso-workflow-refactor*
*Context gathered: 2026-06-07*

