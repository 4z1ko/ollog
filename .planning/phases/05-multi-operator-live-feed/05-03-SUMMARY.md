---
phase: 05-multi-operator-live-feed
plan: "03"
subsystem: api
tags: [sse, htmx, mongodb-change-stream, fastapi, jinja2]

# Dependency graph
requires:
  - phase: 05-01
    provides: MongoDB single-node replica set required for change streams
  - phase: 01-04
    provides: Cookie auth dependency (get_current_operator_callsign_cookie) used on SSE endpoint
  - phase: 03-03
    provides: QSO form page (templates/log/form.html) where Station Feed section is added
provides:
  - SSE endpoint at /feed/station with cookie authentication
  - ConnectionManager with per-client asyncio.Queue broadcast
  - watch_qsos change stream watcher started in app lifespan
  - feed_row.html partial for rendered HTML broadcast
  - Station Feed section in QSO form page (HTMX SSE extension, sse-connect, sse-swap)
affects: [future phases that build on live feed, any UI changes to form.html]

# Tech tracking
tech-stack:
  added:
    - htmx-ext-sse@2.2.4 (CDN, no build step)
    - fastapi.sse (EventSourceResponse, ServerSentEvent)
  patterns:
    - ConnectionManager with asyncio.Queue per client — queues added on connect, discarded on disconnect
    - Change stream watcher renders HTML before broadcast (no JSON on the wire, no client-side templating)
    - Lifespan-managed background task: create_task after init_db, cancel before close_db
    - SSE endpoint uses cookie auth (EventSource cannot send Authorization headers)

key-files:
  created:
    - app/feed/__init__.py
    - app/feed/manager.py
    - app/feed/router.py
    - templates/log/feed_row.html
  modified:
    - app/main.py
    - templates/base.html
    - templates/log/form.html

key-decisions:
  - "ConnectionManager broadcasts rendered HTML strings (not JSON) so browser needs no client-side template logic"
  - "SSE endpoint uses get_current_operator_callsign_cookie (not Bearer) because EventSource API cannot set headers"
  - "Change stream watcher reconnects on PyMongoError with 1s backoff; CancelledError breaks cleanly"
  - "watch_qsos watcher started after init_db() and cancelled before close_db() to prevent use of closed connection"
  - "feed_row.html uses flat context dict keys (call, band, operator) not model attribute paths — rendered outside request context via get_template().render()"

patterns-established:
  - "SSE pattern: hx-ext=sse on container, sse-connect=URL on container, sse-swap=event-name on target tbody, hx-swap=afterbegin for prepend"
  - "Lifespan background task pattern: watcher_task = asyncio.create_task(...) then cancel/await in shutdown block"

# Metrics
duration: ~15min
completed: 2026-04-04
---

# Phase 5 Plan 3: Live Station Feed Summary

**SSE-based real-time QSO feed using MongoDB change streams, asyncio.Queue broadcast, and HTMX SSE extension — new QSOs appear across all operator tabs without page refresh**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-04
- **Completed:** 2026-04-04
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 7

## Accomplishments
- Feed module (ConnectionManager + change stream watcher + SSE endpoint) implemented in app/feed/
- Change stream watcher started in app lifespan, cleanly cancelled on shutdown
- HTMX SSE extension wired into base.html and QSO form page; new QSO rows prepended to Station Feed table in real-time
- Human end-to-end verification completed and approved

## Task Commits

Each task was committed atomically:

1. **Task 1: ConnectionManager, change stream watcher, and SSE endpoint** - `a2a3d63` (feat)
2. **Task 2: HTMX SSE integration in QSO form page** - `bef0a4c` (feat)
3. **Task 3: Verify live feed end-to-end** - human-verify checkpoint (approved by user, no code commit)

**Plan metadata:** (docs commit added at plan close)

## Files Created/Modified
- `app/feed/__init__.py` - Feed package init (empty)
- `app/feed/manager.py` - ConnectionManager with asyncio.Queue broadcast; watch_qsos change stream watcher
- `app/feed/router.py` - SSE endpoint at /feed/station with cookie authentication
- `app/main.py` - Lifespan updated with watcher task start/cancel; feed router registered
- `templates/log/feed_row.html` - QSO feed row partial rendered by watcher before broadcast
- `templates/base.html` - htmx-ext-sse@2.2.4 script tag added
- `templates/log/form.html` - Station Feed section with SSE subscription (sse-connect, sse-swap, hx-swap=afterbegin)

## Decisions Made
- Broadcast rendered HTML strings (not JSON) — no client-side templating needed, simpler HTMX sse-swap wiring
- Cookie auth on SSE endpoint — EventSource API cannot set custom headers (no Authorization support in browsers)
- Change stream watcher reconnects on PyMongoError with 1s backoff; CancelledError exits loop cleanly
- Jinja2 `get_template().render(ctx)` used in watcher (not TemplateResponse) because no Request object is in scope

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Live station feed is fully operational; ready for phase 05-04 (final integration or phase wrap-up)
- All multi-operator requirements are now implemented: operator isolation (05-02) + concurrent write safety (05-01) + real-time shared feed (05-03)

---
*Phase: 05-multi-operator-live-feed*
*Completed: 2026-04-04*
