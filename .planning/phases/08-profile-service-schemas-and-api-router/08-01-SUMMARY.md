---
phase: 08-profile-service-schemas-and-api-router
plan: "01"
subsystem: api
tags: [pydantic, adif, maidenhead, profile, schema-validation]

requires:
  - phase: 07-profile-data-model
    provides: User Beanie document with profile fields including my_gridsquare, latitude, longitude

provides:
  - ProfileUpdateRequest Pydantic v2 schema with MY_GRIDSQUARE regex validation and station_callsign normalization
  - ProfileResponse Pydantic v2 schema with read-only callsign and derived lat/lon fields
  - User.my_ant renamed to my_antenna per ADIF 3.1.6 spec

affects:
  - 08-02 (API router uses both schemas for PATCH/GET profile endpoints)
  - 09-adif-export (my_antenna field name used in ADIF MY_ANTENNA export)

tech-stack:
  added: []
  patterns:
    - "All ProfileUpdateRequest fields Optional[...] = None — model_dump(exclude_unset=True) drives partial PATCH updates"
    - "field_validator on my_gridsquare auto-uppercases valid grids and rejects invalid character classes"
    - "station_callsign validator normalizes empty string to None to prevent LoTW/POTA blank-field failures"

key-files:
  created:
    - app/profile/schemas.py
  modified:
    - app/auth/models.py

key-decisions:
  - "my_ant renamed to my_antenna — confirmed ADIF 3.1.6 field name MY_ANTENNA; field was Optional[str]=None with no production data so no migration required"
  - "latitude and longitude excluded from ProfileUpdateRequest — derived from my_gridsquare by service layer, not user-supplied"
  - "MY_GRIDSQUARE_RE = r'^[A-Ra-r]{2}[0-9]{2}([A-Xa-x]{2})?$' — accepts 4-char and 6-char Maidenhead only; no 8-char extended locators"
  - "station_callsign empty-string-to-None normalization at schema layer — prevents upstream failures at ADIF export time"

patterns-established:
  - "Schema-layer grid validation: reject before reaching service or DB layer"
  - "ProfileResponse field names mirror User model exactly for model_validate(user.model_dump()) round-trip compatibility"

duration: 3min
completed: 2026-04-04
---

# Phase 8 Plan 01: Profile Schemas and User Model Field Rename Summary

**Pydantic v2 ProfileUpdateRequest with Maidenhead grid regex, station_callsign normalization, and ProfileResponse read-only fields; User.my_ant renamed to my_antenna per ADIF 3.1.6**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-04T17:47:18Z
- **Completed:** 2026-04-04T17:50:09Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Renamed `my_ant` to `my_antenna` in User model — ADIF 3.1.6 compliance with zero migration risk
- Created `ProfileUpdateRequest` with MY_GRIDSQUARE regex (4/6-char Maidenhead), email via EmailStr, station_callsign empty-string-to-None normalization, and exclude_unset-compatible Optional fields
- Created `ProfileResponse` with read-only `callsign` (non-optional) and derived `latitude`/`longitude` fields excluded from update request

## Task Commits

Each task was committed atomically:

1. **Task 1: Rename my_ant to my_antenna in User model** - `5d41f36` (feat)
2. **Task 2: Create ProfileUpdateRequest and ProfileResponse schemas** - `7a6f7f0` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `app/auth/models.py` - Renamed my_ant field to my_antenna with ADIF 3.1.6 comment
- `app/profile/schemas.py` - ProfileUpdateRequest and ProfileResponse Pydantic v2 models with MY_GRIDSQUARE_RE constant

## Decisions Made

- `my_ant` renamed to `my_antenna` — ADIF 3.1.6 specifies MY_ANTENNA; field was deferred in Phase 7 with explicit note to confirm at Phase 8
- `latitude` and `longitude` excluded from ProfileUpdateRequest — these are computed from my_gridsquare in the service layer (Phase 8 plan 02), not user-supplied values
- Grid regex allows 4-char and 6-char Maidenhead only — 8-char extended locators not used in amateur radio logging practice
- station_callsign normalization at schema layer — earlier normalization means service and DB layers never see blank strings

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both schemas ready for 08-02 API router: ProfileUpdateRequest for PATCH body, ProfileResponse for GET and PATCH response
- User.my_antenna field name confirmed — any references to my_ant elsewhere will need updating (search confirms none exist)
- Field name alignment between User model and schemas verified — model_validate(user.model_dump()) round-trip will work correctly

---
*Phase: 08-profile-service-schemas-and-api-router*
*Completed: 2026-04-04*
