---
phase: 041-multi-operator-udp-routing
plan: 01
subsystem: udp
tags: [udp, operator-cache, adif, routing, multi-operator]

# Dependency graph
requires:
  - phase: 040-restore-ui
    provides: admin ui with user create/toggle that now triggers cache invalidation
  - phase: udp-token-cache-precedent
    provides: token_cache.py pattern (load/resolve/notify_refresh singleton)
provides:
  - In-memory callsign-to-User cache with dirty-flag lazy reload (app/udp/operator_cache.py)
  - OPERATOR-field routing in _handle_datagram with unknown-callsign drop and no-operator guard
  - operator_cache.load() at startup inside udp_enabled block
  - operator_cache.notify_refresh() after all operator mutation endpoints
affects: [udp, admin, startup, multi-operator-routing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "UDPOperatorCache mirrors UDPTokenCache: load()/resolve()/notify_refresh() dirty-flag singleton"
    - "Lazy import of operator_cache inside _handle_datagram to avoid circular imports"
    - "record.pop() for OPERATOR field — same pattern as APP_OLLOG_TOKEN — field must not reach QSO doc"
    - "notify_refresh() is synchronous (sets _dirty=True); reload is lazy on next resolve()"

key-files:
  created:
    - app/udp/operator_cache.py
  modified:
    - app/udp/server.py
    - app/main.py
    - app/admin/router.py
    - app/admin/ui_router.py

key-decisions:
  - "OPERATOR field routing inserted after APP_OLLOG_TOKEN block, before missing-fields check — ensures APP_OLLOG_TOKEN always wins if both present"
  - "Stale early UDP_OPERATOR guard removed and replaced with post-resolution guard covering both no-UDP_OPERATOR and unknown-OPERATOR cases"
  - "notify_refresh() excluded from reset_password endpoints — password changes have no routing impact"
  - "operator_cache import at top-level in admin routers (not lazy) — no circular import risk from admin layer"

patterns-established:
  - "New UDP routing stage pattern: pop field → resolve via cache → drop+WARN if not found → set operator/user"
  - "Admin mutation hook pattern: await mutation, then synchronous notify_refresh() before return"

# Metrics
duration: 2min
completed: 2026-04-15
---

# Phase 041 Plan 01: Multi-Operator UDP Routing — Operator Cache and Routing Summary

**In-memory UDPOperatorCache with dirty-flag lazy reload routes OPERATOR-field datagrams to per-operator QSO logs with O(1) callsign resolution and zero per-datagram DB queries**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-15T09:16:57Z
- **Completed:** 2026-04-15T09:19:15Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Created app/udp/operator_cache.py: UDPOperatorCache class with load(), resolve(), notify_refresh() and module-level singleton, mirroring token_cache.py pattern exactly
- Modified _handle_datagram in server.py to pop OPERATOR field after APP_OLLOG_TOKEN block, resolve via operator_cache, drop unknown callsigns with WARNING, and guard no-operator-configured after both resolution paths; removed stale early UDP_OPERATOR guard
- Wired operator_cache.load() at startup in main.py udp_enabled block alongside token_cache.load(); added notify_refresh() hooks in admin/router.py (create_user, set_user_enabled) and admin/ui_router.py (create_user, toggle_user)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create operator_cache.py and wire OPERATOR routing into _handle_datagram** - `1cab4f4` (feat)
2. **Task 2: Wire startup loading and admin router notify_refresh hooks** - `fe6f3b0` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `app/udp/operator_cache.py` - In-memory callsign-to-User cache with dirty-flag lazy reload; UDPOperatorCache class with load(), resolve(), notify_refresh(); module-level singleton
- `app/udp/server.py` - _handle_datagram now pops OPERATOR field, resolves via operator_cache, drops unknown-operator datagrams with WARNING; stale early guard removed and replaced with post-resolution no-operator guard
- `app/main.py` - operator_cache import and await operator_cache.load() added to udp_enabled block after token_cache.load()
- `app/admin/router.py` - top-level operator_cache import; notify_refresh() after create_user insert and set_user_enabled set (2 sites)
- `app/admin/ui_router.py` - top-level operator_cache import; notify_refresh() after create_user insert and toggle_user set (2 sites)

## Decisions Made
- OPERATOR field routing is inserted between the APP_OLLOG_TOKEN block and the missing-fields check — APP_OLLOG_TOKEN always wins when both fields are present, because token routing runs first and sets operator/user before OPERATOR routing runs
- The stale early `if operator is None` guard (before parsing, line 42-45) was removed and replaced with a post-resolution guard that covers both the UDP-05 fallback case and the UDP-06 no-operator-configured drop
- notify_refresh() is excluded from reset_password endpoints in both admin routers — password changes have no effect on callsign or enabled status, so no cache invalidation is needed
- operator_cache is imported at top-level in admin/router.py and admin/ui_router.py (not lazy) — no circular import risk from the admin layer to the udp module

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Requirements UDP-01 through UDP-06 are fully implemented
- Multi-operator UDP routing is live: any enabled operator can receive QSOs by including their callsign in OPERATOR ADIF field
- operator_cache invalidation is wired to all operator mutation endpoints (create, enable/disable via both API and UI routers)
- Documentation phase (deployment.md update explaining UDP_OPERATOR as optional fallback and multi-operator routing) is the next planned deliverable

---
*Phase: 041-multi-operator-udp-routing*
*Completed: 2026-04-15*

## Self-Check: PASSED

- FOUND: app/udp/operator_cache.py
- FOUND: app/udp/server.py
- FOUND: app/main.py
- FOUND: app/admin/router.py
- FOUND: app/admin/ui_router.py
- FOUND: .planning/phases/041-multi-operator-udp-routing/041-01-SUMMARY.md
- COMMIT 1cab4f4: verified
- COMMIT fe6f3b0: verified
