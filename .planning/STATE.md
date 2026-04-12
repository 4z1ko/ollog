# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-11)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v1.9 Admin & Login UI Redesign — Phase 33: Design Tokens and CSS Component System

## Current Position

Phase: 33 of 36 (Design Tokens and CSS Component System)
Plan: 1 of 1 in current phase (complete)
Status: In progress
Last activity: 2026-04-12 — Phase 33 Plan 01 complete: canvas/surface/shadow tokens, system font stack, badge rounded-md, Google Fonts removed

Progress: [█████████████████████░░░░░░░░░] ~68% (32/36 phases complete across all milestones)

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
- **HiDPI icon blurry:** Use `w-6 h-6` (24px, 1:1 with Heroicons viewBox) for all prominent nav and card header icons. `w-4 h-4` is acceptable for small secondary icons only.

### Key Architecture (v1.9)

- **Stack:** CSS-first, template-second. `tailwind.config.js` tokens → `input.css` component classes → `npm run build` → templates consume output.css.
- **No Python changes:** No routes, no models, no database changes. Pure frontend visual redesign.
- **Phase 35 dependency:** Login pages depend on Phase 33 (tokens) not Phase 34 (admin templates) — they can be worked in parallel with Phase 34 once Phase 33 is complete.
- **Build order:** Phase 32 (theme infra) → Phase 33 (tokens) → Phase 34 (admin) + Phase 35 (login, parallel) → Phase 36 (log views).

### Known Tech Debt (carried forward)

- `QSO.find_active()` in models.py — dead production code
- `from_mongo_dt()` in utils.py — tested, not called in production
- Docker end-to-end verification pending (requires live Docker environment)

### Decisions (Phase 33)

- **033-01:** canvas and surface tokens added in extend.colors alongside sidebar block — sidebar preserved unchanged
- **033-01:** boxShadow.card uses two-layer RGBA for Apple-caliber subtle elevation
- **033-01:** dark:shadow-none on .card and .table-wrap — shadow removed in dark mode to avoid halo artifact
- **033-01:** .card-title loses uppercase/tracking-wider, uses text-gray-700/200 for stronger contrast
- **033-01:** badge rounded-md chosen over rounded-full — matches Apple HIG status indicator convention
- **033-01:** Inter fully removed from config and input.css; system font stack leads with -apple-system, eliminating CDN font request

### Decisions (Phase 32)

- **032-01:** Use `document.body` (not `document`) for htmx:afterSettle listener — matches existing HTMX event patterns in codebase
- **032-01:** IIFE moved before stylesheet link tag to ensure synchronous execution before any paint
- **032-01:** rAF-rAF pattern chosen for transition suppression — inject style before dark class, remove after two animation frames so user toggles still animate

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-12
Stopped at: Completed 033-01-PLAN.md — design tokens, system fonts, badge shape, Google Fonts removed
Resume file: None
