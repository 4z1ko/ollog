# Phase 37: Infrastructure and Backup Endpoint - Research

**Researched:** 2026-04-13
**Domain:** FastAPI FileResponse, asyncio.to_thread, Docker volume mounts, Python 3.12 datetime
**Confidence:** HIGH

## Summary

Phase 37 is a wiring phase: the backup engine (`run_backup` in `app/backup/dump.py`) is fully operational and is already used by the CLI (`python -m app.backup`) and the APScheduler nightly job. The phase adds three things: a Docker volume mount in `docker-compose.yml`, a new `GET /admin/ui/backup/download` route in `app/admin/ui_router.py`, and a one-line deprecation fix in `dump.py`. No new dependencies are required.

The critical implementation decision concerns `asyncio.to_thread()`. BACK-03 and the STATE.md both mandate `asyncio.to_thread(run_backup, settings)`, but `run_backup` is currently declared `async def`. `asyncio.to_thread` wraps **synchronous** callables only — passing an async coroutine to it is incorrect. The blocking I/O (`gzip.open`, `gz.write`) lives inside the async coroutine where it does block the event loop. The resolution: `run_backup` must be split into a sync helper that handles the gzip write (wrappable with `to_thread`) while the MongoDB `await` calls stay in an outer async orchestrator. Alternatively, the entire dump function can be made synchronous using pymongo's sync `MongoClient` (already a dependency: `pymongo>=4.16.0`). Either approach satisfies BACK-03; the planner must choose and specify one explicitly.

All other aspects are straightforward: `require_admin_cookie` is already implemented and tested, `FileResponse` automatically sets `Content-Disposition: attachment` when given a `filename=` parameter, and the `./backups` volume mount only needs adding to the `admin` service (the `api` service already has it).

**Primary recommendation:** Split `run_backup` into a sync `_write_backup(settings) -> Path` (gzip I/O, sync MongoClient) wrapped in `asyncio.to_thread`, with the S3 upload path remaining `async`. This matches the stated architecture intent while correctly using `to_thread` on a sync callable.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.135.0 | `FileResponse`, router, `Depends` | Already the project web framework |
| fastapi.responses.FileResponse | (bundled) | Stream file with `Content-Disposition: attachment` | Sets all required headers automatically |
| asyncio.to_thread | stdlib (Python 3.9+) | Run sync blocking I/O in thread pool | Prevents blocking uvicorn event loop |
| pymongo | >=4.16.0 | Sync `MongoClient` for use inside `to_thread` | Already a project dependency; sync client required for thread context |
| datetime.now(timezone.utc) | stdlib | UTC-aware timestamp (Python 3.12+ safe) | Replaces deprecated `datetime.utcnow()` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pathlib.Path | stdlib | File path manipulation | Already used in `dump.py` for backup_path.stem |
| gzip | stdlib | Compressed NDJSON backup format | Already used in `dump.py` |
| bson.json_util | (pymongo bundled) | EJSON encoding for MongoDB documents | Already used in `dump.py` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sync MongoClient inside `to_thread` | Refactor to pure async with `aiofiles` | `aiofiles` is not in dependencies; adds a dependency for a marginal gain |
| sync MongoClient inside `to_thread` | `await run_backup(settings)` directly (no `to_thread`) | Violates BACK-03; blocks event loop during gzip write |

**Installation:** No new packages required. All dependencies already in `pyproject.toml`.

---

## Architecture Patterns

### Files Touched

```
docker-compose.yml              # Add volume mount to admin service
app/backup/dump.py              # datetime fix + sync/async refactor for to_thread
app/admin/ui_router.py          # New GET /admin/ui/backup/download endpoint
```

### Pattern 1: Docker Volume Mount

**What:** Add `- ./backups:/app/backups` to the `admin` service `volumes` block in `docker-compose.yml`
**When to use:** Any service that needs to read or write files that must survive container restarts

Current state in `docker-compose.yml` — `api` service has the mount, `admin` service does not:
```yaml
# api service (already correct)
volumes:
  - ./backups:/app/backups

# admin service (currently missing volumes: block — add it)
volumes:
  - ./backups:/app/backups
```

### Pattern 2: FileResponse with Timestamped Filename

**What:** Return a `FileResponse` that triggers browser file-save dialog with a human-readable timestamped filename
**When to use:** Any endpoint that delivers a file download to a browser

```python
# Source: https://fastapi.tiangolo.com/advanced/custom-response/#fileresponse
from fastapi.responses import FileResponse

return FileResponse(
    path=backup_path,
    media_type="application/gzip",
    filename=f"ollog-backup-{backup_path.stem}.gz",
)
```

`backup_path.stem` is the filename without extension (e.g. `20260413T153042Z`), so the browser receives `ollog-backup-20260413T153042Z.gz`. `FileResponse` automatically adds `Content-Disposition: attachment; filename="..."`.

**Note on BACK-04 filename format:** The requirement says `YYYY-MM-DD-HH-MM-SS` (human-readable with hyphens). The current `dump.py` generates `%Y%m%dT%H%M%SZ` (compact ISO-8601). The `datetime.now(timezone.utc)` fix in BACK-05 is the right time to also change the `strftime` format string to `%Y-%m-%dT%H-%M-%SZ` or similar if human-readability is needed. Verify the intended filename format against BACK-04.

### Pattern 3: asyncio.to_thread Wrapping Sync I/O

**What:** Run a synchronous blocking function in the default thread pool executor without blocking the uvicorn event loop
**When to use:** Any sync blocking I/O (file writes, sync DB calls) called from an async route handler

```python
# Source: https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread
import asyncio

# CORRECT: pass a sync callable
backup_path = await asyncio.to_thread(sync_run_backup, settings)

# INCORRECT: do not pass an async coroutine to to_thread
# backup_path = await asyncio.to_thread(run_backup, settings)  # run_backup is async def
```

**The refactor needed in `dump.py`:** The gzip write and pymongo sync calls must be extracted into a `def _write_backup(settings) -> Path` (sync, uses `pymongo.MongoClient`). The outer `async def run_backup(settings)` then becomes:

```python
async def run_backup(settings) -> Path:
    backup_path = await asyncio.to_thread(_write_backup, settings)
    if settings.backup_s3_bucket is not None:
        from app.backup.upload import upload_to_s3
        key = f"{settings.backup_s3_prefix}{backup_path.name}"
        await upload_to_s3(backup_path, settings.backup_s3_bucket, key)
    return backup_path
```

### Pattern 4: require_admin_cookie Dependency

**What:** Protect a route with the admin cookie JWT dependency, not Bearer token
**When to use:** Every admin UI route — browser sends cookie, not `Authorization: Bearer`

```python
# Source: app/auth/dependencies.py (already in codebase)
from app.auth.dependencies import require_admin_cookie
from app.auth.models import User

@ui_router.get("/backup/download")
async def backup_download(
    _user: User = Depends(require_admin_cookie),
):
    ...
```

### Anti-Patterns to Avoid

- **Using `require_admin` (Bearer) on UI routes:** Browser does not send `Authorization: Bearer`. Causes 401 → 302 to login page silently, with no indication of the real problem. Use `require_admin_cookie` exclusively.
- **Passing async coroutine to `asyncio.to_thread`:** `asyncio.to_thread` calls `func(*args, **kwargs)` in a thread. If `func` is an async function, calling it returns a coroutine object, not a result — the coroutine is never awaited. The thread returns the coroutine object and the route gets a `Path`-shaped coroutine, not a `Path`. This is a silent bug.
- **HTMX on the download link (Phase 38 concern, noted here):** If Phase 38 adds a download button with any `hx-*` attribute, HTMX will intercept the response. `Content-Disposition: attachment` is silently ignored, the binary payload is discarded, and the button appears to do nothing. The anchor must be a plain `<a href>` with no HTMX attributes.
- **Testing endpoint without volume mount:** The download works within the same container request even without the volume mount (file is on the overlay filesystem). The bug only surfaces after `docker compose down`. Always verify the volume mount before declaring the endpoint working.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Content-Disposition header | Manual header dict | `FileResponse(filename=...)` | FastAPI sets `Content-Disposition`, `Content-Length`, `Last-Modified`, `ETag` automatically |
| Thread pool execution | `concurrent.futures.ThreadPoolExecutor` | `asyncio.to_thread()` | `to_thread` propagates contextvars, integrates with the running event loop, is the stdlib-standard approach since Python 3.9 |
| UTC timestamp | `datetime.utcnow()` | `datetime.now(timezone.utc)` | `utcnow()` deprecated in Python 3.12, returns naive datetime (no tzinfo), scheduled for removal |

**Key insight:** `FileResponse` handles the entire file delivery protocol. The route handler only needs to produce the file path; `FileResponse` handles chunked streaming, correct headers, and cleanup.

---

## Common Pitfalls

### Pitfall 1: asyncio.to_thread Called with Async Function

**What goes wrong:** `await asyncio.to_thread(run_backup, settings)` appears to work (no exception) but the thread receives an unawaited coroutine instead of executing the backup. The route returns normally but no backup file is created or the file is empty.
**Why it happens:** `asyncio.to_thread` calls `func(*args)` synchronously in a thread. If `func` is `async def`, calling it returns a coroutine object without running it. The coroutine is never scheduled on the event loop.
**How to avoid:** Only pass `def` (sync) functions to `asyncio.to_thread`. The refactor of `dump.py` must produce a sync `_write_backup` function.
**Warning signs:** No exception raised, no backup file on disk, or a zero-byte backup file.

### Pitfall 2: Volume Mount Missing from admin Service

**What goes wrong:** Backup downloads successfully within a session, files appear in `/app/backups` inside the container. After `docker compose down && docker compose up`, the backups directory in the admin container is empty.
**Why it happens:** Without the volume mount, files are written to the container's ephemeral overlay filesystem. The `api` service already has `- ./backups:/app/backups` but `admin` service does not.
**How to avoid:** Add `volumes: [- ./backups:/app/backups]` to the `admin` service in `docker-compose.yml` before any endpoint testing.
**Warning signs:** `ls ./backups/` on the host shows no files after a download.

### Pitfall 3: datetime.utcnow() DeprecationWarning in Python 3.12

**What goes wrong:** Backup generation emits `DeprecationWarning: datetime.datetime.utcnow() is deprecated` in server logs. In Python 3.14 (which is installed on this system), this becomes a removal and will raise `AttributeError`.
**Why it happens:** `datetime.utcnow()` was deprecated in Python 3.12 and removed in 3.14. The Dockerfile uses `python:3.12-slim`, so the container is safe for now, but local development on Python 3.14 will break.
**How to avoid:** Replace `datetime.utcnow().strftime(...)` with `datetime.now(timezone.utc).strftime(...)` in `dump.py`. Import `timezone` from `datetime`.
**Warning signs:** `DeprecationWarning` in server logs; `AttributeError: type object 'datetime.datetime' has no attribute 'utcnow'` on Python 3.14+.

### Pitfall 4: Filename Format Mismatch (BACK-04 vs Current Implementation)

**What goes wrong:** BACK-04 specifies `YYYY-MM-DD-HH-MM-SS` format (e.g. `ollog-backup-2026-04-14-15-30-42.gz`). Current `dump.py` generates `%Y%m%dT%H%M%SZ` (compact: `20260413T153042Z`). These are different formats.
**Why it happens:** The strftime format in `dump.py` predates BACK-04. The `filename=f"ollog-backup-{backup_path.stem}.gz"` pattern inherits whatever format `dump.py` uses.
**How to avoid:** When fixing `datetime.utcnow()` in `dump.py` (BACK-05), also update the `strftime` format string. The `backup_path.stem` approach still works — change the format in `dump.py` and the `FileResponse` filename automatically matches.
**Warning signs:** Downloaded file named `ollog-backup-20260413T153042Z.gz` instead of `ollog-backup-2026-04-13-15-30-42.gz`.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### Backup Download Endpoint

```python
# Placement: app/admin/ui_router.py, after existing routes
import asyncio
from fastapi.responses import FileResponse
from app.backup.dump import run_backup
from app.config import settings

@ui_router.get("/backup/download")
async def backup_download(
    _user: User = Depends(require_admin_cookie),
):
    """Trigger a full MongoDB backup and return it as a .gz file download."""
    backup_path = await asyncio.to_thread(_sync_run_backup, settings)
    return FileResponse(
        path=backup_path,
        media_type="application/gzip",
        filename=f"ollog-backup-{backup_path.stem}.gz",
    )
```

### datetime.utcnow() Fix in dump.py

```python
# Before (deprecated):
from datetime import datetime
backup_path = (
    Path(settings.backup_dir)
    / f"{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.gz"
)

# After (Python 3.12+ safe):
from datetime import datetime, timezone
backup_path = (
    Path(settings.backup_dir)
    / f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ')}.gz"
)
# Note: strftime format also updated to match BACK-04 human-readable requirement
```

### Docker Compose Volume Mount

```yaml
# In docker-compose.yml, admin service:
admin:
  build: .
  command: uvicorn app.admin_main:app --host 0.0.0.0 --port 8001
  ports:
    - "8001:8001"
  profiles:
    - admin
  depends_on:
    mongodb:
      condition: service_healthy
  env_file: .env
  environment:
    - MONGODB_URI=mongodb://mongodb:27017/?replicaSet=rs0
    - MONGODB_DB=ollog
  volumes:
    - ./backups:/app/backups   # ADD THIS LINE
```

### Sync Run Backup for asyncio.to_thread

```python
# In app/backup/dump.py — new sync helper (uses pymongo sync MongoClient)
import gzip
from datetime import datetime, timezone
from pathlib import Path

from bson.json_util import dumps, CANONICAL_JSON_OPTIONS
from pymongo import MongoClient  # sync client, not AsyncMongoClient

def _write_backup(settings) -> Path:
    """Synchronous backup writer — safe to call from asyncio.to_thread()."""
    client = MongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    
    backup_path = (
        Path(settings.backup_dir)
        / f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ')}.gz"
    )
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with gzip.open(backup_path, "wt", encoding="utf-8") as gz:
            for coll_name in sorted(db.list_collection_names()):
                docs = list(db[coll_name].find({}))
                for doc in docs:
                    line = (
                        dumps(
                            {"collection": coll_name, "doc": doc},
                            json_options=CANONICAL_JSON_OPTIONS,
                        )
                        + "\n"
                    )
                    gz.write(line)
    finally:
        client.close()
    
    return backup_path
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Python 3.12 deprecated, 3.14 removed | Phase 37 must fix; local dev uses Python 3.14 |
| `AsyncMongoClient` in dump.py | `MongoClient` (sync) in `_write_backup` | Phase 37 refactor | Required to make `asyncio.to_thread` work correctly |
| No `volumes:` in admin service | `- ./backups:/app/backups` | Phase 37 adds | Without it, backups lost on container restart |

**Deprecated/outdated:**
- `datetime.utcnow()`: deprecated Python 3.12, removed Python 3.14. The host environment runs Python 3.14. Fix in Phase 37.

---

## Open Questions

1. **asyncio.to_thread with async run_backup — resolution approach**
   - What we know: `run_backup` is `async def` containing blocking `gzip.open`/`gz.write`. `asyncio.to_thread` requires a sync callable. The requirement (BACK-03) mandates `to_thread`.
   - What's unclear: The planner must decide whether to (a) extract a sync `_write_backup` helper using `pymongo.MongoClient`, keeping `run_backup` as an async orchestrator, or (b) restructure differently.
   - Recommendation: Option (a) — extract `_write_backup(settings) -> Path` as a sync `def` using `pymongo.MongoClient`. Keep `async def run_backup(settings)` as the public API for CLI and scheduler (it calls `await asyncio.to_thread(_write_backup, settings)` + async S3 upload). This is backward-compatible and satisfies BACK-03.

2. **strftime format for BACK-04 compliance**
   - What we know: BACK-04 requires `YYYY-MM-DD-HH-MM-SS`. Current format is `%Y%m%dT%H%M%SZ`. The `FileResponse` filename derives from `backup_path.stem`.
   - What's unclear: The exact target format string (should it be `%Y-%m-%dT%H-%M-%SZ` or `%Y-%m-%d-%H-%M-%S`?).
   - Recommendation: Use `%Y-%m-%dT%H-%M-%SZ` which produces `2026-04-13T15-30-42Z` — human-readable, sortable, and unambiguous. The planner should confirm against BACK-04 wording.

3. **Existing tests for dump.py**
   - What we know: No tests directory for backup (`tests/backup/` does not exist). The CLI and scheduler use `run_backup` but there are no pytest tests for it.
   - What's unclear: Whether BACK-03 verification can be achieved with unit tests or only by manual curl verification.
   - Recommendation: Add a minimal test that verifies the backup endpoint returns 200 with `Content-Disposition: attachment`. Mock `asyncio.to_thread` or use the admin_main app directly. Follow the pattern in `test_adif_export.py`.

---

## Sources

### Primary (HIGH confidence)
- Codebase direct inspection — `app/backup/dump.py`, `app/admin/ui_router.py`, `app/auth/dependencies.py`, `app/config.py`, `docker-compose.yml`, `pyproject.toml`
- `.planning/STATE.md` — v2.0 critical implementation rules and architecture decisions
- `.planning/REQUIREMENTS.md` — BACK-01 through BACK-05, INFRA-01 verbatim requirements
- `https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread` — asyncio.to_thread added Python 3.9, signature, threading behavior
- `https://docs.python.org/3/library/datetime.html` — `datetime.utcnow()` deprecated Python 3.12
- `https://fastapi.tiangolo.com/advanced/custom-response/#fileresponse` — FileResponse parameters, Content-Disposition behavior

### Secondary (MEDIUM confidence)
- Python 3.14 local environment verification — `asyncio.to_thread` confirmed available, `datetime.utcnow` confirmed removed

---

## Metadata

**Confidence breakdown:**
- Docker volume mount: HIGH — direct inspection of `docker-compose.yml`; `api` service has the pattern, `admin` does not
- FileResponse behavior: HIGH — official FastAPI docs confirmed; matches existing usage in codebase
- asyncio.to_thread: HIGH — official Python docs; Python 3.9+; confirmed available in current environment
- datetime fix: HIGH — official Python docs; `utcnow()` deprecated 3.12, removed 3.14; confirmed by local Python 3.14 installation
- asyncio.to_thread/async mismatch: HIGH — confirmed by reading `dump.py`; `run_backup` is `async def`; documented as open question

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable domain — FastAPI, stdlib asyncio, Docker Compose)
