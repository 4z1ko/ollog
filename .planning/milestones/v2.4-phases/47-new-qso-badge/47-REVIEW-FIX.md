---
phase: 47-new-qso-badge
fixed_at: 2026-04-18T00:00:00Z
review_path: .planning/phases/47-new-qso-badge/47-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 47: Code Review Fix Report

**Fixed at:** 2026-04-18
**Source review:** .planning/phases/47-new-qso-badge/47-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (WR-01, WR-02, WR-03; IN-* findings excluded per fix_scope=critical_warning)
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: Duplicate `auto-refresh-ok` DOM query hides logic structure and is fragile

**Files modified:** `templates/log/log.html`
**Commit:** d3cb08b
**Applied fix:** Replaced the two independent `document.getElementById('auto-refresh-ok')` calls (lines 214 and 218) with a single `var canAutoRefresh = !!document.getElementById('auto-refresh-ok');` query. Restructured the conditional into a clear if/else: when `canAutoRefresh` is false, increment badge and `return`; when true, fall through to the auto-refresh path. Eliminates the theoretical race window and makes the mutual-exclusion intent explicit.

### WR-02: `htmx:sseError` leaves stale LIVE color classes on the indicator

**Files modified:** `templates/log/log.html`
**Commit:** 088cd58
**Applied fix:** Extended the `htmx:sseError` handler's `classList.remove()` call to strip all five emerald LIVE classes (`hidden`, `bg-emerald-100`, `dark:bg-emerald-900/40`, `text-emerald-700`, `dark:text-emerald-400`) before adding the rose OFFLINE classes (`flex`, `bg-rose-100`, `text-rose-700`). Dark-mode rose variants were intentionally omitted per the review note that `dark:bg-rose-*` and `dark:text-rose-*` are not present in the compiled `output.css`.

### WR-03: `htmx:afterSettle` dismisses badge on any HTMX settle, not only SSE refreshes

**Files modified:** `templates/log/log.html`
**Commit:** 6917bf1
**Applied fix:** Introduced `var pendingSseRefresh = false;` in the variable declaration block. Set `pendingSseRefresh = true` immediately before the `htmx.ajax()` call in the `htmx:sseMessage` handler. Updated the `htmx:afterSettle` listener to check `pendingSseRefresh &&` before calling `dismissBadge()`, and reset the flag to `false` after dismissal. Badge dismissal is now scoped exclusively to SSE-triggered auto-refreshes and will not fire on filter-form submissions, sort clicks, or Clear button swaps.

## Skipped Issues

None.

---

_Fixed: 2026-04-18_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
