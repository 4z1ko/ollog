---
phase: 14-mkdocs-infrastructure
plan: 01
subsystem: infra
tags: [mkdocs, mkdocs-material, documentation, static-site]

# Dependency graph
requires:
  - phase: 13-openapi-schema-cleanup
    provides: clean API schema — mkdocs adds docs layer alongside existing Swagger UI
provides:
  - mkdocs-material dev dependency in pyproject.toml
  - mkdocs.yml configured with Material theme and site_url /guide/
  - docs/index.md scaffold homepage
  - site/ directory built and committed to repo
affects: [15-mkdocs-content, Dockerfile, app/main.py]

# Tech tracking
tech-stack:
  added: [mkdocs-material==9.7.6, mkdocs==1.6.1]
  patterns: [built docs committed to repo (no CI), site_url sub-path /guide/ for correct relative asset paths]

key-files:
  created: [mkdocs.yml, docs/index.md, site/index.html, site/assets/]
  modified: [pyproject.toml, uv.lock]

key-decisions:
  - "mkdocs-material==9.* added to [dependency-groups].dev only — not in production dependencies"
  - "site_url set to http://localhost:8000/guide/ with trailing slash — prevents broken relative asset paths at sub-path"
  - "site/ committed to repo — enables Dockerfile COPY site/ without installing MkDocs in production image"
  - "site/ intentionally not in .gitignore per MKDOCS-05 design decision"

patterns-established:
  - "MkDocs build: uv run mkdocs build --strict — warnings become errors, catches missing nav files"
  - "Docs live in docs/, output in site/, no docs_dir or site_dir override needed"

# Metrics
duration: 8min
completed: 2026-04-05
---

# Phase 14 Plan 01: MkDocs Infrastructure Summary

**mkdocs-material==9.* installed as dev-only dependency with site/ built and committed to repo, ready to serve at /guide/ sub-path**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-05T15:16:00Z
- **Completed:** 2026-04-05T15:24:25Z
- **Tasks:** 2
- **Files modified:** 6 (pyproject.toml, uv.lock, mkdocs.yml, docs/index.md, site/ directory 48 files)

## Accomplishments
- mkdocs-material==9.7.6 installed as dev-only dependency (not in production deps)
- mkdocs.yml created with Material slate/indigo theme, site_url pointing to /guide/ with trailing slash
- docs/index.md scaffold homepage created
- uv run mkdocs build --strict succeeds (exit 0), site/ directory with index.html, assets/, sitemap.xml committed

## Task Commits

Each task was committed atomically:

1. **Task 1: Install mkdocs-material, create mkdocs.yml, scaffold docs/index.md** - `bc30606` (feat)
2. **Task 2: Build and commit site/ directory** - `e854a29` (feat)

**Plan metadata:** (to be committed with SUMMARY.md and STATE.md update)

## Files Created/Modified
- `pyproject.toml` - mkdocs-material==9.* added to [dependency-groups].dev
- `uv.lock` - lockfile updated with 21 new packages
- `mkdocs.yml` - MkDocs configuration: Material theme, slate palette, site_url /guide/, nav: Home
- `docs/index.md` - Scaffold homepage for docs site
- `site/index.html` - Built MkDocs homepage output
- `site/assets/` - CSS and JS from Material theme (stylesheets, javascripts, lunr search)
- `site/sitemap.xml` - Generated sitemap

## Decisions Made
- site_url ends in `/guide/` with trailing slash — without it, MkDocs generates relative asset paths that break when served at a sub-path
- site/ committed to repo rather than gitignored — Dockerfile can COPY them without installing MkDocs in production image

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Material for MkDocs team prints a warning about MkDocs 2.0 incompatibilities to stderr during build. This is informational only — build succeeded with exit 0, all output files generated correctly. Not an error.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- MkDocs build pipeline established, ready for Phase 15 content authoring
- site/ at repo root, ready for Dockerfile COPY site/ and app/main.py StaticFiles mount at /guide
- Blocker from STATE.md remains: verify CSS/JS assets load at /guide sub-path needs live test before content phase

---
*Phase: 14-mkdocs-infrastructure*
*Completed: 2026-04-05*

## Self-Check: PASSED

- pyproject.toml: FOUND
- mkdocs.yml: FOUND
- docs/index.md: FOUND
- site/index.html: FOUND
- site/assets/: FOUND
- site/sitemap.xml: FOUND
- 14-01-SUMMARY.md: FOUND
- Commit bc30606: FOUND
- Commit e854a29: FOUND
