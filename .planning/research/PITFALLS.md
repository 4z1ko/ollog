# Domain Pitfalls — ollog v1.8

**Domain:** FastAPI + Beanie/MongoDB admin isolation, database backup, MkDocs docs rewrite
**Researched:** 2026-04-10
**Scope:** Three new capabilities: admin container, mongodump backup, MkDocs /guide rewrite

---

## Summary

Three distinct risk profiles converge in v1.8. The admin container adds a second long-running
process that shares state (cookies, JWT, Beanie, templates, static files) with the main app.
The backup module introduces a shell dependency (mongodump binary) that does not exist in the
base image, and a volume problem that will silently discard backups on container restart. The
docs rewrite is the lowest-risk area but has two sharp edges: plugin compatibility for API
reference embedding and `use_directory_urls: true` relying on `html=True` in the StaticFiles
mount.

Critical issues to resolve before building: (1) mongodump binary absent from python:3.12-slim,
(2) cookie name collision between port 8000 and 8001 when both run on the same hostname, and
(3) the `./backups/` path inside the container is ephemeral unless a volume is declared.

---

## 1. Admin Container Isolation

### 1.1 Cookie Cross-Port Contamination (CRITICAL)

**What goes wrong:** RFC 6265 Section 5.1.3 explicitly excludes port from cookie scope. Browsers
send cookies matching the domain and path regardless of port number. If both the main app
(port 8000) and the admin app (port 8001) set a cookie named `access_token` on the same domain
(e.g., `localhost` or `ollog.example.com`), each app receives the other app's cookie on every
request.

**Why it happens:** The current `app/admin/ui_router.py` sets
`response.set_cookie(key="access_token", ...)` without a `path` attribute, so the cookie is
scoped to `/`. A cookie set at `localhost:8000/admin/ui/login` is sent back to `localhost:8001/`
and vice versa — browsers do not distinguish ports when deciding which cookies to send.

**Consequences:**
- An operator logged into the main app at port 8000 will have their `access_token` cookie silently
  sent to the admin app at port 8001, potentially authenticating them as the wrong session.
- When an admin logs into port 8001, the new `access_token` overwrites whatever was set on port
  8000, logging the operator out of the main UI.
- This is not theoretical. It is guaranteed default browser behavior under RFC 6265.

**Prevention:** Use distinct cookie names per app, not distinct ports. The admin app must set a
cookie named `admin_token` (or any name that does not collide with `access_token`). The
`get_current_user_cookie` dependency in `app/auth/dependencies.py` reads
`Cookie(default=None)` using the parameter name `access_token` as the alias. The admin app's
equivalent dependency must read `Cookie(alias="admin_token")`. Both cookies will still be
transmitted to both ports, but each dependency ignores the wrong-named cookie.

**Alternative (secondary hardening):** Set `path="/admin"` on the admin cookie so the browser
only sends it with requests whose path starts with `/admin`. Only safe if the admin app never
serves anything outside `/admin`.

**Detection:** During local dev with both containers running, print `request.cookies` at the top
of each login handler and verify no cross-contamination.

**Confidence:** HIGH — RFC 6265 Section 5.1.3 (rfc-editor.org/rfc/rfc6265); Firefox Bugzilla
#469287 confirms real-world port-sharing behavior; w3tutorials.net/blog/are-http-cookies-port-specific/.

---

### 1.2 Beanie Global Initialization State (MODERATE — low risk under Docker Compose)

**What goes wrong:** `init_beanie()` stores model registry state at the module level inside
Beanie's internal `Settings` class. If two FastAPI apps sharing the same codebase both call
`init_beanie()` in the same OS process, the second call silently replaces the first call's
model registry.

**Current risk level:** Under Docker Compose each container is a separate Python interpreter.
The two calls to `init_beanie` in two separate containers cannot interfere. This pitfall is
latent — it activates only if the admin app is ever run in-process (e.g., via `app.mount()`).

**Consequence if activated:** Any document model omitted from the second `init_beanie()` call
becomes non-functional (queries raise `CollectionWasNotInitialized`). An admin app that
incorrectly calls `init_beanie(document_models=[User, ApiToken])` omitting `QSO` would break
QSO queries for any shared code path.

**Prevention:** Always call `init_beanie` with the full `document_models=[QSO, User, ApiToken]`
list in both apps, even if the admin app never queries QSO. Cost is negligible (index validation
at startup). Document this constraint in a comment next to the admin app's lifespan.

**Confidence:** MEDIUM — Beanie initialization docs at beanie-odm.dev/tutorial/initialization/;
module-level state pattern confirmed by Beanie source inspection.

---

### 1.3 Jinja2Templates Directory — No Conflict (INFORMATIONAL)

**What goes wrong:** Multiple `Jinja2Templates(directory="templates")` instantiations in the
same process (one in `app/main.py`, one in `app/admin/ui_router.py`) concern some developers.

**Reality:** `Jinja2Templates` creates an independent Jinja2 `Environment` per instance. There
is no global Jinja2 state. Two instances pointed at the same directory read the same files
independently — correct and intended behavior for a shared codebase. This is not a pitfall.

**Actual risk:** The `templates/` directory is baked into the image via `COPY templates/ templates/`.
If a future admin-specific Dockerfile omits certain templates, template-not-found errors surface
at request time, not startup. Keep a single Dockerfile; use the `command:` override in Docker
Compose to differentiate the entry point (`uvicorn app.main:app` vs `uvicorn app.admin_main:app`),
not separate build contexts.

**Confidence:** HIGH — Jinja2 Environment is instance-scoped; FastAPI templates documentation.

---

### 1.4 JWT Secret Shared Between Containers (LOW)

**What goes wrong:** Both containers read `SECRET_KEY` from the same `.env`. A token minted by
the main app is accepted by the admin app — this is the intended design. The risk is operational.

**Risk:** If `SECRET_KEY` is rotated and only one container is restarted, the two containers
temporarily hold different secrets. Tokens minted by the restarted container are rejected by the
non-restarted one, producing silent 401 errors.

**Secondary risk (code inspection):** `docker-compose.yml` line 29 hardcodes
`SECRET_KEY=dev-secret-change-in-production` in the `environment` block. If `.env` is absent,
`pydantic-settings` uses this insecure fallback for both containers. `app/config.py` declares
`secret_key: str` with no default — but the docker-compose environment override supplies one,
bypassing the Pydantic required-field guard. Remove the docker-compose default and force
operators to set `SECRET_KEY` explicitly in `.env`.

**Prevention:** (1) Always restart both containers atomically: `docker compose up -d --force-recreate`.
(2) Remove the `SECRET_KEY=dev-secret-change-in-production` line from `docker-compose.yml`.
Document the atomic restart requirement in the deployment guide.

**Confidence:** HIGH — code inspection of `docker-compose.yml` lines 28-30 and `app/config.py`.

---

### 1.5 CORS Between Port 8000 and 8001 (LOW — conditional)

**What goes wrong:** Ports define different origins for CORS purposes (unlike cookies). If any
HTMX partial or JS `fetch()` call in the admin UI at port 8001 targets the main API at port 8000,
the browser blocks it as a cross-origin request. The main app has no `CORSMiddleware` configured.

**When this bites:** Only if the admin container makes cross-port API calls. If the admin app
is fully self-contained (all its fetch targets are on port 8001), CORS is a non-issue.

**Prevention:** Keep all admin UI requests on the same origin (port 8001 calls port 8001 only).
If cross-port calls are ever added, configure `CORSMiddleware` with an explicit `allow_origins`
list — never `["*"]` with `allow_credentials=True` (FastAPI rejects this combination).

**Confidence:** HIGH — FastAPI CORS docs (fastapi.tiangolo.com/tutorial/cors/); browser
same-origin policy specification.

---

## 2. Database Backup

### 2.1 mongodump Binary Absent from python:3.12-slim (CRITICAL)

**What goes wrong:** `python:3.12-slim` (Debian Bookworm minimal) does not include `mongodump`.
It is part of `mongodb-database-tools`, a separate package acquired only from MongoDB's apt
repository. Any `subprocess.run(["mongodump", ...])` call inside the container raises
`FileNotFoundError` at runtime.

**Why it happens:** The Dockerfile installs only `pip install .`. `mongodump` is not a Python
package and is not acquired via pip.

**Consequences:** Backup module silently fails or crashes on first invocation. If the exception
is swallowed, no error is logged and no backup is created.

**Prevention options:**

Option A — Install `mongodb-database-tools` in the Dockerfile (adds ~40 MB):
```dockerfile
RUN apt-get update && apt-get install -y gnupg curl && \
    curl -fsSL https://www.mongodb.org/static/pgp/server-8.0.asc | \
      gpg -o /usr/share/keyrings/mongodb-server-8.0.gpg --dearmor && \
    echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] \
      https://repo.mongodb.org/apt/debian bookworm/mongodb-org/8.0 main" \
      | tee /etc/apt/sources.list.d/mongodb-org-8.0.list && \
    apt-get update && apt-get install -y mongodb-database-tools && \
    rm -rf /var/lib/apt/lists/*
```
The MongoDB apt repo for Bookworm amd64 now includes `mongodb-database-tools` as of MongoDB 8.0.

Option B — Pure-Python export using PyMongo (no binary dependency, recommended):
Iterate each collection with `motor.AsyncIOMotorCollection.find({})` and serialize with
`bson.json_util.dumps()` (EJSON format). No binary required. Output is re-importable with
`mongoimport`. Adequate for typical ham log databases (< 100K QSOs). Does not preserve BSON
types beyond what EJSON supports — suitable for disaster recovery, not byte-for-byte BSON replay.

**Recommendation:** Option B. It avoids image bloat and the MongoDB apt key management ceremony.
If exact BSON fidelity is ever required, document Option A as the upgrade path.

**Confidence:** HIGH — Docker Hub layer manifest for python:3.12-slim confirms no mongodb-database-tools;
MongoDB database tools installation docs (mongodb.com/docs/database-tools/installation/).

---

### 2.2 Backup Volume Ephemerality (CRITICAL)

**What goes wrong:** If `python -m app.backup` writes to `./backups/` inside the container and
that path is not a mounted volume, all backup files are discarded on container restart. Docker
container writable layers are ephemeral.

**Why it happens:** The current `docker-compose.yml` declares only the `mongo-data` named volume.
No `backups` volume is declared. Any `./backups/` or `/app/backups/` path inside the `api`
container is ephemeral container-layer storage.

**Consequences:** A backup written before a successful S3 upload is fine. But if S3 upload fails
after the local file is written and then the container restarts before retry, the file is gone
with no recovery path.

**Prevention:**
1. Add a named volume or bind mount to `docker-compose.yml`:
   ```yaml
   # Named volume (survives restarts, managed by Docker)
   - backups:/app/backups

   # OR bind mount (host path visible to ops)
   - ./backups:/app/backups
   ```
2. The backup module must read its output path from an env var (`BACKUP_DIR`, defaulting to
   `/app/backups`) — never a relative `./backups/` path.
3. After a confirmed S3 upload, delete the local file to prevent unbounded disk growth.

**Confidence:** HIGH — Docker Compose volume documentation; code inspection of docker-compose.yml.

---

### 2.3 S3 Upload Atomicity and Interrupted Uploads (MODERATE)

**What goes wrong:** `boto3.upload_file()` is not atomic from the caller's perspective. For files
above 8 MB it uses multipart upload (multiple HTTP requests via `TransferConfig`). If the Python
process is killed mid-upload, in-progress parts are orphaned in S3: invisible as completed
objects but charged at standard storage rates. They accumulate silently.

**What S3 does guarantee:** `PutObject` (single-part upload) is fully atomic on S3's side — no
partial objects are ever committed. For compressed EJSON exports of a typical ham log, staying
under 8 MB avoids multipart entirely.

**Consequences of interrupted multipart:**
- No corrupt object in the bucket (correct behavior)
- Orphaned parts accumulate, incurring storage charges
- No automatic cleanup unless a bucket lifecycle rule is configured

**Prevention:**
1. Configure a bucket lifecycle rule: `AbortIncompleteMultipartUploads` after 1 day. One-time S3
   console setting, not code.
2. Write the backup to a local temp file first, verify it is non-zero and has a valid gzip header,
   then upload. Never stream directly from the backup generator to S3.
3. Log the S3 ETag returned by boto3 after upload for auditability.
4. Use `upload_file` with a `Callback` parameter so interrupted uploads appear in logs.

**Confidence:** HIGH — AWS S3 PutObject atomicity guarantee (docs.aws.amazon.com/AmazonS3);
boto3 abort_multipart_upload docs.

---

### 2.4 Cron Expression Parsing Library (MODERATE)

**What goes wrong:** Python's stdlib has no cron expression parser. `BACKUP_SCHEDULE` requires
one. The ecosystem has shifted: `aiocron` (a common async cron wrapper) migrated from `croniter`
to `cronsim` in December 2024. `cronsim` has stricter validation for some edge-case expressions
(day-of-week/day-of-month interactions, `@yearly`/`@reboot` macros).

**Prevention:**
- For a simple scheduler loop, use `croniter` directly (now maintained under pallets-eco). It
  has a stable API and does not require asyncio integration.
- Pattern: `asyncio.create_task(_backup_loop())` where `_backup_loop` uses `croniter` to compute
  `next_run = iter.get_next(datetime)`, then `await asyncio.sleep((next_run - now).total_seconds())`.
- Do not use `aiocron` as the scheduling layer if you rely on non-standard cron macros — test
  the specific `BACKUP_SCHEDULE` value against `cronsim` before shipping.
- Pin whichever library is chosen to a specific minor version in `pyproject.toml`.

**Confidence:** MEDIUM — aiocron GitHub repo confirms cronsim migration (Dec 2024);
pallets-eco/croniter PyPI confirms active maintenance.

---

### 2.5 asyncio.create_task Shutdown Handling (MODERATE)

**What goes wrong:** A backup cron loop created with `asyncio.create_task()` is cancelled during
uvicorn shutdown. If the task is mid-backup when the signal arrives, the local gzip file and any
S3 upload in progress are abandoned in an indeterminate state.

**Why it happens:** The existing lifespan in `app/main.py` already demonstrates the correct
shutdown pattern for the change-stream watcher (lines 94-98: cancel + `await` with
`CancelledError` handling). A backup task created outside the lifespan (e.g., inside the backup
module's own startup function) is not tracked by lifespan and will not be waited for during
shutdown.

**Consequences:** Corrupt local `.gz` files; incomplete multipart S3 uploads; silent data loss
if the temp file cleanup `finally` block runs during cancellation before S3 confirms the upload.

**Prevention:**
1. Track the backup task in the lifespan `yield` block, following the existing watcher pattern:
   ```python
   backup_task = asyncio.create_task(_backup_loop())
   yield
   backup_task.cancel()
   try:
       await backup_task
   except asyncio.CancelledError:
       pass
   ```
2. Use a `try/finally` inside `_backup_loop` to delete the local temp file on `CancelledError`.
3. Accept that a backup in progress at shutdown time is abandoned. Do not attempt S3 upload after
   receiving `CancelledError` — the S3 client connection state is undefined at that point.

**Confidence:** HIGH — Python asyncio documentation; code inspection of `app/main.py` lines
48-99 (existing watcher and UDP shutdown pattern).

---

### 2.6 BACKUP_SCHEDULE Absent Crashes Startup (LOW)

**What goes wrong:** If `BACKUP_SCHEDULE` is not set in the environment and the backup loop
unconditionally tries to parse `None` as a cron expression, startup raises a `TypeError` before
the app begins serving requests.

**Prevention:** Follow the existing `udp_enabled` guard pattern from `app/config.py`:
```python
backup_schedule: str | None = None  # None = disabled, backup loop does not start
```
In lifespan, start the backup task only when `settings.backup_schedule is not None`. This makes
backup opt-in with zero startup cost when not configured.

**Confidence:** HIGH — code inspection of `app/config.py` lines 17-18 (udp_enabled pattern).

---

## 3. MkDocs Docs Rewrite

### 3.1 html=True on StaticFiles Mount Is Load-Bearing (HIGH)

**What goes wrong:** MkDocs Material with `use_directory_urls: true` (current setting in
`mkdocs.yml`) generates `getting-started/index.html` instead of `getting-started.html`. The
`site/` directory is mounted via `StaticFiles(directory="site", html=True)` at `/guide`. The
`html=True` parameter enables directory-index resolution — a request to `/guide/getting-started`
is served as `/guide/getting-started/index.html`. Without `html=True`, all non-root pages
return 404.

**Current state:** `app/main.py` line 151 correctly sets `html=True`. This will continue to work
after the rewrite as long as `html=True` is not removed.

**Risk:** The parameter is not obviously necessary; a developer reading the mount line cold would
not know it is load-bearing and might remove it during a cleanup pass.

**Prevention:** Add a comment at the mount line:
```python
# html=True is load-bearing: use_directory_urls=true in mkdocs.yml generates
# page/index.html paths; html=True enables directory index resolution in StaticFiles.
app.mount("/guide", StaticFiles(directory="site", html=True), name="guide")
```

**Confidence:** HIGH — code inspection of `main.py` line 151 and `mkdocs.yml`; MkDocs
`use_directory_urls` documentation.

---

### 3.2 API Reference Embedding — Plugin and Schema Export (MODERATE)

**What goes wrong:** Embedding the FastAPI OpenAPI spec in a MkDocs page requires a plugin not
currently in `pyproject.toml`. Two plugins exist:

- `mkdocs-swagger-ui-tag` (blueswen/mkdocs-swagger-ui-tag) — bundles Swagger UI assets
  statically. Works when `site/` is served offline via FastAPI's StaticFiles with no CDN access.
- `mkdocs-render-swagger-plugin` (bharel/mkdocs-render-swagger-plugin) — injects a CDN
  `<script>` tag pointing to unpkg.com. Breaks on private networks with no internet access.

**Use `mkdocs-swagger-ui-tag`.** The `mkdocs-render-swagger-plugin` CDN dependency is incompatible
with the project's deployment model (served from FastAPI StaticFiles, potentially on a private
hamnet).

**Schema export requirement:** Both plugins require an OpenAPI JSON file at build time. FastAPI
serves its schema at `/openapi.json` (live), but `mkdocs build` is a static process. The schema
file must be exported to `docs/openapi.json` before building:
```bash
python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > docs/openapi.json
```
This requires the app to be importable without a running database. Currently safe: `init_db()` is
called only inside the lifespan context manager, not at module import time.

**Prevention:**
1. Add `mkdocs-swagger-ui-tag` to `[dependency-groups] dev` in `pyproject.toml`.
2. Add the schema export command as a pre-build step (Makefile, justfile, or CI).
3. Add `docs/openapi.json` to `.gitignore` — it is a build artifact, not source.

**Confidence:** MEDIUM — mkdocs-swagger-ui-tag GitHub (blueswen/mkdocs-swagger-ui-tag); code
inspection confirming `init_db` is lifespan-scoped, safe to import without DB.

---

### 3.3 Nav Structure and Search Indexing (LOW)

**What goes wrong:** Deeply nested nav sections increase click depth without improving search
recall. The `navigation.indexes` and `navigation.sections` features in Material have a documented
incompatibility (mkdocs-material issue #3070): section index pages are not rendered correctly in
certain Material versions when both features are active simultaneously.

**Current state:** `mkdocs.yml` uses a flat 7-page nav with no nested sections or Material
feature flags. The rewrite may introduce sections.

**Prevention:**
- Keep nav at 2 levels maximum: top-level sections with individual pages beneath.
- Do not activate both `navigation.indexes` and `navigation.sections` in `mkdocs.yml` features.
- Do not create section folders with only one page — promote single-page sections to top level.

**Confidence:** MEDIUM — mkdocs-material navigation docs (squidfunk.github.io/mkdocs-material);
GitHub issue #3070.

---

### 3.4 mkdocs serve in Docker Not Required (LOW)

**What goes wrong:** `mkdocs serve` inside Docker binds to `127.0.0.1:8000` by default,
unreachable from the host. Requires `--dev-addr 0.0.0.0:PORT` to work inside a container.

**Why this is low risk:** The project serves the built `site/` via FastAPI StaticFiles. `mkdocs serve`
is a dev tool only. The production build path is `mkdocs build` then `COPY site/ site/` then FastAPI
serves `/guide`. Running `mkdocs serve` in Docker is never required.

**Prevention:** Run `mkdocs serve` outside Docker in the dev virtual env. Document this in the
deployment guide so developers do not waste time trying to run it inside a container.

**Confidence:** HIGH — MkDocs `--dev-addr` documentation; Dockerfile inspection.

---

## 4. Phase-Specific Warning Summary

| Phase Topic | Pitfall | Severity | Mitigation |
|---|---|---|---|
| Admin container | `access_token` cookie collides between port 8000 and 8001 | CRITICAL | Rename admin cookie to `admin_token` |
| Admin container | Beanie double-init if ever merged to single process | LOW (Docker) | Always pass full `document_models` list |
| Admin container | `SECRET_KEY` docker-compose default bypasses Pydantic guard | MODERATE | Remove hardcoded dev default from docker-compose.yml |
| Admin container | CORS blocks cross-port JS fetch calls | LOW (conditional) | Keep admin UI requests on same origin (port 8001 only) |
| Backup module | `mongodump` absent from python:3.12-slim | CRITICAL | Use pure-Python PyMongo export OR apt-install database-tools |
| Backup module | `./backups/` path ephemeral in container | CRITICAL | Declare named volume or bind mount in docker-compose.yml |
| Backup module | S3 multipart upload leaves orphaned parts on interrupt | MODERATE | S3 lifecycle AbortIncompleteMultipartUploads rule (1 day) |
| Backup module | asyncio backup task not cancelled cleanly at shutdown | MODERATE | Track task in lifespan; cancel + await on shutdown |
| Backup module | `BACKUP_SCHEDULE` absent crashes startup | LOW | `backup_schedule: str \| None = None` default in config |
| Docs rewrite | `html=True` removed from StaticFiles mount | HIGH | Add load-bearing comment at mount line in main.py |
| Docs rewrite | CDN-dependent swagger plugin breaks offline serving | MODERATE | Use mkdocs-swagger-ui-tag (static assets), not render-swagger-plugin |
| Docs rewrite | OpenAPI schema not exported before `mkdocs build` | MODERATE | Add pre-build `python -c "... app.openapi()"` export step |
| Docs rewrite | `navigation.indexes` + `navigation.sections` conflict | LOW | Do not activate both simultaneously in mkdocs.yml features |

---

## Sources

- RFC 6265 Section 5.1.3 (cookies exclude port from scope): https://www.rfc-editor.org/rfc/rfc6265
- Firefox Bugzilla #469287 (cookie port-sharing real-world): https://bugzilla.mozilla.org/show_bug.cgi?id=469287
- Cookie port-sharing analysis: https://www.w3tutorials.net/blog/are-http-cookies-port-specific/
- FastAPI CORS documentation: https://fastapi.tiangolo.com/tutorial/cors/
- Beanie initialization documentation: https://beanie-odm.dev/tutorial/initialization/
- MongoDB Database Tools installation (Bookworm): https://www.mongodb.com/docs/database-tools/installation/
- mongodump compatibility documentation: https://www.mongodb.com/docs/database-tools/mongodump/mongodump-compatibility-and-installation/
- Docker Hub python:3.12-slim layer manifest: https://hub.docker.com/layers/library/python/3.12-slim/images/sha256-ac212230555ffb7ec17c214fb4cf036ced11b30b5b460994376b0725c7f6c151
- AWS S3 multipart upload overview: https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html
- AWS S3 AbortIncompleteMultipartUploads lifecycle: https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpu-abort-incomplete-mpu-lifecycle-config.html
- boto3 abort_multipart_upload: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/abort_multipart_upload.html
- aiocron (cronsim migration Dec 2024): https://github.com/gawel/aiocron
- croniter (pallets-eco, active): https://github.com/pallets-eco/croniter
- Python asyncio task cancellation: https://docs.python.org/3/library/asyncio-task.html
- mkdocs-swagger-ui-tag (static assets, recommended): https://github.com/blueswen/mkdocs-swagger-ui-tag
- mkdocs-render-swagger-plugin (CDN-dependent, avoid): https://github.com/bharel/mkdocs-render-swagger-plugin
- MkDocs Material navigation setup: https://squidfunk.github.io/mkdocs-material/setup/setting-up-navigation/
- navigation.indexes + navigation.sections incompatibility: https://github.com/squidfunk/mkdocs-material/issues/3070
