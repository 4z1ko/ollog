# Stack Research: Apple-like UI Redesign (Dark/Light Mode + Icons)

**Domain:** ollog — UI redesign milestone adding Apple-inspired aesthetics, icon library, and dark/light mode toggle to existing FastAPI + Jinja2 + HTMX + Tailwind CSS app
**Researched:** 2026-04-11
**Confidence:** HIGH for dark mode config (already correct), Heroicons Python package, font stack. MEDIUM for heroicons npm version pinning (latest confirmed via multiple sources, not direct npm registry query).

---

## Executive Summary

The project already has the correct foundations for this milestone:

- `darkMode: 'class'` is already set in `tailwind.config.js` — this is exactly right for localStorage-based toggling
- The FOUC-prevention inline script is already in `templates/base.html` with localStorage + `prefers-color-scheme` fallback — this is the canonical pattern
- Inter font is already loaded via Google Fonts CDN and set as the primary sans-serif in `input.css` and `tailwind.config.js`
- A component library (`card`, `btn-*`, `form-input`, etc.) already exists in `static/css/input.css`
- The Tailwind build pipeline (`npm run build` / `npm run watch`) is operational

**Net new dependencies for this milestone:**

| Layer | What to Add | Why |
|-------|-------------|-----|
| Python | `heroicons[jinja]>=2.13` | Render SVG icons natively in Jinja2 templates without React |
| CSS | Tailwind theme extensions in `tailwind.config.js` | Apple-calibrated border radii, shadows, and color tokens |
| Font | Switch CDN → `@fontsource-variable/inter` (npm) | Self-hosted variable font, no Google Fonts external dependency |

**Nothing else is needed.** No Alpine.js, no heavy component framework, no new CSS framework.

---

## 1. Dark/Light Mode — Already Correct

### Status: COMPLETE — no changes required

The existing `tailwind.config.js` already has:

```js
darkMode: 'class',
```

The `class` strategy adds the `dark` class to `<html>` to activate dark mode. This is the only strategy that supports user-controlled toggling with localStorage persistence. The alternative `media` strategy only follows the OS setting — it does not allow user overrides.

The existing `base.html` FOUC-prevention script is already correct:

```html
<script>
  (function () {
    var theme = localStorage.getItem('theme');
    if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark');
    }
  })();
</script>
```

This must remain inline in `<head>` (not deferred, not in an external JS file). Deferring it causes a visible flash of the wrong theme on page load.

**Toggle button implementation** (add to any template — no additional libraries):

```html
<button id="theme-toggle" aria-label="Toggle dark mode">
  <!-- sun/moon icons go here (Heroicons) -->
</button>

<script>
  document.getElementById('theme-toggle').addEventListener('click', function () {
    var html = document.documentElement;
    var isDark = html.classList.toggle('dark');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  });
</script>
```

**Confidence:** HIGH — pattern confirmed in official Tailwind CSS dark mode docs and widely validated in community. The existing implementation matches the canonical approach exactly.

**Sources:**
- [Tailwind CSS — Dark Mode](https://tailwindcss.com/docs/dark-mode)
- [Tailwind CSS v3 — Dark Mode](https://v3.tailwindcss.com/docs/dark-mode)

---

## 2. Icon Library — `heroicons` Python Package

### Recommendation: `heroicons[jinja]` (adamchainz) — latest: 2.13.0

**Why this over alternatives:**

| Option | Verdict | Reason |
|--------|---------|--------|
| `heroicons[jinja]` Python package | **Use this** | Renders SVG inline in Jinja2 templates via template function calls; designed for non-React server-rendered apps; maintained by adamchainz (Django/Jinja specialist) |
| `heroicons` npm package (SVG files only) | Avoid as primary | Requires a build step to copy SVGs into templates or a custom Jinja2 macro; more friction than the Python package |
| Lucide (`lucide-static` npm) | Avoid | Good library, but adds an npm dependency with no Python/Jinja integration story; more appropriate for React/Vue |
| Font Awesome CDN | Avoid | External dependency, large payload for icon fonts, inconsistent with Tailwind design philosophy |
| Inline SVG copy-paste | Avoid | Works but is unmaintainable at scale; templates become bloated |

**Why Heroicons specifically:**
- Created by the Tailwind Labs team — designed to work with Tailwind CSS class conventions
- MIT licensed, 316 icons (v2.2.0 npm), four styles: outline 24px, solid 24px, mini 20px, micro 16px
- The Python package (adamchainz) wraps the official heroicons SVG files and exposes Jinja2-compatible template functions

**Heroicons v2 size guide for browser display:**
- `heroicon_outline` / `heroicon_solid` → 24×24px — standard UI elements (buttons, navigation)
- `heroicon_mini` → 20×20px — compact contexts (table cells, badges, inline text)
- `heroicon_micro` → 16×16px — tight density contexts (tags, small labels)

Use `w-5 h-5` Tailwind classes for 20px (mini) and `w-6 h-6` for 24px (outline/solid) — these map to correct pixel sizes in a 16px root font context.

### Installation

```bash
pip install "heroicons[jinja]>=2.13"
```

### FastAPI/Jinja2 Integration Pattern

FastAPI's `Jinja2Templates` accepts a pre-configured `jinja2.Environment`. Add heroicons globals when constructing the environment:

```python
# app/templates.py (or wherever Jinja2Templates is configured)
import jinja2
from fastapi.templating import Jinja2Templates
from heroicons.jinja import heroicon_micro, heroicon_mini, heroicon_outline, heroicon_solid

environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"),
    autoescape=True,
)
environment.globals.update({
    "heroicon_micro": heroicon_micro,
    "heroicon_mini": heroicon_mini,
    "heroicon_outline": heroicon_outline,
    "heroicon_solid": heroicon_solid,
})

templates = Jinja2Templates(env=environment)
```

### Template Usage

```html
<!-- 24px outline icon, sized with Tailwind -->
{{ heroicon_outline("user", class="w-6 h-6 text-gray-500") }}

<!-- 20px mini icon in a button -->
<button class="btn btn-primary">
  {{ heroicon_mini("plus", class="w-5 h-5") }}
  Add Contact
</button>

<!-- 16px micro icon in a badge -->
<span class="badge-green">
  {{ heroicon_micro("check", class="w-4 h-4") }}
  Active
</span>
```

The `class` kwarg passes directly to the SVG element. `stroke_width` is also supported for outline icons. The package renders `<svg>` markup with `aria-hidden="true"` by default — add `aria-label` explicitly for interactive icons.

**Confidence:** HIGH for integration pattern (confirmed in adamchainz/heroicons README). MEDIUM for version 2.13.0 as latest (confirmed via PyPI libraries.io listing; PyPI page confirmed version existence).

**Sources:**
- [adamchainz/heroicons — GitHub README](https://github.com/adamchainz/heroicons)
- [heroicons 2.13.0 on PyPI — Libraries.io](https://libraries.io/pypi/heroicons)
- [heroicons — PyPI](https://pypi.org/project/heroicons/)

---

## 3. Typography — Apple-Like Font Stack

### Recommendation: Upgrade to `@fontsource-variable/inter` (self-hosted variable font)

The project currently uses Inter via Google Fonts CDN:

```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

This works but has two problems for an Apple-like feel:
1. External CDN dependency — adds latency and a third-party network request
2. Non-variable static weights — the Google Fonts version loads separate wfont files per weight

**Recommended upgrade:** `@fontsource-variable/inter` — the variable font variant of Inter, self-hosted, served from your own static assets.

```bash
npm install @fontsource-variable/inter
```

Then in `static/css/input.css`, replace the Google Fonts `@import` (or remove the `<link>` from `base.html`) with:

```css
@import "@fontsource-variable/inter";
```

The variable font supports all weights (100–900) and optical sizes in a single file. With Tailwind's build pipeline (`npm run build`), the font files are bundled into the CSS output or can be copied to `static/`.

**If self-hosting the font file adds build complexity:** Keep the Google Fonts CDN link but add `font-display: swap` and the `preconnect` hints already present in `base.html`. The Apple-like aesthetic is achieved by the design tokens and class patterns, not the font delivery mechanism.

### CSS Font Stack for Apple-Like Feel

The `tailwind.config.js` already has a correct font stack:

```js
fontFamily: {
  sans: [
    'Inter',
    'ui-sans-serif',
    'system-ui',
    '-apple-system',   // macOS/iOS: San Francisco
    'sans-serif',
  ],
},
```

`-apple-system` resolves to San Francisco on Apple devices — so on macOS/iOS, the fallback is SF Pro itself. On non-Apple devices, Inter renders with the same optical characteristics. This is exactly the right stack.

**Do NOT add `BlinkMacSystemFont`** — it was a Blink-era Chrome workaround for macOS that is now redundant. `system-ui` covers modern Chrome/Edge on macOS.

**Note:** Apple does not license SF Pro for `@font-face` web embedding. The system stack approach (`-apple-system`) is the only sanctioned way to display SF Pro on web pages — and it only works on Apple devices. For cross-platform Apple aesthetics, Inter is the canonical choice.

**Confidence:** HIGH — CSS font stack behavior verified via CSS-Tricks system font stack reference and Apple Developer forums. Inter ↔ SF Pro optical similarity is well-established in the design community.

**Sources:**
- [System Font Stack — CSS-Tricks](https://css-tricks.com/snippets/css/system-font-stack/)
- [Apple Developer — SF Fonts licensing](https://developer.apple.com/forums/thread/127350)
- [@fontsource-variable/inter — npm](https://www.npmjs.com/package/@fontsource-variable/inter)

---

## 4. Apple-Like Design Tokens (Tailwind Config Extensions)

No new library is required. Apple HIG design values are expressible as Tailwind theme extensions.

### Recommended `tailwind.config.js` additions

```js
theme: {
  extend: {
    // ... existing colors and fontFamily ...

    borderRadius: {
      'apple-sm': '8px',   // small buttons, badges
      'apple-md': '12px',  // inputs, small cards
      'apple-lg': '16px',  // standard cards (App Store card style)
      'apple-xl': '20px',  // large feature cards
      'apple-2xl': '24px', // modals, sheets
    },

    boxShadow: {
      // Apple-style layered shadows (subtle, not Material-style drops)
      'apple-sm': '0 1px 3px 0 rgba(0,0,0,0.06), 0 1px 2px -1px rgba(0,0,0,0.04)',
      'apple-md': '0 4px 12px 0 rgba(0,0,0,0.08), 0 2px 4px -2px rgba(0,0,0,0.05)',
      'apple-lg': '0 8px 24px 0 rgba(0,0,0,0.10), 0 4px 8px -4px rgba(0,0,0,0.06)',
      // Dark mode: slightly stronger shadows since backgrounds are dark
      'apple-dark': '0 4px 16px 0 rgba(0,0,0,0.40)',
    },

    backdropBlur: {
      'apple': '20px',  // Used for frosted glass / translucent cards
    },
  },
},
```

These values are derived from Apple HIG specifications (16px corner radius for standard cards, `backdrop-filter: blur(20px)` for system sheets). Apply via standard Tailwind classes: `rounded-apple-lg`, `shadow-apple-md`, `backdrop-blur-apple`.

**Confidence:** MEDIUM — values derived from Apple HIG token analysis and community CSS recreation projects. Not from a published Apple specification document.

**Sources:**
- [Apple HIG Design System tokens — GitHub](https://github.com/cmurphy1140/apple-design-system)
- [iOS App Design Guidelines 2025 — tapptitude](https://tapptitude.com/blog/i-os-app-design-guidelines-for-2025)

---

## 5. What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Alpine.js | Adds a second JS reactive framework alongside HTMX; creates two overlapping DOM-management systems | Vanilla `<script>` for the dark mode toggle; HTMX for all server interactions |
| Flowbite / daisyUI / Preline | Pre-built component libraries that ship their own Tailwind plugins and override token values; fight with existing component classes in `input.css` | Extend existing `input.css` component layer with Apple-calibrated values |
| Headless UI (npm) | React/Vue only — incompatible with Jinja2 template rendering | Native HTML elements styled with Tailwind |
| Font Awesome CDN | Icon font approach; inconsistent sizing behaviour vs inline SVG; external dependency | `heroicons[jinja]` inline SVG |
| `@heroicons/react` npm package | React-only; outputs JSX, not usable in Jinja2 templates | `heroicons[jinja]` Python package |
| Tailwind CSS v4 (upgrade) | Breaking changes from v3; `darkMode: 'class'` config syntax changed; would require rewriting `tailwind.config.js` and possibly `input.css` | Stay on Tailwind CSS 3.4.x which is already installed and working |
| Google Fonts variable font via CDN | Google Fonts does not serve the Inter variable font with the full axis range as a single file | `@fontsource-variable/inter` (npm, self-hosted) if switching to variable font |

---

## 6. Summary of Required Changes

### Python dependencies (`pyproject.toml` or `requirements.txt`)

```
heroicons[jinja]>=2.13
```

### npm dependencies (`package.json`)

```json
"dependencies": {
  "@fontsource-variable/inter": "^5.0.0"
}
```

Optional — only needed if switching from Google Fonts CDN to self-hosted. The CDN approach continues to work.

### `tailwind.config.js`

Add `borderRadius` and `boxShadow` Apple token extensions (see Section 4). No other changes needed — `darkMode: 'class'` is already correct.

### `templates/base.html`

No structural changes. The FOUC script is already correct. Add the dark mode toggle button in whatever layout template wraps the admin console.

### Application code

Wire the heroicons Jinja2 functions into the `Jinja2Templates` environment (see Section 2 integration pattern).

---

## Version Compatibility

| Package | Version | Python | Notes |
|---------|---------|--------|-------|
| `heroicons[jinja]` | `>=2.13` | 3.9–3.13 | Confirmed Python 3.12 compatible |
| `@fontsource-variable/inter` | `^5.0.0` | N/A | npm package; works with Tailwind 3.4 build pipeline |
| `tailwindcss` | `3.4.17` (existing) | N/A | No upgrade needed; `darkMode: 'class'` is stable in 3.x |

---

## Sources

- [Tailwind CSS — Dark Mode (v3)](https://v3.tailwindcss.com/docs/dark-mode) — darkMode: 'class' strategy, toggle pattern
- [adamchainz/heroicons — GitHub](https://github.com/adamchainz/heroicons) — Jinja2 integration pattern, function signatures
- [heroicons — PyPI](https://pypi.org/project/heroicons/) — version 2.13.0 confirmed
- [heroicons.com](https://heroicons.com/) — icon styles, size guide (24px/20px/16px)
- [@heroicons/react 2.2.0 — cloudsmith.com](https://cloudsmith.com/navigator/npm/@heroicons/react) — npm version 2.2.0 confirmed
- [@fontsource-variable/inter — npm](https://www.npmjs.com/package/@fontsource-variable/inter) — self-hosted variable font
- [System Font Stack — CSS-Tricks](https://css-tricks.com/snippets/css/system-font-stack/) — `-apple-system` fallback behavior
- [Apple Developer Forums — SF Fonts web embedding](https://developer.apple.com/forums/thread/127350) — confirms no @font-face licensing for SF Pro
- [Apple HIG design system tokens — cmurphy1140/apple-design-system](https://github.com/cmurphy1140/apple-design-system) — border radius and shadow values

---

*Stack research for: ollog Apple-like UI redesign milestone*
*Researched: 2026-04-11*
