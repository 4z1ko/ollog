# Architecture Research: ollog v1.8

**Domain:** Admin container split, backup module, MkDocs rewrite
**Researched:** 2026-04-10
**Confidence:** HIGH (direct codebase inspection of all relevant files)

---

## Summary

Three new capabilities land in v1.8. Each is architecturally independent and introduces
no circular dependencies with existing modules:

1. **Admin container** — a second Docker Compose service that runs the *same image* but
   exposes only admin routes. Cleanest approach: an `app/admin_main.py` entry point that
   builds a restricted FastAPI app object, selected by the service's `command:` override
   in `docker-compose.yml`. No env var app-mode branching inside `main.py`.

2. **Backup module** — a standalone CLI module at `app/backup/` (package, not a single
   file) that connects to MongoDB independently of FastAPI and uploads a dump to S3.
   Invoked via `python -m app.backup`. The existing named volume `mongo-data` is
   confirmed present and relevant.

3. **Docs rewrite** — MkDocs Material is already wired up (`mkdocs.yml` exists, `site/`
   is built and mounted at `/guide` in `main.py`). The rewrite is a content-only task
   with no structural changes needed to the serve path.

---

## Section 1: Existing Route Map

Understanding the full route surface is prerequisite to defining what the admin container
should (and should not) expose.

### Route prefixes in `app/main.py`

| Router | Prefix | Auth type | Audience |
|--------|--------|-----------|----------|
| `auth.router` | `/auth` | None / Bearer JWT | Everyone |
| `admin.router` | `/admin/users` | Bearer JWT + `require_admin` | Admin only |
| `admin.ui_router` | `/admin/ui` | Cookie JWT + `require_admin_cookie` | Admin browser |
| `qso.router` | `/api/qsos` | Bearer JWT or API key | Operators |
| `qso.ui_router` | `/log` | Cookie JWT | Operators browser |
| `adif.router` | `/api/adif` | Bearer JWT | Operators |
| `feed.router` | `/feed` | Cookie JWT | Operators browser |
| `profile.router` | `/api/profile` | Bearer JWT | Operators |
| `tokens.router` | `/api/tokens` | Bearer JWT | Operators |
| Static `site/` | `/guide` | None | Public |
| Static `static/` | `/static` | None | Public |
| `GET /health` | `/health` | None | Monitoring |
| `GET /api/whoami` | `/api/whoami` | Bearer JWT | Debug |

### Admin container scope

The admin container should expose only the routes needed for admin management work:

- `/auth` — login (to acquire a JWT before hitting admin endpoints)
- `/admin/users` — REST account management
- `/admin/ui` — browser-based admin panel
- `/health` — container health check
- `/static` — CSS/JS assets required by admin UI templates

Routes the admin container explicitly must NOT expose:
- `/api/qsos`, `/log`, `/api/adif`, `/feed` — operator logging surface
- `/api/tokens`, `/api/profile` — operator self-service; not relevant to admin workflows
- `/guide` — documentation; no need on port 8001

---

## Section 2: Admin Container — Approach Decision

Three approaches considered:

### Approach A: `APP_MODE` env var inside `main.py` (NOT recommended)

```python
# app/main.py — branching version
import os
mode = os.getenv("APP_MODE", "operator")

app = FastAPI(...)
app.include_router(auth_router)
if mode == "admin":
    app.include_router(admin_router)
    app.include_router(ui_router)
else:
    app.include_router(qso_router)
    ...
```

**Problem:** `main.py` becomes a conditional mess. Every future router addition needs to
decide which mode it belongs to. Lifespan also starts the UDP listener and change-stream
watcher — both unnecessary for the admin container. Branching lifespan logic compounds
the problem.

### Approach B: Two separate `main.py` entry points with a shared app factory (recommended)

Create `app/admin_main.py` as a minimal FastAPI application that imports only the admin
routers. `app/main.py` stays exactly as it is.

```python
# app/admin_main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db, close_db
from app.config import settings
from app.admin.router import router as admin_router
from app.admin.ui_router import ui_router
from app.auth.router import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # No UDP listener, no change-stream watcher
    yield
    await close_db()


app = FastAPI(title="ollog-admin", version="0.1.0", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(ui_router, include_in_schema=False)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(HTTPException)
async def ui_auth_redirect(request: Request, exc: HTTPException):
    path = request.url.path
    if path.startswith("/admin/ui/") and exc.status_code in (401, 403):
        return RedirectResponse(url="/admin/ui/login", status_code=302)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.get("/health")
async def health():
    from app.database import get_client
    client = get_client()
    if client is None:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "error"})
    try:
        await client.admin.command("ping")
        return {"status": "ok", "mongodb": "connected"}
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "error"})
```

**Why this is correct:**
- `main.py` is untouched — no regression risk to the operator service.
- `admin_main.py` is small, readable, and self-documenting.
- Lifespan is minimal — no wasted UDP socket or change-stream task.
- The `_bootstrap_admin()` call is not needed in `admin_main.py` because the admin user
  is bootstrapped by the operator service at startup. If the operator service is not
  running, the admin account bootstrap would not have run anyway. (Both services share
  the same MongoDB; the bootstrap is idempotent so it can optionally be included.)
- `init_db()` and `close_db()` are the same functions — both services share
  `app/database.py` without modification.

### Approach C: Docker `command:` override to a different Python file

```yaml
admin:
  build: .
  command: ["uvicorn", "app.admin_main:app", "--host", "0.0.0.0", "--port", "8001"]
```

This is actually the *same* as Approach B — it requires `app/admin_main.py` to exist.
"Approach C" is how you wire Approach B into Docker Compose, not a separate strategy.

### Docker Compose changes

```yaml
# docker-compose.yml additions

  admin:
    build: .
    command: ["uvicorn", "app.admin_main:app", "--host", "0.0.0.0", "--port", "8001"]
    ports:
      - "8001:8001"
    depends_on:
      mongodb:
        condition: service_healthy
    env_file: .env
    environment:
      - SECRET_KEY=dev-secret-change-in-production
      - MONGODB_URI=mongodb://mongodb:27017/?replicaSet=rs0
      - MONGODB_DB=ollog
```

The `admin` service uses an identical `env_file:` and environment block. Both services
share the same image, same database, same JWT secret — a token issued on port 8000 is
valid on port 8001 and vice versa. This is correct: an admin who logs in on the operator
UI should be able to use the same session on the admin UI.

**Image build note:** The `Dockerfile` `COPY` section does not include `docs/` or
`mkdocs.yml` — only `app/`, `templates/`, `static/`, `site/`. The admin image needs
`static/` (for template assets) but not `site/`. This is already handled correctly.

---

## Section 3: Backup Module — Package vs. Single File

### Decision: `app/backup/` package (not `app/backup.py`)

Rationale:

A backup operation involves at minimum three distinct concerns:
1. `__main__.py` — CLI entry point and argument parsing
2. MongoDB dump logic — connecting to Motor/PyMongo, running `mongodump` or
   streaming a collection export
3. S3 upload logic — boto3/aiobotocore calls, retry, presigned URL or direct put

Putting all three in a single `app/backup.py` creates a file that will grow past
200 lines immediately and has no natural seam for tests or future features (e.g. restore,
backup verification, rotation policy). A package with clear module boundaries is better:

```
app/backup/
    __init__.py        # public API if needed; may be empty
    __main__.py        # entry point: python -m app.backup [args]
    dump.py            # MongoDB dump: mongodump subprocess or Motor streaming
    upload.py          # S3 upload via boto3
    config.py          # backup-specific settings (S3 bucket, prefix, schedule)
    scheduler.py       # APScheduler or simple asyncio.sleep loop for scheduled runs
```

`python -m app.backup` dispatches to `app/backup/__main__.py`. This is standard Python
packaging convention and works with the existing project layout.

### MongoDB connection in backup

The backup module must connect to MongoDB *independently* of the FastAPI app. It cannot
import `app.database` and call `init_db()` because that function also calls `init_beanie`
which requires the full model tree. For a dump, raw PyMongo is preferable:

```python
# app/backup/dump.py
from pymongo import MongoClient

def dump_collection(uri: str, db_name: str, collection: str) -> bytes:
    """Stream all documents from a collection as NDJSON bytes."""
    import json
    client = MongoClient(uri)
    db = client[db_name]
    lines = []
    for doc in db[collection].find():
        doc["_id"] = str(doc["_id"])
        lines.append(json.dumps(doc))
    client.close()
    return b"\n".join(line.encode() for line in lines)
```

Alternative: call `mongodump` as a subprocess and capture stdout (BSON). This is more
faithful for restore purposes but requires `mongodump` to be present in the image. The
Dockerfile base is `python:3.12-slim` which does not include MongoDB tools. Either:
- Add `RUN apt-get install -y mongodb-database-tools` to Dockerfile, or
- Use the pure-Python NDJSON approach and skip `mongodump` entirely.

For v1.8, the pure-Python approach is recommended: no Dockerfile changes, no binary
dependency. The output format (NDJSON per collection) is sufficient for point-in-time
restore and is human-readable.

### S3 upload

Use `boto3` (synchronous) in the backup CLI — it does not need to be async since the CLI
is not a FastAPI endpoint. `boto3` is simpler and better documented than `aiobotocore`
for a CLI use case:

```python
# app/backup/upload.py
import boto3
from datetime import datetime, timezone

def upload_to_s3(data: bytes, bucket: str, key_prefix: str, filename: str) -> str:
    """Upload bytes to S3. Returns the S3 object key."""
    s3 = boto3.client("s3")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"{key_prefix}/{timestamp}-{filename}"
    s3.put_object(Bucket=bucket, Key=key, Body=data)
    return key
```

S3 credentials come from environment variables (`AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`) — the standard boto3 credential chain.
No custom credential handling needed.

### Scheduled runs

If v1.8 requires scheduled backups (e.g. nightly), two options:

**Option A: Docker Compose `cron` service** — add a `backup` service with
`restart: always` that loops with `sleep`:

```yaml
  backup:
    build: .
    command: >
      sh -c "while true; do python -m app.backup; sleep 86400; done"
    env_file: .env
    environment:
      - MONGODB_URI=mongodb://mongodb:27017/?replicaSet=rs0
      - BACKUP_S3_BUCKET=my-ollog-backups
```

**Option B: APScheduler inside `app/backup/scheduler.py`** — a long-running Python
process that fires the backup job on a cron schedule.

Option A is simpler and requires no additional dependencies. Recommended for v1.8.

### Named volume and backup path

From `docker-compose.yml`:

```yaml
volumes:
  mongo-data:
```

The `mongodb` service mounts `mongo-data:/data/db`. This is a Docker named volume, not a
bind mount. It cannot be accessed directly from the host filesystem path. Implications:

- A `mongodump`-based backup would need the backup service to share the same volume
  mount (`mongo-data:/data/db:ro`) — messy and fragile.
- The pure-Python NDJSON approach (connecting to `mongodb:27017` via network) sidesteps
  this entirely. The backup service connects to MongoDB the same way the API service does.
- **Confirmed: there is no bind-mount path to worry about.** The backup module uses the
  `MONGODB_URI` environment variable, not a filesystem path.

---

## Section 4: MkDocs — Current State and What Changes

### What already exists

```
mkdocs.yml          # config: Material theme, slate/indigo, 7-page nav
docs/               # source markdown
    index.md
    deployment.md
    getting-started.md
    admin-guide.md
    api-reference.md
    adif-field-reference.md
    troubleshooting.md
site/               # built HTML (committed to repo, served by FastAPI)
```

`app/main.py` line 151:
```python
app.mount("/guide", StaticFiles(directory="site", html=True), name="guide")
```

The docs are served at `/guide` by the operator service. MkDocs Material is already
configured with the correct theme (`slate` scheme, `indigo` primary). This is a
content-rewrite task, not an infrastructure task.

### What v1.8 changes

The "docs rewrite" means updating the content of `docs/*.md` files and rebuilding
`site/`. No changes needed to:
- `mkdocs.yml` (unless new pages are added to `nav:`)
- `app/main.py` (mount point stays at `/guide`)
- `Dockerfile` (already `COPY site/ site/`)
- `docker-compose.yml` (no new service)

If new pages are added (e.g. a backup guide or API token guide), add them to the `nav:`
in `mkdocs.yml` and create the corresponding `docs/*.md` files. Rebuild with
`mkdocs build` before committing the updated `site/`.

The admin container (`admin_main.py`) does not mount `/guide` — documentation is only
relevant on the operator-facing port 8000.

### Build workflow

```bash
# From project root, with mkdocs-material installed:
mkdocs build          # outputs to site/
# Then commit site/ alongside docs/ changes
```

The `site/` directory is committed to the repository (as it is today) so Docker image
builds do not require `mkdocs` to be present in the image. This is the correct pattern
for this project.

---

## Section 5: Shared Infrastructure — What Both Services Use

| Component | Used by operator | Used by admin | Notes |
|-----------|-----------------|---------------|-------|
| `app/config.py` | Yes | Yes | Both read from same `.env` |
| `app/database.py` | Yes | Yes | `init_db()` / `close_db()` |
| `app/auth/` | Yes | Yes | Models, deps, router, service |
| `app/admin/router.py` | Yes | Yes | Admin user CRUD |
| `app/admin/ui_router.py` | Yes | Yes | Admin browser UI |
| `app/qso/` | Yes | No | Operator-only |
| `app/adif/` | Yes | No | Operator-only |
| `app/feed/` | Yes | No | Operator-only |
| `app/profile/` | Yes | No | Operator-only |
| `app/tokens/` | Yes | No | Operator-only |
| `app/udp/` | Yes (if enabled) | No | Operator-only |
| `app/backup/` | No | No | CLI-only, invoked by backup service |
| `templates/` | Yes | Yes | Admin UI templates are in `templates/admin/` |
| `static/` | Yes | Yes | CSS/JS for both UIs |
| `site/` | Yes | No | Only operator service mounts /guide |

---

## Section 6: Component Boundaries Diagram

```
Docker Compose
│
├── mongodb (mongo:7, named volume mongo-data)
│   └── Collections: qsos, users, api_tokens
│
├── api (port 8000) → uvicorn app.main:app
│   Routes: /auth /admin/users /admin/ui /api/qsos /log
│           /api/adif /feed /api/profile /api/tokens
│           /guide /static /health
│   Lifespan: init_db, _bootstrap_admin, watch_qsos, udp_listener
│
├── admin (port 8001) → uvicorn app.admin_main:app
│   Routes: /auth /admin/users /admin/ui /static /health
│   Lifespan: init_db only (no UDP, no change stream)
│
└── backup (no port) → python -m app.backup
    Connects to: MONGODB_URI (direct PyMongo)
    Writes to: AWS S3 via boto3
    Trigger: schedule (sleep loop) or one-shot
```

---

## Section 7: Anti-Patterns to Avoid

### Anti-Pattern 1: `APP_MODE` env var branching in `main.py`

**What goes wrong:** `main.py` accumulates conditional logic. Every new router and every
lifespan concern needs a mode check. Tests need to set `APP_MODE` before importing.

**Do this instead:** Separate entry point `app/admin_main.py`. Keep `main.py` clean.

### Anti-Pattern 2: `app/backup.py` as a single file

**What goes wrong:** Dump logic, S3 upload, CLI parsing, and scheduling all live in one
file. It grows past 300 lines with no seam for tests. Future features (restore, rotation)
have nowhere to live.

**Do this instead:** `app/backup/` package with `__main__.py`, `dump.py`, `upload.py`,
`config.py`.

### Anti-Pattern 3: Sharing the `site/` mount on the admin container

**What goes wrong:** The admin container serves docs at `/guide`. This doubles the
surface area where documentation is accessible and adds a `StaticFiles` mount that serves
no purpose for admin workflows.

**Do this instead:** `admin_main.py` does not mount `/guide`. Docs are operator-facing
only.

### Anti-Pattern 4: Using `mongodump` subprocess without the binary in the image

**What goes wrong:** `python:3.12-slim` does not include `mongodb-database-tools`.
`mongodump` fails with `FileNotFoundError`. Adding it requires a multi-stage build or
apt install, which bloats the image used for both the API and admin services.

**Do this instead:** Use Motor or PyMongo to stream documents as NDJSON. No binary
dependency. No Dockerfile change.

### Anti-Pattern 5: `admin_main.py` imports from `main.py`

**What goes wrong:** `main.py` creates the `app` FastAPI object at module import time.
Importing from `main.py` in `admin_main.py` starts the full operator lifespan.

**Do this instead:** `admin_main.py` imports directly from `app.admin.router`,
`app.auth.router`, etc. Never imports from `app.main`.

---

## Sources

- Direct codebase inspection: `docker-compose.yml`, `Dockerfile`, `app/main.py`,
  `app/config.py`, `app/database.py`, `app/admin/router.py`, `app/admin/ui_router.py`,
  `app/qso/router.py`, `app/qso/ui_router.py`, `app/auth/router.py`, `app/adif/router.py`,
  `app/feed/router.py`, `app/profile/router.py`, `app/tokens/router.py`,
  `app/udp/server.py`, `mkdocs.yml`, `docs/index.md` (HIGH confidence — live codebase)
- FastAPI `StaticFiles` mount ordering: `main.py` line 151 comment notes it is
  load-bearing — confirmed pattern (HIGH confidence)
- Docker Compose named volume vs. bind mount: `docker-compose.yml` `volumes:` section
  shows `mongo-data:` (named, not bind-mounted) — directly observed (HIGH confidence)
- `python -m package` entry point convention: Python stdlib `__main__.py` pattern
  (HIGH confidence)
- boto3 credential chain: standard AWS SDK pattern, no project-specific validation needed
  (MEDIUM confidence — standard but not verified against current project deps)

---

*Architecture research for: ollog v1.8 — admin container, backup module, docs rewrite*
*Researched: 2026-04-10*
