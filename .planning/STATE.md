# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v1.9 Admin & Login UI Redesign — Phase 36: Log Views

## Current Position

Phase: 36 of 36 (Log Views)
Plan: 1 of TBD in current phase
Status: Ready to start
Last activity: 2026-04-11 — Phase 35 complete: .glass-card component class with -webkit-backdrop-filter, both login templates updated, postcss autoprefixer fix, Safari visual approval

Progress: [███████████████████████████░░░] ~92% (36/36 phases started — Phase 35 complete, Phase 36 next)

## Performance Metrics

**Velocity (historical):**
- Total plans completed: 31 plans across v1.0–v1.8
- Average duration: ~5–20 min/plan

**By Milestone:**

| Milestone | Phases | Plans |
|-----------|--------|-------|
| v1.0 | 1–6 | 19 |
| v1.1 | 7–10 | 7 |
| v1.2 | 11–12 | 2 |
| v1.3 | 13–15 | 8 |
| v1.4 | 16–18 | 4 |
| v1.5 | 19–22 | 4 |
| v1.6 | 23–24 | 2 |
| v1.7 | 25–28 | 4 |
| v1.8 | 29–31 | 3 (all complete) |
| v1.9 | 32–36 | TBD |

## Accumulated Context

### v1.9 Critical Build Rules (Pitfall Prevention)

- **FOUC prevention:** The inline IIFE in `base.html` `<head>` is load-bearing. Never move it, add `defer`/`async`, or extract it to an external file. Add a load-bearing comment before Phase 32 ships.
- **Tailwind purge:** New `dark:` classes must appear as complete literal strings in scanned template files. Always run `npm run build` + grep verification for new classes before committing templates or `input.css`.
- **Transition flash:** Never add `transition-*` to `<body>`, `<html>`, or `*` in `@layer base`. Use the `no-transition` class suppression pattern in the IIFE for user-initiated toggles only.
- **HTMX icon desync:** The `htmx:afterSettle` handler must be wired in `base_app.html` in Phase 32, before any new Apple components are built.
- **Safari backdrop-filter:** Declare `-webkit-backdrop-filter` explicitly in `@layer components` for glass card classes. Use fixed pixel values (e.g. `blur(12px)`), not CSS variable references.
- **PostCSS autoprefixer:** Default autoprefixer silently strips manually-added `-webkit-` prefixes it considers unnecessary. Always configure `postcss.config.js` with `autoprefixer({ remove: false })` when writing explicit webkit prefixes in source CSS. After any build, grep output.css to confirm the prefix survived.
- **HiDPI icon blurry:** Use `w-6 h-6` (24px, 1:1 with Heroicons viewBox) for all prominent nav and card header icons. `w-4 h-4` is acceptable for small secondary icons only.
- **FastAPI sub-app StaticFiles:** Every FastAPI sub-app that serves HTML must have its own `StaticFiles` mount for `/static`. The main app mount does not propagate. Always verify before CSS-dependent visual verification steps.

### Key Architecture (v1.9)

- **Stack:** CSS-first, template-second. `tailwind.config.js` tokens → `input.css` component classes → `npm run build` → templates consume output.css.
- **No Python changes:** No routes, no models, no database changes. Pure frontend visual redesign.
- **Phase 35 dependency:** Login pages depend on Phase 33 (tokens) not Phase 34 (admin templates) — they can be worked in parallel with Phase 34 once Phase 33 is complete.
- **Build order:** Phase 32 (theme infra) → Phase 33 (tokens) → Phase 34 (admin) + Phase 35 (login, parallel) → Phase 36 (log views).

### Known Tech Debt (carried forward)

- `QSO.find_active()` in models.py — dead production code
- `from_mongo_dt()` in utils.py — tested, not called in production
- Docker end-to-end verification pending (requires live Docker environment)

### Decisions (Phase 35)

- **035-01:** `.glass-card` uses raw `-webkit-backdrop-filter: blur(12px)` not `@apply backdrop-blur-md` — Tailwind backdrop-blur utilities emit CSS variable references which fail in Safari pre-18.0 and 18.x
- **035-01:** `postcss.config.js` created with `autoprefixer({ remove: false })` — default autoprefixer silently strips manually-added `-webkit-backdrop-filter` during build; `remove: false` preserves it
- **035-01:** `bg-white/10` used instead of `bg-white/5` — 10% white opacity improves legibility over dark violet/indigo gradients

### Decisions (Phase 34)

- **034-01:** sidebar_class block placed inside class attribute of `<aside>` — minimal-invasive extension point; empty default block adds no whitespace artifact for operators
- **034-01:** `dark:bg-surface-dark` placed as literal string in users.html (not Jinja expression) — required for Tailwind purge scanner to include utility in output.css
- **034-01:** shield icon in sidebar_user avatar badge left at w-4 h-4 — badge icon sizing is correct; only nav-link SVGs promoted to w-6 h-6
- **034-01:** aria-hidden=true on all three new action button SVGs; button aria-label carries accessible name — icons are decorative
- **034-02:** output.css not committed — build artifact; human visual approval recorded as verification
- **034-02:** StaticFiles mount added to admin_main.py (blocking bug fix) — sub-app was 404-ing on /static/css/output.css at port 8001

### Decisions (Phase 33)

- **033-01:** canvas and surface tokens added in extend.colors alongside sidebar block — sidebar preserved unchanged
- **033-01:** boxShadow.card uses two-layer RGBA for Apple-caliber subtle elevation
- **033-01:** dark:shadow-none on .card and .table-wrap — shadow removed in dark mode to avoid halo artifact
- **033-01:** .card-title loses uppercase/tracking-wider, uses text-gray-700/200 for stronger contrast
- **033-01:** badge rounded-md chosen over rounded-full — matches Apple HIG status indicator convention
- **033-01:** Inter fully removed from config and input.css; system font stack leads with -apple-system, eliminating CDN font request
- **033-02:** bg-canvas-light/dark placed as literal strings in base_app.html (not Jinja expressions) — prevents Tailwind purge (Pitfall 1)
- **033-02:** Sidebar logo SVG kept at w-5 h-5; only nav-item anchor SVGs and theme toggle SVGs promoted to w-6 h-6
- **033-02:** All 10 grep token checks required to pass before committing output.css — no partial verification accepted

### Decisions (Phase 32)

- **032-01:** Use `document.body` (not `document`) for htmx:afterSettle listener — matches existing HTMX event patterns in codebase
- **032-01:** IIFE moved before stylesheet link tag to ensure synchronous execution before any paint
- **032-01:** rAF-rAF pattern chosen for transition suppression — inject style before dark class, remove after two animation frames so user toggles still animate

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-11
Stopped at: Completed 035-01-PLAN.md — Phase 35 fully complete; .glass-card component class, postcss autoprefixer fix, Safari/Chrome/Firefox visual approval on both login pages
Resume file: None
