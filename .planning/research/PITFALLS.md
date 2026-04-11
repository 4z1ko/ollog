# Pitfalls Research

**Domain:** Apple-like UI redesign + dark/light mode — Jinja2 + HTMX 2.0.4 + Tailwind CSS v3
**Researched:** 2026-04-11
**Confidence:** HIGH (all critical pitfalls verified against official Tailwind docs, HTMX GitHub issues, and MDN; no finding relies solely on training data)

---

## Summary

Four distinct risk profiles converge in this milestone. The flash-of-wrong-theme (FOWT) pitfall
is the most user-visible: a white flash on hard navigation that is imperceptible in development
but immediately obvious to any user who chose dark mode. Tailwind purge removing `dark:` classes
is the most insidious: it is undetectable in development (full CSS is always present) but breaks
the production build silently. The HTMX partial-swap desync problem is the most project-specific:
the existing codebase has three HTMX swap targets and an SSE-driven refresh, each of which can
leave the dark mode toggle icon in the wrong state. The SVG sharpness problem is cosmetic but
directly at odds with the Apple aesthetic goal.

This project already has the FOWT prevention correctly implemented (inline IIFE in `<head>` in
`base.html`). The primary risk is regressing that during the redesign. The Tailwind purge risk
requires a build-discipline gate to be established before any visual work begins. The HTMX desync
risk requires a single `htmx:afterSettle` listener to be added once, early.

---

## Critical Pitfalls

### Pitfall 1: Flash of Wrong Theme (FOWT) — Regression During Redesign

**What goes wrong:**
The page briefly renders in light mode before the `dark` class is applied to `<html>`, even though
the user had selected dark mode. A white flash appears on every hard navigation, page refresh, and
browser-back event.

**Why it happens:**
The browser paints HTML synchronously before JavaScript executes. If the theme-restoration script
is ever moved out of `<head>`, converted to an external file, or given `defer`/`async`/`type="module"`,
the stylesheet cascade runs without the `dark` class on `<html>`. By the time JavaScript reads
`localStorage` and adds `dark`, the browser has already painted the wrong colors.

**This project's current state:**
`base.html` lines 13–21 already have the correct inline IIFE. This is the right approach. The risk
is regression during the redesign: the IIFE could be accidentally moved during template refactoring,
extracted into a JS file for "cleanliness," or wrapped in a Jinja2 `{% block head_scripts %}` block
that renders at the bottom of `<body>`.

**How to avoid:**
- Keep the theme script as a raw inline `<script>` block in `<head>`, positioned before the
  `<link rel="stylesheet">` tag.
- Never add `defer`, `async`, or `type="module"` to it.
- Never extract it to a static JS file.
- Never place it in a Jinja2 `{% block %}` that a child template could move or omit.
- Test explicitly: set dark mode, do a hard refresh (Cmd+Shift+R), verify zero white flash.
- Add a code comment marking it as load-bearing: `<!-- LOAD-BEARING: must be inline, in <head>, before stylesheet -->`.

**Warning signs:**
- Any PR that moves or removes the `<script>` block from `<head>` in `base.html`.
- A new `<script src="/static/js/theme.js">` tag appearing where the inline script was.
- `type="module"` added to the theme script (modules are deferred by spec).
- White flash visible on hard reload in development, even briefly.
- A Jinja2 `{% block %}` wrapping the theme script, allowing child templates to override it.

**Phase to address:** Theme infrastructure setup — first task, before any visual template changes.

---

### Pitfall 2: Tailwind Purges `dark:` Variants in Production Build

**What goes wrong:**
Dark mode classes that appear only in files not covered by the `content` glob, or that are
constructed via string concatenation, are absent from the production CSS bundle. The UI looks
correct in development (`output.css` is rebuilt continuously by `npm run watch` or is stale-but-complete)
but dark mode breaks after `npm run build --minify`.

**Why it happens:**
Tailwind's content scanner treats every source file as plain text. A class is included in the
output only if its complete literal string (e.g., `dark:bg-gray-900`) appears somewhere in a
scanned file. The current `tailwind.config.js` scans `./templates/**/*.html`. Any class that:

- Is constructed dynamically in Python (e.g., `"dark:bg-" + severity`),
- Exists only in a new template directory outside `./templates/`,
- Appears only in a JavaScript `classList.add()` call that is not in a `.html` file,
- Is a new Apple-style utility like `dark:backdrop-blur-xl` or `dark:ring-white/10` added to a
  template while the build watcher is not running,

...will be missing from the production bundle.

**The specific trap for this project:**
The redesign will introduce new classes. If the developer adds `dark:bg-white/5 dark:ring-1
dark:ring-white/10` to a template during a dev session with `npm run watch` running, those classes
appear in the live `output.css`. But if the same template is edited without the watcher, or if the
build is not re-run before commit, the committed `output.css` will be missing those classes and
dark mode will silently break for those elements.

**How to avoid:**
- Always run `npm run watch` during development. Never rely on a stale `output.css`.
- Run `npm run build` and perform a visual dark-mode smoke test before every commit that touches
  `.html` templates or `input.css`.
- For any new class added during the Apple redesign (glassmorphism utilities, new color stops,
  `ring-white/*` opacity variants), verify with: `grep "class-name" static/css/output.css`.
- Never construct Tailwind class names via Python string concatenation or f-strings. Use complete
  literal class name strings.
- If Python needs to vary classes conditionally, use a lookup dict (complete strings as values,
  not string-assembled fragments).
- Add `output.css` to the git repository (it already appears to be committed) and verify it is
  rebuilt via `npm run build` in CI before deployment.

**Warning signs:**
- A dark mode style works in the development browser but is missing after deploying.
- Python code contains `"dark:" + variable` patterns.
- `grep "dark:backdrop" static/css/output.css` returns nothing after a build that added glassmorphism.
- A new `.html` file lives outside `./templates/` (e.g., in `components/` or `views/`).
- The build watcher was not running when templates were edited.

**Phase to address:** Theme infrastructure setup (establish build discipline and verification gate);
repeated at the end of each component-level phase as a go/no-go check.

---

### Pitfall 3: HTMX Partial Swaps Desync the Theme Toggle Icon

**What goes wrong:**
After an HTMX swap replaces content (e.g., sorting the log table, paginating, submitting the
create-operator form), the dark mode toggle in the sidebar shows the wrong icon or label. The
`dark` class on `<html>` is unaffected — the page colors remain correct — but the toggle button
displays moon when it should show sun, or the label says "Dark mode" when it should say "Light mode."

**Why it happens:**
The `updateThemeIcons()` function in `base_app.html` runs once on `DOMContentLoaded`. HTMX swaps
do not re-fire `DOMContentLoaded`. In the current codebase, this is not yet a problem because the
sidebar (which contains the toggle) is never the HTMX swap target. However:

1. If a future HTMX swap uses `hx-swap-oob` to update any element that contains or is an ancestor
   of `#theme-btn`, `#icon-moon`, `#icon-sun`, or `#theme-label`, the newly-inserted HTML will not
   have the icon state set by JavaScript — it will reflect whatever the server rendered.

2. New Apple-style components added during the redesign that have theme-dependent initialization
   (a toggle chip, a colored status badge, a modal with theme-aware backdrop) will not initialize
   correctly after any HTMX swap unless they listen to `htmx:afterSettle`.

3. HTMX's settle period is a specific danger zone: `htmx:afterSwap` fires before HTMX restores
   original classes from the server response, so an icon re-initialization running on `afterSwap`
   may be overwritten by HTMX's own settle step. The correct event is `htmx:afterSettle`.

**This project's current HTMX targets:**
- `#log-table` (innerHTML): log table rows and pagination. Does not contain the toggle.
- `#users-table-body` (innerHTML): operator rows. Does not contain the toggle.
- SSE-driven refresh of `#log-table`: same scope as above.
- The `<html>` and `<body>` elements are never HTMX targets. The `dark` class on `<html>` is safe.

**How to avoid:**
- Add a single `htmx:afterSettle` event listener on `document.body` that calls
  `updateThemeIcons(document.documentElement.classList.contains('dark'))`. This is a one-line
  addition to the existing `<script>` block in `base_app.html`.
- Never use `hx-swap="outerHTML"` or `hx-swap-oob` on elements that are ancestors of the
  toggle button (i.e., the sidebar, `<body>`, or `<html>`).
- When adding new Apple-style components that need theme-aware JS initialization, always register
  on `htmx:afterSettle`, not only `DOMContentLoaded`.
- Use `htmx:afterSettle` (not `htmx:afterSwap`) because HTMX may restore server-supplied classes
  during the settle window after `afterSwap` fires.

**Warning signs:**
- The toggle label says "Light mode" after clicking a column sort link in the log table.
- A new component has a `DOMContentLoaded` listener for theme initialization but no `htmx:afterSettle` listener.
- An `hx-swap-oob` target in a server response wraps or contains the sidebar.
- Any HTMX request targets `body` or sets `hx-target` to a selector that matches an ancestor of `#theme-btn`.

**Phase to address:** Theme infrastructure setup — add the `htmx:afterSettle` handler once, early,
before building any new components.

---

### Pitfall 4: SVG Icons Blurry on HiDPI / Retina Displays

**What goes wrong:**
Icons in the redesigned Apple-style UI look fuzzy or anti-aliased on Retina and HiDPI displays
(MacBook Pro, iPhone, any 2x+ device pixel ratio display). This is directly contrary to the goal
of an Apple-quality aesthetic — Apple users are acutely sensitive to sub-pixel rendering artifacts.

**Why it happens:**
The Heroicons used throughout this project have `viewBox="0 0 24 24"`. Rendering them at exactly
24px CSS (or multiples of 24px) keeps stroke coordinates on integer pixel boundaries. Rendering at
20px CSS (`w-5 h-5`, the most common Tailwind icon size) requires a 20/24 = 0.833x scaling factor.
On a 1x display this is undetectable. On a 2x Retina display, the browser renders 40 physical
pixels divided by 24 viewBox units = 1.667 physical pixels per SVG unit — fractional pixel
coordinates force anti-aliasing on all stroke edges, producing visibly blurry icons.

The problem is most pronounced for prominent icons (sidebar nav, card headers, modal icons) and
worst at `w-5 h-5` (20px). Less visible at `w-4 h-4` (16px) on 2x displays (32 physical pixels,
ratio is 1.333x — acceptable for small secondary icons).

**How to avoid:**
- For prominent icons in the Apple redesign (sidebar nav items, card headers, empty state
  illustrations, button icons), use `w-6 h-6` (24px CSS) — a 1:1 match with the Heroicons
  `viewBox`. Sharp at both 1x and 2x.
- For small secondary icons (sort indicators, inline text icons), `w-4 h-4` (16px) is acceptable.
  The anti-aliasing at this size is visually tolerable.
- Avoid `w-5 h-5` for prominent icons. It is the worst case for 2x rendering.
- Never use `<img src="icon.svg">`. Use inline `<svg>` only: it inherits CSS `color`, responds
  to `dark:` variants, and uses the full display DPR for rasterization.
- Never apply CSS `transform: scale()` to icons. Use explicit Tailwind size classes.
- Do not use arbitrary sizes like `w-[18px]` or `w-[22px]` — they produce non-integer ratios
  against the 24px viewBox at both 1x and 2x.

**Warning signs:**
- Redesigned nav items or card headers use `w-5 h-5` icons.
- Any icon element uses `<img>` instead of inline `<svg>`.
- An icon uses `w-[18px]`, `w-[22px]`, or any arbitrary pixel value not in the w-4/w-5/w-6 set.
- Icons look correct on a 1080p monitor but blurry on a MacBook Pro Retina.

**Phase to address:** Component styling phase — apply consistently when building all Apple-style
nav items, card headers, and any new icon usage.

---

### Pitfall 5: CSS Transitions Cause Their Own Flash on Page Load

**What goes wrong:**
When `transition-colors duration-300` is added to `<body>`, cards, or table cells (a natural
choice for a smooth Apple-like theme toggle), it causes a visible color-fade animation on every
hard page load. Instead of preventing the flash of wrong theme, it makes it worse: the page
fades from light to dark over 300ms on every navigation.

**Why it happens:**
The inline IIFE in `<head>` adds the `dark` class to `<html>` synchronously. However, child
elements painted after the external stylesheet loads — which happens slightly after the script
runs — have transitions active from the moment the CSS is parsed. Any element that paints its
initial background color in a state that briefly conflicts with the `dark` class before the
browser resolves the cascade will animate the transition visibly.

Specifically: if `transition-colors` is on `<body>` or `.card` in a `@layer base` rule, the
initial paint of those elements may trigger the transition even on first load, creating a
300ms fade from a light background to the correct dark background.

**How to avoid:**
- Do NOT add `transition-colors` or `transition-all` to `<html>`, `<body>`, `.card`, `.data-table td`,
  `.form-input`, or any element that is painted as part of the initial page layout.
- Add smooth transitions ONLY to explicitly interactive states: the theme toggle button's own
  indicator, hover states on nav items, focus rings on inputs.
- For the toggle button animation, transition the button's icon rotation or label opacity —
  not the page background.
- If full-page theme transition on *user-initiated* toggle (not on load) is desired, use a JS
  approach: suppress all transitions during initial load by adding a `no-transition` utility
  class to `<html>` and removing it in the IIFE, after the `dark` class is set:
  ```html
  <script>
    (function() {
      document.documentElement.classList.add('no-transition');
      var theme = localStorage.getItem('theme');
      if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
      }
      // Remove no-transition after first paint to allow user-initiated toggle to animate
      requestAnimationFrame(function() {
        document.documentElement.classList.remove('no-transition');
      });
    })();
  </script>
  ```
  Then define `.no-transition * { transition: none !important; }` in `input.css`.

**Warning signs:**
- A `@layer base` rule adds `transition-colors` to `html`, `body`, or `*`.
- Cards or the page background visibly fade in to the correct dark color on each page load.
- The fade is more visible on slow network connections (larger gap between script and first paint).
- `transition-all` appears anywhere in the component layer — this catches background-color among
  everything else.

**Phase to address:** Theme infrastructure setup — establish the transition policy before applying
any transitions to components.

---

### Pitfall 6: `backdrop-filter` Glassmorphism Breaks on Older Safari and with CSS Variables

**What goes wrong:**
Apple-like frosted glass cards (`backdrop-filter: blur(...)`) render as plain, non-blurred
opaque backgrounds on older Safari. In Safari 18, `backdrop-filter` works with fixed values
but fails silently when the blur value is specified via a CSS custom property.

**Why it happens:**
Tailwind's `backdrop-blur-*` utilities emit only the unprefixed `backdrop-filter` property. The
`-webkit-backdrop-filter` prefix was required in Safari until version 17. Starting Safari 18,
the prefix is no longer required for fixed values — but there is a confirmed open bug (MDN
browser-compat-data issue #25914, still open in 2025) where `backdrop-filter` with CSS variable
values (e.g., `backdrop-filter: blur(var(--blur))`) fails in Safari even with the prefix. Fixed
values (`blur(12px)`) work; variable references do not.

**How to avoid:**
- For any glassmorphism component class defined in `input.css` via `@apply` or explicit CSS,
  always write both forms:
  ```css
  .glass-card {
    -webkit-backdrop-filter: blur(12px) saturate(180%);
    backdrop-filter: blur(12px) saturate(180%);
  }
  ```
- Do not use CSS custom properties as the value for `backdrop-filter` or `-webkit-backdrop-filter`.
  Use fixed pixel values only.
- Tailwind's `backdrop-blur-*` utilities do NOT add the `-webkit-` prefix automatically. Any
  component using glassmorphism must declare both forms explicitly.
- Test on Safari (macOS or Browserstack) before marking a glass component done. The Chrome/Firefox
  experience is not representative.
- If Safari support cannot be tested, use `@supports (backdrop-filter: blur(1px))` to fall back
  gracefully to a semi-transparent solid background.

**Warning signs:**
- A glass card looks correct in Chrome but shows a solid background in Safari.
- `backdrop-filter` is set via a Tailwind arbitrary value with a CSS variable: `backdrop-blur-[var(--blur)]`.
- Only Tailwind utility classes are used for the blur effect without explicit `-webkit-backdrop-filter`
  in `input.css`.
- `grep "\-webkit-backdrop-filter" static/css/output.css` returns nothing.

**Phase to address:** Glassmorphism / glass card component phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Putting all dark mode logic in `@layer base` (e.g., `body { @apply dark:bg-gray-950 }`) | Centralizes styles, no per-element `dark:` prefixes needed | Dark variant rules become invisible to template authors; inconsistency creeps in as others add inline `dark:` classes in templates | Never — choose one approach and enforce it; prefer inline `dark:` in templates for visibility |
| Using `!important` on dark mode overrides to fix legacy conflicts | Quickly overrides light-mode styles during redesign | Creates specificity wars; hard to remove later; blocks future intent | Only as a temporary bridge for a single PR; must be removed in the same or next phase |
| Storing theme preference in a cookie (server-rendered) instead of localStorage | Server can render the correct `dark` class on `<html>` without JS flash | Adds cookie round-trip; breaks with CDN edge caching; requires session awareness | Never for this project — the current localStorage IIFE is sufficient and correct |
| Using `transition-all` on cards or form elements | Smooth transitions on all state changes | Triggers on every HTMX swap that adds/removes a class; colors also animate on page load FOUC | Never — use `transition-colors` only, on interactive elements only |
| Keeping sidebar background as a raw hex (`#1a1d2e`) only in inline `style=""` | One-off exact Apple color without build-time overhead | Cannot be targeted by `dark:` prefix variants; invisible to Tailwind purge scanner | Unacceptable inline; already correctly placed as a named design token in `tailwind.config.js` |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| HTMX swaps + theme toggle icon | `updateThemeIcons()` only runs on `DOMContentLoaded`; swaps do not re-fire that event | Add `document.body.addEventListener('htmx:afterSettle', ...)` that re-calls `updateThemeIcons()` |
| HTMX SSE re-render (`#log-table`) + inline color styles | SSE-delivered HTML that uses inline `style="background-color: white"` ignores dark mode | Never use inline `style` for color values in HTMX partials; rely entirely on Tailwind classes with `dark:` variants |
| Tailwind build watch + new Apple component classes | Adding `dark:backdrop-blur-xl` or `dark:ring-white/10` while build watcher is not running produces stale `output.css` | Always verify new classes are in the built CSS with `grep` before committing |
| `backdrop-filter` + Tailwind | Tailwind's `backdrop-blur-*` emits only unprefixed property; Safari needs `-webkit-backdrop-filter` | Declare `-webkit-backdrop-filter` explicitly in `@layer components` in `input.css` for glass card components |
| HTMX `hx-push-url="true"` navigation + dark class | Full-page navigation replaces `#log-table` or `#users-table-body`; sidebar persists; `<html>` is never replaced | This is safe by current design — verify no HTMX target is `body` or `html` |
| Jinja2 server-side dark class | Passing `dark_mode=True` from Python to render the `dark` class server-side creates round-trip dependency | Keep dark mode state entirely in `localStorage`; the server never needs to know the theme |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `backdrop-filter: blur()` on many concurrent elements | Scroll jank on mid-tier hardware; GPU memory pressure on mobile; fan noise on MacBooks | Limit glassmorphism to 1–2 focal elements (sidebar, modal, hero card); do not apply to every table row or form card | Immediately on older GPUs; at 3+ concurrent blurred layers on mobile |
| `transition-all` on frequently HTMX-swapped elements | Every swap that adds/removes any class triggers a full CSS transition sweep | Use `transition-colors` scoped to interactive elements only; never `transition-all` | Every HTMX swap; noticeable immediately |
| Overloaded `@layer base` with dark overrides | CSS specificity becomes unpredictable; bundle size grows | Keep base layer minimal (typography, font, HTML element resets); put component dark styles in `@layer components` | At 30+ component override rules in base layer |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Reading `localStorage.theme` and reflecting it into server-side Jinja2 HTML as a class or attribute | If an attacker can write arbitrary values to `localStorage` (via another XSS), the value could be reflected into template output as executable HTML | The theme value is used only in client-side JS as a boolean gate for `classList.add('dark')`; it is never sent to the server or rendered server-side |
| Using `document.write()` or `innerHTML` assignment in the theme IIFE to apply the dark class | If the IIFE is extended and uses `innerHTML`, it opens an XSS vector | The IIFE must only call `document.documentElement.classList.add('dark')`; never write HTML from localStorage values |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Theme toggle only reachable by opening the sidebar on mobile | Mobile users cannot change theme without first opening the sidebar; discovery is zero | Add a small theme toggle icon button to the mobile top bar (`md:hidden` section of `base_app.html`) that is always visible |
| Theme toggle does not follow system preference after it changes | User sets OS to dark mode after having explicitly selected light mode in the app — app stays light (correct). But if user has never explicitly set a preference (`localStorage.theme` is null), and their system changes, the app should follow | The current IIFE already handles this correctly: only override with localStorage if `theme` is explicitly set; otherwise follow `prefers-color-scheme`. Do not regress this. |
| Color contrast failures in dark mode | Gray text on dark gray backgrounds fails WCAG AA (4.5:1 for normal text). Specific failure: `text-gray-500` on `bg-gray-900` = ~3.5:1 contrast ratio | Run all `dark:text-gray-400` and `dark:text-gray-500` instances through a contrast checker against their dark background. Minimum acceptable: 4.5:1 for body text, 3:1 for large text |
| Dark mode transition not announced to screen readers | Screen reader users receive no cue when the theme changes | Add `aria-label` to the toggle button that updates with the action (e.g., "Switch to light mode") and use `aria-live="polite"` on a visually-hidden status element |
| Login page ignores the theme IIFE | The login page shows a white flash or incorrect theme because `base.html` (the login base) may not have been updated in sync with `base_app.html` | Verify both `templates/log/login.html` and `templates/admin/login.html` extend `base.html` which contains the IIFE; do not duplicate the IIFE in login templates |

---

## "Looks Done But Isn't" Checklist

- [ ] **FOWT on hard refresh:** Set dark mode, do Cmd+Shift+R, verify zero white flash. Test on both a login page and an authenticated page.
- [ ] **Dark mode on login pages:** `templates/log/login.html` and `templates/admin/login.html` must both get the `dark` class on `<html>` before paint.
- [ ] **Production CSS contains new classes:** Run `npm run build`, then `grep` for every new Apple-style class added (e.g., `backdrop-blur`, `ring-white/10`, `bg-white/5`, `divide-white/10`).
- [ ] **HTMX swap toggle icon sync:** Sort a column in Log View while in dark mode. Verify the moon/sun icon and label are correct after the swap.
- [ ] **SSE re-render dark survival:** Trigger an SSE-driven `#log-table` refresh. Verify the LIVE badge uses dark colors (`dark:bg-emerald-900/40`).
- [ ] **`-webkit-backdrop-filter` present (if glassmorphism used):** `grep "\-webkit-backdrop-filter" static/css/output.css` must return results.
- [ ] **No `transition-colors` on load-bearing elements:** Inspect `input.css`: no `transition-*` rule in `@layer base` on `html`, `body`, or `*`. No page color fade on hard refresh.
- [ ] **Icon size audit:** All prominent icons (nav items, card headers) use `w-6 h-6` (24px). No `w-5 h-5` on prominent icons in the Apple redesign.
- [ ] **Mobile toggle accessible:** Dark mode toggle is reachable on a narrow viewport without opening the sidebar.
- [ ] **Contrast ratio check:** All `dark:text-gray-400` instances on `dark:bg-gray-900` or `dark:bg-gray-950` backgrounds pass WCAG AA (4.5:1 for normal text).

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| FOWT reinstated (script moved or made external) | LOW | Move the inline IIFE back into `<head>` in `base.html`, before the `<link>` stylesheet; remove `defer`/`async`/`src` if present |
| `dark:` classes missing from production CSS | LOW–MEDIUM | Identify missing classes via visual inspection in dark mode, confirm via `grep` on `output.css`, ensure all templates are in the `content` glob, run `npm run build`, re-verify |
| HTMX swap desyncs toggle icon | LOW | Add `document.body.addEventListener('htmx:afterSettle', function() { updateThemeIcons(document.documentElement.classList.contains('dark')); });` to `base_app.html` |
| Glassmorphism broken on Safari | LOW | Add `-webkit-backdrop-filter` to the glass card class in `input.css`; rebuild CSS; avoid CSS variable values |
| CSS transition plays on page load | LOW | Remove `transition-*` from base-layer HTML/body rules; restrict to interactive hover/focus states |
| SVG icons blurry on HiDPI | MEDIUM | Audit all prominent icons; change `w-5 h-5` to `w-6 h-6`; rebuild; verify visually on a 2x display |
| Color contrast failures discovered post-launch | MEDIUM | Identify failing pairs with a contrast checker; adjust `dark:text-gray-*` level upward (e.g., `400` → `300`) until passing |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Flash of wrong theme (FOWT) | Theme infrastructure setup — Phase 1 | Hard refresh in dark mode: zero white flash; inline script still in `<head>` of `base.html` |
| Tailwind purging dark: variants | Theme infrastructure setup — Phase 1 (build discipline) + verification gate at end of each phase | `npm run build` + `grep` new classes in `output.css`; visual dark smoke test |
| HTMX swap toggle icon desync | Theme infrastructure setup — Phase 1 (add `htmx:afterSettle` handler) | Sort log table column in dark mode; verify icon and label are correct |
| SVG icon blurriness on HiDPI | Component styling phase | Visual review on a 2x display; all prominent icons are `w-6 h-6` |
| `backdrop-filter` Safari breakage | Glassmorphism component phase | Safari visual test; `grep "\-webkit-backdrop-filter" output.css` |
| CSS transition on page load | Theme infrastructure setup — Phase 1 | No color fade on hard refresh; no `transition-*` in base layer on `html`/`body` |
| Color contrast failures | Component styling phase + accessibility review | WCAG contrast checker on all `dark:text-*` on dark backgrounds |

---

## Sources

- [Tailwind CSS dark mode — official docs (v3)](https://tailwindcss.com/docs/dark-mode) — HIGH confidence
- [Tailwind CSS content configuration — official docs](https://tailwindcss.com/docs/content-configuration) — HIGH confidence
- [Tailwind dark mode classes purged in production — GitHub Discussion #4358](https://github.com/tailwindlabs/tailwindcss/discussions/4358) — HIGH confidence
- [HTMX `hx-preserve` attribute — official docs](https://htmx.org/attributes/hx-preserve/) — HIGH confidence
- [HTMX issue #412: classes removed during HTMX settle period](https://github.com/bigskysoftware/htmx/issues/412) — HIGH confidence
- [HTMX issue #2349: dark mode discussion on HTMX site](https://github.com/bigskysoftware/htmx/issues/2349) — MEDIUM confidence
- [caniuse: CSS backdrop-filter browser support](https://caniuse.com/css-backdrop-filter) — HIGH confidence
- [MDN browser-compat-data #25914: Safari 18 backdrop-filter with CSS variables broken](https://github.com/mdn/browser-compat-data/issues/25914) — HIGH confidence (confirmed open bug, 2025)
- [lightningcss #537: -webkit- prefix dropped from backdrop-filter](https://github.com/parcel-bundler/lightningcss/issues/537) — HIGH confidence
- [FOUC dark mode prevention — Victor Dibia (Gatsby/Tailwind)](https://victordibia.com/blog/gatsby-fouc/) — MEDIUM confidence (principle is framework-agnostic)
- [Disable CSS transitions on color scheme change — reemus.dev](https://reemus.dev/article/disable-css-transition-color-scheme-change) — MEDIUM confidence
- [SVG blurry on Retina — SVGGenie](https://www.svggenie.com/blog/svg-blurry-fixes) — MEDIUM confidence (aligns with browser rendering behavior)
- [Dark mode transition flash — tailwindlabs GitHub Discussion #3479](https://github.com/tailwindlabs/tailwindcss/discussions/3479) — HIGH confidence

---
*Pitfalls research for: Apple-like UI redesign + dark/light mode on Jinja2 + HTMX + Tailwind CSS*
*Researched: 2026-04-11*
