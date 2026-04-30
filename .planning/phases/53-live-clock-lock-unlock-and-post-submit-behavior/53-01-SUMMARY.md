---
phase: 53-live-clock-lock-unlock-and-post-submit-behavior
plan: 01
subsystem: ui
tags: [tailwind, htmx, jinja2, heroicons, form, dark-mode]

# Dependency graph
requires:
  - phase: 52-time-on-db-migration
    provides: Server-side HHMMSS acceptance and readonly vs disabled contract established

provides:
  - QSO_DATE input wrapped in relative div with inline padlock button (id=qso-date-input, id=qso-date-lock, id=qso-date-lock-icon)
  - TIME_ON input wrapped in relative div with inline padlock button (id=qso-time-input, id=qso-time-lock, id=qso-time-lock-icon)
  - Reset-mode toggle widget in submit row (id=reset-mode-toggle, id=reset-mode-label)
  - All new Tailwind utility classes emitted to static/css/output.css via npm run build
  - Static locked-state visual rendering on first paint (no JS required for initial state)

affects:
  - 53-02-PLAN (Plan 02 JS implementation — all element IDs are ready for binding)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Padlock input wrapper: relative parent + absolute inset-y-0 right-0 button for icon overlay"
    - "Tailwind peer-checked toggle: sr-only peer checkbox + peer-checked: label variants"
    - "Heroicons inline SVG at stroke-width=1.5 for form icon consistency"
    - "readonly HTML attribute on locked fields (not disabled — disabled drops field from POST body)"

key-files:
  created: []
  modified:
    - templates/log/form.html
    - static/css/output.css

key-decisions:
  - "Using readonly (not disabled) on QSO_DATE/TIME_ON so field values always reach the server POST body"
  - "Lock-closed SVG path baked into initial HTML so locked state renders before JS loads"
  - "Toggle checkbox has checked HTML attribute by default matching D-03 default (Reset to live UTC)"
  - "pr-3 (not pr-2.5) for padlock button to stay on 4-point grid per UI-SPEC"
  - "flex-wrap on submit row prevents toggle overflow on narrow viewports"
  - "ml-auto on toggle container pushes it to right edge of flex row"

patterns-established:
  - "Padlock input wrapper: class=relative > input class=form-input pr-9 + button class=absolute inset-y-0 right-0"
  - "Heroicons 24px outline SVGs: fill=none viewBox=0 0 24 24 stroke-width=1.5 stroke=currentColor"
  - "Toggle switch: input type=checkbox class=sr-only peer + label with peer-checked: Tailwind variants"

requirements-completed:
  - DATE-02
  - DATE-03
  - TIME-03
  - RESET-01

# Metrics
duration: 15min
completed: 2026-04-29
---

# Phase 53 Plan 01: Live Clock Lock/Unlock and Post-Submit Behavior — HTML/CSS Scaffolding Summary

**Padlock-wrapped QSO_DATE/TIME_ON inputs with Heroicons lock-closed SVGs and a peer-checked Tailwind toggle in the submit row, all rendering correctly in locked state before any JavaScript runs**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-29T16:30:08Z
- **Completed:** 2026-04-29T16:45:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- QSO_DATE and TIME_ON inputs wrapped in `relative` divs with `<button type="button">` padlock icons at right edge, rendered locked (bg-gray-50 dark:bg-gray-800/50 cursor-not-allowed) on first paint with `readonly` HTML attribute
- Reset-mode toggle widget added inline to submit row — hidden `sr-only peer` checkbox, pill-shaped label with `peer-checked:bg-indigo-500` and `peer-checked:after:translate-x-4`, `#reset-mode-label` span defaulting to "Reset to live UTC"
- All new Tailwind utility classes (including `dark:bg-gray-800/50`, `peer-checked:*`, `after:*`) confirmed emitted in `static/css/output.css` after `npm run build`; `npm run verify` passes

## Task Commits

Each task was committed atomically:

1. **Task 1: Wrap QSO_DATE and TIME_ON inputs with padlock buttons** - `631d933` (feat)
2. **Task 2: Add reset-mode toggle widget to submit row** - `426f341` (feat)
3. **Task 3: Build Tailwind output.css and verify all new classes are emitted** - `eb76ec7` (chore)

## Files Created/Modified

- `templates/log/form.html` - QSO_DATE and TIME_ON inputs wrapped in relative/absolute padlock structure; submit row extended with peer-checked toggle widget; TIME_ON placeholder changed from HHMM to HHMMSS
- `static/css/output.css` - Rebuilt to include all Phase 53 utility classes

## Decisions Made

- Followed plan exactly as specified. All implementation decisions were locked in CONTEXT.md prior to this plan.
- `pr-3` used for padlock button (not `pr-2.5`) per UI-SPEC adjustment to stay on 4-point grid
- `flex-wrap` added to submit row as specified in plan to prevent toggle overflow on narrow viewports

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Backend regression test (`uv run pytest tests/ -x -q`) could not complete because MongoDB is not available in this execution environment (Docker not running). This is a known pre-existing constraint per CLAUDE.md ("Tests require MongoDB on localhost:27017"). No Python files were modified in this plan, so no regression risk exists.

## User Setup Required

None — no external service configuration required.

## Known Stubs

None. The date and time fields are intentionally empty (no JS values set) on initial paint — the live clock and `initDateTime()` function will be added by Plan 02. This is the designed split between Plan 01 (HTML/CSS) and Plan 02 (JavaScript behavior).

## Hand-off Note for Plan 02

All element IDs are in place and ready for JavaScript binding:

| ID | Element | Purpose |
|----|---------|---------|
| `qso-date-input` | QSO_DATE `<input>` | Target for `initDateTime()` date value + readOnly toggle |
| `qso-time-input` | TIME_ON `<input>` | Target for `initDateTime()` time value + setInterval |
| `qso-date-lock` | QSO_DATE padlock `<button>` | Click target for `toggleDateLock()` |
| `qso-time-lock` | TIME_ON padlock `<button>` | Click target for `toggleTimeLock()` |
| `qso-date-lock-icon` | QSO_DATE lock `<svg>` | Target for SVG path swap (closed ↔ open) |
| `qso-time-lock-icon` | TIME_ON lock `<svg>` | Target for SVG path swap (closed ↔ open) |
| `reset-mode-toggle` | Hidden `<input type="checkbox">` | `initResetToggle()` reads/writes via `.checked` |
| `reset-mode-label` | `<span>` text | `initResetToggle()` sets `.textContent` |

The lock-closed SVG path used in HTML (for reference in JS path-swap):
```
M16.5 10.5V6.75C16.5 4.26472 14.4853 2.25 12 2.25C9.51472 2.25 7.5 4.26472 7.5 6.75V10.5M6.75 21.75H17.25C18.4926 21.75 19.5 20.7426 19.5 19.5V12.75C19.5 11.5074 18.4926 10.5 17.25 10.5H6.75C5.50736 10.5 4.5 11.5074 4.5 12.75V19.5C4.5 20.7426 5.50736 21.75 6.75 21.75Z
```

The lock-open SVG path (for Plan 02 JS to swap in on unlock):
```
M13.5 10.5V6.75C13.5 4.26472 15.5147 2.25 18 2.25C20.4853 2.25 22.5 4.26472 22.5 6.75V10.5M3.75 21.75H14.25C15.4926 21.75 16.5 20.7426 16.5 19.5V12.75C16.5 11.5074 15.4926 10.5 14.25 10.5H3.75C2.50736 10.5 1.5 11.5074 1.5 12.75V19.5C1.5 20.7426 2.50736 21.75 3.75 21.75Z
```

## Next Phase Readiness

Plan 02 can proceed immediately — all HTML scaffolding and CSS output are in place. Plan 02's responsibility:
- Add `var timeInterval = null;` at top of IIFE
- Add `initDateTime()`, `pad2()`, `applyLockedStyle()`, `removeLockedStyle()` helpers
- Add `toggleDateLock()` and `toggleTimeLock()` functions
- Update `rules.TIME_ON` regex from `/^\d{4}$/` to `/^\d{6}$/`
- Update `validate()` to skip locked fields (D-12)
- Prepend HHMM normalization to `htmx:beforeRequest` (D-10)
- Replace `htmx:afterSwap` handler with reset-mode branch (D-07/D-08/D-09)
- Add `form.addEventListener('reset', ...)` for Clear button
- Add `initResetToggle()` IIFE
- Call `initDateTime()` at bottom of outer IIFE (page load)

---

## Self-Check

**Checking created files exist:**

- `templates/log/form.html` — modified (existed before)
- `static/css/output.css` — modified (existed before)
- `.planning/phases/53-live-clock-lock-unlock-and-post-submit-behavior/53-01-SUMMARY.md` — this file

**Checking commits exist:**

- Task 1: `631d933` — feat(53-01): wrap QSO_DATE and TIME_ON inputs with padlock buttons
- Task 2: `426f341` — feat(53-01): add reset-mode toggle widget to submit row
- Task 3: `eb76ec7` — chore(53-01): rebuild Tailwind output.css with Phase 53 utility classes

## Self-Check: PASSED

---
*Phase: 53-live-clock-lock-unlock-and-post-submit-behavior*
*Completed: 2026-04-29*
