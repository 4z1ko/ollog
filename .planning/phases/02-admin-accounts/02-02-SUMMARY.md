---
phase: 02-admin-accounts
plan: "02"
subsystem: ui
tags: [fastapi, jinja2, htmx, jwt, cookies, admin, operator-management]

# Dependency graph
requires:
  - phase: 02-01
    provides: Admin API router, User model, require_admin dependency, hash_password, JWT auth service
provides:
  - Admin web UI at /admin/ui with login, user management table, HTMX-driven CRUD actions
  - Cookie-based JWT auth (HttpOnly, SameSite=lax) for browser sessions
  - Redirect-on-auth-failure for all /admin/ui/* routes (no raw JSON errors in browser)
  - Exception handler in app.main scoped to /admin/ui/* prefix for 401/403 redirect
affects: [03-qso-crud, 05-live-feed]

# Tech tracking
tech-stack:
  added:
    - Jinja2Templates (bundled with fastapi[all] / python-multipart already installed)
    - HTMX 2.0.4 via CDN (no npm, no build step)
  patterns:
    - "Jinja2Templates instantiated once at module level in ui_router.py with directory='templates'"
    - "HTMX partial responses: hx-target='#users-table-body' hx-swap='innerHTML' returning users_table.html"
    - "Exception handler on app checks request.url.path.startswith('/admin/ui/') to redirect 401/403 to login"
    - "Cookie auth via Cookie(default=None) fastapi param; HttpOnly + SameSite=lax set on login success"
    - "Last-admin guard in toggle endpoint: count enabled admins before disabling any admin account"

key-files:
  created:
    - app/admin/ui_router.py
    - templates/base.html
    - templates/admin/login.html
    - templates/admin/users.html
    - templates/admin/users_table.html
    - static/.gitkeep
  modified:
    - app/auth/dependencies.py
    - app/main.py
    - Dockerfile

key-decisions:
  - "Exception handler approach used for UI auth redirects — app.exception_handler checks path prefix, returns RedirectResponse for 401/403 on /admin/ui/* routes; other routes still get JSON"
  - "HTMX used for all table mutations (create, toggle, reset-password) — responses return users_table.html partial, swapped into #users-table-body without full page reload"
  - "Inline CSS only in base.html — no external CSS framework; keeps deployment simple and avoids npm/build pipeline"

patterns-established:
  - "UI templates use {% extends 'base.html' %} / {% block content %} — consistent layout inheritance"
  - "HTMX partials pattern: endpoint returns partial template, HTMX swaps into named target element"
  - "Cookie auth separate from Bearer auth — get_current_user_cookie reads Cookie header, get_current_user reads Authorization Bearer"

# Metrics
duration: ~15min (including human verification)
completed: 2026-04-03
---

# Phase 2 Plan 02: Admin Web UI Summary

**Browser-based admin panel at /admin/ui with HTMX-driven operator management: cookie JWT login, create/toggle/reset-password without page reloads, auth-failure redirects to login (not JSON)**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-03T09:59:03Z
- **Completed:** 2026-04-03 (after human verification)
- **Tasks:** 2 (1 auto + 1 human-verify)
- **Files modified:** 9

## Accomplishments
- Admin login page at /admin/ui/login sets HttpOnly JWT cookie on success, redirects to users page
- Users management table with HTMX: create operator, toggle enabled/disabled, reset password — all update table inline without full reload
- Last-admin guard in toggle endpoint prevents disabling the sole enabled admin (returns error in table partial)
- Auth failures on all /admin/ui/* routes redirect to /admin/ui/login; no raw JSON 401/403 in the browser
- Dockerfile updated to copy templates/ and static/ directories for production builds

## Task Commits

Each task was committed atomically:

1. **Task 1: Cookie auth dependencies, UI router, templates, and static file setup** - `691c351` (feat)
2. **Task 2: Verify admin UI flow in browser** - (checkpoint: approved by user — no code commit)

**Plan metadata:** _(final docs commit — see below)_

## Files Created/Modified
- `app/admin/ui_router.py` - APIRouter at /admin/ui: login (GET/POST), users (GET), create (POST), toggle (POST), reset-password (POST), logout (GET); 222 lines
- `app/auth/dependencies.py` - Added get_current_user_cookie (Cookie-based) and require_admin_cookie; existing Bearer functions unchanged
- `app/main.py` - Added ui_router include, StaticFiles mount at /static, HTTPException handler for /admin/ui/* redirect
- `templates/base.html` - HTML5 boilerplate with HTMX 2.0.4 CDN, inline CSS for readability, content block
- `templates/admin/login.html` - Login form POSTing to /admin/ui/login; shows error context if set
- `templates/admin/users.html` - Full users page with create form (hx-post) and table with #users-table-body target
- `templates/admin/users_table.html` - Table row partial: toggle button and password reset form both target #users-table-body
- `static/.gitkeep` - Empty file ensuring static/ directory tracked in git
- `Dockerfile` - Added COPY templates/ and COPY static/ before CMD

## Decisions Made
- Exception handler approach for UI auth redirects: `app.exception_handler(HTTPException)` checks `request.url.path.startswith("/admin/ui/")` — simpler than per-route try/except; keeps protected route signatures clean
- HTMX 2.0.4 via CDN: no npm or build step needed; suitable for internal admin tool
- Inline CSS in base.html only: no framework dependency; keeps deployment self-contained

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 2 (Admin Accounts) fully complete: JSON API (02-01) and web UI (02-02) both done
- Ready for Phase 3 (QSO CRUD): operator auth (Bearer token from login) established; admin can create operator accounts via web UI before operators begin logging
- No blockers

---
*Phase: 02-admin-accounts*
*Completed: 2026-04-03*

## Self-Check: PASSED

- app/admin/ui_router.py: FOUND (confirmed in git show 691c351)
- app/auth/dependencies.py: FOUND (modified in 691c351)
- app/main.py: FOUND (modified in 691c351)
- templates/base.html: FOUND (created in 691c351)
- templates/admin/login.html: FOUND (created in 691c351)
- templates/admin/users.html: FOUND (created in 691c351)
- templates/admin/users_table.html: FOUND (created in 691c351)
- static/.gitkeep: FOUND (created in 691c351)
- Dockerfile: FOUND (modified in 691c351)
- commit 691c351: FOUND
