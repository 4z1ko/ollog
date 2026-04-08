---
phase: 23-sse-triggered-log-table-reload
plan: 01
subsystem: ui
tags: [htmx, sse, server-sent-events, jinja2, log-table, live-refresh]

# Dependency graph
requires:
  - phase: 16-udp-infrastructure
    provides: /feed/station SSE endpoint that broadcasts new_qso events
  - phase: 22-log-view
    provides: /log/view partial endpoint and #log-table htmx target
provides:
  - SSE-triggered live refresh of log table on new QSO (form, UDP, or API)
  - Server-side auto-refresh guard in log_table.html (page 1, default sort, no filters)
  - Client-side guards (no refresh during edit, no refresh on page 2+/filters/non-default sort)
  - Live/Offline indicator in nav bar reflecting SSE connection state
affects: [24-phase, any phase modifying log.html or log_table.html]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SSE event listener pattern: htmx:sseMessage with manual guard checks via getElementById/querySelector instead of hx-trigger=sse:[event] filter (reliability over brevity)"
    - "Server-side guard marker: hidden span in partial template rendered conditionally controls client behavior without JS state"

key-files:
  created: []
  modified:
    - templates/log/log_table.html
    - templates/log/log.html

key-decisions:
  - "Use htmx:sseMessage JS listener instead of hx-trigger=sse:new_qso [condition] because JS filter evaluation on SSE hx-trigger had only medium research confidence"
  - "Place hx-ext=sse and sse-connect on #log-table (not inside log_table.html partial) so SSE connection survives every htmx innerHTML swap on the target"
  - "Use #auto-refresh-ok hidden span as server-side truth: server renders it only at page 1 + default sort + no filters; marker disappears on any navigation away from that state"

patterns-established:
  - "Server-side guard marker: render a hidden element conditionally in a partial; client JS checks for its presence to decide behavior"
  - "SSE on swap target: place hx-ext/sse-connect on the outer container div, not inside the swapped innerHTML"

# Metrics
duration: 3min
completed: 2026-04-08
---

# Phase 23 Plan 01: SSE-Triggered Log Table Reload Summary

**SSE live refresh wired to #log-table via htmx:sseMessage listener with server-side (auto-refresh-ok marker) and client-side (edit row, pagination/filter/sort) guards and a LIVE/OFFLINE nav indicator**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-08T15:28:06Z
- **Completed:** 2026-04-08T15:31:12Z
- **Tasks:** 1 of 2 (paused at human-verify checkpoint)
- **Files modified:** 2

## Accomplishments
- Wired /feed/station SSE endpoint to log table: new QSOs appear automatically on default view
- Added server-side auto-refresh guard: `#auto-refresh-ok` span rendered only on page 1, sort=`-qso_date_utc`, and no active filters
- Added client-side guards: skip refresh during inline edit (`#log-table input` selector), plus the server-side marker handles pagination/filter/sort suppression
- Added LIVE/OFFLINE indicator in nav bar using htmx:sseOpen/sseError/sseClose event listeners

## Task Commits

Each task was committed atomically:

1. **Task 1: Add server-side guard marker and SSE wiring to templates** - `56b6a8e` (feat)

_Task 2 is a human-verify checkpoint — awaiting operator verification._

## Files Created/Modified
- `templates/log/log_table.html` — Added conditional `#auto-refresh-ok` hidden span at top of file
- `templates/log/log.html` — Added `hx-ext="sse"` and `sse-connect="/feed/station"` on `#log-table`, added `#live-indicator` span in nav, added SSE event handler script block

## Decisions Made
- Used `htmx:sseMessage` JS listener instead of `hx-trigger="sse:new_qso [condition]"` — JS filter evaluation in htmx SSE triggers had only medium confidence from research; the listener approach is fully reliable
- Placed `hx-ext="sse"` and `sse-connect` on `#log-table` container (not inside the partial) — `#log-table` is the swap target and its attributes survive every htmx innerHTML swap
- Server-side truth via hidden span: the server evaluates guard conditions and renders `#auto-refresh-ok` only when refresh is safe; the client only needs `getElementById` to check

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Task 1 complete and committed. Template changes are live.
- User must start the app (`docker compose up`) and verify LIVE-01 through LIVE-05 behaviors manually via the checkpoint.
- After checkpoint approval, Phase 23 Plan 01 is complete and Phase 24 can begin.

---
*Phase: 23-sse-triggered-log-table-reload*
*Completed: 2026-04-08*
