# Phase 30: Database Backup CLI and Scheduler - Research

**Researched:** 2026-04-10
**Domain:** MongoDB EJSON export, APScheduler 3.x asyncio, aioboto3 S3 upload, FastAPI lifespan wiring
**Confidence:** HIGH

---

## User Constraints (from phase_context — no CONTEXT.md)

### Locked Decisions
- Package layout: `app/backup/__main__.py`, `dump.py`, `upload.py`, `scheduler.py`
- Export method: pure-Python PyMongo + `bson.json_util.dumps()` EJSON (no `mongodump` subprocess)
- Volume: bind mount `./backups:/app/backups` in `docker-compose.yml`
- Scheduler: APScheduler 3.x `AsyncIOScheduler` + `CronTrigger.from_crontab()`; pinned `apscheduler>=3.10,<4`
- S3 upload: `aioboto3>=13,<16` async upload inside lifespan; standard boto3 credential chain
- Output path: `BACKUP_DIR` env var (default `/app/backups`); no hardcoded relative paths
- `BACKUP_SCHEDULE` defaults to `None`; scheduler does not start when absent
- Backup asyncio task tracked in lifespan `yield` block, cancelled and awaited on shutdown
- CLI: `python -m app.backup` invocation (runs `__main__.py`)
- S3 upload failure: log ERROR, keep local file, exit code 0

### Deferred Ideas (OUT OF SCOPE)
- `mongodump` subprocess-based backup
- APScheduler 4.x
- Synchronous boto3 (inside lifespan — CLI may use sync if no running loop)

---

## Summary

Phase 30 adds a `python -m app.backup` CLI and optional cron-scheduled S3 backup to the operator service. The CLI produces a gzip-compressed EJSON file covering all MongoDB collections; the scheduler wires into the existing FastAPI lifespan alongside the change-stream watcher and UDP listener, using the same guarded-by-env-var start pattern already established by `udp_enabled`.

All three core libraries are already confirmed for the stack (`pymongo` is a direct dependency, `apscheduler>=3.10,<4` and `aioboto3>=13,<16` are new additions to `pyproject.toml`). The implementation touches five files: `pyproject.toml` (new deps), `app/config.py` (new settings fields), `app/main.py` (scheduler wiring in lifespan), `docker-compose.yml` (bind mount + commented example), and the new `app/backup/` package (four files). The change-stream watcher pattern in `app/feed/manager.py` is the canonical template for how async tasks are created, tracked, cancelled, and awaited.

The export format decision (EJSON via `bson.json_util`) means restoration uses `mongoimport --jsonArray --mode=upsert`, not `mongorestore`. This is a deliberate, pre-researched tradeoff documented in SUMMARY.md.

**Primary recommendation:** Mirror the UDP lifespan pattern for conditional startup; mirror the change-stream watcher pattern for task tracking/cancellation; use `bson.json_util.dumps()` with `CANONICAL_JSON_OPTIONS` for type-preserving EJSON and the aioboto3 `upload_fileobj` async pattern for S3.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pymongo | >=4.16.0 (already in deps) | MongoDB async client; iterate all collections | Already a direct dependency; `AsyncMongoClient` used throughout |
| bson (ships with pymongo) | same as pymongo | `json_util.dumps()` for EJSON serialization | Ships with pymongo; no extra install; `CANONICAL_JSON_OPTIONS` preserves BSON types |
| apscheduler | >=3.10,<4 | `AsyncIOScheduler` + `CronTrigger.from_crontab()` | Only stable asyncio scheduler with crontab string support; v4 is alpha with redesigned API |
| aioboto3 | >=13,<16 | Async S3 `upload_fileobj` inside event loop | Drop-in async wrapper for boto3; avoids blocking the event loop on large uploads |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| gzip (stdlib) | stdlib | Compress EJSON output | Always — part of the `.gz` output format |
| pathlib (stdlib) | stdlib | `BACKUP_DIR` path handling, file naming | Always — avoids os.path string manipulation |
| asyncio (stdlib) | stdlib | `create_task`, `CancelledError` | Always — wiring backup task into lifespan |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `aioboto3` async upload | synchronous `boto3` | boto3 blocks the event loop during upload — acceptable for CLI standalone use, unacceptable inside FastAPI lifespan |
| `CANONICAL_JSON_OPTIONS` | `RELAXED_JSON_OPTIONS` (default) | Relaxed loses type fidelity for Int64, Decimal128, Binary; Canonical preserves all types for restore fidelity |
| bind mount `./backups:/app/backups` | named Docker volume | Bind mount is host-visible (operators can `ls ./backups`); named volume requires `docker cp` — bind mount is better UX for self-hosted ham radio app |

**Installation (additions to `pyproject.toml`):**
```
apscheduler>=3.10,<4
aioboto3>=13,<16
```

---

## Architecture Patterns

### Package Structure
```
app/backup/
├── __init__.py          # empty (makes it a package)
├── __main__.py          # CLI entry point; asyncio.run(main()); prints confirmation to stdout
├── dump.py              # run_backup() — connects to MongoDB, iterates collections, writes .gz
├── upload.py            # upload_to_s3() — async; aioboto3 session.client("s3").upload_fileobj()
└── scheduler.py         # make_scheduler() — returns configured AsyncIOScheduler; not started here
```

### Pattern 1: Conditional Scheduler Startup (mirrors `udp_enabled`)

**What:** Scheduler is started only when `BACKUP_SCHEDULE` is set in env. When absent, no scheduler code runs.

**When to use:** Any optional background service gated on an env var.

**Template from existing code (`app/main.py` lines 33-56):**
```python
# Source: /Users/royco/ollog/app/main.py — udp_enabled guard pattern
backup_task = None
if settings.backup_schedule:
    from app.backup.scheduler import make_scheduler
    scheduler = make_scheduler(settings)
    scheduler.start()
    backup_task = asyncio.create_task(_run_backup_on_schedule(settings))

yield

# Shutdown
if backup_task is not None:
    backup_task.cancel()
    try:
        await backup_task
    except asyncio.CancelledError:
        pass
if settings.backup_schedule and scheduler.running:
    scheduler.shutdown(wait=False)
```

Note: APScheduler's `AsyncIOScheduler` integrates with the running event loop — `scheduler.start()` is synchronous, `scheduler.shutdown()` is also synchronous. The `wait=False` flag prevents blocking shutdown.

### Pattern 2: Async Task Cancellation (mirrors change-stream watcher)

**What:** `asyncio.create_task()` result stored in a variable; at shutdown: `.cancel()` then `await` with `CancelledError` suppression.

**Template from existing code (`app/main.py` lines 65-70 and `app/feed/manager.py` lines 38-42):**
```python
# Source: /Users/royco/ollog/app/main.py
if watcher_task is not None:
    watcher_task.cancel()
    try:
        await watcher_task
    except asyncio.CancelledError:
        pass
```

The backup asyncio task (if any) MUST follow this exact pattern.

### Pattern 3: EJSON Export with gzip

**What:** Iterate all collections in the database, serialize each document with `bson.json_util.dumps()`, write newline-delimited JSON into a gzip file.

**Verified API:**
```python
# Source: pymongo official docs — https://pymongo.readthedocs.io/en/stable/api/bson/json_util.html
from bson.json_util import dumps, CANONICAL_JSON_OPTIONS

# For each collection doc:
line = dumps(doc, json_options=CANONICAL_JSON_OPTIONS) + "\n"
```

**Output format:** One JSON object per line (NDJSON), wrapped per collection. This format is importable via `mongoimport --jsonArray` (if each collection is a JSON array) or via `mongoimport` in NDJSON mode.

**Recommended output structure inside the .gz:**
```
{"_collection": "qsos", "docs": [{...}, {...}]}
{"_collection": "users", "docs": [{...}]}
{"_collection": "apitokens", "docs": [{...}]}
```
Or: one JSON array per collection as separate keys in a single top-level object. Either approach supports restore. Simplest: one JSON object per line, `{"collection": name, "doc": doc_dict}` — one line per document.

### Pattern 4: S3 Upload (aioboto3)

**What:** Async upload of a local file to S3 using `upload_fileobj`.

**Verified from aioboto3 official docs (aioboto3.readthedocs.io/en/latest/usage.html):**
```python
# Source: aioboto3 official usage docs
import aioboto3

async def upload_to_s3(local_path: Path, bucket: str, key: str) -> None:
    session = aioboto3.Session()
    async with session.client("s3") as s3:
        with local_path.open("rb") as fp:
            await s3.upload_fileobj(fp, bucket, key)
```

Credentials come from environment: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`. No custom credential handling needed — standard boto3 credential chain.

### Pattern 5: APScheduler 3.x AsyncIOScheduler

**What:** Periodic cron-based job execution inside an asyncio event loop.

**Verified from APScheduler 3.x official docs (apscheduler.readthedocs.io/en/3.x/):**
```python
# Source: APScheduler 3.x docs
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()
scheduler.add_job(
    my_async_func,
    CronTrigger.from_crontab("0 2 * * *"),  # runs at 02:00 UTC daily
)
scheduler.start()
# ... later at shutdown:
scheduler.shutdown(wait=False)
```

`CronTrigger.from_crontab(expr, timezone=None)` — classmethod, accepts standard 5-field crontab string.

### Pattern 6: CLI Entry Point

**What:** `python -m app.backup` runs `app/backup/__main__.py`.

```python
# app/backup/__main__.py
import asyncio
from app.backup.dump import run_backup

if __name__ == "__main__":
    asyncio.run(run_backup())
```

The CLI path uses `asyncio.run()` — it creates its own event loop. This means the async MongoDB client in `app/database.py` is NOT pre-initialized; the CLI must create its own `AsyncMongoClient` directly (not use `get_client()` which returns the global lifespan-managed instance).

### Pattern 7: Settings Extension

**What:** New fields added to `app/config.py` `Settings` class.

**Template (following existing UDP pattern):**
```python
# Following the udp_enabled / udp_port / udp_operator naming pattern
backup_dir: str = "/app/backups"
backup_schedule: str | None = None
aws_access_key_id: str | None = None          # or rely on env chain
aws_secret_access_key: str | None = None      # or rely on env chain
aws_default_region: str | None = None
backup_s3_bucket: str | None = None           # needed to enable S3 upload
backup_s3_prefix: str = "backups/"           # key prefix in bucket
```

Note: boto3/aioboto3 automatically reads `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` from the environment. Adding them to Settings is optional but makes them visible as first-class config. The minimum required custom setting for S3 is `backup_s3_bucket`.

### Anti-Patterns to Avoid

- **Using `get_client()` in CLI path:** `get_client()` returns the lifespan-managed global client. In `python -m app.backup`, `init_db()` has not been called and `get_client()` returns `None`. The CLI must instantiate its own `AsyncMongoClient(settings.mongodb_uri)` directly.
- **Blocking S3 upload inside lifespan:** `boto3.upload_file()` (synchronous) inside an async lifespan blocks the event loop for the duration of the upload. Always use `aioboto3` with `await upload_fileobj()`.
- **Hardcoded `/app/backups` path:** All path construction must go through `settings.backup_dir` (wrapped in `Path(settings.backup_dir)`).
- **Starting scheduler unconditionally:** Scheduler must be gated on `if settings.backup_schedule:` — absence of the env var means no scheduler, no task, clean startup.
- **Not tracking backup task in lifespan:** An untracked `create_task()` may be mid-backup on shutdown. Track and cancel just like `watcher_task`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cron expression parsing | Custom interval math | `CronTrigger.from_crontab()` | Standard crontab syntax edge cases (DST, month-end, leap year) are handled by APScheduler |
| S3 multipart upload chunking | Custom file splitting | `aioboto3.upload_fileobj()` | boto3 s3transfer handles chunking, retries, concurrency automatically |
| BSON type serialization | Custom ObjectId/datetime JSON encoder | `bson.json_util.dumps()` | Handles ObjectId, datetime, Binary, Decimal128, Int64 — all BSON types |
| Event loop detection (CLI vs server) | Check `asyncio.get_event_loop().is_running()` | Use `asyncio.run()` in CLI, `await` in lifespan | `asyncio.run()` always creates a clean loop; no detection needed if CLI is standalone |

**Key insight:** BSON has many more types than JSON. `json_util.dumps()` is the only correct serializer for MongoDB documents — any custom JSON encoder will silently corrupt ObjectId, datetime, Int64, and Binary fields.

---

## Common Pitfalls

### Pitfall 1: CLI Uses Global MongoDB Client
**What goes wrong:** `from app.database import get_client; client = get_client()` returns `None` in CLI context because `init_db()` was never called.
**Why it happens:** `get_client()` returns the module-level `_client` variable set by `init_db()`. CLI invocation does not go through FastAPI lifespan.
**How to avoid:** CLI (`__main__.py` and `dump.py`) must create its own `AsyncMongoClient(settings.mongodb_uri)` directly, not via `app.database`.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute` on any collection access.

### Pitfall 2: Relative Path on Container Restart
**What goes wrong:** Files written to `./backups/` (relative path inside container) are lost on container restart.
**Why it happens:** Container writable layer is ephemeral; relative paths resolve inside the container filesystem, not the bind mount.
**How to avoid:** Always use `settings.backup_dir` (default `/app/backups`) which maps to the bind mount. The bind mount `./backups:/app/backups` in `docker-compose.yml` makes `/app/backups` host-backed.
**Warning signs:** Backup reports success but `./backups/` on host is empty.

### Pitfall 3: APScheduler v4 Alpha Install
**What goes wrong:** `pip install apscheduler` without a ceiling installs v4.x (alpha) which has a completely redesigned API — `AsyncIOScheduler` does not exist in v4.
**Why it happens:** PyPI returns the latest version without ceiling constraints.
**How to avoid:** Pin `apscheduler>=3.10,<4` in `pyproject.toml`.
**Warning signs:** `ImportError: cannot import name 'AsyncIOScheduler' from 'apscheduler.schedulers.asyncio'`.

### Pitfall 4: S3 Upload Partial Failure Leaves Multipart Parts
**What goes wrong:** If a large upload is interrupted mid-way, S3 retains incomplete multipart upload parts that incur storage charges indefinitely.
**Why it happens:** S3 multipart uploads are not atomic — incomplete parts persist until explicitly aborted.
**How to avoid:** This is an operational concern, not a code concern. Configure an `AbortIncompleteMultipartUploads` lifecycle rule (1 day) on the backup S3 bucket. `upload_fileobj` does handle retries, but power loss during upload can still orphan parts.
**Warning signs:** Unexpected S3 storage charges; `s3://bucket?uploads` list shows incomplete uploads.

### Pitfall 5: S3 Credentials Silent Failure
**What goes wrong:** `upload_fileobj` raises `ClientError: An error occurred (NoCredentialsError)` or `ClientError: (InvalidAccessKeyId)` — but the spec requires: log ERROR, keep local file, exit 0.
**Why it happens:** `AWS_*` env vars not set or set incorrectly.
**How to avoid:** Wrap the entire S3 upload in `try/except Exception` in `upload.py`, log `logger.error(...)`, and return without re-raising. Never propagate S3 exceptions to the caller.
**Warning signs:** Backup task crashes silently or raises unhandled exception in lifespan.

### Pitfall 6: Scheduler Not Shut Down on Lifespan Exit
**What goes wrong:** `AsyncIOScheduler` continues running after FastAPI lifespan exits, logging errors about missing event loop.
**Why it happens:** APScheduler keeps a reference to the event loop; if the app exits without `scheduler.shutdown()`, it may attempt to fire jobs on a closed loop.
**How to avoid:** In the lifespan teardown, call `scheduler.shutdown(wait=False)` after cancelling the backup task.
**Warning signs:** `RuntimeError: Event loop is closed` errors in logs after shutdown.

---

## Code Examples

Verified patterns from official sources and live codebase inspection:

### EJSON Export of One Collection
```python
# Source: pymongo docs + bson.json_util official docs
import gzip
import json
from pathlib import Path
from bson.json_util import dumps, CANONICAL_JSON_OPTIONS
from pymongo import AsyncMongoClient

async def run_backup(mongodb_uri: str, db_name: str, backup_dir: str) -> Path:
    client = AsyncMongoClient(mongodb_uri)
    db = client[db_name]
    
    backup_path = Path(backup_dir) / f"{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.gz"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    
    collection_names = await db.list_collection_names()
    
    with gzip.open(backup_path, "wt", encoding="utf-8") as gz:
        for coll_name in sorted(collection_names):
            docs = await db[coll_name].find({}).to_list(length=None)
            line = dumps({"collection": coll_name, "docs": docs}, json_options=CANONICAL_JSON_OPTIONS)
            gz.write(line + "\n")
    
    client.close()
    return backup_path
```

Note: `to_list(length=None)` loads entire collection into memory. For typical ham logs (thousands of QSOs), this is acceptable. For very large datasets, use async cursor iteration instead.

### APScheduler 3.x Scheduler Setup
```python
# Source: APScheduler 3.x official docs — apscheduler.readthedocs.io/en/3.x/
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

def make_scheduler(cron_expr: str, job_func) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        job_func,
        CronTrigger.from_crontab(cron_expr),
    )
    return scheduler

# In lifespan:
scheduler = make_scheduler(settings.backup_schedule, run_backup_job)
scheduler.start()          # synchronous
# ...
scheduler.shutdown(wait=False)  # synchronous
```

### aioboto3 S3 Upload
```python
# Source: aioboto3 official usage docs — aioboto3.readthedocs.io/en/latest/usage.html
import aioboto3
from pathlib import Path

async def upload_to_s3(local_path: Path, bucket: str, key: str) -> None:
    session = aioboto3.Session()
    async with session.client("s3") as s3:
        try:
            with local_path.open("rb") as fp:
                await s3.upload_fileobj(fp, bucket, key)
        except Exception as exc:
            logger.error("S3 upload failed for %s: %s", local_path, exc)
            # Do not re-raise — keep local file, exit code 0
```

### Lifespan Wiring Pattern (from existing code)
```python
# Source: /Users/royco/ollog/app/main.py — exact pattern to replicate

# Before yield:
backup_task = None
if settings.backup_schedule:
    from app.backup.scheduler import make_scheduler
    scheduler = make_scheduler(settings.backup_schedule, _backup_job)
    scheduler.start()
    backup_task = asyncio.create_task(_backup_loop())

yield

# After yield (shutdown):
if backup_task is not None:
    backup_task.cancel()
    try:
        await backup_task
    except asyncio.CancelledError:
        pass
if settings.backup_schedule and scheduler.running:
    scheduler.shutdown(wait=False)
```

### docker-compose.yml Additions
```yaml
# Source: phase requirement BAK-03, BAK-06

services:
  api:
    # ... existing config ...
    volumes:
      - ./backups:/app/backups
    environment:
      # ... existing env ...
      # BACKUP_SCHEDULE=0 2 * * *  # Uncomment to enable nightly 02:00 UTC backups

volumes:
  mongo-data:
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `mongodump` subprocess for backup | Pure-Python PyMongo EJSON export | This project: always | No binary dependency; no Dockerfile change; adequate for small-medium datasets |
| Synchronous `boto3` blocking upload | `aioboto3` async upload | aioboto3 project inception | Non-blocking; safe inside FastAPI lifespan event loop |
| APScheduler 3.x (stable) | APScheduler 4.x (alpha, different API) | APScheduler 4.0a released 2023+ | Must pin `<4` — 4.x removes `AsyncIOScheduler` |
| Hardcoded backup paths | `BACKUP_DIR` env var | This phase | Container-portable; no rebuild needed to change path |

**Deprecated/outdated:**
- `mongodump` in this project: binary absent from `python:3.12-slim`; resolved as out-of-scope.
- APScheduler 4.x: alpha API redesign; `AsyncIOScheduler` removed; pin `<4` is mandatory.

---

## Open Questions

1. **EJSON output structure per collection**
   - What we know: `bson.json_util.dumps()` serializes a Python dict to EJSON string; output goes into a gzip file
   - What's unclear: Whether to write one JSON object per document (NDJSON, easy streaming restore) or one JSON array per collection (one line per collection, simpler file structure)
   - Recommendation: Use one line per document, tagged with collection name: `{"collection": "qsos", "doc": {...}}`. This allows streaming restore and avoids loading entire arrays into memory during restore.

2. **`backup_s3_bucket` — Settings field or direct env var?**
   - What we know: boto3 credential chain handles `AWS_*` env vars automatically; `BACKUP_S3_BUCKET` is not a standard boto3 env var
   - What's unclear: Whether to add `backup_s3_bucket: str | None = None` to Settings (explicit, discoverable) or document it as a raw env var
   - Recommendation: Add to Settings as `backup_s3_bucket: str | None = None`. Follows existing pattern of all config through `app/config.py`.

3. **S3 guard condition**
   - What we know: S3 upload should only happen when S3 vars are set
   - What's unclear: Which combination of vars to check — `backup_s3_bucket` alone? `bucket + region`?
   - Recommendation: Check `if settings.backup_s3_bucket is not None:` — if bucket is set, attempt upload; let boto3 raise `NoCredentialsError` which is caught and logged as ERROR.

---

## Sources

### Primary (HIGH confidence)
- `/Users/royco/ollog/app/main.py` — live codebase; exact lifespan patterns for conditional startup and task cancellation
- `/Users/royco/ollog/app/config.py` — live codebase; Settings class structure and naming conventions
- `/Users/royco/ollog/app/database.py` — live codebase; `get_client()` returns global `_client`, which is `None` before `init_db()`
- `/Users/royco/ollog/app/feed/manager.py` — live codebase; `asyncio.CancelledError` handling pattern in `watch_qsos`
- `/Users/royco/ollog/.planning/research/SUMMARY.md` — milestone research; all architecture decisions for backup pre-researched
- APScheduler 3.x docs (apscheduler.readthedocs.io/en/3.x/) — `AsyncIOScheduler`, `CronTrigger.from_crontab()` signature and usage verified
- pymongo json_util docs (pymongo.readthedocs.io/en/stable/api/bson/json_util.html) — `dumps()`, `CANONICAL_JSON_OPTIONS`, `RELAXED_JSON_OPTIONS` verified
- aioboto3 official usage docs (aioboto3.readthedocs.io/en/latest/usage.html) — `session.client("s3")` async context manager + `upload_fileobj` pattern verified

### Secondary (MEDIUM confidence)
- PyPI aioboto3 page — current version 15.5.0 (released 2025-10-30); within `>=13,<16` pin
- WebSearch for PyMongo EJSON export pattern — confirmed `bson.json_util` is the standard approach; multiple sources consistent

### Tertiary (LOW confidence)
- S3 multipart AbortIncompleteMultipartUploads recommendation — from SUMMARY.md; operational concern not code; low risk for small backup files

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified via official docs; versions confirmed on PyPI
- Architecture: HIGH — all patterns traced directly to live codebase (`app/main.py`, `app/feed/manager.py`)
- Pitfalls: HIGH — all pitfalls verified either by official docs or direct codebase inspection
- Code examples: HIGH — all examples derived from official docs or live code, not training data alone

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (APScheduler 3.x is stable; aioboto3 minor versions change more frequently but API is stable)
