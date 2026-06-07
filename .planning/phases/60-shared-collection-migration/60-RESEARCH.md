# Phase 60 Research: Shared Collection Migration

**Date:** 2026-06-07
**Phase:** 60 - Shared Collection Migration
**Status:** Complete

## Current State

The app still uses the shared Beanie `QSO` document bound to `QSO.Settings.name = "qsos"`. Startup backfills in `app/main.py` normalize that collection before the app starts serving requests:

- `_created_at` backfill
- `TIME_ON` normalization
- `rowHash` backfill/index setup

Phase 59 added `app/qso/collections.py`, which provides the target collection naming/access/index boundary for `<username>_qsos`.

## Migration Shape

The safest Phase 60 migration is a copy-only backfill:

1. Read all documents from `settings.mongodb_db["qsos"]`.
2. Resolve each document's `_operator` callsign to exactly one `User`.
3. Ensure the target user's QSO indexes exist.
4. Insert the raw document into `<username>_qsos` only if its `_id` is absent there.
5. Report skipped/unresolved/ambiguous/conflicting documents.
6. Leave the source document untouched.

This keeps Phase 60 behavior-neutral while making Phase 61 possible.

## Resolution Risk

`User.username` is unique, but `User.callsign` is not unique in the model. The migration must therefore build a callsign-to-users map and treat duplicate matches as ambiguous. Guessing would risk moving QSOs into the wrong user's collection.

The copied QSO document's `_operator` field should not be normalized or rewritten. It remains the historical callsign field for ADIF/display semantics.

## Idempotence Strategy

Use insert-only semantics for target writes. A target document with the same `_id` should be counted as already migrated and left unchanged. This protects newer per-user changes if an operator has already written or edited target-side data before a rerun.

If target `rowHash` uniqueness rejects a different `_id` with the same `rowHash`, report the document as a conflict instead of overwriting or deleting anything.

## Recommended Module

Add `app/qso/collection_migration.py` with:

- report data helpers
- callsign resolution helpers
- `migrate_shared_qsos_to_user_collections(...)`
- optional `dry_run`
- JSON report writing
- `python -m app.qso.collection_migration` CLI

Startup can import and call the migration from `app/main.py` after rowHash backfill, keeping ordering explicit and idempotent.

## Test Strategy

Focused tests should cover the migration logic without requiring live MongoDB:

- normal migration for two users
- idempotent rerun does not duplicate or overwrite
- unresolved `_operator` reported
- duplicate callsign ambiguity reported
- soft-deleted rows copied
- `rowHash`, `_created_at`, `_id`, extras, profile fields, and custom fields preserved
- indexes created before target writes

Optional live MongoDB tests can be skipped when MongoDB is unavailable, following existing test style.

