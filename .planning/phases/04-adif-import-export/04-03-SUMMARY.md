---
phase: 04-adif-import-export
plan: 03
subsystem: api
tags: [adif, export, streaming, fastapi, integration-tests]

requires:
  - phase: 04-adif-import-export
    plan: 01
    provides: serialize_adi(), ADIF serializer
  - phase: 04-adif-import-export
    plan: 02
    provides: process_import() with duplicate detection

provides:
  - GET /api/adif/export — streaming .adi file download via Bearer auth
  - GET /log/export — cookie-auth mirror of API export for UI access
  - _qso_to_adif_dict() helper — maps QSO document to ADIF field dict
  - Integration test suite: tests/test_adif_export.py (5 tests)

affects:
  - Phase 05 (live QSO feed — no changes required; ADIF pipeline complete)

tech-stack:
  added: []
  patterns:
    - StreamingResponse with async generator — yields ADIF header then one record per QSO
    - _qso_to_adif_dict() — declared fields (CALL, BAND, MODE) explicit; model_extra iterated with SKIP_FIELDS guard
    - Two export entry points: /api/adif/export (Bearer) and /log/export (cookie) share same _qso_to_adif_dict + serialize_adi logic

key-files:
  created:
    - tests/test_adif_export.py
  modified:
    - app/adif/router.py
    - app/qso/ui_router.py

key-decisions:
  - "_qso_to_adif_dict() adds declared fields explicitly (CALL, BAND, MODE) and iterates model_extra for the rest — internal fields excluded via SKIP_FIELDS set"
  - "qso_date_utc excluded from ADIF output via SKIP_FIELDS — it is an internal index field, not an ADIF-standard field (QSO_DATE + TIME_ON in model_extra serve that purpose)"
  - "/log/export uses cookie auth (get_current_operator_callsign_cookie) not a redirect — the API endpoint uses Bearer auth so a simple redirect would fail for browser users without Authorization header"
  - "StreamingResponse yields header first then one record per QSO — avoids materializing full file in memory for large logbooks"

duration: 6min
completed: 2026-04-03
---

# Phase 4 Plan 3: ADIF Export Summary

**Streaming GET /api/adif/export and /log/export endpoints that serialize the operator's non-deleted QSOs as a valid .adi file, preserving APP_ and USERDEF fields from model_extra while excluding internal fields**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-03T20:54:55Z
- **Completed:** 2026-04-03T21:01:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `_qso_to_adif_dict(qso: QSO) -> dict` helper added to `app/adif/router.py`:
  - Adds declared ADIF fields (CALL, BAND, MODE) explicitly, skipping None values
  - Iterates `model_extra` to capture QSO_DATE, TIME_ON, FREQ, RST_*, APP_*, USERDEF_*, etc.
  - Skips internal fields via `_SKIP_FIELDS = {"qso_date_utc", "_operator", "_deleted", "_id", "id", "revision_id"}`
  - All values coerced to `str` for serializer compatibility
- `GET /api/adif/export` added to ADIF router:
  - Bearer auth via `get_current_operator_callsign`
  - Query: `QSO.find({"_operator": operator, "_deleted": False}).to_list()`
  - `StreamingResponse` with async generator: yields ADIF header then `serialize_adi([_qso_to_adif_dict(qso)])` per record
  - `Content-Disposition: attachment; filename={operator}_logbook.adi`
- `GET /log/export` added to `ui_router.py`:
  - Cookie auth via `get_current_operator_callsign_cookie`
  - Identical filtering and serialization logic — only auth dependency differs
  - Separate endpoint (not a redirect) because API endpoint requires Bearer token
- `tests/test_adif_export.py` created with 5 integration tests:
  1. `test_export_three_qsos_valid_adif` — 3 QSOs (incl. APP_MYLOGGER_SCORE) → valid ADIF, all 3 records present
  2. `test_export_excludes_soft_deleted` — 2 QSOs, 1 soft-deleted → export has 1 record
  3. `test_export_operator_isolation` — QSOs for 2 operators → export as A returns only A's QSOs
  4. `test_export_excludes_qso_date_utc_field` — "qso_date_utc" string must not appear in output
  5. `test_export_app_field_preserved` — APP_CONTEST_ID survives export/parse round-trip

## Task Commits

1. **Task 1: Create ADIF export endpoint with streaming response** - `eefef66` (feat)
2. **Task 2: Add export UI link and export integration tests** - `f78be54` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `app/adif/router.py` — Added `StreamingResponse` + `serialize_adi` imports; `_SKIP_FIELDS` constant; `_qso_to_adif_dict()` helper; `GET /export` endpoint
- `app/qso/ui_router.py` — Added `_qso_to_adif_dict` + `serialize_adi` + `StreamingResponse` imports; `GET /export` route with cookie auth
- `tests/test_adif_export.py` — 5 integration tests for the export endpoint

## Decisions Made

- `_qso_to_adif_dict()` design: declared fields explicit + model_extra iteration with skip guard. This ensures CALL/BAND/MODE are always present (they're declared fields, not in model_extra on loaded documents), while all extra ADIF fields (QSO_DATE, TIME_ON, FREQ, APP_*, etc.) come through model_extra unchanged.
- `/log/export` as a standalone endpoint (not a `RedirectResponse`): browsers don't send Authorization headers on redirects, so a redirect from cookie-auth UI to Bearer-auth API would fail with 401. Duplicate logic is minimal (3 lines) — worth it for correct auth behavior.
- `qso_date_utc` in `_SKIP_FIELDS`: it is an internal computed index field; the actual ADIF date/time is stored as `QSO_DATE` and `TIME_ON` in model_extra which DO get exported.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- ADIF import/export pipeline is complete: parse, validate, deduplicate, insert (import); query, map, stream (export)
- Phase 05 (live QSO feed) can proceed
- No open issues in the ADIF subsystem

## Self-Check: PASSED

Verified files exist and commits present in git log.
