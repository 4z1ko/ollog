# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-09)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v1.7 API Token Auth — Phase 28: UDP APP_OLLOG_TOKEN Support — COMPLETE

## Current Position

Phase: 28 of 28 (UDP APP_OLLOG_TOKEN Support) — COMPLETE
Plan: 1 of 1 in Phase 28 — COMPLETE
Status: Phase 28 plan 01 complete — UDPTokenCache + APP_OLLOG_TOKEN resolution + 5 tests delivered; v1.7 complete
Last activity: 2026-04-10 — Phase 28 plan 01 executed (UDP token cache, per-datagram operator resolution, cache invalidation)

Progress: [█████████████████████░░░░░░░░░] ~67% (27/~40 estimated plans)

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
| v1.7 | 25–28 | 2+ |

## Accumulated Context

### Key Decisions (v1.7)

Full decision log in PROJECT.md Key Decisions table.

Recent decisions locked by research:
- HMAC-SHA256 for token hashing (not Argon2 — 200-500ms verify is unacceptable per request)
- Separate `api_tokens` Beanie collection (not embedded in User — avoids per-request token list deserialization)
- Per-datagram in-memory cache for UDP token resolution (not startup-pin — startup-pin delivers nothing UDP_OPERATOR doesn't)
- `X-API-Key` header (not `Authorization: Bearer`) — clean separation from JWT session auth
- `APP_OLLOG_TOKEN` fixed ADIF field name (APP_ prefix per ADIF spec convention)

Phase 25 execution decisions:
- generate_api_token() returns tuple[str, str] so callers always have prefix without recomputing (Phase 25-01)
- hashed_token field name used (consistent with User.hashed_password naming convention) (Phase 25-01)

Phase 26 execution decisions:
- HTMX UI routes always return HTTP 200 with error state in partial body — HTMX 2.x convention (Phase 26-01)
- token_is_active() uses Any duck typing to avoid circular import from service.py to models.py (Phase 26-01)
- Integration tests use directConnection=true to bypass replica set hostname resolution in test environment (Phase 26-01)

Phase 27 execution decisions:
- auto_error=False on both optional schemes (OAuth2PasswordBearer + APIKeyHeader) prevents premature 403 before both auth paths can run (Phase 27-01)
- JWT path tried first in get_current_user_jwt_or_apikey to preserve existing session-caller behaviour with no performance regression (Phase 27-01)
- get_current_user_cookie added to CALLSIGN_DEPS audit set — POST /log/qsos uses full User dep with callsign extracted in function body, not via callsign-only wrapper (Phase 27-01)
- token_is_active() normalises timezone-naive MongoDB datetimes to UTC before comparison — avoids TypeError crash on expired token checks (Phase 27-01)

Phase 28 execution decisions:
- asyncio.Lock used (not threading.Lock) — single-threaded asyncio app (Phase 28-01)
- Cache key is stored hashed_token from ApiToken; hash_api_token(raw) computed at resolve time — no redundant hashing during load (Phase 28-01)
- notify_refresh() is synchronous and sets _dirty=True only; reload deferred to next resolve() — lazy cache invalidation (Phase 28-01)
- APP_OLLOG_TOKEN present + invalid = hard reject, no fallthrough to UDP_OPERATOR (security requirement) (Phase 28-01)
- Both operator AND user overridden together from resolved_user — prevents operator/user mismatch pitfall (Phase 28-01)

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

Last session: 2026-04-10
Stopped at: Completed 028-01-PLAN.md (UDPTokenCache, APP_OLLOG_TOKEN branch, 5 token tests — v1.7 complete)
Resume file: None
