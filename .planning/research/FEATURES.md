# Feature Research

**Domain:** Apple-like UI redesign — admin console and login page (FastAPI + HTMX + Jinja2 + Tailwind CSS)
**Researched:** 2026-04-11
**Confidence:** HIGH (Apple HIG verified via Apple Developer docs; Tailwind dark mode via official docs; Heroicons sizing via official library docs; FOUC prevention via MDN + CSS-Tricks; existing codebase audited directly)

---

## Context and Constraints

This research answers: what is the right feature set for the Apple-like UI redesign milestone in ollog?

**What already exists (do not re-implement):**
- `darkMode: 'class'` strategy in `tailwind.config.js` — class toggling is already wired
- Inline `<script>` in `<head>` reads `localStorage.getItem('theme')` and applies `dark` class before paint — FOUC prevention is already implemented
- `toggleTheme()` JS function in `base_app.html` with moon/sun icon swap and `localStorage.setItem`
- Sidebar dark mode toggle button wired to `toggleTheme()`
- Full Tailwind `dark:` variant coverage on all component classes in `input.css`
- Heroicons SVG icons used throughout (outline style, `stroke-width="1.5"`, `w-5 h-5` sizing on nav items, `w-4 h-4` on button icons)
- Custom `sidebar.*` color tokens in `tailwind.config.js`
- Component CSS classes: `.card`, `.card-header`, `.card-title`, `.card-body`, `.btn`, `.btn-primary`, `.btn-danger`, `.btn-success`, `.btn-secondary`, `.btn-ghost`, `.btn-sm`, `.form-input`, `.form-label`, `.form-hint`, `.form-select`, `.badge-green`, `.badge-red`, `.badge-blue`, `.badge-gray`, `.alert-error`, `.alert-success`, `.alert-warning`, `.data-table`, `.table-wrap`, `.nav-item`, `.nav-item-active`
- Inter font loaded via Google Fonts, configured as `font-sans` in Tailwind

**What this milestone adds:**
- Shift font stack from Inter (external CDN) to system font stack (`-apple-system, BlinkMacSystemFont, "SF Pro Display", ui-sans-serif, system-ui, sans-serif`)
- Refine color tokens to match Apple's semantic color philosophy (label/secondary/tertiary hierarchy, layered backgrounds)
- Tighten spacing, border-radius, and shadow values to Apple HIG proportions
- Ensure icon stroke widths and sizes follow Heroicons v2 conventions consistently
- Smooth CSS transition on theme switch (no JS animation libraries)
- Login page: dark gradient stays, gains Apple-style refinements
- Admin console: card surfaces, table styling, badge rendering, button hierarchy aligned to Apple aesthetic

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that define "Apple-like" — missing them means the redesign does not land.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| System font stack (SF Pro on Apple devices) | The single most recognizable element of Apple UI. SF Pro renders at every size from 11px to 34px with optical sizing. Non-Apple devices fall back to Segoe UI / Roboto gracefully. | LOW | Replace Inter `@import` with `-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif` in `input.css` base layer. Remove Google Fonts `<link>` tags from `base.html`. Update `tailwind.config.js` `fontFamily.sans`. |
| Generous, consistent whitespace | Apple UIs breathe. Crowded layouts feel un-Apple immediately. The admin table and form need more breathing room between rows, between cards, and around headings. | LOW | Increase `card-body` padding from `py-5` to `py-6`. Table `td` padding from `py-3` to `py-3.5`. Page-level `space-y` from `space-y-6` to `space-y-8`. |
| Subtle, physically-grounded card shadows | Apple uses `box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08)` — close to the current `shadow-sm` but needs a second shadow layer for realism. Dark mode: no shadow (surfaces are distinguished by background color elevation, not shadow). | LOW | Extend `tailwind.config.js` with a custom `shadow-card` token. Apply in `.card` component. Add `dark:shadow-none`. |
| Rounded corners at Apple proportions | Apple uses `border-radius: 10px` for cards, `8px` for form inputs, `6px` for small badges. Current `rounded-xl` (12px) on cards is close; `rounded-lg` (8px) on inputs is correct. Small badges need `rounded-md` (6px) not `rounded-full`. | LOW | Audit badge classes: change from `rounded-full` to `rounded-md`. Keep `rounded-xl` on cards. Keep `rounded-lg` on inputs. Login card: keep `rounded-2xl`. |
| Layered background colors for depth | Apple uses two levels: primary background (white / near-black) and secondary background (gray-50 / slightly elevated dark) to separate card surfaces from page canvas. This is already partially done (`bg-white dark:bg-gray-900` cards on `bg-slate-50 dark:bg-gray-950` page). Needs tightening. | LOW | Standardize: page canvas = `bg-gray-50 dark:bg-[#0f0f0f]`, card surface = `bg-white dark:bg-[#1c1c1e]`. These are Apple's exact HIG background values for grouped interfaces. |
| Typography hierarchy (SF Pro scale) | Apple uses 13px/medium for table cell content, 11px/semibold for labels and column headers, 15px/semibold for card titles, 17px/bold for page headers. Current sizes are close but inconsistent (card title uses `text-sm` uppercase tracking which is not Apple — Apple prefers sentence-case, heavier weight, no letter-spacing). | MEDIUM | Redesign `.card-title`: remove `uppercase tracking-wider`, use `text-[15px] font-semibold text-gray-900 dark:text-white`. Table `th`: change to `text-[11px] font-semibold text-gray-500 dark:text-gray-400` (keep uppercase for this context — it's standard in Apple admin UIs like App Store Connect). |
| Primary accent color (Apple blue or brand violet) | Apple uses system blue (`#007AFF`) as primary accent. The existing brand uses indigo/violet, which is distinctive. Keep the brand color but ensure it renders correctly in both light and dark modes. | LOW | Current `indigo-600` / `violet-600` split is slightly inconsistent. Commit to a single accent: `indigo-600` (#4F46E5) for primary actions everywhere. Login card: keep violet (it's a separate design context). |
| Focus rings that match Apple FaceID/accessibility look | Apple's focus treatment: `2px solid [accent-color]`, `2px offset`. Current implementation is correct (`focus:ring-2 focus:ring-indigo-500`). Needs audit to ensure no elements are missing focus rings. | LOW | Audit all interactive elements in `users_table.html` and `login.html` for focus classes. HTMX-driven buttons need `focus:outline-none focus:ring-2` even in partial templates. |
| Dark/light toggle visible and accessible | Users expect to find a theme toggle. Current placement (bottom of sidebar) is good for an admin console. Toggle label must update ("Dark mode" / "Light mode"). | LOW | Already implemented. Verify moon/sun icon swap works after HTMX partial swaps (icon state is re-initialized on `DOMContentLoaded` — confirm this fires correctly after HTMX `htmx:afterSwap`). |
| Smooth theme transition (no flash, no jarring swap) | A 200ms `transition-colors` on the `body` or root makes theme switching feel polished, not abrupt. | LOW | Add `transition-colors duration-200` to `body` in base CSS. Important: only apply transition *after* initial paint (the inline head script sets the class before transition is active, preventing FOUC on load while still enabling smooth manual toggle). |

### Differentiators (Competitive Advantage)

Features beyond baseline Apple aesthetics that elevate the admin console further.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `color-scheme` meta tag and CSS property | Tells the browser's native UI elements (scrollbars, date inputs, select dropdowns) to also respect the dark/light theme. Without this, native controls stay light even when your UI is dark. Apple's own web properties always set this. | LOW | Add `<meta name="color-scheme" content="light dark">` to `base.html`. Add `color-scheme: light dark` to the `html` selector in `input.css`. |
| Sidebar with correct Apple dark navy (not pure black) | Apple sidebar backgrounds are never `#000` — they use a warm-dark navy that matches macOS sidebars (`#1c1c1e` system background, or `#1a1d2e` as currently defined). The current `sidebar.DEFAULT: '#1a1d2e'` is close to Apple's macOS sidebar color. Refine to match. | LOW | Current custom sidebar color is already Apple-adjacent. Minor tuning: `sidebar.DEFAULT: '#1c1c1e'` (exact Apple system grouped background in dark mode). Sidebar border: `#2c2c2e` (Apple separator color). |
| Heroicons stroke width consistency | Heroicons v2 `outline` style is designed at `stroke-width="1.5"`. Using `2` on small icons makes them look chunky. All sidebar icons should be `1.5`. Button icons at 16px (`w-4 h-4`) can use `2` for legibility. This is the same convention Apple uses (thinner strokes at larger sizes, slightly bolder at smaller sizes). | LOW | Audit all SVG icons in templates. Nav/sidebar icons (`w-5 h-5`): enforce `stroke-width="1.5"`. Button icons (`w-4 h-4`): allow `stroke-width="2"`. Already mostly correct — verify `users_table.html` action buttons. |
| Semantic HTML improvements for accessibility | Apple's own web interfaces use `<header>`, proper `<label for="">` associations, `aria-label` on icon-only buttons. Current templates use `<h1>` in card headers (correct) but lack `aria-label` on HTMX action buttons. | MEDIUM | Add `aria-label="Enable operator"`, `aria-label="Disable operator"`, `aria-label="Reset password"` to action buttons in `users_table.html`. Ensures screen readers work correctly, which aligns with Apple's accessibility-first philosophy. |
| Login page: refine gradient and glass card | Login page already uses a dark gradient background with a frosted glass card (`bg-white/5 backdrop-blur-sm border border-white/10`). Apple's 2025 Liquid Glass design elevates this pattern. Minor refinements: slightly increase blur (`backdrop-blur-md`), add `shadow-2xl` to the card, use `ring-1 ring-white/10` instead of `border`. | LOW | Login card changes are isolated to `login.html` — no CSS component changes needed. Pure Tailwind class changes. |
| Consistent icon sizing between admin and operator areas | The admin area (`base_app.html` already has `w-5 h-5` on sidebar icons) must match exactly so that if the admin is also an operator moving between views, nothing feels different. | LOW | Verify the admin `users.html` sidebar override uses same `w-5 h-5` sizing as the base sidebar. Already appears correct based on code audit. |

### Anti-Features (Commonly Requested, Often Problematic)

Features to explicitly not build during this milestone.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Liquid Glass / backdrop-filter everywhere | Apple's WWDC 2025 Liquid Glass trend is visually impressive. Developers want to replicate it. | Liquid Glass (`backdrop-filter: blur + saturate + brightness`) is performance-expensive. On low-end hardware or when applied to HTMX-swapped partial DOM nodes, it causes repainting issues. Looks great in native apps with GPU compositing; unpredictable in HTML table rows. | Use it only where Apple already uses it: the login modal card (`backdrop-blur-md`) and nothing else. Admin console uses solid card surfaces. |
| Framer Motion / GSAP animations | Smooth element entry animations look polished in design demos. | This is a server-rendered Jinja2 + HTMX app. Adding a JS animation framework introduces a runtime dependency that conflicts with HTMX's `hx-swap` transitions. HTMX has its own `htmx-swapping` / `htmx-settling` CSS hook system. | Use CSS `transition-all duration-150` on interactive elements. Use HTMX's built-in `hx-swap="innerHTML transition:true"` if fade-in on table row insert is desired (Tailwind opacity class). |
| Custom SVG icon library (e.g., Phosphor, Lucide) | Lucide or Phosphor have more icon variety than Heroicons. | The codebase is already 100% Heroicons SVG (inline). Switching icon libraries means auditing and replacing every icon in every template — a disproportionate effort that delivers zero user-visible improvement for a UI polish milestone. | Stay on Heroicons v2 outline. If a specific icon is missing, add it as a one-off inline SVG. |
| Google Fonts CDN fallback for non-Apple devices | "What if system fonts look bad on Windows?" | System font stacks already include `"Segoe UI"` for Windows (renders well), `"Roboto"` for older Android, `"Helvetica Neue"` as a macOS fallback. Loading an external font file adds 50-200ms of render-blocking latency and a third-party network dependency for an admin tool that should work offline. | Remove the Inter Google Fonts `<link>` from `base.html`. The system font stack is the correct solution. |
| Three-state toggle (Light / Dark / System) | GitHub, Linear, and Notion offer a three-state toggle (light, dark, system default). | The admin console is a low-frequency tool (accessed occasionally, not daily). A three-state toggle adds UI complexity (three states in the toggle button label/icon, more localStorage state) for marginal value. The current two-state implementation (light/dark, respects `prefers-color-scheme` on first load) is correct for this context. | Keep the two-state toggle. System preference is respected on first visit via the existing `prefers-color-scheme` check in the head script. |
| Custom CSS animations on button hover | Animated scale/glow on hover feels "premium" | These require `transform` and complex `transition` chains that interact poorly with HTMX indicator states (`htmx-request` class). Apple's own web admin interfaces (App Store Connect, Apple Business Manager) do not use hover animations on buttons — they use simple `background-color` transitions. | `hover:bg-indigo-500 transition-colors duration-150` is the correct Apple approach. Already implemented. |
| Dark mode for the login page's gradient background | "The login page should respond to the dark toggle too." | The admin login page extends `base.html` (not `base_app.html`), which does not include the sidebar or `toggleTheme()` script. The page's hardcoded dark gradient works correctly for its purpose — it is always dark because admin login pages conventionally use dark/dramatic backgrounds regardless of system preference. | Leave the login page with its dark gradient as a design choice. No `dark:` variants needed on `login.html`. |

---

## Feature Dependencies

```
System Font Stack
    └──requires──> Remove Google Fonts <link> from base.html
                       └──requires──> Update tailwind.config.js fontFamily.sans

Layered Background Colors
    └──requires──> Tailwind config custom color tokens (or direct Tailwind values)
                       └──enhances──> Card shadow refinement (dark:shadow-none)

color-scheme CSS property
    └──requires──> Meta tag in base.html
    └──requires──> CSS property on html selector in input.css
    └──enhances──> Native scrollbar/input rendering in dark mode

Theme Transition (smooth toggle)
    └──requires──> transition-colors on body/html (not on html at load time — causes FOUC)
    └──note: must NOT apply during initial paint; only activates after page is loaded

Badge border-radius change (rounded-full -> rounded-md)
    └──requires──> Audit all .badge-* usages in templates (users_table.html, log templates)
    └──affects──> Both admin and operator areas (shared CSS classes)

Card title typography change
    └──conflicts──> Existing uppercase tracking convention in .card-title
    └──requires──> Update every template using .card-title to confirm visual result
```

### Dependency Notes

- **System font stack requires Google Fonts removal:** Leaving both in place causes a flash — Google Fonts loads asynchronously and replaces system font mid-render.
- **Theme transition must not apply at initial paint:** The head script sets `class="dark"` before CSS loads. If `html { transition-colors }` is always active, it animates the initial dark-mode application on load, causing a 200ms fade from white to dark. Solution: add `transition-colors` via a JS `classList.add` call after `DOMContentLoaded` fires.
- **Badge radius change affects shared classes:** `.badge-green`, `.badge-red`, etc. are used in both admin `users_table.html` and operator log tables. A change to the shared component affects both contexts — verify both look correct.
- **HTMX partial swaps and `DOMContentLoaded`:** The `updateThemeIcons()` function fires on `DOMContentLoaded`. After an HTMX swap replaces the sidebar (which doesn't happen in current code — the sidebar is not an HTMX target), icons would reset. Confirm that sidebar is never a swap target. It is not, in current code.

---

## MVP Definition

This is a UI-only milestone with no backend changes. All features are purely frontend (HTML templates + CSS).

### Launch With (v1)

- [ ] System font stack — drop Inter CDN, use `-apple-system` stack — foundational, affects every page
- [ ] `color-scheme` meta tag + CSS property — browser native controls respect theme
- [ ] Layered background color refinement — page canvas vs card surface distinction tightened
- [ ] Smooth theme transition after paint (not at load) — polished toggle feel
- [ ] Badge border-radius: `rounded-full` to `rounded-md` — Apple badge convention
- [ ] Card shadow refinement — second shadow layer for light mode, `shadow-none` for dark
- [ ] Card title typography update — remove uppercase tracking, use sentence-case semibold
- [ ] Icon stroke-width audit — `1.5` on navigation, `2` on small button icons
- [ ] Accessibility audit: `aria-label` on HTMX action buttons in `users_table.html`

### Add After Validation (v1.x)

- [ ] Login page glass card refinements (`backdrop-blur-md`, ring treatment) — isolated change, low risk, add if main work looks clean
- [ ] Sidebar color tuning (`#1c1c1e` vs `#1a1d2e`) — very minor, validate after font/color system changes settle

### Future Consideration (v2+)

- [ ] Heroicons v3 migration (if released) — check for any sizing/API changes before upgrading
- [ ] CSS `@layer` restructure to align with Tailwind v4's native cascade layers — not yet needed

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| System font stack (SF Pro on Apple) | HIGH | LOW | P1 |
| Layered background colors | HIGH | LOW | P1 |
| `color-scheme` property + meta tag | HIGH | LOW | P1 |
| Badge rounded-md (not rounded-full) | MEDIUM | LOW | P1 |
| Card shadow refinement | MEDIUM | LOW | P1 |
| Smooth theme transition after paint | MEDIUM | LOW | P1 |
| Card title typography (no uppercase) | MEDIUM | LOW | P1 |
| Icon stroke-width consistency audit | LOW | LOW | P2 |
| Aria-label on action buttons | MEDIUM | LOW | P2 |
| Login glass card refinements | LOW | LOW | P2 |
| Sidebar color tuning | LOW | LOW | P3 |

**Priority key:**
- P1: Must have — defines whether the redesign achieves "Apple-like"
- P2: Should have — polish and correctness, not blockers
- P3: Nice to have, minimal impact

---

## Competitor / Reference Analysis

These are the reference points for "Apple-like admin UI on web":

| Design Pattern | Reference UI | Current ollog | Target |
|----------------|-------------|---------------|--------|
| Font | Inter (Google CDN) | Inter | `-apple-system` system stack |
| Card background (light) | App Store Connect: `#ffffff` on `#f5f5f7` page | `bg-white` on `bg-slate-50` — close | `bg-white` on `bg-gray-50` — tighten values |
| Card background (dark) | macOS system: `#1c1c1e` on `#000000` | `bg-gray-900` on `bg-gray-950` — close | `bg-[#1c1c1e]` on `bg-[#000000]` or `bg-[#0f0f0f]` |
| Badge shape | Apple SF Symbols badge: rectangle with 6px radius | `rounded-full` (pill) | `rounded-md` (6px) |
| Card title | App Store Connect: 15px/600 sentence-case | `text-sm uppercase tracking-wider` | `text-[15px] font-semibold` no uppercase |
| Button hover | Apple web: color shift only | `hover:bg-*` — correct | Keep as-is |
| Shadow | Apple: subtle 2-layer shadow in light, none in dark | `shadow-sm` only | `shadow-card` custom 2-layer in light, `shadow-none` in dark |
| Icon stroke | Heroicons recommended: 1.5 for outline 24px | Mixed: some 1.5, some 2 on nav | Standardize: 1.5 nav/24px, 2 for button/16px |
| color-scheme | Apple web: always set | Not set | Add meta + CSS property |

---

## HTMX / Jinja2 Integration Notes

These are implementation constraints unique to this stack that affect feature delivery:

1. **No client-side component re-render.** All template changes go to `.html` files. CSS changes go to `input.css` and trigger a Tailwind rebuild (`npx tailwindcss -i input.css -o output.css`). No build pipeline beyond that.

2. **HTMX partial swaps swap `tbody` content, not the full page.** Dark mode class on `<html>` persists across swaps. Theme state is stable through HTMX navigation.

3. **`DOMContentLoaded` fires once per full page load, not after HTMX swaps.** The `updateThemeIcons()` function is safe because the sidebar (which contains the theme toggle icon) is never an HTMX swap target in current templates.

4. **Tailwind CSS class purging.** All classes used in templates must appear literally (not constructed dynamically via Jinja2 string concatenation) for Tailwind to include them in the output. Current dynamic class usage (`{{ 'btn-danger' if user.enabled else 'btn-success' }}`) is fine — both class names appear as string literals in the template.

5. **Any new color values used as `bg-[#1c1c1e]` (arbitrary values) require the Tailwind rebuild to run.** Arbitrary value syntax works at build time, not at runtime. This is fine for this project — it already uses a build step.

---

## Sources

- Apple Human Interface Guidelines — Color: https://developer.apple.com/design/human-interface-guidelines/color
- Apple Human Interface Guidelines — Typography: https://developer.apple.com/design/human-interface-guidelines/typography
- Heroicons v2 official docs (outline/solid/mini/micro sizing): https://heroicons.com
- Tailwind CSS Dark Mode (class strategy): https://tailwindcss.com/docs/dark-mode
- Tailwind CSS color-scheme: https://tailwindcss.com/docs/color-scheme
- CSS-Tricks — Flash of Inaccurate Color Theme (FART): https://css-tricks.com/flash-of-inaccurate-color-theme-fart/
- MDN — prefers-color-scheme: https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-color-scheme
- systemfontstack.com: https://systemfontstack.com/
- Apple macOS system semantic colors (dark mode cheat sheet): https://sarunw.com/posts/dark-color-cheat-sheet/

---
*Feature research for: Apple-like UI redesign — ollog admin console and login page*
*Researched: 2026-04-11*
