---
phase: 035-login-page-glass-card-redesign
plan: 01
subsystem: ui
tags: [tailwind, css, glassmorphism, safari, webkit, postcss, backdrop-filter]

# Dependency graph
requires:
  - phase: 033-design-tokens
    provides: Tailwind config with canvas/surface color tokens and input.css @layer components structure
provides:
  - ".glass-card component class in @layer components with fixed-pixel -webkit-backdrop-filter"
  - "Both login templates (admin + operator) using glass-card instead of inline Tailwind utilities"
  - "postcss.config.js with autoprefixer({ remove: false }) to preserve -webkit-backdrop-filter through build"
  - "output.css rebuilt with -webkit-backdrop-filter:blur(12px) present"
affects: [036-log-views, future-glass-components]

# Tech tracking
tech-stack:
  added: ["postcss.config.js (autoprefixer remove:false)", "autoprefixer (npm)"]
  patterns:
    - "Glass card component: raw CSS -webkit-backdrop-filter in @layer components, NOT @apply backdrop-blur-* (avoids CSS variable indirection)"
    - "PostCSS autoprefixer must be configured with remove:false to preserve manually-added -webkit- prefixes through the build pipeline"
    - "Fixed pixel blur values (blur(12px)) required for Safari — CSS variable references fail in -webkit-backdrop-filter on Safari pre-18.0 and 18.x"

key-files:
  created:
    - postcss.config.js
  modified:
    - static/css/input.css
    - templates/admin/login.html
    - templates/log/login.html
    - static/css/output.css
    - package.json

key-decisions:
  - "035-01: .glass-card uses raw -webkit-backdrop-filter: blur(12px) not @apply backdrop-blur-md — Tailwind backdrop-blur utilities emit CSS variable references which fail in Safari"
  - "035-01: postcss.config.js created with autoprefixer({ remove: false }) — default autoprefixer silently strips manually-added -webkit-backdrop-filter during build"
  - "035-01: bg-white/10 (10% white) used instead of original bg-white/5 (5%) — stronger opacity improves legibility over dark violet/indigo gradients"

patterns-established:
  - "Safari glass pattern: always write -webkit-backdrop-filter with literal pixel values in @layer components; never use @apply for backdrop-filter properties"
  - "Build pipeline check: after adding any -webkit- property manually, verify grep output.css confirms it survives the build"

# Metrics
duration: ~30min
completed: 2026-04-11
---

# Phase 35 Plan 01: Login Page Glass Card Redesign Summary

**.glass-card Tailwind component class with explicit -webkit-backdrop-filter:blur(12px) and postcss.config.js autoprefixer fix — frosted glass renders in Safari, Chrome, and Firefox on both login pages**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-11
- **Completed:** 2026-04-11
- **Tasks:** 3 (2 auto + 1 human-verify checkpoint)
- **Files modified:** 5

## Accomplishments

- Added `.glass-card` to `@layer components` in `input.css` with raw `-webkit-backdrop-filter: blur(12px)` and `backdrop-filter: blur(12px)` — no CSS variable references
- Replaced verbose inline Tailwind utility chains on both login card divs with `class="glass-card"` — admin and operator login templates cleaned up
- Discovered and fixed postcss autoprefixer silently stripping `-webkit-backdrop-filter` during build; created `postcss.config.js` with `autoprefixer({ remove: false })` — output.css now reliably contains the webkit-prefixed property after every build
- Human visual verification confirmed frosted-glass appearance in Safari, Chrome, and Firefox on both `/admin/ui/login` and `/log/login`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add .glass-card component class to input.css** - `243d3b9` (feat)
2. **Task 2: Replace inline glass classes, fix build pipeline, rebuild CSS** - `487e4db` (feat)
3. **Task 3: Safari visual verification** - human checkpoint, approved by user (no commit)

## Files Created/Modified

- `postcss.config.js` — created; configures autoprefixer with `remove: false` to preserve manually-added -webkit- prefixes through Tailwind build
- `static/css/input.css` — added `.glass-card` block inside `@layer components` with raw backdrop-filter CSS
- `templates/admin/login.html` — card div replaced from inline utility chain to `class="glass-card"`
- `templates/log/login.html` — same replacement as admin login
- `static/css/output.css` — rebuilt artifact; now contains `.glass-card` with `-webkit-backdrop-filter:blur(12px)`

## Decisions Made

- `.glass-card` uses raw CSS `-webkit-backdrop-filter: blur(12px)` instead of `@apply backdrop-blur-md`: Tailwind's backdrop-blur utilities expand to `backdrop-filter: var(--tw-backdrop-blur) ...`, which (1) does not emit a corresponding `-webkit-backdrop-filter` property and (2) uses CSS variable references that Safari pre-18.0 and 18.x do not reliably resolve inside `-webkit-backdrop-filter`. Only fixed pixel values work cross-browser.
- `postcss.config.js` created with `autoprefixer({ remove: false })`: the default autoprefixer configuration removes vendor-prefixed properties it considers unnecessary or redundant, silently stripping the `-webkit-backdrop-filter` that was manually written. `remove: false` disables that behavior and preserves the explicit webkit prefix.
- `bg-white/10` used in `.glass-card` instead of the original `bg-white/5`: 10% white opacity provides better visual contrast and legibility of the glass card over the dark violet and indigo gradients used on the admin and operator login backgrounds respectively.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] PostCSS autoprefixer stripping -webkit-backdrop-filter from output.css**
- **Found during:** Task 2 (rebuild + verify step)
- **Issue:** After running `npm run build`, `grep 'webkit-backdrop-filter' output.css` returned empty. The `-webkit-backdrop-filter` written in `input.css` was being silently removed by autoprefixer during the Tailwind build pipeline. Without this fix, Safari would receive no webkit-prefixed property and the entire point of the plan would be defeated.
- **Fix:** Created `postcss.config.js` with `module.exports = { plugins: [require('autoprefixer')({ remove: false })] }`. Updated `package.json` build script to pipe through postcss. Rebuilt and re-verified output.css.
- **Files modified:** `postcss.config.js` (created), `package.json` (build script updated)
- **Verification:** `grep 'webkit-backdrop-filter' output.css` returned `-webkit-backdrop-filter:blur(12px)` after the fix
- **Committed in:** `487e4db` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking build pipeline issue)
**Impact on plan:** Auto-fix was necessary for the plan objective to be achievable. Without it, output.css would never contain the webkit prefix regardless of what was written in input.css. No scope creep — postcss.config.js is standard configuration for any project using PostCSS.

## Issues Encountered

The autoprefixer stripping issue was the primary obstacle. It was non-obvious because the source `input.css` clearly contained the `-webkit-backdrop-filter` line, making it appear correct until the built `output.css` was inspected. The diagnostic was: write the property in source, run build, grep output — absence in output pointed to the build pipeline as the removal point, not the source.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 35 complete: both login pages render frosted-glass in Safari, Chrome, and Firefox
- LOGN-01, LOGN-02, LOGN-03 all satisfied
- `postcss.config.js` with `autoprefixer({ remove: false })` is now in place — any future `-webkit-` properties written manually in `input.css` will survive the build
- Phase 36 (log views) can proceed immediately; no blockers

---
*Phase: 035-login-page-glass-card-redesign*
*Completed: 2026-04-11*
