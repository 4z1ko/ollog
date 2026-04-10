---
phase: 029-admin-container-isolation
verified: 2026-04-10T23:55:00Z
status: human_needed
score: 7/7 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 6/7
  gaps_closed:
    - "admin container serves /admin/*, /auth, and /health; returns 404 for /log/ and /api/ — app/main.py no longer includes admin_router or ui_router"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Confirm admin container port isolation"
    expected: "curl http://localhost:8001/admin/ui/login returns 200 HTML; curl http://localhost:8000/admin/ui/login returns 404"
    why_human: "Requires running Docker Compose — cannot verify programmatically without containers"
  - test: "Confirm admin_token cookie is set correctly on login"
    expected: "POST /admin/ui/login on port 8001 sets Set-Cookie: admin_token=...; HttpOnly; SameSite=Lax"
    why_human: "Requires live admin container — verified by code inspection but needs runtime confirmation"
---

# Phase 29: Admin Container Isolation Verification Report

**Phase Goal:** Admin routes (`/admin/*`, `/auth`, `/health`) run as a separate Docker Compose service on port 8001, startable and stoppable independently without affecting the operator app on port 8000.
**Verified:** 2026-04-10T23:55:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `docker compose up` starts only app (port 8000); admin does not start | VERIFIED | `docker-compose.yml` lines 39-40: `profiles: [admin]` on admin service; profile-gated services are skipped without `--profile admin` |
| 2 | `docker compose --profile admin up` starts both app (8000) and admin (8001) | VERIFIED | `docker-compose.yml` admin service on port 8001 with `profiles: [admin]` |
| 3 | admin container serves `/admin/*`, `/auth`, `/health`; returns 404 for `/log/` and `/api/` | VERIFIED | `admin_main.py` includes auth_router, admin_router, ui_router, and `/health` only. `app/main.py` no longer includes admin_router or ui_router — confirmed by full file read (lines 76-115: auth_router, qso_router, qso_ui_router, adif_router, feed_router, profile_router, token_router only) |
| 4 | operator app (`app/main.py`) does NOT serve `/admin/*` routes — those routes are absent | VERIFIED | `app/main.py` contains zero references to `admin_router` or `ui_router` for admin. No admin import lines present |
| 5 | admin login sets cookie named `admin_token`; operator `access_token` cookie is not changed | VERIFIED | `app/admin/ui_router.py` line 75: `response.set_cookie(key="admin_token", ...)`. Operator cookie (`access_token`) is set only by the separate operator UI login |
| 6 | operator app on port 8000 is completely unaffected by admin container stop/start | VERIFIED | `api` service in `docker-compose.yml` has no `depends_on` referencing `admin`. Services share only MongoDB |
| 7 | starting either service without SECRET_KEY in .env fails with Pydantic validation error | VERIFIED | `app/config.py` has `secret_key: str` with no default; Pydantic-settings raises `ValidationError` on startup if absent |
| 8 | all existing tests pass after bootstrap extraction | PARTIAL | 72 non-MongoDB unit tests pass. `test_qso_duplicate_rejected` and `test_qso_soft_delete_flag` fail with infrastructure errors (require live MongoDB replica-set); these failures predate phase 29 |

**Score:** 7/7 must-have truths verified (Truth 8 pre-existing infrastructure failure, not a phase regression)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/auth/bootstrap.py` | contains `async def _bootstrap_admin` | VERIFIED | Line 8: `async def _bootstrap_admin() -> None:` — full 35-line implementation |
| `app/admin_main.py` | contains `app = FastAPI` | VERIFIED | Line 16: `app = FastAPI(title="ollog-admin", version="0.1.0", lifespan=lifespan)` — fully wired |
| `app/auth/dependencies.py` | contains `admin_token` | VERIFIED | Lines 111-142: `get_current_admin_cookie` reads `admin_token: str | None = Cookie(default=None)` |
| `app/admin/ui_router.py` | contains `admin_token` | VERIFIED | Line 75: `response.set_cookie(key="admin_token", ...)` in `login_submit` |
| `docker-compose.yml` | contains `profiles` | VERIFIED | Lines 39-40: `profiles: [admin]` on admin service |
| `app/main.py` | must NOT contain `admin_router` | VERIFIED | Full file read confirms zero occurrences of `admin_router` or any admin UI router import |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/main.py` | `app/auth/bootstrap.py` | `from app.auth.bootstrap import _bootstrap_admin` | VERIFIED | Line 12 of main.py — bootstrap correctly imported and called in lifespan |
| `app/admin_main.py` | `app/auth/bootstrap.py` | `from app.auth.bootstrap import _bootstrap_admin` | VERIFIED | Line 5 of admin_main.py — does not import from app.main |
| `require_admin_cookie` | `get_current_admin_cookie` | `Depends(get_current_admin_cookie)` | VERIFIED | Lines 145-148 of dependencies.py: `require_admin_cookie` takes `user: User = Depends(get_current_admin_cookie)` |
| `docker-compose.yml` admin service | SECRET_KEY | must NOT have hardcoded SECRET_KEY | VERIFIED | Admin service uses `env_file: .env` only; no hardcoded SECRET_KEY |

### Requirements Coverage

Not assessed — REQUIREMENTS.md phase mapping not checked for this phase.

### Anti-Patterns Found

None. The previously-flagged anti-pattern (admin routes registered on port 8000) has been resolved.

### Human Verification Required

**1. Port isolation confirmation**

**Test:** With both services running, confirm `curl http://localhost:8000/admin/ui/login` returns 404 and `curl http://localhost:8001/admin/ui/login` returns 200.
**Expected:** Strict port separation — admin UI accessible only on 8001, not on 8000.
**Why human:** Requires running Docker Compose with real containers.

**2. admin_token cookie runtime behavior**

**Test:** POST to `http://localhost:8001/admin/ui/login` with valid admin credentials.
**Expected:** Response sets `Set-Cookie: admin_token=<jwt>; HttpOnly; SameSite=Lax` and does NOT set or modify `access_token`.
**Why human:** Verified by code inspection; runtime confirmation recommended.

### Re-verification Summary

The single gap from the initial verification has been closed. `app/main.py` previously registered `admin_router` and `ui_router` (for the admin panel), making `/admin/*` accessible on port 8000 as well as 8001. Those registrations have been removed. The current `app/main.py` (158 lines) includes only operator-facing routers: `auth_router`, `qso_router`, `qso_ui_router`, `adif_router`, `feed_router`, `profile_router`, and `token_router`. No admin routes, no admin imports.

All 7 must-have truths now pass automated verification. The two remaining human verification items (port isolation under live Docker, cookie runtime behavior) were present in the initial report and are unchanged — they require running containers, not code fixes.

---

_Verified: 2026-04-10T23:55:00Z_
_Verifier: Claude (gsd-verifier)_
