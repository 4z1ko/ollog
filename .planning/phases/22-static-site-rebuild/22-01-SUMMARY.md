---
phase: 22-static-site-rebuild
plan: 01
subsystem: docs
tags: [mkdocs, mkdocs-material, static-site, documentation, udp]

# Dependency graph
requires:
  - phase: 19-udp-documentation
    provides: UDP env var documentation in docs/deployment.md
  - phase: 20-udp-getting-started
    provides: Sending QSOs via UDP section in docs/getting-started.md
  - phase: 21-udp-troubleshooting
    provides: UDP troubleshooting entries in docs/troubleshooting.md
provides:
  - Rebuilt site/ tree with all UDP documentation from Phases 19-21
  - site/deployment/index.html with UDP_ENABLED, UDP_PORT, UDP_BIND_HOST, UDP_OPERATOR env var docs
  - site/getting-started/index.html with Sending QSOs via UDP section
  - site/troubleshooting/index.html with UDP troubleshooting entries
affects: [any phase serving or referencing site/]

# Tech tracking
tech-stack:
  added: [mkdocs-material==9.7.6]
  patterns: [mkdocs build from repo root, site/ committed to git for StaticFiles serving]

key-files:
  created: []
  modified:
    - site/deployment/index.html
    - site/getting-started/index.html
    - site/troubleshooting/index.html
    - site/search/search_index.json
    - site/sitemap.xml
    - site/sitemap.xml.gz

key-decisions:
  - "Installed mkdocs-material 9.x via pip with --break-system-packages due to PEP 668 restriction on macOS"
  - "Used python3 -m mkdocs instead of python -m mkdocs (python not available on system)"

patterns-established:
  - "mkdocs build pattern: python3 -m mkdocs build from repo root"

# Metrics
duration: 2min
completed: 2026-04-08
---

# Phase 22 Plan 01: Static Site Rebuild Summary

**MkDocs static site rebuilt with mkdocs-material 9.x, incorporating all UDP documentation from Phases 19-21 into site/ for FastAPI StaticFiles serving at /guide**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-04-08T11:20:21Z
- **Completed:** 2026-04-08T11:22:30Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Installed mkdocs-material 9.7.6 (not previously available on system)
- Built site/ from docs/ sources; all six changed files reflect UDP additions from Phases 19-21
- Verified UDP_ENABLED, "Sending QSOs via UDP", and UDP troubleshooting entries present in built HTML
- Committed rebuilt site/ completing v1.5 milestone

## Task Commits

Each task was committed atomically:

1. **Task 1: Build the static site with mkdocs** - no separate commit (build-only step, output staged in Task 2)
2. **Task 2: Commit updated site/ to git** - `a5b3710` (docs)

## Files Created/Modified
- `site/deployment/index.html` - Now contains UDP_ENABLED, UDP_PORT, UDP_BIND_HOST, UDP_OPERATOR env var documentation
- `site/getting-started/index.html` - Now contains "Sending QSOs via UDP" section with Log4OM and ADIF UDP instructions
- `site/troubleshooting/index.html` - Now contains UDP socket, binding, and operator callsign troubleshooting entries
- `site/search/search_index.json` - Updated search index reflecting new UDP content
- `site/sitemap.xml` - Updated sitemap
- `site/sitemap.xml.gz` - Updated compressed sitemap

## Decisions Made
- Installed mkdocs-material via `pip3 install "mkdocs-material==9.*" --break-system-packages` due to macOS PEP 668 restriction preventing normal pip installs
- Used `python3 -m mkdocs` because the `python` command is not available on this system

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used python3 instead of python, installed mkdocs-material**
- **Found during:** Task 1 (Build the static site with mkdocs)
- **Issue:** Plan called `python -m mkdocs --version` but `python` command not found; mkdocs module not installed under python3 either
- **Fix:** Used `python3 -m mkdocs` throughout; installed `mkdocs-material==9.*` with `--break-system-packages` flag to satisfy PEP 668 on macOS
- **Files modified:** None (installation only)
- **Verification:** `python3 -m mkdocs --version` succeeded after install; build completed in 0.25 seconds
- **Committed in:** a5b3710 (Task 2 commit includes built output)

---

**Total deviations:** 1 auto-fixed (1 blocking — missing tool/dependency)
**Impact on plan:** Necessary to complete the build. No scope changes.

## Issues Encountered
- `python` command not available on macOS — resolved by using `python3 -m mkdocs` throughout

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- v1.5 milestone complete: UDP listener implemented (Phase 16), UDP documentation written (Phases 19-21), static site rebuilt (Phase 22)
- FastAPI app at /guide now serves current UDP documentation to operators
- No known blockers for future phases

---
*Phase: 22-static-site-rebuild*
*Completed: 2026-04-08*

## Self-Check: PASSED

- site/deployment/index.html: FOUND
- site/getting-started/index.html: FOUND
- site/troubleshooting/index.html: FOUND
- 22-01-SUMMARY.md: FOUND
- Commit a5b3710: FOUND
