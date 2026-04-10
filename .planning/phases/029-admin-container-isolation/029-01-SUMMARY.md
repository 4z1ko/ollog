---
phase: 029-admin-container-isolation
plan: 01
subsystem: infra
tags: [docker, fastapi, jwt, cookie, docker-compose]

# Dependency graph
requires:
  - phase: 025-admin-ui
    provides: app/admin/ui_router.py with login/logout cookie handling
  - phase: 022-jwt-auth
    provides: JWT auth dependencies, get_current_user_cookie pattern
provides:
  - app/auth/bootstrap.py with _bootstrap_admin function, importable by any entry point
  - app/admin_main.py standalone FastAPI entry point for admin container on port 8001
  - app/auth/dependencies.py get_current_admin_cookie reading admin_token cookie
  - docker-compose.yml admin service gated behind profiles: [admin]
affects: [030-database-backup, 031-docs-rewrite]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Standalone FastAPI entry point per container role (admin_main.py vs main.py)"
    - "RFC 6265 cookie name separation: admin_token for port 8001, access_token for port 8000"
    - "Docker Compose profiles gate for optional services"

key-files:
  created:
    - app/auth/bootstrap.py
    - app/admin_main.py
  modified:
    - app/main.py
    - app/auth/dependencies.py
    - app/admin/ui_router.py
    - docker-compose.yml
    - tests/test_auth.py

key-decisions:
  - "admin_main.py is a standalone FastAPI entry point — never imports from app.main"
  - "Admin cookie renamed to admin_token to prevent RFC 6265 port-scope cookie collision"
  - "SECRET_KEY hardcoded default removed from docker-compose.yml — must come from .env"
  - "Admin lifespan is minimal: init_db + _bootstrap_admin only; no UDP, no SSE watcher"

patterns-established:
  - "Bootstrap pattern: _bootstrap_admin in app/auth/bootstrap.py, imported by both main.py and admin_main.py"
  - "Cookie isolation: each service uses a distinct cookie name corresponding to its role"

# Metrics
duration: 4min
completed: 2026-04-10
---

# Phase 29 Plan 01: Admin Container Isolation Summary

**Standalone admin FastAPI entry point on port 8001 with admin_token cookie, Docker Compose profile gate, and extracted bootstrap module shared between both containers**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-10T20:06:39Z
- **Completed:** 2026-04-10T20:10:51Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Created `app/auth/bootstrap.py` with `_bootstrap_admin` extracted from `app/main.py`, importable by any FastAPI entry point
- Created `app/admin_main.py` as a fully standalone FastAPI app for the admin container — no imports from `app.main`, minimal lifespan (DB init + bootstrap only)
- Added `get_current_admin_cookie` dependency reading `admin_token` cookie; updated `require_admin_cookie` to depend on it; renamed admin login/logout cookie from `access_token` to `admin_token`
- Added `admin` service to `docker-compose.yml` behind `profiles: [admin]` on port 8001; removed hardcoded `SECRET_KEY` default from `api` service

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract _bootstrap_admin to app/auth/bootstrap.py** - `d477c87` (feat)
2. **Task 2: Create admin_main.py and update cookie dependencies** - `130ab53` (feat)
3. **Task 3: Add admin Docker Compose service and remove hardcoded SECRET_KEY** - `b3649d6` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `app/auth/bootstrap.py` - Extracted `_bootstrap_admin` function, importable by both entry points
- `app/admin_main.py` - Standalone FastAPI entry point for admin container, port 8001
- `app/main.py` - Removed `_bootstrap_admin` definition; imports from `app.auth.bootstrap`
- `app/auth/dependencies.py` - Added `get_current_admin_cookie` (reads `admin_token`); updated `require_admin_cookie`
- `app/admin/ui_router.py` - Cookie key changed from `access_token` to `admin_token` in set_cookie and delete_cookie
- `docker-compose.yml` - Added `admin` service with `profiles: [admin]`, port 8001; removed hardcoded `SECRET_KEY`
- `tests/test_auth.py` - Updated `test_admin_bootstrap` to patch via `bootstrap_module` instead of `main_module`

## Decisions Made
- `admin_main.py` is a standalone FastAPI entry point and never imports from `app.main`
- Admin cookie renamed to `admin_token` to prevent RFC 6265 port-scope cookie collision between ports 8000 and 8001
- `SECRET_KEY` hardcoded default removed; both services must source it from `.env`
- Admin lifespan is minimal (`init_db` + `_bootstrap_admin` only) — no UDP listener, no SSE change-stream watcher

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- MongoDB-dependent tests are skipped in local dev environment (connect to `mongodb:27017` Docker hostname); 103 static tests pass. This is pre-existing behaviour, not caused by this plan.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Admin container isolation complete; `docker compose --profile admin up` will start both `api` (port 8000) and `admin` (port 8001)
- `SECRET_KEY` must be present in `.env` — both services will fail with a Pydantic validation error if absent
- Phase 30 (Database Backup) can proceed; backup lifespan will be added to `app/main.py`

---
*Phase: 029-admin-container-isolation*
*Completed: 2026-04-10*

## Self-Check: PASSED

- app/auth/bootstrap.py: FOUND
- app/admin_main.py: FOUND
- 029-01-SUMMARY.md: FOUND
- Commit d477c87 (Task 1): FOUND
- Commit 130ab53 (Task 2): FOUND
- Commit b3649d6 (Task 3): FOUND
