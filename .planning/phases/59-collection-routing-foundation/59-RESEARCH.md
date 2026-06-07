# Phase 59 Research: Collection Routing Foundation

**Date:** 2026-06-07
**Phase:** 59 - Collection Routing Foundation
**Status:** Complete

## Current Implementation

The application currently registers `QSO` as a Beanie `Document` with `QSO.Settings.name = "qsos"`. Service, router, startup, stats, live-feed, and admin code all ultimately query this fixed shared collection and scope rows with the `_operator` callsign field.

`app/database.py` already exposes the active async MongoDB client through `get_client()`, so Phase 59 can add dynamic collection access without creating another client or changing database initialization semantics.

`app/qso/models.py` remains useful as the QSO validation and serialization shape. Its declared aliases preserve the physical MongoDB fields `_operator`, `_deleted`, `_created_at`, and `rowHash`, and its current indexes define the behavior that dynamic collections need to preserve.

## Relevant Constraints

- Collection names must be exactly `<username>_qsos` for safe usernames; `john_doe` must produce `john_doe_qsos`.
- Runtime routing is username-based, not callsign-based.
- The `_operator` callsign field stays in each document for ADIF, display, and historical semantics.
- Phase 59 must not migrate data or refactor every call site; it should create the access boundary later phases will use.
- The helper should reject unsafe usernames instead of silently rewriting them into a different collection name.

## Recommended Approach

Add a small `app/qso/collections.py` module that owns:

- `qso_collection_name(username: str) -> str`
- `get_user_qso_collection(user_or_username)`
- `get_qso_collection_for_username(username: str)`
- index model definitions for dynamic QSO collections
- idempotent index setup helpers

Keep the current `QSO` Beanie document registered for now. Later phases can validate raw MongoDB documents with `QSO.model_validate(...)` or construct `QSO(**doc)` while targeting raw per-user collections for storage.

## Index Strategy

Phase 59 should mirror current index intent on per-user collections:

- duplicate lookup fields: `_operator`, `CALL`, `qso_date_utc`, `BAND`, `MODE`
- active/deleted filtering: `_operator`, `_deleted`
- created-at sorting: `_operator`, `_created_at`
- rowHash uniqueness: unique sparse `rowHash`

Even though physical per-user isolation eventually allows simpler indexes, matching the existing query shape reduces risk while Phases 61 and 62 move call sites.

## Validation Implications

Tests can stay fast and focused:

- pure tests for collection-name derivation and unsafe username rejection
- monkeypatched database-client tests for collection access
- mocked async collection tests for `create_indexes(...)`
- source-level assertions that index names/options preserve rowHash uniqueness and current query support

No live MongoDB is required for Phase 59 verification.

