# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-06)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v1.4 — UDP Interface (Phase 16 complete, starting Phase 17)

## Current Position

Phase: 17 — QSO Processing Pipeline
Plan: 01 complete
Status: Plan 17-01 complete — _handle_datagram pipeline, lifespan User lookup, 8 unit tests
Last activity: 2026-04-06 — Plan 17-01 executed (1/1 plans)

Progress: [████░░░░░░░░░░░░░░░░] 38% (v1.4 Phase 17 plan 01 complete, 3 of ~8 plans done)

## Performance Metrics

**Velocity (historical):**
- Total plans completed: 36 (v1.0: 19, v1.1: 7, v1.2: 2, v1.3: 8)
- Average duration: ~5–16 min/plan

**By Milestone:**

| Milestone | Phases | Plans |
|-----------|--------|-------|
| v1.0 | 1–6 | 19 |
| v1.1 | 7–10 | 7 |
| v1.2 | 11–12 | 2 |
| v1.3 | 13–15 | 8 |
| v1.4 | 16–18 | TBD |

## Accumulated Context

### Key Decisions (summary — full log in PROJECT.md)

Full decision log in PROJECT.md Key Decisions table. All v1.0–v1.3 decisions recorded there.

**v1.4 decisions already made (from research):**

| Decision | Rationale |
|----------|-----------|
| `UDP_OPERATOR` config for operator identity (not JWT in datagrams) | JWTs expire with no UDP refresh path; overnight FT8 sessions would silently stop logging |
| Loopback-bind default (`UDP_BIND_HOST=127.0.0.1`) | Protects against LAN exposure by default; matches ham radio ecosystem convention |
| `UDP_ENABLED=false` default | Existing deployments unaffected on upgrade |
| Default UDP port 2399 | Port 2237 (WSJT-X) and 12060 (N1MM+) are ecosystem-occupied; dedicated port avoids silent conflict |
| `asyncio.DatagramProtocol` (stdlib) | No new production dependencies; runs on uvicorn's event loop |
| `process_import()` extraction before Phase 17 | Current function raises `HTTPException`; uncatchable from UDP async task |
| `asyncio.get_running_loop()` not `get_event_loop()` | Python 3.14 deprecates `get_event_loop()`; project runs Python 3.14 |
| Operator `User` document cached at startup | Avoids MongoDB round-trip per datagram |
| `_background_tasks` set for task strong references | Prevents async tasks from being garbage-collected before completing |
| Lazy imports inside `_handle_datagram` body | Matches import_qsos_from_bytes pattern, avoids circular imports at module load |
| `build_qso_dict(profile=user)` called directly (not `import_qsos_from_bytes`) | import_qsos_from_bytes omits profile= parameter, breaking auto-stamping for UDP path |
| Operator attribution from config only, ADIF OPERATOR field ignored | Prevents spoofing; config operator is authoritative for UDP ingestion |

### Known Tech Debt

- QSO.find_active() in models.py — dead production code
- from_mongo_dt() in utils.py — tested, not called in production
- Docker end-to-end verification pending

### Blockers/Concerns

None.

### Pending Todos

- Run `/gsd:plan-phase 17` to plan QSO Processing Pipeline

## Session Continuity

Last session: 2026-04-06
Stopped at: Completed 17-01-PLAN.md — UDP QSO processing pipeline implemented and tested
Resume file: None
