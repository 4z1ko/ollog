# Phase 47: New QSO Badge — Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a client-side "N new QSO(s)" badge to `log.html` that appears when new QSOs arrive via SSE while the operator is on page 2+ or has active filters — situations where the table does NOT auto-refresh. The badge is dismissable with a single click (no page jump) and auto-dismisses when the operator navigates back to page 1 with no filters. Pure JS within the existing IIFE — no backend changes, no new packages.

</domain>

<decisions>
## Implementation Decisions

### Badge Visual Design
- **D-01:** Badge is a **compact pill chip**, left-aligned, positioned immediately above `#log-table` (sibling, not child). Small and subtle — not a full-width info bar.
- **D-02:** Color scheme: **indigo** (brand color). Matches the app's primary button and design tokens. Light mode: `bg-indigo-100 text-indigo-700`. Dark mode: `dark:bg-indigo-900/40 dark:text-indigo-300`. Rounded-full, small padding (px-2.5 py-1), text-xs font-semibold — same visual weight as the existing LIVE indicator pill.
- **D-03:** Badge text: `"N new QSO"` (singular) / `"N new QSOs"` (plural). An `×` close button on the right. Example: `▲ 3 new QSOs ×`.

### Badge Show/Hide Logic
- **D-04:** Badge appears when a `new_qso` SSE event fires AND `auto-refresh-ok` is **absent** from DOM (page 2+, active filters, or default sort not applied). This reuses the existing sentinel mechanism — no new server-side logic needed.
- **D-05:** Badge is hidden by default (`hidden` class). Counter starts at 0. On each qualifying SSE event, increment counter and show badge.
- **D-06:** Edit mode behavior: badge **increments** even when a row edit form is open on page 2+ (Claude's discretion — consistent with "not on page 1" logic; edit mode is only a guard for auto-refresh, not for badge visibility).

### Dismiss Behavior
- **D-07:** Click to dismiss: reset counter to 0, hide badge. **No page navigation, no scroll** (LIVE-04).
- **D-08:** Auto-dismiss on `htmx:afterSettle`: when `#log-table` completes a swap and `auto-refresh-ok` is now present in DOM (user navigated to page 1 with no filters), reset counter and hide badge. This is the mechanism for SC4.

### DOM Placement
- **D-09:** Badge `<div id="new-qso-badge">` placed **immediately before** `#log-table` inside the `max-w-7xl mx-auto space-y-6` wrapper. Starts with `hidden` class. HTMX SSE swaps `#log-table` innerHTML — badge is a sibling, so it survives all swaps.

### JS Structure
- **D-10:** Badge counter (`newQsoCount`) and show/hide logic live inside the existing IIFE in `log.html`, alongside `eventsFlowing`, `audioCtx`, `userInteracted`. No new `<script>` block.

### Claude's Discretion
- Exact Tailwind classes for the indigo pill (use existing LIVE indicator as size reference)
- Transition/animation on badge appear (optional fade-in, or just show — keep simple)
- Whether to include an upward arrow icon (`▲`) or a bell icon inside the pill — either works

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Primary Files to Modify
- `templates/log/log.html` — IIFE `<script>` (htmx:sseMessage handler, badge JS); badge HTML added as sibling of `#log-table` (line 106)
- `templates/log/log_table.html` — `auto-refresh-ok` sentinel (line 2); badge show/hide hooks on `htmx:afterSettle`

### Existing Sentinel Mechanism
- `templates/log/log_table.html` line 2: `<span id="auto-refresh-ok" hidden></span>` — present only on page 1 with default sort and no filters. Badge uses this same signal.

### Existing LIVE Indicator (visual reference)
- `templates/log/log.html` lines 18–23: the existing LIVE indicator pill — use same px-2.5 py-1 rounded-full text-xs font-semibold sizing for the badge pill.

### Design Tokens Reference
- `templates/base_app.html` — card classes, badge-blue reference, dark mode variables

### Architecture Decisions (PRE-DECIDED — must follow)
- `.planning/STATE.md` §v2.4 Architecture Decisions — Badge placement, htmx:afterSettle re-sync, no new packages

### Requirements
- `.planning/REQUIREMENTS.md` — LIVE-03 (badge on page 2+), LIVE-04 (click-to-dismiss, no page jump)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `document.getElementById('live-indicator')` and its show/hide pattern (lines 118–174 in log.html) — same class manipulation pattern for badge
- `#auto-refresh-ok` sentinel — the existing "am I on page 1 with no filters?" signal; badge reuses this without any new Python/server changes
- `htmx:sseMessage` handler (lines 161–183 in log.html) — badge increment hook goes here, after the sound playback block, when `auto-refresh-ok` is absent

### Established Patterns
- IIFE `<script>` for all page-level JS state (no global leaks)
- `classList.remove('hidden') / classList.add('hidden')` for show/hide (used for LIVE indicator)
- `rounded-full px-2.5 py-1 text-xs font-semibold` — established pill sizing from LIVE indicator

### Integration Points
- `htmx:sseMessage` handler: after the sound block, add `if (!document.getElementById('auto-refresh-ok')) { newQsoCount++; updateBadge(); }`
- `htmx:afterSettle`: new listener — if `auto-refresh-ok` is present after swap, call `dismissBadge()`
- Badge HTML: sibling `<div>` immediately before `<div id="log-table" ...>` in log.html

</code_context>

<specifics>
## Specific Ideas

- Badge pill should visually echo the LIVE indicator (same size/weight) but use indigo rather than emerald — the operator sees both at once in the header + above-table area.
- Text format from success criteria: `"1 new QSO"` (singular), `"3 new QSOs"` (plural) — JS must handle both.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 47-new-qso-badge*
*Context gathered: 2026-04-17*
