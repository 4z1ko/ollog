---
phase: 030-database-backup-cli-and-scheduler
verified: 2026-04-10T20:51:33Z
status: passed
score: 5/5 must-have truths verified
re_verification: false
---

# Phase 30: Database Backup CLI and Scheduler — Verification Report

**Phase Goal:** `python -m app.backup` produces a gzip EJSON export of all MongoDB collections to `./backups/<timestamp>.gz`, with optional scheduled S3 upload via `BACKUP_SCHEDULE` cron env var — and backup files survive container restarts via bind mount.

**Verified:** 2026-04-10T20:51:33Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                  | Status     | Evidence                                                                                          |
|----|--------------------------------------------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------------|
| 1  | `python -m app.backup` exits 0 and prints the path of the created .gz file to stdout                  | VERIFIED   | `__main__.py` calls `asyncio.run(main())`; `main()` awaits `run_backup()` and calls `print(str(backup_path))`; no `sys.exit` call so Python default exit 0 applies |
| 2  | gunzip shows NDJSON lines with `{"collection": ..., "doc": ...}` and EJSON-encoded BSON types          | VERIFIED   | `dump.py` writes `dumps({"collection": coll_name, "doc": doc}, json_options=CANONICAL_JSON_OPTIONS) + "\n"` inside `gzip.open(..., "wt")`; CANONICAL_JSON_OPTIONS encodes ObjectId, datetime, etc. as EJSON |
| 3  | Backup files survive container restarts via bind mount (host-visible without docker cp)                | VERIFIED   | `docker-compose.yml` line 29: `- ./backups:/app/backups`; `settings.backup_dir` defaults to `/app/backups`; `dump.py` writes to `Path(settings.backup_dir)` |
| 4  | Operator app logs 'Backup scheduler started' at startup when BACKUP_SCHEDULE is set; no scheduler log when absent | VERIFIED   | `main.py` lines 61-70: `if settings.backup_schedule:` gates the entire scheduler block; `logger.info("Backup scheduler started (cron: %s)", settings.backup_schedule)` only executes inside that branch |
| 5  | When backup_s3_bucket is set and S3 upload fails, app logs ERROR, local file is kept, process exits 0  | VERIFIED   | `upload.py` wraps entire upload in `try/except Exception as exc:` with `logger.error(...)` and no `raise`; `dump.py` calls `upload_to_s3` after `return`-eligible code but before returning `backup_path` — local file is already written before upload attempt; `__main__.py` has no surrounding try/except so S3 error is swallowed and process exits 0 |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact                      | Status     | Details                                                                                 |
|-------------------------------|------------|-----------------------------------------------------------------------------------------|
| `app/backup/__init__.py`      | VERIFIED   | Exists (1-line file, intentionally minimal — package marker)                            |
| `app/backup/__main__.py`      | VERIFIED   | Contains `asyncio.run`; substantive entry point with `print(str(backup_path))`          |
| `app/backup/dump.py`          | VERIFIED   | Contains `CANONICAL_JSON_OPTIONS` imported and used at call site; full implementation   |
| `app/backup/upload.py`        | VERIFIED   | Contains `upload_to_s3`; full aioboto3 async implementation with exception swallowing   |
| `app/backup/scheduler.py`     | VERIFIED   | Contains `make_scheduler`; configures `AsyncIOScheduler` with `CronTrigger`             |
| `app/config.py`               | VERIFIED   | Contains `backup_dir`, `backup_schedule`, `backup_s3_bucket`, `backup_s3_prefix` fields |
| `app/main.py`                 | VERIFIED   | Contains `backup_schedule` check at line 61; scheduler lifecycle managed in lifespan    |
| `docker-compose.yml`          | VERIFIED   | Line 29: `- ./backups:/app/backups` bind mount on api service                           |
| `pyproject.toml`              | VERIFIED   | Line 9: `"apscheduler>=3.10,<4"` — correct bounded pin                                 |

---

### Key Link Verification

| From            | To                       | Via                                          | Status  | Details                                                                                         |
|-----------------|--------------------------|----------------------------------------------|---------|-------------------------------------------------------------------------------------------------|
| `dump.py`       | MongoDB                  | `AsyncMongoClient(settings.mongodb_uri)`     | WIRED   | Direct instantiation at line 20; get_client() not imported or called anywhere in backup module  |
| `dump.py`       | EJSON encoding           | `CANONICAL_JSON_OPTIONS`                     | WIRED   | Imported from `bson.json_util` line 6; passed as `json_options=` at line 37                    |
| `pyproject.toml`| apscheduler v3 API       | `>=3.10,<4`                                  | WIRED   | Ceiling `<4` prevents accidental install of v4-alpha which removed `AsyncIOScheduler`           |
| `upload.py`     | caller error isolation   | bare `except Exception`                      | WIRED   | Lines 22-23: catches all exceptions; no `raise`; only `logger.error`                           |
| `main.py`       | scheduler start          | `if settings.backup_schedule:` gate          | WIRED   | Lines 61-70: entire scheduler creation and start inside the conditional block                   |

---

### Requirements Coverage

No requirements from REQUIREMENTS.md were mapped to this phase — skipped.

---

### Anti-Patterns Found

None. No TODO/FIXME/placeholder comments, no empty return values, no stub implementations found in any backup module file.

---

### Human Verification Required

#### 1. End-to-end CLI run against live MongoDB

**Test:** With MongoDB running, execute `python -m app.backup` from the project root.
**Expected:** Process prints a path like `./backups/20260410T205133Z.gz`, exits 0; `gunzip -c` on the file shows NDJSON lines with EJSON-encoded documents.
**Why human:** Cannot start MongoDB or execute the Python module in this verification context.

#### 2. Container restart file persistence

**Test:** Run `docker compose up -d`, trigger a backup, then `docker compose restart api`; confirm the `.gz` file is still visible on the host in `./backups/`.
**Expected:** File persists; host directory is writable without `docker cp`.
**Why human:** Requires running Docker.

#### 3. Scheduler startup log presence/absence

**Test:** Start container with `BACKUP_SCHEDULE=` unset; confirm no "Backup scheduler started" line appears. Then set `BACKUP_SCHEDULE=* * * * *` and restart; confirm the log line appears.
**Expected:** Log line present only when env var is set.
**Why human:** Requires running the application.

---

### Gaps Summary

No gaps. All five observable truths are supported by substantive, wired artifacts. All key link invariants hold in the actual code.

---

_Verified: 2026-04-10T20:51:33Z_
_Verifier: Claude (gsd-verifier)_
