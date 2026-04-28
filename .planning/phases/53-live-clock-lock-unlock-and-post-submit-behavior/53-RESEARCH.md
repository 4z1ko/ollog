# Phase 53: Live Clock, Lock/Unlock, and Post-Submit Behavior - Research

**Researched:** 2026-04-28
**Domain:** Vanilla JavaScript in a Jinja2/HTMX template — setInterval, UTC clock, readonly toggling, HTMX event hooks, Tailwind toggle switch, localStorage
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01 — Reset toggle widget:** Hidden checkbox + styled label, pure Tailwind inline in `form.html`. No new CSS component class in `input.css`.

**D-02 — Toggle placement:** Inline with the submit row (same flex row as "Log QSO" and "Clear").

**D-03 — Default state:** ON ("Reset to live UTC") when no `localStorage` preference saved yet.

**D-04 — Padlock placement:** Inline suffix inside the input wrapper, right side (password show/hide pattern). Input gets `padding-right` so text doesn't overlap icon. Padlock is `<button type="button">` — does not trigger form submission.

**D-05 — Padlock icons:** Heroicons outline style matching existing SVGs (`fill="none"`, `stroke-width="1.5"`, `stroke="currentColor"`, `viewBox="0 0 24 24"`). lock-closed SVG when locked, lock-open SVG when unlocked.

**D-06 — Locked field styling:** Locked → `bg-gray-50 dark:bg-gray-800/50` + `cursor-not-allowed`. Unlocked → normal `form-input` styling.

**D-07 — Post-submit focus:** Always focus CALL field after successful QSO log, regardless of reset mode.

**D-08 — "Reset to live UTC" mode:** Call `initDateTime()` immediately after `form.reset()` in `htmx:afterSwap` handler to re-populate both fields to locked UTC state and restart time `setInterval`.

**D-09 — "Keep current date/time" mode:** Skip `form.reset()` entirely. Fields, lock state, and `setInterval` preserved as-is. Only clear validation errors and re-focus CALL.

**D-10 — HHMM normalization:** Runs first in `htmx:beforeRequest`, before `validate()`. After normalization, TIME_ON is always 6 digits. Validation rule updates to `^\d{6}$`. Normalization: if value matches `^\d{4}$`, append `"00"`.

**D-11 — DATE validation:** Rule stays `^\d{8}$`.

**D-12 — Locked field validation:** Locked fields excluded from client-side validation errors — JS manages their value and it is always valid.

### Claude's Discretion

- Exact Tailwind utility classes for toggle switch pill and thumb (follow existing dark: patterns, colors like `indigo-500` / `gray-300`)
- `initDateTime()` function naming and exact structure (initialize both fields + start the time `setInterval`)
- Heroicons SVG viewBox and exact `<path>` data for lock-closed and lock-open (outline variants, rendered at `w-4 h-4`)
- Whether padlock wrapper div uses `relative` positioning or a flex row — whichever is cleaner given existing `.form-input` class structure

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATE-01 | Date field defaults to today's UTC date in YYYYMMDD format on form load | `initDateTime()` calls `Date.getUTCFullYear/Month/Date()`, pads with leading zeros, sets `.value`, applies `.readOnly = true` |
| DATE-02 | Date field is locked (readonly) by default | `.readOnly = true` set in `initDateTime()`; value is included in POST body (readonly, not disabled) |
| DATE-03 | Lock icon button toggles readonly on date field | `<button type="button">` in input wrapper; click handler toggles `.readOnly`, swaps icon SVG, applies/removes locked CSS classes |
| DATE-04 | Manual date validated against YYYYMMDD; invalid rejected before submission | `rules.QSO_DATE` regex `/^\d{8}$/`; `setError()` shows `.form-input-error`; checked in `htmx:beforeRequest` |
| TIME-01 | Time field defaults to current UTC time in HHMMSS format on form load | `initDateTime()` reads `getUTCHours/Minutes/Seconds()`, pads to 6 digits, sets `.value`, applies `.readOnly = true` |
| TIME-02 | While locked, time auto-updates every second via setInterval using UTC | `setInterval` in `initDateTime()` updates value from `Date.getUTC*()` every 1000ms; interval cleared on unlock |
| TIME-03 | Lock icon button toggles auto-update and editability on time field | Click clears stored `setInterval` id on unlock; restarts interval on re-lock |
| TIME-04 | Manual time accepts HHMM or HHMMSS; HHMM normalized to HHMM00 before submit | Normalization in `htmx:beforeRequest`: `if (/^\d{4}$/.test(v)) field.value = v + '00'` |
| TIME-05 | Invalid time format rejected with visible feedback before submit | After normalization, `rules.TIME_ON` regex `/^\d{6}$/`; `.form-input-error` class applied |
| RESET-01 | Toggle on form controls post-submit behavior | Hidden checkbox (`id="reset-mode-toggle"`) + styled label; state persists in `localStorage` key `ollog.resetMode` |
| RESET-02 | "Keep current date/time" — values and lock state preserved after submit | `htmx:afterSwap` skips `form.reset()` and `initDateTime()`; only clears errors and focuses CALL |
| RESET-03 | "Reset to live UTC" — both fields return to locked state after submit | `htmx:afterSwap` calls `form.reset()` then `initDateTime()` immediately after |
</phase_requirements>

---

## Summary

Phase 53 is a pure frontend change — a single file modification to `templates/log/form.html`. No Python, no new dependencies, no backend touch. The implementation adds three interlocked JavaScript behaviors: (1) a live UTC clock via `setInterval` using only `Date.getUTC*()`, (2) padlock toggle controls on the QSO_DATE and TIME_ON inputs using `<button type="button">` with Heroicons outline SVGs, and (3) a post-submit reset behavior toggle switch stored in `localStorage` that branches the `htmx:afterSwap` handler.

All the HTMX hooks needed (`htmx:beforeRequest` for normalization+validation, `htmx:afterSwap` for post-submit reset) already exist in `form.html`. The existing validation object (`rules`), `setError()`, `clearErrors()`, and `submitAttempted` flag are all reused. The only updates are: (a) the TIME_ON validation regex changes from `/^\d{4}$/` to `/^\d{6}$/`, (b) locked fields are excluded from validation errors, (c) normalization is prepended to `htmx:beforeRequest`, and (d) `htmx:afterSwap` branches on `localStorage.getItem('ollog.resetMode')`.

The HTMX swap target `#qso-result` is a sibling of the form, not an ancestor. This means the form DOM, all `addEventListener` calls, and the `setInterval` handle all survive every submit/swap cycle — no re-initialization on swap is needed, only the post-reset `initDateTime()` call in "Reset to live UTC" mode.

**Primary recommendation:** Implement all changes in one plan (single wave) targeting `templates/log/form.html` only. Run `npm run build` + `npm run verify` after adding new `dark:` Tailwind classes, and manually verify the toggle and clock in-browser.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Live UTC clock | Browser / Client | — | `setInterval` runs in the browser; only JS has access to real-time updates without polling |
| Padlock toggle (readonly) | Browser / Client | — | DOM attribute manipulation; no server state involved |
| HHMM → HHMM00 normalization | Browser / Client | API / Backend | Client normalizes before POST; server already accepts both (DB-02, Phase 52) |
| Client-side validation | Browser / Client | — | Runs in `htmx:beforeRequest` gate; prevents invalid POST |
| Post-submit reset behavior | Browser / Client | — | Branching logic in `htmx:afterSwap`; state in localStorage |
| Reset preference persistence | Browser / Client | — | `localStorage` key `ollog.resetMode`; no server-side persistence this phase |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vanilla JS (ES5 compatible) | Browser native | setInterval, DOM manipulation, localStorage | No build step; matches existing IIFE pattern in form.html [VERIFIED: codebase] |
| HTMX | 2.0.4 | `htmx:beforeRequest`, `htmx:afterSwap` events | Already loaded in base.html [VERIFIED: codebase] |
| Tailwind CSS | 3.4.x | Toggle switch styles, locked field visual states | Already in build; content scan covers `templates/**/*.html` [VERIFIED: codebase] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Heroicons outline SVG (inlined) | 2.x paths | lock-closed and lock-open icons | Inline SVG, no npm package needed — matches existing icon pattern [VERIFIED: github.com/tailwindlabs/heroicons] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `Date.getUTC*()` | `Intl.DateTimeFormat` with `timeZone:'UTC'` | Both work; `getUTC*()` is more readable for this simple HHMMSS case; explicit about UTC [ASSUMED] |
| `<button type="button">` padlock | `<span onclick>` | `<button>` is accessible (keyboard focusable, ARIA role), matches D-04 decision |
| localStorage | sessionStorage | localStorage persists across page loads/sessions — correct for a preference [VERIFIED: MDN] |

---

## Architecture Patterns

### System Architecture Diagram

```
Page load
  └─► initDateTime()
        ├─► QSO_DATE.value = today UTC (YYYYMMDD), readOnly=true, locked CSS
        ├─► TIME_ON.value  = now UTC  (HHMMSS),    readOnly=true, locked CSS
        └─► timeInterval = setInterval(updateTimeClock, 1000)

Padlock click (date)
  ├─► if locked: readOnly=false, open-icon, clear locked CSS, no interval change
  └─► if unlocked: readOnly=true, closed-icon, apply locked CSS, restore current UTC date

Padlock click (time)
  ├─► if locked: clearInterval(timeInterval), readOnly=false, open-icon, clear locked CSS
  └─► if unlocked: readOnly=true, closed-icon, apply locked CSS,
                   timeInterval = setInterval(updateTimeClock, 1000)

keydown Enter on input → htmx.trigger(form, 'submit')

htmx:beforeRequest
  ├─► 1. HHMM normalization on TIME_ON (^\d{4}$ → append "00")
  ├─► 2. submitAttempted = true
  └─► 3. if !validate() → e.preventDefault()

validate()
  ├─► Skip locked fields (readOnly === true)
  └─► Apply rules: CALL (non-empty), QSO_DATE (^\d{8}$), TIME_ON (^\d{6}$), BAND, MODE

htmx:afterSwap (target === #qso-result, result has .success-msg)
  ├─► branch: localStorage.getItem('ollog.resetMode') !== 'keep'  [DEFAULT]
  │     ├─► form.reset()
  │     ├─► initDateTime()   ← re-populates + re-locks + restarts interval
  │     ├─► clearErrors()
  │     ├─► submitAttempted = false
  │     └─► CALL.focus()
  └─► branch: resetMode === 'keep'
        ├─► (no form.reset, no initDateTime)
        ├─► clearErrors()
        ├─► submitAttempted = false
        └─► CALL.focus()

form 'reset' event (Clear button / type=reset)
  └─► initDateTime()   ← re-populates after native reset clears auto-populated fields

Toggle switch (hidden checkbox #reset-mode-toggle)
  ├─► change event → localStorage.setItem('ollog.resetMode', checked ? 'reset' : 'keep')
  └─► on page load: restore checkbox state from localStorage
```

### Recommended Project Structure

```
templates/log/
└── form.html    ← only file modified; all new JS in the existing <script> IIFE
```

### Pattern 1: UTC Clock with setInterval

**What:** On load, populate QSO_DATE and TIME_ON with current UTC values and set the TIME_ON interval to update every second.

**When to use:** Page load and after every "Reset to live UTC" post-submit.

```javascript
// Source: CONTEXT.md D-08, REQUIREMENTS.md TIME-01, TIME-02
// All Date methods must be getUTC* variants — never getHours/getDate etc.
var timeInterval = null;

function pad2(n) { return n < 10 ? '0' + n : '' + n; }

function getUTCDate() {
  var d = new Date();
  return '' + d.getUTCFullYear() + pad2(d.getUTCMonth() + 1) + pad2(d.getUTCDate());
}

function getUTCTime() {
  var d = new Date();
  return pad2(d.getUTCHours()) + pad2(d.getUTCMinutes()) + pad2(d.getUTCSeconds());
}

function initDateTime() {
  var dateEl = field('QSO_DATE');
  var timeEl = field('TIME_ON');

  // Stop any existing interval before starting a new one
  if (timeInterval) { clearInterval(timeInterval); timeInterval = null; }

  dateEl.value = getUTCDate();
  dateEl.readOnly = true;
  applyLockedStyle(dateEl);

  timeEl.value = getUTCTime();
  timeEl.readOnly = true;
  applyLockedStyle(timeEl);

  timeInterval = setInterval(function () {
    if (timeEl.readOnly) { timeEl.value = getUTCTime(); }
  }, 1000);
}
```

### Pattern 2: Padlock Toggle

**What:** `<button type="button">` next to the input field toggles `.readOnly`, swaps the icon SVG, and applies/removes locked CSS classes.

**When to use:** DATE-03 and TIME-03 requirements.

```html
<!-- Source: CONTEXT.md D-04, D-05 -->
<div class="relative">
  <input type="text" name="QSO_DATE" id="qso-date-input"
         placeholder="YYYYMMDD" required autocomplete="off"
         class="form-input font-mono pr-9 bg-gray-50 dark:bg-gray-800/50 cursor-not-allowed">
  <button type="button" id="qso-date-lock"
          onclick="toggleDateLock()"
          class="absolute inset-y-0 right-0 flex items-center pr-2.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
    <!-- Swap between lock-closed (locked) and lock-open (unlocked) SVGs via JS -->
    <svg id="qso-date-lock-icon" class="w-4 h-4" fill="none" viewBox="0 0 24 24"
         stroke-width="1.5" stroke="currentColor">
      <!-- lock-closed path rendered by default -->
    </svg>
  </button>
</div>
```

```javascript
// Source: CONTEXT.md D-06
function applyLockedStyle(el) {
  el.classList.add('bg-gray-50', 'dark:bg-gray-800/50', 'cursor-not-allowed');
  el.classList.remove('bg-white', 'dark:bg-gray-800');
}
function removeLockedStyle(el) {
  el.classList.remove('bg-gray-50', 'dark:bg-gray-800/50', 'cursor-not-allowed');
}
```

**CRITICAL:** `dark:bg-gray-800/50` and `cursor-not-allowed` must appear as complete literal strings in `form.html` for Tailwind purge. Run `npm run build` + `npm run verify` after adding.

### Pattern 3: HHMM Normalization Before HTMX Request

**What:** Prepend normalization to the existing `htmx:beforeRequest` handler before `validate()`.

**When to use:** TIME-04 requirement — 4-digit entries must be padded before validation and POST.

```javascript
// Source: CONTEXT.md D-10
form.addEventListener('htmx:beforeRequest', function (e) {
  // Step 1: normalize HHMM → HHMM00
  var timeEl = field('TIME_ON');
  if (timeEl && /^\d{4}$/.test(timeEl.value.trim())) {
    timeEl.value = timeEl.value.trim() + '00';
  }

  // Step 2: gate behind validation (existing logic)
  submitAttempted = true;
  if (!validate()) {
    e.preventDefault();
  }
});
```

### Pattern 4: Tailwind Toggle Switch (hidden checkbox + label)

**What:** A pill-shaped toggle built from `<input type="checkbox" class="sr-only peer">` and a `<label>` using Tailwind's `peer-checked:` variant.

**When to use:** RESET-01 — no new CSS class needed, no `input.css` changes.

```html
<!-- Source: CONTEXT.md D-01, D-02 -->
<!-- Tailwind v3 peer-checked pattern — all classes must be literal strings for purge -->
<div class="flex items-center gap-2">
  <input type="checkbox" id="reset-mode-toggle" class="sr-only peer">
  <label for="reset-mode-toggle"
         class="relative inline-flex items-center cursor-pointer
                w-9 h-5 bg-gray-300 dark:bg-gray-600 rounded-full
                peer-checked:bg-indigo-500
                after:content-[''] after:absolute after:top-0.5 after:left-0.5
                after:bg-white after:rounded-full after:h-4 after:w-4
                after:transition-all
                peer-checked:after:translate-x-4">
  </label>
  <span class="text-xs text-gray-500 dark:text-gray-400" id="reset-mode-label">
    Reset to live UTC
  </span>
</div>
```

```javascript
// Source: CONTEXT.md D-03; localStorage key ollog.resetMode
(function initResetToggle() {
  var toggle = document.getElementById('reset-mode-toggle');
  var label  = document.getElementById('reset-mode-label');
  // Default: checked = reset mode (ON)
  var saved = localStorage.getItem('ollog.resetMode');
  toggle.checked = (saved !== 'keep'); // default ON when not set
  label.textContent = toggle.checked ? 'Reset to live UTC' : 'Keep current date/time';

  toggle.addEventListener('change', function () {
    if (toggle.checked) {
      localStorage.setItem('ollog.resetMode', 'reset');
      label.textContent = 'Reset to live UTC';
    } else {
      localStorage.setItem('ollog.resetMode', 'keep');
      label.textContent = 'Keep current date/time';
    }
  });
})();
```

### Pattern 5: Post-Submit Branching in htmx:afterSwap

**What:** The existing `htmx:afterSwap` handler is replaced with a branched version that checks `localStorage.getItem('ollog.resetMode')`.

```javascript
// Source: CONTEXT.md D-07, D-08, D-09
document.body.addEventListener('htmx:afterSwap', function (e) {
  if (!e.detail.target || e.detail.target.id !== 'qso-result') return;
  var result = document.getElementById('qso-result');
  if (result && result.querySelector('.success-msg')) {
    var mode = localStorage.getItem('ollog.resetMode');
    if (mode !== 'keep') {
      // "Reset to live UTC" (default)
      form.reset();
      initDateTime();  // re-populate + re-lock + restart interval
    }
    // Both modes: clear errors, reset attempt flag, focus CALL
    clearErrors();
    submitAttempted = false;
    var callField = form.querySelector('[name="CALL"]');
    if (callField) callField.focus();
  }
});
```

### Pattern 6: Clear Button → Re-initialize DateTime

**What:** The native `reset` event fires when the user clicks the `<button type="reset">` (Clear). Since `form.reset()` clears auto-populated fields, a `reset` listener must call `initDateTime()`.

```javascript
// Source: CONTEXT.md code_context / specifics
form.addEventListener('reset', function () {
  // form.reset() already ran; now re-apply UTC defaults and locked state
  setTimeout(function () { initDateTime(); }, 0);
  // setTimeout(0) defers until after the browser's native reset completes
});
```

**Note:** The `setTimeout(0)` deferral is needed because the `reset` event fires synchronously before the browser applies `form.reset()` when `type="reset"` button is clicked. Without it, `initDateTime()` sets the value and then `form.reset()` clears it.

Actually — re-checking: `reset` event fires AFTER the browser clears fields for `type="reset"` button. The deferral is NOT required for `form.addEventListener('reset', ...)`. But it is safe to include as a no-op guard. [ASSUMED — verify with in-browser test]

### Anti-Patterns to Avoid

- **Using `disabled` instead of `readOnly`:** `disabled` silently drops the field value from the POST body. Always use `.readOnly = true` / `.readOnly = false`. [VERIFIED: CONTEXT.md specifics, STATE.md]
- **Using `getHours()` / `getDate()` / `getMonth()`:** These return local timezone values. Every UTC access must use `getUTCHours()`, `getUTCDate()`, `getUTCMonth()`, `getUTCFullYear()`, `getUTCSeconds()`. [VERIFIED: CONTEXT.md specifics]
- **Changing `hx-target` to the form or an ancestor:** Destroys form DOM, event listeners, and `setInterval`. `hx-target="#qso-result"` must remain a sibling. [VERIFIED: STATE.md]
- **Adding new CSS classes in `input.css` for the toggle:** D-01 locks the decision to inline Tailwind utilities in `form.html`.
- **Forgetting Tailwind purge for new `dark:` classes:** Classes like `dark:bg-gray-800/50` must appear as complete literal strings in a scanned `.html` file. Run `npm run build` + `npm run verify` after any template change.
- **Using `form.dispatchEvent(new Event('reset'))` to trigger clear:** This would cause double-init if the Clear button already fires the reset event. Only call `initDateTime()` from the `form reset` event listener, not manually.
- **Validating locked fields:** When `readOnly === true`, the field's value is managed by JS and is always valid format. The validate() function must skip locked fields to avoid false error states (D-12).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UTC time formatting | Custom date-to-string function beyond simple pad2 | `Date.getUTC*()` + a minimal `pad2()` helper | No library needed; scope is HHMMSS only |
| Toggle switch UI | New `@layer components` CSS class | Inline Tailwind `peer-checked:` utilities | D-01 locks this; no `input.css` changes |
| Icon assets | Custom SVG or icon font | Heroicons outline 24px inline SVG | Matches existing icon style; no extra HTTP request |
| localStorage wrapper | Abstraction layer | Direct `localStorage.getItem/setItem` | Single key; abstraction is unnecessary complexity |

**Key insight:** This is a narrow in-template JS feature. The existing validation framework, HTMX hooks, and `setInterval`/`localStorage` browser APIs cover all requirements without additional libraries.

---

## Common Pitfalls

### Pitfall 1: `setInterval` Leaking Across Resets

**What goes wrong:** If `initDateTime()` is called without clearing the previous interval, multiple intervals run concurrently — TIME_ON flickers or updates twice per second; intervals pile up across every post-submit reset.

**Why it happens:** `initDateTime()` is called from `htmx:afterSwap` (potentially many times per session); without clearing first, each call creates a new interval.

**How to avoid:** Store the interval id in a module-scoped variable (`var timeInterval = null`). At the start of `initDateTime()`, call `if (timeInterval) { clearInterval(timeInterval); timeInterval = null; }` before `setInterval`. [VERIFIED: standard JS pattern]

**Warning signs:** TIME_ON updates inconsistently or jumps by multiple seconds per displayed second.

### Pitfall 2: `form.reset()` Clearing Auto-Populated Fields

**What goes wrong:** Calling `form.reset()` in the "Reset to live UTC" branch clears QSO_DATE and TIME_ON back to empty (their initial HTML `value` attribute is empty). If `initDateTime()` is not called immediately after, the fields appear blank.

**Why it happens:** `form.reset()` restores fields to their HTML-attribute defaults, not to JS-assigned values.

**How to avoid:** Always call `initDateTime()` immediately after `form.reset()` in the "Reset to live UTC" branch. [VERIFIED: CONTEXT.md code_context]

**Warning signs:** Date/Time fields show empty after a successful QSO log in "Reset" mode.

### Pitfall 3: Tailwind Purge Removing `dark:bg-gray-800/50`

**What goes wrong:** New `dark:` modifier classes that don't appear anywhere as complete literal strings in scanned template files get purged from `output.css`. The locked-field visual state silently fails in dark mode.

**Why it happens:** Tailwind 3 (JIT) only generates classes for exact string matches found in `content` scan paths. Dynamic string construction (`'dark:bg-' + 'gray-800/50'`) is not recognized.

**How to avoid:** Write every complete class string as a literal in the template HTML. After editing `form.html`, always run `npm run build` then `grep 'bg-gray-800' static/css/output.css` to confirm the class was emitted. [VERIFIED: CLAUDE.md, STATE.md]

**Warning signs:** Locked field has no visual distinction in dark mode.

### Pitfall 4: `reset` Event Timing with `type="reset"` Button

**What goes wrong:** If `initDateTime()` is called before the browser applies the native reset, the date/time values get set and then immediately cleared by the reset.

**Why it happens:** The `reset` event fires when the user clicks `<button type="reset">`. The browser processes the reset synchronously after the event handler returns — so a synchronous call to `initDateTime()` in the handler runs before the browser's own clear.

**How to avoid:** Use `setTimeout(function() { initDateTime(); }, 0)` in the form `reset` event listener. This defers `initDateTime()` until the browser completes its native reset. [ASSUMED — verify with in-browser test in the Clear button path]

**Warning signs:** After clicking "Clear", QSO_DATE / TIME_ON fields are blank instead of showing UTC defaults.

### Pitfall 5: Locked Fields Showing Validation Errors on Submit

**What goes wrong:** On submit, `validate()` runs all rules including `QSO_DATE` and `TIME_ON`. If the field is locked (readOnly=true), the value is managed by JS and is guaranteed valid — but if the user previously cleared and re-locked, `form.reset()` may have temporarily set the value to empty before `initDateTime()` re-populated it. If any timing gap exists, validation runs against an empty value and flags the field.

**Why it happens:** Race condition between `form.reset()` → empty value → `initDateTime()` → valid value when validation fires in `htmx:beforeRequest`.

**How to avoid:** D-12 — the `validate()` function must skip locked fields entirely (`if (el.readOnly) return; // always valid`). [VERIFIED: CONTEXT.md D-12]

**Warning signs:** QSO_DATE or TIME_ON show red error ring even though they display valid UTC values.

---

## Code Examples

### Heroicons: Lock-Closed (24px outline)

```html
<!-- Source: https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/lock-closed.svg -->
<!-- Render at w-4 h-4 per CONTEXT.md D-05 -->
<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
  <path stroke-linecap="round" stroke-linejoin="round"
        d="M16.5 10.5V6.75C16.5 4.26472 14.4853 2.25 12 2.25C9.51472 2.25 7.5 4.26472 7.5 6.75V10.5M6.75 21.75H17.25C18.4926 21.75 19.5 20.7426 19.5 19.5V12.75C19.5 11.5074 18.4926 10.5 17.25 10.5H6.75C5.50736 10.5 4.5 11.5074 4.5 12.75V19.5C4.5 20.7426 5.50736 21.75 6.75 21.75Z" />
</svg>
```

### Heroicons: Lock-Open (24px outline)

```html
<!-- Source: https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/lock-open.svg -->
<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
  <path stroke-linecap="round" stroke-linejoin="round"
        d="M13.5 10.5V6.75C13.5 4.26472 15.5147 2.25 18 2.25C20.4853 2.25 22.5 4.26472 22.5 6.75V10.5M3.75 21.75H14.25C15.4926 21.75 16.5 20.7426 16.5 19.5V12.75C16.5 11.5074 15.4926 10.5 14.25 10.5H3.75C2.50736 10.5 1.5 11.5074 1.5 12.75V19.5C1.5 20.7426 2.50736 21.75 3.75 21.75Z" />
</svg>
```

### Updated TIME_ON Validation Rule

```javascript
// Source: CONTEXT.md D-10 — after normalization, TIME_ON is always 6 digits
var rules = {
  CALL:     function (v) { return v.trim().length > 0; },
  QSO_DATE: function (v) { return /^\d{8}$/.test(v.trim()); },
  TIME_ON:  function (v) { return /^\d{6}$/.test(v.trim()); },  // was /^\d{4}$/
  BAND:     function (v) { return v.trim().length > 0; },
  MODE:     function (v) { return v.trim().length > 0; },
};
```

### Updated validate() to Skip Locked Fields

```javascript
// Source: CONTEXT.md D-12
function validate() {
  var ok = true;
  Object.keys(rules).forEach(function (name) {
    var el = field(name);
    if (!el) return;
    if (el.readOnly) { setError(el, false); return; } // locked = always valid
    var valid = rules[name](el.value);
    setError(el, !valid);
    if (!valid) ok = false;
  });
  return ok;
}
```

### Existing Tailwind Color References (Dark Mode Palette)

From `input.css` inspection — color choices to follow for new classes:
- Focused/active: `indigo-500`, `indigo-600`
- Muted/locked bg light: `gray-50`
- Muted/locked bg dark: `gray-800/50` (translucent)
- Border default: `gray-300` / `gray-600`
- Text muted: `gray-400` / `gray-500`
- Toggle pill off: `gray-300` / `gray-600`
- Toggle thumb: `white` (after:bg-white)

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `<input type="time">` | Manual text input + JS clock | By design from project start | Avoids browser local-time conversion in type="time" inputs |
| Custom date/time pickers | `Date.getUTC*()` + setInterval | By design | No dependency; simpler; correct UTC behavior |

**Deprecated/outdated:**
- `TIME_ON` regex `/^\d{4}$/`: replaced by `/^\d{6}$/` after Phase 53. The old regex existed because the server previously accepted HHMM; after Phase 52 normalization is in place, 6 digits is canonical.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `reset` event fires AFTER browser applies native reset (so `initDateTime()` can be called synchronously in the listener, without setTimeout) | Patterns - Anti-Patterns, Pitfall 4 | If wrong: Clear button leaves fields blank. Mitigation: use `setTimeout(0)` defensively as noted in Pitfall 4 |
| A2 | `peer-checked:` + `after:` Tailwind utilities for toggle switch work correctly in Tailwind 3.4.x without additional plugins | Standard Stack, Pattern 4 | If wrong: toggle switch renders incorrectly. Mitigation: validate with `npm run build` + visual check |

---

## Open Questions

1. **`reset` event timing (A1 above)**
   - What we know: `form.reset()` called programmatically in htmx:afterSwap works fine because we call `initDateTime()` immediately after. The question is only about the Clear button's native reset event.
   - What's unclear: Whether the `reset` event listener runs before or after the browser clears field values in the button-click path.
   - Recommendation: Use `setTimeout(0)` defensively in the `reset` event listener for the Clear button. Zero cost if unnecessary, prevents blank-field bug if needed.

---

## Environment Availability

Step 2.6: SKIPPED — phase is a single-file frontend template change. External dependencies are the existing browser APIs (`Date`, `localStorage`, `setInterval`) and the already-installed Tailwind CSS + HTMX stack. No new runtimes, databases, or CLI tools required beyond the already-verified build chain.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend); manual browser verification (frontend) |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/` |
| Frontend build | `npm run build && npm run verify` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Notes |
|--------|----------|-----------|-------------------|-------|
| DATE-01 | Date field pre-filled with UTC date on load | Manual browser | — | JavaScript/DOM; no pytest hook |
| DATE-02 | Date field readonly by default | Manual browser | — | DOM attribute check |
| DATE-03 | Padlock toggles readonly on date | Manual browser | — | UI interaction |
| DATE-04 | Invalid date rejected with inline feedback | Manual browser | — | Client-side validation |
| TIME-01 | Time field pre-filled with UTC HHMMSS on load | Manual browser | — | JavaScript/DOM |
| TIME-02 | Time field auto-updates every second | Manual browser | — | Real-time behavior |
| TIME-03 | Padlock toggles auto-update on time | Manual browser | — | UI interaction |
| TIME-04 | HHMM normalized to HHMM00 before submit | Manual browser (network tab) | — | Verify POST body |
| TIME-05 | Invalid time rejected with inline feedback | Manual browser | — | Client-side validation |
| RESET-01 | Toggle present in submit row | Manual browser | — | DOM check |
| RESET-02 | "Keep current" preserves fields after submit | Manual browser | — | Post-submit state |
| RESET-03 | "Reset to live UTC" re-locks fields after submit | Manual browser | — | Post-submit state |

All phase requirements are pure frontend JavaScript/DOM behaviors. They are not testable with pytest. The existing backend test suite (`uv run pytest tests/ -x -q`) must remain green as a regression guard; no new pytest tests are required for this phase.

### Sampling Rate

- **Per task commit:** `npm run build && npm run verify` (confirms dark: classes emitted)
- **Per wave merge:** `uv run pytest tests/ -x -q` (backend regression guard)
- **Phase gate:** Full suite green + manual browser walkthrough of all 7 success criteria

### Wave 0 Gaps

None — no new test files required. Frontend behavior is verified manually per the success criteria checklist in the phase description.

---

## Security Domain

Phase 53 introduces no new authentication, session management, access control, cryptographic operations, or server-side input handling. All changes are client-side JavaScript in a template. The server-side `TIME_ON` validation (DB-02) was addressed in Phase 52.

ASVS categories not applicable: V2 (Authentication), V3 (Session Management), V4 (Access Control), V6 (Cryptography).

V5 (Input Validation): The HHMM→HHMM00 normalization and 6-digit regex validation occur client-side. The server already accepts both HHMM and HHMMSS (DB-02, Phase 52). No new server-side validation surface is introduced.

---

## Project Constraints (from CLAUDE.md)

- **`readonly` not `disabled`:** `disabled` silently drops `QSO_DATE`/`TIME_ON` from POST body. Always use `.readOnly = true/false`.
- **`Date.getUTC*()` exclusively:** Never `getHours()`, `getDate()`, etc. — local timezone leakage.
- **Tailwind `dark:` class purge:** Complete literal strings must appear in scanned `.html` files. Run `npm run build` + `npm run verify` after adding new dark: classes.
- **FOUC prevention IIFE in `base.html`:** Load-bearing — do not touch, defer, or extract.
- **No new dependencies:** Phase is browser-native JS + existing HTMX + existing Tailwind.
- **`hx-target="#qso-result"` must remain a sibling div:** Changing target to form or an ancestor destroys form DOM and all attached timers.
- **APScheduler pyproject.toml constraint:** Unrelated to this phase — do not touch.
- **Tailwind v3:** `peer-checked:` and `after:` variants are supported without plugins.

---

## Sources

### Primary (HIGH confidence)

- `templates/log/form.html` [VERIFIED: codebase] — existing HTMX hooks, validation object, `htmx:afterSwap` handler
- `static/css/input.css` [VERIFIED: codebase] — `form-input`, `form-input-error`, color palette
- `tailwind.config.js` [VERIFIED: codebase] — `content: ['./templates/**/*.html']`, `darkMode: 'class'`
- `.planning/phases/53-live-clock-lock-unlock-and-post-submit-behavior/53-CONTEXT.md` [VERIFIED: codebase] — all 12 decisions
- `.planning/REQUIREMENTS.md` [VERIFIED: codebase] — exact acceptance criteria for all 12 requirements
- `.planning/STATE.md` [VERIFIED: codebase] — accumulated v2.7 critical pitfalls

### Secondary (MEDIUM confidence)

- `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/lock-closed.svg` [VERIFIED: WebFetch] — exact `<path>` data
- `https://raw.githubusercontent.com/tailwindlabs/heroicons/master/src/24/outline/lock-open.svg` [VERIFIED: WebFetch] — exact `<path>` data

### Tertiary (LOW confidence)

- `reset` event timing behavior (A1) — [ASSUMED] based on JS spec knowledge; needs in-browser verification

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; no new deps
- Architecture: HIGH — single file, all hooks exist, decisions are locked
- Pitfalls: HIGH — sourced from CLAUDE.md, CONTEXT.md, STATE.md; one LOW item (reset timing)
- Heroicon SVG paths: HIGH — fetched directly from official source

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable browser APIs; Tailwind 3.4.x)
