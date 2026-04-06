---
phase: 17-qso-processing-pipeline
plan: 01
subsystem: udp
tags: [asyncio, udp, adif, mongodb, beanie, pytest, mock]

requires:
  - phase: 16-udp-infrastructure
    provides: QSODatagramProtocol skeleton, start_udp_listener, UDP lifespan in main.py
  - phase: 15-qso-stamping
    provides: build_qso_dict with profile= parameter for auto-stamping
  - phase: 14-adif-import
    provides: import_qsos_from_bytes, find_duplicate, _REQUIRED_FIELDS
provides:
  - _handle_datagram coroutine — full parse-validate-build-dedup-insert UDP pipeline
  - QSODatagramProtocol with operator/user at construction, create_task dispatch
  - Lifespan User lookup for UDP operator at startup (cached, not per-datagram)
  - 8 unit tests covering all UDP pipeline scenarios
affects: [18-e2e-udp-testing, any phase that extends UDP ingest]

tech-stack:
  added: []
  patterns:
    - "Lazy imports inside coroutine body to avoid circular imports at module load"
    - "_background_tasks set pattern for strong references to in-flight asyncio Tasks"
    - "model_construct() for constructing Beanie User without DB in tests"
    - "patch app.qso.models.QSO and app.qso.service.find_duplicate as mock targets"

key-files:
  created:
    - tests/test_udp_pipeline.py
  modified:
    - app/udp/server.py
    - app/main.py

key-decisions:
  - "Lazy imports inside _handle_datagram body (matches import_qsos_from_bytes pattern) — avoids circular imports"
  - "operator attribution from config only, never from ADIF datagram OPERATOR field"
  - "build_qso_dict called with profile=user (not import_qsos_from_bytes) to enable auto-stamping"
  - "start_udp_listener uses lambda: QSODatagramProtocol(operator=..., user=...) for protocol factory"

patterns-established:
  - "UDP pipeline: parse_adi -> validate _REQUIRED_FIELDS -> build_qso_dict(profile=user) -> find_duplicate -> QSO.insert"
  - "Exception containment: entire _handle_datagram body wrapped in try/except Exception to prevent task crashes"
  - "operator=None guard: discard datagram immediately with WARNING log, never attempt processing"

duration: 20min
completed: 2026-04-06
---

# Phase 17 Plan 01: QSO Processing Pipeline Summary

**Full UDP QSO processing pipeline: ADIF parse, field validation, profile auto-stamping via build_qso_dict(profile=user), duplicate detection, and MongoDB insert with operator attribution from config**

## Performance

- **Duration:** 20 min
- **Started:** 2026-04-06T18:14:11Z
- **Completed:** 2026-04-06T18:34:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Implemented `_handle_datagram` coroutine with complete parse-validate-build-dedup-insert pipeline in `app/udp/server.py`
- Updated `QSODatagramProtocol` to accept `operator` and `user` at construction and dispatch via `create_task` with `_background_tasks` strong reference pattern
- Wired `app/main.py` lifespan to fetch the operator `User` document once at startup (after `_bootstrap_admin`), normalise callsign to uppercase, and pass both to `start_udp_listener`
- Created 8 unit tests covering all scenarios: successful insert, profile auto-stamping, missing field rejection, duplicate detection, operator isolation from datagram content, no operator configured, empty datagram, and exception containment

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement _handle_datagram and wire into QSODatagramProtocol** - `50f1c45` (feat)
2. **Task 2: Wire operator User lookup into lifespan startup** - `39d62a5` (feat)
3. **Task 3: Create unit tests for _handle_datagram** - `19d1c75` (test)

## Files Created/Modified

- `app/udp/server.py` - Added `_handle_datagram` coroutine, updated `QSODatagramProtocol.__init__` to accept operator/user, updated `datagram_received` to dispatch via `create_task`, updated `start_udp_listener` signature with operator/user kwargs
- `app/main.py` - Replaced bare UDP startup block with User lookup, callsign uppercase normalisation, and keyword args to `start_udp_listener`
- `tests/test_udp_pipeline.py` - 8 async pytest tests for `_handle_datagram`, all mocked (no MongoDB required)

## Decisions Made

- Lazy imports inside `_handle_datagram` body (matches `import_qsos_from_bytes` pattern) to avoid circular imports at module load time
- Operator attribution comes from config `UDP_OPERATOR` only — ADIF datagram `OPERATOR` field is overwritten by profile auto-stamping; never used for `operator_callsign`
- `build_qso_dict(record, operator, profile=user)` used directly (not `import_qsos_from_bytes`) because `import_qsos_from_bytes` omits the `profile=` parameter
- `start_udp_listener` uses `lambda: QSODatagramProtocol(operator=operator, user=user)` factory so asyncio can construct fresh protocol instances correctly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Full UDP QSO ingestion pipeline is complete and tested
- UDP-inserted QSOs use identical code path to REST API QSOs (same `build_qso_dict` + `find_duplicate` + `QSO.insert`)
- Profile auto-stamping works identically for UDP and REST paths
- Ready for Phase 18: end-to-end UDP integration testing with live MongoDB

---
*Phase: 17-qso-processing-pipeline*
*Completed: 2026-04-06*
