# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-14)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v2.1 Database Restore — Phase 39: Restore Backend

## Current Position

Phase: 39 of 40 (Restore Backend)
Plan: —
Milestone: v2.1 Database Restore — in progress
Status: Ready to plan
Last activity: 2026-04-14 — v2.1 roadmap created; Phase 39 next

Progress: [x] Phase 37 [x] Phase 38 [ ] Phase 39 [ ] Phase 40

## Performance Metrics

**Velocity (historical):**
- Total plans completed: 49 plans across v1.0–v2.0
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
| v1.8 | 29–31 | 3 |
| v1.9 | 32–36 | 5 |
| v2.0 | 37–38 | 2 |

**Phase 37 metrics:** 4 min, 2 tasks, 3 files modified
**Phase 38 metrics:** 35 min, 2 tasks, 3 files modified

## Accumulated Context

### Critical Build Rules (carried forward)

- **FOUC prevention:** The inline IIFE in `base.html` `<head>` is load-bearing. Never move it, add `defer`/`async`, or extract it to an external file.
- **Tailwind purge:** New `dark:` classes must appear as complete literal strings in scanned template files. Always run `npm run build` + grep verification for new classes before committing templates or `input.css`.
- **Safari backdrop-filter:** Declare `-webkit-backdrop-filter` explicitly in `@layer components` for glass card classes. Use fixed pixel values, not CSS variable references.
- **PostCSS autoprefixer:** Always configure `postcss.config.js` with `autoprefixer({ remove: false })` when writing explicit webkit prefixes in source CSS.
- **FastAPI sub-app StaticFiles:** Every FastAPI sub-app that serves HTML must have its own `StaticFiles` mount for `/static`. The main app mount does not propagate.
- **apscheduler<4 upper bound is load-bearing:** Do not touch `pyproject.toml` APScheduler constraints.

### Known Tech Debt

- `QSO.find_active()` in models.py — dead production code
- `from_mongo_dt()` in utils.py — tested, not called in production
- Docker end-to-end verification pending (requires live Docker environment)

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-14
Stopped at: v2.1 roadmap created — ROADMAP.md, STATE.md, REQUIREMENTS.md updated; Phase 39 ready to plan
Resume file: None
