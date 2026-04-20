# Phase 47: New QSO Badge — Research

**Researched:** 2026-04-17
**Domain:** Client-side JavaScript / HTMX SSE event handling / Tailwind CSS dark mode
**Confidence:** HIGH

---

## Summary

Phase 47 adds a "N new QSO(s)" notification badge to `log.html`. All design, architectural,
and behavioural decisions are locked in 47-CONTEXT.md and the pre-decided v2.4 architecture
recorded in STATE.md. There is no backend work, no new packages, and no new Python files.

The implementation is four coordinated changes:

1. A new `<div id="new-qso-badge">` HTML element placed as a DOM sibling of `#log-table`
   (immediately before it) inside the `max-w-7xl mx-auto space-y-6` wrapper.
2. A `newQsoCount` integer variable and two helper functions (`updateBadge`, `dismissBadge`)
   added inside the existing IIFE in `log.html`.
3. A hook in the existing `htmx:sseMessage` handler — after the sound block — that increments
   `newQsoCount` when `#auto-refresh-ok` is absent from the DOM.
4. A new `htmx:afterSettle` listener on `document.body` that auto-dismisses the badge when the
   `#auto-refresh-ok` sentinel reappears after a table swap.

The only risk area is Tailwind CSS class purging: `dark:text-indigo-300` and
`dark:bg-indigo-900/40` must appear as complete literal strings in a scanned template before
`npm run build` is run. Both classes already exist in `templates/log/about.html`, so they are
already in `output.css` — but the executor MUST verify with `npm run build && npm run verify`
after adding the badge HTML to `log.html`.

**Primary recommendation:** Implement entirely in `templates/log/log.html` — badge HTML and JS
both live there. No changes to `log_table.html`, backend, or CSS are expected.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Badge is a compact pill chip, left-aligned, positioned immediately above `#log-table`
  (sibling, not child). Small and subtle — not a full-width info bar.
- **D-02:** Color scheme: indigo. Light mode: `bg-indigo-100 text-indigo-700`. Dark mode:
  `dark:bg-indigo-900/40 dark:text-indigo-300`. `rounded-full px-2.5 py-1 text-xs
  font-semibold` — same visual weight as the existing LIVE indicator pill.
- **D-03:** Badge text: `"N new QSO"` (singular) / `"N new QSOs"` (plural). An `×` close button
  on the right. Example: `▲ 3 new QSOs ×`.
- **D-04:** Badge appears when a `new_qso` SSE event fires AND `auto-refresh-ok` is absent from
  DOM. Reuses the existing sentinel — no new server-side logic needed.
- **D-05:** Badge is hidden by default (`hidden` class). Counter starts at 0.
- **D-06:** Edit mode: badge increments even when a row edit form is open on page 2+.
- **D-07:** Click to dismiss: reset counter to 0, hide badge. No page navigation, no scroll.
- **D-08:** Auto-dismiss on `htmx:afterSettle`: when `#log-table` completes a swap and
  `auto-refresh-ok` is now present, reset counter and hide badge.
- **D-09:** Badge `<div id="new-qso-badge">` placed immediately before `#log-table` inside
  the `max-w-7xl mx-auto space-y-6` wrapper. Starts with `hidden` class.
- **D-10:** Badge counter (`newQsoCount`) and show/hide logic live inside the existing IIFE in
  `log.html`. No new `<script>` block.

### Claude's Discretion

- Exact Tailwind classes for the indigo pill (use existing LIVE indicator as size reference)
- Transition/animation on badge appear (optional fade-in, or just show — keep simple)
- Whether to include an upward arrow icon (`▲`) or a bell icon inside the pill — either works

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIVE-03 | When new QSOs arrive while the operator is on page 2+ or has active filters, a "N new QSO(s)" badge appears in the log view header | Sentinel `#auto-refresh-ok` (already in `log_table.html` line 2) provides the page/filter signal. Badge increments in the `htmx:sseMessage` handler when sentinel is absent. |
| LIVE-04 | Clicking the badge dismisses it (resets counter to zero) — no page jump, no auto-scroll | Click listener on `#new-qso-badge` calls `dismissBadge()` — no HTMX request, no navigation. `htmx:afterSettle` auto-dismiss covers SC-4. |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Badge display and counter state | Browser / Client | — | Pure JS in IIFE; no server round-trip needed |
| "Am I on page 1 with no filters?" signal | Frontend Server (SSR) | Browser | Server renders `#auto-refresh-ok` sentinel in `log_table.html`; JS reads DOM |
| Badge dismiss | Browser / Client | — | Class manipulation only; no server call |
| Auto-dismiss on navigation | Browser / Client | — | `htmx:afterSettle` listener reads DOM for sentinel |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| HTMX | 1.9.x (in-use) | SSE events and partial swaps | Already installed; `htmx:sseMessage` and `htmx:afterSettle` are the integration points |
| Tailwind CSS | 3.4.17 (in-use) | Utility class styling | Already installed; `dark:` class purge rules apply |
| Vanilla JS (IIFE) | ES5/ES6 (in-use) | Badge state management | Established project pattern; no new deps allowed |

No new packages. `requirements.txt` and `package.json` do not change. [VERIFIED: STATE.md §v2.4 Architecture Decisions; 47-CONTEXT.md domain section]

### Supporting

None — this phase has no supporting libraries beyond what is already installed.

### Alternatives Considered

None applicable — all choices are locked decisions from CONTEXT.md.

---

## Architecture Patterns

### System Architecture Diagram

```
UDP/WSJT-X datagram
        |
        v
app/udp/ → MongoDB (qsos collection)
        |
        v (change stream)
app/feed/manager.py (watch_qsos)
        |  SSE event: "new_qso"
        v
Browser EventSource (hx-ext="sse" on #log-table)
        |
        v
htmx:sseMessage (document.body listener in IIFE)
        |
        +-- #auto-refresh-ok present? --> htmx.ajax() refreshes #log-table (page 1 path)
        |
        +-- #auto-refresh-ok absent?  --> newQsoCount++; updateBadge() (page 2+ path)
                                            |
                                            v
                                     #new-qso-badge shown with "N new QSO(s)"
                                            |
                     +-----------------------+---------------------+
                     |                                             |
              user clicks badge                        htmx:afterSettle fires after
                     |                                 any #log-table swap
                     v                                             |
              dismissBadge()                    #auto-refresh-ok present?
              (counter=0, hide)                         |
                                                YES: dismissBadge()
                                                NO:  no action
```

### Recommended Project Structure

No structural changes. All modifications are within existing files:

```
templates/log/
├── log.html           # MODIFY: badge HTML + IIFE changes (badge var, updateBadge,
│                      #   dismissBadge, sseMessage hook, afterSettle listener)
└── log_table.html     # READ-ONLY: auto-refresh-ok sentinel is already correct
```

### Pattern 1: IIFE State Variable Addition

**What:** Add `newQsoCount` alongside existing IIFE variables; add `updateBadge` and
`dismissBadge` helper functions.

**When to use:** All badge state lives here — mirrors how `eventsFlowing`, `audioCtx`, and
`userInteracted` are structured.

**Example:**

```javascript
// Source: log.html existing IIFE structure (lines 117–201)
(function () {
  var indicator = document.getElementById('live-indicator');
  var badge = document.getElementById('new-qso-badge');
  var badgeText = document.getElementById('new-qso-badge-text');
  var newQsoCount = 0;
  var eventsFlowing = false;
  // ... existing vars ...

  function updateBadge() {
    badgeText.textContent = newQsoCount === 1 ? '1 new QSO' : newQsoCount + ' new QSOs';
    badge.classList.remove('hidden');
    badge.classList.add('flex');
  }

  function dismissBadge() {
    newQsoCount = 0;
    badge.classList.add('hidden');
    badge.classList.remove('flex');
  }

  badge.addEventListener('click', dismissBadge);
  // ...
})();
```

### Pattern 2: SSE Message Hook

**What:** After the sound playback block in `htmx:sseMessage`, add the badge increment.
The existing edit-mode guard (`if (document.querySelector('#log-table input')) return;`)
runs AFTER the badge increment — badge increments even in edit mode on page 2+ (D-06).

**Example:**

```javascript
// Source: log.html lines 161–183 (htmx:sseMessage handler)
document.body.addEventListener('htmx:sseMessage', function (e) {
  if (!e.target || e.target.id !== 'log-table') return;
  if (!e.detail || e.detail.type !== 'new_qso') return;
  // ... eventsFlowing + sound block (unchanged) ...

  // Badge increment — fires BEFORE the edit-mode guard
  if (!document.getElementById('auto-refresh-ok')) {
    newQsoCount++;
    updateBadge();
  }

  // Existing auto-refresh guards (unchanged)
  if (!document.getElementById('auto-refresh-ok')) return;
  if (document.querySelector('#log-table input')) return;
  htmx.ajax('GET', '/log/view', { target: '#log-table', swap: 'innerHTML' });
});
```

**CRITICAL placement note:** The badge increment block must go BEFORE the
`if (!document.getElementById('auto-refresh-ok')) return;` line, otherwise it would be
unreachable. The increment checks for absence of the sentinel and then falls through — the
early return also checks for absence, so control never reaches `htmx.ajax()` when absent.
This is correct: the increment fires when absent, the early return fires when absent (stops
before `htmx.ajax`), and `htmx.ajax` only fires when present.

### Pattern 3: htmx:afterSettle Auto-Dismiss

**What:** A new listener on `document.body`. HTMX fires `htmx:afterSettle` with
`evt.detail.target` pointing to the element whose content was settled.

**When to use:** After any `#log-table` swap completes (pagination, filter, column sort, SSE
auto-refresh), check if user is now on page 1 with no filters.

**Example:**

```javascript
// Source: Context7 /bigskysoftware/htmx — htmx:afterSettle event
// evt.detail.target is the swap target element
document.body.addEventListener('htmx:afterSettle', function (evt) {
  if (document.getElementById('auto-refresh-ok')) {
    dismissBadge();
  }
});
```

**Note:** The existing `htmx:afterSettle` listener in `base_app.html` (line 213) does a
theme icon sync. It does NOT have an `evt.detail.target` check. The badge's afterSettle
listener also does not need a target check — if `auto-refresh-ok` is present after ANY
settle, the operator is on a page-1 no-filter view, and dismissing is always correct.

### Pattern 4: Badge HTML

**What:** Sibling `<div>` immediately before `<div id="log-table" ...>` in `log.html`.
Must have `hidden` class initially and include both `hidden` and `flex` in its class
manipulations (never `flex` without removing `hidden` first).

**Example (from UI-SPEC.md):**

```html
<!-- Source: 47-UI-SPEC.md Component Inventory -->
<div id="new-qso-badge"
     class="hidden items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold
            bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300
            cursor-pointer select-none mb-2">
  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24"
       stroke-width="2" stroke="currentColor">
    <!-- chevron-up or arrow-up from Heroicons -->
    <path stroke-linecap="round" stroke-linejoin="round"
          d="M4.5 15.75l7.5-7.5 7.5 7.5" />
  </svg>
  <span id="new-qso-badge-text">1 new QSO</span>
  <span class="ml-1 opacity-70">&times;</span>
</div>
```

### Anti-Patterns to Avoid

- **Nesting badge inside `#log-table`:** HTMX SSE swaps replace `#log-table` innerHTML.
  A nested badge is destroyed on every swap. CRITICAL: badge must be a DOM sibling.
- **Setting badge visible with only `flex` (without removing `hidden`):** Tailwind `hidden`
  sets `display: none !important` — adding `flex` does not override it. Must
  `classList.remove('hidden')` before `classList.add('flex')`.
- **Firing badge increment after the `return` guard:** The code path
  `if (!auto-refresh-ok) return;` must be AFTER the badge increment, not before.
- **Using CSS transitions that require new classes not in output.css:** If the executor
  adds `transition-opacity duration-150`, these classes must already be in `output.css` or
  the template must contain them as literal strings. Check with `npm run build`.
- **Checking `e.detail.target.id` in `htmx:afterSettle`:** Unnecessary — if
  `auto-refresh-ok` is present after any settle, dismiss is always safe.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "Am I on page 1 with no filters?" | Custom URL parsing / state variable tracking | `#auto-refresh-ok` sentinel in `log_table.html` | Server renders the sentinel; JS reads one DOM lookup; already proven correct in Phase 44 |
| HTMX event routing | Custom event system | `htmx:sseMessage` + `htmx:afterSettle` | Already wired; `e.detail.type` discriminates SSE event names |
| Badge show/hide toggle | CSS class factory or display style | `classList.remove('hidden'); classList.add('flex')` pattern | Matches LIVE indicator pattern already in log.html; consistent |

**Key insight:** The `#auto-refresh-ok` sentinel is the single source of truth for "should
auto-refresh happen?" The badge inverts that question: badge increments exactly when
auto-refresh would NOT happen. No duplication of filter/page state in JS is needed.

---

## Common Pitfalls

### Pitfall 1: Badge increment is unreachable

**What goes wrong:** Developer places the badge increment block after
`if (!document.getElementById('auto-refresh-ok')) return;`. Since both conditions check for
sentinel absence, the increment is never reached.

**Why it happens:** The existing handler already has an early return on sentinel absence. The
natural place to add the increment looks like "after the return" but must actually be before.

**How to avoid:** Insert the increment block between the sound block and the first
`if (!auto-refresh-ok)` early return. See Pattern 2 above.

**Warning signs:** Badge never appears even when navigating to page 2 and inserting a QSO.

### Pitfall 2: Badge destroyed by SSE swap

**What goes wrong:** Badge `<div>` is placed inside `<div id="log-table">` (as a child). When
the SSE auto-refresh fires on page 1 and the user later navigates to page 2, the badge appears
and then gets wiped on the next auto-refresh cycle.

**Why it happens:** `hx-swap="innerHTML"` replaces everything inside `#log-table`.

**How to avoid:** Always place badge immediately BEFORE `<div id="log-table" ...>`, never
inside it.

**Warning signs:** Badge disappears unexpectedly after returning to page 2.

### Pitfall 3: Tailwind dark classes not in output.css

**What goes wrong:** `dark:text-indigo-300` or `dark:bg-indigo-900/40` are not present in
`output.css` after `npm run build` because Tailwind's JIT scanner only includes classes
appearing as complete literal strings in scanned template files.

**Why it happens:** If the class is added only via JS string concatenation or `@apply` in
`input.css`, the scanner misses it.

**How to avoid:** Confirm the classes appear literally in a `.html` file inside `templates/`.
Current status: `dark:text-indigo-300` and `dark:bg-indigo-900/30` (note: `/30` not `/40`)
already exist in `templates/log/about.html`. However `dark:bg-indigo-900/40` specifically
must also appear. This class exists in `templates/log/import.html` as `dark:bg-indigo-900/40`
— verified. [VERIFIED: grep of templates/] After adding badge HTML to `log.html`, run
`npm run build && npm run verify`.

**Warning signs:** Badge background missing in dark mode; pill appears transparent on dark
background.

### Pitfall 4: `hidden` + `flex` conflict

**What goes wrong:** `updateBadge()` adds `flex` without removing `hidden`. Tailwind's
`hidden` utility compiles to `display: none !important` — the `!important` overrides the
`flex` rule, so badge remains invisible.

**Why it happens:** Developers see `items-center flex` in the static HTML but forget that
`hidden` is gating the display property.

**How to avoid:** Always pair: `badge.classList.remove('hidden'); badge.classList.add('flex');`
and in dismiss: `badge.classList.add('hidden'); badge.classList.remove('flex');`.

**Warning signs:** `updateBadge()` runs without errors but badge is not visible.

### Pitfall 5: afterSettle listener attached inside IIFE before DOM is ready

**What goes wrong:** The IIFE runs synchronously when the `<script>` tag is parsed. If
`document.getElementById('new-qso-badge')` is called before the badge HTML is in the DOM
(e.g., if the script is moved to `<head>`), it returns null and subsequent `.classList` calls
throw.

**Why it happens:** The `<script>` block is at the bottom of `{% block content %}` in the
existing template — DOM is ready. This is safe as long as the badge HTML is placed in the
same `{% block content %}` above the `<script>`.

**How to avoid:** Keep the script at the bottom of `{% block content %}`. Keep badge HTML in
the `max-w-7xl mx-auto space-y-6` div above the script. Do not move either element.

**Warning signs:** `TypeError: Cannot read properties of null (reading 'classList')` in
browser console.

---

## Code Examples

Verified patterns from official sources and existing codebase:

### htmx:afterSettle event — target property

```javascript
// Source: Context7 /bigskysoftware/htmx (htmx events documentation)
document.body.addEventListener('htmx:afterSettle', function(evt) {
  // evt.detail.target: the target element of the swap request
  // evt.detail.elt: the element that triggered the request
});
```

### Existing LIVE indicator show/hide (canonical pattern to mirror)

```javascript
// Source: log.html lines 168–173 (existing, verified)
indicator.classList.remove('hidden');
indicator.classList.add('flex');
indicator.querySelector('span:last-child').textContent = 'LIVE';
```

### Existing sentinel lookup (canonical)

```javascript
// Source: log.html line 180 (existing, verified)
if (!document.getElementById('auto-refresh-ok')) return;
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Full-page reload for new QSO notification | SSE + HTMX partial swap with in-page badge | Phase 44 (v2.4) | No page reload; user stays on page 2+ uninterrupted |

**Not applicable:** This phase has no deprecated or replaced patterns — it introduces a net-new
capability.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `dark:bg-indigo-900/40` already exists in `output.css` via `templates/log/import.html` | Common Pitfalls #3 | Dark mode badge background would be invisible; fix is running `npm run build` |

If this table is nearly empty it is because this phase's choices are locked decisions verified
against the actual codebase source files.

---

## Open Questions

1. **Optional fade-in animation**
   - What we know: CONTEXT.md marks animation as Claude's discretion; LIVE indicator uses
     plain class swap with no transition.
   - What's unclear: Whether `transition-opacity duration-150` classes are already in
     `output.css`.
   - Recommendation: Implement without transition first (matching LIVE indicator). If the
     executor wants a fade, verify classes exist in `output.css` before adding.

2. **Icon choice: chevron-up vs arrow-up**
   - What we know: CONTEXT.md D-03 uses `▲` as reference; UI-SPEC says either is acceptable.
   - What's unclear: Which looks better alongside the `LIVE` text pill in the same row area.
   - Recommendation: Use Heroicons `chevron-up` (path: `M4.5 15.75l7.5-7.5 7.5 7.5`) at
     `w-3.5 h-3.5` — it is lower visual weight than arrow-up and matches the subtle style goal.

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — pure frontend template + JS change, no new
tools, no new services, no new CLI utilities required).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (existing) |
| Config file | `pytest.ini` or inline (existing) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIVE-03 | Badge appears on page 2+ when `#auto-refresh-ok` absent and SSE fires | manual-only (browser interaction; SSE + DOM state) | n/a | — |
| LIVE-04 | Badge dismisses on click with no navigation | manual-only (browser click event) | n/a | — |
| LIVE-03 + LIVE-04 (indirect) | `updateBadge` text logic produces correct singular/plural | unit | `uv run pytest tests/ -k badge -x` | ❌ Wave 0 |

**Manual-only justification for LIVE-03 / LIVE-04 core behavior:** These requirements depend
on SSE event delivery, real HTMX swap lifecycle, and browser DOM interaction — none of which
are testable without a running browser. The existing test suite (see `test_watcher.py`) mocks
the change stream, but cannot simulate `htmx:sseMessage` browser events. The acceptance tests
for SC-1 through SC-5 are human-verified against a running Docker stack.

**What CAN be unit-tested:** The plural/singular text logic
(`newQsoCount === 1 ? '1 new QSO' : newQsoCount + ' new QSOs'`) is pure logic that could be
extracted and tested, but given it is a one-liner it is low value to test in isolation. No
unit test file is required for this phase — the implementation is small enough that browser
verification against the success criteria is the appropriate gate.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -x -q` (regression guard — ensures no Python is broken)
- **Per wave merge:** `uv run pytest tests/`
- **Phase gate:** Full suite green + manual browser verification of SC-1 through SC-5

### Wave 0 Gaps

None — no new Python files, no new test infrastructure needed. Existing test suite provides
regression coverage for unrelated modules. The phase's deliverable is a template + JS change
with no testable Python surface.

---

## Security Domain

This phase introduces no server-side code, no new endpoints, no data input from users, and no
authentication changes. The only change is a read-only DOM manipulation in a Jinja2 template
loaded for already-authenticated operators.

ASVS categories are not applicable. The badge increments on SSE events that already flow
through the existing authenticated SSE endpoint (`/feed/station`) — no new attack surface is
introduced.

---

## Project Constraints (from CLAUDE.md)

Directives that apply to this phase:

| Directive | Impact on Phase 47 |
|-----------|-------------------|
| **FOUC prevention:** Inline IIFE in `base.html` `<head>` is load-bearing; never move or defer | Not affected — phase modifies the IIFE in `log.html` `{% block content %}`, not in `base.html` `<head>` |
| **Tailwind purge:** New `dark:` classes must appear as complete literal strings in scanned template files; run `npm run build` + `npm run verify` after adding new dark classes | CRITICAL: After adding badge HTML to `log.html`, executor MUST run `npm run build && npm run verify`. Relevant classes: `dark:bg-indigo-900/40` (existing in `import.html`) and `dark:text-indigo-300` (existing in `about.html`) |
| **No new Python packages** | Confirmed — no changes to `requirements.txt` or `pyproject.toml` |
| **No new JS dependencies** | Confirmed — no `npm install` needed |
| **APScheduler `<4` upper bound is load-bearing** | Not affected |
| **FastAPI sub-app StaticFiles** | Not affected |
| **Safari `backdrop-filter`** | Not affected — phase uses no backdrop-filter |

---

## Sources

### Primary (HIGH confidence)

- `templates/log/log.html` — full IIFE structure, existing `htmx:sseMessage` handler, LIVE indicator pattern (lines 115–202); read directly
- `templates/log/log_table.html` — `#auto-refresh-ok` sentinel (line 2); read directly
- `.planning/phases/47-new-qso-badge/47-CONTEXT.md` — all locked decisions D-01 through D-10; read directly
- `.planning/phases/47-new-qso-badge/47-UI-SPEC.md` — badge HTML structure, class audit, interaction contract; read directly
- `.planning/STATE.md` §v2.4 Architecture Decisions — badge placement, afterSettle re-sync, no new packages; read directly
- Context7 `/bigskysoftware/htmx` — `htmx:afterSettle` event shape (`evt.detail.target`); verified via `npx ctx7@latest docs`
- `templates/base_app.html` line 213 — existing `htmx:afterSettle` usage pattern (no target check); read directly

### Secondary (MEDIUM confidence)

- `static/css/input.css` `.badge-blue` — confirms `dark:bg-indigo-900/40` and `dark:text-indigo-400` are established project patterns; grep verified
- `templates/log/about.html` — confirms `dark:text-indigo-300` already appears as literal string in templates; grep verified
- `templates/log/import.html` — confirms `dark:bg-indigo-900/40` already appears as literal string in templates; grep verified

### Tertiary (LOW confidence)

None — all claims verified against codebase or official documentation in this session.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; existing stack verified in codebase
- Architecture: HIGH — locked decisions from CONTEXT.md; verified against actual template files
- Pitfalls: HIGH — derived from reading actual template code and Tailwind purge rules
- Tailwind class availability: HIGH — verified via grep of existing templates

**Research date:** 2026-04-17
**Valid until:** 2026-06-17 (stable — Tailwind v3, HTMX 1.9.x, no fast-moving dependencies)
