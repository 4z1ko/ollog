# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v1.9 Admin & Login UI Redesign

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-04-11 — Milestone v1.9 started

## Performance Metrics

**Velocity (historical):**
- Total plans completed: 47 (v1.0: 19, v1.1: 7, v1.2: 2, v1.3: 8, v1.4: 4, v1.5: 4, v1.6: 2, v1.7: 4, v1.8: 1)
- Average duration: ~5–20 min/plan

**By Milestone:**

| Milestone | Phases | Plans |
|-----------|--------|-------|
| v1.0 | 1–6 | 19 |
| v1.1 | 7–10 | 7 |
| v1.2 | 11–12 | 2 |
| v1.3 | 13–15 | 8 |
| v1.4 | 16–18 | 4 |
| v1.5 | 19–22 | 4 |
| v1.6 | 23–24 | 2 |
| v1.7 | 25–28 | 4 |
| v1.8 | 29–31 | 3 (all complete) |

## Accumulated Context

### v1.8 Milestone Goals

1. **Admin Container** — Separate Docker Compose service (shared image), port 8001, admin-only routes (/admin/*, /auth, /health), stoppable independently without affecting operator app
2. **Database Backup** — `python -m app.backup` CLI → PyMongo EJSON .gz to ./backups/<timestamp>.gz; BACKUP_SCHEDULE cron env var + S3 credentials for automated scheduled uploads
3. **Docs Rewrite** — Full comprehensive rewrite of /guide covering all features from v1.0–v1.8 (2-level nav, interactive API reference via mkdocs-swagger-ui-tag)

### Key Architecture Decisions (v1.8)

- **ADM:** `app/admin_main.py` is a standalone FastAPI entry point — NOT `app/main.py` with an APP_MODE flag; `admin_main.py` must never import from `app.main`
- **ADM:** Admin cookie is `admin_token` (not `access_token`) — RFC 6265 excludes port from cookie scope; name collision between ports 8000 and 8001 is guaranteed without rename
- **ADM:** Admin lifespan calls `init_db()` + `_bootstrap_admin()` only — no UDP listener, no SSE change-stream watcher
- **ADM:** `init_beanie()` must include full `document_models=[QSO, User, ApiToken]` list in admin app to prevent `CollectionWasNotInitialized`
- **ADM:** `SECRET_KEY=dev-secret-change-in-production` hardcoded default removed from `docker-compose.yml`; must come from `.env`
- **BAK:** Pure-Python PyMongo + `bson.json_util.dumps()` EJSON (no `mongodump` subprocess — not in `python:3.12-slim`)
- **BAK:** Bind mount `./backups:/app/backups` in docker-compose.yml (host-visible; survives restarts)
- **BAK:** APScheduler 3.x `AsyncIOScheduler` + `CronTrigger.from_crontab()`; pin `apscheduler>=3.10,<4`
- **BAK:** `aioboto3>=13,<16` for async S3 upload inside lifespan; standard boto3 credential chain
- **BAK:** `BACKUP_SCHEDULE` defaults to `None`; scheduler not started when absent (mirrors `udp_enabled` guard)
- **BAK:** Backup asyncio task tracked in lifespan `yield` block, cancelled + awaited on shutdown (mirrors change-stream watcher)
- **DOC:** `mkdocs-swagger-ui-tag` (static assets bundled, no CDN) — NOT `mkdocs-render-swagger-plugin`
- **DOC:** `openapi.json` exported with `python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > docs/openapi.json` before `mkdocs build`
- **DOC:** `html=True` on `StaticFiles(directory="site", html=True)` in `app/main.py` is load-bearing for MkDocs `use_directory_urls: true`; must be annotated with a comment
- **DOC:** Do not activate both `navigation.indexes` and `navigation.sections` simultaneously (MkDocs Material issue #3070)
- **DOC:** `not_in_nav: | openapi.json` suppresses MkDocs INFO/WARNING about openapi.json not in nav — required when openapi.json lives in docs/ for swagger-ui-tag src path resolution
- **DOC:** openapi.json path count for operator app is 11 unique paths (16 operations) — admin endpoints are in admin_main.py and excluded from operator OpenAPI schema by design

### Key Decisions (v1.7 — carried forward)

Full decision log in PROJECT.md Key Decisions table.

- HMAC-SHA256 for token hashing (not Argon2 — 200-500ms verify is unacceptable per request)
- Separate `api_tokens` Beanie collection (not embedded in User)
- `X-API-Key` header (not `Authorization: Bearer`) — clean separation from JWT session auth
- `APP_OLLOG_TOKEN` fixed ADIF field name (APP_ prefix per ADIF spec convention)
- `auto_error=False` on both optional schemes; raise HTTP 401 manually
- Lazy cache invalidation with `_dirty=True` flag (UDPTokenCache)

### Known Tech Debt

- `QSO.find_active()` in models.py — dead production code
- `from_mongo_dt()` in utils.py — tested, not called in production
- Docker end-to-end verification pending (requires live Docker environment)

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-11
Stopped at: Completed 031-01-PLAN.md — comprehensive docs rewrite (25 pages, Swagger UI, v1.8 content, mkdocs build --strict exit 0)
Resume file: None
