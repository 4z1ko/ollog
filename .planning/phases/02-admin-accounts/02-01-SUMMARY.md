---
phase: 02-admin-accounts
plan: "01"
subsystem: api
tags: [fastapi, beanie, pymongo, jwt, admin, operator-management]

# Dependency graph
requires:
  - phase: 01-04
    provides: User model, require_admin dependency, hash_password, JWT auth service
provides:
  - Admin API router at /admin/users with create, toggle-enabled, reset-password, list endpoints
  - Last-admin lockout guard on PATCH /{username}/enabled
  - 15 integration tests for all admin endpoints
affects: [02-02-admin-ui, 03-qso-crud, 05-live-feed]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "All admin endpoints use Depends(require_admin) directly in the decorator — no per-function param needed"
    - "Beanie ExpressionField form {User.enabled: value} used in .set() calls — resolves aliases correctly"
    - "Last-admin guard counts enabled admins by role query, not by checking current user identity"

key-files:
  created:
    - app/admin/__init__.py
    - app/admin/router.py
    - tests/test_admin_api.py
  modified:
    - app/main.py

key-decisions:
  - "require_admin injected via dependencies=[Depends(require_admin)] on the decorator — cleaner than per-function param since admin endpoints need no user object in body"
  - "aclose() used instead of close() for pymongo AsyncMongoClient in test fixtures — pymongo 4.9+ async client requires awaitable close"

patterns-established:
  - "Test fixtures in test file itself (not conftest.py) when conftest is owned by another plan"
  - "admin_db fixture pattern: init_beanie with [User, QSO], drop ollog_test, aclose() on teardown"

# Metrics
duration: 4min
completed: 2026-04-03
---

# Phase 2 Plan 01: Admin API Summary

**FastAPI admin CRUD API at /admin/users — create/toggle/reset-password/list operators, last-admin lockout guard, 15 passing integration tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-03T07:02:34Z
- **Completed:** 2026-04-03T07:06:34Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Admin API router with 4 endpoints (POST /admin/users/, PATCH /{username}/enabled, POST /{username}/reset-password, GET /admin/users/) mounted via app.main
- Last-admin lockout guard prevents disabling the sole enabled admin (409 Conflict)
- 15 integration tests covering success cases, 401/403 auth enforcement, duplicate username, last-admin guard, nonexistent user, disabled-user login rejection, and password reset side-effect verification

## Task Commits

Each task was committed atomically:

1. **Task 1: Admin API router with create, toggle-enabled, and reset-password endpoints** - `023ed74` (feat)
2. **Task 2: Admin API tests** - `d8f0e65` (feat)

**Plan metadata:** _(final docs commit — see below)_

## Files Created/Modified
- `app/admin/__init__.py` - Admin module package
- `app/admin/router.py` - APIRouter with 4 endpoints, Pydantic request models, last-admin guard
- `app/main.py` - Added include_router(admin_router) after auth_router
- `tests/test_admin_api.py` - 15 integration tests with admin_db fixture

## Decisions Made
- `dependencies=[Depends(require_admin)]` on decorator (not function param) — admin endpoints don't need the user object in the function body, so this avoids an unused parameter while still enforcing auth
- `aclose()` used for pymongo AsyncMongoClient teardown — pymongo 4.9+ async client's `close()` is now a coroutine; using `aclose()` removes the RuntimeWarning about unawaited coroutine

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Used `aclose()` instead of `close()` for pymongo AsyncMongoClient**
- **Found during:** Task 2 (admin API tests)
- **Issue:** pymongo 4.9+ `AsyncMongoClient.close()` is a coroutine; calling it without `await` generates `RuntimeWarning: coroutine 'AsyncMongoClient.close' was never awaited`
- **Fix:** Changed `client.close()` to `await client.aclose()` in the admin_db fixture
- **Files modified:** tests/test_admin_api.py
- **Verification:** Warning disappeared; all 15 tests still pass
- **Committed in:** d8f0e65 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Minor correctness fix in test teardown. No scope creep.

## Issues Encountered
- Beanie ExpressionField (`User.enabled`) is not accessible before `init_beanie` is called (class attributes are set by Beanie's init process), but at API endpoint runtime `init_beanie` has already been called during lifespan startup — so `{User.enabled: value}` in `.set()` calls works correctly as specified

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Admin API complete, ready for 02-02 (admin web UI) which calls the same endpoints
- All 15 tests pass; auth enforcement (401/403), last-admin guard, and side-effect correctness verified
- No blockers

---
*Phase: 02-admin-accounts*
*Completed: 2026-04-03*

## Self-Check: PASSED

- app/admin/__init__.py: FOUND
- app/admin/router.py: FOUND
- tests/test_admin_api.py: FOUND
- 02-01-SUMMARY.md: FOUND
- commit 023ed74: FOUND
- commit d8f0e65: FOUND
