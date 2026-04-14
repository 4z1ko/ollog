---
phase: 039-restore-backend
plan: 01
subsystem: api
tags: [fastapi, mongodb, bson, htmx, pymongo, gzip, ndjson]

# Dependency graph
requires:
  - phase: 038
    provides: dump.py with run_backup and gzip NDJSON format used by restore
provides:
  - app/backup/restore.py with _restore_from_file (sync) and run_restore (async)
  - POST /admin/ui/restore/upload route with gzip+NDJSON validation and tempfile handling
  - POST /admin/ui/restore/confirm route with path traversal guard, password check, auto-backup before drop+restore
  - Five HTMX fragment templates under templates/admin/restore/
affects: [040-restore-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sync helper + async asyncio.to_thread wrapper (mirrors dump.py)"
    - "bson.json_util.loads for BSON-correct deserialization (not json.loads)"
    - "Lazy imports inside route handlers for backup/restore deps"
    - "All HTMX error responses return HTTP 200 (HTMX 2.x ignores body on 4xx)"
    - "Path traversal guard: resolve path and check startswith(gettempdir)"

key-files:
  created:
    - app/backup/restore.py
    - templates/admin/restore/upload_error.html
    - templates/admin/restore/password_modal.html
    - templates/admin/restore/password_error.html
    - templates/admin/restore/restore_success.html
    - templates/admin/restore/restore_failure.html
  modified:
    - app/admin/ui_router.py

key-decisions:
  - "Use bson.json_util.loads (not json.loads) to restore ObjectId, datetime with correct BSON types"
  - "Auto-backup runs before any db.drop() to satisfy OPS-01 safety requirement"
  - "Path traversal guard checks resolve(temp_path).startswith(gettempdir), .gz suffix, and file existence"
  - "All HTMX responses return HTTP 200 — HTMX 2.x drops response body on 4xx"
  - "try/finally client.close() wraps only drop+insert loop (not read loop), mirroring dump.py pattern"

patterns-established:
  - "Restore module: sync _restore_from_file + async run_restore (same pattern as dump.py)"
  - "HTMX fragment templates: no html/body wrapper, minimal HTML with alert/modal CSS classes"

# Metrics
duration: 3min
completed: 2026-04-14
---

# Phase 39 Plan 01: Restore Backend Summary

**FastAPI restore backend with bson.json_util.loads, path traversal guard, auto-backup-before-drop, and five HTMX fragment templates wired to POST /restore/upload and /restore/confirm**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-14T17:26:04Z
- **Completed:** 2026-04-14T17:29:15Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- `app/backup/restore.py` created with sync `_restore_from_file` (uses `bson.json_util.loads`) and async `run_restore` (uses `asyncio.to_thread`), mirroring `dump.py` structure exactly
- `POST /admin/ui/restore/upload` validates gzip decompressibility and NDJSON structure, returns `password_modal.html` on success or `upload_error.html` on failure with no tempfile leak
- `POST /admin/ui/restore/confirm` enforces path traversal guard, password verification, runs auto-backup before any `db.drop()`, and cleans up the tempfile in `finally`
- All five HTMX fragment templates created under `templates/admin/restore/`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create app/backup/restore.py** - `24b0de2` (feat)
2. **Task 2: Add restore routes and fragment templates** - `61e42c3` (feat)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified
- `app/backup/restore.py` - Sync/async restore module using bson.json_util.loads
- `app/admin/ui_router.py` - Added UploadFile import, restore_upload and restore_confirm routes
- `templates/admin/restore/upload_error.html` - Inline error fragment for bad file upload
- `templates/admin/restore/password_modal.html` - Modal fragment with hidden temp_path input
- `templates/admin/restore/password_error.html` - Modal re-render with inline password error
- `templates/admin/restore/restore_success.html` - Success banner with auto-backup filename
- `templates/admin/restore/restore_failure.html` - Error banner with auto-backup filename and error message

## Decisions Made
- Used `bson.json_util.loads` aliased as `bson_loads` (not `json.loads`) so ObjectId, datetime, and all BSON types are restored with correct types, not plain dicts
- Auto-backup runs before any `db.drop()` to satisfy OPS-01 — if restore fails after auto-backup, the failure response still includes the auto-backup filename
- Path traversal guard: `resolve(temp_path).startswith(gettempdir())`, `.gz` suffix check, and `.exists()` check — all three required before any file access
- All HTMX error responses return HTTP 200 status — HTMX 2.x ignores the response body on 4xx, which would silently swallow error fragments

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All backend logic and fragment templates are complete for Phase 40 (Restore UI)
- Phase 40 needs to: wire the HTMX upload form to POST /restore/upload, add CSS for modal/alert classes, and add a restore page shell
- No blockers or concerns

## Self-Check: PASSED

All files verified present on disk. Both task commits verified in git log.

---
*Phase: 039-restore-backend*
*Completed: 2026-04-14*
