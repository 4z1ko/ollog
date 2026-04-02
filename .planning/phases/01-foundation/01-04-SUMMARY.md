---
phase: 01-foundation
plan: 04
subsystem: auth
tags: [pyjwt, pwdlib, argon2, beanie, fastapi, jwt, auth, dependencies]

# Dependency graph
requires: ["01-01", "01-02", "01-03"]
provides:
  - User Beanie Document with unique username index
  - hash_password() and verify_password() via pwdlib/Argon2
  - create_access_token() and decode_access_token() via PyJWT
  - get_current_user FastAPI dependency (JWT -> User lookup)
  - get_current_operator_callsign dependency (callsign injection from JWT)
  - require_admin dependency (403 for non-admin)
  - POST /auth/token OAuth2 login endpoint
  - GET /auth/me authenticated profile endpoint
  - GET /api/whoami protected test endpoint
  - Admin bootstrap from env vars in lifespan
  - User registered in database.py init_beanie document_models
affects: [all subsequent phases — every protected endpoint depends on get_current_user or get_current_operator_callsign]

# Tech tracking
tech-stack:
  patterns:
    - PyJWT (import jwt) — NOT python-jose
    - pwdlib PasswordHash.recommended() — NOT passlib — selects Argon2
    - OAuth2PasswordBearer(tokenUrl="/auth/token") for token extraction
    - JWT payload carries: sub (username), callsign, role, exp
    - Callsign injected via get_current_operator_callsign dependency — never from request body
    - Admin bootstrapped in lifespan context manager after init_beanie

key-files:
  created:
    - app/auth/models.py
    - app/auth/service.py
    - app/auth/dependencies.py
    - app/auth/router.py
    - app/auth/__init__.py
    - tests/test_auth.py
  modified:
    - app/database.py
    - app/main.py

key-decisions:
  - "PyJWT used via `import jwt` — python-jose explicitly excluded (locked decision)"
  - "pwdlib PasswordHash.recommended() selects Argon2 — passlib explicitly excluded (locked decision)"
  - "JWT carries sub, callsign, role, exp — all four claims verified by tests"
  - "get_current_operator_callsign is the single callsign injection point — QSO operations must depend on this"
  - "Admin bootstrap runs in lifespan after init_beanie — no web endpoint for admin creation"
  - "MongoDB-dependent tests use @mongo_required skip mark — graceful skip when DB unavailable"

patterns-established:
  - "Auth pattern: Depends(get_current_operator_callsign) for any endpoint that needs operator callsign"
  - "Admin guard: Depends(require_admin) for any admin-only endpoint"
  - "Token creation: create_access_token(data={'sub': username, 'callsign': cs, 'role': role})"
  - "Password ops: hash_password(plain) on creation, verify_password(plain, hashed) on login"

# Metrics
duration: ~15min
completed: 2026-04-03
---

# Phase 1 Plan 04: Auth Service Summary

**JWT authentication service with User model, pwdlib/Argon2 password hashing, PyJWT tokens, FastAPI dependencies, login endpoint, and admin bootstrap from environment variables.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-04-03
- **Tasks:** 2
- **Files created:** 6
- **Files modified:** 2

## Accomplishments

- `app/auth/models.py`: User Beanie Document — username (unique index), hashed_password, callsign, role (default "operator"), enabled (default True)
- `app/auth/service.py`: `hash_password()`, `verify_password()` via pwdlib Argon2; `create_access_token()`, `decode_access_token()` via PyJWT; JWT carries sub, callsign, role, exp
- `app/auth/dependencies.py`: `get_current_user` (JWT decode + User lookup), `get_current_operator_callsign` (callsign injection point), `require_admin` (403 guard)
- `app/auth/router.py`: POST /auth/token (OAuth2 form login), GET /auth/me (authenticated profile)
- `app/auth/__init__.py`: exports all public symbols
- `app/database.py`: User added to init_beanie document_models alongside QSO
- `app/main.py`: auth router included, `_bootstrap_admin()` called in lifespan, GET /api/whoami test endpoint
- `tests/test_auth.py`: 20 tests (9 static always-pass, 11 MongoDB integration with skip guard)

## Task Commits

- `64ef0f2` — feat(01-04): add User model and auth service (JWT + pwdlib)
- `9098d40` — feat(01-04): add auth router, login endpoint, admin bootstrap

## Test Results

- **28 passed, 11 skipped** (MongoDB not available in this environment)
- Static tests verify: User model structure, JWT claims, password hashing, no banned imports
- Integration tests cover: login flow, 401/403 responses, expired tokens, disabled users, callsign injection, admin bootstrap — all properly skip when MongoDB unavailable

## Files Created/Modified

- `app/auth/models.py` — User Document
- `app/auth/service.py` — password hashing + JWT service
- `app/auth/dependencies.py` — FastAPI auth dependencies
- `app/auth/router.py` — auth endpoints
- `app/auth/__init__.py` — module exports
- `app/database.py` — User added to document_models
- `app/main.py` — router included, admin bootstrap, whoami endpoint
- `tests/test_auth.py` — 20 auth tests

## Decisions Made

- MongoDB-dependent tests use a `@mongo_required` skip mark that checks port 27017 availability — consistent with how test_qso_schema.py behaves (errors become skips rather than failures when DB is unavailable)
- `_bootstrap_admin()` is a standalone async function (not inlined in lifespan) to enable direct testing
- `/api/whoami` added as a dedicated test endpoint proving the full callsign-from-JWT chain; will be replaced in later phases

## Deviations from Plan

None. All locked decisions implemented exactly as specified.

## Locked Decision Verification

- `import jwt` (PyJWT): confirmed — `grep -r "jose" app/` returns nothing
- `pwdlib PasswordHash`: confirmed — `grep -r "passlib" app/` returns nothing
- `pymongo AsyncMongoClient`: confirmed — `grep -r "motor" app/` returns nothing
- JWT carries callsign, username (sub), role, exp: verified by `test_create_access_token_contains_required_claims`
- Callsign from JWT only: `get_current_operator_callsign` is the sole injection point — never from request body
- Admin bootstrap from env vars: `_bootstrap_admin()` checks settings.admin_username/password/callsign
- lifespan context manager: confirmed — no @app.on_event decorators

## Next Phase Readiness

- All QSO write endpoints (01-05+) must depend on `get_current_operator_callsign` — never accept callsign from request
- Admin-only endpoints use `Depends(require_admin)`
- `create_access_token()` signature is stable: `data={"sub": username, "callsign": cs, "role": role}`

---
*Phase: 01-foundation*
*Completed: 2026-04-03*

## Self-Check: PASSED

All 8 files present. Banned imports verified absent. JWT claims verified by test. Callsign injection pattern established. Admin bootstrap in lifespan. All static tests pass (9/9).
