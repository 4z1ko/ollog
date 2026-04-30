---
phase: 53
plan: 02
subsystem: ui
tags: [javascript, htmx, tailwind, form, utc-clock, localStorage, padlock]

# Dependency graph
requires:
  - phase: 53-01
    provides: HTML scaffold with all element IDs (qso-date-input, qso-time-input, qso-date-lock, qso-time-lock, qso-date-lock-icon, qso-time-lock-icon, reset-mode-toggle, reset-mode-label)

provides:
  - Live UTC clock via setInterval using getUTC* exclusively, auto-updating TIME_ON every second
  - Padlock toggle handlers for QSO_DATE and TIME_ON (readOnly toggle, SVG path swap, aria-label swap, locked-style toggle)
  - HHMM->HHMM00 normalization in htmx:beforeRequest before validation fires
  - Locked-field-aware validate() that skips readOnly fields (D-12)
  - initResetToggle() IIFE: localStorage-backed reset-mode persistence with 'Reset to live UTC' / 'Keep current date/time' label
  - Branched htmx:afterSwap: 'reset' mode replays form.reset() + initDateTime(); 'keep' mode preserves all field state
  - Clear button (type=reset) repopulates date/time via deferred initDateTime() in form reset event

affects:
  - Verifier (Task 5): human browser verification of all 12 Phase 53 requirements

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "module-scoped var timeInterval = null with clearInterval guard at top of initDateTime()"
    - "getUTC* exclusively — never getHours/getDate/getMonth/getMinutes/getSeconds/getFullYear"
    - "SVG path swap via path.setAttribute('d', locked ? LOCK_CLOSED_D : LOCK_OPEN_D)"
    - "HHMM normalization: /^\\d{4}$/.test before validate(), append '00' only on unlocked field"
    - "localStorage key ollog.resetMode ('reset' | 'keep'); default ON (reset) when null"
    - "setTimeout(fn, 0) deferral for Clear button reset event (Pitfall 4 guard)"

key-files:
  created: []
  modified:
    - templates/log/form.html

key-decisions:
  - "initDateTime() uses getElementById (not field()) to access date/time inputs — more explicit for the initialization path"
  - "setInterval body guards on timeEl.readOnly to avoid mutating an unlocked field even if interval was not cleared"
  - "Time padlock unlock: clearInterval + timeInterval=null (full teardown); re-lock: new setInterval"
  - "date padlock re-lock: restores currentUTCDate() value (does not call initDateTime() — avoids restarting time interval)"
  - "initResetToggle inserted before htmx:beforeRequest — toggle is fully initialized before any submit can occur"
  - "clearErrors() + submitAttempted=false + CALL.focus() placed OUTSIDE the if(mode!='keep') block — both branches always run them"

# Metrics
duration: ~20min
completed: 2026-04-29
---

# Phase 53 Plan 02: Live Clock Lock/Unlock and Post-Submit Behavior — JavaScript Behavior Layer Summary

**Full JavaScript behavior layer for UTC live clock, padlock toggles, HHMM normalization, locked-field validation, and localStorage-backed post-submit reset branching in form.html**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-29
- **Completed:** 2026-04-29
- **Tasks:** 4 automated + 1 checkpoint (human browser verification pending)
- **Files modified:** 1 (templates/log/form.html)

## Accomplishments

### Task 1: UTC Clock Helpers + initDateTime()
- Added `var timeInterval = null` module-scoped handle
- Added `pad2()`, `currentUTCDate()`, `currentUTCTime()` using `getUTC*` exclusively (no local-time accessors)
- Added `applyLockedStyle()` and `removeLockedStyle()` targeting `bg-gray-50`, `dark:bg-gray-800/50`, `cursor-not-allowed`
- Added `initDateTime()` with clearInterval guard at top, populates both fields, locks both, starts setInterval
- Added page-load call to `initDateTime()` at bottom of IIFE

### Task 2: Padlock Toggle Handlers + Clear Button Hook
- Added `LOCK_CLOSED_D` and `LOCK_OPEN_D` Heroicons 24px outline path constants
- Added `setLockIcon()` helper: `path.setAttribute('d', locked ? LOCK_CLOSED_D : LOCK_OPEN_D)`
- Added date padlock click handler: toggles readOnly, locked CSS, SVG path, aria-label
- Added time padlock click handler: same plus `clearInterval` on unlock and `setInterval` restart on re-lock
- Added `form.addEventListener('reset', ...)` with `setTimeout(fn, 0)` deferral calling `initDateTime()`

### Task 3: Validation + HHMM Normalization
- Changed TIME_ON rule from `/^\d{4}$/` to `/^\d{6}$/`
- Added `if (el.readOnly) { setError(el, false); return; }` guard inside `validate()` (D-12)
- Prepended HHMM normalization to `htmx:beforeRequest`: if TIME_ON is unlocked and matches `/^\d{4}$/`, appends `'00'` before `validate()` fires

### Task 4: Reset-Mode Persistence + Branched htmx:afterSwap
- Added `initResetToggle()` IIFE: reads `localStorage.getItem('ollog.resetMode')`, sets checkbox and label text, attaches change listener
- Replaced `htmx:afterSwap` handler with branched version: `mode !== 'keep'` → `form.reset()` + `initDateTime()`; both modes → `clearErrors()` + `submitAttempted=false` + `CALL.focus()`

## Task Commits

Each task committed atomically:

1. **Task 1: UTC clock helpers and initDateTime()** - `544d724` (feat)
2. **Task 2: Padlock toggle handlers and Clear button reset hook** - `bed6389` (feat)
3. **Task 3: TIME_ON validation, locked-field skip, HHMM normalization** - `1471c91` (feat)
4. **Task 4: Reset-mode persistence and branched htmx:afterSwap** - `4942dd3` (feat)

## Files Created/Modified

- `templates/log/form.html` — all JS behavior added inside the existing IIFE `<script>` block; 166 lines added across 4 commits

## Decisions Made

- `initDateTime()` uses `getElementById` directly (not `field()`) to access `qso-date-input` and `qso-time-input` — they are not form field inputs looked up by `name`, they are accessed by ID
- The `setInterval` callback guards on `timeEl.readOnly` as a secondary defense: even if the interval runs after unlock (before explicit clearInterval), it will not overwrite the user's value
- The date padlock re-lock path calls `currentUTCDate()` directly and does NOT call `initDateTime()` — calling `initDateTime()` would also restart the time interval, which is only needed when re-locking the time field
- `initResetToggle()` is placed BEFORE `htmx:beforeRequest` in the IIFE so the toggle is fully initialized before any submit can fire

## Deviations from Plan

None — all four tasks executed exactly as specified in 53-02-PLAN.md.

## Verification Results

### Automated Gates (all passed)
- Task 1: all 12 grep checks passed (timeInterval, pad2, currentUTCDate, currentUTCTime, getUTCFullYear, getUTCHours, applyLockedStyle, removeLockedStyle, initDateTime, clearInterval guard, setInterval, no local-time accessors)
- Task 2: all 13 checks passed (LOCK_CLOSED_D, LOCK_OPEN_D, setLockIcon, date/time lock handlers, reset listener, setTimeout defer, all 4 aria-labels, no .disabled=)
- Task 3: TIME_ON regex updated to d{6}, QSO_DATE unchanged at d{8}, locked-field guard present, normalization guard and append present
- Task 4: initResetToggle present, localStorage.getItem appears exactly 2x, both setItem calls present, both label strings present, mode check and branching present, form.reset() followed by initDateTime()
- Phase-level: no .disabled= anywhere, no local-time accessors, npm run build + npm run verify both pass

### Human Verification (Task 5): CHECKPOINT — AWAITING HUMAN APPROVAL

Task 5 is a `checkpoint:human-verify` gate. The automated tasks are complete and all checks pass. Human browser verification is required to confirm all 12 phase requirements (DATE-01 through DATE-04, TIME-01 through TIME-05, RESET-01 through RESET-03) pass in a live browser session.

See the Task 5 verification procedure in `53-02-PLAN.md` for the full step-by-step walkthrough.

## Issues Encountered

- Backend regression test (`uv run pytest tests/ -x -q`) not run: MongoDB is not available in this execution environment (Docker not running). No Python files were modified in this plan, so no regression risk exists. This is a known pre-existing constraint per CLAUDE.md.
- npm run build and npm run verify both passed — no new Tailwind dark: classes were added in Plan 02 (JS only), confirming Plan 01's classes remain present.

## Known Stubs

None. All element IDs are wired to live behavior. The only pending work is Task 5 human browser verification.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. All changes are client-side JS within the existing IIFE. The threat mitigations from the plan's threat model are implemented:

- T-53-07 (setInterval leakage): clearInterval guard at top of every `initDateTime()` call — mitigated
- T-53-08 (DOM XSS): `label.textContent` used (not innerHTML) for toggle label — mitigated

---

## Self-Check

**Checking modified files exist:**

- `templates/log/form.html` — modified (verified by reading file)
- `.planning/phases/53-live-clock-lock-unlock-and-post-submit-behavior/53-02-SUMMARY.md` — this file

**Checking commits exist:**

- Task 1: `544d724` — feat(53-02): add UTC clock helpers and initDateTime() with page-load init — FOUND
- Task 2: `bed6389` — feat(53-02): add padlock toggle handlers and Clear button reset hook — FOUND
- Task 3: `1471c91` — feat(53-02): update TIME_ON validation, locked-field skip, HHMM normalization — FOUND
- Task 4: `4942dd3` — feat(53-02): add reset-mode persistence and branched htmx:afterSwap — FOUND

## Self-Check: PASSED
