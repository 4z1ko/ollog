# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-09)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v1.7 API Token Auth — Phase 25: Token Model and Service Layer

## Current Position

Phase: 25 of 28 (Token Model and Service Layer)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-04-09 — Roadmap created for v1.7 (Phases 25–28)

Progress: [██████████████████░░░░░░░░░░░░] ~60% (24/~40 estimated plans)

## Performance Metrics

**Velocity (historical):**
- Total plans completed: 46 (v1.0: 19, v1.1: 7, v1.2: 2, v1.3: 8, v1.4: 4, v1.5: 4, v1.6: 2)
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
| v1.7 | 25–28 | TBD |

## Accumulated Context

### Key Decisions (v1.7)

Full decision log in PROJECT.md Key Decisions table.

Recent decisions locked by research:
- HMAC-SHA256 for token hashing (not Argon2 — 200-500ms verify is unacceptable per request)
- Separate `api_tokens` Beanie collection (not embedded in User — avoids per-request token list deserialization)
- Per-datagram in-memory cache for UDP token resolution (not startup-pin — startup-pin delivers nothing UDP_OPERATOR doesn't)
- `X-API-Key` header (not `Authorization: Bearer`) — clean separation from JWT session auth
- `APP_OLLOG_TOKEN` fixed ADIF field name (APP_ prefix per ADIF spec convention)

### Critical Integration Risks (v1.7)

- Phase 27: `OAuth2PasswordBearer(auto_error=True)` returns HTTP 403 before `APIKeyHeader` can run — must use `auto_error=False` on both schemes; raise HTTP 401 manually
- Phase 28: Cache invalidation signal path — how ASGI token create/revoke notifies `QSODatagramProtocol`; candidates: asyncio shared dict with Lock, asyncio.Event reload signal, TTL refresh

### Known Tech Debt

- `QSO.find_active()` in models.py — dead production code
- `from_mongo_dt()` in utils.py — tested, not called in production
- Docker end-to-end verification pending (requires live Docker environment)

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-09
Stopped at: v1.7 roadmap written (ROADMAP.md, STATE.md, REQUIREMENTS.md traceability updated)
Resume file: None
