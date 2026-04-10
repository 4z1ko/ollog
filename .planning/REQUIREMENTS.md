# Requirements: v1.8 Admin Isolation, Backup & Docs

**Milestone:** v1.8
**Goal:** The admin console runs as an independent Docker service on port 8001 (admin-only routes, stoppable without affecting the operator app), operators and admins can create local point-in-time backups via CLI and schedule automated uploads to AWS S3 via a cron env var, and the /guide documentation site is fully rewritten to comprehensively cover all features from v1.0–v1.8.

---

## ADMIN Requirements (ADM)

**ADM-01** — A new Docker Compose service (`admin`) uses the same image as the operator service but runs `app/admin_main.py` on port 8001, gated behind `profiles: [admin]` so it does not start by default.

**ADM-02** — The admin container exposes only admin routes (`/admin/*`, `/auth`) and its own `/health` endpoint; it does not serve operator routes (`/log/*`, `/api/*`).

**ADM-03** — The admin container's FastAPI lifespan calls `init_db()` and `_bootstrap_admin()` only — no UDP listener, no SSE change-stream watcher.

**ADM-04** — The admin container uses cookie name `admin_token` (not `access_token`) to prevent cookie collision with the operator container on the same hostname (RFC 6265 port exclusion).

**ADM-05** — A JWT issued by the operator container is accepted by the admin container (same `SECRET_KEY`); users do not need to re-authenticate when switching between containers.

**ADM-06** — The hardcoded `SECRET_KEY=dev-secret-change-in-production` default is removed from `docker-compose.yml`; the value must be provided via `.env` (existing Pydantic required-field validation fires if absent).

**ADM-07** — The operator container (`app/main.py`, port 8000) is completely unchanged by this work; adding the admin service does not break or modify any existing operator behavior.

---

## BACKUP Requirements (BAK)

**BAK-01** — `python -m app.backup` produces a point-in-time EJSON export of all MongoDB collections to `./backups/<timestamp>.gz` (NDJSON, gzip-compressed, importable via `mongoimport`); confirmation is printed to stdout on success.

**BAK-02** — The backup module uses pure-Python PyMongo + `bson.json_util.dumps()` for export — no `mongodump` subprocess (not available in `python:3.12-slim`).

**BAK-03** — `docker-compose.yml` declares a bind mount (`./backups:/app/backups`) so backup files survive container restarts and are directly accessible on the host filesystem.

**BAK-04** — When `BACKUP_SCHEDULE` env var is set (cron string, e.g. `0 2 * * *`), the operator app starts an APScheduler 3.x `AsyncIOScheduler` background task that runs the backup on schedule; when `BACKUP_SCHEDULE` is absent, no scheduler starts (mirrors the `udp_enabled` guard pattern).

**BAK-05** — When `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_DEFAULT_REGION` are all set, each backup (scheduled or CLI) uploads the `.gz` file to S3 after successful local write; S3 upload failures are logged at ERROR level, do not delete the local file, and do not cause a non-zero exit code.

**BAK-06** — `docker-compose.yml` includes a commented-out `# BACKUP_SCHEDULE=0 2 * * *` example in the operator service env block.

**BAK-07** — The backup asyncio task is tracked in the lifespan `yield` block and cancelled + awaited on shutdown (mirrors the change-stream watcher pattern in `app/main.py`).

**BAK-08** — The `BACKUP_DIR` env var (default `/app/backups`) controls the output path; the module never uses a hardcoded relative path.

---

## DOCS Requirements (DOC)

**DOC-01** — The `/guide` site is fully rewritten to cover all features from v1.0–v1.8; no feature shipped in a previous milestone is left undocumented.

**DOC-02** — The MkDocs nav is restructured into a 2-level grouped layout with sections: Getting Started, Operator Guide, Admin Guide, API Reference, Reference, Troubleshooting.

**DOC-03** — An interactive API reference page is embedded using `mkdocs-swagger-ui-tag` (static assets, no CDN dependency); `openapi.json` is exported from the running app as a pre-build step.

**DOC-04** — The admin container setup (port 8001, profiles flag, admin_token cookie) is documented in the Admin Guide section.

**DOC-05** — The backup CLI and S3 scheduled backup setup are documented in the Admin Guide section.

**DOC-06** — The API token feature (v1.7) is documented: creation, listing, revocation, usage with `X-API-Key` header and UDP `APP_OLLOG_TOKEN` field.

**DOC-07** — The `html=True` argument on the `StaticFiles` mount in `app/main.py` is annotated with a comment explaining it is load-bearing for MkDocs `use_directory_urls: true` behavior.

**DOC-08** — `mkdocs build` succeeds with zero warnings after the rewrite; the rebuilt `site/` is committed to the repository.

---

## Non-Goals (v1.8)

- Admin UI feature additions (no new admin pages beyond what already exists)
- Backup restore automation (restore path is manual `mongoimport` — no automated restore CLI)
- Incremental/differential backups (point-in-time full export only)
- Multi-region S3 replication
- MkDocs versioning (`mike` plugin)

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ADM-01 | Phase 29 | Pending |
| ADM-02 | Phase 29 | Pending |
| ADM-03 | Phase 29 | Pending |
| ADM-04 | Phase 29 | Pending |
| ADM-05 | Phase 29 | Pending |
| ADM-06 | Phase 29 | Pending |
| ADM-07 | Phase 29 | Pending |
| BAK-01 | Phase 30 | Pending |
| BAK-02 | Phase 30 | Pending |
| BAK-03 | Phase 30 | Pending |
| BAK-04 | Phase 30 | Pending |
| BAK-05 | Phase 30 | Pending |
| BAK-06 | Phase 30 | Pending |
| BAK-07 | Phase 30 | Pending |
| BAK-08 | Phase 30 | Pending |
| DOC-01 | Phase 31 | Pending |
| DOC-02 | Phase 31 | Pending |
| DOC-03 | Phase 31 | Pending |
| DOC-04 | Phase 31 | Pending |
| DOC-05 | Phase 31 | Pending |
| DOC-06 | Phase 31 | Pending |
| DOC-07 | Phase 31 | Pending |
| DOC-08 | Phase 31 | Pending |
