# Phase 47: New QSO Badge — Pattern Map

**Mapped:** 2026-04-17
**Files analyzed:** 2 (both are modifications of existing files; no new files)
**Analogs found:** 2 / 2

---

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `templates/log/log.html` | component (SSE-driven UI) | event-driven | `templates/log/log.html` lines 18–23 (LIVE indicator) + lines 161–183 (sseMessage handler) | exact — same file, same pattern |
| `templates/log/log_table.html` | component (SSR partial) | request-response | `templates/log/log_table.html` line 2 (`#auto-refresh-ok` sentinel) | read-only reference — no changes needed per RESEARCH.md |

---

## Pattern Assignments

### `templates/log/log.html` — badge HTML block (new sibling before `#log-table`)

**Analog:** `templates/log/log.html` lines 18–23 (existing LIVE indicator pill)

**Existing LIVE indicator pattern** (lines 18–23) — copy visual structure, substitute indigo for emerald:
```html
<span id="live-indicator"
      class="hidden items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold
             bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400">
  <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse inline-block"></span>
  LIVE
</span>
```

**Badge HTML to insert immediately before line 106** (`<div id="log-table" ...>`):
- Keep same pill sizing: `px-2.5 py-1 rounded-full text-xs font-semibold`
- Swap color: `bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300`
- Add `cursor-pointer select-none mb-2` for click-to-dismiss affordance
- Must start with `hidden` class; JS adds `flex` and removes `hidden` on show
- Must include `id="new-qso-badge"` on outer div and `id="new-qso-badge-text"` on text span
- Place inside the `max-w-7xl mx-auto space-y-6` wrapper (line 6), NOT inside `#log-table`

**DOM placement** (line 105–111 for reference):
```html
  <!-- Log table (SSE + HTMX swap target) -->
  <div id="log-table"
       hx-ext="sse"
       sse-connect="/feed/station"
       hx-trigger="sse:new_qso">
    {% include "log/log_table.html" %}
  </div>
```
Badge goes immediately before the `<!-- Log table -->` comment block, as a sibling `<div>`.

---

### `templates/log/log.html` — IIFE JS additions (inside existing `<script>` block)

**Analog:** `templates/log/log.html` lines 117–201 (entire IIFE block)

**IIFE variable declaration pattern** (lines 118–122) — add `badge` and `badgeText` refs and `newQsoCount` alongside existing vars:
```javascript
(function () {
  var indicator = document.getElementById('live-indicator');
  var eventsFlowing = false;
  var AudioCtxClass = window.AudioContext || window.webkitAudioContext;
  var audioCtx = null;
  var userInteracted = false;
  // ... new vars go here:
  // var badge = document.getElementById('new-qso-badge');
  // var badgeText = document.getElementById('new-qso-badge-text');
  // var newQsoCount = 0;
```

**Show/hide class manipulation pattern** (lines 168–173) — exact pattern to mirror for `updateBadge` / `dismissBadge`:
```javascript
// Show (LIVE indicator — canonical pattern)
indicator.classList.remove('hidden');
indicator.classList.add('flex');
indicator.querySelector('span:last-child').textContent = 'LIVE';

// Hide (sseClose handler, lines 198–200)
indicator.classList.add('hidden');
indicator.classList.remove('flex');
```
`updateBadge` and `dismissBadge` must follow this identical `remove('hidden') / add('flex')` sequence — never add `flex` without removing `hidden` first (Tailwind `hidden` sets `display:none !important`).

**`htmx:sseMessage` handler** (lines 161–183) — badge increment goes BETWEEN the sound block (line 179) and the first `auto-refresh-ok` early return (line 180). Insertion point is exact:
```javascript
document.body.addEventListener('htmx:sseMessage', function (e) {
  if (!e.target || e.target.id !== 'log-table') return;
  if (!e.detail || e.detail.type !== 'new_qso') return;
  // ... eventsFlowing + LIVE indicator block (lines 166–174, unchanged) ...
  // Sound notification (lines 176–179, unchanged)
  if (NOTIFY_SOUND === 'true' && userInteracted && audioCtx) {
    playTone(audioCtx);
  }
  // INSERT BADGE INCREMENT HERE (before the return guard):
  // if (!document.getElementById('auto-refresh-ok')) {
  //   newQsoCount++;
  //   updateBadge();
  // }
  if (!document.getElementById('auto-refresh-ok')) return;   // line 180 — do NOT move
  if (document.querySelector('#log-table input')) return;    // line 181
  htmx.ajax('GET', '/log/view', { target: '#log-table', swap: 'innerHTML' });
});
```
Critical: the badge increment checks for sentinel absence and then falls through; the early return on line 180 also checks for absence. Both are correct — increment fires (and function returns) when sentinel is absent; `htmx.ajax` only fires when sentinel is present.

**`htmx:afterSettle` pattern** (base_app.html line 213) — existing usage with no target check, to mirror:
```javascript
// Existing in base_app.html (line 213) — no target guard needed
document.body.addEventListener('htmx:afterSettle', function () {
  updateThemeIcons(document.documentElement.classList.contains('dark'));
});
// New badge listener uses same no-target-guard pattern:
// document.body.addEventListener('htmx:afterSettle', function () {
//   if (document.getElementById('auto-refresh-ok')) {
//     dismissBadge();
//   }
// });
```

**Click-to-dismiss pattern** — badge element gets a click listener, not a button inside it:
```javascript
// Pattern: badge outer div is the click target
badge.addEventListener('click', dismissBadge);
```

---

## Shared Patterns

### Hidden/Flex Toggle (applies to badge show/hide)
**Source:** `templates/log/log.html` lines 168–173 and 198–200
**Apply to:** `updateBadge()` and `dismissBadge()` helpers
```javascript
// Show
element.classList.remove('hidden');
element.classList.add('flex');
// Hide
element.classList.add('hidden');
element.classList.remove('flex');
```

### SSE Event Guard (applies to badge increment hook)
**Source:** `templates/log/log.html` lines 164–165
**Apply to:** `htmx:sseMessage` handler — gate all badge/indicator logic on correct element and event type
```javascript
if (!e.target || e.target.id !== 'log-table') return;
if (!e.detail || e.detail.type !== 'new_qso') return;
```

### Sentinel DOM Lookup (applies to badge increment condition and auto-dismiss)
**Source:** `templates/log/log.html` line 180; `templates/log/log_table.html` line 1–3
**Apply to:** badge increment condition (`!sentinel` = show badge) and afterSettle auto-dismiss (`sentinel present` = dismiss badge)
```javascript
// Sentinel rendered server-side only on page 1, default sort, no filters:
// {% if page == 1 and sort == '-qso_date_utc' and not filters.call ... %}
// <span id="auto-refresh-ok" hidden></span>
// {% endif %}
//
// JS lookup (canonical):
document.getElementById('auto-refresh-ok')
```

### Indigo Pill Color Tokens
**Source:** `static/css/input.css` lines 144–147 (`.badge-blue` definition); `templates/log/import.html` line 70; `templates/log/about.html` lines 36–37
**Apply to:** badge HTML Tailwind classes
```
Light mode: bg-indigo-100 text-indigo-700
Dark mode:  dark:bg-indigo-900/40 dark:text-indigo-300
```
Note: `.badge-blue` uses `text-indigo-400` for dark text; badge uses `text-indigo-300` (slightly brighter, per D-02). Both `dark:bg-indigo-900/40` and `dark:text-indigo-300` are confirmed present as literal strings in existing templates (`import.html` and `about.html`) and thus already in `output.css`.

### Pill Sizing
**Source:** `templates/log/log.html` lines 19–20 (LIVE indicator)
**Apply to:** badge outer div classes
```
rounded-full px-2.5 py-1 text-xs font-semibold
```

---

## No Analog Found

None — all patterns have direct analogs in the existing codebase.

---

## Metadata

**Analog search scope:** `templates/log/`, `templates/base_app.html`, `static/css/input.css`
**Files scanned:** `log.html`, `log_table.html`, `base_app.html`, `input.css`, `about.html`, `import.html`
**Pattern extraction date:** 2026-04-17
