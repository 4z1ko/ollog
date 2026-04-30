---
phase: 53-live-clock-lock-unlock-and-post-submit-behavior
reviewed: 2026-04-29T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - templates/log/form.html
  - static/css/output.css
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 53: Code Review Report

**Reviewed:** 2026-04-29
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed the QSO log form template and compiled Tailwind CSS output for the live-clock lock/unlock and post-submit behavior feature. The implementation is well-structured with clear intent comments (D-06, D-12, TIME-01, RESET-01, etc.). No critical bugs or security issues were found. The live clock, padlock toggle, validation gate, HHMM normalization, and reset-mode toggle all function correctly.

One warning-level bug was identified: the `htmx:afterSwap` success handler in "reset" mode calls `initDateTime()` directly and also triggers a second call via the `reset` event listener's `setTimeout(0)`. Due to browser event ordering, the direct call is the effective one, but the `setTimeout`-deferred call executes afterward and restarts the `setInterval` unnecessarily. In practice the behavior is correct because `initDateTime()` is idempotent, but the double-call is an unintended side effect of the code structure.

Two info-level issues were found: a stale comment and a redundant field clear.

---

## Warnings

### WR-01: `initDateTime` called twice on successful submit in reset mode

**File:** `templates/log/form.html:368-370,438-439`

**Issue:** When a QSO is successfully submitted in "reset to live UTC" mode, `form.reset()` is called at line 438, which synchronously fires the `reset` event. The reset event listener (lines 368-370) queues `initDateTime()` via `setTimeout(0)`. Then `initDateTime()` is called directly at line 439. Browser event order means:

1. `form.reset()` fires `reset` event → `setTimeout(0, initDateTime)` queued
2. Browser applies native form reset (clears all field values)
3. `form.reset()` returns
4. `initDateTime()` called directly at line 439 — this is the effective call
5. `setTimeout` fires → `initDateTime()` called a second time, clearing the valid interval started in step 4 and creating a new one

The double-call is safe because `initDateTime()` is idempotent (it clears any prior interval before setting a new one). However, it creates a spurious extra interval registration 0–1 ms after the real one, and the intent is not clear to future readers. The direct call at line 439 already correctly runs after native reset completes, making the `reset`-event-triggered `setTimeout` path entirely redundant in this code path.

**Fix:** Call `initDateTime()` only once. Since the `form.reset()` call in the success handler is immediately followed by `initDateTime()`, suppress the re-init from the reset event in this case, or skip the direct `initDateTime()` call and let the `reset` event handler's `setTimeout` handle it (the latter was the original design):

```javascript
// Option A: remove the direct initDateTime() call and let the reset
// event handler's setTimeout do the work (consistent with Clear button path):
document.body.addEventListener('htmx:afterSwap', function (e) {
  if (!e.detail.target || e.detail.target.id !== 'qso-result') return;
  var result = document.getElementById('qso-result');
  if (result && result.querySelector('.success-msg')) {
    var mode = localStorage.getItem('ollog.resetMode');
    if (mode !== 'keep') {
      form.reset();
      // initDateTime() will be called by the reset event handler via setTimeout(0)
    }
    clearErrors();
    submitAttempted = false;
    var callField = form.querySelector('[name="CALL"]');
    if (callField) { callField.value = ''; callField.focus(); }
  }
});
```

---

## Info

### IN-01: Stale comment — TIME rule described as "4 digits" but rule requires 6

**File:** `templates/log/form.html:209`

**Issue:** The comment reads `TIME: exactly 4 digits`, but the actual validation rule at line 213 is `/^\d{6}$/` (6 digits). The HHMM→HHMMSS normalization in `htmx:beforeRequest` (lines 419-422) promotes a 4-digit entry to 6 before validation runs, so the rule is correct. The comment is outdated and misleading for future readers.

**Fix:**
```javascript
// CALL: any non-empty string; DATE: exactly 8 digits; TIME: exactly 6 digits (HHMMSS);
// HHMM (4 digits) is accepted and normalized to HHMMSS in htmx:beforeRequest before validation
```

### IN-02: Redundant CALL field clear in reset mode after `form.reset()`

**File:** `templates/log/form.html:445`

**Issue:** In the success handler's "reset to live UTC" branch, `form.reset()` is called at line 438 which already clears the CALL input to its empty default. The explicit `callField.value = ''` at line 445 clears it again. This is harmless but redundant.

**Fix:** The line can be removed since `form.reset()` already clears CALL:

```javascript
// Both modes: clear errors, reset attempt flag, focus CALL
clearErrors();
submitAttempted = false;
var callField = form.querySelector('[name="CALL"]');
if (callField) { callField.focus(); }  // value already cleared by form.reset()
```

Note: In "keep" mode (where `form.reset()` is skipped), the explicit `callField.value = ''` is necessary and must be retained. The redundancy only applies to the reset-mode branch.

---

_Reviewed: 2026-04-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
