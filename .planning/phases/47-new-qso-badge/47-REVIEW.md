---
phase: 47-new-qso-badge
reviewed: 2026-04-18T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - templates/log/log.html
  - static/css/output.css
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 47: Code Review Report

**Reviewed:** 2026-04-18
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Phase 47 adds a `#new-qso-badge` notification element alongside the HTMX SSE swap target `#log-table`. The overall approach is sound: the badge is a DOM sibling (not a child) of the swap target so it survives `innerHTML` swaps, and the sentinel pattern (`auto-refresh-ok`) correctly distinguishes page-1/no-filter state from paginated/filtered state.

Three warnings were found. Two are logic bugs in the `htmx:sseMessage` handler: (1) a redundant double-evaluation of `auto-refresh-ok` that conceals the intended mutual-exclusion structure and creates a subtle interaction order dependency, and (2) the OFFLINE indicator state left with stale emerald classes when the connection drops after having been live — the `htmx:sseError` handler never removes the LIVE color classes. One warning concerns `htmx:afterSettle` firing globally: it will dismiss the badge on any HTMX settle, not just SSE refreshes, which could silently dismiss a badge during a filter swap.

Two info items: `indicator.querySelector('span:last-child')` is brittle given the element's two child spans, and `NOTIFY_SOUND` is a template-rendered string constant compared with `=== 'true'` when a boolean template variable would be cleaner.

---

## Warnings

### WR-01: Duplicate `auto-refresh-ok` DOM query hides logic structure and is fragile

**File:** `templates/log/log.html:214-218`

**Issue:** The `auto-refresh-ok` guard is evaluated twice in sequence at lines 214 and 218:

```js
// line 214-217
if (!document.getElementById('auto-refresh-ok')) {
  newQsoCount++;
  updateBadge();
}
// line 218
if (!document.getElementById('auto-refresh-ok')) return;
```

These two `getElementById` calls are independent DOM queries. Any mutation between them (e.g., from a concurrent `htmx:afterSettle` triggered by a parallel request) could theoretically yield different results. More practically, the logic reads as two separate paths when the intent is a single branch: "if sentinel absent, badge and return; if sentinel present, refresh." The current form lets execution fall through to `updateBadge()` on line 216 and *also* continue to line 219 in the same event tick if the sentinel appears between the two queries — an impossible scenario in single-threaded JS but obscures intent and makes the code harder to audit.

**Fix:** Collapse into one query and use a clear if/else:

```js
var canAutoRefresh = !!document.getElementById('auto-refresh-ok');
if (!canAutoRefresh) {
  newQsoCount++;
  updateBadge();
  return;
}
if (document.querySelector('#log-table input')) return;
htmx.ajax('GET', '/log/view', { target: '#log-table', swap: 'innerHTML' });
```

---

### WR-02: `htmx:sseError` leaves stale LIVE color classes on the indicator

**File:** `templates/log/log.html:223-229`

**Issue:** The `htmx:sseError` handler shows the indicator and sets the text to `'OFFLINE'` but never removes the emerald (LIVE) background and text color classes that the `htmx:sseMessage` handler added. After a connection that was live drops, the indicator shows `'OFFLINE'` in green-on-green styling, which is both confusing and unreadable depending on the color scheme.

```js
// current — missing class cleanup:
document.body.addEventListener('htmx:sseError', function (e) {
  if (e.target && e.target.id === 'log-table') {
    eventsFlowing = false;
    indicator.classList.remove('hidden');
    indicator.classList.add('flex');
    indicator.querySelector('span:last-child').textContent = 'OFFLINE';
    // MISSING: remove emerald, add rose
  }
});
```

**Fix:**

```js
document.body.addEventListener('htmx:sseError', function (e) {
  if (e.target && e.target.id === 'log-table') {
    eventsFlowing = false;
    indicator.classList.remove('hidden', 'bg-emerald-100', 'dark:bg-emerald-900/40',
                               'text-emerald-700', 'dark:text-emerald-400');
    indicator.classList.add('flex', 'bg-rose-100', 'text-rose-700');
    indicator.querySelector('span:last-child').textContent = 'OFFLINE';
  }
});
```

Note: `dark:bg-rose-*` and `dark:text-rose-*` variants are not present in the compiled `output.css` (only `dark:text-rose-400` is). If dark-mode OFFLINE styling is desired, add those classes to a template and rebuild CSS.

---

### WR-03: `htmx:afterSettle` dismisses badge on any HTMX settle, not only SSE refreshes

**File:** `templates/log/log.html:240-243`

**Issue:** The `htmx:afterSettle` listener has no target guard:

```js
document.body.addEventListener('htmx:afterSettle', function () {
  if (document.getElementById('auto-refresh-ok')) {
    dismissBadge();
  }
});
```

`htmx:afterSettle` fires after **every** HTMX swap on the page — including filter-form submissions (`hx-get="/log/view"` targeting `#log-table`), column sort clicks, and the Clear button. All of those swaps replace `#log-table` innerHTML. If the result happens to be page 1 with no filters (i.e., `auto-refresh-ok` is present after the swap), the badge will be silently dismissed even if the user navigated there manually and new QSOs had arrived in the interim.

This is low-severity in practice because the user navigating to page 1 should see the new QSOs in the refreshed table, so dismissing the badge is arguably correct. However, the *intent* documented in the code comments is to dismiss only after an **SSE-triggered** auto-refresh, not after user-initiated navigations. A mismatch between intent and implementation is a latent bug if the logic evolves.

**Fix:** Scope the dismiss to SSE-triggered refreshes only by setting a flag before the `htmx.ajax` call:

```js
var pendingSseRefresh = false;

// in htmx:sseMessage handler, before htmx.ajax:
pendingSseRefresh = true;
htmx.ajax('GET', '/log/view', { target: '#log-table', swap: 'innerHTML' });

// in htmx:afterSettle:
document.body.addEventListener('htmx:afterSettle', function () {
  if (pendingSseRefresh && document.getElementById('auto-refresh-ok')) {
    pendingSseRefresh = false;
    dismissBadge();
  }
});
```

---

## Info

### IN-01: `indicator.querySelector('span:last-child')` is brittle

**File:** `templates/log/log.html:203, 228`

**Issue:** The live indicator element has two child `<span>` elements: the animated dot (index 0) and the text label (index 1). Selecting via `:last-child` works today but will silently break if a third child element is ever added (e.g., an icon) after the text span.

**Fix:** Give the text span an explicit id or class:

```html
<!-- in template: -->
<span id="live-indicator-label">LIVE</span>

<!-- in JS: -->
var indicatorLabel = document.getElementById('live-indicator-label');
// replace all: indicator.querySelector('span:last-child').textContent = ...
// with:        indicatorLabel.textContent = ...
```

---

### IN-02: `NOTIFY_SOUND` string constant compared as `=== 'true'`

**File:** `templates/log/log.html:130, 210`

**Issue:** The Jinja2 template renders `notify_sound` as the string `"true"` or `"false"`:

```js
const NOTIFY_SOUND = "{{ 'true' if notify_sound else 'false' }}";
```

This works but requires a string comparison `=== 'true'` at each call site and could be confused with a boolean. If a developer writes `if (NOTIFY_SOUND)` it will always be truthy (non-empty string).

**Fix:** Render as a JS boolean directly:

```js
const NOTIFY_SOUND = {{ 'true' if notify_sound else 'false' }};
// usage becomes: if (NOTIFY_SOUND && userInteracted && audioCtx)
```

This removes the quotes so the template emits a bare JS boolean literal.

---

_Reviewed: 2026-04-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
