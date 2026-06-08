# Phase 62 Validation Strategy

**Date:** 2026-06-08
**Status:** Ready

## Goal

Verify that all remaining cross-feature QSO paths work with per-user `<username>_qsos` collections while preserving external behavior.

## Required Evidence

### INT-01 Stats

- Stats service aggregates from the logged-in user's collection.
- Stats route still renders the same template context and empty/non-empty chart behavior.
- Another user's collection data does not appear in the current user's stats.

### INT-02 Admin Clear Log

- Admin modal counts the target user's collection.
- Correct admin password deletes active QSOs from the target user's collection.
- Wrong admin password does not delete.
- Password verification remains against the admin user.

### INT-03 Live Feed / SSE

- Successful app-created QSO inserts broadcast the same feed row HTML to existing SSE clients.
- Shared `qsos` change stream watcher is no longer required for live-feed behavior.
- Existing Log View auto-refresh sentinel/new-QSO badge behavior remains compatible.

### INT-04 Backup / Restore

- Backup output includes dynamically named `<username>_qsos` collections.
- Restore recreates dynamic QSO collections and documents.
- BSON types such as ObjectId and datetime survive round-trip.

### INT-05 / VERIFY-03 / VERIFY-04 Isolation and Regression

- Tests cover representative REST, browser/service, ADIF, stats, admin clear-log, API-token, and UDP paths against per-user collections or fake equivalents.
- Existing API schemas, UI contexts, duplicate handling, sorting, filtering, pagination, and live-update sentinels remain compatible.

## Suggested Verification Commands

```bash
.venv/bin/python -m pytest tests/test_stats.py tests/test_admin_clear_log.py tests/test_watcher.py tests/test_sse_sentinel.py
.venv/bin/python -m pytest tests/test_qso_service_collections.py tests/test_qso_collections.py tests/test_qso_collection_migration.py tests/test_udp_token.py tests/test_udp_pipeline.py tests/test_clear_log.py
.venv/bin/python -m pytest tests/test_qso_api.py tests/test_qso_api_key.py tests/test_adif_import.py tests/test_adif_export.py tests/test_duplicate_detection.py tests/test_custom_qso_fields.py
.venv/bin/python -m ruff check app/stats app/admin app/feed app/main.py app/backup tests/test_stats.py tests/test_admin_clear_log.py tests/test_watcher.py
.venv/bin/python -m compileall app/stats app/admin app/feed app/backup app/main.py
```

Mongo-dependent tests may skip when MongoDB is unavailable; fake/unit tests must still pass.
