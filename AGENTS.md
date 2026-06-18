# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## What This Is

**ollog** — a self-hosted, ADIF-native, multi-operator ham radio logbook. Multiple operators log QSOs simultaneously under their own callsigns without conflicts. Data is stored verbatim in ADIF field format. Current milestone: v2.2 (Multi-Operator UDP), archived 2026-04-15.

## Common Commands

**Run with Docker (primary dev path):**
```bash
docker-compose up -d           # Start MongoDB + API on :8000
docker-compose up -d admin     # Also start admin panel on :8001
```

**Run without Docker:**
```bash
export MONGODB_URI=mongodb://localhost:27017
export MONGODB_DB=ollog
export SECRET_KEY=dev-secret-12345
export API_TOKEN_SECRET=dev-api-secret
uvicorn app.main:app --reload
```

**Tests (requires MongoDB on localhost:27017):**
```bash
uv run pytest tests/
uv run pytest tests/test_qso.py          # Single test file
uv run pytest tests/test_qso.py::test_create_qso  # Single test
```

**Frontend CSS (Tailwind v3):**
```bash
npm run build    # Compile output.css once
npm run watch    # Live rebuild during development
npm run verify   # Assert dark mode + color-scheme classes are present
```

**Documentation:**
```bash
uv run mkdocs build --strict   # Build to site/ (mounted at /guide in the app)
uv run mkdocs serve            # Preview docs locally
```

## Architecture

### Stack
- **FastAPI** + **Beanie** (async MongoDB ODM, Pydantic-native) + **Jinja2** templates
- **HTMX** for partial DOM swaps; **Tailwind CSS** for styling
- **APScheduler** for cron-based backups; **Server-Sent Events** for live QSO feed via MongoDB change streams
- **PyJWT** + **pwdlib[argon2]** for auth

### Two FastAPI Apps
- `app/main.py` — operator-facing app on port 8000. Includes 7 routers: auth, qso, qso-ui, adif, feed, profile, tokens.
- `app/admin_main.py` — admin panel on port 8001. Separate service in docker-compose (`profiles: [admin]`). Includes admin CRUD, backups, restores.

### Request Flow
```
Router (app/*/router.py)
  → Service layer (app/*/service.py)  ← business logic, duplicate detection, stamping
  → Beanie models (app/*/models.py)   ← MongoDB collections
```

### Authentication
Two parallel auth strategies coexist:
- **JWT Bearer token** — REST API (Authorization header). JWT payload includes operator callsign.
- **HttpOnly cookie** — UI routes, SSE feed. `get_current_user_cookie` dependency.
- **API key** — X-API-Key header, hashed in `api_tokens` collection. Used as alternative to JWT for QSO endpoints.

Every QSO query filters by `_operator: <callsign>` from the JWT — multi-operator isolation is enforced at the service layer.

### Database Collections

**qsos** — ADIF fields stored verbatim (uppercase keys: CALL, BAND, MODE, FREQ, etc.)
- Internal fields prefixed `_`: `_operator` (from JWT callsign), `_deleted` (soft delete)
- Compound index on `(_operator, CALL, qso_date_utc, BAND, MODE)`
- Extra ADIF fields allowed via `model_config = ConfigDict(extra="allow")`
- Duplicate window: ±2 minutes same CALL+BAND+MODE per operator

**users** — operator profiles
- Fields: username, hashed_password, callsign, station_callsign, gridsquare, lat/lon, rig, antenna, etc.
- Unique index on username

**api_tokens** — API key storage (hash + salt, never store plaintext)

### Key Modules

| Module | Purpose |
|--------|---------|
| `app/qso/` | QSO REST API + Jinja2 UI router (HTMX-driven log table) |
| `app/adif/` | ADIF import (parse_adi) and export (serialize_adi) |
| `app/feed/` | SSE endpoint — MongoDB change stream → browser live updates |
| `app/udp/` | UDP datagram listener; parses incoming ADIF datagrams from logging software (e.g. WSJT-X) |
| `app/backup/` | mongodump/mongorestore + optional S3 upload via aioboto3 |
| `app/callsign/` | ITU prefix resolver for country flags |
| `app/auth/` | JWT issue/verify, cookie auth, admin bootstrap |

### Frontend Notes

- **Dark mode**: `dark:` Tailwind classes are critical — run `npm run verify` after adding new dark classes to confirm they appear in `static/css/output.css`.
- **FOUC prevention**: `templates/base.html` contains a load-bearing inline `<script>` that applies the theme class before page paint. Do not move it or make it `defer`.
- **HTMX + SSE**: The live log table swaps via SSE events from `/feed/station`. QSO form submissions use HTMX `hx-post` with `hx-swap="outerHTML"`.

### Lifespan Startup Order (`app/main.py`)
1. `init_db()` — Beanie + MongoDB init
2. UDP listener (if `UDP_ENABLED=true`)
3. SSE change-stream watcher
4. Backup scheduler (if `BACKUP_SCHEDULE` is set)

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `MONGODB_URI` | MongoDB connection string |
| `MONGODB_DB` | Database name |
| `SECRET_KEY` | JWT signing key |
| `API_TOKEN_SECRET` | API key hashing secret |
| `JWT_EXPIRE_MINUTES` | Token lifetime (default 480 — 8 hrs for overnight FT8 sessions) |
| `ADMIN_USERNAME/PASSWORD/CALLSIGN` | Bootstrap admin (clear from env after first run) |
| `UDP_ENABLED` | Enable UDP ADIF listener (default true) |
| `UDP_PORT` | UDP listen port (default 2399) |
| `UDP_BIND_HOST` | UDP bind address (127.0.0.1 for local, 0.0.0.0 for LAN) |
| `BACKUP_SCHEDULE` | Cron expression for automatic backups |
| `BACKUP_S3_BUCKET` | Optional S3 bucket for backup upload |

## Project Planning

This project uses GSD milestone workflow. Planning artifacts live in `.planning/`:
- `PROJECT.md` — requirements by version
- `ROADMAP.md` — full release roadmap
- `STATE.md` — current phase + performance metrics
- `phases/` — individual phase PLAN.md files
- `milestones/` — archived milestone metadata

Use `/gsd:progress` to check current state and route to next action.
