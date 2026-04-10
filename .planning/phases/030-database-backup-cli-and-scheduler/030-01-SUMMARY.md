---
phase: 030-database-backup-cli-and-scheduler
plan: "01"
subsystem: database
tags: [backup, pymongo, bson, ejson, gzip, ndjson, apscheduler, aioboto3, s3, cron]

# Dependency graph
requires:
  - phase: 029-admin-container-isolation
    provides: app/config.py Settings base, app/main.py lifespan pattern
provides:
  - app/backup/ package with CLI, dump, upload, and scheduler modules
  - BACKUP_SCHEDULE cron scheduler wired into lifespan
  - Host-visible bind mount for backup persistence across restarts
  - S3 upload with graceful failure handling
affects:
  - 031-documentation-rewrite (docs must cover backup CLI usage)

# Tech tracking
tech-stack:
  added:
    - apscheduler>=3.10,<4 (AsyncIOScheduler + CronTrigger)
    - aioboto3>=13,<16 (async S3 upload)
  patterns:
    - "CLI backup via python -m app.backup — asyncio.run() creates own event loop, no lifespan"
    - "AsyncMongoClient instantiated directly in dump.py (not get_client()) — lifespan not running in CLI"
    - "EJSON NDJSON: one JSON object per line, bson.json_util.dumps(CANONICAL_JSON_OPTIONS)"
    - "Conditional scheduler startup in lifespan mirroring udp_enabled guard pattern"
    - "S3 failure absorbed in upload.py — ERROR log, local file kept, caller never sees exception"

key-files:
  created:
    - app/backup/__init__.py
    - app/backup/__main__.py
    - app/backup/dump.py
    - app/backup/upload.py
    - app/backup/scheduler.py
  modified:
    - pyproject.toml
    - app/config.py
    - app/main.py
    - docker-compose.yml

key-decisions:
  - "AsyncMongoClient instantiated directly in dump.py — get_client() returns None in CLI context where lifespan has not run"
  - "CANONICAL_JSON_OPTIONS (not RELAXED) preserves Int64, Decimal128, Binary type fidelity"
  - "apscheduler pinned <4 — v4 alpha removed AsyncIOScheduler entirely"
  - "AWS credentials via boto3 credential chain, not Settings fields"
  - "backup_task=None in lifespan for forward compatibility; APScheduler manages job dispatch"

patterns-established:
  - "Backup package: dump.py creates own client, never shares app-level connection pool"
  - "make_scheduler() returns configured-but-not-started scheduler; lifespan calls .start()"
  - "Shutdown: backup_task cancel + backup_scheduler.shutdown(wait=False) before close_db()"

# Metrics
duration: 4min
completed: 2026-04-10
---

# Phase 030 Plan 01: Database Backup CLI and Scheduler Summary

**Pure-Python MongoDB EJSON gzip backup via `python -m app.backup`, with optional APScheduler cron scheduling and async S3 upload wired into FastAPI lifespan**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-10T20:43:07Z
- **Completed:** 2026-04-10T20:47:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Created `app/backup/` package with four source files: EJSON NDJSON gzip dumper, aioboto3 S3 uploader, APScheduler factory, and CLI `__main__` entry point
- Added four backup Settings fields to `app/config.py` and wired conditional scheduler startup/shutdown into lifespan in `app/main.py`
- Added `./backups:/app/backups` bind mount and commented `BACKUP_SCHEDULE` example to `docker-compose.yml`; added `apscheduler>=3.10,<4` and `aioboto3>=13,<16` to `pyproject.toml`

## Task Commits

Each task was committed atomically:

1. **Task 1: Create app/backup/ package** - `c5569b8` (feat)
2. **Task 2: Wire dependencies, settings, lifespan, and docker-compose** - `e6b3406` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified

- `app/backup/__init__.py` — empty package marker
- `app/backup/__main__.py` — CLI entry point; `asyncio.run(main())`; prints confirmed path to stdout
- `app/backup/dump.py` — `run_backup(settings)` coroutine using `AsyncMongoClient` + `bson.json_util.dumps(CANONICAL_JSON_OPTIONS)` NDJSON gzip
- `app/backup/upload.py` — `upload_to_s3()` with aioboto3; catches all exceptions, logs ERROR, never re-raises
- `app/backup/scheduler.py` — `make_scheduler()` factory returning configured `AsyncIOScheduler` (not started)
- `pyproject.toml` — added `aioboto3>=13,<16` and `apscheduler>=3.10,<4`
- `app/config.py` — added `backup_dir`, `backup_schedule`, `backup_s3_bucket`, `backup_s3_prefix` fields
- `app/main.py` — conditional scheduler startup/shutdown in lifespan guarded by `settings.backup_schedule`
- `docker-compose.yml` — bind mount `./backups:/app/backups`; commented `BACKUP_SCHEDULE=0 2 * * *` example

## Decisions Made

- **AsyncMongoClient direct instantiation in dump.py:** `get_client()` returns `None` in CLI context where FastAPI lifespan has not run; backup must create its own client
- **CANONICAL_JSON_OPTIONS over RELAXED:** Preserves `Int64`, `Decimal128`, `Binary` type fidelity through round-trips; relaxed mode loses these
- **apscheduler pinned `<4`:** v4 alpha removed `AsyncIOScheduler` entirely; pin is mandatory for compatibility
- **AWS credentials via boto3 credential chain:** `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` not added to Settings — aioboto3/boto3 reads them automatically from environment
- **`backup_task=None` in lifespan:** APScheduler manages job dispatch internally; explicit `asyncio.Task` tracking is present for forward compatibility but starts as `None`

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required beyond optionally setting `BACKUP_SCHEDULE` in `.env` and AWS credential env vars for S3 upload.

## Self-Check

**Checking created files exist:**

- `app/backup/__init__.py` — FOUND
- `app/backup/__main__.py` — FOUND
- `app/backup/dump.py` — FOUND
- `app/backup/upload.py` — FOUND
- `app/backup/scheduler.py` — FOUND

**Checking commits exist:**

- `c5569b8` — FOUND (feat(030-01): create app/backup/ package)
- `e6b3406` — FOUND (feat(030-01): wire backup deps, settings, lifespan, and docker-compose)

## Self-Check: PASSED

## Next Phase Readiness

- Phase 030 complete — database backup CLI, scheduler, and S3 upload all implemented
- Phase 031 (documentation rewrite) can now document the backup CLI workflow
- Operator can run `python -m app.backup` in container or locally (with correct `.env`) to produce a `.gz` export immediately
- `BACKUP_SCHEDULE` env var in `.env` activates nightly backups without code changes

---
*Phase: 030-database-backup-cli-and-scheduler*
*Completed: 2026-04-10*
