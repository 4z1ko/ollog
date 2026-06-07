# Phase 61 Research: QSO Workflow Refactor

**Date:** 2026-06-07
**Phase:** 61 - QSO Workflow Refactor
**Status:** Complete

## Current State

Phase 59 introduced safe per-user collection helpers. Phase 60 copies legacy shared `qsos` data into `<username>_qsos`. Runtime QSO workflows still mostly use the Beanie `QSO` document bound to the shared `qsos` collection.

The current service layer is the central risk point:

- `insert_qso_dict()` constructs `QSO` and calls `.insert()`.
- `find_duplicate()` uses `QSO.find_one(...)`.
- `import_qsos_from_bytes()` calls duplicate and insert helpers.
- `get_qso_page()` uses `QSO.find(...)`.
- `clear_operator_log()` uses `QSO.find(...).delete_many()`.

Routers and background flows call those helpers, so moving the service boundary first should reduce duplicated raw MongoDB logic.

## Recommended Architecture

Add raw collection-aware service helpers while preserving `QSO` as the Pydantic/Beanie-shaped document object used by serializers and templates.

Useful helper concepts:

- `qso_from_mongo_doc(doc) -> QSO`
- `qso_to_mongo_doc(qso_dict) -> dict`
- collection-aware `insert_qso_dict(..., collection)`
- collection-aware `find_duplicate(..., collection)`
- collection-aware `get_qso_page(..., collection)`
- collection-aware `get_qso_by_id(..., collection)`
- collection-aware `update_qso(...)` and `soft_delete_qso(...)`

The route/service public behavior should stay stable; only the storage target changes.

## API/Ownership Strategy

REST:

- Use `get_current_user_jwt_or_apikey` for list/get/create/patch/delete.
- Derive collection from `user.username`.
- Continue stamping `_operator` from `user.callsign`.

Browser UI:

- Prefer `get_current_user_cookie` for QSO storage routes.
- Preserve existing template contexts and HTMX 200 error fragment behavior.
- Move entry, log view, inline edit/delete, import/export, duplicate review, custom defaults, and operator clear-log to the user's collection.

ADIF:

- REST import/export should use authenticated `User`.
- Browser import/export should use cookie-authenticated `User`.
- Duplicate review force-import must insert into the same user's collection.

UDP:

- Token and OPERATOR paths already resolve to users.
- Fallback `UDP_OPERATOR` must resolve to a `User`; if not resolvable, reject/log instead of writing to a callsign-only shared path.

## Verification Strategy

Use focused tests that can run without broad full-suite fragility:

- pure/fake collection unit tests for service helpers and rowHash behavior
- route-level tests or existing integration tests adjusted to assert per-user collection isolation
- API-key test proving token owner's username-derived collection is used
- UDP tests proving token/fallback user routing passes a user-aware insert path
- ADIF import/export tests proving only the user's collection is read/written

Some legacy Mongo-backed tests may still skip when MongoDB is unavailable. Phase 61 should include enough fake/unit coverage to keep verification meaningful without live MongoDB.

