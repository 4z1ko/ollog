# Phase 61 Validation Strategy

**Date:** 2026-06-07
**Phase:** 61 - QSO Workflow Refactor

## Scope Under Test

Phase 61 validates direct QSO workflow routing:

- REST QSO CRUD
- browser QSO entry/log view/edit/delete/clear-log
- ADIF import/export and duplicate review
- API-token QSO access
- UDP QSO ingestion
- duplicate and rowHash behavior scoped to the user's collection
- custom QSO defaults that look at prior QSOs

Stats, admin clear-log, live feed, and backup/restore remain Phase 62.

## Nyquist Sample Points

1. **REST CRUD**
   - Create/list/get/patch/delete use the authenticated user's collection and keep response schemas unchanged.
   - Guessing another user's QSO ID returns not found.

2. **Browser workflows**
   - QSO form insert, log view pagination/filtering/sorting, inline edit/delete, and operator clear-log use the logged-in user's collection.
   - HTMX partial/error behavior stays unchanged.

3. **ADIF**
   - Import duplicate checks and inserts happen in the user's collection.
   - Duplicate review force-import uses the same collection.
   - Export reads only the user's collection.

4. **API-token**
   - `X-API-Key` routes target the token owner's username-derived collection.

5. **UDP**
   - `APP_OLLOG_TOKEN` writes to token owner's collection.
   - OPERATOR override writes to resolved user's collection.
   - UDP fallback writes only when a fallback user exists.

6. **RowHash**
   - Unique rowHash conflicts are scoped to one user collection.
   - Two users can store identical effective QSOs independently.

7. **Compatibility**
   - `QSO` serialization helpers, API response models, template view dicts, custom fields, sorting, filtering, pagination, and duplicate messages remain compatible.

## Verification Commands

```bash
.venv/bin/python -m pytest tests/test_qso_service_collections.py tests/test_qso_collections.py tests/test_qso_collection_migration.py
.venv/bin/python -m pytest tests/test_qso_api.py tests/test_qso_api_key.py tests/test_adif_import.py tests/test_adif_export.py tests/test_duplicate_detection.py tests/test_udp_token.py tests/test_udp_pipeline.py tests/test_clear_log.py tests/test_custom_qso_fields.py
.venv/bin/python -m ruff check app/qso/service.py app/qso/router.py app/qso/ui_router.py app/adif/router.py app/qso/custom_fields.py app/udp/server.py tests/test_qso_service_collections.py
.venv/bin/python -m compileall app/qso app/adif app/udp tests/test_qso_service_collections.py
```

## Acceptance

Phase 61 passes when direct QSO workflows no longer depend on the fixed shared `qsos` collection for runtime CRUD, all ownership is routed through the authenticated/resolved user, and public behavior remains compatible.

