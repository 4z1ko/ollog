# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-03)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: 1 of 5 (Foundation)
Plan: 3 of 4 in current phase
Status: In progress
Last activity: 2026-04-03 — Completed 01-03 (QSO MongoDB Schema)

Progress: [####░░░░░░] 15%

## Performance Metrics

**Velocity:**
- Total plans completed: 2 (01-01, 01-03)
- Average duration: ~7 min
- Total execution time: 0.25 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 2/4 | ~14 min | ~7 min |

**Recent Trend:**
- Last 5 plans: 01-01 (4min), 01-03 (~10min)
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Foundation: ADIF field names stored verbatim as MongoDB document keys — no translation layer, no snake_case mapping
- Foundation: Shared `qsos` collection with `_operator` as leading field in all compound indexes (not per-operator collections)
- Foundation: All datetimes UTC-aware codebase-wide; re-attach UTC tzinfo after every MongoDB read via utility function
- Foundation: Compound unique index on {_operator, CALL, qso_date_utc, BAND, MODE} + upsert=True for concurrent duplicate safety
- 01-01: pymongo AsyncMongoClient used instead of motor — pymongo 4.9+ has native async support, motor is a redundant wrapper
- 01-01: SECRET_KEY has no default in Settings class — forces explicit env var, prevents silent insecure defaults
- 01-01: Dev SECRET_KEY set in docker-compose.yml environment block so local dev works without copying .env
- 01-03: _operator MongoDB field via Field(serialization_alias="_operator") + populate_by_name=True — no fallback to "operator" (locked)
- 01-03: _deleted MongoDB field via Field(serialization_alias="_deleted") on is_deleted Python attribute
- 01-03: find_active() queries raw MongoDB field names {"_operator": operator, "_deleted": False} to hit indexes correctly
- 01-03: from_mongo_dt() re-attaches UTC tzinfo only to naive datetimes; aware datetimes returned unchanged

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 1: Verify ADIF library maintainership on PyPI (`adif-io`, `adif3`) before choosing library vs. custom parser — custom parser (~100 lines) may be preferable given parser correctness requirements
- Phase 4: Decide async import job queue (FastAPI BackgroundTasks vs. Celery + Redis) before Phase 4 planning — Redis adds operational dependency for self-hosted deployments
- Phase 5: Research FastAPI WebSocket vs. SSE for multi-operator live feed; verify Beanie/Motor change stream support
- 01-01: Docker not installed on dev machine — verify `docker compose up -d --build && curl http://localhost:8000/health` on a machine with Docker before declaring environment ready

## Session Continuity

Last session: 2026-04-03
Stopped at: Completed 01-03 — QSO Beanie Document model with compound unique index, _operator/_deleted aliases, find_active(), from_mongo_dt()
Resume file: None
