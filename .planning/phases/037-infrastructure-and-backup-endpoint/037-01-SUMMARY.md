---
phase: 037-infrastructure-and-backup-endpoint
plan: 01
subsystem: infra
tags: [mongodb, backup, fastapi, docker, asyncio, pymongo]

# Dependency graph
requires: []
provides:
  - GET /admin/ui/backup/download endpoint that streams a timestamped .gz backup file
  - sync _write_backup helper using MongoClient for asyncio.to_thread compatibility
  - async run_backup orchestrator with asyncio.to_thread wrapping
  - Docker volume mount ./backups:/app/backups on admin service
  - datetime.now(timezone.utc) replaces deprecated datetime.utcnow()
affects: [038-backup-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sync/async split: sync DB helper (_write_backup) wrapped by async orchestrator (run_backup) via asyncio.to_thread"
    - "Lazy imports inside route handler to avoid circular import risk with app.config.settings"
    - "FileResponse filename derived from backup_path.stem to avoid second datetime.now() call"

key-files:
  created: []
  modified:
    - app/backup/dump.py
    - app/admin/ui_router.py
    - docker-compose.yml

key-decisions:
  - "Split run_backup into sync _write_backup (MongoClient) + async run_backup (asyncio.to_thread) — necessary because AsyncMongoClient cannot be used in sync context, and passing async def to asyncio.to_thread silently returns a coroutine object"
  - "Use require_admin_cookie (not require_admin) on backup endpoint — browser sends cookie not Bearer header, wrong dependency causes silent 302 redirect"
  - "Derive FileResponse filename from backup_path.stem to ensure filename matches file on disk without a second datetime call"

patterns-established:
  - "asyncio.to_thread pattern: sync DB I/O helpers callable from async FastAPI routes without blocking event loop"
  - "Cookie-based admin auth: all admin UI routes use require_admin_cookie exclusively"

# Metrics
duration: 4min
completed: 2026-04-14
---

# Phase 37 Plan 01: Infrastructure and Backup Endpoint Summary

**MongoDB backup wired to GET /admin/ui/backup/download with Docker volume persistence, asyncio.to_thread event-loop safety, and cookie-based admin auth**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-14T13:57:17Z
- **Completed:** 2026-04-14T14:01:07Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Refactored `app/backup/dump.py` into sync `_write_backup` + async `run_backup` orchestrator; `asyncio.to_thread` wrapping keeps event loop unblocked during MongoDB reads and gzip I/O
- Replaced deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)` and updated strftime format to `%Y-%m-%d-%H-%M-%S` (human-readable hyphen-separated, no T separator)
- Added `./backups:/app/backups` volume mount to `admin` service in docker-compose.yml, matching the existing `api` service mount
- Added `GET /admin/ui/backup/download` to `app/admin/ui_router.py` protected by `require_admin_cookie`, returning `FileResponse` with `application/gzip` media type and `ollog-backup-{timestamp}.gz` filename

## Task Commits

Each task was committed atomically:

1. **Task 1: Refactor dump.py and add Docker volume mount** - `a0af77d` (feat)
2. **Task 2: Add backup download endpoint to admin UI router** - `da331cf` (feat)

**Plan metadata:** (docs commit — see final commit hash below)

## Files Created/Modified
- `app/backup/dump.py` - Split into sync `_write_backup` + async `run_backup`; asyncio.to_thread wrapping; deprecated utcnow replaced; strftime format updated
- `app/admin/ui_router.py` - Added `FileResponse` import; new `GET /backup/download` route with `require_admin_cookie` auth
- `docker-compose.yml` - Added `./backups:/app/backups` volume mount to `admin` service

## Decisions Made
- Split `run_backup` into sync/async to satisfy `asyncio.to_thread` requirement: `asyncio.to_thread` requires a sync callable — passing `async def` silently returns a coroutine object instead of a Path
- Used `require_admin_cookie` (not `require_admin`) because the browser sends a cookie not a Bearer Authorization header; wrong dependency causes silent 302 redirect masking the failure
- Derived `FileResponse` filename from `backup_path.stem` to avoid a second `datetime.now()` call and guarantee the download filename matches the actual file on disk

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failures in `tests/test_qso_schema.py::test_qso_duplicate_rejected` and all MongoDB integration tests — these require a live MongoDB at `mongodb:27017` (Docker-internal hostname, not available on host). Confirmed pre-existing by stash check against prior commit. No regressions introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Backend half of v2.0 Database Backup is complete
- Phase 38 can add sidebar nav entry, `GET /admin/ui/backup` page route, and `templates/admin/backup.html` with plain `<a href="/admin/ui/backup/download">` anchor (no HTMX attributes)
- Docker volume mount is in place; `./backups/` directory will be created on first backup run

---
*Phase: 037-infrastructure-and-backup-endpoint*
*Completed: 2026-04-14*
