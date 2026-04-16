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
- ✅ **v1.8 Admin Isolation, Backup & Docs** — Phases 29–31 (shipped 2026-04-10)
- ✅ **v1.9 Admin & Login UI Redesign** — Phases 32–36 (shipped 2026-04-11)
- ✅ **v2.0 Database Backup** — Phases 37–38 (shipped 2026-04-14)
- ✅ **v2.1 Database Restore** — Phases 39–40 (shipped 2026-04-14)
- ✅ **v2.2 Multi-Operator UDP** — Phase 41 (shipped 2026-04-15)
- 🔄 **v2.3 Operator Statistics** — Phases 42–43 (active)


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

### ✅ v1.8 Admin Isolation, Backup & Docs — SHIPPED 2026-04-10

**Milestone Goal:** The admin console runs as an independent Docker service on port 8001 (admin-only routes, stoppable without affecting the operator app), operators can create local point-in-time backups via CLI and schedule automated S3 uploads via a cron env var, and `/guide` is fully rewritten to cover all features from v1.0–v1.8.

- [x] **Phase 29: Admin Container Isolation** — `app/admin_main.py` standalone entry point, `admin_token` cookie, `profiles: [admin]` compose service on port 8001, `SECRET_KEY` default removed; covers ADM-01–07
- [x] **Phase 30: Database Backup CLI and Scheduler** — `app/backup/` package with PyMongo EJSON export, APScheduler 3.x cron scheduler, aioboto3 S3 upload, bind mount and lifespan wiring; covers BAK-01–08
- [x] **Phase 31: Comprehensive Docs Rewrite** — full `docs/*.md` rewrite covering v1.0–v1.8, 2-level nav, `mkdocs-swagger-ui-tag` interactive API reference, `html=True` load-bearing comment, `mkdocs build` zero-warning rebuild; covers DOC-01–08

---

<details>
<summary>✅ v1.9 Admin & Login UI Redesign (Phases 32–36) — SHIPPED 2026-04-11</summary>

- [x] Phase 32: Theme Infrastructure and Build Discipline (1/1 plan) — completed 2026-04-11
- [x] Phase 33: Design Tokens and CSS Component System (2/2 plans) — completed 2026-04-11
- [x] Phase 34: Admin Console Template Polish (2/2 plans) — completed 2026-04-11
- [x] Phase 35: Login Page Glass Card Redesign (1/1 plan) — completed 2026-04-11
- [x] Phase 36: Operator Log Views (3/3 plans) — completed 2026-04-11

Full archive: `.planning/milestones/v1.9-ROADMAP.md`

</details>

---

<details>
<summary>✅ v2.0 Database Backup (Phases 37–38) — SHIPPED 2026-04-14</summary>

- [x] Phase 37: Infrastructure and Backup Endpoint (1/1 plan) — completed 2026-04-14
- [x] Phase 38: Admin Backup UI (1/1 plan) — completed 2026-04-14

Full archive: `.planning/milestones/v2.0-ROADMAP.md`

</details>

---

<details>
<summary>✅ v2.1 Database Restore (Phases 39–40) — SHIPPED 2026-04-14</summary>

- [x] **Phase 39: Restore Backend** — `app/backup/restore.py` module, `POST /admin/ui/restore/upload` (validate file integrity), `POST /admin/ui/restore/confirm` (auto-backup + drop + restore), password verification wiring
- [x] **Phase 40: Restore UI** — `GET /admin/ui/restore` page route, `templates/admin/restore.html` with HTMX upload form + password modal (backdrop blur), sidebar updated on all three admin pages

Full archive: `.planning/milestones/v2.1-ROADMAP.md`

</details>

---

### v2.3 Operator Statistics (Phases 42–43)

**Milestone Goal:** Each operator can view a dedicated statistics page at `/log/stats` with pie charts for band, mode, and DXCC entity breakdowns — all data scoped to their own log.

- [ ] **Phase 42: Stats Aggregation Backend** — `get_stats()` service function, `GET /log/stats` route handler, JWT-isolated MongoDB aggregations, DXCC Python-side rollup, empty-state data shape
- [ ] **Phase 43: Stats UI** — `templates/log/stats.html` with three Chart.js pie charts, dark/light theme adaptation, `{% block extra_scripts %}` in `base.html`, Stats sidebar nav link in `base_app.html`

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
- [x] 026-01-PLAN.md — expires_at model patch, REST CRUD /api/tokens, HTMX profile UI, templates, and integration tests

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
- [x] 027-01-PLAN.md — dual-auth dependencies (JWT + X-API-Key), QSO router Depends() swap, isolation audit update, integration tests

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
- [x] 028-01-PLAN.md — UDPTokenCache singleton, _handle_datagram APP_OLLOG_TOKEN branch, notify_refresh() wiring, tests

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
- [x] 029-01-PLAN.md — admin_main.py entry point, admin_token cookie rename, docker-compose.yml admin service + profiles, SECRET_KEY default removal

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
- [x] 030-01-PLAN.md — app/backup/ package, PyMongo EJSON dump, aioboto3 S3 upload, APScheduler lifespan wiring, bind mount, pyproject.toml deps

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
- [x] 031-01-PLAN.md — docs/*.md rewrite, mkdocs.yml nav restructure, mkdocs-swagger-ui-tag integration, openapi.json export, html=True comment, mkdocs build

---

### Phase 32: Theme Infrastructure and Build Discipline

**Goal:** The theme toggle, dark/light persistence, FOUC prevention, and build safety gates are all locked in — every subsequent phase builds on a verified foundation.
**Depends on:** Phase 31 (v1.8 complete)
**Requirements:** THEM-01, THEM-02, THEM-03, THEM-04, THEM-05, THEM-06
**Success Criteria** (what must be TRUE):
  1. A sun/moon toggle button is visible and clickable at the bottom of the sidebar nav on every page (admin and operator); clicking it switches the page between dark and light mode immediately
  2. Reloading any page after switching theme renders the correct theme with no white or light flash visible before the page is fully painted
  3. Scrollbars, form inputs, and select dropdowns adopt the active theme's color scheme — native browser controls do not stay light in dark mode
  4. Theme icon on the toggle button shows the correct sun/moon state after HTMX partial swaps replace page content
  5. Toggling the theme animates a smooth color transition; loading any page cold shows no color animation before the user interacts
**Plans:** 1 plan

Plans:
- [x] 032-01-PLAN.md — FOUC IIFE annotation, rAF-rAF transition suppression, color-scheme meta+CSS, htmx:afterSettle handler, verify script

---

### Phase 33: Design Tokens and CSS Component System

**Goal:** All Apple-calibrated design tokens are defined in `tailwind.config.js` and CSS variables in `input.css`, and the full component class library (`.card`, `.btn-*`, `.form-input`, `.badge-*`, `.data-table`, `.card-title`) is built and verified in `output.css`.
**Depends on:** Phase 32
**Requirements:** DSGN-01, DSGN-02, DSGN-03, DSGN-04, DSGN-05, DSGN-06
**Success Criteria** (what must be TRUE):
  1. The page canvas renders `#f2f2f7` in light mode and `#0f0f0f` in dark mode; card surfaces render white in light mode and `#1c1c1e` in dark mode
  2. All body text uses the system font stack (`-apple-system, BlinkMacSystemFont`) — no Google Fonts or external CDN font requests appear in the browser network tab
  3. Cards in light mode show a visible two-layer shadow depth; the same cards in dark mode have no shadow, relying on surface color contrast alone
  4. Status badges (enabled/disabled) use a rectangular shape with visibly rounded corners — no pill-shaped badges remain in any template
  5. Prominent nav and card header icons render sharp and correctly sized at 24px on both standard and Retina/HiDPI displays
**Plans:** 2 plans

Plans:
- [x] 033-01-PLAN.md — tailwind.config.js tokens (canvas, surface, shadow-card, system font), input.css component class updates (card, badges, card-title), base.html CDN removal
- [x] 033-02-PLAN.md — base_app.html canvas classes + nav icon sizing, npm run build + grep verification, human visual review

---

### Phase 34: Admin Console Template Polish

**Goal:** The admin operator management UI and sidebar are fully redesigned using Apple component tokens, with correct icon sizing and accessible action buttons throughout.
**Depends on:** Phase 33
**Requirements:** ADMN-01, ADMN-02, ADMN-03
**Success Criteria** (what must be TRUE):
  1. The admin operator management table renders inside an Apple-style card container with refined typography — no raw table-without-card layout remains
  2. The admin sidebar background uses `#1c1c1e` in dark mode with generous padding; nav items have consistent spacing and clear active states
  3. Every operator action button (enable, disable, reset password) has a visible, correctly-sized icon and an `aria-label` that identifies the action and the target operator
**Plans:** 1 plan

Plans:
- [x] 034-01: users.html, users_table.html, base_app.html sidebar redesign with Apple tokens; icon sizing audit; aria-label attributes

---

### Phase 35: Login Page Glass Card Redesign

**Goal:** Both login pages (admin and operator) present an Apple glassmorphism card that renders correctly in Safari and all major browsers.
**Depends on:** Phase 33
**Requirements:** LOGN-01, LOGN-02, LOGN-03
**Success Criteria** (what must be TRUE):
  1. The admin login card displays a frosted-glass appearance with visible backdrop blur over the dark gradient background in Chrome and Firefox
  2. The operator login card uses the same glass card pattern and is visually consistent with the admin login card
  3. Both glass cards render correctly in Safari — the backdrop blur effect is visible, not a solid opaque background
**Plans:** 1 plan

Plans:
- [x] 035-01-PLAN.md — .glass-card in input.css with -webkit-backdrop-filter: blur(12px) (literal, not CSS variable); both login templates updated to glass-card; npm run build; Safari visual verification checkpoint

---

### Phase 36: Operator Log Views

**Goal:** All operator-facing log templates (log view, QSO form, import page) use Apple component tokens and render correct dark-mode colors through HTMX partial swaps and SSE-driven refreshes.
**Depends on:** Phase 34
**Requirements:** OPER-01, OPER-02, OPER-03
**Success Criteria** (what must be TRUE):
  1. The operator log view table and pagination controls render using Apple card and data-table component classes in both light and dark mode; SSE-triggered log table refreshes preserve correct dark-mode colors
  2. The QSO entry form uses Apple form input and button styles — field labels, inputs, and submit button match the established component library
  3. The ADIF import page uses Apple card and button styles — the file upload area and import report are visually consistent with the rest of the operator UI
**Plans:** 3 plans

Plans:
- [x] 036-01-PLAN.md — Remove inline style= attrs from log_table.html, qso_row.html, qso_row_edit.html, qso_result.html; npm run build verification
- [x] 036-02-PLAN.md — Full rewrite of import_report.html to component classes with dark-mode utilities; npm run build verification
- [x] 036-03-PLAN.md — Final inline-style audit + human visual review (dark mode log view, SSE refresh, import report)

---

### Phase 37: Infrastructure and Backup Endpoint

**Goal:** The admin can successfully download a valid MongoDB backup `.gz` file via `GET /admin/ui/backup/download`, with the file persisting to the shared `./backups` volume and arriving in the browser with a correctly formatted timestamped filename.
**Depends on:** Phase 36 (v1.9 complete)
**Requirements:** INFRA-01, BACK-01, BACK-02, BACK-03, BACK-04, BACK-05
**Architecture decisions:**
  - `run_backup(settings)` already exists in `app/backup/dump.py` — this phase is wiring, not building
  - `asyncio.to_thread(run_backup, settings)` wraps the synchronous gzip I/O to avoid blocking the uvicorn event loop
  - `FileResponse` with `filename=f"ollog-backup-{backup_path.stem}.gz"` generates the correct `Content-Disposition: attachment` header automatically
  - Auth via `Depends(require_admin_cookie)` — the same dependency used on every other admin UI route; never `require_admin` (Bearer)
  - Volume mount added to the `admin` service in `docker-compose.yml` — without it, backups land in the container's ephemeral overlay filesystem
  - `datetime.utcnow()` replaced with `datetime.now(timezone.utc)` in `dump.py` — Python 3.12 deprecation fix, touched in the same phase as the endpoint
**Success Criteria** (what must be TRUE):
  1. `curl -I` against `/admin/ui/backup/download` with a valid admin cookie returns `content-disposition: attachment; filename="ollog-backup-YYYY-MM-DD-HH-MM-SS.gz"` and `content-type: application/gzip`
  2. `curl` without a valid admin cookie receives a 302 redirect to the admin login page — the backup endpoint is not accessible to unauthenticated requests
  3. `gunzip -t` on the downloaded file exits 0 — the file is a valid gzip archive containing EJSON-encoded MongoDB collection data
  4. A backup file written by the endpoint is visible on the host at `./backups/<timestamp>.gz` after the request completes — it is not lost in the container's ephemeral filesystem
  5. Loading another admin page while a backup is in progress responds in under 1 second — the event loop is not blocked during `run_backup` execution
**Plans:** 1 plan

Plans:
- [x] 037-01-PLAN.md — docker-compose.yml admin volume mount, dump.py utcnow fix, ui_router.py backup download endpoint with asyncio.to_thread + FileResponse

---

### Phase 38: Admin Backup UI

**Goal:** The admin console has a dedicated Backup page at `/admin/ui/backup` with a sidebar nav link and a "Download Backup" button that triggers a browser-native file save dialog.
**Depends on:** Phase 37
**Requirements:** UI-01, UI-02, UI-03, UI-04
**Architecture decisions:**
  - Download button is a plain `<a href="/admin/ui/backup/download" class="btn-primary">` anchor — no `hx-*` attributes; HTMX intercepts XHR responses and silently discards binary content
  - New `backup.html` template uses existing Apple component tokens (`.card`, `.btn-primary`, `.card-title`) — no new CSS classes needed
  - Sidebar nav item added to `base_app.html` admin nav section linking to `/admin/ui/backup`
  - `GET /admin/ui/backup` route serves the `backup.html` template; separate from the download endpoint on the same path prefix
**Success Criteria** (what must be TRUE):
  1. A "Backup" item appears in the admin sidebar nav and is reachable by clicking — it loads the backup page at `/admin/ui/backup`
  2. The backup page displays a "Download Backup" button; clicking it opens a browser Save dialog (or downloads directly to the default downloads folder) — no HTMX interception occurs
  3. The backup page and button are visually consistent with the rest of the admin UI — card container, card title, and button use the v1.9 Apple component tokens without introducing new styles
  4. Navigating to `/admin/ui/backup` in a logged-out browser session redirects to the admin login page — the page is not publicly accessible
**Plans:** 1 plan

Plans:
- [x] 038-01-PLAN.md — GET /admin/ui/backup route, backup.html template with card + plain anchor, sidebar nav item

---

### Phase 39: Restore Backend

**Goal:** The two-phase restore API exists and is fully functional — an uploaded `.gz` file is validated for integrity and NDJSON format, a password modal form triggers auto-backup then drop-and-restore, and all outcomes (validation failure, wrong password, restore success, restore failure) return appropriate HTMX response fragments.
**Depends on:** Phase 38 (v2.0 complete)
**Requirements:** VAL-01, VAL-02, VAL-03, AUTH-02, AUTH-03, OPS-01, OPS-02, OPS-03, OPS-04
**Architecture decisions:**
  - `app/backup/restore.py`: sync `_restore_from_file(backup_path, settings)` + async `run_restore(backup_path, settings)` wrapper using `asyncio.to_thread` — mirrors `dump.py` structure exactly
  - `_restore_from_file` reads the `.gz` line by line: groups records by collection name, drops each collection, inserts documents in batches using MongoClient (not Beanie — sync path)
  - `POST /admin/ui/restore/upload`: receives `UploadFile`, writes to `tempfile.NamedTemporaryFile(delete=False, suffix=".gz")`, validates gzip decompressibility + NDJSON record structure; on failure returns error HTML fragment; on success returns modal HTML fragment containing a hidden `<input name="temp_path">` field
  - `POST /admin/ui/restore/confirm`: receives form fields `password` + `temp_path`; looks up admin User document, calls `verify_password(password, user.hashed_password)`; on mismatch returns inline error fragment; on match calls `run_backup()` then `run_restore(temp_path)`; cleans up temp file in all branches
  - File validation: decompress first chunk with `gzip.open`, read first line, parse with `json.loads`, check keys `"collection"` and `"doc"` both present
  - Auth: `Depends(require_admin_cookie)` on both POST routes — cookie already verified; password check is a second explicit factor, not a re-check of the cookie
**Success Criteria** (what must be TRUE):
  1. `POST /restore/upload` with a valid ollog `.gz` backup file returns an HTML fragment containing a password modal — not a redirect, not JSON
  2. `POST /restore/upload` with a corrupt or non-gzip file returns an inline error HTML fragment; the database is unchanged
  3. `POST /restore/upload` with a gzip file whose contents are not NDJSON `{"collection": ..., "doc": ...}` records returns an inline error HTML fragment; the database is unchanged
  4. `POST /restore/confirm` with the correct admin password triggers an auto-backup (a new `.gz` file appears in `./backups/` before any data is modified), then drops and repopulates all collections from the uploaded file
  5. `POST /restore/confirm` with a wrong password returns an inline error fragment visible inside the modal; no auto-backup is created and no data is modified
  6. On successful restore, the response fragment indicates success and includes the auto-backup filename so the admin knows the safety net exists
  7. On restore failure after the wipe has started, the response fragment includes the auto-backup filename so the admin can recover
**Plans:** 1 plan

Plans:
- [x] 039-01-PLAN.md — app/backup/restore.py module, POST /restore/upload (validate + modal), POST /restore/confirm (password verify + auto-backup + restore), HTMX response fragments

---

### Phase 40: Restore UI

**Goal:** The admin console has a dedicated Restore page at `/admin/ui/restore` with an HTMX file upload form, a password confirmation modal with backdrop blur, and all three admin sidebar pages (Operators, Backup, Restore) showing all three nav links with correct active states.
**Depends on:** Phase 39
**Requirements:** UI-01, UI-02, UI-03, AUTH-01, AUTH-04
**Architecture decisions:**
  - `GET /admin/ui/restore` route in `app/admin/ui_router.py` serves `templates/admin/restore.html` behind `Depends(require_admin_cookie)`
  - `restore.html` upload form uses `hx-post="/admin/ui/restore/upload"` + `hx-target="#restore-response"` + `hx-encoding="multipart/form-data"`; response div `#restore-response` swaps in either error HTML or the modal HTML returned by Phase 39
  - Password modal: rendered as an overlay `<div>` with `position: fixed; inset: 0` and `backdrop-filter: blur(8px)` (plus `-webkit-backdrop-filter`) over the page; contains the confirm form posting to `/admin/ui/restore/confirm`
  - Cancel button in modal: plain `hx-on:click` that removes the modal div from DOM — no server round-trip; uploaded temp file is cleaned up on next server restart (acceptable: temp files are small and ephemeral)
  - Sidebar: all three admin pages (`users.html`, `backup.html`, `restore.html`) updated to show Operators, Backup, and Restore nav links; active state driven by current URL path comparison
  - No new CSS component classes needed — modal overlay uses inline Tailwind utilities for the fixed backdrop; form and button use existing `.card`, `.btn-primary`, `.form-input` tokens
**Success Criteria** (what must be TRUE):
  1. Navigating to `/admin/ui/restore` in a logged-out browser session redirects to the admin login page — the page is not publicly accessible
  2. The Restore page displays a file upload form accepting `.gz` files; submitting a valid backup file via the form causes a password modal to appear over the page with the background visibly blurred — no page reload occurs
  3. The password modal contains a "Cancel" button; clicking it dismisses the modal without reloading the page and without starting a restore operation
  4. All three admin pages (Operators, Backup, Restore) show all three sidebar nav links; the active page's nav link is visually distinguished from the inactive links
  5. The Restore page and modal are visually consistent with the rest of the admin UI — card layout, form inputs, and buttons use the established Apple component tokens
**Plans:** 1 plan

Plans:
- [x] 040-01-PLAN.md — GET /admin/ui/restore route, restore.html template (upload form + modal overlay), sidebar updates on users.html + backup.html + restore.html

---

### Phase 41: Multi-Operator UDP Routing

**Goal:** Any enabled operator can receive QSOs over UDP by including their callsign in the OPERATOR field of the ADIF datagram — each datagram is routed to the correct personal log from an in-memory cache, with no MongoDB round-trip per datagram.
**Depends on:** Phase 40 (v2.1 complete)
**Requirements:** UDP-01, UDP-02, UDP-03, UDP-04, UDP-05, UDP-06, DOC-01, DOC-02
**Architecture decisions:**
  - New `app/udp/operator_cache.py` mirrors the `token_cache.py` pattern exactly: `load()` at startup fetches all enabled operators into a `{callsign: User}` dict; `resolve(callsign)` does an O(1) dict lookup; `notify_refresh()` sets a dirty flag so the next `resolve()` call triggers a lazy reload
  - `_handle_datagram` routing order: (1) if OPERATOR field present → resolve via operator_cache → drop+WARN if not found; (2) if no OPERATOR field and UDP_OPERATOR set → use existing startup-cached user; (3) if no OPERATOR field and no UDP_OPERATOR → drop+WARN
  - `app/main.py` loads operator_cache at startup alongside token_cache; operator_cache.load() called inside the same lifespan block after init_db()
  - `app/auth/service.py` calls `operator_cache.notify_refresh()` after create_operator, enable_operator, disable_operator, and update_operator — keeps cache consistent without requiring restart
  - `UDP_OPERATOR` env var remains in config as `str | None` (already Optional) — no migration needed; existing deployments that rely on it continue to work unchanged
  - Docs: `docs/deployment.md` updated to document UDP_OPERATOR as optional fallback; multi-operator routing section added with datagram example showing OPERATOR field; `uv run mkdocs build --strict` run and `site/` committed
**Success Criteria** (what must be TRUE):
  1. A UDP datagram containing `<OPERATOR:4>W1AW` is logged under W1AW's personal log — the QSO appears in W1AW's log view and is absent from any other operator's log
  2. Two operators (W1AW and K0RY) can each send UDP datagrams simultaneously; QSOs arrive in each operator's separate log with no cross-contamination
  3. A UDP datagram containing an OPERATOR field whose callsign is not a registered, enabled operator is dropped and a WARNING is logged that includes the unrecognized callsign and the source IP:port — no QSO is inserted
  4. A UDP datagram with no OPERATOR field is routed using UDP_OPERATOR env var when set — existing single-operator UDP behavior is unchanged
  5. A UDP datagram with no OPERATOR field and no UDP_OPERATOR env var set is dropped with a WARNING — the app does not crash and subsequent datagrams are processed normally
  6. Disabling or creating an operator in the admin console takes effect for UDP routing within one datagram of the change — no app restart required
**Plans:** 2 plans

Plans:
- [x] 041-01-PLAN.md — operator_cache.py, server.py OPERATOR routing, main.py startup, admin router notify_refresh hooks
- [x] 041-02-PLAN.md — docs updates (deployment, udp-adif, env vars) + mkdocs rebuild

---

### Phase 42: Stats Aggregation Backend

**Goal:** The stats service layer correctly computes band counts, mode counts, DXCC entity counts, and unique entity total for any operator's log — with JWT-isolated data, empty-state handling, and a `GET /log/stats` route that delivers this data to the template layer.
**Depends on:** Phase 41 (v2.2 complete)
**Requirements:** STATS-06, STATS-07
**Success Criteria** (what must be TRUE):
  1. Navigating to `/log/stats` as an authenticated operator returns an HTTP 200 response — the route exists and is protected by cookie auth
  2. An operator with QSOs logged sees data shaped for all three charts (band counts, mode counts, DXCC counts) and a non-zero unique entity count in the template context — no KeyError or empty dict
  3. An operator with zero QSOs logged sees template context with `total_qsos == 0` — the route does not error out or raise an exception on an empty log
  4. Viewing `/log/stats` as operator A never returns QSO data belonging to operator B — each operator's stats are isolated by `_operator` from the JWT cookie
**Plans:** 1 plan

Plans:
- [ ] 42-01-PLAN.md — stats service (get_stats), stats router (GET /log/stats), stub template, tests

---

### Phase 43: Stats UI

**Goal:** Operators can view a fully functional statistics page at `/log/stats` with three interactive pie charts, a DXCC entity count scalar, a sidebar nav link, and correct chart colors in both dark and light themes — all without a page reload on theme toggle.
**Depends on:** Phase 42
**Requirements:** STATS-01, STATS-02, STATS-03, STATS-04, STATS-05, STATS-08
**Success Criteria** (what must be TRUE):
  1. A "Stats" link (with bar-chart icon) appears in the operator sidebar nav and navigates to `/log/stats` when clicked
  2. The stats page displays three pie charts labeled "By Band", "By Mode", and "By DXCC Entity" — each chart shows correct slice labels and proportional sizing derived from the operator's actual QSO data
  3. The DXCC chart shows at most 8 named entity slices; when more than 8 entities are present, the remainder appears as a single "Other" slice with the correct summed count — and "Other" is absent when 8 or fewer entities exist
  4. A scalar count of unique DXCC entities worked is displayed on the page (e.g. "42 entities") — this number equals the total distinct entities before the top-8 truncation
  5. Toggling between dark and light mode without a page reload causes all three charts to re-initialize with mode-appropriate colors — no chart displays stale light-mode colors in dark mode or vice versa
**Plans:** 1 plan

Plans:
- [ ] 42-01-PLAN.md — stats service (get_stats), stats router (GET /log/stats), stub template, tests
**UI hint**: yes

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
| 29. Admin Container Isolation | v1.8 | 1/1 | ✓ Complete | 2026-04-10 |
| 30. Database Backup CLI and Scheduler | v1.8 | 1/1 | ✓ Complete | 2026-04-10 |
| 31. Comprehensive Docs Rewrite | v1.8 | 1/1 | ✓ Complete | 2026-04-10 |
| 32. Theme Infrastructure and Build Discipline | v1.9 | 1/1 | ✓ Complete | 2026-04-11 |
| 33. Design Tokens and CSS Component System | v1.9 | 2/2 | ✓ Complete | 2026-04-11 |
| 34. Admin Console Template Polish | v1.9 | 2/2 | ✓ Complete | 2026-04-11 |
| 35. Login Page Glass Card Redesign | v1.9 | 1/1 | ✓ Complete | 2026-04-11 |
| 36. Operator Log Views | v1.9 | 3/3 | ✓ Complete | 2026-04-11 |
| 37. Infrastructure and Backup Endpoint | v2.0 | 1/1 | ✓ Complete | 2026-04-14 |
| 38. Admin Backup UI | v2.0 | 1/1 | ✓ Complete | 2026-04-14 |
| 39. Restore Backend | v2.1 | 1/1 | ✓ Complete | 2026-04-14 |
| 40. Restore UI | v2.1 | 1/1 | ✓ Complete | 2026-04-14 |
| 41. Multi-Operator UDP Routing | v2.2 | 2/2 | ✓ Complete | 2026-04-15 |
| 42. Stats Aggregation Backend | v2.3 | 0/1 | Planning complete | - |
| 43. Stats UI | v2.3 | 0/? | Not started | - |

---

<details>
<summary>✅ v2.2 Multi-Operator UDP (Phase 41) — SHIPPED 2026-04-15</summary>

- [x] Phase 41: Multi-Operator UDP Routing (2/2 plans) — completed 2026-04-15

Full archive: `.planning/milestones/v2.2-ROADMAP.md`

</details>
