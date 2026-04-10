# Roadmap: ollog — Ham Radio Online Logbook

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-04)
- ✅ **v1.1 Operator & Station Profiles** — Phases 7–10 (shipped 2026-04-04)
- ✅ **v1.2 Callsign Entity Lookup & Country Flags** — Phases 11–12 (shipped 2026-04-04)
- ✅ **v1.3 Documentation** — Phases 13–15 (shipped 2026-04-05)
- ✅ **v1.4 UDP Interface** — Phases 16–18 (shipped 2026-04-06)
- ✅ **v1.5 Documentation Update** — Phases 19–22 (shipped 2026-04-08)
- ✅ **v1.6 Live Log Table** — Phases 23–24 (shipped 2026-04-08)
- ✅ **v1.7 API Token Auth** — Phases 25–28 (shipped 2026-04-09)


## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–6) — SHIPPED 2026-04-04</summary>

- [x] Phase 1: Foundation (4/4 plans) — completed 2026-04-03
- [x] Phase 2: Admin & Accounts (2/2 plans) — completed 2026-04-03
- [x] Phase 3: QSO Entry & Log View (4/4 plans) — completed 2026-04-03
- [x] Phase 4: ADIF Import & Export (4/4 plans) — completed 2026-04-03
- [x] Phase 5: Multi-Operator & Live Feed (4/4 plans) — completed 2026-04-04
- [x] Phase 6: Navigation Fix (1/1 plan) — completed 2026-04-04

Full archive: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 Operator & Station Profiles (Phases 7–10) — SHIPPED 2026-04-04</summary>

- [x] Phase 7: Profile Data Model and Grid Utility (2/2 plans) — completed 2026-04-04
- [x] Phase 8: Profile Service, Schemas, and API Router (2/2 plans) — completed 2026-04-04
- [x] Phase 9: QSO Auto-Stamping (1/1 plan) — completed 2026-04-04
- [x] Phase 10: Profile UI (2/2 plans) — completed 2026-04-04

Full archive: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 Callsign Entity Lookup & Country Flags (Phases 11–12) — SHIPPED 2026-04-04</summary>

- [x] Phase 11: Prefix Resolver Module — completed 2026-04-04
- [x] Phase 12: Flag Display Integration — completed 2026-04-04

Full archive: `.planning/milestones/v1.2-ROADMAP.md`

</details>

<details>
<summary>✅ v1.3 Documentation (Phases 13–15) — SHIPPED 2026-04-05</summary>

- [x] Phase 13: OpenAPI Schema Cleanup (2/2 plans) — completed 2026-04-04
- [x] Phase 14: MkDocs Infrastructure (2/2 plans) — completed 2026-04-04
- [x] Phase 15: Narrative Documentation Content (4/4 plans) — completed 2026-04-05

Full archive: `.planning/milestones/v1.3-ROADMAP.md`

</details>

<details>
<summary>✅ v1.4 UDP Interface (Phases 16–18) — SHIPPED 2026-04-06</summary>

- [x] Phase 16: UDP Infrastructure (2/2 plans) — completed 2026-04-06
- [x] Phase 17: QSO Processing Pipeline (1/1 plan) — completed 2026-04-06
- [x] Phase 18: Error Handling and Observability (1/1 plan) — completed 2026-04-06

Full archive: `.planning/milestones/v1.4-ROADMAP.md`

</details>

<details>
<summary>✅ v1.5 Documentation Update (Phases 19–22) — SHIPPED 2026-04-08</summary>

- [x] Phase 19: Deployment Guide — UDP Configuration (1/1 plan) — completed 2026-04-08
- [x] Phase 20: Getting-Started Guide — Sending QSOs via UDP (1/1 plan) — completed 2026-04-08
- [x] Phase 21: Troubleshooting Guide — UDP Issues (1/1 plan) — completed 2026-04-08
- [x] Phase 22: Static Site Rebuild (1/1 plan) — completed 2026-04-08

Full archive: `.planning/milestones/v1.5-ROADMAP.md`

</details>

<details>
<summary>✅ v1.6 Live Log Table (Phases 23–24) — SHIPPED 2026-04-08</summary>

- [x] Phase 23: SSE-Triggered Log Table Reload (1/1 plan) — completed 2026-04-08
- [x] Phase 24: Session Robustness (1/1 plan) — completed 2026-04-08

Full archive: `.planning/milestones/v1.6-ROADMAP.md`

</details>

---

### ✅ v1.7 API Token Auth (Phases 25–28) — SHIPPED 2026-04-09

**Milestone Goal:** Operators can create named API tokens from Profile Settings and use them to authenticate REST API calls (`X-API-Key` header) and identify themselves in UDP ADIF datagrams (`APP_OLLOG_TOKEN` field).

- [x] **Phase 25: Token Model and Service Layer** — `ApiToken` Beanie document, HMAC-SHA256 helpers, `api_token_secret` config; foundation for all subsequent token phases
- [x] **Phase 26: Token CRUD API and Profile UI** — REST endpoints for token lifecycle (create/list/revoke) behind JWT, HTMX token section in Profile Settings with show-once plaintext banner; covers TOK-01–04
- [x] **Phase 27: X-API-Key REST Authentication** — combined JWT + API-key dependency with `auto_error=False`, opt-in on all QSO endpoints; covers API-01–03
- [x] **Phase 28: UDP APP_OLLOG_TOKEN Support** — per-datagram in-memory HMAC cache, `APP_OLLOG_TOKEN` field resolution in `_handle_datagram`, `UDP_OPERATOR` fallback preserved; covers UDP-01–03

---

### v1.8 Admin Isolation, Backup & Docs

**Milestone Goal:** The admin console runs as an independent Docker service on port 8001 (admin-only routes, stoppable without affecting the operator app), operators can create local point-in-time backups via CLI and schedule automated S3 uploads via a cron env var, and `/guide` is fully rewritten to cover all features from v1.0–v1.8.

- [ ] **Phase 29: Admin Container Isolation** — `app/admin_main.py` standalone entry point, `admin_token` cookie, `profiles: [admin]` compose service on port 8001, `SECRET_KEY` default removed; covers ADM-01–07
- [ ] **Phase 30: Database Backup CLI and Scheduler** — `app/backup/` package with PyMongo EJSON export, APScheduler 3.x cron scheduler, aioboto3 S3 upload, bind mount and lifespan wiring; covers BAK-01–08
- [ ] **Phase 31: Comprehensive Docs Rewrite** — full `docs/*.md` rewrite covering v1.0–v1.8, 2-level nav, `mkdocs-swagger-ui-tag` interactive API reference, `html=True` load-bearing comment, `mkdocs build` zero-warning rebuild; covers DOC-01–08

---

## Phase Details

### Phase 25: Token Model and Service Layer

**Goal:** The `ApiToken` Beanie document exists as a registered MongoDB collection with all fields, indexes, and pure HMAC-SHA256 service helpers in place — making the rest of v1.7 buildable and independently testable.
**Depends on:** Phase 24 (v1.6 complete)
**Requirements:** *(foundation phase — no directly observable v1.7 requirements; enables Phase 26–28)*
**Success Criteria** (what must be TRUE):
  1. `ApiToken` collection exists in MongoDB after app startup with the correct compound index on `(token_prefix, user_id)`
  2. `generate_api_token()` returns a string starting with `ollog_` containing 256 bits of URL-safe entropy
  3. `hash_api_token()` and `verify_api_token()` use HMAC-SHA256 (not Argon2); `verify_api_token()` is constant-time via `hmac.compare_digest`
  4. `api_token_secret` is loaded from `Settings` as a `SecretStr` separate from `SECRET_KEY`
  5. Token name validation rejects names outside alphanumeric + hyphen/underscore, 1–80 chars
**Plans:** 1 plan

Plans:
- [x] 025-01-PLAN.md — ApiToken model, HMAC-SHA256 service helpers, config, and tests

---

### Phase 26: Token CRUD API and Profile UI

**Goal:** Operators can create named API tokens, see them listed in Profile Settings, and revoke them — with the plaintext token shown exactly once at creation.
**Depends on:** Phase 25
**Requirements:** TOK-01, TOK-02, TOK-03, TOK-04
**Success Criteria** (what must be TRUE):
  1. Operator can submit a token creation form in Profile Settings with a required name and optional expiry date; the response shows the full plaintext token in a banner marked "will not be shown again"
  2. After closing or dismissing the creation banner, the plaintext token cannot be recovered — revisiting the profile page shows only the token prefix, label, creation date, and expiry
  3. The active token list displays label, creation date, expiry (or "Never"), and the first 8 characters of the token for identification
  4. Operator can revoke any individual token; the token immediately stops being accepted for authentication on subsequent requests
**Plans:** 1 plan

Plans:
- [ ] 026-01-PLAN.md — expires_at model patch, REST CRUD /api/tokens, HTMX profile UI, templates, and integration tests

---

### Phase 27: X-API-Key REST Authentication

**Goal:** All QSO REST API endpoints accept `X-API-Key: <token>` as a valid alternative to JWT Bearer, with identical operator isolation and correct HTTP 401 responses for invalid or missing credentials.
**Depends on:** Phase 26
**Requirements:** API-01, API-02, API-03
**Success Criteria** (what must be TRUE):
  1. A `curl` request to any QSO endpoint with `X-API-Key: <valid-token>` succeeds and returns the authenticated operator's data — no JWT needed
  2. The operator identity resolved from an API key is identical to the identity resolved from a JWT for the same operator — no cross-operator data access is possible
  3. A request with a missing, invalid, or expired credential (both JWT and API key absent or wrong) returns HTTP 401 — never HTTP 403
  4. Admin and profile endpoints continue to require JWT; they do not accept `X-API-Key` authentication
**Plans:** 1 plan

Plans:
- [ ] 027-01-PLAN.md — dual-auth dependencies (JWT + X-API-Key), QSO router Depends() swap, isolation audit update, integration tests

---

### Phase 28: UDP APP_OLLOG_TOKEN Support

**Goal:** UDP datagrams containing `APP_OLLOG_TOKEN` resolve operator identity from that token value per datagram, enabling multi-operator UDP setups — while datagrams without the field continue to fall back to `UDP_OPERATOR` with no regression.
**Depends on:** Phase 25
**Requirements:** UDP-01, UDP-02, UDP-03
**Success Criteria** (what must be TRUE):
  1. A UDP datagram containing a valid `APP_OLLOG_TOKEN` field is accepted and the QSO is logged under the operator whose token matches — not the `UDP_OPERATOR` config value
  2. A UDP datagram containing an invalid or revoked `APP_OLLOG_TOKEN` is rejected with a structured log line; it does not fall through silently to `UDP_OPERATOR`
  3. A UDP datagram without `APP_OLLOG_TOKEN` is processed exactly as before using `UDP_OPERATOR` — existing behavior is unchanged
  4. The in-memory token cache is loaded at startup and refreshed when any token is created or revoked; no MongoDB round-trip occurs per datagram
**Plans:** 1 plan

Plans:
- [ ] 028-01-PLAN.md — UDPTokenCache singleton, _handle_datagram APP_OLLOG_TOKEN branch, notify_refresh() wiring, tests

---

### Phase 29: Admin Container Isolation

**Goal:** Admin routes (`/admin/*`, `/auth`, `/health`) run as a separate Docker Compose service on port 8001, startable and stoppable independently without affecting the operator app on port 8000.
**Depends on:** Phase 28 (v1.7 complete)
**Requirements:** ADM-01, ADM-02, ADM-03, ADM-04, ADM-05, ADM-06, ADM-07
**Architecture decisions:**
  - Entry point is `app/admin_main.py` (standalone FastAPI app — NOT `app/main.py` with a mode flag); `admin_main.py` must never import from `app.main`
  - Admin cookie renamed to `admin_token`; operator `access_token` cookie is untouched (RFC 6265 port exclusion means both containers share the same cookie jar on `localhost`)
  - Admin lifespan calls `init_db()` and `_bootstrap_admin()` only — no UDP listener, no SSE change-stream watcher
  - `init_beanie()` called with full `document_models=[QSO, User, ApiToken]` list to prevent `CollectionWasNotInitialized` on any shared code path
  - `SECRET_KEY=dev-secret-change-in-production` default removed from `docker-compose.yml`; value must come from `.env` so Pydantic required-field validation fires if absent
**Success Criteria** (what must be TRUE):
  1. Running `docker compose --profile admin up` starts both `app` (port 8000) and `admin` (port 8001) services; running `docker compose up` starts only `app` — the admin service does not appear
  2. The admin container serves `/admin/*` and `/auth` and returns HTTP 200 on `/health`; a request to `/log/` or `/api/` on port 8001 returns HTTP 404
  3. Stopping the admin container (`docker compose --profile admin stop admin`) does not affect the operator app — QSO logging on port 8000 continues uninterrupted
  4. An admin who logs in on port 8001 uses cookie `admin_token`; the operator app's `access_token` cookie is untouched and continues to function on port 8000
  5. Starting the operator or admin service without `SECRET_KEY` in `.env` fails at startup with a Pydantic validation error — the hardcoded default is no longer present in `docker-compose.yml`
**Plans:** 1 plan

Plans:
- [ ] 029-01-PLAN.md — admin_main.py entry point, admin_token cookie rename, docker-compose.yml admin service + profiles, SECRET_KEY default removal

---

### Phase 30: Database Backup CLI and Scheduler

**Goal:** `python -m app.backup` produces a gzip EJSON export of all MongoDB collections to `./backups/<timestamp>.gz`, with optional scheduled S3 upload via `BACKUP_SCHEDULE` cron env var — and backup files survive container restarts via bind mount.
**Depends on:** Phase 29
**Requirements:** BAK-01, BAK-02, BAK-03, BAK-04, BAK-05, BAK-06, BAK-07, BAK-08
**Architecture decisions:**
  - Package layout: `app/backup/__main__.py`, `dump.py`, `upload.py`, `scheduler.py`
  - Export method: pure-Python PyMongo + `bson.json_util.dumps()` EJSON (no `mongodump` subprocess — not available in `python:3.12-slim`)
  - Volume: bind mount `./backups:/app/backups` in `docker-compose.yml` (host-visible, survives restarts)
  - Scheduler: APScheduler 3.x `AsyncIOScheduler` + `CronTrigger.from_crontab()`; pinned `apscheduler>=3.10,<4`
  - S3 upload: `aioboto3>=13,<16` for async path inside lifespan; standard boto3 credential chain (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`)
  - Output path: `BACKUP_DIR` env var (default `/app/backups`); no hardcoded relative paths
  - Scheduler guard: `BACKUP_SCHEDULE` defaults to `None`; scheduler does not start when absent (mirrors `udp_enabled` pattern)
  - Lifespan: backup asyncio task tracked in `yield` block, cancelled and awaited on shutdown (mirrors change-stream watcher pattern)
**Success Criteria** (what must be TRUE):
  1. Running `python -m app.backup` outside the container produces a file at `./backups/<timestamp>.gz`; `gunzip` and inspection show NDJSON with EJSON-encoded BSON types; stdout confirms success with the output path
  2. The `.gz` file persists after `docker compose restart` — it is present on the host filesystem at `./backups/<timestamp>.gz` without `docker cp`
  3. When `BACKUP_SCHEDULE=0 2 * * *` is set, the operator app logs a scheduler start message at startup; a backup file appears in `./backups/` at the scheduled time without manual invocation
  4. When `BACKUP_SCHEDULE` is not set, the operator app starts normally with no scheduler log lines and no APScheduler import errors
  5. When all four S3 env vars are set, each backup (CLI or scheduled) is uploaded to the configured S3 bucket after local write; an S3 upload failure logs at ERROR level, leaves the local `.gz` intact, and exits with code 0
**Plans:** 1 plan

Plans:
- [ ] 030-01-PLAN.md — app/backup/ package, PyMongo EJSON dump, aioboto3 S3 upload, APScheduler lifespan wiring, bind mount, pyproject.toml deps

---

### Phase 31: Comprehensive Docs Rewrite

**Goal:** `/guide` covers all features from v1.0–v1.8 with a 2-level grouped nav structure and an embedded interactive API reference — and `mkdocs build` completes with zero warnings.
**Depends on:** Phase 30
**Requirements:** DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06, DOC-07, DOC-08
**Architecture decisions:**
  - Plugin: `mkdocs-swagger-ui-tag` (static assets bundled — no CDN dependency; works offline and on hamnet); NOT `mkdocs-render-swagger-plugin`
  - `openapi.json` export: `python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > docs/openapi.json` as a pre-build step (importable without a running database because `init_db()` is lifespan-scoped)
  - `html=True` on `StaticFiles(directory="site", html=True)` in `app/main.py` is load-bearing for MkDocs `use_directory_urls: true`; annotate with an explicit comment before shipping
  - Nav: 2-level grouped sections — Getting Started, Operator Guide, Admin Guide, API Reference, Reference, Troubleshooting
  - Do not activate both `navigation.indexes` and `navigation.sections` in `mkdocs.yml` simultaneously (documented MkDocs Material incompatibility, issue #3070)
  - Built `site/` committed to the repository; served by existing FastAPI `StaticFiles` mount at `/guide`
**Success Criteria** (what must be TRUE):
  1. Every feature shipped in v1.0–v1.8 is reachable from `/guide` in at most two nav clicks — no milestone's features are absent from the site
  2. The nav renders as a 2-level grouped structure matching the defined sections (Getting Started, Operator Guide, Admin Guide, API Reference, Reference, Troubleshooting); no flat single-level nav remains
  3. The API Reference page at `/guide/api-reference/` embeds a functional Swagger UI with no CDN requests — all assets are served from `/guide` static files
  4. Admin container setup (port 8001, `--profile admin` flag, `admin_token` cookie) and backup CLI (`python -m app.backup`, `BACKUP_SCHEDULE`, S3 env vars) are each documented in the Admin Guide section
  5. `mkdocs build` exits with zero warnings; the rebuilt `site/` is committed and the `/guide` route in the running app serves the updated content
**Plans:** 1 plan

Plans:
- [ ] 031-01-PLAN.md — docs/*.md rewrite, mkdocs.yml nav restructure, mkdocs-swagger-ui-tag integration, openapi.json export, html=True comment, mkdocs build

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 4/4 | ✓ Complete | 2026-04-03 |
| 2. Admin & Accounts | v1.0 | 2/2 | ✓ Complete | 2026-04-03 |
| 3. QSO Entry & Log View | v1.0 | 4/4 | ✓ Complete | 2026-04-03 |
| 4. ADIF Import & Export | v1.0 | 4/4 | ✓ Complete | 2026-04-03 |
| 5. Multi-Operator & Live Feed | v1.0 | 4/4 | ✓ Complete | 2026-04-04 |
| 6. Navigation Fix | v1.0 | 1/1 | ✓ Complete | 2026-04-04 |
| 7. Profile Data Model and Grid Utility | v1.1 | 2/2 | ✓ Complete | 2026-04-04 |
| 8. Profile Service, Schemas, and API Router | v1.1 | 2/2 | ✓ Complete | 2026-04-04 |
| 9. QSO Auto-Stamping | v1.1 | 1/1 | ✓ Complete | 2026-04-04 |
| 10. Profile UI | v1.1 | 2/2 | ✓ Complete | 2026-04-04 |
| 11. Prefix Resolver Module | v1.2 | 1/1 | ✓ Complete | 2026-04-04 |
| 12. Flag Display Integration | v1.2 | 1/1 | ✓ Complete | 2026-04-04 |
| 13. OpenAPI Schema Cleanup | v1.3 | 2/2 | ✓ Complete | 2026-04-04 |
| 14. MkDocs Infrastructure | v1.3 | 2/2 | ✓ Complete | 2026-04-04 |
| 15. Narrative Documentation Content | v1.3 | 4/4 | ✓ Complete | 2026-04-05 |
| 16. UDP Infrastructure | v1.4 | 2/2 | ✓ Complete | 2026-04-06 |
| 17. QSO Processing Pipeline | v1.4 | 1/1 | ✓ Complete | 2026-04-06 |
| 18. Error Handling and Observability | v1.4 | 1/1 | ✓ Complete | 2026-04-06 |
| 19. Deployment Guide — UDP Configuration | v1.5 | 1/1 | ✓ Complete | 2026-04-08 |
| 20. Getting-Started Guide — Sending QSOs via UDP | v1.5 | 1/1 | ✓ Complete | 2026-04-08 |
| 21. Troubleshooting Guide — UDP Issues | v1.5 | 1/1 | ✓ Complete | 2026-04-08 |
| 22. Static Site Rebuild | v1.5 | 1/1 | ✓ Complete | 2026-04-08 |
| 23. SSE-Triggered Log Table Reload | v1.6 | 1/1 | ✓ Complete | 2026-04-08 |
| 24. Session Robustness | v1.6 | 1/1 | ✓ Complete | 2026-04-08 |
| 25. Token Model and Service Layer | v1.7 | 1/1 | ✓ Complete | 2026-04-09 |
| 26. Token CRUD API and Profile UI | v1.7 | 1/1 | ✓ Complete | 2026-04-09 |
| 27. X-API-Key REST Authentication | v1.7 | 1/1 | ✓ Complete | 2026-04-09 |
| 28. UDP APP_OLLOG_TOKEN Support | v1.7 | 1/1 | ✓ Complete | 2026-04-09 |
| 29. Admin Container Isolation | v1.8 | 0/1 | ⬜ Planned | — |
| 30. Database Backup CLI and Scheduler | v1.8 | 0/1 | ⬜ Planned | — |
| 31. Comprehensive Docs Rewrite | v1.8 | 0/1 | ⬜ Planned | — |
