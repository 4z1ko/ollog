---
phase: 15-narrative-documentation-content
plan: 03
subsystem: api
tags: [adif, fastapi, rest-api, jwt, bearer-token, sse, mongodb]

# Dependency graph
requires:
  - phase: 13-openapi-schema-cleanup
    provides: finalized QSO/ADIF/admin schemas and response models
  - phase: 07-adif-import-export
    provides: ADIF import/export endpoints
  - phase: 04-admin-users
    provides: admin user management endpoints
  - phase: 05-feed-sse
    provides: SSE station feed endpoint
provides:
  - Complete API reference documenting all 16 endpoints across 6 groups
  - curl examples for every endpoint
  - Both auth flows (Bearer token + HTTP-only cookie) explained
affects: [any developer onboarding, scripting, external integrations]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ADIF field names are uppercase (CALL, BAND, MODE, QSO_DATE, TIME_ON)"
    - "QSO create uses QSOCreateRequest with extra='allow' for arbitrary ADIF fields"
    - "OPERATOR/STATION_CALLSIGN auto-stamped from JWT profile, not accepted in body"
    - "Admin reset-password uses field 'password' (not 'new_password')"
    - "SSE endpoint excluded from OpenAPI schema, uses cookie auth"

key-files:
  created:
    - docs/api-reference.md
  modified: []

key-decisions:
  - "QSO request fields are uppercase ADIF names (CALL, QSO_DATE, TIME_ON, BAND, MODE) not lowercase"
  - "GET /auth/me returns username/callsign/role (not is_admin/enabled)"
  - "GET /api/qsos/ returns paginated response with page and page_size in addition to items/total"
  - "Admin reset-password field is 'password' not 'new_password'"
  - "Feed SSE events carry HTML fragments (not JSON QSO objects) with event name 'new_qso'"
  - "ADIF import preserves file OPERATOR/STATION_CALLSIGN values (no auto-stamp)"

patterns-established:
  - "API reference split into 2 tasks: auth+QSO first half, ADIF+profile+admin+SSE second half"

# Metrics
duration: 15min
completed: 2026-04-05
---

# Phase 15 Plan 03: API Reference Summary

**Complete REST API reference for all 16 ollog endpoints with curl examples, correct field names, exact status codes, and both auth flows documented**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-05T19:00:21Z
- **Completed:** 2026-04-05T19:15:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Created `docs/api-reference.md` covering all 16 endpoints across 6 groups (Auth, QSO, ADIF, Profile, Admin, SSE)
- Documented both auth mechanisms: Bearer token (primary) and HTTP-only cookie (SSE only), with explanation of why SSE uses cookies
- Every endpoint includes method, path, auth requirement, request/response format, status codes, and a working curl example
- Corrected multiple field name discrepancies between plan draft and actual code (uppercase ADIF fields, pagination response shape, admin password field name)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write API reference — auth section and QSO endpoints** - `f5eb3a8` (feat)
2. **Task 2: Write API reference — ADIF, Profile, Admin, and SSE endpoints** - `3eaa745` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `docs/api-reference.md` - Complete API reference with all 16 endpoints, curl examples, auth flow documentation

## Decisions Made

- Documented QSO request fields as uppercase (`CALL`, `QSO_DATE`, `TIME_ON`, `BAND`, `MODE`) matching the actual `QSOCreateRequest` schema — plan draft incorrectly used lowercase
- `GET /api/qsos/` response documented with `page` and `page_size` fields from the actual `QSOListResponse` model (plan draft omitted these)
- Admin `reset-password` request field documented as `password` matching `ResetPasswordRequest.password` — plan draft used `new_password`
- SSE event `data` documented as HTML fragment (not JSON QSO object) — this is what the feed manager publishes based on `await q.get()` returning `html`
- ADIF import report documented with correct `ADIFImportReport` schema including `total_records`, `accepted`, `duplicates`, `errors` (plan draft had a simplified version)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected incorrect field names throughout plan draft**
- **Found during:** Task 1 and Task 2 (reviewing actual router and schema files)
- **Issue:** Plan draft used lowercase QSO field names (call, band, mode, qso_date, time_on), `is_admin`/`enabled` for GET /auth/me response, `new_password` for reset-password, and simplified response shapes
- **Fix:** Cross-referenced every field name against actual router/schema source files before writing documentation
- **Files modified:** docs/api-reference.md
- **Verification:** All field names match actual Pydantic models in router source
- **Committed in:** f5eb3a8, 3eaa745

---

**Total deviations:** 1 auto-fixed (Rule 1 - corrected field name discrepancies between plan draft and actual code)
**Impact on plan:** Essential for documentation accuracy. Without this correction, developers would get 422 errors using the example curl commands.

## Issues Encountered

None — router and schema files were straightforward to read. The only notable discovery was the field name discrepancies which were corrected inline.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- API reference complete; phase 15 documentation content plans can proceed
- docs/api-reference.md ready to be linked from MkDocs nav (phase 14 infrastructure already in place)
- All 16 endpoints documented with enough detail for a developer to integrate without guessing

---
*Phase: 15-narrative-documentation-content*
*Completed: 2026-04-05*

## Self-Check: PASSED

- docs/api-reference.md: FOUND
- 15-03-SUMMARY.md: FOUND
- Commit f5eb3a8: FOUND
- Commit 3eaa745: FOUND
- 16 endpoints documented: CONFIRMED
- 7 section headings (6 endpoint groups + auth intro): CONFIRMED
