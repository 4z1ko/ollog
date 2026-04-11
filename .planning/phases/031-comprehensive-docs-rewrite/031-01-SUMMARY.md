---
phase: 031-comprehensive-docs-rewrite
plan: 01
subsystem: docs
tags: [mkdocs, swagger-ui, adif, documentation, fastapi]

requires:
  - phase: 029-admin-isolation
    provides: admin container on port 8001, admin_token cookie, admin_main.py
  - phase: 030-database-backup
    provides: backup CLI, BACKUP_SCHEDULE, S3 upload, app.backup module
  - phase: 027-api-tokens
    provides: API token creation/revocation, X-API-Key header, APP_OLLOG_TOKEN ADIF field

provides:
  - 2-level grouped nav with 6 sections covering all v1.0–v1.8 features
  - Interactive Swagger UI embedded at /guide/api-reference/interactive/ via mkdocs-swagger-ui-tag
  - admin-container.md, backup.md, api-tokens.md (new pages for v1.7/v1.8 features)
  - docs/openapi.json exported from FastAPI and committed
  - site/ built with mkdocs build --strict (exit 0)
  - html=True annotation in app/main.py explaining load-bearing flag

affects: [deployment, operator-onboarding, admin-onboarding]

tech-stack:
  added: [mkdocs-swagger-ui-tag>=0.8.0]
  patterns: [not_in_nav suppression for static assets not in nav, swagger-ui-tag for embedded API reference without CDN]

key-files:
  created:
    - docs/getting-started/index.md
    - docs/getting-started/quickstart.md
    - docs/getting-started/first-qso.md
    - docs/operator-guide/index.md
    - docs/operator-guide/logging-qsos.md
    - docs/operator-guide/adif-import-export.md
    - docs/operator-guide/api-tokens.md
    - docs/operator-guide/profile.md
    - docs/operator-guide/udp-adif.md
    - docs/admin-guide/index.md
    - docs/admin-guide/deployment.md
    - docs/admin-guide/admin-container.md
    - docs/admin-guide/account-management.md
    - docs/admin-guide/backup.md
    - docs/api-reference/index.md
    - docs/api-reference/interactive.md
    - docs/reference/index.md
    - docs/reference/adif-field-reference.md
    - docs/reference/environment-variables.md
    - docs/troubleshooting/index.md
    - docs/openapi.json
  modified:
    - mkdocs.yml
    - pyproject.toml
    - app/main.py
    - docs/index.md

key-decisions:
  - "mkdocs-swagger-ui-tag serves Swagger UI assets from /guide static files — no CDN requests"
  - "not_in_nav used to suppress openapi.json from MkDocs nav warning"
  - "navigation.expand only — do NOT combine navigation.indexes + navigation.sections (MkDocs Material issue #3070)"
  - "html=True on StaticFiles is load-bearing for use_directory_urls:true — annotated with comment in app/main.py"
  - "APP_OLLOG_TOKEN is an ADIF field name (not env var) — documented in udp-adif.md and api-tokens.md"
  - "Old flat docs retained on disk but removed from nav — mkdocs does not build them"

patterns-established:
  - "Interactive API reference: export openapi.json before mkdocs build, use swagger-ui-tag with src=../openapi.json"
  - "2-level nav: section name with index.md as first entry, child pages follow"

duration: 27min
completed: 2026-04-11
---

# Phase 031 Plan 01: Comprehensive Docs Rewrite Summary

**25 markdown files across 6 nav sections covering all v1.0–v1.8 features, with embedded Swagger UI via mkdocs-swagger-ui-tag and mkdocs build --strict exit 0**

## Performance

- **Duration:** ~27 min
- **Started:** 2026-04-11T11:07:15Z
- **Completed:** 2026-04-11T11:34:00Z
- **Tasks:** 4
- **Files modified:** 27

## Accomplishments

- Rewrote flat 7-page docs into 2-level grouped 6-section site (Getting Started, Operator Guide, Admin Guide, API Reference, Reference, Troubleshooting)
- Added 3 wholly-new pages: admin-container.md, backup.md, api-tokens.md — covering all v1.7/v1.8 features absent from previous docs
- Embedded interactive Swagger UI at /guide/api-reference/interactive/ using mkdocs-swagger-ui-tag with all assets bundled (no CDN requests)
- Fixed JWT_EXPIRE_MINUTES default from 60 to 480 throughout all docs
- Added API_TOKEN_SECRET and backup env vars to deployment and environment-variables docs
- Annotated html=True as load-bearing in app/main.py

## Task Commits

1. **Task 1: Infrastructure** - `8bb03a5` (chore)
2. **Task 2: Content migration** - `ef6d81e` (feat)
3. **Task 3: New content** - `e43c30c` (feat)
4. **Task 4: Export, build, commit site/** - `4e747ad` (docs)

## Files Created/Modified

- `mkdocs.yml` — replaced flat nav with 6-section 2-level grouped nav, added swagger-ui-tag plugin and not_in_nav
- `pyproject.toml` — added mkdocs-swagger-ui-tag>=0.8.0 to dev dependency group
- `app/main.py` — added html=True load-bearing comment above StaticFiles mount
- `docs/index.md` — updated quick links and feature list with v1.7/v1.8 mentions
- `docs/getting-started/` — 3 files: index.md, quickstart.md (JWT default fixed), first-qso.md
- `docs/operator-guide/` — 6 files: index.md, logging-qsos.md, adif-import-export.md, api-tokens.md, profile.md, udp-adif.md
- `docs/admin-guide/` — 5 files: index.md, deployment.md (new env vars added), admin-container.md, account-management.md, backup.md
- `docs/api-reference/` — 2 files: index.md, interactive.md (swagger-ui-tag embed)
- `docs/reference/` — 3 files: index.md, adif-field-reference.md, environment-variables.md
- `docs/troubleshooting/` — 1 file: index.md (links updated)
- `docs/openapi.json` — exported from FastAPI app (16 endpoint operations)
- `site/` — built output committed

## Decisions Made

- Used `mkdocs-swagger-ui-tag` (not `mkdocs-render-swagger-plugin`) — bundles all Swagger UI assets, no CDN dependency
- `not_in_nav: | openapi.json` — suppresses MkDocs warning about openapi.json being in docs/ but not in nav
- `navigation.expand` only — not `navigation.indexes + navigation.sections` (avoids MkDocs Material issue #3070)
- Old flat docs (deployment.md, getting-started.md, etc.) kept on disk but removed from nav — mkdocs INFO message (not warning) about unlisted pages is acceptable
- `APP_OLLOG_TOKEN` explicitly documented as an ADIF field name in both udp-adif.md and api-tokens.md — with "not an environment variable" callout

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] openapi.json path count below plan threshold**
- **Found during:** Task 4 verification
- **Issue:** Plan expected `len(d['paths']) >= 19` but the operator app has 11 unique paths (16 operations). The admin endpoints are in `app/admin_main.py` (a separate FastAPI app) and are intentionally not included in the operator app's OpenAPI schema.
- **Fix:** Proceeded without change — the actual path count (11) is correct. The plan's ">=19" threshold was written assuming admin endpoints would be included, but they are architecturally separate. The 16 operations across 11 paths correctly represent the operator API.
- **Impact:** Verification threshold not met numerically, but the schema is correct and complete for the operator app.

---

**Total deviations:** 1 (documentation discrepancy, no code change required)
**Impact on plan:** Operator API schema is correct. The numeric threshold in the plan was based on an incorrect assumption about which endpoints would be exported.

## Issues Encountered

The MkDocs Material warning box about MkDocs 2.0 appears in the build output as colored terminal output but does not affect the build. It is a vendored warning from the Material theme, not a build warning — exit code remains 0.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- All v1.0–v1.8 features are documented and reachable from /guide in at most two nav clicks
- site/ is committed and ready to be included in the Docker image
- v1.8 milestone complete (Phases 29, 30, 31 all done)

## Self-Check: PASSED

All key files found on disk. All 4 task commits verified in git log.

---
*Phase: 031-comprehensive-docs-rewrite*
*Completed: 2026-04-11*
