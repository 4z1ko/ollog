# Research Summary: ollog v1.8

**Project:** ollog v1.8
**Domain:** FastAPI + Beanie (MongoDB) + HTMX ham radio QSO logging app
**Researched:** 2026-04-10
**Confidence:** HIGH (admin container, backup approach, docs tooling all grounded in live codebase inspection and official docs)

---

## Executive Summary

v1.8 adds three independent capabilities to an already-working FastAPI + Beanie + HTMX stack: a dedicated admin container, a database backup CLI, and a comprehensive docs rewrite. Each capability is architecturally isolated — they share the same image and database but do not entangle each other's code paths. The recommended implementation strategy is to build all three as sequential phases with low coupling risk since there are no cross-feature dependencies.

The two most consequential decisions for this milestone are already resolved by research. First, the admin container must use a distinct cookie name (`admin_token`, not `access_token`) because RFC 6265 excludes port from cookie scope — both containers running on `localhost` at ports 8000 and 8001 share the same cookie jar, making name collision a guaranteed silent auth bug, not a theoretical edge case. Second, the backup module cannot call `mongodump` via subprocess because `python:3.12-slim` does not include MongoDB Database Tools, and adding them bloats the image shared with the API and admin services; instead, the backup should use pure-Python PyMongo/BSON export (EJSON format via `bson.json_util.dumps()`), which requires no Dockerfile changes and is adequate for point-in-time restore of any realistic ham log dataset.

The docs rewrite is low-risk: MkDocs Material is already installed, `site/` is already mounted at `/guide`, and the work is content-only. The only sharp edge is the decision on whether to embed interactive API reference — if so, `mkdocs-swagger-ui-tag` (static assets, no CDN) is the only viable plugin for an app served from FastAPI StaticFiles, and it requires exporting `openapi.json` as a pre-build step.

---

## v1.8 Feature Areas

### Admin Container

**Recommended approach:** Create `app/admin_main.py` as a standalone FastAPI entry point that imports only the admin and auth routers. Keep `app/main.py` completely unchanged. Wire the Docker Compose `admin` service to use `command: ["uvicorn", "app.admin_main:app", "--host", "0.0.0.0", "--port", "8001"]` and gate the service behind `profiles: [admin]` so it is opt-in and does not start by default.

The admin container's lifespan should call `init_db()` and `close_db()` only — no UDP listener, no change-stream watcher. Both containers share the same `.env`, the same `SECRET_KEY`, and the same MongoDB instance, so a JWT issued on port 8000 is valid on port 8001 (this is intentional: an admin logged into the operator UI should not have to re-authenticate).

**Key constraints:**
- Admin cookie must be named `admin_token`. The admin login handler sets `response.set_cookie(key="admin_token", ...)` and the admin auth dependency reads `Cookie(alias="admin_token")`. The operator-side `access_token` cookie remains unchanged.
- `admin_main.py` must never import from `app.main` — doing so would instantiate the operator `FastAPI` app object and start its lifespan.
- `init_beanie()` must be called with the full `document_models=[QSO, User, ApiToken]` list even in the admin app, to avoid `CollectionWasNotInitialized` errors on any shared code path.

**Critical pitfalls to avoid:**
- Cookie name collision between port 8000 and 8001 (CRITICAL — RFC 6265, guaranteed browser behavior).
- `admin_main.py` importing from `app.main` and triggering operator lifespan startup.
- `SECRET_KEY=dev-secret-change-in-production` hardcoded in `docker-compose.yml` environment block — remove it; force the value to come from `.env` so the Pydantic required-field guard actually fires.

---

### Database Backup

**Recommended approach:** Implement `app/backup/` as a Python package (not a single file) with `__main__.py`, `dump.py`, `upload.py`, and `scheduler.py`. Invoke via `python -m app.backup`. Use pure-Python PyMongo/BSON export (not `mongodump` subprocess). Use `aioboto3>=13,<16` for async S3 uploads when the scheduler runs inside a FastAPI lifespan context; use synchronous `boto3` if the CLI is invoked standalone. Schedule via APScheduler 3.x (`AsyncIOScheduler` + `CronTrigger.from_crontab()`) — pin to `<4` to avoid the incompatible v4 alpha.

Backup volume persistence requires explicit action: declare a named volume (`backups:/app/backups`) or bind mount (`./backups:/app/backups`) in `docker-compose.yml`. Without this, every backup file is discarded on container restart. The backup module must read its output path from a `BACKUP_DIR` env var (default `/app/backups`), never a relative path.

The `BACKUP_SCHEDULE` env var must default to `None` in `app/config.py` and the scheduler must not start when the value is absent — follow the existing `udp_enabled` guard pattern. This prevents startup crashes on deployments that do not need scheduled backups.

**Key constraints:**
- `mongodump` is NOT available in `python:3.12-slim`. Do not add `subprocess.run(["mongodump", ...])` without first resolving the Dockerfile question.
- `./backups/` inside a container is ephemeral. A named volume or bind mount is mandatory.
- Track the backup asyncio task in the lifespan `yield` block (cancel + await on shutdown), following the existing change-stream watcher pattern in `app/main.py` lines 94-98.

**Critical pitfalls to avoid:**
- `mongodump` binary absent from the image (CRITICAL — `FileNotFoundError` at runtime, potentially silent).
- Backup files written to ephemeral container layer with no volume mount (CRITICAL — files discarded on restart).
- `asyncio.create_task()` backup loop not tracked by lifespan — orphaned mid-backup on shutdown.
- S3 multipart upload parts orphaned on interrupt — configure `AbortIncompleteMultipartUploads` (1 day) lifecycle rule on the S3 bucket as a one-time operational step.

---

### Docs Rewrite

**Recommended approach:** Content-only rewrite of `docs/*.md` files followed by `mkdocs build` to regenerate `site/`. No new infrastructure, no new MkDocs plugins required unless interactive API reference is in scope. If API reference embedding is added, use `mkdocs-swagger-ui-tag` (static assets bundled) — not `mkdocs-render-swagger-plugin` (CDN-dependent, breaks on private hamnet deployments).

Run `mkdocs serve` outside Docker in the dev virtualenv. The production path is `mkdocs build` then commit `site/` then Docker image picks it up via existing `COPY site/ site/`.

**Key constraints:**
- `html=True` on the `StaticFiles(directory="site", html=True)` mount in `app/main.py` is load-bearing. MkDocs Material with `use_directory_urls: true` generates `page/index.html` paths; removing `html=True` causes all non-root pages to 404. Add an explicit comment at that line before the rewrite ships.
- If API reference pages are added, the `openapi.json` schema must be exported before `mkdocs build` runs: `python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > docs/openapi.json`. This works because `init_db()` is lifespan-scoped and the app is importable without a running database.
- Do not activate both `navigation.indexes` and `navigation.sections` in `mkdocs.yml` simultaneously — documented incompatibility in Material issue #3070.

**Critical pitfalls to avoid:**
- Removing `html=True` from the StaticFiles mount (HIGH — all docs pages 404 immediately).
- Using `mkdocs-render-swagger-plugin` (CDN-dependent, fails offline/hamnet).
- Forgetting to export `openapi.json` before `mkdocs build` if API reference pages are included.

---

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Admin container entry point | `app/admin_main.py` (separate file) | Keeps `app/main.py` untouched; minimal lifespan; no conditional branching; clean separation |
| Admin container wiring | Docker Compose `profiles: [admin]` + `command:` override | Opt-in service; one Dockerfile; no second build context |
| Admin cookie name | `admin_token` (not `access_token`) | RFC 6265 excludes port from cookie scope; cookie name is the only reliable isolation mechanism between ports 8000 and 8001 on the same hostname |
| MongoDB export method | Pure-Python PyMongo + `bson.json_util.dumps()` (EJSON) | No Dockerfile changes; no `mongodump` binary dependency; adequate for restore; EJSON re-importable via `mongoimport` |
| Cron scheduler | APScheduler 3.x (`AsyncIOScheduler` + `CronTrigger.from_crontab()`) | Stable; native asyncio; plugs into existing lifespan pattern; `<4` pin avoids alpha API redesign |
| Async S3 upload | `aioboto3>=13,<16` | Drop-in async boto3; `upload_fileobj()` natively async; avoids blocking event loop; explicit upper bound for stability |
| S3 credentials | Standard boto3 credential chain (env vars) | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` — no custom credential handling needed |
| Backup volume | Named volume or bind mount (explicit in compose) | Container writable layers are ephemeral; `./backups/` without a volume declaration loses files on restart |
| Backup package layout | `app/backup/` package with `__main__.py`, `dump.py`, `upload.py`, `scheduler.py` | `python -m app.backup` entry point; clear module boundaries; room for restore/rotation in future |
| Docs tooling | MkDocs Material (already installed, content-only rewrite) | No new stack additions; `mkdocs build` → `site/` → committed to repo → served by FastAPI StaticFiles at `/guide` |
| API reference plugin (if used) | `mkdocs-swagger-ui-tag` | Static assets bundled; no CDN dependency; works offline and on hamnet |
| APScheduler version ceiling | `apscheduler>=3.10,<4` | APScheduler 4.x is alpha with a fully redesigned API; `<4` ceiling prevents accidental upgrade |

---

## Phase Ordering Recommendation

The three v1.8 capabilities have no code-level dependencies on each other. The following order is recommended based on risk profile and value delivery:

**Phase 1 — Admin Container**
Build `app/admin_main.py`, update `docker-compose.yml` with `profiles: [admin]`, rename the admin cookie to `admin_token`, remove the hardcoded `SECRET_KEY` default from compose. This is the highest-risk capability (cookie collision is a silent security bug) and the most architecturally self-contained. Delivering it first validates the two-container compose setup before backup complexity is added.

**Phase 2 — Database Backup**
Build `app/backup/` package, add PyMongo EJSON export, add aioboto3 S3 upload, wire APScheduler into the operator app's lifespan (gated by `BACKUP_SCHEDULE`), add named volume to compose. Add new deps to `pyproject.toml` (`apscheduler>=3.10,<4`, `aioboto3>=13,<16`). This phase has the most moving parts (scheduler, S3, volume config) and benefits from admin container already being validated in compose.

**Phase 3 — Docs Rewrite**
Rewrite all `docs/*.md` files covering v1.0–v1.8 features. Update `mkdocs.yml` nav. Add load-bearing comment to the `html=True` StaticFiles mount. Run `mkdocs build`, commit `site/`. Lowest risk; pure content work; best done last so it can document the admin container and backup features shipped in phases 1 and 2.

**Research flags:**
- Phase 1 (Admin Container): No further research needed. Architecture is fully specified (`admin_main.py`, `profiles: [admin]`, `admin_token` cookie). All patterns are standard FastAPI.
- Phase 2 (Backup): The pure-Python vs `mongodump` subprocess question is resolved (pure-Python recommended), but the exact EJSON field mapping for restore should be validated during implementation. S3 upload atomicity and lifecycle rule are operational, not code concerns.
- Phase 3 (Docs): No research needed. Whether to include interactive API reference is an open question (see below) but does not block rewrite of prose content.

---

## Open Questions

The following questions need a decision before or during planning. None blocks starting Phase 1.

1. **Interactive API reference in docs:** Should `/guide` include an embedded Swagger UI page? If yes, `mkdocs-swagger-ui-tag` must be added to dev dependencies and a `docs/openapi.json` export step added to the build workflow. If no, docs remain prose-only. Decision needed before Phase 3 planning.

2. **Backup schedule default in compose:** Should `docker-compose.yml` include a commented-out example `BACKUP_SCHEDULE` env var (e.g., `# BACKUP_SCHEDULE=0 2 * * *`) to guide operators? Or should all backup config be documented only in the guide? Affects compose template and docs simultaneously.

3. **Bind mount vs named volume for backups:** Named volume (`backups:/app/backups`) is managed by Docker and survives restarts but is not directly accessible from the host filesystem without `docker cp`. Bind mount (`./backups:/app/backups`) is host-visible and easier for operators to verify backup files exist. For a self-hosted ham radio app, bind mount is arguably better UX. Decision needed before Phase 2 planning.

4. **Admin bootstrap in `admin_main.py` lifespan:** The operator service's lifespan calls `_bootstrap_admin()` at startup (idempotent). The admin container's minimal lifespan omits this call. This is safe as long as the operator service has run at least once. Clarify whether the admin container should also call `_bootstrap_admin()` (defensive, idempotent, negligible cost) or rely on operator service having already run it.

5. **`mongodump` vs pure-Python EJSON:** Research recommends pure-Python for simplicity, but pure-Python EJSON export does not produce a `mongorestore`-compatible binary archive (it produces NDJSON importable via `mongoimport`). If the restore path must use `mongorestore` (not `mongoimport`), the Dockerfile `apt-get install mongodb-database-tools` path is required. Confirm the acceptable restore method before Phase 2.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Admin container architecture | HIGH | Directly grounded in live codebase inspection of all router files, `docker-compose.yml`, and `app/main.py`. Approach decision (separate entry point) is unambiguous. |
| Cookie collision pitfall | HIGH | RFC 6265 Section 5.1.3 + Firefox Bugzilla #469287 confirm real-world behavior. Prevention (rename cookie) is unambiguous. |
| Backup: pure-Python export | HIGH | `python:3.12-slim` confirmed without MongoDB Database Tools. PyMongo + `bson.json_util` is standard. Volume ephemerality confirmed by compose inspection. |
| Backup: APScheduler 3.x | HIGH | Official docs confirm `AsyncIOScheduler` + `CronTrigger.from_crontab()`. `<4` ceiling confirmed by APScheduler 4 alpha status on PyPI. |
| Backup: aioboto3 | MEDIUM-HIGH | API confirmed in docs and PyPI. `>=13,<16` pin is conservative. `upload_fileobj` async pattern confirmed in library source. |
| Docs: MkDocs Material | HIGH | Live `mkdocs.yml` + `site/` inspection. `html=True` load-bearing status confirmed by reading `main.py` line 151 and MkDocs `use_directory_urls` docs. |
| Docs: swagger plugin choice | MEDIUM | `mkdocs-swagger-ui-tag` confirmed static. CDN issue with render-swagger confirmed. Interaction with this project's specific MkDocs version not directly tested. |

**Overall confidence:** HIGH

**Gaps to address during implementation:**
- EJSON restore fidelity vs `mongorestore` binary format — confirm acceptable restore method before writing `dump.py`.
- `admin_main.py` bootstrap call decision — confirm before writing admin lifespan.
- Interactive API reference decision — confirm before Phase 3 planning to avoid mid-docs-rewrite plugin integration work.

---

## Sources

### Primary (HIGH confidence — official docs and live codebase)
- RFC 6265 Section 5.1.3 — cookie port exclusion (rfc-editor.org/rfc/rfc6265)
- Firefox Bugzilla #469287 — real-world cookie port-sharing confirmation
- APScheduler 3.x User Guide + CronTrigger docs — scheduler integration pattern
- APScheduler 4.0 Migration Guide — alpha status and API redesign confirmation
- Docker Compose profiles documentation — `profiles:` semantics
- FastAPI Bigger Applications docs — `include_router` and app factory patterns
- MongoDB Database Tools installation docs — `mongodump` package requirements
- Docker Hub python:3.12-slim layer manifest — confirmed absence of mongodb-database-tools
- AWS S3 PutObject atomicity guarantee + multipart upload docs
- MkDocs Material `use_directory_urls` documentation
- Live codebase inspection: `docker-compose.yml`, `Dockerfile`, `app/main.py`, `app/config.py`, `app/database.py`, `app/admin/router.py`, `app/admin/ui_router.py`, `mkdocs.yml`

### Secondary (MEDIUM confidence)
- aioboto3 PyPI + usage docs — version pinning and `upload_fileobj` async pattern
- mkdocs-swagger-ui-tag GitHub (blueswen) — static asset bundling confirmed
- Beanie initialization docs — module-level state pattern (global init risk)
- MkDocs Material issue #3070 — `navigation.indexes` + `navigation.sections` incompatibility

### Tertiary (LOW confidence)
- Docker Compose v5.0.1 WSL2 `COMPOSE_PROFILES` env var edge case — single issue report, resolution status unclear; use `--profile` CLI flag for production deployments as a safe alternative

---

*Research completed: 2026-04-10*
*Ready for roadmap: yes*
