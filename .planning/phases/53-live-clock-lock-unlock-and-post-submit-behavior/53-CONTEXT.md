# Phase 53: Live Clock, Lock/Unlock, and Post-Submit Behavior - Context

**Gathered:** 2026-04-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Frontend-only changes in `templates/log/form.html`: live UTC clock with `setInterval`, inline padlock toggle controls on the QSO_DATE and TIME_ON fields, HHMM→HHMM00 normalization before submission, and a post-submit reset behavior toggle switch.

No backend changes. No new Python files. No new dependencies.

</domain>

<decisions>
## Implementation Decisions

### Reset Toggle (RESET-01, RESET-02, RESET-03)
- **D-01:** Widget type: toggle switch, built from a hidden checkbox + styled label using pure Tailwind utility classes inline in `form.html`. No new CSS component class in `input.css`. Follows the existing pattern of inline Tailwind in templates.
- **D-02:** Placement: inline with the submit row — the same flex row as the "Log QSO" button and "Clear" button. Visual association between the action and its post-submit behavior.
- **D-03:** Default state: ON ("Reset to live UTC") when no `localStorage` preference has been saved yet. First-time operators get the safest default.

### Padlock Icon Controls (DATE-03, TIME-03)
- **D-04:** Placement: inline suffix inside the input wrapper, right side (password show/hide pattern). The input gets `padding-right` so the text value doesn't overlap the icon. The padlock is a `<button type="button">` so it doesn't trigger form submission.
- **D-05:** Icons: Heroicons outline style to match existing form icons (which use `fill="none"`, `stroke-width="2"`, `stroke="currentColor"`). Use lock-closed SVG when locked, lock-open SVG when unlocked.

### Locked Field Styling (DATE-02, TIME-02)
- **D-06:** When locked: muted background (e.g. `bg-gray-50 dark:bg-gray-800/50`) + `cursor-not-allowed`. When unlocked: normal `form-input` styling. The background change reinforces the readonly state visually, supplementing the padlock icon.

### Post-Submit Behavior
- **D-07:** Always focus the CALL field after a successful QSO log, regardless of which reset mode is active. Consistent behavior — the next action is always entering the next callsign.
- **D-08:** "Reset to live UTC" mode: call `initDateTime()` immediately after `form.reset()` in the `htmx:afterSwap` handler to re-populate both fields to locked UTC state and restart the time `setInterval`.
- **D-09:** "Keep current date/time" mode: skip `form.reset()` entirely. Fields, lock state, and `setInterval` are preserved as-is. Only clear validation errors and re-focus CALL.

### Validation Updates (DATE-04, TIME-04, TIME-05)
- **D-10:** HHMM normalization runs first in `htmx:beforeRequest`, before `validate()` fires. After normalization, the TIME_ON value is always 6 digits, so the validation rule updates to `^\d{6}$`. The normalization is: if value matches `^\d{4}$`, append `"00"`.
- **D-11:** DATE validation rule stays `^\d{8}$` — date field is locked by default and only editable when explicitly unlocked, so invalid dates are rare but still validated.
- **D-12:** Locked fields are excluded from client-side validation errors — when a field is locked, the JS manages its value and it is always valid.

### Claude's Discretion
- Exact Tailwind utility classes for the toggle switch pill and thumb (follow existing dark: patterns in the template for color choices like `indigo-500` / `gray-300`)
- `initDateTime()` function naming and exact structure (initialize both fields + start the time `setInterval`)
- Heroicons SVG viewBox and exact `<path>` data for lock-closed and lock-open (outline variants, 16×16 `w-4 h-4`)
- Whether the padlock wrapper div uses `relative` positioning or a flex row — whichever is cleaner given the existing `.form-input` class structure

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Target file
- `templates/log/form.html` — the only file being modified; contains existing validation JS, `htmx:beforeRequest` gate, `htmx:afterSwap` reset handler, and full form HTML structure

### Requirements
- `.planning/REQUIREMENTS.md` §DATE, §TIME, §RESET — all 12 requirements for this phase with exact acceptance criteria

### Styling reference
- `static/css/input.css` — `@layer components` definitions for `.form-input`, `.btn-primary`, `.btn-ghost`, `.card-body`; check dark: patterns for existing color choices
- `tailwind.config.js` — content scan paths; confirm `templates/**/*.html` is included so new dark: classes emit to `output.css`

### Prior context (decisions already locked)
- `.planning/phases/52-time-on-db-migration/52-CONTEXT.md` — backend migration decisions; confirms `readonly` (not `disabled`) and DB-02 are already satisfied

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `htmx:beforeRequest` handler in `form.html` (lines ~167–172): already gates submission behind `validate()` — HHMM normalization goes here, before the `validate()` call
- `htmx:afterSwap` handler in `form.html` (lines ~174–186): calls `form.reset()` + focus CALL on success — this is the hook for post-submit reset behavior branching
- Existing form validation `rules` object: contains `QSO_DATE: /^\d{8}$/` and `TIME_ON: /^\d{4}$/` — TIME_ON rule needs update to `^\d{6}$` after normalization is in place

### Established Patterns
- Heroicons inline SVG: existing `<svg>` in the submit button uses `fill="none"`, `stroke-width="2"`, `stroke="currentColor"`, `viewBox="0 0 24 24"` — padlock icons must match this style
- Tailwind dark: classes must appear as complete literal strings in scanned templates for Tailwind purge; run `npm run build` + grep verification after adding new dark: classes
- FOUC prevention inline IIFE in `base.html` `<head>` is load-bearing — do not touch it

### Integration Points
- `#qso-result` is `hx-target` — form DOM, event listeners, and `setInterval` all survive every HTMX swap; no re-initialization hook needed
- `form.reset()` clears auto-populated fields — must call `initDateTime()` immediately after reset in "Reset to live UTC" mode to re-populate and re-apply `readonly`
- `localStorage` key for reset preference: use a namespaced key (e.g. `ollog.resetMode`) to avoid collision

</code_context>

<specifics>
## Specific Ideas

- STATE.md explicitly called out: `disabled` silently drops QSO_DATE/TIME_ON from POST body — always use `.readOnly = true/false`, never `.disabled`
- STATE.md: `Date.getUTC*()` exclusively — never `getHours()`, `getDate()`, etc.
- The "Clear" button (`type="reset"`) will trigger `form.reset()`, clearing auto-populated fields — the reset button's click handler (or `form`'s `reset` event) must call `initDateTime()` to restore locked UTC defaults after a manual clear

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 53-live-clock-lock-unlock-and-post-submit-behavior*
*Context gathered: 2026-04-28*
