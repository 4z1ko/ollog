---
phase: 033-design-tokens-and-css-component-system
plan: 01
subsystem: ui
tags: [tailwind, css, design-tokens, apple-hig, system-fonts]

# Dependency graph
requires:
  - phase: 032-theme-infrastructure-and-build-discipline
    provides: Tailwind build pipeline, darkMode class config, FOUC suppression IIFE
provides:
  - canvas.light (#f2f2f7) and canvas.dark (#0f0f0f) color tokens in tailwind.config.js
  - surface.light (#ffffff) and surface.dark (#1c1c1e) color tokens in tailwind.config.js
  - boxShadow.card two-layer subtle shadow token in tailwind.config.js
  - -apple-system system font stack (Inter removed) in tailwind.config.js and input.css
  - .card component using bg-surface-light/dark and shadow-card
  - .table-wrap component using shadow-card dark:shadow-none
  - .card-title with stronger text colors, no uppercase/tracking-wider
  - All four badge classes using rounded-md instead of rounded-full
  - base.html free of Google Fonts CDN requests
affects: [034-admin-templates, 035-login-pages, 036-log-views]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Token-first: define in tailwind.config.js, consume via @apply in input.css, templates consume output.css
    - System font stack: OS-native fonts eliminate CDN round-trips and match platform UI conventions
    - Two-layer shadow: subtle depth without visual heaviness (Apple HIG)

key-files:
  created: []
  modified:
    - tailwind.config.js
    - static/css/input.css
    - templates/base.html

key-decisions:
  - "canvas and surface tokens defined in tailwind.config.js extend.colors (not theme root) so sidebar block is preserved"
  - "boxShadow.card uses two-layer RGBA to mimic Apple card elevation subtlety"
  - "Inter fully removed from both tailwind.config.js and input.css @layer base — system stack leads with -apple-system"
  - "badge rounded-full changed to rounded-md across all four badge classes — squircle pill matches Apple HIG"
  - "card-title loses uppercase/tracking-wider — normalised to sentence case with stronger contrast colors"

patterns-established:
  - "Token consumption: bg-surface-light dark:bg-surface-dark pattern for card backgrounds"
  - "Shadow pattern: shadow-card dark:shadow-none — shadow removed in dark mode to avoid halo effect"

# Metrics
duration: 14min
completed: 2026-04-12
---

# Phase 33 Plan 01: Design Tokens and CSS Component System Summary

**Apple HIG design tokens (canvas/surface/shadow) wired into tailwind.config.js and component classes — Inter replaced with -apple-system stack, Google Fonts CDN eliminated**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-12T09:21:49Z
- **Completed:** 2026-04-12T09:35:49Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Added canvas, surface, and boxShadow.card tokens to tailwind.config.js (preserving sidebar block)
- Updated .card and .table-wrap to consume surface tokens and shadow-card; updated .card-title style
- Changed all four badge classes from rounded-full to rounded-md for Apple HIG conformance
- Removed Inter from both config and CSS; system font stack now leads with -apple-system
- Removed three Google Fonts CDN link tags from base.html — zero external font requests

## Task Commits

Each task was committed atomically:

1. **Task 1: Add design tokens to tailwind.config.js and remove Inter from font stack** - `bda6e61` (feat)
2. **Task 2: Update input.css component classes and html base font rule** - `4fa0340` (feat)
3. **Task 3: Remove Google Fonts CDN links from base.html** - `47642ba` (feat)

## Files Created/Modified
- `tailwind.config.js` - Added canvas, surface, boxShadow.card tokens; replaced Inter font stack
- `static/css/input.css` - Updated .card, .table-wrap, .card-title, all badge classes; replaced font-family
- `templates/base.html` - Deleted three Google Fonts preconnect/stylesheet link tags

## Decisions Made
- canvas and surface tokens added alongside existing sidebar block in `extend.colors` — sidebar block preserved unchanged
- boxShadow.card uses two-layer RGBA for Apple-caliber subtle elevation
- `dark:shadow-none` on .card and .table-wrap — shadow removed in dark mode to avoid halo artifact on dark backgrounds
- .card-title loses uppercase + tracking-wider: normalised to sentence case with text-gray-700/200 for better contrast
- badge rounded-md chosen over rounded-full — matches Apple pill button convention for status indicators

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Verification script for `output.css` checked for hex strings (`1c1c1e`, `f2f2f7`) but Tailwind emits RGB notation (`28 28 30`). Tokens confirmed present via Python parse — not a real failure.
- Badge verify script false positive: minified output.css is a single line; `grep 'badge-' | grep -q 'rounded-full'` matched `rounded-full` from unrelated template classes on same line. Confirmed all badge classes emit `border-radius:.375rem` (rounded-md), not `9999px` (rounded-full).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- All design tokens are in place and verified in output.css
- Templates in Phase 34 (admin) and Phase 35 (login) can immediately use bg-canvas-light/dark, bg-surface-light/dark, shadow-card
- Phase 36 (log views) inherits all tokens without additional config work
- No blockers

---
*Phase: 033-design-tokens-and-css-component-system*
*Completed: 2026-04-12*
