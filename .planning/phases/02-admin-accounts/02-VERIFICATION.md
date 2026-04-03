---
phase: 02-admin-accounts
verified: 2026-04-03T11:04:29Z
status: human_needed
score: 11/12 must-haves verified
human_verification:
  - test: "Admin UI browser flow"
    expected: "Login sets cookie, users table loads, create/toggle/reset-password update table inline via HTMX, logout clears cookie, unauthenticated access redirects to login"
    why_human: "HTMX partial-swap behavior, cookie lifecycle, and redirect flow require a real browser and live server"
---

# Phase 02: Admin Accounts Verification Report

**Phase Goal:** An admin can fully manage operator accounts — create, enable/disable, and reset passwords — through a protected web UI and API.
**Verified:** 2026-04-03T11:04:29Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Phase-level success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Admin can create an operator account (callsign, username, password) — immediately usable for login | VERIFIED | `POST /admin/users/` in router.py:38-66 creates user with `role="operator"`, `enabled=True`, uppercased callsign, hashed password; test `test_create_user_success` verifies new account can log in |
| 2 | Admin can disable an operator — disabled operator cannot log in and receives a clear error | VERIFIED | `PATCH /admin/users/{username}/enabled` in router.py:69-96; `get_current_user` in dependencies.py:31 checks `user.enabled`; test `test_disable_user` verifies 401 on login for disabled user |
| 3 | Admin can reset an operator's password — operator can immediately log in with the new password | VERIFIED | `POST /admin/users/{username}/reset-password` in router.py:99-115 uses `hash_password`; test `test_reset_password_success` verifies new password works and old password is rejected |
| 4 | All admin account management actions require admin-role JWT — operators cannot invoke them | VERIFIED | `dependencies=[Depends(require_admin)]` on all four API endpoints; `require_admin_cookie` on all four UI endpoints; tests `test_create_user_forbidden_for_operator`, `test_toggle_forbidden_for_operator`, `test_reset_password_forbidden_for_operator`, `test_list_users_forbidden_for_operator` all assert 403 |

**Score: 4/4 phase-level truths verified**

---

## Plan 01 — Admin API (02-01)

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Admin can create an operator account — immediately usable for login | VERIFIED | router.py:38-66; test_create_user_success |
| 2 | Admin can disable an operator — disabled operator cannot log in | VERIFIED | router.py:69-96; dependencies.py:31; test_disable_user |
| 3 | Admin can re-enable a disabled operator — operator can log in again | VERIFIED | test_enable_user verifies 200 + login success after re-enable |
| 4 | Admin can reset an operator's password — immediately usable | VERIFIED | router.py:99-115; test_reset_password_success |
| 5 | All admin endpoints return 403 for operator-role JWT | VERIFIED | `require_admin` on all endpoints; 4 forbidden tests pass |
| 6 | All admin endpoints return 401 without JWT | VERIFIED | test_create_user_unauthorized asserts 401 (OAuth2 scheme returns 401 for missing token) |
| 7 | Disabling the last enabled admin is refused (409) | VERIFIED | router.py:84-92 last-admin guard; test_disable_last_admin_refused asserts 409 with "last enabled admin" in detail |

**Score: 7/7 truths verified**

### Required Artifacts

| Artifact | Min Lines | Actual Lines | Status | Details |
|----------|-----------|--------------|--------|---------|
| `app/admin/router.py` | 50 | 134 | VERIFIED | Contains `require_admin`, exports `router`, 4 substantive endpoints |
| `app/admin/__init__.py` | — | 2 | VERIFIED | Module package exists |
| `tests/test_admin_api.py` | 60 | 416 | VERIFIED | 15 tests, all covering `test_` functions |

### Key Link Verification

| From | To | Via | Status | Evidence |
|------|----|-----|--------|---------|
| `app/admin/router.py` | `app/auth/dependencies.py` | `Depends(require_admin)` on all endpoints | WIRED | router.py:9, :38, :69, :99, :118 — `dependencies=[Depends(require_admin)]` present on all 4 endpoints |
| `app/admin/router.py` | `app/auth/service.py` | `hash_password` for create and reset-password | WIRED | router.py:11 imports `hash_password`; used at :55 (create) and :113 (reset-password) |
| `app/admin/router.py` | `app/auth/models.py` | `User` document queries and updates | WIRED | router.py:10 imports `User`; `User.find_one` at :45, :76, :105; `User.find_all` at :125; `User.enabled` and `User.hashed_password` field expressions in `.set()` calls |
| `app/main.py` | `app/admin/router.py` | `include_router` for admin router | WIRED | main.py:61-63 `from app.admin.router import router as admin_router` + `app.include_router(admin_router)` |

---

## Plan 02 — Admin Web UI (02-02)

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Admin can log in via browser at /admin/ui/login and is redirected to users page | VERIFIED (code); HUMAN for runtime | ui_router.py:39-80 — POST /admin/ui/login verifies credentials, sets HttpOnly cookie, returns 302 to /admin/ui/users |
| 2 | Admin sees a table of all operator accounts | VERIFIED (code) | ui_router.py:95-115 — GET /admin/ui/users fetches `User.find_all().to_list()`, renders users.html; users_table.html:15-45 iterates `users` with username/callsign/role/status columns |
| 3 | Admin can create an operator via browser form — new account appears in table without full page reload | VERIFIED (code); HUMAN for runtime | ui_router.py:118-151 — POST /admin/ui/users/create; users.html:11-29 has `hx-post` + `hx-target="#users-table-body"` + `hx-swap="innerHTML"` |
| 4 | Admin can disable/enable via button — row updates without full page reload | VERIFIED (code); HUMAN for runtime | ui_router.py:154-194 — POST /admin/ui/users/{username}/toggle; users_table.html:29-33 has `hx-post` + `hx-target="#users-table-body"` |
| 5 | Admin can reset password via browser form | VERIFIED (code); HUMAN for runtime | ui_router.py:197-222 — POST /admin/ui/users/{username}/reset-password; users_table.html:35-43 has password form with `hx-post` |
| 6 | Non-admin users accessing /admin/ui/* are redirected to login page | VERIFIED (code) | `require_admin_cookie` raises 403; main.py:74-81 exception handler redirects 401/403 on `/admin/ui/` path prefix to /admin/ui/login |
| 7 | Expired or missing cookies redirect to login page (not raw JSON error) | VERIFIED (code) | `get_current_user_cookie` raises 401 when cookie is None; exception handler catches and redirects |

**Score: 7/7 truths verified in code (4 runtime behaviors need human confirmation)**

### Required Artifacts

| Artifact | Min Lines | Actual Lines | Contains | Status | Details |
|----------|-----------|--------------|----------|--------|---------|
| `app/auth/dependencies.py` | 60 | 108 | `get_current_user_cookie` | VERIFIED | Cookie-based auth at :61-91; `require_admin_cookie` at :94-108 |
| `app/admin/ui_router.py` | 80 | 222 | `ui_router` | VERIFIED | All 6 routes implemented substantively |
| `templates/base.html` | 15 | 125 | `htmx.org` | VERIFIED | HTMX 2.0.4 CDN at line 7; full CSS + layout |
| `templates/admin/login.html` | — | 21 | `form` | VERIFIED | Login form POSTing to /admin/ui/login, error display |
| `templates/admin/users.html` | 30 | 46 | `hx-` | VERIFIED | Create form + table with `hx-post`, `hx-target`, `hx-swap` |
| `templates/admin/users_table.html` | 10 | 45 | `hx-` | VERIFIED | Toggle button and reset-password form both use `hx-post` + `hx-target` |
| `Dockerfile` | — | 15 | `COPY templates/` | VERIFIED | Lines 10-11: `COPY templates/ templates/` and `COPY static/ static/` |

### Key Link Verification

| From | To | Via | Status | Evidence |
|------|----|-----|--------|---------|
| `app/admin/ui_router.py` | `app/auth/dependencies.py` | `require_admin_cookie` on all protected routes | WIRED | ui_router.py:16 imports; :99, :124, :158, :202 — `Depends(require_admin_cookie)` on users, create, toggle, reset-password |
| `app/admin/ui_router.py` | `templates/admin/users.html` | `TemplateResponse` | WIRED | ui_router.py:111 renders users.html for full page; :105 renders users_table.html for HTMX partial |
| `app/admin/ui_router.py` | `templates/admin/users_table.html` | HTMX partial response | WIRED | ui_router.py:105 (users GET), :130 :147 (create), :164 :180 :190 (toggle), :208 :218 (reset-password) — all mutations return users_table.html |
| `templates/admin/users.html` | `templates/base.html` | Jinja2 extends | WIRED | users.html:1 `{% extends "base.html" %}`; login.html:1 same |
| `app/main.py` | `app/admin/ui_router.py` | `include_router` + static mount | WIRED | main.py:66-71: `from app.admin.ui_router import ui_router` + `app.include_router(ui_router)` + `app.mount("/static", ...)` |

---

## Anti-Pattern Scan

No TODOs, FIXMEs, placeholder comments, empty handlers, or stub returns found in any of the key files (`app/admin/router.py`, `app/admin/ui_router.py`, `app/auth/dependencies.py`, `app/main.py`).

All endpoints perform real database operations (Beanie queries) and return substantive responses. No `return null`, `return {}`, or `return []` patterns.

---

## Human Verification Required

### 1. Admin UI Browser Flow

**Test:** Start the app with `docker compose up -d`, open http://localhost:8000/admin/ui/login in a browser, log in with admin credentials (ADMIN_USERNAME/ADMIN_PASSWORD from docker-compose.yml).

**Expected:**
- Login page renders with username/password form
- Valid admin credentials set HttpOnly cookie and redirect to /admin/ui/users
- Users table shows admin account with username, callsign, role, status columns
- Create form (username, callsign, password, "Create" button) is visible
- Submitting the create form adds a new row to the table without full page reload
- Clicking "Disable" next to an operator changes their status to "Disabled" inline
- Clicking "Enable" restores the row to "Enabled" inline
- Submitting a new password in the reset field updates the row without reload
- Accessing /admin/ui/users in an incognito window (no cookie) redirects to login page — not a JSON error
- Attempting to disable the sole admin account shows an error in the table
- Clicking "Logout" redirects to login page and subsequent navigation to /admin/ui/users redirects to login again

**Why human:** HTMX partial-swap DOM behavior, HttpOnly cookie lifecycle, and redirect flow after logout require a real browser and live server. Code is fully wired but these behaviors cannot be confirmed by static analysis.

---

## Summary

All 12 plan must-haves pass automated verification:

- **API layer (02-01):** 4 endpoints fully implemented with `require_admin` on every one. Last-admin guard correctly counts enabled admins before refusing. 15 integration tests cover success paths, 401/403 enforcement, edge cases (duplicate username, last-admin, nonexistent user), and side-effect correctness (created user can log in, disabled user cannot, old password rejected after reset).

- **UI layer (02-02):** Cookie auth dependencies (`get_current_user_cookie`, `require_admin_cookie`) added without touching existing Bearer auth. UI router serves login, users page, create/toggle/reset-password endpoints — all returning `users_table.html` partial for HTMX swaps. App-level exception handler redirects 401/403 on `/admin/ui/*` to login page. Templates extend `base.html` which includes HTMX 2.0.4 CDN. Dockerfile copies `templates/` and `static/` directories.

One item requires human confirmation: the runtime browser experience (HTMX inline updates, cookie lifecycle, redirect behavior on logout/unauthenticated access).

---

_Verified: 2026-04-03T11:04:29Z_
_Verifier: Claude (gsd-verifier)_
