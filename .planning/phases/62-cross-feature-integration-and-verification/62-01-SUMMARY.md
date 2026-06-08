---
phase: 62
plan: 62-01
status: complete
completed: 2026-06-08
---

# Phase 62 Plan 01 Summary

## Objective

Finish v3.1 cross-feature integration by moving remaining QSO-related features onto per-user `<username>_qsos` collections, preserving live feed behavior through app-level broadcasts, and proving backup/restore includes dynamic QSO collections.

## Implemented

- Stats now resolves the logged-in `User`, aggregates from that user's raw QSO collection, and preserves the existing stats response/template data shape.
- Admin clear-log now counts and deletes from the target user's QSO collection while preserving admin-owned password verification and HTMX 200-fragment behavior.
- Live feed broadcasts now happen from successful app-created QSO inserts via `insert_qso_dict(...)`, covering REST, browser, ADIF import/review, UDP, and ACLog write paths through the shared insert service.
- Startup no longer starts a live-feed change stream watcher against the legacy shared `qsos` collection.
- Backup/restore full-database behavior is covered with a dynamic `alice_qsos`/`bob_qsos` round-trip test, including ObjectId and datetime BSON preservation.
- Stats/admin tests were adapted to seed/read per-user collections when MongoDB is available and skip cleanly when unavailable.
- Added fake/unit coverage for stats aggregation without MongoDB, feed broadcast rendering, and service-level insert broadcasts.
- Updated v3.1 requirements traceability for QSO, cross-feature, and verification requirements.

## Verification

- `.venv/bin/python -m pytest tests/test_watcher.py tests/test_backup_restore.py tests/test_qso_service_collections.py tests/test_stats.py tests/test_admin_clear_log.py tests/test_qso_collections.py tests/test_qso_collection_migration.py tests/test_udp_token.py tests/test_udp_pipeline.py tests/test_clear_log.py tests/test_sse_sentinel.py` — 63 passed, 25 skipped.
- `.venv/bin/python -m pytest tests/test_qso_api.py tests/test_qso_api_key.py tests/test_adif_import.py tests/test_adif_export.py tests/test_duplicate_detection.py tests/test_custom_qso_fields.py` — 10 passed, 55 skipped.
- `.venv/bin/python -m ruff check app/stats app/admin app/feed app/main.py app/backup app/qso app/adif app/udp app/aclog tests/test_stats.py tests/test_admin_clear_log.py tests/test_watcher.py tests/test_backup_restore.py tests/test_qso_service_collections.py` — passed.
- `.venv/bin/python -m compileall app/stats app/admin app/feed app/backup app/qso app/adif app/udp app/aclog app/main.py tests/test_stats.py tests/test_admin_clear_log.py tests/test_watcher.py tests/test_backup_restore.py tests/test_qso_service_collections.py` — passed.

## Notes

- Mongo-backed tests skip in this sandbox because local MongoDB is unavailable.
- Remaining `QSO.get_pymongo_collection()` usage is in legacy startup migrations and rowHash migration helpers, not Phase 62 runtime feature paths.
- `watch_qsos(...)` remains as a tested helper but is no longer started against the shared `qsos` collection during app startup.
