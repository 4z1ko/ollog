# Stack Research: v1.8 Admin Container, DB Backup, Docs Rewrite

**Domain:** ollog v1.8 — three new capabilities added to an existing FastAPI + Beanie + HTMX stack
**Researched:** 2026-04-10
**Confidence:** HIGH for mongodump CLI, Docker Compose profiles, FastAPI app factory, APScheduler 3. MEDIUM for aioboto3 (well-documented but version pinning requires care).

---

## Summary

v1.8 adds three orthogonal capabilities to the existing stack. The findings below confirm:

1. **mongodump subprocess** — a single `subprocess.run()` call with `--archive=<path> --gzip` produces a `.gz` file directly; no streaming or piping needed. This is entirely within Python stdlib.

2. **Cron scheduling** — APScheduler 3.x (`AsyncIOScheduler` + `CronTrigger.from_crontab()`) is the right fit. It plugs into the existing lifespan pattern with zero architectural change. APScheduler 4 is in alpha and has a fully redesigned API; avoid it until stable.

3. **S3 uploads** — `aioboto3` (async wrapper around boto3) is recommended over raw `boto3 + run_in_executor`. For a scheduled background task uploading a single file, the perf difference is negligible, but aioboto3 keeps the code idiomatic async and avoids thread-pool concerns in a long-running ASGI process.

4. **Admin container split** — Docker Compose `profiles` feature handles the optional second service cleanly. A `create_app(mode)` factory function in `app/main.py` selectively calls `include_router` based on a `APP_MODE` env var. No second Dockerfile needed.

5. **Docs rewrite** — MkDocs Material is already installed. This milestone is purely content work; no stack additions.

**Net new dependencies:** `APScheduler==3.*`, `aioboto3>=13`

---

## 1. mongodump via Python subprocess

### Command that produces a single .gz archive

```bash
mongodump \
  --uri="mongodb://mongodb:27017/?replicaSet=rs0" \
  --db=ollog \
  --archive=/backups/20260410T020000.gz \
  --gzip
```

- `--archive=<filepath>` writes a binary archive to a file (not a directory tree)
- `--gzip` compresses every collection stream inside the archive
- Combined: produces a self-contained, mongorestore-compatible `.gz` file
- Without a filename argument (`--archive` alone with no `=`), mongodump writes to stdout — always provide an explicit path

**Python subprocess pattern (synchronous, called from an async context via `asyncio.to_thread`):**

```python
import subprocess
from pathlib import Path
from datetime import datetime, timezone

def run_mongodump(uri: str, db: str, backup_dir: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = backup_dir / f"{ts}.gz"
    backup_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            "mongodump",
            f"--uri={uri}",
            f"--db={db}",
            f"--archive={out_path}",
            "--gzip",
        ],
        capture_output=True,
        check=False,   # check manually to surface stderr in logs
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"mongodump failed (rc={result.returncode}): "
            f"{result.stderr.decode(errors='replace')}"
        )
    return out_path
```

**Important:** `mongodump` must be present in the container's `PATH`. The `mongo:7` image in the existing compose file does NOT include database tools — add a separate install step or use `mongo/mongodb-database-tools` in the Dockerfile. See pitfall below.

**Calling from async context:**

```python
out_path = await asyncio.to_thread(run_mongodump, uri, db, backup_dir)
```

`asyncio.to_thread` (Python 3.9+, available in this project's Python 3.12 base) runs the blocking call in the default thread pool without blocking the event loop.

**Confidence:** HIGH — command syntax from MongoDB official docs. `subprocess.run` with `capture_output=True` is Python stdlib.

**Sources:**
- [mongodump — MongoDB Database Tools](https://www.mongodb.com/docs/database-tools/mongodump/)
- [mongodump Examples — MongoDB Database Tools](https://www.mongodb.com/docs/database-tools/mongodump/mongodump-examples/)

---

## 2. Cron Scheduling in an ASGI App

### Recommendation: APScheduler 3.x (`AsyncIOScheduler`)

**Why APScheduler 3 over alternatives:**

| Option | Verdict | Reason |
|--------|---------|--------|
| APScheduler 3.x `AsyncIOScheduler` | **Use this** | Stable, production-used, native asyncio, plugs into lifespan, `CronTrigger.from_crontab()` parses a full cron string directly |
| APScheduler 4.x `AsyncScheduler` | Avoid for now | Full API redesign (ground-up rewrite), currently at `4.0.0a6` (alpha as of April 2025). Breaking changes: jobs must use async context manager, AnyIO dependency added, job stores incompatible with 3.x |
| `croniter` + manual `asyncio.sleep` | Avoid | More code, no built-in missed-job handling, reinventing the wheel |
| `aiocron` | Avoid | Switched from `croniter` to `cronsim` in Dec 2024, smaller ecosystem, less documentation than APScheduler |
| Celery Beat | Overkill | Requires a broker (Redis/RabbitMQ); the project has no existing task queue |

### Integration pattern with existing lifespan

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # ... existing startup ...

    backup_schedule = settings.backup_schedule  # e.g. "0 2 * * *"
    if backup_schedule:
        scheduler.add_job(
            run_backup_job,
            trigger=CronTrigger.from_crontab(backup_schedule),
            id="s3_backup",
            replace_existing=True,
        )
        scheduler.start()

    yield

    if scheduler.running:
        scheduler.shutdown(wait=False)
    # ... existing teardown ...
```

**`CronTrigger.from_crontab(expr)`** — class method available since APScheduler 3.x; accepts a standard 5-field cron string (`"0 2 * * *"`, `"*/30 * * * *"`, etc.). Confirmed in 3.11.2.post1 docs. This is exactly what the `BACKUP_SCHEDULE` env var needs.

**Add `backup_schedule` to `app/config.py`:**

```python
backup_schedule: str | None = None   # e.g. "0 2 * * *"
```

**Install:**

```
apscheduler>=3.10,<4
```

Pin to `<4` to prevent accidental upgrade to the redesigned v4 alpha series.

**Confidence:** HIGH — APScheduler 3 docs confirm `AsyncIOScheduler` + `CronTrigger.from_crontab()`. MEDIUM on the `<4` ceiling advisory (v4 alpha confirmed in PyPI, still pre-release as of research date).

**Sources:**
- [APScheduler 3.x User Guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html)
- [APScheduler CronTrigger docs](https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html)
- [APScheduler 4.0 Migration Guide](https://apscheduler.readthedocs.io/en/master/migration.html)
- [APScheduler on PyPI](https://pypi.org/project/APScheduler/)

---

## 3. S3 Uploads: aioboto3 vs boto3

### Recommendation: `aioboto3`

**Why not plain `boto3`:**

boto3 uses blocking I/O. In an ASGI process running on a single event loop, blocking calls stall all other requests for the duration. The canonical workaround is `asyncio.loop.run_in_executor(None, ...)`, but this adds boilerplate and the thread-pool sizing must be managed manually. For a long-running server process this is a latent issue, not just a style preference.

**Why aioboto3:**

- Drop-in async equivalent of boto3 (same method names, same kwargs)
- Built on `aiobotocore`, which is the aio-libs-maintained async botocore backend
- `upload_fileobj()` is natively async — no executor needed
- Supports Python 3.12+ (confirmed: versions 13–15.x explicitly support Python 3.12, 3.13, 3.14)
- Latest stable: 15.5.0 (October 2025)

**Pattern for uploading the backup file:**

```python
import aioboto3
from pathlib import Path

async def upload_to_s3(
    local_path: Path,
    bucket: str,
    key: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
    aws_region: str,
    endpoint_url: str | None = None,   # for S3-compatible stores
) -> None:
    session = aioboto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region,
    )
    async with session.client("s3", endpoint_url=endpoint_url) as s3:
        with local_path.open("rb") as f:
            await s3.upload_fileobj(f, bucket, key)
```

**Note:** `.client()` and `.resource()` must be used as async context managers in aioboto3 v11+. Earlier `boto3.client()` style (non-context-manager) no longer works.

**Env vars to add to `app/config.py`:**

```python
aws_access_key_id: str | None = None
aws_secret_access_key: SecretStr | None = None
aws_region: str = "us-east-1"
aws_s3_bucket: str | None = None
aws_s3_key_prefix: str = "backups/"
aws_s3_endpoint_url: str | None = None  # S3-compatible (Backblaze, MinIO, etc.)
```

**Install:**

```
aioboto3>=13,<16
```

Pin upper bound to `<16` to stay within the tested range. The major version tracks aiobotocore, which tracks botocore; major version bumps may include auth or API changes.

**Confidence:** MEDIUM-HIGH — aioboto3 API confirmed in official docs and PyPI. The `upload_fileobj` async pattern confirmed in library source. Version pinning recommendation is conservative.

**Sources:**
- [aioboto3 on PyPI](https://pypi.org/project/aioboto3/)
- [aioboto3 Usage Docs](https://aioboto3.readthedocs.io/en/latest/usage.html)
- [aiobotocore S3 Basic Usage](https://aiobotocore.aio-libs.org/en/latest/examples/s3/basic_usage.html)
- [aioboto3 GitHub — terricain/aioboto3](https://github.com/terricain/aioboto3)

---

## 4. Docker Compose Profiles for Optional Admin Service

### How Compose profiles work

Services **without** a `profiles` key always start with `docker compose up`. Services **with** a `profiles` key only start when that profile is explicitly activated.

Activation methods:
- CLI flag: `docker compose --profile admin up`
- Env var: `COMPOSE_PROFILES=admin docker compose up`
- `.env` file: `COMPOSE_PROFILES=admin`

### Recommended compose.yml shape for v1.8

```yaml
services:
  mongodb:
    # no profiles key — always starts
    image: mongo:7
    ...

  api:
    # no profiles key — always starts (port 8000, operator routes only)
    build: .
    ports:
      - "8000:8000"
    environment:
      - APP_MODE=operator
    ...

  admin:
    # profiles key — only starts when 'admin' profile is active
    build: .          # same image as api
    profiles: [admin]
    ports:
      - "8001:8001"
    environment:
      - APP_MODE=admin
    command: ["uvicorn", "app.main:create_app_admin", "--host", "0.0.0.0", "--port", "8001"]
    depends_on:
      mongodb:
        condition: service_healthy
    ...
```

**Key points:**
- `mongodb` and `api` have no `profiles` key → always start
- `admin` has `profiles: [admin]` → opt-in only
- Both `api` and `admin` use the same `build: .` image — one Dockerfile
- Differentiation is by `APP_MODE` env var and/or `command` override

**Profile activation for operators deploying the admin container:**

```bash
docker compose --profile admin up -d
```

Or persistently in `.env`:

```
COMPOSE_PROFILES=admin
```

**Caveats:**
- There is a documented edge case (Docker Compose v5.0.1, January 2026 GitHub issue) where `COMPOSE_PROFILES` env var was ignored in WSL2. The `--profile` flag always works. For production deployments, prefer the `--profile` CLI flag or set `COMPOSE_PROFILES` in a file rather than as a shell export.
- The admin service must not have `container_name` that conflicts with the api service, even though they use the same image.

**Confidence:** HIGH — Docker official docs confirm the profiles semantics. The WSL2 edge case is flagged as LOW confidence (single issue report, unclear if resolved).

**Sources:**
- [Docker Compose — Use service profiles](https://docs.docker.com/compose/how-tos/profiles/)
- [Docker Compose — Profiles reference](https://docs.docker.com/reference/compose-file/profiles/)

---

## 5. FastAPI App Factory for Selective Router Mounting

### Pattern: `create_app(mode)` factory function

The cleanest approach for running admin routes on port 8001 from the same codebase is a factory function that takes a mode string and conditionally calls `include_router`.

```python
# app/main.py

def create_app(mode: str = "operator") -> FastAPI:
    app = FastAPI(title="ollog", lifespan=lifespan)

    # Always-included routers (shared across both modes)
    app.include_router(auth_router)
    app.include_router(health_router)

    if mode == "operator":
        app.include_router(qso_router)
        app.include_router(qso_ui_router, include_in_schema=False)
        app.include_router(adif_router)
        app.include_router(feed_router, include_in_schema=False)
        app.include_router(profile_router)
        app.include_router(token_router)
        app.mount("/guide", StaticFiles(directory="site", html=True), name="guide")
        app.mount("/static", StaticFiles(directory="static"), name="static")

    elif mode == "admin":
        app.include_router(admin_router)
        app.include_router(admin_ui_router, include_in_schema=False)
        app.mount("/static", StaticFiles(directory="static"), name="static")

    return app

# Module-level app objects for uvicorn entrypoints:
app = create_app(mode=os.getenv("APP_MODE", "operator"))
```

**Two uvicorn entrypoints, one codebase:**

```bash
# Operator (port 8000):
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Admin (port 8001):
APP_MODE=admin uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Uvicorn imports `app.main`, which evaluates `create_app(os.getenv("APP_MODE", "operator"))` at module load time. The env var is read once at startup — this is correct and idiomatic.

**Alternative: callable app entrypoint**

Uvicorn supports a `app:create_app` factory callable with `--factory` flag:

```bash
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8001
```

However, this does not allow passing arguments from env vars cleanly. The module-level `app = create_app(...)` pattern is simpler and more readable.

**Lifespan considerations:**

`lifespan` is defined on the `FastAPI` instance, not on `APIRouter`. Both the operator app and the admin app will run their own `lifespan` — each will call `init_db()`, start the watcher, etc. This is correct: the admin container is a separate process and needs its own DB connection. The UDP server should be gated by `settings.udp_enabled` (already is), so it will not start in the admin container unless explicitly configured.

**Confidence:** HIGH — FastAPI `include_router` is standard and well-documented. The module-level factory pattern is confirmed in the FastAPI best-practices community. Lifespan behavior per-app-instance is confirmed (FastAPI docs note lifespan only runs on `FastAPI`, not `APIRouter`).

**Sources:**
- [FastAPI — Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [FastAPI Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/)
- [FastAPI app factory discussion](https://github.com/fastapi/fastapi/discussions/6302)

---

## 6. MkDocs Material — Docs Rewrite

No new stack additions needed. `mkdocs-material==9.*` is already in the `[dependency-groups] dev` section of `pyproject.toml` and installed in the virtualenv (`mkdocs_material-9.7.6.dist-info` confirmed in `.venv`).

The v1.8 docs work is content-only:
- Update `mkdocs.yml` nav structure to reflect v1.0–v1.8 features
- Rewrite `.md` files under the `docs/` directory
- `mkdocs build` produces the `site/` directory which is already mounted at `/guide` in `app/main.py`

No library research required for this capability.

---

## Recommended Stack Additions (pyproject.toml diff)

```toml
dependencies = [
    # ... existing ...
    "apscheduler>=3.10,<4",
    "aioboto3>=13,<16",
]
```

**What is NOT needed:**

| Considered | Decision | Reason |
|-----------|----------|--------|
| `croniter` | Skip | APScheduler includes its own cron parsing via `CronTrigger.from_crontab()` |
| `aiocron` | Skip | Less mature than APScheduler; recently swapped cron parser library |
| `boto3` (sync) | Skip | Would require `run_in_executor` boilerplate to avoid blocking the event loop |
| `aiobotocore` (direct) | Skip | aioboto3 wraps aiobotocore and provides the higher-level `upload_fileobj()` API |
| APScheduler 4.x | Skip | Alpha software, fully breaking API vs 3.x, no stable release yet |
| `motor` | Skip | Already using Beanie which wraps motor; no direct motor usage needed |
| `python-crontab` | Skip | OS-level crontab editor; not relevant for in-process scheduling |

---

## Pitfall: mongodump Not in the App Container

The existing Dockerfile builds a Python application image, not a MongoDB image. `mongodump` is a separate tool from the MongoDB Database Tools package — it is NOT included in `mongo:7` image and NOT in standard Python base images.

**Required Dockerfile addition:**

For Debian/Ubuntu-based Python images:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnupg curl && \
    curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
        gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg && \
    echo "deb [ arch=amd64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
        https://repo.mongodb.org/apt/debian bookworm/mongodb-org/7.0 main" \
        > /etc/apt/sources.list.d/mongodb-org-7.0.list && \
    apt-get update && apt-get install -y --no-install-recommends \
        mongodb-database-tools && \
    rm -rf /var/lib/apt/lists/*
```

This installs `mongodump`, `mongorestore`, `mongoexport`, etc. as system tools accessible from `subprocess.run(["mongodump", ...])`. The version must match the server version (7.0 in the current stack).

The `app/backup.py` module should verify `mongodump` is on PATH at startup and fail fast with a clear error message rather than failing silently at backup time.

---

## Complete Dependency Summary

| Package | Version Pin | Purpose | Confidence |
|---------|-------------|---------|------------|
| `apscheduler` | `>=3.10,<4` | Cron scheduler (`AsyncIOScheduler`, `CronTrigger.from_crontab`) | HIGH |
| `aioboto3` | `>=13,<16` | Async S3 upload (`upload_fileobj`) | MEDIUM-HIGH |
| `mongodump` (system tool) | MongoDB 7.0 (match server) | Subprocess backup invocation | HIGH |

All other v1.8 capabilities use existing dependencies or Docker Compose config.

---

## Sources

- [mongodump — MongoDB Database Tools official docs](https://www.mongodb.com/docs/database-tools/mongodump/)
- [mongodump Examples](https://www.mongodb.com/docs/database-tools/mongodump/mongodump-examples/)
- [APScheduler 3.x User Guide](https://apscheduler.readthedocs.io/en/3.x/userguide.html)
- [APScheduler CronTrigger](https://apscheduler.readthedocs.io/en/3.x/modules/triggers/cron.html)
- [APScheduler 4 Migration Guide](https://apscheduler.readthedocs.io/en/master/migration.html)
- [APScheduler on PyPI](https://pypi.org/project/APScheduler/)
- [aioboto3 on PyPI](https://pypi.org/project/aioboto3/)
- [aioboto3 Usage Docs](https://aioboto3.readthedocs.io/en/latest/usage.html)
- [aiobotocore S3 Basic Usage](https://aiobotocore.aio-libs.org/en/latest/examples/s3/basic_usage.html)
- [Docker Compose — Use service profiles](https://docs.docker.com/compose/how-tos/profiles/)
- [Docker Compose — Profiles reference](https://docs.docker.com/reference/compose-file/profiles/)
- [FastAPI — Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [FastAPI Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/)

---

*Stack research for: ollog v1.8 milestone*
*Researched: 2026-04-10*
