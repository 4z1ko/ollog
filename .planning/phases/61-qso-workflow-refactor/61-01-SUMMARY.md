# Phase 61 Execution Summary: Dynamic QSO Workflow Collection Routing

**Completed:** 2026-06-08
**Plan:** 61-01 Dynamic QSO Workflow Collection Routing
**Status:** Implementation complete, ready for UAT

## What Changed

- Added collection-aware QSO service primitives in `app/qso/service.py` for raw per-user collection insert, duplicate lookup, pagination, update, soft-delete, clear-log, and raw MongoDB document hydration.
- Routed REST QSO CRUD in `app/qso/router.py` through `get_current_user_jwt_or_apikey` and `get_user_qso_collection(user)`, preserving existing response schemas, status codes, protected-field stripping, and duplicate conflict payloads.
- Routed browser QSO workflows in `app/qso/ui_router.py` through the logged-in user's collection, including entry, log view, inline edit/view/update/delete, ADIF import/export, duplicate review import, custom-field defaults, and operator clear-log.
- Routed REST ADIF import/export in `app/adif/router.py` through the authenticated user's collection.
- Routed UDP and ACLog ingestion paths to pass the resolved user's collection into the shared ingestion service while retaining test fallback behavior when the app database client is not initialized.
- Updated custom QSO default lookup in `app/qso/custom_fields.py` so "last QSO" defaults can query the user's per-user collection.
- Added `tests/test_qso_service_collections.py` to exercise raw collection behavior without requiring live MongoDB.
- Updated UDP and clear-log tests to reflect username-derived collection routing.

## Behavior Preserved

- `_operator` remains stored as the callsign in every QSO document.
- Public REST paths, browser routes, templates, HTMX fragments, ADIF stream format, duplicate review reports, and API-token auth behavior are unchanged.
- Duplicate detection and `rowHash` duplicate recovery now operate within the same user collection.
- The shared legacy `qsos` path remains available as a service fallback for existing tests/backward-compatible helpers and for Phase 62-owned features not yet refactored.

## Deferred To Phase 62

- Stats aggregation
- Admin clear-log
- Live feed/SSE watcher
- Backup/restore dynamic collection coverage
- Broad cross-feature isolation/security regression suite

## Notes

- Mongo-backed integration tests skip cleanly in this sandbox because local MongoDB is unavailable.
- Phase 61 direct QSO workflow routing is implemented and ready for `/gsd-verify-work phase 61`.
