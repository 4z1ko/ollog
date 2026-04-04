# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-03)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: 6 of 6 (Navigation Fix)
Plan: 1 of 1 in current phase
Status: Phase 6 complete — 1/1 plans done
Last activity: 2026-04-04 — Completed 06-01 (Add Import/Export nav links to form.html and log.html)

Progress: [████████████████████████████████] 83% (19 of ~23 plans)

## Performance Metrics

**Velocity:**
- Total plans completed: 18 (01-01, 01-02, 01-03, 01-04, 02-01, 03-01, 03-02, 03-03, 03-04, 04-01, 04-02, 04-03, 04-04, 05-01, 05-02, 05-03, 05-04, 06-01)
- Average duration: ~7.1 min
- Total execution time: ~1.73 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 4/4 | ~40 min | ~10 min |
| 02-admin-accounts | 2/2 | ~19 min | ~9.5 min |
| 03-qso-entry-log-view | 4/4 | ~27 min | ~6.8 min |
| 04-adif-import-export | 4/4 | ~34 min | ~8.5 min |

**Recent Trend:**
- Last 5 plans: 04-01 (16min), 04-02 (~8min), 04-03 (~6min), 04-04 (~4min), 05-01 (~8min)
- Trend: stable

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 05-multi-operator-live-feed | 4/4 | ~37 min | ~9.3 min |
| 06-navigation-fix | 1/1 | ~2 min | ~2 min |

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
- [Phase 04-adif-import-export]: 04-03: _qso_to_adif_dict() adds declared fields (CALL, BAND, MODE) explicitly and iterates model_extra for rest — SKIP_FIELDS guard removes qso_date_utc and internal Beanie fields
- [Phase 04-adif-import-export]: 04-03: /log/export is a standalone cookie-auth endpoint (not a redirect to /api/adif/export) — browsers don't forward Authorization headers on redirect
- [Phase 04-adif-import-export]: 04-03: qso_date_utc excluded from ADIF export; QSO_DATE and TIME_ON in model_extra serve the ADIF-standard date/time purpose
- [Phase 04-adif-import-export]: 04-04: ADIF fixture byte lengths must be exact byte counts (UTF-8), not character counts — verified via parse_adi() returning correct records before committing
- [Phase 04-adif-import-export]: 04-04: Integration tests skip gracefully via mongo_required + _mongo_available() TCP probe — consistent pattern across all integration test files
- [Phase 05-multi-operator-live-feed]: MongoDB replica set upgrade done in docker-compose.yml only — app/config.py default left standalone for non-Docker local dev
- [Phase 05-multi-operator-live-feed]: Self-initiating healthcheck pattern: rs.initiate() runs inside healthcheck probe, no separate init container or entrypoint script needed
- [Phase 05-multi-operator-live-feed]: 05-02: Route introspection uses inspect.signature + recursive Depends() walk to collect callsign dep names — catches transitive injection without relying on parameter name strings
- [Phase 05-multi-operator-live-feed]: 05-02: isolation_test_db fixture (local, not conftest) inits both QSO and User models — needed because User is imported transitively when app.main is loaded
- [Phase 05-multi-operator-live-feed]: 05-02: find_duplicate() negative scoping test: BB2BB cannot find AA1AA's QSO, AA1AA finds own — proves isolation at duplicate-detection layer
- [Phase 05-multi-operator-live-feed]: 05-03: ConnectionManager broadcasts rendered HTML strings (not JSON) — no client-side templating needed, simpler HTMX sse-swap wiring
- [Phase 05-multi-operator-live-feed]: 05-03: SSE endpoint uses cookie auth (get_current_operator_callsign_cookie) — EventSource API cannot send Authorization headers
- [Phase 05-multi-operator-live-feed]: 05-03: Change stream watcher started after init_db() in lifespan, cancelled before close_db() — prevents use of closed connection
- [Phase 05-multi-operator-live-feed]: 05-03: feed_row.html uses flat context dict keys rendered via get_template().render(ctx) — no Request object available in watcher scope
- [Phase 05-04]: directConnection=true added to all integration test fixture URIs — enables direct driver connection to replica set node, works for both standalone and replica set without ServerSelectionTimeoutError

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 1: Verify ADIF library maintainership on PyPI (`adif-io`, `adif3`) before choosing library vs. custom parser — custom parser (~100 lines) may be preferable given parser correctness requirements
- Phase 4: Decide async import job queue (FastAPI BackgroundTasks vs. Celery + Redis) before Phase 4 planning — Redis adds operational dependency for self-hosted deployments
- Phase 5: Research FastAPI WebSocket vs. SSE for multi-operator live feed; verify Beanie/Motor change stream support
- 01-01: Docker not installed on dev machine — verify `docker compose up -d --build && curl http://localhost:8000/health` on a machine with Docker before declaring environment ready

## Session Continuity

Last session: 2026-04-04
Stopped at: Completed 06-01 — Added Import/Export nav links to form.html and log.html; ADIF import/export pages now reachable from any log UI page. Phase 6 complete.
Resume file: None
