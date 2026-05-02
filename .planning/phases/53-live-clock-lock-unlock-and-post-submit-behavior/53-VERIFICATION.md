---
phase: 53-live-clock-lock-unlock-and-post-submit-behavior
verified: 2026-05-01T20:15:00Z
status: human_needed
score: 7/7
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/7
  gaps_closed:
    - "With Reset to live UTC selected, after a successful QSO submit both fields return to locked state with refreshed UTC values and a restarted clock — initDateTime() now calls setLockIcon() and resets aria-labels for both padlocks"
    - "Entering an invalid time (e.g. 9999) into an unlocked field is rejected with visible inline feedback — TIME_ON validation rule updated to /^([01]\\d|2[0-3])([0-5]\\d)([0-5]\\d)$/, which rejects 9999→999900 (hours=99 out of range)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "RESET-03: Verify padlock icons return to closed state after 'Reset to live UTC' submit"
    expected: "After unlocking the time field, submitting a QSO with 'Reset to live UTC' selected, both the time and date padlock icons should show CLOSED lock state and aria-label should read 'Lock time field' / 'Lock date field' respectively."
    why_human: "SVG path state and aria-label reset after post-submit initDateTime() call can only be confirmed in a live browser session."
  - test: "SC-5 / TIME-05: Verify '9999' is now rejected client-side with inline feedback"
    expected: "With the time field unlocked, type '9999' and click Log QSO. A red error ring should appear around the time field and no HTMX POST should fire. '9999' normalizes to '999900' which fails /^([01]\\d|2[0-3])([0-5]\\d)([0-5]\\d)$/ (hours=99 invalid), so the regex rejects it."
    why_human: "Requires running the app in a browser to confirm the inline error ring appears and that the Network tab shows no POST."
---

# Phase 53: Live Clock, Lock/Unlock, and Post-Submit Behavior — Verification Report

**Phase Goal:** The Log QSO form displays live UTC date and time by default with lock/unlock controls, normalizes 4-digit time input to HHMMSS before submission, and restores the correct field state after each submission based on the operator's chosen reset behavior.
**Verified:** 2026-05-01T20:15:00Z
**Status:** human_needed
**Re-verification:** Yes — after two inline gap fixes

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | On page load, QSO_DATE displays today's UTC date in YYYYMMDD format and TIME_ON displays current UTC time in HHMMSS format | VERIFIED | `initDateTime()` calls `currentUTCDate()` and `currentUTCTime()` using `getUTC*` methods exclusively; both fields populated on the `initDateTime()` call at the IIFE bottom (line 451). Zero occurrences of `.getHours()`, `.getMinutes()`, etc. |
| 2 | While TIME_ON is locked, its displayed value increments every second using getUTC* methods exclusively | VERIFIED | `setInterval` in `initDateTime()` (lines 270-275) calls `currentUTCTime()` which uses `getUTCHours()`, `getUTCMinutes()`, `getUTCSeconds()`. Zero local-time accessors confirmed. The interval guard checks `timeEl.readOnly` before updating. |
| 3 | Clicking the date padlock toggles QSO_DATE.readOnly, swaps the SVG between lock-closed and lock-open paths, updates aria-label, and adds/removes the locked-state Tailwind classes | VERIFIED | Date padlock click handler (lines 319-342) toggles `readOnly`, calls `removeLockedStyle/applyLockedStyle`, calls `setLockIcon(dateLockIcon, false/true)`, sets `aria-label` to all four expected values. Both Heroicons paths verified (`LOCK_CLOSED_D` starts `M16.5 10.5V6.75`, `LOCK_OPEN_D` starts `M13.5 10.5V6.75`). |
| 4 | Clicking the time padlock additionally clears or restarts the setInterval | VERIFIED | Time padlock click handler (lines 345-373): unlock branch calls `clearInterval(timeInterval); timeInterval = null;`; re-lock branch calls `setInterval(...)` to restart. |
| 5 | With Keep current date/time selected, after a successful QSO submit field values, lock state, and setInterval are unchanged; only validation errors and submitAttempted flag are cleared and CALL is focused | VERIFIED | `htmx:afterSwap` handler: `if (mode !== 'keep')` block containing `form.reset()` is skipped; `clearErrors()`, `submitAttempted = false`, `callField.value = ''`, `callField.focus()` run in both branches. The `setInterval` is not touched in the keep-mode path. |
| 6 | With Reset to live UTC selected, after a successful QSO submit both fields return to locked state with refreshed UTC values and a restarted clock | VERIFIED | **Gap 1 closed.** `initDateTime()` (lines 262-268) now calls `setLockIcon(document.getElementById('qso-date-lock-icon'), true)`, `setLockIcon(document.getElementById('qso-time-lock-icon'), true)`, sets both buttons' `aria-label` to `'Lock date field'` / `'Lock time field'`, in addition to the existing `readOnly=true`, `applyLockedStyle()`, and `setInterval` restart. Both icons and aria-labels are reset on every `initDateTime()` call. |
| 7 | Entering an invalid date or invalid time (e.g. 9999) into an unlocked field is rejected with visible inline feedback before the form submits | VERIFIED | **Gap 2 closed.** `TIME_ON` rule updated from `/^\d{6}$/` to `/^([01]\d|2[0-3])([0-5]\d)([0-5]\d)$/` (line 213). `9999` normalizes to `999900` via the HHMM→HHMM00 normalization in `htmx:beforeRequest`; `999900` has hours=99 which fails `([01]\d\|2[0-3])`, so validation rejects it with a `.form-input-error` ring and `e.preventDefault()`. Tested: `9999`→`999900` FAIL; `1430`→`143000` PASS; `2359`→`235900` PASS; `9900`→`990000` FAIL. |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `templates/log/form.html` | Padlock-wrapped QSO_DATE/TIME_ON inputs + reset-mode toggle UI | VERIFIED | `id="qso-date-input"`, `id="qso-time-input"`, `id="qso-date-lock"`, `id="qso-time-lock"` each appear exactly once; `id="reset-mode-toggle"` and `id="reset-mode-label"` present; `readonly` attribute on both inputs; `dark:bg-gray-800/50` and `cursor-not-allowed` present. |
| `templates/log/form.html` | Reset-mode toggle widget | VERIFIED | `id="reset-mode-toggle"` present; `class="sr-only peer" checked` confirmed; `>Reset to live UTC<` present; `peer-checked:bg-indigo-500` present. |
| `templates/log/form.html` | JavaScript behavior for live UTC clock, padlock toggles, HHMM normalization, validation, post-submit reset branching, localStorage persistence | VERIFIED | `function initDateTime` found; `function initResetToggle` found; all padlock handlers present with icon+aria reset in initDateTime body. |
| `templates/log/form.html` | Updated TIME_ON validation regex and locked-field skip in validate() | VERIFIED | `TIME_ON: function (v) { return /^([01]\d|2[0-3])([0-5]\d)([0-5]\d)$/.test(v.trim()); }` confirmed at line 213 (range-checking regex, not just digit count); `if (el.readOnly) { setError(el, false); return; }` present in `validate()`. |
| `templates/log/form.html` | HHMM->HHMM00 normalization in htmx:beforeRequest before validate | VERIFIED | `/^\d{4}$/.test(timeEl.value.trim())` + `timeEl.value.trim() + '00'` at lines 428-429; runs before `validate()`. |
| `templates/log/form.html` | localStorage-backed reset-mode branching in htmx:afterSwap | VERIFIED | `localStorage.getItem('ollog.resetMode')` appears exactly twice (toggle init + afterSwap); `if (mode !== 'keep')` branching confirmed. |
| `static/css/output.css` | Compiled Tailwind classes for new locked-state and toggle utilities | VERIFIED | `bg-gray-50`, `bg-gray-800`, `cursor-not-allowed`, `sr-only`, `peer-checked`, `translate-x-4`, `pr-9` all confirmed present in previous verification; no new Tailwind classes added in the gap fixes (JS-only changes). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `initDateTime()` | `setInterval(updateTimeClock, 1000)` | `timeInterval` module-scoped var + clearInterval guard | VERIFIED | `clearInterval(timeInterval); timeInterval = null;` guard at top of `initDateTime()`; `setInterval` call present with `timeEl.readOnly` guard in callback. |
| `initDateTime()` | SVG icon + aria-label reset on both padlocks | Direct `getElementById` + `setLockIcon()` + `setAttribute` | VERIFIED (new) | Lines 263-268 call `setLockIcon(...)` with `locked=true` on both icons and `setAttribute('aria-label', 'Lock date/time field')` on both buttons — added by Gap 1 fix. |
| `htmx:beforeRequest` handler | TIME_ON value normalization | regex `/^\d{4}$/` test, append `'00'` | VERIFIED | `if (timeEl && !timeEl.readOnly && /^\d{4}$/.test(timeEl.value.trim()))` at line 428; append `'00'` at line 429, before `validate()`. |
| TIME_ON validation rule | Range check rejecting hours >23 / minutes >59 / seconds >59 | `/^([01]\d|2[0-3])([0-5]\d)([0-5]\d)$/` | VERIFIED (new) | Line 213; regex verified to reject `999900` (9999 normalized), `240000`, `126099`; accepts `000000`, `143000`, `235959`. |
| `htmx:afterSwap` handler | `form.reset()` + `initDateTime()` OR no-op | `localStorage.getItem('ollog.resetMode') !== 'keep'` | VERIFIED | `var mode = localStorage.getItem('ollog.resetMode')` + `if (mode !== 'keep') { form.reset(); }`. `initDateTime()` triggered via the `reset` event handler's `setTimeout(0)` chain. |
| `form.reset` event listener | `initDateTime()` | `setTimeout(fn, 0)` defensive deferral | VERIFIED | `form.addEventListener('reset', function () { setTimeout(function () { initDateTime(); }, 0); });` present. |
| Padlock click handlers | `QSO_DATE.readOnly` / `TIME_ON.readOnly` toggling + SVG path swap + aria-label update | `addEventListener('click', ...)` on `#qso-date-lock` and `#qso-time-lock` | VERIFIED | Both handlers present; all four aria-label values confirmed; `setLockIcon()` called on both lock/unlock paths. |
| `form.html` (toggle label) | `static/css/output.css` (`peer-checked:bg-indigo-500`) | Tailwind JIT class purge | VERIFIED | `peer-checked` present in `output.css`; full toggle class strings present in form.html as literal strings. |

### Data-Flow Trace (Level 4)

Not applicable — this phase delivers client-side JavaScript UI behavior, not server-rendered dynamic data. UTC time values come from `new Date()` in the browser; `localStorage` persistence writes and reads a single string. No server-side data flows into the new form elements.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| initDateTime() contains setLockIcon calls | `grep -n "setLockIcon\|aria-label\|dBtn\|tBtn" templates/log/form.html` (inside initDateTime body lines 262-268) | Lines 263-268: setLockIcon x2, dBtn/tBtn setAttribute x2 | PASS |
| 9999 rejected after normalization | `node -e "var re=/^([01]\\d\|2[0-3])([0-5]\\d)([0-5]\\d)\$/; console.log(re.test('999900'))"` | false | PASS |
| 1430 accepted after normalization | same regex test on '143000' | true | PASS |
| TIME_ON regex is range-checking (not just digit count) | `grep "TIME_ON.*function" templates/log/form.html` | `/^([01]\d\|2[0-3])([0-5]\d)([0-5]\d)$/` | PASS |
| No local-time accessor leak | `grep -cE '\.getHours\(\)\|\.getMinutes\(\)' templates/log/form.html` | 0 | PASS |
| No `disabled` attribute manipulation | `grep -cE '\.disabled\s*=' templates/log/form.html` | 0 | PASS |
| setInterval count correct | `grep -c 'setInterval' templates/log/form.html` | 2 (initDateTime + time re-lock handler) | PASS |
| clearInterval count correct | `grep -c 'clearInterval' templates/log/form.html` | 3 (initDateTime guard + unlock path + re-lock cleanup) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DATE-01 | 53-02 | Date field defaults to today's UTC date in `YYYYMMDD` on form load | SATISFIED | `initDateTime()` sets `dateEl.value = currentUTCDate()` using `getUTCFullYear/Month/Date` |
| DATE-02 | 53-01, 53-02 | Date field is `readonly` by default — value is included in form submission | SATISFIED | `readonly` HTML attribute on input (line 43); JS also sets `dateEl.readOnly = true` in `initDateTime()` |
| DATE-03 | 53-01, 53-02 | Lock icon button toggles between readonly and editable | SATISFIED | Padlock click handler verified; SVG swap and aria-label swap work; icon restored to closed by `initDateTime()` on reset path |
| DATE-04 | 53-02 | Manual date input validated against `YYYYMMDD`; invalid input rejected with feedback | SATISFIED | `QSO_DATE: function (v) { return /^\d{8}$/.test(v.trim()); }` + `.form-input-error` ring via `setError()` |
| TIME-01 | 53-02 | Time field defaults to current UTC time in `HHMMSS` on form load | SATISFIED | `initDateTime()` sets `timeEl.value = currentUTCTime()` using `getUTCHours/Minutes/Seconds` |
| TIME-02 | 53-02 | While locked, time field auto-updates every second via `setInterval` using `getUTC*()` | SATISFIED | `setInterval` in `initDateTime()` with `timeEl.readOnly` guard; zero local-time accessors |
| TIME-03 | 53-01, 53-02 | Lock icon button next to time field toggles auto-update and editable state | SATISFIED | Time padlock click handler: `clearInterval` on unlock, new `setInterval` on re-lock; icon and aria-label reset by `initDateTime()` on reset path |
| TIME-04 | 53-02 | `HHMM` (4 digits) accepted and normalized to `HHMM00` before submission | SATISFIED | Normalization in `htmx:beforeRequest` at lines 428-429 |
| TIME-05 | 53-02 | Invalid time formats rejected with visible feedback | SATISFIED | Range-checking regex `/^([01]\d\|2[0-3])([0-5]\d)([0-5]\d)$/` rejects `9999`→`999900` (hours=99 out of range), `abcd`, `12`, non-calendar-valid times like `9900`→`990000`. Pending browser confirmation (human item 2). |
| RESET-01 | 53-01, 53-02 | Toggle on Log QSO form controls post-submission behavior | SATISFIED | Toggle widget present; `initResetToggle()` wires `localStorage.setItem` on change; label updates correctly |
| RESET-02 | 53-02 | "Keep current date/time" — field values and lock/unlock state preserved after submission | SATISFIED | `htmx:afterSwap` skips `form.reset()` and `initDateTime()` in `keep` mode; only `clearErrors()`, `submitAttempted=false`, CALL clear+focus run |
| RESET-03 | 53-02 | "Reset to live UTC" — both fields return to locked state with live UTC after submission | SATISFIED | `initDateTime()` now resets SVG icons to lock-closed and restores aria-labels in addition to resetting readOnly and values. Pending browser confirmation (human item 1). |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `templates/log/form.html` | 208 | Stale comment: `// TIME: exactly 4 digits` — rule is now a range-checking regex | Info | Misleading to future readers; not a functional issue |

### Human Verification Required

#### 1. RESET-03 Icon Sync — Confirm Gap 1 Fix Works in Browser

**Test:** Run the app, open `/log/form`. Click the time padlock to unlock, click the date padlock to unlock (both should show open-lock icons). With "Reset to live UTC" selected, submit a valid QSO (fill CALL, BAND, MODE). After the success message swaps in, inspect both padlock buttons.
**Expected:** Both padlock icons show the CLOSED lock SVG. Both buttons have `aria-label="Lock date field"` and `aria-label="Lock time field"` respectively. Both fields are readonly with locked grey background. The time field shows current UTC and is ticking.
**Why human:** Requires running the app in a browser to confirm the visual state of SVG icons and DOM attribute values after the post-submit `initDateTime()` call.

#### 2. SC-5 / TIME-05 — Confirm '9999' Is Now Rejected Client-Side

**Test:** Run the app, open `/log/form`. Click the time padlock to unlock. Clear the time field and type `9999`. Click "Log QSO" (with any other required fields filled).
**Expected:** A red error ring appears around the time field and no HTMX POST is fired (Network tab shows no request to `/log/qsos`). The normalization converts `9999` to `999900`, the range-checking regex `/^([01]\d|2[0-3])([0-5]\d)([0-5]\d)$/` rejects `999900` because hours=99 is outside the `[01]\d|2[0-3]` range, `validate()` returns false, and `e.preventDefault()` blocks the POST.
**Why human:** Requires running the app in a browser to confirm the inline error ring appears and the Network tab shows no POST request.

### Gaps Summary

Both previously identified gaps are now closed by inline code changes:

**Gap 1 — CLOSED:** `initDateTime()` now calls `setLockIcon()` with `locked=true` on both padlock SVG elements and resets both button `aria-label` attributes to `'Lock date field'` / `'Lock time field'` (lines 262-268 in current `templates/log/form.html`). This ensures that when "Reset to live UTC" mode triggers `form.reset()` + `initDateTime()`, the padlock icons return to closed state exactly as on a fresh page load.

**Gap 2 — CLOSED:** The `TIME_ON` validation rule was updated from the simple digit-count regex `/^\d{6}$/` to a range-checking regex `/^([01]\d|2[0-3])([0-5]\d)([0-5]\d)$/` (line 213). After the HHMM normalization in `htmx:beforeRequest` transforms `9999` to `999900`, this regex rejects `999900` because the hours group `99` does not match `[01]\d|2[0-3]`. Tested programmatically: `9999`→`999900` fails; `1430`→`143000` passes; `2359`→`235900` passes; `9900`→`990000` fails.

**Remaining:** Two human browser verification items confirm the fixes work in a live browser session. All 7 observable truths pass code inspection — status is `human_needed`, not `gaps_found`.

**Stale comment** at line 208 (`// TIME: exactly 4 digits`) remains informational — the rule is now a range-checking regex. Not a functional gap.

---

_Verified: 2026-05-01T20:15:00Z_
_Verifier: Claude (gsd-verifier)_
