# Phase 36: Operator Log Views - Research

**Researched:** 2026-04-11
**Domain:** Jinja2 templates / Tailwind CSS component tokens / HTMX SSE partial rendering
**Confidence:** HIGH — all findings derived from direct source inspection

## Summary

Phase 36 is a pure frontend template-polish pass over four operator-facing templates: `log.html`, `log_table.html`, `form.html`, and `import.html`. The Phase 33 component library is already fully defined in `input.css` (card, data-table, btn-*, form-input, badge-*, etc.) and the token theme (canvas, surface, sidebar) is live in `tailwind.config.js`. Three of the four primary templates (`log.html`, `form.html`, `import.html`) are already substantially migrated — they use the component classes correctly. The work for those three is surgical: remove isolated inline styles, wire in missing Apple token classes, and ensure no gaps.

The biggest work item is `import_report.html`, a swapped partial that is entirely inline-styled with hardcoded light-mode colors (no dark: classes at all). It must be fully rewritten using the component system. Additionally `qso_row.html` and `qso_row_edit.html` contain inline `style=""` attributes that must be converted to Tailwind classes, since they render inside the `data-table` tbody that SSE and HTMX reload.

`log_table.html` is the SSE-swapped partial. It already uses `.card`, `.table-wrap`, `.data-table`, and `dark:` utility classes extensively. The two `style="cursor:pointer;"` inline attributes on pagination anchor tags in that file must be removed (replace with Tailwind `cursor-pointer` class), satisfying the OPER-01 "no inline style attributes in any partial" requirement.

No new CSS component classes are needed in `input.css`. All required visual states are covered by the existing library.

**Primary recommendation:** Focus the plan on (1) `import_report.html` full rewrite to component classes, (2) remove the two `cursor:pointer` inline styles from `log_table.html`, (3) convert `qso_row_edit.html`'s width-style inputs to `form-input` with Tailwind width utilities, (4) replace the flag `style` in `qso_row.html` with Tailwind inline-align classes, and (5) convert `qso_result.html`'s flex container inline style to Tailwind.

---

## Current State of Each Template

### log.html — LARGELY DONE, one gap

**File:** `templates/log/log.html`

**What already works:**
- Uses `.card`, `.card-header`, `.card-title`, `.card-body` correctly
- Filter form uses `.form-label`, `.form-input`, `.form-select` correctly
- Submit / Clear buttons use `.btn-primary btn-sm` and `.btn-ghost btn-sm`
- Export link uses `.btn-ghost btn-sm`
- Live indicator uses raw Tailwind utilities with proper `dark:` variants
- SSE connection is on `<div id="log-table" hx-ext="sse" sse-connect="/feed/station">` — the partial is included inside this div
- Page header `h1` uses `text-gray-900 dark:text-white` — raw Tailwind, acceptable (no component class wraps page titles)

**No inline style attributes** — this file is clean.

**Outstanding gap:**
- The `badge-blue` badge on the Filters card header renders "Active" when filters are applied — this class already exists in the component library. Currently correct.
- OPER-01 compliance: PASS for this file.

**Changes needed:** None to `log.html` itself.

---

### log_table.html — TWO INLINE STYLES TO REMOVE

**File:** `templates/log/log_table.html`

**What already works:**
- Empty state uses `.card`, `.card-body` with `dark:` variants throughout
- Table uses `.table-wrap` and `.data-table` — both carry full dark-mode definitions in `input.css`
- Sort arrows use `hover:text-indigo-400 transition-colors` — correct
- Pagination text uses `text-gray-500 dark:text-gray-400`, `text-gray-700 dark:text-gray-300` — correct
- Previous / Next pagination links use `.btn-ghost .btn-sm` — correct

**Inline styles found (OPER-01 violations):**
```
line 100: style="cursor:pointer;"   ← on Previous pagination <a>
line 118: style="cursor:pointer;"   ← on Next pagination <a>
```

These two `<a>` elements already have `class="btn-ghost btn-sm"`. The `.btn` base class in `input.css` does NOT include `cursor-pointer`. The `.btn-ghost` and `.btn-sm` classes do not either. The inline style was added to make the anchor behave like a button. 

**Fix:** Add Tailwind class `cursor-pointer` to both `<a>` tags and remove the `style=""` attribute. This class is a standard Tailwind utility — it will be included in output.css as long as it appears literally in a scanned template.

**SSE dark-mode consideration:**
`log_table.html` is rendered server-side and included initially via `{% include %}` in `log.html`. It is also fetched fresh via `htmx.ajax('GET', '/log/view', ...)` on SSE `new_qso` events. The swap replaces `#log-table` innerHTML. Since `log_table.html` uses only Tailwind component classes and `dark:` utilities (no JS-injected styles), dark mode is preserved correctly after SSE swap — the `dark` class lives on `<html>`, which is outside the swap target. No additional SSE-specific treatment is needed.

**Changes needed:**
- Line 100: Remove `style="cursor:pointer;"`, add `cursor-pointer` to class
- Line 118: Remove `style="cursor:pointer;"`, add `cursor-pointer` to class

---

### form.html — DONE, NO CHANGES NEEDED

**File:** `templates/log/form.html`

**What already works:**
- Page header: `text-gray-900 dark:text-white` / `text-gray-500 dark:text-gray-400`
- QSO Entry card: `.card`, `.card-header`, `.card-title`, `.card-body` — correct
- All form fields: `.form-label`, `.form-input font-mono` — correct
- Selects: `.form-select` — correct
- Submit: `.btn-primary`, Clear: `.btn-ghost btn-sm` — correct
- Station Feed card: `.card`, `.card-header`, `.card-title` — correct
- Station Feed table: `.table-wrap` with border customization, `.data-table` — correct
- Footer caption: `dark:border-gray-800 dark:text-gray-500` — correct

**Inline styles:** None found in `form.html`.

**Validation JS:** References `.form-input-error` class — this class exists in `input.css`.

**OPER-02 compliance:** PASS. No changes needed to `form.html`.

---

### import.html — DONE, NO CHANGES NEEDED

**File:** `templates/log/import.html`

**What already works:**
- Page header: correct dark: variants
- Upload card: `.card`, `.card-header`, `.card-title`, `.badge-gray` — correct
- Drop zone: raw Tailwind utilities with full dark: variants (`dark:border-gray-700`, `dark:bg-gray-800/50`, `dark:hover:border-indigo-500`, `dark:hover:bg-indigo-950/20`) — correct
- Submit: `.btn-primary` — correct
- Info card: `.card`, `.card-body` with `dark:bg-indigo-900/40 dark:text-indigo-400` etc. — correct

**Inline styles:** None in `import.html`.

**OPER-03 compliance:** PASS for the page template itself. The gap is in the result partial (see below).

---

### import_report.html — FULL REWRITE REQUIRED

**File:** `templates/log/import_report.html`

**Current state:** Entirely inline-styled. Uses `style="background:white;..."` on wrapper, inline color values for section headings (`#1e8449`, `#856404`, `#c0392b`), bare `<table>` / `<thead>` / `<th>` / `<td>` with no classes. Zero dark-mode support.

This is swapped into `#import-result` in `import.html` after a successful HTMX POST. Any user in dark mode will see a stark white box rendered on a dark canvas — a jarring regression.

**Required rewrite approach:**
- Outer wrapper: replace inline-styled `<div>` with `.card .card-body`
- Summary line: use `text-sm font-semibold text-gray-700 dark:text-gray-300`
- Section headings "Accepted / Duplicates / Errors": use component badges or styled `<h3>` with appropriate text color tokens (`text-emerald-700 dark:text-emerald-400`, `text-amber-700 dark:text-amber-400`, `text-rose-700 dark:text-rose-400`)
- Tables: use `.table-wrap` + `.data-table`
- "No records found" fallback: use `text-gray-500 dark:text-gray-400 text-sm`

**No new CSS classes needed** — all required classes exist in the component library.

---

### qso_row.html — ONE INLINE STYLE TO CONVERT

**File:** `templates/log/qso_row.html`

**Current state:**
```html
<img ... style="vertical-align:middle;margin-right:4px;">
```

This is a flag image rendered inside a `<td>` of the data-table. The inline style handles vertical alignment and spacing.

**Fix:** Replace with Tailwind utilities `inline align-middle mr-1` on the `<img>` tag.

Note: `qso_row.html` is NOT a direct scope item in OPER-01/02/03 (those name `log.html`, `log_table.html`, `form.html`, `import.html`) — but it renders inside the `log_table.html` SSE-swapped partial, so it is in scope for the "no inline style attributes in any partial" rule if interpreted broadly. The plan should include this file as part of the log table cleanup.

---

### qso_row_edit.html — MULTIPLE INLINE STYLES TO CONVERT

**File:** `templates/log/qso_row_edit.html`

**Current state:** Eight `style="width:Npx"` attributes on input elements. Inputs have no class at all — they render as bare browser-default inputs (light-mode only, no dark: styling).

**Fix approach:**
- Add `.form-input` class to all inputs (provides dark-mode bg, border, text colors)
- Replace `style="width:Npx"` with appropriate Tailwind width utilities: `w-24` (90px→96px), `w-16` (60px→64px), `w-20` (80px→80px), `w-10` (40px→40px)
- Use `font-mono` on the text inputs (date, time, call, freq, RST fields)

---

### qso_result.html — ONE INLINE STYLE TO CONVERT

**File:** `templates/log/qso_result.html`

**Current state:**
- `style="flex-direction:column;gap:0.5rem;"` on the duplicate confirmation `<form>`
- `style="display:flex;gap:0.5rem;"` on the button row `<div>`

**Fix approach:**
- Replace `style="flex-direction:column;gap:0.5rem;"` with `class="flex flex-col gap-2"`
- Replace `style="display:flex;gap:0.5rem;"` with `class="flex gap-2"`
- Buttons already use `.danger` (via the legacy alias `button.danger { @apply btn-danger }`) and bare button (via the `button:not([class])` base rule) — these are already handled by the component system

---

## Component Class Mapping

All classes needed for Phase 36 are already defined in `input.css` (Phase 33 deliverable).

| Template Element | Class to Use | Source in input.css |
|-----------------|--------------|---------------------|
| Card container | `.card` | line 73 |
| Card header row | `.card-header` | line 77 |
| Card title text | `.card-title` | line 80 |
| Card body padding | `.card-body` | line 83 |
| Table scroll wrapper | `.table-wrap` | line 104 |
| Table element | `.data-table` | line 108 |
| Form text input | `.form-input` | line 24 |
| Form select | `.form-select` | line 31 |
| Form field label | `.form-label` | line 35 |
| Primary button | `.btn-primary` | line 47 |
| Ghost/outline button | `.btn-ghost` | line 63 |
| Small button modifier | `.btn-sm` | line 69 |
| Green badge | `.badge-green` | line 136 |
| Red badge | `.badge-red` | line 140 |
| Amber/yellow badge | `.badge-blue` (repurpose) OR raw Tailwind | — |
| Gray badge | `.badge-gray` | line 149 |
| Error field ring | `.form-input-error` | line 154 |

Note: There is no `.badge-amber` or `.badge-yellow` in the component library. For the import report "Duplicates" section heading, use raw Tailwind utilities: `text-amber-700 dark:text-amber-400` rather than adding a new badge class. This avoids any new input.css changes.

---

## SSE Mechanism Analysis

**How SSE refresh works in log.html:**

1. `<div id="log-table" hx-ext="sse" sse-connect="/feed/station">` — this div holds the SSE connection
2. On `new_qso` SSE event, the inline JS fires `htmx.ajax('GET', '/log/view', { target: '#log-table', swap: 'innerHTML' })`
3. The server renders `log.html` and extracts the content of `{% include "log/log_table.html" %}` (full page render, then HTMX targets just the `#log-table` div's innerHTML)
4. Actually the HTMX GET to `/log/view` with `target: '#log-table'` and `swap: 'innerHTML'` replaces only the innerHTML of `#log-table`, not the div itself — the SSE connection div is preserved

**Dark-mode correctness after SSE swap:**
- The `dark` class lives on `<html>` (toggled by `toggleTheme()` in base.html)
- `log_table.html` uses only static class strings (`dark:bg-gray-900`, `dark:border-gray-800`, etc.) — these resolve correctly at paint time regardless of when the DOM was inserted
- There is no JS that needs to run after swap to apply dark classes
- The existing `htmx:afterSettle` handler in `base_app.html` calls `updateThemeIcons()` — this syncs the theme toggle button icon but does not affect the log table

**Conclusion:** SSE dark-mode is already architecturally correct. The only fix needed is removing the two inline `cursor:pointer` styles that bypass the class system.

---

## Inline Style Inventory (All Templates)

| File | Line | Inline Style | Fix |
|------|------|-------------|-----|
| `log_table.html` | 100 | `style="cursor:pointer;"` | Add `cursor-pointer` class |
| `log_table.html` | 118 | `style="cursor:pointer;"` | Add `cursor-pointer` class |
| `qso_row.html` | 9 | `style="vertical-align:middle;margin-right:4px;"` | Add `inline align-middle mr-1` classes |
| `qso_row_edit.html` | 3 | `style="width:90px"` | Add `w-24` class + `.form-input font-mono` |
| `qso_row_edit.html` | 4 | `style="width:60px"` | Add `w-16` class + `.form-input font-mono` |
| `qso_row_edit.html` | 6 | `style="width:80px"` | Add `w-20` class + `.form-input font-mono uppercase` |
| `qso_row_edit.html` | 7 | `style="width:60px"` | Add `w-16` class + `.form-input font-mono` |
| `qso_row_edit.html` | 8 | `style="width:60px"` | Add `w-16` class + `.form-input font-mono` |
| `qso_row_edit.html` | 9 | `style="width:80px"` | Add `w-20` class + `.form-input font-mono` |
| `qso_row_edit.html` | 11 | `style="width:40px"` | Add `w-10` class + `.form-input font-mono` |
| `qso_row_edit.html` | 12 | `style="width:40px"` | Add `w-10` class + `.form-input font-mono` |
| `import_report.html` | 1 | `style="background:white;..."` | Rewrite with `.card .card-body` |
| `import_report.html` | 2 | `style="margin:...;font-weight:600;"` | Replace with Tailwind classes |
| `import_report.html` | 10 | `style="...color:#1e8449;..."` | Replace with `text-emerald-700 dark:text-emerald-400` |
| `import_report.html` | 32 | `style="...color:#856404;..."` | Replace with `text-amber-700 dark:text-amber-400` |
| `import_report.html` | 56 | `style="...color:#c0392b;..."` | Replace with `text-rose-700 dark:text-rose-400` |
| `import_report.html` | 80 | `style="color:#555;"` | Replace with `text-gray-500 dark:text-gray-400 text-sm` |
| `qso_result.html` | 9 | `style="flex-direction:column;gap:0.5rem;"` | Add `flex flex-col gap-2` class |
| `qso_result.html` | 18 | `style="display:flex;gap:0.5rem;"` | Add `flex gap-2` class |

---

## New CSS Classes Needed in input.css

**None.** All required visual states are covered by the Phase 33 component library. Do not add to `input.css`.

---

## Tailwind Purge / Build Rules

The Tailwind content scanner is configured for `./templates/**/*.html` (verified in `tailwind.config.js`). Build command: `npm run build` (runs `tailwindcss -i ... -o ... --minify --postcss`).

New Tailwind utility classes being added in this phase:
- `cursor-pointer` — already a standard Tailwind class, will be included when it appears literally in a template
- `inline`, `align-middle`, `mr-1` — standard utilities, will be included
- `w-24`, `w-16`, `w-20`, `w-10` — standard utilities, will be included
- `flex`, `flex-col`, `gap-2` — standard utilities, will be included
- `text-amber-700`, `dark:text-amber-400` — standard utilities, will be included

All of these are standard Tailwind v3 utilities that appear as literal strings in the template files being edited. No safelisting required.

**Verification step after each template change:** `npm run build` then grep the output.css for the new class names to confirm they were captured.

---

## Pagination Controls Analysis

**Location:** `log_table.html` lines 83–127

**Current structure:**
- Outer div: `flex items-center justify-between px-1 mt-4` — correct Tailwind layout
- Count text: `text-sm text-gray-500 dark:text-gray-400` with `text-gray-700 dark:text-gray-300` for numbers — correct
- Previous / Next: `class="btn-ghost btn-sm"` on `<a>` tags with HTMX attributes — correct
- Page indicator: `text-sm text-gray-500 dark:text-gray-400 px-2` — correct

**Only fix needed:** Remove the two `style="cursor:pointer;"` inline attributes (OPER-01 violation). Add `cursor-pointer` to the class string on each `<a>`.

The pagination is NOT missing Apple component token classes — it already uses the component system correctly via `.btn-ghost btn-sm`.

---

## Architecture Patterns

### Pattern 1: Template-Only Change (No Python)
All changes are HTML class additions/removals. No Python routes, models, or schemas are touched. The build pipeline is:
1. Edit template
2. `npm run build` in `/Users/royco/ollog`
3. Verify class appears in `output.css`
4. Manual browser check for dark mode

### Pattern 2: Partial-Safe Dark Mode
When editing partials that are HTMX/SSE-swapped (`log_table.html`, `import_report.html`, `qso_row.html`, `qso_row_edit.html`, `qso_result.html`), use only Tailwind `dark:` utility classes — never inline styles, never JS-applied styles. The `dark` class on `<html>` is always present during partial re-renders.

### Pattern 3: Component Class First, Raw Tailwind Second
Use defined component classes (`.card`, `.data-table`, etc.) for structural elements. Use raw Tailwind utilities only for layout, spacing, and color variants not covered by a component class. Never add one-off CSS to `input.css` for this phase.

### Anti-Patterns to Avoid
- **Inline style attributes:** Zero tolerance per OPER-01. Every `style=""` found must be converted.
- **Hardcoded light-mode colors:** `background:white`, `color:#1e8449`, `color:#555` etc. in partials break dark mode.
- **Adding new component classes to input.css:** Not needed and adds risk of build issues.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Dark-mode card wrapper | Custom CSS | `.card` (already dark-mode aware) |
| Styled table | Custom CSS | `.table-wrap` + `.data-table` |
| Colored section headings in import report | Inline styles | Raw `text-*-700 dark:text-*-400` utilities |
| Amber badge variant | New `.badge-amber` in input.css | Raw `text-amber-700 dark:text-amber-400` on existing elements |
| Cursor on HTMX anchor | `style="cursor:pointer"` | `cursor-pointer` Tailwind class |

---

## Common Pitfalls

### Pitfall 1: cursor-pointer Not in btn Base Class
**What goes wrong:** The `.btn` base class in `input.css` does not include `cursor-pointer`. This was intentional (buttons are already pointer by default). Anchors styled as buttons need `cursor-pointer` added explicitly as a Tailwind utility.
**How to avoid:** Add `cursor-pointer` as a class, not via inline style.

### Pitfall 2: import_report.html Tables Need table-wrap Wrapper
**What goes wrong:** `.data-table` needs to be inside `.table-wrap` for the rounded border and overflow behavior. Forgetting the wrapper produces an unstyled table edge.
**How to avoid:** Always wrap `.data-table` in a `<div class="table-wrap">`.

### Pitfall 3: Purge Miss for Dynamically-Built Class Strings
**What goes wrong:** If a class is assembled in Python or Jinja2 string concatenation (e.g., `"text-" + color + "-700"`), Tailwind's static scanner misses it.
**How to avoid:** All class names in this phase are static literal strings in the HTML templates. No dynamic construction.

### Pitfall 4: Amber/Yellow Variants Not in Badge Component
**What goes wrong:** Assuming `.badge-amber` or `.badge-yellow` exists — it does not. Only `badge-green`, `badge-red`, `badge-blue`, `badge-gray` are defined.
**How to avoid:** Use raw `text-amber-700 dark:text-amber-400` utilities for the Duplicates section in import_report.html.

### Pitfall 5: qso_row_edit.html Inputs in TD Context
**What goes wrong:** Adding full-width `form-input` to inputs inside narrow `<td>` cells causes column overflow.
**How to avoid:** Pair `.form-input` with an explicit width class (`w-24`, `w-16`, etc.) to constrain the input within the cell.

---

## Code Examples

### Pagination anchor fix (log_table.html)
```html
<!-- BEFORE -->
<a class="btn-ghost btn-sm"
   hx-get="..."
   hx-target="#log-table"
   hx-swap="innerHTML"
   hx-push-url="true"
   style="cursor:pointer;">

<!-- AFTER -->
<a class="btn-ghost btn-sm cursor-pointer"
   hx-get="..."
   hx-target="#log-table"
   hx-swap="innerHTML"
   hx-push-url="true">
```

### import_report.html outer card structure
```html
<!-- BEFORE -->
<div style="background:white;border-radius:6px;padding:1rem 1.2rem;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
  <p style="margin:0 0 0.8rem;font-weight:600;">...</p>
  ...
</div>

<!-- AFTER -->
<div class="card">
  <div class="card-body space-y-4">
    <p class="text-sm font-semibold text-gray-700 dark:text-gray-300">...</p>
    ...
  </div>
</div>
```

### import_report.html section heading with dark mode
```html
<!-- BEFORE -->
<h3 style="font-size:0.9rem;text-transform:uppercase;letter-spacing:0.05em;color:#1e8449;margin:0.8rem 0 0.4rem;">
  Accepted ({{ report.accepted | length }})
</h3>

<!-- AFTER -->
<h3 class="text-xs font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-400 mt-3 mb-1.5">
  Accepted ({{ report.accepted | length }})
</h3>
```

### import_report.html table structure
```html
<!-- BEFORE -->
<table>
  <thead>
    <tr><th>Record #</th><th>Callsign</th></tr>
  </thead>
  <tbody>...</tbody>
</table>

<!-- AFTER -->
<div class="table-wrap">
  <table class="data-table">
    <thead>
      <tr><th>Record #</th><th>Callsign</th></tr>
    </thead>
    <tbody>...</tbody>
  </table>
</div>
```

### qso_row_edit.html input fix
```html
<!-- BEFORE -->
<input type="text" name="CALL" value="{{ qso.CALL }}" style="width:80px">

<!-- AFTER -->
<input type="text" name="CALL" value="{{ qso.CALL }}" class="form-input font-mono uppercase w-20">
```

### qso_row.html flag image fix
```html
<!-- BEFORE -->
<img src="/static/flags/{{ qso.flag_iso }}.svg"
     width="20" height="15"
     alt="{{ qso.flag_country or '' }}"
     title="{{ qso.flag_country or '' }}"
     style="vertical-align:middle;margin-right:4px;">

<!-- AFTER -->
<img src="/static/flags/{{ qso.flag_iso }}.svg"
     width="20" height="15"
     alt="{{ qso.flag_country or '' }}"
     title="{{ qso.flag_country or '' }}"
     class="inline align-middle mr-1">
```

### qso_result.html flex container fix
```html
<!-- BEFORE -->
<form ... style="flex-direction:column;gap:0.5rem;">
  ...
  <div style="display:flex;gap:0.5rem;">

<!-- AFTER -->
<form ... class="flex flex-col gap-2">
  ...
  <div class="flex gap-2">
```

---

## Task Decomposition Recommendation for Planner

The planner should produce these tasks in order:

**Task 1: log_table.html — Remove inline cursor styles (OPER-01)**
- Remove two `style="cursor:pointer;"` attributes (lines 100, 118)
- Add `cursor-pointer` class to both `<a>` pagination buttons
- Build and verify `cursor-pointer` in output.css

**Task 2: import_report.html — Full rewrite to component classes (OPER-03)**
- Rewrite outer wrapper with `.card .card-body`
- Rewrite summary paragraph with Tailwind text utilities
- Rewrite three section headings with color token utilities + dark variants
- Wrap each table in `.table-wrap` and add `.data-table` class
- Replace "no records" paragraph with dark-safe text classes
- Build and verify new class names in output.css

**Task 3: qso_row.html — Convert flag img inline style (OPER-01 / table partial)**
- Replace `style="vertical-align:middle;margin-right:4px;"` with `class="inline align-middle mr-1"`
- Build and verify

**Task 4: qso_row_edit.html — Convert input inline styles (OPER-01 / table partial)**
- Add `.form-input` and appropriate width classes to all 8 inputs
- Remove all `style="width:Npx"` attributes
- Build and verify

**Task 5: qso_result.html — Convert flex inline styles**
- Replace two inline flex styles with Tailwind classes
- Build and verify

**Task 6: Integration verification**
- Manual browser test: log view in dark mode, trigger SSE swap (or simulate with HTMX GET), confirm colors correct
- Check import report in dark mode
- Check QSO edit row in dark mode
- Confirm zero `style=""` attributes remain in operator partials

---

## Open Questions

1. **Phase 36 scope boundary for qso_row.html / qso_row_edit.html / qso_result.html**
   - What we know: OPER-01 names `log.html` and `log_table.html` explicitly. These three partial files render inside or alongside the named templates.
   - What's unclear: Whether these three files are explicitly in scope for Phase 36 or deferred.
   - Recommendation: Include them. OPER-01 says "no inline style attributes in any partial." These files are partials that render inside the operator log view. Excluding them leaves OPER-01 non-compliant.

---

## Sources

### Primary (HIGH confidence)
- Direct source inspection of `/Users/royco/ollog/static/css/input.css` — full component library
- Direct source inspection of `/Users/royco/ollog/tailwind.config.js` — token definitions
- Direct source inspection of `/Users/royco/ollog/templates/log/log.html` — SSE mechanism, log.html state
- Direct source inspection of `/Users/royco/ollog/templates/log/log_table.html` — partial structure, inline styles
- Direct source inspection of `/Users/royco/ollog/templates/log/form.html` — form state
- Direct source inspection of `/Users/royco/ollog/templates/log/import.html` — import page state
- Direct source inspection of `/Users/royco/ollog/templates/log/import_report.html` — inline-styled partial
- Direct source inspection of `/Users/royco/ollog/templates/log/qso_row.html` — flag img inline style
- Direct source inspection of `/Users/royco/ollog/templates/log/qso_row_edit.html` — input inline styles
- Direct source inspection of `/Users/royco/ollog/templates/log/qso_result.html` — flex inline styles
- Direct source inspection of `/Users/royco/ollog/package.json` and `postcss.config.js` — build pipeline

---

## Metadata

**Confidence breakdown:**
- Current template state: HIGH — read directly from source files
- Component class applicability: HIGH — all classes verified in input.css
- SSE dark-mode behavior: HIGH — mechanism fully traced in log.html + base_app.html
- Inline style inventory: HIGH — found via direct grep across all template files
- Build pipeline: HIGH — verified from package.json and postcss.config.js

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (stable — no external dependencies, all source material is local)
