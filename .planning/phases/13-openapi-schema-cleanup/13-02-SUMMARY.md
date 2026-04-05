---
phase: 13-openapi-schema-cleanup
plan: "02"
subsystem: api
tags: [fastapi, openapi, pydantic, adif, swagger]

# Dependency graph
requires:
  - phase: 12-country-lookup
    provides: stable codebase on which OpenAPI cleanup proceeds
provides:
  - ADIFImportReport Pydantic model with typed sub-models in app/adif/router.py
  - Annotated ADIF import endpoint (response_model=ADIFImportReport)
  - Annotated ADIF export endpoint (response_class=StreamingResponse, text/plain)
  - HTMX browser routes excluded from OpenAPI schema via include_in_schema=False
  - Feed SSE route excluded from OpenAPI schema via include_in_schema=False
affects: [phase-14-mkdocs-guide, phase-15-troubleshooting, openapi, swagger-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "include_in_schema=False on browser-only router mounts to hide from Swagger UI"
    - "response_model= on REST endpoints for typed Swagger responses"
    - "responses= parameter on StreamingResponse endpoints for content-type annotation"

key-files:
  created: []
  modified:
    - app/adif/router.py
    - app/main.py

key-decisions:
  - "ADIFRecordError.call is Optional[str] — parse errors have no call key; per-record errors do"
  - "Export endpoint uses responses= not response_model= because StreamingResponse cannot be Pydantic-validated"
  - "Feed router excluded from schema because /feed/station uses cookie auth and cannot be called from Swagger UI"

patterns-established:
  - "Browser-only routers (cookie auth, Jinja2 templates) get include_in_schema=False at mount site"
  - "REST endpoints get response_model= or responses= for typed Swagger docs"

# Metrics
duration: 2min
completed: 2026-04-05
---

# Phase 13 Plan 02: ADIF Schema Annotations and Route Exclusions Summary

**ADIFImportReport Pydantic model with typed sub-models; ADIF endpoints annotated with response types; HTMX browser routes and feed SSE excluded from /openapi.json**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-05T12:00:09Z
- **Completed:** 2026-04-05T12:02:41Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Defined ADIFImportReport model and three sub-models (ADIFRecordAccepted, ADIFRecordDuplicate, ADIFRecordError) with correct optional fields
- Annotated import endpoint with `response_model=ADIFImportReport` so Swagger shows the typed 200 response
- Annotated export endpoint with `response_class=StreamingResponse` and `responses=` for text/plain content-type display
- Added `include_in_schema=False` to admin UI, QSO UI, and feed router mounts — 12 clean API paths in /openapi.json

## Task Commits

Each task was committed atomically:

1. **Task 1: Define ADIFImportReport model and annotate ADIF endpoints** - `0aaccdc` (feat)
2. **Task 2: Exclude HTMX and feed routes from OpenAPI schema** - `d67e4f8` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `app/adif/router.py` - Added ADIFRecordAccepted, ADIFRecordDuplicate, ADIFRecordError, ADIFImportReport models; annotated import and export endpoint decorators
- `app/main.py` - Added include_in_schema=False to ui_router, qso_ui_router, and feed_router mounts

## Decisions Made

- ADIFRecordError.call is Optional[str] = None — parse_adi() errors include only record_index and error (no call key); per-record processing errors do include call. Optional field handles both shapes without two separate error models.
- Export endpoint annotated with responses= parameter rather than response_model= because StreamingResponse is not Pydantic-serializable; response_model would cause validation errors at runtime.
- Feed router excluded from schema: /feed/station uses cookie auth (get_current_operator_callsign_cookie) and cannot be exercised from Swagger UI — same rationale as the HTMX UI routers.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Tests require a running MongoDB replica set (hostname "mongodb") which is not available in the local dev environment. The 13 non-DB tests all pass; the DB-dependent tests fail on ServerSelectionTimeoutError — a pre-existing environment constraint, not caused by these changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- OpenAPI schema now has typed ADIF responses and clean browser-route exclusions (OAPI-02, OAPI-04 satisfied)
- Ready for Phase 13 Plan 03 if additional OpenAPI cleanup requirements remain, or Phase 14 (MkDocs guide)
- No blockers introduced

---
*Phase: 13-openapi-schema-cleanup*
*Completed: 2026-04-05*
