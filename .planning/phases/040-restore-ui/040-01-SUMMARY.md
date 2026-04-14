---
phase: 040-restore-ui
plan: 01
subsystem: ui
tags: [tailwind, htmx, fastapi, jinja2, css, modal]

# Dependency graph
requires:
  - phase: 039-restore-backend
    provides: POST /admin/ui/restore/upload, POST /admin/ui/restore/confirm, password_modal.html, upload_error.html fragments
provides:
  - GET /admin/ui/restore route with dual-render (full page vs HTMX cancel bare div)
  - templates/admin/restore.html with .gz upload form and HTMX wiring
  - modal-backdrop, modal-box, modal-title, modal-body, modal-actions, form-group, form-control CSS component classes
  - Restore nav link added to users.html and backup.html sidebars (three-link nav complete)
affects: [restore-backend, admin-ui, css-build]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "dual-render GET route: full HTML page for direct navigation, bare div fragment for HTMX cancel (avoids page reload on modal dismiss)"
    - "modal-backdrop uses raw CSS backdrop-filter instead of @apply — Safari requires fixed pixel values not CSS var refs"
    - "HTMX upload form uses hx-encoding=multipart/form-data with separate #restore-result and #restore-modal swap targets as siblings"

key-files:
  created:
    - templates/admin/restore.html
  modified:
    - static/css/input.css
    - static/css/output.css
    - app/admin/ui_router.py
    - templates/admin/users.html
    - templates/admin/backup.html

key-decisions:
  - "#restore-modal div is a sibling of #restore-result (not nested in form) — cancel button targets #restore-modal with outerHTML swap to clear modal"
  - "GET /restore returns HTMLResponse('<div id=\"restore-modal\"></div>') when hx-request header present — clears modal without page reload"
  - "modal-backdrop backdrop-filter uses raw CSS (-webkit-backdrop-filter: blur(4px)) not @apply — consistent with glass-card Safari fix pattern"

patterns-established:
  - "Dual-render GET route: check hx_request header, return fragment or full page"
  - "Admin sidebar: always three nav links (Operators, Backup, Restore), only current page gets nav-item-active"

# Metrics
duration: 4min
completed: 2026-04-14
---

# Phase 40 Plan 01: Restore UI Summary

**Restore admin page shell with modal CSS component classes, HTMX dual-render GET route, .gz upload form, and three-link sidebar nav across all admin pages**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-14T18:05:50Z
- **Completed:** 2026-04-14T18:09:14Z
- **Tasks:** 2 auto tasks complete (1 checkpoint pending human verify)
- **Files modified:** 5 (plus output.css rebuild)

## Accomplishments
- Added 7 CSS component classes (modal-backdrop, modal-box, modal-title, modal-body, modal-actions, form-group, form-control) to input.css and rebuilt output.css — modal fragments from Phase 39 now have compiled styles
- Created restore.html with HTMX-wired .gz upload form: hx-post to /restore/upload targeting #restore-result, and sibling #restore-modal swap target for the password modal
- Added GET /admin/ui/restore with auth gate (require_admin_cookie) and dual-render logic: full page for browser navigation, bare `<div id="restore-modal"></div>` for HTMX cancel
- Added Restore nav link to users.html and backup.html sidebars — all three admin pages now show the complete three-link nav

## Task Commits

Each task was committed atomically:

1. **Task 1: Add modal and form-control CSS component classes** - `469d191` (feat)
2. **Task 2: Create restore.html, add GET route, update sidebars** - `d705d6d` (feat)

## Files Created/Modified
- `static/css/input.css` - Added 7 modal/form component classes in @layer components
- `static/css/output.css` - Rebuilt with npm run build (modal-backdrop, modal-box, form-control verified present)
- `templates/admin/restore.html` - New Restore page extending base_app.html with three-link sidebar, upload form, HTMX targets
- `app/admin/ui_router.py` - Added GET /admin/ui/restore (restore_page) with dual-render between line 258 and the POST /restore/upload route
- `templates/admin/users.html` - Added Restore nav link after Backup link in sidebar_nav block
- `templates/admin/backup.html` - Added Restore nav link after Backup active link in sidebar_nav block

## Decisions Made
- `#restore-modal` is a sibling div of `#restore-result`, not nested inside the form — required by HTMX outerHTML swap pattern used by the Cancel button
- GET /restore returns a bare `<div id="restore-modal"></div>` on HTMX requests (hx_request header present) to clear the modal without triggering a full page reload
- `backdrop-filter` in `.modal-backdrop` uses raw CSS `(-webkit-backdrop-filter: blur(4px))` rather than `@apply` — consistent with the glass-card Safari fix pattern established in Phase 32

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required. Human verification checkpoint requires starting the dev server and testing the upload flow interactively.

## Next Phase Readiness
- Restore page UI shell complete and wired to Phase 39 backend routes
- Human verification checkpoint pending: auth gate, page render, three-link sidebar, file upload modal flow, cancel dismiss, and modal styling must be confirmed
- After human approval, Phase 40 Plan 01 is fully complete and v2.1 Database Restore milestone is done

---
*Phase: 040-restore-ui*
*Completed: 2026-04-14*

## Self-Check: PASSED

- FOUND: templates/admin/restore.html
- FOUND: static/css/input.css
- FOUND: static/css/output.css
- FOUND: app/admin/ui_router.py
- FOUND: 040-01-SUMMARY.md
- FOUND commit: 469d191 (Task 1 — CSS modal classes)
- FOUND commit: d705d6d (Task 2 — restore page, route, sidebar links)
