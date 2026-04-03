# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-03)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: 4 of 5 (ADIF Import/Export)
Plan: 2 of 3 in current phase
Status: In progress — 04-02 done
Last activity: 2026-04-03 — Completed 04-02 (ADIF Import Duplicate Detection)

Progress: [████████████████] 52% (12 of ~23 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 11 (01-01, 01-02, 01-03, 01-04, 02-01, 03-01, 03-02, 03-03, 03-04, 04-01, 04-02)
- Average duration: ~8 min
- Total execution time: ~1.5 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 4/4 | ~40 min | ~10 min |
| 02-admin-accounts | 2/2 | ~19 min | ~9.5 min |
| 03-qso-entry-log-view | 4/4 | ~27 min | ~6.8 min |
| 04-adif-import-export | 2/3 | ~24 min | ~12 min |

**Recent Trend:**
- Last 5 plans: 03-02 (4min), 03-03 (3min), 03-04 (~8min), 04-01 (16min), 04-02 (~8min)
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Foundation: ADIF field names stored verbatim as MongoDB document keys — no translation layer, no snake_case mapping
- Foundation: Shared `qsos` collection with `_operator` as leading field in all compound indexes (not per-operator collections)
- Foundation: All datetimes UTC-aware codebase-wide; re-attach UTC tzinfo after every MongoDB read via utility function
- Foundation: Compound index on {_operator, CALL, qso_date_utc, BAND, MODE} — was unique, dropped unique=True in 03-02 (app-level find_duplicate() is now enforcement)
- 01-01: pymongo AsyncMongoClient used instead of motor — pymongo 4.9+ has native async support, motor is a redundant wrapper
- 01-01: SECRET_KEY has no default in Settings class — forces explicit env var, prevents silent insecure defaults
- 01-01: Dev SECRET_KEY set in docker-compose.yml environment block so local dev works without copying .env
- 01-03: _operator MongoDB field via Field(alias="_operator", serialization_alias="_operator") + populate_by_name=True — alias required for Beanie storage (CORRECTED: serialization_alias alone does not set MongoDB field name)
- 01-03: _deleted MongoDB field via Field(alias="_deleted", serialization_alias="_deleted") on is_deleted Python attribute (CORRECTED in 03-01)
- 01-03: find_active() queries raw MongoDB field names {"_operator": operator, "_deleted": False} to hit indexes correctly
- 01-03: from_mongo_dt() re-attaches UTC tzinfo only to naive datetimes; aware datetimes returned unchanged
- 01-04: PyJWT (import jwt) used — python-jose explicitly excluded; pwdlib Argon2 used — passlib explicitly excluded
- 01-04: JWT carries sub (username), callsign, role, exp — all four claims required
- 01-04: get_current_operator_callsign is the single callsign injection point for all QSO operations
- 01-04: Admin bootstrap runs in lifespan from ADMIN_USERNAME/PASSWORD/CALLSIGN env vars — no web endpoint
- 02-01: require_admin injected via dependencies=[Depends(require_admin)] on decorator — admin endpoints don't need user object in function body
- 02-01: aclose() used instead of close() for pymongo AsyncMongoClient in test fixtures — pymongo 4.9+ async client requires awaitable close
- 02-02: Exception handler on app checks request.url.path.startswith('/admin/ui/') — redirects 401/403 to login page; other routes still return JSON
- 02-02: HTMX 2.0.4 via CDN, inline CSS only — no npm or build step; suitable for internal admin tool
- [Phase 03-01]: Beanie requires alias= (not serialization_alias=) for correct MongoDB field name storage — _operator/_deleted use alias in QSO model
- [Phase 03-01]: QSO response serialization via _qso_to_dict(): strip _id, add string id, isoformat datetimes to avoid FastAPI PydanticSerializationError
- [Phase 03-qso-entry-log-view]: 03-02: Compound unique index dropped (unique=True removed) — app-level find_duplicate() is the enforcement mechanism; unique index blocked soft-delete re-insertion and force=true use cases
- [Phase 03-qso-entry-log-view]: 03-02: 409 detail is a dict not a string — UI can extract existing_id for confirmation dialog without parsing error text
- [Phase 03-qso-entry-log-view]: 03-03: POST /log/qsos always returns HTTP 200 — HTMX 2.x does not swap on 4xx; template content distinguishes success vs duplicate warning
- [Phase 03-qso-entry-log-view]: 03-03: Operator login at /log/login has no role restriction — any enabled user (operator or admin) can log in here (contrast with /admin/ui/login which requires role=admin)
- [Phase 03-qso-entry-log-view]: 03-04: _qso_to_view_dict() extracts Beanie model_extra fields (FREQ, RST_SENT, etc.) to plain dict before template rendering — direct attribute access on model_extra fields is unreliable in Jinja2
- [Phase 03-qso-entry-log-view]: 03-04: HX-Request header check on /log/view returns partial (log_table.html) or full page (log.html) — single endpoint serves both HTMX and direct browser requests
- [Phase 04-adif-import-export]: 04-01: process_import() extracted as shared async helper — API endpoint returns dict as JSON; UI endpoint passes dict to Jinja2 template; eliminates logic duplication
- [Phase 04-adif-import-export]: 04-01: UI POST /log/import always returns HTTP 200 — catches HTTPException from process_import and renders error-msg div so HTMX swaps correctly on size-limit errors
- [Phase 04-adif-import-export]: 04-01: 10 MB guard in process_import() so both API and UI callers enforce same limit
- [Phase 04-adif-import-export]: 04-02: find_duplicate() called after build_qso_dict(), before QSO.insert() — duplicate records skip insertion via continue; appear in duplicates list with record_index, call, existing_id
- [Phase 04-adif-import-export]: 04-02: Re-importing the same ADIF file produces zero accepted and all records as duplicates (idempotency guaranteed by +/-2 min fuzzy window)

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 1: Verify ADIF library maintainership on PyPI (`adif-io`, `adif3`) before choosing library vs. custom parser — custom parser (~100 lines) may be preferable given parser correctness requirements
- Phase 4: Decide async import job queue (FastAPI BackgroundTasks vs. Celery + Redis) before Phase 4 planning — Redis adds operational dependency for self-hosted deployments
- Phase 5: Research FastAPI WebSocket vs. SSE for multi-operator live feed; verify Beanie/Motor change stream support
- 01-01: Docker not installed on dev machine — verify `docker compose up -d --build && curl http://localhost:8000/health` on a machine with Docker before declaring environment ready

## Session Continuity

Last session: 2026-04-03
Stopped at: Completed 04-02 — find_duplicate() wired into process_import() loop; integration tests in tests/test_adif_import.py. Phase 4 plan 2 of 3 done.
Resume file: None
