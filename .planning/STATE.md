# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04 after v1.1 roadmap)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** Phase 8 — Profile Service Schemas and API Router (v1.1)

## Current Position

Phase: 8 of 10 (Profile Service Schemas and API Router)
Plan: 1 of 2 in current phase — plan 01 complete
Status: In progress
Last activity: 2026-04-04 — 08-01 complete (profile schemas and my_antenna field rename)

Progress: [██████░░░░] ~62% (v1.0 complete; v1.1 phase 07 done)

## Performance Metrics

**v1.0 Velocity:**
- Total plans completed: 19
- Average duration: ~7.5 min/plan
- Total execution time: ~2.4 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 4/4 | ~40 min | ~10 min |
| 02-admin-accounts | 2/2 | ~19 min | ~9.5 min |
| 03-qso-entry-log-view | 4/4 | ~27 min | ~6.8 min |
| 04-adif-import-export | 4/4 | ~34 min | ~8.5 min |
| 05-multi-operator-live-feed | 4/4 | ~37 min | ~9.3 min |
| 06-navigation-fix | 1/1 | ~2 min | ~2 min |

*v1.1 metrics will accumulate as phases complete*

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 07-01 | 1/1 | ~4 min | ~4 min |
| 07-02 | 1/1 | ~3 min | ~3 min |
| 08-01 | 1/1 | ~3 min | ~3 min |

## Accumulated Context

### Key Decisions (summary — full log in PROJECT.md)

- Profile fields embedded in existing User Beanie document — no separate collection, no migration (confirmed implemented 07-01)
- maidenhead>=1.8.0 + pydantic[email]>=2.0 are the only new dependencies (installed 07-01)
- No validators or computed fields in User model — grid-to-latlon conversion deferred to service layer in Phase 8
- center=True required for maidenhead.to_location() — SW corner default causes up to 80 km error (confirmed implemented 07-02)
- grid_to_latlon pre-validates character classes (pos 0-1 letters, 2-3 digits, 4-5 letters) to catch "99AA" explicitly
- Profile GET/PATCH derives operator from JWT only — no callsign in query params or body
- STATION_CALLSIGN omitted entirely (not empty string) when blank — prevents LoTW/POTA upload failures
- ADIF import path explicitly excluded from auto-stamping — historical records preserved as-is
- MY_ANTENNA confirmed as ADIF 3.1.6 field name — my_ant renamed to my_antenna in User model at 08-01 (no migration needed, field was Optional with no production data)
- MY_GRIDSQUARE_RE accepts 4-char and 6-char Maidenhead only — regex r"^[A-Ra-r]{2}[0-9]{2}([A-Xa-x]{2})?$"
- latitude/longitude excluded from ProfileUpdateRequest — derived by service layer from my_gridsquare, not user-supplied
- station_callsign empty-string-to-None normalization at schema layer — service and DB never see blank strings

### Research Flags for Planning

- Phase 10: Verify ADIF MY_LAT/MY_LON XDDD MM.MMM export format before writing conversion utility

### Known Tech Debt (from v1.0)

- QSO.find_active() in models.py — dead production code
- from_mongo_dt() in utils.py — tested, not called in production
- Docker end-to-end verification pending

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-04
Stopped at: Completed 08-01-PLAN.md (profile schemas and my_antenna field rename)
Resume file: None
