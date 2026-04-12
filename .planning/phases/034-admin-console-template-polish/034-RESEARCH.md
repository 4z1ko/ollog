# Phase 34: Admin Console Template Polish — Research

**Researched:** 2026-04-11
**Domain:** Jinja2 template HTML, Tailwind CSS component classes, ARIA accessibility
**Confidence:** HIGH — all findings verified by direct code inspection

---

## Summary

Phase 33 delivered a complete component class library (`.card`, `.btn-*`, `.badge-*`, `.data-table`, `.nav-item`, etc.) and the operator-facing `base_app.html` was already updated to use `w-6 h-6` nav icons and canvas tokens. The admin console (`users.html`, `users_table.html`) extends `base_app.html` and overrides its `sidebar_nav`, `sidebar_user`, and `sidebar_logout` blocks, so the admin sidebar is assembled entirely in `users.html` via Jinja2 block overrides — there is no separate `templates/admin/base.html`.

The admin templates are in better shape than expected. `users.html` already uses `.card`, `.card-header`, `.card-title`, `.card-body`, `.btn-primary`, `.data-table`, `.table-wrap`, and `.form-input`. The three outstanding gaps are: (1) admin sidebar nav icons use `w-5 h-5` instead of `w-6 h-6`; (2) the sidebar background is `bg-sidebar` (`#1a1d2e`), not the Apple dark surface `#1c1c1e` that ADMN-02 requires; (3) action buttons in `users_table.html` have no icons and no `aria-label` attributes.

**Primary recommendation:** Three targeted template edits — `users.html` for sidebar icon sizing and sidebar background, `users_table.html` for `aria-label` attributes and icons on action buttons — plus one CSS addition if the `#1c1c1e` sidebar background is needed. No Python changes, no structural rewrites.

---

## Current State of Admin Templates

### `templates/admin/users.html`

This template extends `base_app.html` and overrides three blocks:

**`{% block sidebar_nav %}`** — Contains one `<a>` with class `nav-item nav-item-active` linking to `/admin/ui/users`. Its SVG icon uses `w-5 h-5` (20px), not `w-6 h-6` (24px). This violates DSGN-06 / ADMN-02.

**`{% block sidebar_user %}`** — Static "Admin / Administrator" user widget. Uses violet-500 badge, `text-white`, `text-sidebar-text`. No issues here — this block is cosmetically correct.

**`{% block sidebar_logout %}`** — Logout link to `/admin/ui/logout` with `nav-item` class. Its SVG icon also uses `w-5 h-5`. Must be updated to `w-6 h-6`.

**`{% block content %}`** — Page content. Already uses:
- `.card`, `.card-header`, `.card-title`, `.card-body` on the Create Operator form
- `.card overflow-hidden` + `.table-wrap rounded-none border-0 border-t ...` + `.data-table` on the operators table
- `.btn-primary` with `w-4 h-4` icon (correct for action button size) on the Create button
- `.form-input`, `.form-label` on all form fields

The content section is already compliant with ADMN-01. The card structure, typography tokens, and table layout are correctly applied.

### `templates/admin/users_table.html`

This is an HTMX partial (swapped into `#users-table-body`). It renders:
- Error/success alert rows using `.alert-error` / `.alert-success` (correct)
- Per-user table rows with `.badge-blue`/`.badge-gray` for role, `.badge-green`/`.badge-red` for status (correct)
- Action cell containing:
  - Toggle button: `class="{{ 'btn-danger' if user.enabled else 'btn-success' }} btn-sm"` — text-only ("Disable"/"Enable"), **no icon, no `aria-label`**
  - Reset password: inline `<form>` with `.form-input w-36` password field and `class="btn-secondary btn-sm"` submit button labeled "Reset" — **no icon, no `aria-label`**

ADMN-03 requires: icons on all three action buttons AND `aria-label` attributes identifying both the action and the target operator.

### `templates/admin/login.html`

Extends `base.html` (not `base_app.html`). Has a standalone dark-gradient login page. **Not targeted by any ADMN requirement.** Out of scope for this phase.

### There is NO `templates/admin/base.html`

The admin sidebar is constructed entirely through Jinja2 block overrides in `users.html`. Every admin sidebar element lives in `users.html`.

---

## Sidebar Architecture: Admin vs. Operator

| Aspect | Operator sidebar (`base_app.html`) | Admin sidebar (`users.html` blocks) |
|--------|------------------------------------|--------------------------------------|
| Background | `bg-sidebar` (`#1a1d2e`) via `<aside class="... bg-sidebar ...">` in `base_app.html` | Same `bg-sidebar` inherited — `base_app.html` renders the `<aside>` element |
| Nav icons | `w-6 h-6` (updated in Phase 33) | `w-5 h-5` (NOT updated — needs fix) |
| Logout icon | `w-6 h-6` (in `sidebar_logout` default block) | `w-5 h-5` in overridden block in `users.html` |
| Active state | `nav-item-active` conditional | `nav-item-active` hardcoded (only one nav item) |

**Critical insight on sidebar background:** The `<aside>` element with `bg-sidebar` is in `base_app.html`, NOT in any overridable block. `users.html` cannot change the sidebar background color by overriding a block — it would require either: (a) adding a new `{% block sidebar_class %}` block to `base_app.html`, or (b) defining a new CSS class that overrides `bg-sidebar` for admin context, or (c) accepting that the admin sidebar uses `bg-sidebar` (`#1a1d2e`) in both modes.

ADMN-02 says "Admin sidebar background uses `#1c1c1e` in dark mode." The token `surface.dark` is `#1c1c1e`. In light mode `bg-sidebar` (`#1a1d2e`) is fine — it's dark either way. The ADMN-02 requirement specifically calls out dark mode.

**Resolution for ADMN-02 sidebar background:** Add a `{% block sidebar_class %}{% endblock %}` extension point to `base_app.html`'s `<aside>` class list, then in `users.html` emit `dark:bg-surface-dark` as a literal class string. Since `dark:bg-surface-dark` is not currently in `output.css` (only `.card:is(.dark *)` uses the `surface.dark` token), this class must appear as a literal string in a scanned template to pass Tailwind purge. Writing `dark:bg-surface-dark` in `users.html` will cause Tailwind to include it.

---

## Phase 33 Component Classes: Direct-Apply vs. Needs-New-CSS

### Can Apply Directly (No New CSS)

| Component | Class | Where Applied |
|-----------|-------|---------------|
| Card container | `.card` | Already in `users.html` — ADMN-01 satisfied |
| Card header | `.card-header` | Already in `users.html` |
| Card title | `.card-title` | Already in `users.html` |
| Card body | `.card-body` | Already in `users.html` |
| Data table | `.data-table` | Already in `users.html` |
| Table wrap | `.table-wrap` | Already in `users.html` |
| Form inputs | `.form-input` | Already in `users.html` and `users_table.html` |
| Badges | `.badge-green`, `.badge-red`, `.badge-blue`, `.badge-gray` | Already in `users_table.html` |
| Buttons | `.btn-danger`, `.btn-success`, `.btn-secondary`, `.btn-sm` | Already in `users_table.html` |
| Nav items | `.nav-item`, `.nav-item-active` | Already in `users.html` |

### Needs New/Modified Usage

| Problem | Current | Required Change |
|---------|---------|-----------------|
| Admin sidebar `#1c1c1e` dark bg | `bg-sidebar` (`#1a1d2e`) on `<aside>` in `base_app.html` | Add `{% block sidebar_class %}{% endblock %}` to `<aside>` in `base_app.html`; in `users.html` emit `dark:bg-surface-dark` in that block |
| Nav icon size | `w-5 h-5` in `users.html` block overrides | Change to `w-6 h-6` in all SVGs within `sidebar_nav` and `sidebar_logout` blocks |
| Action button icons | No icons on toggle/reset buttons | Add `w-4 h-4` SVG icons before button text in `users_table.html` |
| Action button aria-labels | No `aria-label` attributes | Add `aria-label="{{ 'Disable' if user.enabled else 'Enable' }} {{ user.username }}"` to toggle button; `aria-label="Reset password for {{ user.username }}"` to reset submit button |

---

## Exact Changes Needed

### ADMN-01: Admin Operator Table (already complete)

The `users.html` content block already uses `.card`, `.card-header`, `.card-title`, `.card-body`, `.data-table`, `.table-wrap`. **No changes required for ADMN-01.** The requirement states "no raw table-without-card layout remains" — the card container is already present.

### ADMN-02: Admin Sidebar Background and Spacing

**File: `templates/base_app.html`** — The `<aside>` tag currently reads:
```
class="fixed inset-y-0 left-0 z-30 w-64 bg-sidebar flex flex-col ..."
```
Add a new Jinja2 block inside the class attribute to allow per-child-template override:
```
class="fixed inset-y-0 left-0 z-30 w-64 bg-sidebar {% block sidebar_class %}{% endblock %} flex flex-col ..."
```

**File: `templates/admin/users.html`** — Add new block:
```
{% block sidebar_class %}dark:bg-surface-dark{% endblock %}
```

This emits `dark:bg-surface-dark` as a literal class string in a Tailwind-scanned template, ensuring the utility is included in `output.css` after `npm run build`.

Nav spacing in `base_app.html` is already `px-3 py-4 space-y-0.5` (generous padding). The `nav-item` class provides `px-3 py-2` per item. No padding changes needed.

**File: `templates/admin/users.html`** — Change all `w-5 h-5` to `w-6 h-6` in the `sidebar_nav` and `sidebar_logout` block overrides. There are 2 SVG icons to update:
- Operators nav link icon (line 9)
- Logout link icon (line 32)

### ADMN-03: Action Button Icons and aria-labels

**File: `templates/admin/users_table.html`**

**Toggle button** (currently line 45-50): Add `aria-label` and icon SVG.

The button renders either "Disable" (when enabled=true, using `btn-danger`) or "Enable" (when enabled=false, using `btn-success`). The `aria-label` must identify both action and target:
- `aria-label="{{ 'Disable' if user.enabled else 'Enable' }} operator {{ user.username }}"`

Icon choice:
- Disable: use a prohibit/X-circle icon at `w-4 h-4`
- Enable: use a check-circle icon at `w-4 h-4`

Jinja2 conditional icon SVG block pattern:
```html
{% if user.enabled %}
<svg class="w-4 h-4" ...><!-- X or stop icon --></svg>
{% else %}
<svg class="w-4 h-4" ...><!-- Check icon --></svg>
{% endif %}
```

**Reset password button** (currently line 58): Add `aria-label` and icon SVG.
- `aria-label="Reset password for {{ user.username }}"`
- Icon: key or lock-open icon at `w-4 h-4`

---

## Build Rules and Purge Safety

### Purge Requirements for New Classes

| New Class | File Where It Must Appear as Literal String | Status |
|-----------|---------------------------------------------|--------|
| `dark:bg-surface-dark` | `templates/admin/users.html` | Will be NEW — must be written exactly |
| `w-6 h-6` | Already in `base_app.html` (scanned) | Already compiled |
| `w-4 h-4` | Already in `users.html` and `users_table.html` | Already compiled |

After any template change, run:
```bash
npm run build
grep "surface-dark" static/css/output.css
```

Expected output after build: `dark\:bg-surface-dark:is(.dark *)` rule with `background-color:rgb(28 28 30/...)`.

### Transition Flash Rule

The `<aside>` element in `base_app.html` currently has `transition-transform duration-200` for mobile slide animation. This is scoped to transform only, not color. Adding `dark:bg-surface-dark` to the aside does not trigger the flash rule (which prohibits `transition-*` on `<body>`, `<html>`, or `*` in `@layer base`). Safe to proceed.

### No Python Changes

All three requirements (ADMN-01, ADMN-02, ADMN-03) are pure HTML template edits. No routes, no models, no schemas, no Python files touched.

---

## Common Pitfalls

### Pitfall 1: Assuming `dark:bg-surface-dark` is already compiled

**What goes wrong:** Developer references `dark:bg-surface-dark` in a template but it is not in `output.css` because no template previously used it as a literal class string. The sidebar remains `#1a1d2e` in dark mode.

**Why it happens:** Tailwind's content scanner only includes classes that appear as complete literal strings in scanned files. The `surface.dark` color token is used by `.card` via `@apply bg-surface-dark` in input.css, which works because `@apply` is in the CSS (not scanned as template). Template usage of `dark:bg-surface-dark` as a utility class is a separate entry in output.css.

**How to avoid:** After editing `users.html` to include `dark:bg-surface-dark`, run `npm run build` and verify: `grep "surface-dark" static/css/output.css`.

### Pitfall 2: Editing `base_app.html` `<aside>` class breaks operator sidebar

**What goes wrong:** Adding a Jinja2 block to the `<aside>` class string inadvertently adds whitespace or breaks the class list for operator templates that don't override the new block.

**How to avoid:** The `{% block sidebar_class %}{% endblock %}` default is empty — operator templates inherit no change. Verify the operator sidebar visually after build.

### Pitfall 3: `aria-label` must contain the specific operator's username

**What goes wrong:** Generic `aria-label="Disable operator"` on every row — screen readers cannot distinguish which operator is targeted.

**How to avoid:** Use `{{ user.username }}` in the `aria-label` value. This is a Jinja2 template expression that resolves at render time and is safe in HTML attributes.

### Pitfall 4: Icon size inconsistency — `w-4 h-4` vs `w-5 h-5`

**What goes wrong:** Using `w-5 h-5` (20px) for action button icons inside `btn-sm` buttons — too large for the small button variant.

**How to avoid:** Per phase build rules: `w-4 h-4` (16px) for secondary action icons. The `btn-sm` class produces `px-3 py-1.5 text-xs` — `w-4 h-4` is the correct companion size.

---

## Architecture Patterns

### Pattern 1: Jinja2 Block Override for Sidebar Customization

`base_app.html` renders the `<aside>` shell; child templates override `sidebar_nav`, `sidebar_user`, and `sidebar_logout` blocks. For per-child background color, add a fourth block `sidebar_class` inside the `<aside>` class attribute:

```html
<!-- In base_app.html <aside> tag: -->
<aside id="sidebar"
       class="fixed inset-y-0 left-0 z-30 w-64 bg-sidebar {% block sidebar_class %}{% endblock %} flex flex-col
              -translate-x-full transition-transform duration-200 ease-in-out
              md:relative md:translate-x-0 md:flex-shrink-0">
```

```html
{# In users.html: #}
{% block sidebar_class %}dark:bg-surface-dark{% endblock %}
```

This pattern is minimal-invasive: operator templates continue to work unchanged (empty block = no extra class), admin gets `dark:bg-surface-dark` appended.

### Pattern 2: Conditional Icon SVG in HTMX Partials

For toggle buttons that switch between two states:

```html
<button
  hx-post="/admin/ui/users/{{ user.username }}/toggle"
  hx-target="#users-table-body"
  hx-swap="innerHTML"
  aria-label="{{ 'Disable' if user.enabled else 'Enable' }} operator {{ user.username }}"
  class="{{ 'btn-danger' if user.enabled else 'btn-success' }} btn-sm"
>
  {% if user.enabled %}
  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 0 0 5.636 5.636m12.728 12.728A9 9 0 0 1 5.636 5.636m12.728 12.728L5.636 5.636" />
  </svg>
  Disable
  {% else %}
  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
  </svg>
  Enable
  {% endif %}
</button>
```

### Pattern 3: aria-label on Submit Buttons Inside Forms

```html
<button type="submit"
        aria-label="Reset password for {{ user.username }}"
        class="btn-secondary btn-sm">
  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 0 1 21.75 8.25Z" />
  </svg>
  Reset
</button>
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dark-mode surface color for sidebar | Custom CSS variable or inline style | `dark:bg-surface-dark` utility + `surface.dark` token already in tailwind.config.js | Token is already defined; utility just needs to appear in a template |
| Accessible button labels | Custom JS tooltip or visually-hidden span | Native `aria-label` HTML attribute | Screen readers read `aria-label` directly; zero extra CSS or JS |
| Small action button styling | Custom `.admin-action-btn` class | `.btn-sm` modifier already in input.css | Consistent with existing button system |
| Status icon in buttons | Custom icon component | Inline Heroicons SVG at `w-4 h-4` | Matches existing pattern in `users.html` Create button |

---

## Open Questions

1. **Sidebar background in light mode**
   - What we know: ADMN-02 says "uses `#1c1c1e` in dark mode" — no light mode spec for admin sidebar
   - What's unclear: Should admin sidebar light mode differ from operator (`#1a1d2e`)? The requirement only specifies dark mode
   - Recommendation: Apply only `dark:bg-surface-dark` (dark mode override); leave light mode as `bg-sidebar` (`#1a1d2e`) — both are dark-ish colors and the distinction is imperceptible in light mode

2. **`users_table.html` icon SVG paths — exact Heroicons to use**
   - What we know: Must use `w-4 h-4`, `fill="none"`, `stroke-width="1.5"`, `stroke="currentColor"` to match existing patterns
   - What's unclear: Specific icon choice (no spec given beyond "correctly-sized icon")
   - Recommendation: Disable = `no-symbol` (circle with slash); Enable = `check-circle`; Reset = `key` — all from Heroicons outline set, matching the existing icon style throughout the app

---

## Sources

### Primary (HIGH confidence — direct code inspection)

- `/Users/royco/ollog/templates/admin/users.html` — admin page template, sidebar blocks, content structure
- `/Users/royco/ollog/templates/admin/users_table.html` — HTMX partial, action button HTML
- `/Users/royco/ollog/templates/admin/login.html` — confirmed out of scope
- `/Users/royco/ollog/templates/base_app.html` — sidebar HTML structure, block definitions, icon sizes
- `/Users/royco/ollog/templates/base.html` — base HTML shell
- `/Users/royco/ollog/static/css/input.css` — all component class definitions
- `/Users/royco/ollog/tailwind.config.js` — color token values including `surface.dark: '#1c1c1e'` and `sidebar.DEFAULT: '#1a1d2e'`
- `/Users/royco/ollog/static/css/output.css` — confirmed `dark:bg-surface-dark` not yet compiled; confirmed `.btn-success`, `.bg-sidebar` present
- `.planning/phases/033-design-tokens-and-css-component-system/033-VERIFICATION.md` — Phase 33 deliverables confirmed

---

## Metadata

**Confidence breakdown:**

- Current template state (ADMN-01 already done, icon sizes, missing aria-labels): HIGH — direct inspection of all template files
- Sidebar background approach (block extension pattern): HIGH — direct inspection of base_app.html block structure
- Purge safety of `dark:bg-surface-dark`: HIGH — verified by inspecting output.css (not present) and tailwind.config.js (token defined)
- Heroicon SVG path strings: MEDIUM — specific `d=` attribute values should be verified against Heroicons v2 at implementation time

**Research date:** 2026-04-11
**Valid until:** Stable — HTML/Tailwind, no fast-moving dependencies. Valid until templates are structurally changed.
