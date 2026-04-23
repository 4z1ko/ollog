---
gsd_state_version: 1.0
milestone: v2.5
milestone_name: QSO Sorting & Entry Timestamp
status: milestone_complete
stopped_at: v2.5 archived 2026-04-23
last_updated: "2026-04-23T00:00:00.000Z"
last_activity: 2026-04-23
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 3
  completed_plans: 3
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-23)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** Planning next milestone (v2.5 shipped)

## Current Position

Phase: —
Plan: —
Status: v2.5 milestone complete — planning next milestone
Last activity: 2026-04-23

```
v2.5 Progress: [██████████] 100% (3/3 phases)
Phase 48: Model Foundation      [x] Complete (2026-04-22)
Phase 49: Service Layer         [x] Complete (2026-04-23)
Phase 50: Sort UI               [x] Complete (2026-04-23)
```

## Performance Metrics

**Velocity (historical):**

- Total plans completed: 69 plans across v1.0–v2.4
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
| v2.5 | 48–50 | TBD |

## Accumulated Context

### Roadmap Evolution

- v2.5 milestone started: QSO Sorting & Entry Timestamp
- v2.5 roadmap finalized 2026-04-20: 3 phases (48–50), 9 requirements mapped

### v2.5 Phase Summary

| Phase | Name | Requirements | Key Work |
|-------|------|--------------|----------|
| 48 | Model Foundation | TS-01, TS-02, TS-03 | `_created_at` field + `default_factory`, compound index, protected fields strip |
| 49 | Service Layer | SORT-03, SORT-04 | `_ALLOWED_SORT_FIELDS` allowlist, view dict enrichment, SSE sentinel extended |
| 50 | Sort UI | SORT-01, SORT-02, UX-01, UX-02 | MODE header, clock icon in DATE header, hollow/solid chevrons |

### Key Decisions for v2.5

- `_created_at` clock icon goes INSIDE the DATE column header — no new `<th>`/`<td>` column
- SSE auto-refresh sentinel extends to include `-_created_at` sort (Phase 49)
- FREQ and RST columns are NOT sortable — excluded from `_ALLOWED_SORT_FIELDS`
- No three-state sort cycle — existing Clear button handles reset to default
- `default_factory=lambda: datetime.now(timezone.utc)` on model (not in `build_qso_dict()`) ensures all 4 insert paths get the timestamp automatically
- Sort string uses MongoDB alias name (`_created_at`), not Python attribute name (`created_at`)

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

Last session: 2026-04-23T20:14:45.295Z
Stopped at: Phase 50 UI-SPEC approved
Next: `/gsd-plan-phase 48`
