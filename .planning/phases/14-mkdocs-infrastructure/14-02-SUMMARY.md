---
phase: 14-mkdocs-infrastructure
plan: 02
subsystem: infra
tags: [fastapi, staticfiles, mkdocs, docker, documentation]

# Dependency graph
requires:
  - phase: 14-01
    provides: site/ directory built and committed, ready for StaticFiles mount
provides:
  - StaticFiles mount at /guide in app/main.py (html=True, before /static)
  - Dockerfile COPY site/ site/ for production image
  - /guide endpoint serving MkDocs documentation at sub-path
affects: [15-mkdocs-content, Dockerfile deployment, app/main.py routing]

# Tech tracking
tech-stack:
  added: []
  patterns: [StaticFiles mount order is load-bearing — /guide registered before /static, html=True enables automatic index.html serving at directory paths]

key-files:
  created: []
  modified: [app/main.py, Dockerfile]

key-decisions:
  - "/guide StaticFiles mount registered before /static in app/main.py — mount order determines precedence for overlapping paths in FastAPI"
  - "html=True on StaticFiles mount enables /guide to serve site/index.html and /guide/somepage/ to serve site/somepage/index.html automatically"
  - "COPY site/ site/ added to Dockerfile — pre-built docs included in production image without installing MkDocs"

patterns-established:
  - "FastAPI static mount order: register specific-path mounts before catch-all mounts"

# Metrics
duration: 6min
completed: 2026-04-04
---

# Phase 14 Plan 02: FastAPI /guide Mount and Dockerfile Summary

**StaticFiles mount at /guide registered before /static in app/main.py (html=True), and Dockerfile gains COPY site/ site/ — MkDocs docs reachable at /guide in dev and production**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-04T18:28:00Z
- **Completed:** 2026-04-04T18:34:00Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Added `app.mount("/guide", StaticFiles(directory="site", html=True), name="guide")` before the /static mount in app/main.py
- Added `COPY site/ site/` after existing COPY lines in Dockerfile
- Verified: GET /guide returns 200 with MkDocs HTML, CSS and JS assets under /guide/assets/ return 200
- mkdocs build --strict still passes with no regression

## Task Commits

Each task was committed atomically:

1. **Task 1: Mount site/ at /guide in FastAPI and update Dockerfile** - `1e202b6` (feat)

**Plan metadata:** (committed with SUMMARY.md and STATE.md)

## Files Created/Modified
- `app/main.py` - Added StaticFiles mount for /guide before /static mount (line 114-115)
- `Dockerfile` - Added COPY site/ site/ after existing COPY directives

## Decisions Made
- html=True on the StaticFiles mount enables automatic index.html serving — without it, `/guide` returns a directory listing or 404 instead of the MkDocs homepage
- Mount order is load-bearing: /guide before /static ensures FastAPI routes /guide requests to the docs site, not the static assets directory

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Full app dev server blocked on MongoDB lifespan startup (no DB available in dev environment). Used a minimal FastAPI test app with just the StaticFiles mount to verify HTTP 200 responses for /guide, CSS, and JS assets. Mount configuration itself was identical to what the production app uses.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- /guide endpoint fully functional and verified: index page and assets serve with 200 status
- Blocker from STATE.md (verify CSS/JS assets at /guide sub-path) is now resolved — confirmed 200 on all asset types
- Dockerfile production image ready with docs included — no MkDocs installation needed in container
- Phase 15 (MkDocs content) can proceed: serve infrastructure is in place

---
*Phase: 14-mkdocs-infrastructure*
*Completed: 2026-04-04*

## Self-Check: PASSED

- app/main.py: FOUND
- Dockerfile: FOUND
- 14-02-SUMMARY.md: FOUND
- Commit 1e202b6: FOUND
- /guide mount before /static: CONFIRMED (line 115 vs line 118)
- COPY site/ site/ in Dockerfile: CONFIRMED
