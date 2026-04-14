---
phase: 038-admin-backup-ui
plan: 01
subsystem: ui
tags: [fastapi, jinja2, htmx, tailwind, admin, backup]

# Dependency graph
requires:
  - phase: 037-backup-endpoint
    provides: GET /admin/ui/backup/download endpoint and cookie auth dependency

provides:
  - Backup page template at templates/admin/backup.html with Apple-style card layout and plain anchor download button
  - GET /admin/ui/backup route in ui_router.py protected by require_admin_cookie
  - Backup sidebar nav link in users.html so admin can navigate between Operators and Backup pages

affects: [admin-ui, backup-download, sidebar-nav]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - plain <a href> anchor for browser file download (never hx-* attributes — HTMX silently discards binary Content-Disposition responses)
    - Jinja2 block overrides per admin page (sidebar_nav, sidebar_user, sidebar_logout, content, active_page)
    - require_admin_cookie (not require_admin) for cookie-based auth on all admin UI routes

key-files:
  created:
    - templates/admin/backup.html
  modified:
    - app/admin/ui_router.py
    - templates/admin/users.html

key-decisions:
  - "Plain <a href> anchor for /admin/ui/backup/download — no hx-* attributes; HTMX intercepts XHR responses and silently discards binary payloads, causing the button to appear inert"
  - "require_admin_cookie dependency on backup_page — browser sends cookie not Bearer header; require_admin would cause silent 302 redirect"
  - "No npm run build — all CSS classes used in backup.html are existing Apple component tokens already compiled in output.css"

patterns-established:
  - "Per-page sidebar active state: each admin template explicitly sets nav-item-active on its own nav link and nav-item only on others"
  - "Admin pages extend base_app.html and override all sidebar blocks (sidebar_nav, sidebar_user, sidebar_logout)"

# Metrics
duration: 35min
completed: 2026-04-14
---

# Phase 038 Plan 01: Admin Backup UI Summary

**Backup page delivered at /admin/ui/backup with cookie-protected route, Apple-style card, and plain anchor download button; Backup nav link added to admin sidebar on both Operators and Backup pages**

## Performance

- **Duration:** 35 min
- **Started:** 2026-04-14T14:18:14Z
- **Completed:** 2026-04-14T14:53:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created templates/admin/backup.html extending base_app.html with correct sidebar nav (Operators inactive, Backup active), card layout, and plain download anchor — zero hx-* attributes
- Added GET /admin/ui/backup route to ui_router.py protected by Depends(require_admin_cookie), rendering the new template with no context variables
- Updated templates/admin/users.html sidebar_nav to include the Backup nav link (inactive) so the admin can navigate between the two admin pages

## Task Commits

Each task was committed atomically:

1. **Task 1: Create backup.html template and update users.html sidebar** - `391233e` (feat)
2. **Task 2: Add GET /admin/ui/backup route to ui_router.py** - `41fcd66` (feat)

**Plan metadata:** see final docs commit

## Files Created/Modified
- `templates/admin/backup.html` - New backup page template: sidebar nav with both Operators and Backup links, card section, plain `<a href="/admin/ui/backup/download">` download button
- `templates/admin/users.html` - Added Backup nav link (inactive) to sidebar_nav block
- `app/admin/ui_router.py` - Added backup_page handler at GET /backup using require_admin_cookie and returning admin/backup.html

## Decisions Made
- Plain `<a href>` anchor (not hx-get or hx-post) for the download button. HTMX intercepts requests and discards `Content-Disposition: attachment` binary responses silently — the download simply never happens with hx-* attributes.
- `require_admin_cookie` dependency (not `require_admin`). The browser POSTs a cookie, not an Authorization Bearer header. Using `require_admin` would return a silent 302 redirect to login, masking the real failure.
- No new CSS classes — all tokens (.card, .card-header, .card-body, .card-title, .btn-primary, .nav-item, .nav-item-active) already compiled in output.css from prior phases. No build step required.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `grep -c` returning exit code 1 when count is 0 caused shell command chaining to stop early; resolved by running verification checks individually.
- Global python3 has no fastapi installed; used `.venv/bin/activate` for route registration verification. Both `/admin/ui/backup` and `/admin/ui/backup/download` confirmed registered.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- v2.0 Database Backup milestone complete: backup endpoint (Phase 37) + backup UI page (Phase 38) both delivered
- Admin sidebar now contains both Operators and Backup nav links with correct active states on each page
- Full flow: admin logs in → sees Operators page → clicks Backup → sees backup page → clicks Download Backup → browser file save dialog fires (plain anchor bypasses HTMX)
- No blockers for production deployment

---
*Phase: 038-admin-backup-ui*
*Completed: 2026-04-14*
