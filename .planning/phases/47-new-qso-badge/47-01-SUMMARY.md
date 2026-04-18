---
phase: 47-new-qso-badge
plan: 01
subsystem: ui
tags: [htmx, sse, tailwind, javascript, live-feed]

requires: []
provides:
  - Indigo pill badge above log table showing count of new QSOs arrived while on page 2+ or filtered view
  - Click-to-dismiss and auto-dismiss badge behavior via htmx:afterSettle
  - SSE-swap-safe DOM placement (sibling of #log-table, not child)
affects: []

tech-stack:
  added: []
  patterns:
    - "DOM sibling placement for SSE-swap-safe persistent UI elements"
    - "classList.remove('hidden') before classList.add('flex') to override Tailwind's !important"
    - "htmx:afterSettle for post-swap auto-dismiss logic"

key-files:
  created: []
  modified:
    - templates/log/log.html
    - static/css/output.css

key-decisions:
  - "Badge placed as DOM sibling immediately before #log-table (not child) so HTMX SSE innerHTML swaps cannot destroy it"
  - "Badge increment block fires BEFORE the auto-refresh-ok return guard so both paths (increment vs auto-refresh) are correctly gated"
  - "htmx:afterSettle used for auto-dismiss (no target guard needed — auto-refresh-ok presence always means page 1, no filters)"

patterns-established:
  - "SSE-safe persistent UI: place elements as siblings of the SSE swap target, never as children"
  - "Tailwind hidden override: always remove 'hidden' before adding 'flex' (hidden compiles to display:none !important)"

requirements-completed:
  - LIVE-03
  - LIVE-04

duration: 20min
completed: 2026-04-18
---

# Phase 47: new-qso-badge Summary

**Indigo pill badge above log table that counts and dismisses new SSE QSOs when operator is on page 2+ or filtered view**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-18
- **Completed:** 2026-04-18
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 2

## Accomplishments
- Badge HTML element (`#new-qso-badge`) inserted as DOM sibling immediately before `#log-table` — survives all HTMX SSE innerHTML swaps
- IIFE JS additions: `newQsoCount` counter, `updateBadge()`/`dismissBadge()` helpers, click listener, badge increment in `htmx:sseMessage`, auto-dismiss in `htmx:afterSettle`
- Singular/plural text correct: "1 new QSO" vs "N new QSOs"
- Human verification passed: badge appears on page 2+, increments, click-dismisses, auto-dismisses on page-1 navigation
- Tailwind build and verify pass; Docker rebuild required to pick up template changes

## Task Commits

1. **Task 1: Add badge HTML and IIFE JS logic** — `7339459` (feat)
2. **Task 2: Human verify** — approved by user

## Files Created/Modified
- [templates/log/log.html](../../../templates/log/log.html) — Badge HTML sibling div, var declarations, updateBadge/dismissBadge functions, click listener, sseMessage increment hook, afterSettle auto-dismiss listener
- `static/css/output.css` — Rebuilt with indigo dark mode classes

## Decisions Made
- Badge is a DOM sibling of `#log-table` (not a child) per D-09 and architecture decision — HTMX SSE swaps replace innerHTML, which would destroy any child element
- `classList.remove('hidden')` called before `classList.add('flex')` — Tailwind's `hidden` compiles to `display:none !important`, so order matters
- Badge increment block placed before the `return` guard in `htmx:sseMessage` so both paths (badge increment for page 2+, auto-refresh for page 1) are correctly sequenced

## Deviations from Plan
None — plan executed exactly as written.

## Issues Encountered
- Docker templates are baked into image (not volume-mounted), so `docker-compose up -d --build` was required to see changes in the running app. Communicated to user during checkpoint.
- `uv run pytest tests/` fails with MongoDB hostname resolution error (`mongodb:27017`) — pre-existing issue unrelated to this phase (confirmed by testing before/after with git stash).

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Badge feature complete and human-verified
- No blockers for next phase

---
*Phase: 47-new-qso-badge*
*Completed: 2026-04-18*
