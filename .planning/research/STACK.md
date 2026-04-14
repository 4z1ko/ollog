# Stack Research

**Domain:** MongoDB backup download endpoint — FastAPI admin sub-app
**Researched:** 2026-04-13
**Confidence:** HIGH (all findings verified directly from codebase; no unverified training-data claims)

---

## Existing Backup Infrastructure (Codebase Audit)

The project already has a complete, working backup engine. This is the single most important finding for this milestone.

| File | What It Does |
|------|-------------|
| `app/backup/dump.py` | `run_backup(settings)` — async; iterates all collections via `AsyncMongoClient`, writes EJSON NDJSON to a gzip file at `settings.backup_dir/{timestamp}.gz`; returns the `Path` of the created file |
| `app/backup/__init__.py` | Empty package marker |
| `app/backup/scheduler.py` | `make_scheduler(cron, job)` — wraps APScheduler `AsyncIOScheduler`; used by `app/main.py` lifespan |
| `app/backup/upload.py` | `upload_to_s3(path, bucket, key)` — aioboto3, fire-and-forget; called by `run_backup` when `BACKUP_S3_BUCKET` is set |
| `app/backup/__main__.py` | CLI entry point: `python -m app.backup` — one-shot backup, prints path to stdout |

`run_backup` already returns the `Path` of the created `.gz` file. The scheduler in `app/main.py` (port 8000, `api` service) calls it on a cron. Nothing in the admin sub-app (`admin_main.py`, port 8001, `admin` service) calls `run_backup` yet.

**Conclusion: zero new Python libraries are needed for the dump itself.** The new milestone adds one HTTP endpoint to `admin_main.py` that calls the already-existing `run_backup`, then streams the resulting file back to the browser.

---

## Recommended Stack

### Core Technologies

All already installed in `pyproject.toml`. No additions required.

| Technology | Pinned Version | Role in Feature | Why It Is The Right Choice |
|------------|---------------|-----------------|---------------------------|
| `fastapi[standard]` | `>=0.135.0` | HTTP endpoint + `StreamingResponse` | Already in stack; `StreamingResponse` handles streaming binary downloads without buffering the full file in memory |
| `pymongo` | `>=4.16.0` | `AsyncMongoClient` used inside `run_backup` | Already used; `bson.json_util.dumps` with `CANONICAL_JSON_OPTIONS` handles ObjectId, datetime, Decimal128 correctly |
| `bson` (bundled with pymongo) | n/a | EJSON serialisation inside `run_backup` | Ships with pymongo; no separate install |
| `gzip` (Python stdlib) | n/a | Compression in `run_backup` | Python stdlib; no install |
| `apscheduler` | `>=3.10,<4` | Existing scheduled backups (unchanged) | Already pinned; `<4` upper bound is load-bearing — APScheduler v4 removed `AsyncIOScheduler` entirely |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `fastapi.responses.StreamingResponse` | bundled with FastAPI | Stream `.gz` file to browser | Use for the download endpoint — yields file in chunks, avoids holding the full backup in memory; consistent with existing patterns in `app/adif/router.py` and `app/qso/ui_router.py` |
| `fastapi.responses.FileResponse` | bundled with FastAPI | Serve static files by path | Do NOT use here — requires the file to pre-exist on a path the server process can reach; the admin container currently lacks the `/app/backups` volume mount (see Docker note below) |
| `fastapi.background.BackgroundTasks` | bundled with FastAPI | Delete temp file after response completes | Not needed here; backup files are intentionally retained on disk |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pytest-asyncio` | Async test runner | Already in `[dev]` deps; sufficient for endpoint integration tests |
| `httpx` | Async HTTP client for tests | Already in `[dev]` deps |

---

## Installation

No new dependencies. The feature uses only what is already declared in `pyproject.toml`.

```bash
# Nothing to add — run_backup, StreamingResponse, and require_admin_cookie are all available
```

The only `pyproject.toml` entry to double-check: `aioboto3>=13,<16` is already a top-level (non-optional) dependency, so it is installed in all containers including `admin`.

---

## Key Decision 1: mongodump subprocess vs pymongo EJSON dump

**Use the existing `app/backup/dump.py::run_backup`. Do not use mongodump.**

| Criterion | `mongodump` subprocess | `run_backup` (pymongo EJSON) |
|-----------|----------------------|------------------------------|
| Available in `python:3.12-slim` | No — not installed | Yes — pure Python |
| Requires Dockerfile change | Yes (install `mongodb-database-tools`, adds ~150 MB) | No |
| Produces `mongorestore`-compatible archive | Yes | No (EJSON NDJSON, not BSON wire format) |
| Handles ObjectId / datetime correctly | Yes | Yes (`CANONICAL_JSON_OPTIONS`) |
| Already tested and documented | No | Yes (scheduler, CLI, `docs/admin-guide/backup.md`) |
| Design intent of this project | Explicitly avoided | Explicitly chosen |

The `docs/admin-guide/backup.md` states verbatim: "No external mongodump tool is required." This is a deliberate, documented architectural decision. The existing dump function is the correct integration point.

**mongodump is a non-starter** for `python:3.12-slim`. The image contains no `mongodump` binary. Adding it requires installing the MongoDB Database Tools package via `apt`, which significantly increases image size and adds system-level complexity with no benefit for a self-hosted ham radio logbook (small dataset, no `mongorestore`-compatible format required).

---

## Key Decision 2: StreamingResponse vs FileResponse

**Use `StreamingResponse` reading the file in binary chunks.**

The download endpoint flow:
1. Call `await run_backup(settings)` — this is already `async`, uses `AsyncMongoClient`, and returns the `Path` of the created `.gz` file.
2. Open the file and yield chunks via an `async` generator.
3. Return `StreamingResponse` with `media_type="application/gzip"` and `Content-Disposition: attachment; filename="ollog-backup-{timestamp}.gz"`.

Why not `FileResponse`:
- `FileResponse` requires the file to exist on a path the serving process can read.
- The `admin` service does NOT currently have the `/app/backups` volume mount in `docker-compose.yml` (only the `api` service has it).
- Even if the volume is added, `StreamingResponse` is already the established pattern in this codebase (used in `app/adif/router.py` for ADIF export and in `app/qso/ui_router.py`). Consistency favors `StreamingResponse`.

---

## Key Decision 3: Timestamp Filename for Browser Download

`run_backup` writes files as `{YYYYMMDDTHHMMSSZ}.gz` (e.g., `20260413T153042Z.gz`). The milestone goal is `ollog-backup-20260413-153042.gz` in the `Content-Disposition` header.

Recommended approach: derive the display filename from `Path.name` with a simple string transform in the endpoint, or compute `datetime.utcnow()` before calling `run_backup` and format it independently. Do NOT rename the file on disk — that creates a race condition if scheduled backups or the CLI are also running.

---

## Docker-Compose Integration Point

The `admin` service currently in `docker-compose.yml`:
- Runs `uvicorn app.admin_main:app --host 0.0.0.0 --port 8001`
- Has `env_file: .env` (so `BACKUP_DIR`, `MONGODB_URI`, `MONGODB_DB` are all available via `settings`)
- Does NOT mount `./backups:/app/backups`

Required addition to `docker-compose.yml` for the backup to persist on the host:

```yaml
admin:
  # ... existing config ...
  volumes:
    - ./backups:/app/backups   # add this line
```

Without this, `run_backup` writes to `/app/backups` inside the admin container's ephemeral filesystem. The file is streamed back to the browser correctly within the same request, but it does not survive container restarts and is not co-located with scheduled backups created by the `api` service. Adding the volume mount is the correct production configuration.

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| pymongo EJSON + gzip (existing `run_backup`) | `mongodump` subprocess | Only if `mongorestore`-compatible BSON archive is required AND Dockerfile is modified to install `mongodb-database-tools` |
| `StreamingResponse` (chunked file read) | `FileResponse` | If admin service has the `/app/backups` volume mount AND file always pre-exists; `FileResponse` then becomes equally valid |
| In-process backup generated on request | Pre-generated backup + serve latest | Only if backup latency matters or the logbook is very large; unnecessary for a self-hosted ham radio logbook |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `mongodump` subprocess | Not present in `python:3.12-slim`; violates existing documented design decision; adds significant Docker image complexity | `app/backup/dump.py::run_backup` |
| GridFS for backup storage | Adds unnecessary indirection; app is single-node self-hosted; backups already go to bind-mounted `./backups/` | Direct filesystem write in `run_backup` |
| APScheduler v4 | `AsyncIOScheduler` was removed in v4; would break the existing scheduler | `apscheduler>=3.10,<4` (already pinned correctly) |
| Blocking file I/O in the async endpoint | Would stall the event loop during dump | `run_backup` is already `async`; for file streaming, use `asyncio.to_thread` if opening the file proves slow on large backups |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `apscheduler>=3.10,<4` | `asyncio` event loop | `<4` upper bound is load-bearing; v4 removed `AsyncIOScheduler` entirely |
| `pymongo>=4.16.0` | Python 3.12, `AsyncMongoClient` | `AsyncMongoClient` is a pymongo 4.x API; compatible with existing Beanie 2.1+ ODM |
| `aioboto3>=13,<16` | Python 3.12, asyncio | Already declared as a non-optional dep; available in all containers |

---

## Sources

All sources are direct codebase reads. Confidence: HIGH throughout.

- `/Users/royco/ollog/app/backup/dump.py` — `run_backup` signature, EJSON strategy, return value confirmed
- `/Users/royco/ollog/app/backup/scheduler.py` — APScheduler v3 pin confirmed
- `/Users/royco/ollog/app/backup/upload.py` — aioboto3 usage confirmed
- `/Users/royco/ollog/app/backup/__main__.py` — CLI entry point confirmed
- `/Users/royco/ollog/app/adif/router.py` — `StreamingResponse` pattern confirmed as established project convention
- `/Users/royco/ollog/app/qso/ui_router.py` — second `StreamingResponse` usage confirmed
- `/Users/royco/ollog/docker-compose.yml` — volume mount gap for admin service confirmed; `env_file` presence confirmed
- `/Users/royco/ollog/Dockerfile` — `python:3.12-slim` base image; no mongodump binary present
- `/Users/royco/ollog/pyproject.toml` — all existing deps confirmed; no new additions needed
- `/Users/royco/ollog/app/config.py` — `backup_dir`, `backup_s3_bucket`, `mongodb_uri`, `mongodb_db` settings confirmed
- `/Users/royco/ollog/app/auth/dependencies.py` — `require_admin_cookie` dependency confirmed available for endpoint auth
- `/Users/royco/ollog/docs/admin-guide/backup.md` — "no mongodump required" design rationale confirmed as intentional and documented

---

*Stack research for: ollog admin backup download endpoint*
*Researched: 2026-04-13*
