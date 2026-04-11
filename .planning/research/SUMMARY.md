# Project Research Summary

**Project:** ollog — Apple-like UI Redesign
**Domain:** Frontend visual redesign — FastAPI + HTMX + Jinja2 + Tailwind CSS v3
**Researched:** 2026-04-11
**Confidence:** HIGH

## Executive Summary

This milestone is a pure frontend visual redesign of the ollog admin console and login pages. No Python, no routes, no database changes. The existing codebase is already well-architected for this work: `darkMode: 'class'` is configured in `tailwind.config.js`, the FOUC-prevention inline script is correctly in place in `base.html`, Heroicons SVGs are already used throughout, and a component class system (`@layer components` in `input.css`) provides clean extension points. The delta is smaller than it appears — the core infrastructure is done; what remains is design token refinement and template polish.

The recommended approach is a three-layer change: (1) update `tailwind.config.js` with Apple-calibrated design tokens (border-radius, shadows, CSS variable-backed surface colors), (2) refine component classes in `input.css` to use those tokens, and (3) update templates to adopt the refined classes and correct a handful of non-Apple conventions (uppercase card titles, pill-shaped badges, `w-5 h-5` icons on prominent nav items). The single new dependency is `heroicons[jinja]>=2.13` to wire icon rendering into the Jinja2 environment — icons already render inline SVG in templates, so this is a registration step, not a capability addition.

The primary risk is not complexity — it is regression. The FOUC-prevention script in `base.html` is load-bearing and must not be moved, deferred, or extracted during refactoring. Tailwind CSS purging can silently strip new `dark:` classes from the production build if the watcher is not running when templates are edited. Adding `transition-colors` to `<body>` or `<html>` at the CSS base layer will cause a visible color-fade animation on every page load, not just on user-initiated toggles. All three risks have known, low-effort prevention strategies and must be locked in before any visual work begins.

---

## Key Findings

### Recommended Stack

The codebase already has everything needed. No new frontend framework, no Alpine.js, no new CSS library. Tailwind CSS 3.4.x should not be upgraded to v4 — the breaking changes to `darkMode: 'class'` config syntax and the rewrite of `input.css` they would require are out of scope for a visual polish milestone.

**Core technologies:**
- `tailwindcss@3.4.x` (existing): design system foundation — `darkMode: 'class'` strategy already configured correctly, keep as-is
- `heroicons[jinja]>=2.13` (add to Python deps): inline SVG rendering in Jinja2 templates via `heroicon_outline()`, `heroicon_solid()`, `heroicon_mini()` template functions; the only Python-native approach for Heroicons in a non-React app
- `@fontsource-variable/inter` (optional npm add): self-hosted variable Inter font, eliminates Google Fonts CDN dependency; the system font stack (`-apple-system`) is an equally valid and simpler primary path that renders SF Pro on Apple devices without any font file
- Vanilla JS (existing): dark mode toggle and icon sync — no animation library or reactive framework needed; `toggleTheme()` and `updateThemeIcons()` in `base_app.html` cover the complete toggle lifecycle

**Key constraint:** Stay on Tailwind v3. The `darkMode: 'class'` syntax changes in v4. Upgrading mid-milestone adds risk with no user-visible benefit.

### Expected Features

The milestone is scoped to visual refinement and correction, not new functionality. Features fall into two categories: corrections (things that exist but do not match Apple conventions) and additions (missing elements that define "Apple-like").

**Must have (table stakes — defines whether the redesign lands):**
- System font stack: replace Inter CDN with `-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif` — the single most recognizable Apple element; SF Pro renders on Apple devices automatically
- `color-scheme` meta tag + CSS property: browser native controls (scrollbars, select dropdowns, date inputs) must respect the theme, not stay light in dark mode
- Layered background colors: `bg-gray-50 dark:bg-[#0f0f0f]` for page canvas, `bg-white dark:bg-[#1c1c1e]` for card surfaces — these are Apple's exact HIG grouped interface background values
- Badge border-radius correction: `rounded-full` (pill shape) to `rounded-md` (6px rectangular) — Apple badge convention
- Card shadow refinement: two-layer shadow in light mode, `shadow-none` in dark mode — physically grounded depth cue
- Card title typography: remove uppercase/tracking-wider, use `text-[15px] font-semibold` sentence-case — matches App Store Connect and Apple admin UI conventions
- Smooth theme transition after paint only (not at load): using the `no-transition` class suppression pattern to animate user-initiated toggles without causing a color-fade on page load

**Should have (polish, P2):**
- Icon stroke-width consistency: `1.5` for nav/24px icons (`w-6 h-6`), `2` for button/16px icons (`w-4 h-4`)
- `aria-label` on HTMX action buttons in `users_table.html`
- Login glass card refinements: `backdrop-blur-md`, `shadow-2xl`, `ring-1 ring-white/10`
- Sidebar color tuning to exact `#1c1c1e` (Apple system grouped background in dark mode)
- `htmx:afterSettle` handler added to `base_app.html` for theme icon sync robustness

**Defer to v2+:**
- Heroicons v3 migration (not yet released)
- CSS `@layer` restructure for Tailwind v4 compatibility
- Three-state toggle (light/dark/system): two-state with `prefers-color-scheme` fallback on first visit is sufficient for an admin tool

### Architecture Approach

This is a CSS-first, template-second change. The build pipeline drives everything: `tailwind.config.js` defines tokens → `input.css` consumes them → `npm run build` compiles `output.css` → templates consume the output. No Python files change. No routes change. The component class system in `@layer components` is the primary abstraction; templates reference class names (`.card`, `.btn-primary`, `.badge-green`) and all visual logic lives in `input.css`. HTMX partial swaps never touch `<html>`, so the `dark` class persists through all user interactions automatically.

**Major components:**
1. `tailwind.config.js` — design token definitions; CSS variable references for theme-adaptive surface, border, and text colors; border-radius and shadow extensions
2. `static/css/input.css` — CSS variable definitions per theme (`:root` light values and `.dark` overrides in `@layer base`), all component class refinements in `@layer components`; this is where the Apple aesthetic is implemented
3. `templates/base_app.html` — the sole location for theme JS (`toggleTheme()`, `updateThemeIcons()`); all other templates are theme-agnostic; HTMX partials inherit theme from `<html class="dark">` with no JS needed
4. Page templates (`log/`, `admin/`) — consume component classes; `log_table.html` and `users_table.html` partials require no theme-specific logic
5. Login pages (`log/login.html`, `admin/login.html`) — standalone glass card redesigns; always render dark regardless of toggle state because their outer container is a fixed dark gradient

**Build order is mandatory:** `tailwind.config.js` → `input.css` → `npm run build` → `base_app.html` → login pages → page templates → HTMX partials. Tailwind's class scanner must see all new class names as literal strings in template files before the build step runs.

### Critical Pitfalls

1. **Flash of Wrong Theme (FOWT) regression** — The inline IIFE in `base.html` `<head>` is already correct and working. The risk is accidentally moving it, adding `defer`/`async`, or extracting it to an external JS file during template refactoring. Prevention: add a load-bearing comment to the script block; test by setting dark mode and doing a hard refresh (Cmd+Shift+R) — zero white flash must be visible; any PR that moves the `<script>` block from `<head>` in `base.html` is a regression.

2. **Tailwind purging `dark:` variants in production** — New Apple-style classes (`dark:bg-[#1c1c1e]`, `dark:ring-white/10`, `dark:backdrop-blur-xl`) must appear as complete literal strings in scanned template files. If added while the build watcher is not running, `output.css` will be stale and the production build silently drops them. Prevention: always run `npm run watch` during development; run `npm run build` + `grep` verification for new classes before every commit that touches templates or `input.css`.

3. **CSS transitions causing their own page-load flash** — Adding `transition-colors` to `<body>`, `<html>`, or `*` in `@layer base` causes a visible 200-300ms color fade on every page load, because the transition animates the initial `dark` class application. Prevention: never add `transition-*` to base-layer HTML/body elements; implement the `no-transition` class suppression pattern in the IIFE (add class before setting dark, remove it via `requestAnimationFrame` after); restrict transitions to interactive hover/focus states only.

4. **HTMX partial swaps desync the theme toggle icon** — `updateThemeIcons()` fires on `DOMContentLoaded` only; HTMX swaps do not re-fire that event. The sidebar is not currently a swap target, so this is latent. Adding any new Apple-style component with theme-aware JS initialization will trigger the bug. Prevention: add `document.body.addEventListener('htmx:afterSettle', function() { updateThemeIcons(document.documentElement.classList.contains('dark')); });` to `base_app.html` in Phase 1, before building any new components.

5. **`backdrop-filter` glassmorphism invisible on Safari** — Tailwind's `backdrop-blur-*` utilities emit only the unprefixed `backdrop-filter` property. The login card glass effect renders as a solid background in Safari unless `-webkit-backdrop-filter` is also declared. CSS variable values for blur amounts break even with the prefix (confirmed open Safari 18 bug). Prevention: declare `-webkit-backdrop-filter` explicitly in `@layer components` for glass card classes; use fixed pixel values (e.g., `blur(12px)`), not CSS variable references.

6. **SVG icons blurry on HiDPI / Retina displays** — Heroicons have `viewBox="0 0 24 24"`. Rendering at 20px CSS (`w-5 h-5`) produces a 0.833x scaling factor — on 2x Retina displays this forces fractional physical pixel coordinates on all stroke edges, producing visibly blurry icons. This is directly contrary to the Apple-quality goal. Prevention: use `w-6 h-6` (24px, 1:1 with viewBox) for all prominent nav and card header icons; `w-4 h-4` is acceptable for small secondary icons.

---

## Implications for Roadmap

### Phase 1: Theme Infrastructure and Build Discipline

**Rationale:** Three of the six critical pitfalls must be locked in before any visual work begins. FOWT regression, Tailwind purge regression, and CSS transition flash are invisible in casual development but immediately user-visible in production. Establishing the `no-transition` suppression pattern and the `htmx:afterSettle` handler here means all subsequent phases build on a verified foundation.

**Delivers:** Load-bearing comment added to FOUC script; `no-transition` suppression pattern implemented in IIFE; `color-scheme` meta tag + CSS property added; `htmx:afterSettle` handler wired in `base_app.html`; heroicons Jinja2 environment configured in app; `npm run build` + `grep` verification gate established; CSS transition policy documented.

**Addresses:** `color-scheme` feature (P1), `htmx:afterSettle` robustness (P2), transition-after-paint polish (P1)

**Avoids:** FOWT regression (Pitfall 1), Tailwind purge regression (Pitfall 2), CSS transition flash on load (Pitfall 3), HTMX icon desync (Pitfall 4)

**Research flags:** Standard patterns — no additional research needed. All patterns verified against official Tailwind, HTMX, and MDN documentation.

---

### Phase 2: Design Tokens and CSS Component System

**Rationale:** All templates must consume from a single design token source. Defining tokens in `tailwind.config.js` and CSS variables in `input.css` before touching any template means every subsequent template change is a one-pass operation using the correct class names. Doing template changes without the token layer produces hardcoded arbitrary hex values that become expensive to unify later.

**Delivers:** CSS variables for surface, border, and text colors in `@layer base` (`:root` light, `.dark` overrides); extended `tailwind.config.js` with Apple-calibrated border-radius and shadow tokens; refined component classes (`.card`, `.btn-*`, `.form-input`, `.badge-*`, `.data-table`, `.card-title`); `npm run build` verification that all new dark-variant classes exist in `output.css`.

**Addresses:** System font stack (P1), layered background colors (P1), badge border-radius correction (P1), card shadow refinement (P1), card title typography correction (P1)

**Avoids:** Hardcoded arbitrary values anti-pattern; Tailwind purge (run build + `grep` at end of phase)

**Research flags:** Standard patterns — CSS variable channel notation for Tailwind opacity support is well-documented. Apple HIG token values (border-radius, shadow layering, exact background hex values) are MEDIUM confidence — community-derived, not official Apple spec. They are directionally correct and validated through multiple independent sources; adjust visually during implementation.

---

### Phase 3: Template Polish — Admin Console

**Rationale:** Admin templates are the primary user-facing surface and the most complex context to validate visually. Separating admin from login pages allows focused review of the core UI before addressing the isolated glass card context. The `users_table.html` partial also provides the clearest test of `htmx:afterSettle` from Phase 1.

**Delivers:** `base_app.html` sidebar refinement with correct Apple dark color tokens; `admin/users.html` and `admin/users_table.html` updated to refined component classes; icon stroke-width audit for nav (`w-6 h-6 stroke-1.5`) and button (`w-4 h-4 stroke-2`) contexts; `aria-label` attributes added to HTMX action buttons.

**Addresses:** Icon stroke-width consistency (P2), accessibility aria-labels (P2), sidebar color tuning (P3)

**Avoids:** SVG blurriness on HiDPI (Pitfall 6) — all prominent icons moved to `w-6 h-6`

**Research flags:** Standard patterns — icon sizing is mechanical. No research dependencies.

---

### Phase 4: Template Polish — Log Views

**Rationale:** Log views contain HTMX-driven `tbody` partials and SSE-driven refresh, making them the most complex context for theme survival. Addressing them after the admin console means the `htmx:afterSettle` handler and component classes are already verified in a simpler context, reducing risk.

**Delivers:** `log/log.html`, `log/log_table.html`, `log/form.html`, `log/import.html` updated to refined component classes; SSE-driven `#log-table` refresh verified to render correct dark-mode colors; no inline `style=""` color attributes in any partial.

**Addresses:** HTMX partial and SSE dark mode correctness; component class consistency across admin and operator areas

**Avoids:** SSE re-render with inline color styles (Integration Gotcha — inline style attributes are invisible to `dark:` variants)

**Research flags:** Standard patterns.

---

### Phase 5: Login Page Glass Card Redesign

**Rationale:** Login pages are standalone templates with no HTMX involvement and always render dark regardless of theme state. They are lower risk than admin/log templates and isolated from the component class system. Addressing them last means the design language is fully established and the glass card refinement is purely additive polish. This is also the only phase where Safari compatibility testing for `backdrop-filter` is required.

**Delivers:** `log/login.html` and `admin/login.html` updated with Apple glass card pattern (`backdrop-blur-md`, `shadow-2xl`, `ring-1 ring-white/10`); explicit `-webkit-backdrop-filter` declared in `@layer components` in `input.css` for the glass card class; `@supports (backdrop-filter: blur(1px))` fallback considered.

**Addresses:** Login glass card refinements (P2), Safari glassmorphism compatibility (Pitfall 6)

**Avoids:** `backdrop-filter` Safari breakage (Pitfall 5); `backdrop-filter` on high-element-count pages (Performance Trap — glass is limited to the single login card, never applied to table rows or list items)

**Research flags:** Standard patterns. Safari compatibility fix is mechanical. Test on Safari before closing this phase.

---

### Phase Ordering Rationale

- Phase 1 before all others: FOWT regression and Tailwind purge are invisible until tested and user-visible immediately in production. No visual work can be trusted without this foundation.
- Phase 2 before templates: token definitions must exist before any template consumes them; going template-first produces hardcoded values that require a second pass.
- Phase 3 before Phase 4: admin templates are simpler (no SSE) and serve as visual reference; Phase 4's log view complexity is reduced when the pattern is already established.
- Phase 5 last: login pages are isolated, low-risk, and additive. Glass card effect is the highest-Safari-risk element — keeping it last means the full test matrix can be completed without blocking earlier phases.

### Research Flags

Phases with standard patterns (skip `/gsd:research-phase`):
- **All five phases:** The entire milestone uses Tailwind CSS, HTMX, and CSS patterns that are thoroughly documented in official sources. STACK.md and ARCHITECTURE.md research is HIGH confidence across all technical decisions.

Areas requiring design judgment during implementation (not blocking research):
- **Phase 2:** Apple HIG token values (specific border-radius measurements, shadow opacity layers, exact background hex values) are MEDIUM confidence. They are the correct starting point; adjust based on visual result during implementation. No research gate required.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Dark mode config verified against official Tailwind v3 docs; heroicons Jinja2 integration confirmed against adamchainz/heroicons README; existing codebase audited directly |
| Features | HIGH | Apple HIG design values verified against Apple Developer docs; existing codebase audited against App Store Connect reference UI; feature scope is corrections + additions, no novel capabilities |
| Architecture | HIGH | Direct live codebase inspection; HTMX `hx-swap` behavior confirmed against official HTMX docs; CSS `@layer` pattern confirmed against Tailwind v3 docs; build pipeline verified operational |
| Pitfalls | HIGH | All six critical pitfalls verified against official Tailwind docs, HTMX GitHub issues, MDN, and caniuse; no finding relies solely on training data; two pitfalls (Tailwind purge, FOWT) confirmed by Tailwind community GitHub discussions |

**Overall confidence:** HIGH

### Gaps to Address

- **Apple HIG exact token values:** Border-radius (10px/8px/6px), shadow layering (opacity and spread values), and exact background hex values (`#1c1c1e`, `#0f0f0f`) are derived from community analysis of Apple UIs, not a published Apple specification document. They are validated through multiple independent community sources and are directionally correct. Adjust visually during Phase 2 implementation if the rendered result diverges from the reference.

- **Inter variable font migration:** Whether to switch from Google Fonts CDN to `@fontsource-variable/inter` is an implementation-time decision. The system font stack (`-apple-system`) achieves the core Apple aesthetic regardless of how Inter is served. If self-hosting adds unexpected build complexity, keeping the CDN link is a valid fallback. Decide in Phase 2.

- **Icon sizing scope:** FEATURES.md identifies `w-5 h-5` as the dominant current icon size across templates. PITFALLS.md recommends `w-6 h-6` for prominent nav icons. The audit in Phase 3 will determine how many icons need updating. Could be narrow (a handful of nav items) or broad (many templates). The fix is mechanical; the only uncertainty is scope.

---

## Sources

### Primary (HIGH confidence)
- [Tailwind CSS Dark Mode (v3) — official docs](https://v3.tailwindcss.com/docs/dark-mode) — `darkMode: 'class'` strategy, toggle pattern
- [Tailwind CSS content configuration — official docs](https://tailwindcss.com/docs/content-configuration) — purge behavior, class scanner rules
- [Tailwind dark mode transition flash — GitHub Discussion #3479](https://github.com/tailwindlabs/tailwindcss/discussions/3479) — transition-on-load pitfall confirmed
- [Tailwind dark mode classes purged in production — GitHub Discussion #4358](https://github.com/tailwindlabs/tailwindcss/discussions/4358) — purge pitfall confirmed
- [adamchainz/heroicons — GitHub README](https://github.com/adamchainz/heroicons) — Jinja2 integration pattern and function signatures
- [heroicons — PyPI](https://pypi.org/project/heroicons/) — version 2.13.0 confirmed
- [HTMX hx-swap documentation](https://htmx.org/attributes/hx-swap/) — innerHTML swap behavior, never touches `<html>` attributes
- [HTMX issue #412](https://github.com/bigskysoftware/htmx/issues/412) — classes removed during HTMX settle period
- [caniuse: CSS backdrop-filter](https://caniuse.com/css-backdrop-filter) — browser support table
- [MDN browser-compat-data #25914](https://github.com/mdn/browser-compat-data/issues/25914) — Safari 18 `backdrop-filter` + CSS variable values: confirmed open bug (2025)
- [Apple Human Interface Guidelines — Color](https://developer.apple.com/design/human-interface-guidelines/color) — semantic color philosophy, surface hierarchy
- [Apple Human Interface Guidelines — Typography](https://developer.apple.com/design/human-interface-guidelines/typography) — type scale, weight, and case conventions
- [Apple Developer Forums — SF Fonts web embedding](https://developer.apple.com/forums/thread/127350) — confirms no `@font-face` licensing for SF Pro

### Secondary (MEDIUM confidence)
- [Apple HIG design system tokens — cmurphy1140/apple-design-system](https://github.com/cmurphy1140/apple-design-system) — border-radius and shadow token values
- [iOS App Design Guidelines 2025 — tapptitude](https://tapptitude.com/blog/i-os-app-design-guidelines-for-2025) — Apple design token analysis
- [Apple macOS dark color cheat sheet — sarunw.com](https://sarunw.com/posts/dark-color-cheat-sheet/) — `#1c1c1e` and `#0f0f0f` background values
- [Disable CSS transitions on color scheme change — reemus.dev](https://reemus.dev/article/disable-css-transition-color-scheme-change) — `no-transition` class suppression pattern
- [System Font Stack — CSS-Tricks](https://css-tricks.com/snippets/css/system-font-stack/) — `-apple-system` fallback behavior
- [@fontsource-variable/inter — npm](https://www.npmjs.com/package/@fontsource-variable/inter) — self-hosted variable font option
- [SVG blurry on Retina — SVGGenie](https://www.svggenie.com/blog/svg-blurry-fixes) — HiDPI icon sizing behavior

---
*Research completed: 2026-04-11*
*Ready for roadmap: yes*
