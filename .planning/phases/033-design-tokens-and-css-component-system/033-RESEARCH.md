# Phase 33: Design Tokens and CSS Component System - Research

**Researched:** 2026-04-11
**Domain:** Tailwind CSS design tokens, @layer components, Apple Human Interface Guidelines color palette, CSS custom properties
**Confidence:** HIGH

---

## Summary

Phase 33 is a surgical CSS and config rewrite — no Python, no routes, no JS. The deliverable is a revised `tailwind.config.js` and `input.css` that encode Apple-calibrated design tokens and produce a verified component class library in `output.css`. The templates already consume the component classes (`.card`, `.btn-*`, `.form-input`, `.badge-*`, `.data-table`, `.card-title`) — they were written in anticipation of this token layer. Only `input.css` and `tailwind.config.js` change in this phase; templates are read-only.

The component class library already exists in `input.css` but uses placeholder Tailwind gray palette colors that don't match the Apple token spec. Four specific changes are required:
1. **Background canvas tokens** — replace `bg-slate-50 dark:bg-gray-950` in `base_app.html` with token-driven values (but these are hardcoded inline, not via component classes, so the token must land in `tailwind.config.js` as named colors or the templates must be updated to use new token class names).
2. **Card surface tokens** — `.card` currently uses `bg-white dark:bg-gray-900`; DSGN-01 requires `white` in light mode and `#1c1c1e` in dark mode. `gray-900` is `#111827`, not `#1c1c1e`. This is a precise change to `.card` in `input.css`.
3. **System font stack** — `tailwind.config.js` currently has `Inter` first in `fontFamily.sans`; `input.css` `@layer base` also hardcodes `Inter`. Google Fonts CDN links exist in `base.html` (lines 34-36). DSGN-02 requires removing Inter and using `-apple-system, BlinkMacSystemFont` as first entries. This touches three files.
4. **Badge shape** — all four badge classes (`.badge-green`, `.badge-red`, `.badge-blue`, `.badge-gray`) use `rounded-full` (pill). DSGN-04 requires `rounded-md` (rectangular with visible rounding). Change is in `input.css` only, four lines.

Card shadow (DSGN-03), card-title typography (DSGN-05), and icon sizing (DSGN-06) need to be audited — some are partially correct, some need token additions.

**Primary recommendation:** Treat this as five targeted changes to `tailwind.config.js` and `input.css` (plus removing three CDN link lines from `base.html`), then run `npm run build` and verify `output.css` contains each component class. Do not rewrite the entire file — preserve all working component classes.

---

## Current State Audit (Confirmed by Codebase Inspection)

### tailwind.config.js — confirmed state

```js
module.exports = {
  darkMode: 'class',
  content: ['./templates/**/*.html'],
  theme: {
    extend: {
      colors: {
        sidebar: { DEFAULT: '#1a1d2e', hover: '#252941', active: '#4338ca', border: '#2d3561', text: '#c4c9e4' },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
```

**Problems:**
- `Inter` leads the `fontFamily.sans` stack — violates DSGN-02
- No Apple canvas/card surface colors defined as tokens
- No shadow tokens for DSGN-03 two-layer depth

### input.css — confirmed state (relevant sections)

| Component class | Current value | Required change |
|----------------|--------------|-----------------|
| `html` base | `font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif;` | Remove Inter; lead with `-apple-system, BlinkMacSystemFont` |
| `.card` | `bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm` | dark surface → `#1c1c1e`; light shadow → two-layer depth; dark shadow → none |
| `.badge-green` | `rounded-full` | Change to `rounded-md` |
| `.badge-red` | `rounded-full` | Change to `rounded-md` |
| `.badge-blue` | `rounded-full` | Change to `rounded-md` |
| `.badge-gray` | `rounded-full` | Change to `rounded-md` |
| `.card-title` | `text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider` | DSGN-05: remove `uppercase tracking-wider`; use sentence-case `font-semibold` |
| `.data-table` | Already correct structure | No change required |
| `.form-input` | Already correct structure | No change required |
| `.btn-*` | Already correct structure | No change required |

### base_app.html — canvas background

The page canvas and main element use inline classes, not component classes:
- Line 8: `bg-slate-50 dark:bg-gray-950` (outer flex container)
- Line 147: `bg-slate-50 dark:bg-gray-950 p-6` (main content area)

`bg-slate-50` = `#f8fafc` — DSGN-01 requires `#f2f2f7` (Apple systemGroupedBackground)
`bg-gray-950` = `#030712` — DSGN-01 requires `#0f0f0f`

This means the template must be updated to use new named token classes, OR new token names must be defined that map to these exact colors. The best approach: define `canvas` color tokens in `tailwind.config.js` (alongside `sidebar`), then update `base_app.html` to use them.

### base.html — Google Fonts CDN

Lines 34-36 contain three CDN links that must be removed per DSGN-02:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

After removal, no external font requests will appear in the network tab — satisfied by system font fallback chain.

### Nav icons — confirmed state

All nav icons in `base_app.html` use `w-5 h-5` (20px), not `w-6 h-6` (24px). DSGN-06 requires `w-6 h-6` for prominent nav/card header icons. This is a template change, not a CSS class change. However, the phase description says only `tailwind.config.js` and `input.css` change; nav icon sizing may be deferred to Phase 34/35. Needs clarification in plan — the success criteria says "Nav/card icons sized at w-6 h-6" but the constraint says no template changes in this phase. Flagged as open question.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Tailwind CSS | 3.4.19 (installed) | Utility CSS, component @layer, dark mode | Already in use; `@layer components` is the canonical location for component class definitions |
| PostCSS | 8.4.x (installed) | CSS processing pipeline | Already in use via Tailwind |

### No new dependencies needed

Zero new npm packages. Zero new Python packages. All work is in existing files.

**Build command (confirmed):**
```bash
npm run build
# expands to: tailwindcss -i ./static/css/input.css -o ./static/css/output.css --minify
```

**Verify command (confirmed working from Phase 32):**
```bash
npm run verify
# expands to: npm run build && grep -q 'color-scheme' static/css/output.css && grep -q 'dark' static/css/output.css && echo 'Verify OK'
```

---

## Architecture Patterns

### Pattern 1: Token Definition in tailwind.config.js

**What:** Named color tokens are added under `theme.extend.colors` in `tailwind.config.js`. They become Tailwind utility classes (`bg-canvas-light`, `bg-canvas-dark`) that templates reference as literal strings. The Tailwind scanner sees these literal class strings in templates and includes them in `output.css`.

**Token names to add:**

```js
// tailwind.config.js — theme.extend.colors additions
colors: {
  sidebar: { /* existing — do not change */ },
  canvas: {
    light: '#f2f2f7',   // Apple systemGroupedBackground (light)
    dark: '#0f0f0f',    // Apple systemGroupedBackground (dark)
  },
  surface: {
    light: '#ffffff',   // Card surface light
    dark: '#1c1c1e',    // Apple secondarySystemGroupedBackground (dark)
  },
}
```

Templates then use: `bg-canvas-light dark:bg-canvas-dark` for the page canvas and `bg-surface-light dark:bg-surface-dark` for cards.

**IMPORTANT:** `tailwind.config.js` token names generate utility classes, but `dark:bg-surface-dark` must appear as a **literal string** in a scanned template file for Tailwind to include it in `output.css`. If the `.card` component class in `@layer components` uses `@apply bg-surface-light dark:bg-surface-dark`, those strings exist only in `input.css` — Tailwind scans CSS files differently from template files. See Pitfall 1.

**Verified approach for component classes:** When using custom token names inside `@apply` in `@layer components`, Tailwind resolves the token from the config at build time. The `@apply bg-surface-dark` in `input.css` is processed by Tailwind's own compilation, not by content scanning. Content scanning only applies to arbitrary strings in template files that Tailwind cannot see at build time. Therefore: `@apply bg-surface-light dark:bg-surface-dark` inside `@layer components` in `input.css` **works correctly** — Tailwind evaluates `@apply` against all known utilities including tokens.

### Pattern 2: @layer components — How Utilities Inside @apply Are Handled

**What:** Tailwind v3 processes `@apply` directives at build time by looking up the utility class definition. It does NOT require those utility classes to also appear in template files. Content scanning controls which **standalone** utility classes appear in `output.css`; `@apply`-referenced utilities are resolved by the PostCSS plugin directly.

**This means:**
- `.card { @apply bg-white dark:bg-surface-dark shadow-card; }` in `input.css` will work if `surface-dark` and `shadow-card` are defined in `tailwind.config.js` — no template literal string required.
- The component class `.card` itself does NOT need to appear in templates for its definition to be included — the `@layer components` block is always emitted (component layer is not purged).
- However, if `bg-canvas-light dark:bg-canvas-dark` are used **only as inline classes in templates** (not inside `@apply`), then those class strings must appear literally in the scanned HTML files.

**Confidence:** HIGH — This is core Tailwind v3 behavior. Verified against Tailwind v3 content/purge documentation.

### Pattern 3: Two-Layer Card Shadow (Light Mode Only)

**What:** Apple-style cards use a layered shadow that creates depth perception. In dark mode, surface color contrast replaces shadow. The standard two-layer shadow pattern:

```css
.card {
  /* light: two-layer shadow */
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
  /* dark: no shadow — dark surface on dark canvas does the work */
}
```

In Tailwind, custom shadow values must be defined in `tailwind.config.js` under `theme.extend.boxShadow` OR raw CSS can be written directly in `@layer components` using CSS properties instead of `@apply`. Since Tailwind's built-in `shadow-sm` is only one layer, a custom token is needed.

**Option A (recommended):** Define a named shadow token:
```js
// tailwind.config.js
theme: {
  extend: {
    boxShadow: {
      card: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
    },
  },
}
```
Then: `@apply shadow-card dark:shadow-none` in `.card`.

**Option B:** Write raw CSS in `@layer components`:
```css
.card {
  @apply bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
}
.dark .card {
  box-shadow: none;
}
```

Option A is preferred because it keeps the shadow as a design token and allows use elsewhere.

### Pattern 4: Dark Mode Shadow Removal

**What:** In `@layer components`, dark mode variants are expressed as `dark:shadow-none`. Within `@apply`, this works as expected — Tailwind generates the `.dark .card { box-shadow: none; }` rule.

**Confirmed syntax:**
```css
.card {
  @apply ... shadow-card dark:shadow-none;
}
```

This produces in `output.css`:
```css
.card { box-shadow: ...; /* shadow-card value */ }
.dark .card { box-shadow: none; }
```

**Confidence:** HIGH — standard Tailwind dark mode in `@layer components` behavior.

### Pattern 5: System Font Stack (No Inter)

**What:** DSGN-02 requires the system font stack with `-apple-system` and `BlinkMacSystemFont` leading. Inter must be removed from both `tailwind.config.js` and the `@layer base` rule in `input.css`.

**Correct stack:**
```js
// tailwind.config.js
fontFamily: {
  sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
},
```

```css
/* input.css @layer base */
html {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  color-scheme: light;
}
```

Note: Tailwind's `fontFamily.sans` default already includes these. By defining them explicitly with `-apple-system` first and removing `Inter`, all `font-sans` and body text uses the system stack.

### Pattern 6: Badge Shape — rounded-full to rounded-md

**What:** Four badge classes all use `rounded-full` which produces pill shapes. DSGN-04 requires `rounded-md` (4px border-radius in Tailwind's default scale). Change is surgical — replace one word in four `@apply` directives.

**Current:**
```css
.badge-green { @apply inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ...; }
```
**Required:**
```css
.badge-green { @apply inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium ...; }
```

### Pattern 7: card-title — Remove Uppercase Typography

**What:** DSGN-05 requires section headers to use sentence-case `font-semibold` typography, no uppercase letter-spacing. Current `.card-title`:
```css
.card-title { @apply text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider; }
```

Required:
```css
.card-title { @apply text-sm font-semibold text-gray-900 dark:text-white; }
```

Note: the color also changes — from muted gray to full contrast (`text-gray-900 dark:text-white`) — this is the Apple section header style.

**Confidence:** MEDIUM — the color change is inferred from Apple HIG conventions and the DSGN-05 requirement wording. The exact target color is not specified in the requirements. The safest choice is the standard heading color used for `h1` tags throughout the templates (`text-gray-900 dark:text-white`).

### Recommended File Change Manifest

| File | Change | DSGN req |
|------|--------|----------|
| `tailwind.config.js` | Add `canvas` and `surface` color tokens | DSGN-01 |
| `tailwind.config.js` | Add `boxShadow.card` token | DSGN-03 |
| `tailwind.config.js` | Replace `fontFamily.sans` (remove Inter) | DSGN-02 |
| `templates/base.html` | Remove 3 Google Fonts CDN link lines (34-36) | DSGN-02 |
| `templates/base_app.html` | Update canvas classes on lines 8 and 147 | DSGN-01 |
| `static/css/input.css` | Update `html` base font-family | DSGN-02 |
| `static/css/input.css` | Update `.card` surface color + shadow | DSGN-01, DSGN-03 |
| `static/css/input.css` | All four badges: `rounded-full` → `rounded-md` | DSGN-04 |
| `static/css/input.css` | `.card-title`: remove uppercase/tracking, update color | DSGN-05 |

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Custom dark canvas color | Inline `style=""` attributes | Named token in `tailwind.config.js` + `bg-canvas-dark` class | Tokens are scannable, refactorable, consistent |
| Multi-layer shadow | Raw `box-shadow` scattered across components | `boxShadow.card` token in config + `@apply shadow-card` | One place to change, named semantically |
| Dark mode shadow removal | Media query hacks | `dark:shadow-none` in `@apply` | Tailwind handles `.dark .card { box-shadow: none }` generation |
| System font stack | Per-element `style="font-family:..."` | `fontFamily.sans` in config applied globally via `@layer base` | Tailwind's `html` base rule applies to all text automatically |

---

## Common Pitfalls

### Pitfall 1: Defining Token Colors but Forgetting Template Literal Strings for Inline Classes

**What goes wrong:** You add `canvas.light` and `canvas.dark` tokens to `tailwind.config.js`, but `base_app.html` still reads `bg-slate-50 dark:bg-gray-950`. The new token classes are never referenced in any template, so Tailwind purges them as unused, and `output.css` does not contain them.

**Why it happens:** Tailwind v3 content scanning is aggressive — it only includes utility classes that appear as literal strings in content files. Token definitions in config do not automatically include themselves in output.

**How to avoid:** After defining tokens, update `base_app.html` lines 8 and 147 to use `bg-canvas-light dark:bg-canvas-dark` as literal class strings. Then verify with `grep 'bg-canvas-light' static/css/output.css`.

**Warning signs:** `npm run build` succeeds but `grep 'canvas' output.css` returns nothing.

### Pitfall 2: @apply with Custom Shadow Token — Token Must Exist at Build Time

**What goes wrong:** You write `@apply shadow-card` in `input.css` but forget to define `boxShadow.card` in `tailwind.config.js`. Tailwind throws a build error: `The 'shadow-card' class does not exist.`

**Why it happens:** `@apply` resolves utilities from the full Tailwind config. If the token isn't defined, the utility class doesn't exist.

**How to avoid:** Always define config tokens before referencing them in `@apply`. Build order: edit config → edit input.css → run build.

**Warning signs:** `npm run build` fails with `Cannot apply unknown utility class: shadow-card`.

### Pitfall 3: Removing Inter Without Removing the CDN Links

**What goes wrong:** `fontFamily.sans` is updated to remove Inter from the JS config and `input.css` base rule, but the three Google Fonts `<link>` tags remain in `base.html`. The browser still makes CDN requests for Inter. Network tab shows `fonts.googleapis.com` traffic. DSGN-02 is not satisfied.

**Why it happens:** The font stack in CSS controls which font the browser *uses*, but CDN `<link>` tags cause the *request* regardless of whether the font is ultimately applied.

**How to avoid:** Remove all three `<link>` lines from `base.html` (lines 34-36) as part of the same task that changes `fontFamily.sans`.

**Warning signs:** Browser DevTools Network tab shows `fonts.googleapis.com` requests on page load.

### Pitfall 4: card-title Color Change Breaking Contrast

**What goes wrong:** Changing `.card-title` to `text-gray-900 dark:text-white` may look overly heavy in card headers — Apple-style card titles are typically medium-weight secondary labels, not full black.

**Why it happens:** DSGN-05 says "sentence-case font-semibold, no uppercase letter-spacing" but doesn't specify the exact color. `text-gray-900` is full contrast; Apple's secondary label color (equivalent to `text-gray-500`) may be more appropriate.

**How to avoid:** Examine how `card-title` is used — always as `<h2>` inside `.card-header`. Apple uses secondary label color (gray) for section titles. A safe choice: `text-gray-700 dark:text-gray-200` (visible but not primary-heading weight). Flag this in the plan and verify visually after build.

**Warning signs:** Card headers look like page titles (same visual weight as `h1` elements).

### Pitfall 5: Tailwind Purge of dark: Variant Classes Added to Templates

**What goes wrong:** When `base_app.html` is updated to use `bg-canvas-light dark:bg-canvas-dark`, these classes must appear as complete literal strings. Jinja2 conditional class expressions like `class="{{ 'bg-canvas-light' if not dark else 'bg-canvas-dark' }}"` will cause one of the two classes to be missing from `output.css` depending on build-time evaluation.

**Why it happens:** Tailwind scans for literal class strings. Dynamic Jinja expressions are not evaluated during Tailwind's build scan.

**How to avoid:** Always write both classes as simultaneous literals: `class="bg-canvas-light dark:bg-canvas-dark"`. The `dark:` prefix variant is Tailwind's mechanism for conditional application, not Jinja2 branching.

**Warning signs:** Dark mode canvas color doesn't apply despite class being in template.

### Pitfall 6: Icon Sizing Requires Template Changes (Not CSS Changes)

**What goes wrong:** DSGN-06 requires nav icons at `w-6 h-6`. All current nav icons in `base_app.html` use `w-5 h-5`. This cannot be fixed by changing `input.css` — the size is set directly on each `<svg class="w-5 h-5 ...">` element in the template.

**Why it happens:** Icon sizing is not a component class — it's a utility applied per-element. There is no `.nav-icon` component class to update.

**How to avoid:** Recognize this as a template change, not a CSS change. Either update `base_app.html` nav icon sizes in this phase, or defer to Phase 34. The phase description says "pure CSS" work but the success criteria explicitly requires `w-6 h-6` icons. Plan must explicitly scope this decision.

**Warning signs:** Icons remain 20px after build.

---

## Code Examples

### tailwind.config.js — complete revised version

```js
// Source: Direct codebase inspection + DSGN-01/02/03 requirements
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: ['./templates/**/*.html'],
  theme: {
    extend: {
      colors: {
        sidebar: {
          DEFAULT: '#1a1d2e',
          hover: '#252941',
          active: '#4338ca',
          border: '#2d3561',
          text: '#c4c9e4',
        },
        canvas: {
          light: '#f2f2f7',  // DSGN-01: Apple systemGroupedBackground light
          dark: '#0f0f0f',   // DSGN-01: Apple systemGroupedBackground dark
        },
        surface: {
          light: '#ffffff',  // DSGN-01: card surface light
          dark: '#1c1c1e',   // DSGN-01: Apple secondarySystemGroupedBackground dark
        },
      },
      fontFamily: {
        // DSGN-02: system font stack, no Inter, no CDN
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
      },
      boxShadow: {
        // DSGN-03: two-layer card shadow (light mode only)
        card: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
      },
    },
  },
  plugins: [],
}
```

### input.css — @layer base changes

```css
/* Source: Direct codebase inspection + DSGN-02 */
@layer base {
  html {
    /* DSGN-02: system font stack, Inter removed */
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color-scheme: light;
  }
  html.dark {
    color-scheme: dark;
  }
  /* existing button:not([class]) rule — unchanged */
}
```

### input.css — .card component class

```css
/* Source: Direct codebase inspection + DSGN-01/DSGN-03 */
.card {
  @apply bg-surface-light dark:bg-surface-dark rounded-xl
         border border-gray-200 dark:border-gray-800
         shadow-card dark:shadow-none;
}
```

### input.css — badge classes (all four)

```css
/* Source: Direct codebase inspection + DSGN-04 */
.badge-green {
  @apply inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium
         bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400;
}
.badge-red {
  @apply inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium
         bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-400;
}
.badge-blue {
  @apply inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium
         bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-400;
}
.badge-gray {
  @apply inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium
         bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400;
}
```

### input.css — .card-title

```css
/* Source: Direct codebase inspection + DSGN-05 */
.card-title {
  /* DSGN-05: sentence-case font-semibold, no uppercase, no tracking-wider */
  @apply text-sm font-semibold text-gray-700 dark:text-gray-200;
}
```

### base_app.html — canvas background update

```html
<!-- Source: Direct codebase inspection + DSGN-01 -->
<!-- line 8 — outer container -->
<div class="flex h-screen overflow-hidden bg-canvas-light dark:bg-canvas-dark">

<!-- line 147 — main content -->
<main class="flex-1 overflow-y-auto bg-canvas-light dark:bg-canvas-dark p-6">
```

### base.html — remove Google Fonts CDN (lines 34-36)

Remove these three lines entirely:
```html
<!-- DELETE THESE THREE LINES — DSGN-02 -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

### Verification grep commands

```bash
# After npm run build, verify each component class is in output.css:
grep -q '.card{' static/css/output.css && echo "card: OK" || echo "card: MISSING"
grep -q 'shadow-card\|1px 3px rgba' static/css/output.css && echo "shadow: OK" || echo "shadow: MISSING"
grep -q 'badge-green' static/css/output.css && echo "badges: OK" || echo "badges: MISSING"
grep -q 'rounded-md' static/css/output.css && echo "rounded-md: OK" || echo "rounded-md: MISSING"
grep 'rounded-full' static/css/output.css | grep -q 'badge-' && echo "ERROR: badge still pill" || echo "badge shape: OK"
grep -q 'bg-canvas-light\|f2f2f7' static/css/output.css && echo "canvas: OK" || echo "canvas: MISSING"
grep -q '1c1c1e' static/css/output.css && echo "surface dark: OK" || echo "surface dark: MISSING"
grep -q 'apple-system\|BlinkMacFont' static/css/output.css && echo "font: OK" || echo "font: MISSING"
grep -q 'Inter' static/css/output.css && echo "ERROR: Inter still present" || echo "Inter removed: OK"
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Component classes with gray palette placeholders | Component classes using named Apple tokens | Visual alignment with Apple HIG; tokens refactorable |
| `shadow-sm` (single layer) on cards | `shadow-card` (two-layer) light, `shadow-none` dark | Apple depth convention; flat dark mode |
| `rounded-full` pill badges | `rounded-md` rectangular badges | Matches DSGN-04; more readable in data tables |
| Inter (CDN) as primary font | System font stack (`-apple-system` first) | No CDN requests; matches Apple native; faster TTFB |
| `uppercase tracking-wider` card titles | Sentence-case `font-semibold` card titles | DSGN-05; more readable; matches Apple section header style |

**No longer valid in this project:**
- `bg-slate-50 dark:bg-gray-950` as canvas colors: replaced by `bg-canvas-light dark:bg-canvas-dark`
- `bg-white dark:bg-gray-900` for card surfaces in component class: replaced by token-driven `bg-surface-light dark:bg-surface-dark`

---

## Open Questions

1. **Do nav icon sizes (DSGN-06) require template changes in this phase?**
   - What we know: All sidebar nav icons use `w-5 h-5` in `base_app.html`. DSGN-06 requires `w-6 h-6`. This cannot be fixed by CSS changes — SVG `class` attributes must be edited in the template. The phase goal says CSS-only, but the success criteria says icons must be at 24px.
   - What's unclear: Whether the planner should scope this change into Phase 33 (touching `base_app.html` for canvas AND icons) or defer to Phase 34.
   - Recommendation: Include `base_app.html` icon sizing in Phase 33 since the template is already being touched for canvas colors. Update all nav `<svg class="w-5 h-5 ...">` to `<svg class="w-6 h-6 ...">` in the same task.

2. **What exact color for card-title text?**
   - What we know: DSGN-05 says "sentence-case font-semibold, no uppercase tracking." The current muted gray (`text-gray-500`) reads as a label, not a heading. Apple uses secondary label color (gray) for section titles.
   - What's unclear: Whether `text-gray-700 dark:text-gray-200` or `text-gray-900 dark:text-white` is correct.
   - Recommendation: Use `text-gray-700 dark:text-gray-200` — it maintains the secondary label feel of a card header title while removing the uppercase treatment. If too light, it can be adjusted in Phase 34/35 visual review.

3. **Does `table-wrap` also need shadow removal in dark mode?**
   - What we know: `.table-wrap` uses `shadow-sm` which is a single-layer shadow. Not mentioned in DSGN-03 (which specifies cards). Currently consistent with `.card` shadow behavior.
   - What's unclear: Whether table wrappers should also lose shadow in dark mode per Apple conventions.
   - Recommendation: Apply the same pattern: update `.table-wrap` to use `shadow-card dark:shadow-none`. Keeps it consistent with `.card`.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `tailwind.config.js`, `static/css/input.css`, `templates/base.html`, `templates/base_app.html`, `templates/admin/users.html`, `templates/admin/users_table.html`, `templates/log/form.html`, `templates/log/log.html`, `templates/log/log_table.html`, `templates/log/import.html`, `package.json`
- Phase 32 RESEARCH.md and PLAN.md (completed) — confirmed Phase 32 changes are in place
- Tailwind CSS v3 docs — `@layer components`, `@apply`, content scanning behavior, `theme.extend` token definition

### Secondary (MEDIUM confidence)
- Apple Human Interface Guidelines color values — `#f2f2f7` (systemGroupedBackground), `#1c1c1e` (secondarySystemGroupedBackground), `#0f0f0f` (dark canvas) — sourced from DSGN-01 requirement specification

### Tertiary (LOW confidence)
- None — all claims verified against codebase inspection or Tailwind documentation

---

## Metadata

**Confidence breakdown:**
- Current codebase state: HIGH — direct file inspection of all relevant files
- Standard stack: HIGH — no new dependencies; all tools installed and working
- Token values: HIGH — values are specified in the phase requirements (DSGN-01 through DSGN-06)
- @apply / @layer behavior: HIGH — core Tailwind v3 behavior, well-documented
- card-title color: MEDIUM — inferred from Apple HIG conventions; exact value unspecified in requirements
- nav icon scope: MEDIUM — success criteria implies template change but phase description implies CSS-only

**Research date:** 2026-04-11
**Valid until:** 2026-05-11 (Tailwind 3.x stable; no pending major version changes)
