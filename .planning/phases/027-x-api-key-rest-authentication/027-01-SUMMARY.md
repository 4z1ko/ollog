---
phase: 027-x-api-key-rest-authentication
plan: 01
subsystem: auth
tags: [api-key, x-api-key, fastapi, beanie, hmac, jwt, dual-auth, qso]

# Dependency graph
requires:
  - phase: 025-api-token-generation
    provides: generate_api_token, hash_api_token, verify_api_token, token_is_active, ApiToken model
  - phase: 026-token-crud-api
    provides: ApiToken CRUD endpoints, token_is_active function
provides:
  - X-API-Key header authentication on all 5 QSO REST endpoints
  - get_current_user_jwt_or_apikey dual-auth FastAPI dependency
  - get_current_operator_callsign_jwt_or_apikey dual-auth callsign dep
  - _resolve_user_from_api_key private helper with prefix-indexed DB lookup
  - 12 integration tests covering all API key auth scenarios
affects:
  - phase-028-udp-api-key-auth (same ApiToken resolution pattern, in-memory cache variant)
  - any future QSO endpoints (must use dual-auth deps not JWT-only deps)

# Tech tracking
tech-stack:
  added: [APIKeyHeader (fastapi.security)]
  patterns:
    - Dual-auth FastAPI dependency pattern (optional schemes + manual 401 raise)
    - Prefix-indexed HMAC token lookup (cheap DB scan before HMAC verify)
    - auto_error=False on both schemes to prevent premature 401/403 before all paths attempted

key-files:
  created:
    - tests/test_qso_api_key.py
  modified:
    - app/auth/dependencies.py
    - app/qso/router.py
    - app/tokens/service.py
    - tests/test_operator_isolation.py

key-decisions:
  - "auto_error=False on both _oauth2_scheme_optional and _apikey_scheme prevents OAuth2PasswordBearer from returning HTTP 403 before APIKeyHeader can run"
  - "JWT path tried first in get_current_user_jwt_or_apikey to preserve existing behaviour for session callers"
  - "get_current_user_cookie added to CALLSIGN_DEPS audit set — POST /log/qsos uses User dep directly, not callsign wrapper"
  - "token_is_active normalises timezone-naive MongoDB datetimes to UTC before comparison (Rule 1 bug fix)"

patterns-established:
  - "Dual-auth dep pattern: two optional schemes + private resolver helper + single 401 raise path"
  - "CALLSIGN_DEPS audit set includes all auth deps that enforce operator identity, including full-User deps that derive callsign in function body"

# Metrics
duration: 34min
completed: 2026-04-10
---

# Phase 27 Plan 01: X-API-Key Auth on QSO Endpoints Summary

**X-API-Key dual-auth dependency added to all five QSO REST endpoints using APIKeyHeader(auto_error=False) + prefix-indexed HMAC token lookup, with identical operator isolation to JWT auth and HTTP 401 for all failure modes**

## Performance

- **Duration:** 34 min
- **Started:** 2026-04-10T17:15:07Z
- **Completed:** 2026-04-10T17:49:53Z
- **Tasks:** 2
- **Files modified:** 5 (4 modified + 1 created)

## Accomplishments
- `get_current_user_jwt_or_apikey` and `get_current_operator_callsign_jwt_or_apikey` added to `app/auth/dependencies.py` with full dual-path logic (JWT first, then X-API-Key header)
- All 5 QSO REST endpoints (`create_qso`, `list_qsos`, `get_qso`, `patch_qso`, `delete_qso`) in `app/qso/router.py` wired to dual-auth dependencies
- Operator isolation audit test (`test_all_qso_routes_inject_callsign_from_jwt`) updated and passing — covers all auth dep patterns including new dual-auth and cookie-based
- 12 integration tests in `tests/test_qso_api_key.py` all pass: valid API key on all 5 endpoints, operator isolation, HTTP 401 for invalid/expired/disabled/missing credentials, JWT regression, admin endpoint rejection

## Task Commits

Each task was committed atomically:

1. **Task 1: Add dual-auth dependencies to app/auth/dependencies.py** - `ec8cdf5` (feat)
2. **Task 2: Wire QSO router, update isolation audit, write API key tests** - `6f3352c` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `/Users/royco/ollog/app/auth/dependencies.py` - Added `_oauth2_scheme_optional`, `_apikey_scheme`, `_resolve_user_from_api_key`, `get_current_user_jwt_or_apikey`, `get_current_operator_callsign_jwt_or_apikey`
- `/Users/royco/ollog/app/qso/router.py` - Swapped all 5 endpoint dependencies from JWT-only to dual-auth
- `/Users/royco/ollog/app/tokens/service.py` - Fixed timezone-naive datetime comparison bug in `token_is_active`
- `/Users/royco/ollog/tests/test_operator_isolation.py` - Extended CALLSIGN_DEPS set with new dual-auth deps and `get_current_user_cookie`
- `/Users/royco/ollog/tests/test_qso_api_key.py` - New file: 12 integration tests for X-API-Key auth on QSO endpoints

## Decisions Made
- `auto_error=False` on both optional scheme objects: prevents `OAuth2PasswordBearer` from returning HTTP 403 before `APIKeyHeader` can run — this was the primary critical integration risk noted in STATE.md for Phase 27
- JWT path is tried first in `get_current_user_jwt_or_apikey` to preserve existing behaviour for session-based callers (no performance regression for the common case)
- Added `get_current_user_cookie` to the isolation audit's `CALLSIGN_DEPS` set: `POST /log/qsos` uses the full User dep and extracts callsign in the function body — the audit must recognise this pattern to pass

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed timezone-naive datetime comparison crash in `token_is_active`**
- **Found during:** Task 2 (`test_expired_api_key_returns_401`)
- **Issue:** MongoDB returns `expires_at` as a timezone-naive datetime; `token_is_active` compared it with `datetime.now(tz=timezone.utc)` (timezone-aware), raising `TypeError: can't compare offset-naive and offset-aware datetimes`
- **Fix:** Added tzinfo guard in `token_is_active` — if `expires.tzinfo is None`, replace with UTC before comparison
- **Files modified:** `app/tokens/service.py`
- **Verification:** `test_expired_api_key_returns_401` now passes; all 12 API key tests pass
- **Committed in:** `6f3352c` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed pre-existing operator isolation audit failure for `POST /log/qsos`**
- **Found during:** Task 2 (isolation audit test run)
- **Issue:** `POST /log/qsos` (HTMX UI route) uses `get_current_user_cookie` directly and derives callsign via `user.callsign` in the function body — not via a callsign-returning wrapper dep. The audit's `CALLSIGN_DEPS` set only included callsign-wrapper deps, so this route was flagged as missing callsign injection even before my changes.
- **Fix:** Added `get_current_user_cookie` to `CALLSIGN_DEPS` set with an explanatory comment; also added it to imports in the test file
- **Files modified:** `tests/test_operator_isolation.py`
- **Verification:** `test_all_qso_routes_inject_callsign_from_jwt` passes
- **Committed in:** `6f3352c` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bug fixes)
**Impact on plan:** Both fixes were necessary for correctness. The timezone fix prevents a runtime crash on expired token checks. The audit fix corrects a pre-existing false positive. No scope creep.

## Issues Encountered
- `tests/test_qso_api.py` has a pre-existing MongoDB connection issue (uses `mongodb://localhost:27017` without `directConnection=true`, picks up a Docker replica set hostname `mongodb:27017` that is not resolvable). This existed before Phase 27 and is unrelated to this plan's changes. The new `test_qso_api_key.py` uses `directConnection=true` and all its tests pass.

## User Setup Required
None - no external service configuration required. All changes are code-only.

## Next Phase Readiness
- Phase 28 (UDP X-API-Key auth) can now reuse `_resolve_user_from_api_key` logic as a reference pattern for the in-memory cache variant
- All QSO REST endpoints accept both JWT and X-API-Key — machine-to-machine callers (scripts, logging software) can POST QSOs immediately with no session management
- `token_is_active` timezone fix ensures reliable expiry enforcement across all token consumers (REST and future UDP)

---
*Phase: 027-x-api-key-rest-authentication*
*Completed: 2026-04-10*

## Self-Check: PASSED

- FOUND: app/auth/dependencies.py (get_current_user_jwt_or_apikey, get_current_operator_callsign_jwt_or_apikey, _resolve_user_from_api_key)
- FOUND: app/qso/router.py (all 5 endpoints wired to dual-auth deps)
- FOUND: app/tokens/service.py (token_is_active timezone bug fixed)
- FOUND: tests/test_qso_api_key.py (12 tests, all passing)
- FOUND: tests/test_operator_isolation.py (CALLSIGN_DEPS updated)
- FOUND: 027-01-SUMMARY.md
- Commits ec8cdf5 and 6f3352c verified in git log
