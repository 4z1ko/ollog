---
phase: 20-getting-started-guide-sending-qsos-via-udp
plan: 01
subsystem: docs
tags: [udp, adif, getting-started, nc, log4om, wsjtx, n1mm, documentation]

# Dependency graph
requires:
  - phase: 19-deployment-guide-update
    provides: deployment.md with UDP_ENABLED / UDP_OPERATOR / UDP_PORT configuration
  - phase: 16-udp-infrastructure
    provides: UDP listener accepting raw ADIF text datagrams on port 2399
provides:
  - Step 8 section in docs/getting-started.md covering UDP QSO submission
  - nc one-liner for testing UDP listener
  - Log4OM direct ADIF UDP integration steps
  - WSJT-X and N1MM+ compatibility notes with ADIF file import workarounds
affects:
  - future documentation phases referencing UDP integration
  - users reading getting-started.md who want to send QSOs via UDP

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Honest compatibility docs: document menu paths for reference even when format is incompatible; explicitly state incompatibility and redirect to correct integration path"
    - "Port disambiguation: mention WSJT-X default (2237) only to contrast with ollog's port (2399), never as if it were ollog's port"

key-files:
  created: []
  modified:
    - docs/getting-started.md

key-decisions:
  - "Document WSJT-X and N1MM+ menu paths for completeness but state format incompatibility prominently and redirect to ADIF file import (Step 5)"
  - "Port 2399 used consistently throughout; 2237 mentioned only as WSJT-X default to prevent confusion"
  - "Log4OM documented as the only logging program with direct ADIF UDP compatibility"

patterns-established:
  - "Incompatibility note pattern: state format mismatch first, show menu path for reference, then provide the correct workaround"

# Metrics
duration: 2min
completed: 2026-04-08
---

# Phase 20 Plan 01: Getting Started Guide — Send QSOs via UDP Summary

**Step 8 section added to getting-started.md documenting nc one-liner, Log4OM direct ADIF UDP steps, and honest WSJT-X/N1MM+ incompatibility notes with ADIF file import workarounds**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-08T10:15:00Z
- **Completed:** 2026-04-08T10:16:27Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Inserted "## Step 8: Send QSOs via UDP" between Step 7 and Next Steps in getting-started.md
- Wrote copy-pasteable nc one-liner with port 2399, -u flag, -w1 flag, and all five required ADIF fields
- Documented Log4OM Setup > Connections numbered steps for direct ADIF UDP integration
- Documented WSJT-X incompatibility (binary-framed protocol) with WSJTX_LOG.ADI file import workaround referencing Step 5
- Documented N1MM+ incompatibility (XML format) with ADIF export/import workaround referencing Step 5
- Port 2399 used consistently; 2237 mentioned only once as "WSJT-X's default" to prevent port confusion

## Task Commits

Each task was committed atomically:

1. **Task 1: Insert Step 8 — Send QSOs via UDP into getting-started.md** - `1c70872` (feat)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified
- `docs/getting-started.md` - Added Step 8 section (67 lines inserted between Step 7 and Next Steps)

## Decisions Made
- Document WSJT-X and N1MM+ menu paths for completeness but state format incompatibility prominently and redirect to ADIF file import (Step 5). This fulfills documentation requirements while being technically accurate — neither program sends raw ADIF text over UDP.
- Port 2399 used consistently throughout all examples. WSJT-X default port 2237 mentioned once in the WSJT-X section only to explain why operators should NOT point WSJT-X at ollog's port.
- Log4OM documented as the only logging program with direct ADIF UDP compatibility, matching findings in 20-RESEARCH.md.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Step 8 section is complete and accurate; ready for any follow-up documentation phases
- If future phases add ADIF-over-UDP support for other logging programs, this section is the natural insertion point

---
*Phase: 20-getting-started-guide-sending-qsos-via-udp*
*Completed: 2026-04-08*

## Self-Check: PASSED

- docs/getting-started.md: FOUND
- 20-01-SUMMARY.md: FOUND
- Commit 1c70872: FOUND
