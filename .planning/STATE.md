---
gsd_state_version: 1.0
milestone: v1.7
milestone_name: API Token Auth
status: executing
stopped_at: Phase 51 UI-SPEC approved
last_updated: "2026-04-24T18:59:04.379Z"
last_activity: 2026-04-24 -- Phase 51 execution started
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 3
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-24)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** Phase 51 — llms-txt-endpoints-and-content

## Current Position

Phase: 51 (llms-txt-endpoints-and-content) — EXECUTING
Plan: 1 of 3
Status: Executing Phase 51
Last activity: 2026-04-24 -- Phase 51 execution started

```
v2.6 Progress: [__________] 0% (0/1 phases)
Phase 51: llms.txt Endpoints and Content  [ ] Not started
```

## Performance Metrics

**Velocity (historical):**

- Total plans completed: 72 plans across v1.0–v2.5
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
| v2.1 | 39–40 | 2 |
| v2.2 | 41 | 2 |
| v2.3 | 42–43 | 2 |
| v2.4 | 44–47 | 5 |
| v2.5 | 48–50 | 3 |
| v2.6 | 51 | TBD |

## Accumulated Context

### Roadmap Evolution

- v2.5 milestone complete: QSO Sorting & Entry Timestamp (Phases 48–50)
- v2.6 milestone started: llms.txt Support (2026-04-24)
- v2.6 roadmap finalized 2026-04-24: 1 phase (51), 7 requirements mapped

### Key Decisions for v2.6

- Static files (`static/llms.txt`, `static/llms-full.txt`) — editable without touching Python
- Two FastAPI routes at `/llms.txt` and `/llms-full.txt` on operator app (port 8000) — not on admin app
- Both routes use `FileResponse` with `include_in_schema=False`
- `/llms.txt` = index (project title + description + section links)
- `/llms-full.txt` = full content (API reference + ADIF field guide + getting-started walkthrough)
- Content sourced from existing MkDocs markdown files in `docs/`

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

Last session: 2026-04-24T18:31:20.832Z
Stopped at: Phase 51 UI-SPEC approved
Next: `/gsd-plan-phase 51`
