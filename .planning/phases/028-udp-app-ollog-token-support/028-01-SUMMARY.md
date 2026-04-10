---
phase: 028-udp-app-ollog-token-support
plan: 01
subsystem: auth
tags: [udp, api-token, in-memory-cache, asyncio, hmac, adif]

# Dependency graph
requires:
  - phase: 025-api-token-foundation
    provides: generate_api_token(), hash_api_token(), ApiToken model, hashed_token field
  - phase: 026-token-ui-and-htmx
    provides: token create/revoke endpoints in tokens/router.py and qso/ui_router.py
  - phase: 027-x-api-key-auth-dependency
    provides: token_is_active() with timezone-normalised expiry check
provides:
  - UDPTokenCache singleton with load(), resolve(), notify_refresh()
  - Per-datagram APP_OLLOG_TOKEN resolution in _handle_datagram
  - Cache invalidation wired into all 4 token mutation endpoints
  - 5 tests covering UDP-01, UDP-02, UDP-03 requirements
affects:
  - app/udp/server.py
  - app/main.py lifespan startup
  - app/tokens/router.py
  - app/qso/ui_router.py

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dirty-flag lazy reload: synchronous notify_refresh() sets _dirty=True, async load() fires on next resolve()"
    - "Cache maps hashed_token (str) -> User, not raw token — raw token hashed at resolve time"
    - "record.pop() consumes APP_OLLOG_TOKEN before build_qso_dict — field never reaches MongoDB"
    - "APP_OLLOG_TOKEN present + invalid = hard reject, no fallthrough to UDP_OPERATOR"
    - "Lazy import of token_cache in _handle_datagram and all 4 mutation endpoints to avoid circular imports"

key-files:
  created:
    - app/udp/token_cache.py
    - tests/test_udp_token.py
  modified:
    - app/udp/server.py
    - app/main.py
    - app/tokens/router.py
    - app/qso/ui_router.py

key-decisions:
  - "asyncio.Lock used (not threading.Lock) — single-threaded asyncio app"
  - "Cache key is stored hashed_token from ApiToken; hash_api_token(raw) computed at resolve time"
  - "notify_refresh() is synchronous (no await) — sets _dirty=True only, reload deferred to next resolve()"
  - "APP_OLLOG_TOKEN present + invalid → hard reject with WARNING, must not fall through to UDP_OPERATOR"
  - "Both operator AND user overridden from resolved_user together — prevents operator/user mismatch pitfall"

patterns-established:
  - "UDP token tests patch app.udp.token_cache.token_cache (module singleton) not the class"
  - "token_cache.load() placed inside udp_enabled block — no DB round-trip when UDP is disabled"

# Metrics
duration: 5min
completed: 2026-04-10
---

# Phase 28 Plan 01: UDP APP_OLLOG_TOKEN Support Summary

**In-memory UDPTokenCache with dirty-flag lazy reload enables per-datagram operator resolution via APP_OLLOG_TOKEN ADIF field, backed by HMAC lookup and cache invalidation on all 4 token mutation endpoints.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-10T18:09:08Z
- **Completed:** 2026-04-10T18:13:26Z
- **Tasks:** 3
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments

- New `app/udp/token_cache.py` provides `UDPTokenCache` singleton with `load()`, `resolve()`, and `notify_refresh()`; loaded at startup inside `udp_enabled` block
- `_handle_datagram` pops `APP_OLLOG_TOKEN` from ADIF record before it reaches `build_qso_dict`, resolves the token to a `User`, and either overrides `operator`+`user` (valid) or rejects with structured `WARNING` log (invalid) — no fallthrough to `UDP_OPERATOR`
- All 4 token mutation endpoints (`POST /api/tokens`, `DELETE /api/tokens/{id}`, HTMX `tokens_create`, HTMX `tokens_revoke`) call `token_cache.notify_refresh()` after mutation, keeping the cache coherent
- 5 new tests in `tests/test_udp_token.py` covering UDP-01/02/03; 18/18 total UDP tests pass

## Task Commits

1. **Task 1: Create UDPTokenCache and wire startup load** — `a83c668` (feat)
2. **Task 2: APP_OLLOG_TOKEN branch + notify_refresh wiring** — `5f11d4c` (feat)
3. **Task 3: Write test_udp_token.py** — `47deb6e` (test)

**Plan metadata:** _(docs commit — see below)_

## Files Created/Modified

- `app/udp/token_cache.py` — UDPTokenCache singleton: load/resolve/notify_refresh, dirty-flag lazy reload
- `app/udp/server.py` — APP_OLLOG_TOKEN branch in _handle_datagram (pop → resolve → reject or override)
- `app/main.py` — `await token_cache.load()` inside `udp_enabled` block at startup
- `app/tokens/router.py` — notify_refresh() after create_token and revoke_token
- `app/qso/ui_router.py` — notify_refresh() after tokens_create (success path) and tokens_revoke
- `tests/test_udp_token.py` — 5 tests covering all three UDP token requirements

## Decisions Made

- `asyncio.Lock` used (not `threading.Lock`) — single-threaded asyncio app; threading Lock would be wrong here
- Cache key is the stored `hashed_token` field from `ApiToken`; `hash_api_token(raw_token)` called at resolve time — avoids redundant hashing during load
- `notify_refresh()` is synchronous and sets `_dirty=True` only; the actual reload happens lazily on next `resolve()` call — matches the locked decision from RESEARCH.md
- `APP_OLLOG_TOKEN` present + invalid is a hard reject with no fallthrough — security requirement; token must not silently degrade to UDP_OPERATOR
- Both `operator` and `user` are updated together from `resolved_user` — prevents the operator/user mismatch pitfall identified in research

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- v1.7 complete: multi-operator UDP setups are now possible without per-datagram DB queries
- UDP-01, UDP-02, UDP-03 requirements fully covered and tested
- No known blockers for future phases

---
*Phase: 028-udp-app-ollog-token-support*
*Completed: 2026-04-10*

## Self-Check: PASSED

- app/udp/token_cache.py: FOUND
- tests/test_udp_token.py: FOUND
- 028-01-SUMMARY.md: FOUND
- Commit a83c668 (feat Task 1): FOUND
- Commit 5f11d4c (feat Task 2): FOUND
- Commit 47deb6e (test Task 3): FOUND
