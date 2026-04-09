# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-08)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v1.6 Live Log Table — Phase 24: Session Robustness

## Current Position

Phase: 24 — Session Robustness
Plan: 01
Status: Complete
Last activity: 2026-04-08 — 24-01 complete, JWT session lifetime raised to 480 minutes

Progress: [██░░░░░░░░░░░░░░░░░░] 20% (v1.6 in progress — Phase 24 Plan 01 complete)

## Performance Metrics

**Velocity (historical):**
- Total plans completed: 44 (v1.0: 19, v1.1: 7, v1.2: 2, v1.3: 8, v1.4: 4, v1.5: 4)
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
| v1.6 (in progress) | 23–24 | 2 |

## Accumulated Context

### Key Decisions

Full decision log in PROJECT.md Key Decisions table.

### Key Architectural Insight (v1.6)

`#log-table` in `log.html` is the HTMX swap *target* — filter, sort, and pagination actions replace its innerHTML but never the container div itself. SSE attributes placed on `#log-table` survive every navigation. This is why `hx-ext="sse"` belongs on `#log-table`, not inside `log_table.html`. The guard condition (`#auto-refresh-ok` hidden marker rendered server-side only at page-1/no-filters/default-sort) prevents disruptive refreshes during browsing.

### Key Decisions (v1.6 Phase 23)

- Use `htmx:sseMessage` JS listener instead of `hx-trigger="sse:new_qso [condition]"` — JS filter evaluation in htmx SSE triggers had only medium confidence from research; the listener approach is fully reliable
- Place `hx-ext="sse"` and `sse-connect` on `#log-table` container (not inside the partial) — attributes survive every htmx innerHTML swap
- Server-side truth via hidden span: server renders `#auto-refresh-ok` only at page 1 + default sort + no filters; client only needs `getElementById` to check

### Key Decisions (v1.6 Phase 24)

- Raised `jwt_expire_minutes` default from 60 to 480 — covers full 8-hour FT8 session without operator action

### Known Tech Debt

- `QSO.find_active()` in models.py — dead production code
- `from_mongo_dt()` in utils.py — tested, not called in production
- Docker end-to-end verification pending (requires live Docker environment)

### Blockers/Concerns

None.

### Pending Todos

- Begin execution with `/gsd:plan-phase 23`

## Session Continuity

Last session: 2026-04-08
Stopped at: Phase 24 Plan 01 complete — JWT session lifetime raised to 480 minutes
Resume file: None
