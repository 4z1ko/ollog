---
gsd_state_version: 1.0
milestone: v1.7
milestone_name: API Token Auth
status: planning
stopped_at: Phase 42 context gathered
last_updated: "2026-04-15T20:19:58.122Z"
last_activity: 2026-04-15 — v2.3 roadmap created (Phases 42–43)
progress:
  total_phases: 19
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v2.3 Operator Statistics — Phase 42 ready to plan

## Current Position

Phase: 42 (Stats Aggregation Backend)
Plan: —
Milestone: v2.3 Operator Statistics
Status: Roadmap complete — ready for Phase 42 planning
Last activity: 2026-04-15 — v2.3 roadmap created (Phases 42–43)

## Performance Metrics

**Velocity (historical):**

- Total plans completed: 51 plans across v1.0–v2.2
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
| v2.3 | 42–43 | TBD |

**Phase 41 metrics:** Plan 01 — 2 min, 2 tasks, 5 files modified; Plan 02 — 3 min, 2 tasks, 11 files modified — COMPLETE

## Accumulated Context

### Critical Build Rules (carried forward)

- **FOUC prevention:** The inline IIFE in `base.html` `<head>` is load-bearing. Never move it, add `defer`/`async`, or extract it to an external file.
- **Tailwind purge:** New `dark:` classes must appear as complete literal strings in scanned template files. Always run `npm run build` + grep verification for new classes before committing templates or `input.css`.
- **Safari backdrop-filter:** Declare `-webkit-backdrop-filter` explicitly in `@layer components` for glass card classes. Use fixed pixel values, not CSS variable references.
- **PostCSS autoprefixer:** Always configure `postcss.config.js` with `autoprefixer({ remove: false })` when writing explicit webkit prefixes in source CSS.
- **FastAPI sub-app StaticFiles:** Every FastAPI sub-app that serves HTML must have its own `StaticFiles` mount for `/static`. The main app mount does not propagate.
- **apscheduler<4 upper bound is load-bearing:** Do not touch `pyproject.toml` APScheduler constraints.

### v2.3 Architecture Decisions (pre-decided from research)

- **Chart.js delivery:** CDN UMD bundle `chart.umd.min.js@4.5.1` via jsDelivr — loaded only in `stats.html`, never in `base.html`. ESM-only build silently fails with "Chart is not defined".
- **MongoDB aggregation access:** `QSO.get_motor_collection().aggregate([...])` with `await cursor.to_list(length=None)` — Beanie does not expose `aggregate()` directly; `get_motor_collection()` is the established pattern (see `app/feed/manager.py`).
- **Pipeline guard:** `$match` with `{"_operator": callsign, "_deleted": False}` must be the FIRST stage in every aggregation pipeline — otherwise a full collection scan occurs across all operators.
- **DXCC rollup is Python-side:** `lookup_prefix()` is pure-Python bisect — cannot run inside MongoDB. Pattern: aggregate by CALL in MongoDB, then resolve DXCC in Python, then re-aggregate by entity.
- **"Other" bucket guard:** Only append "Other" slice when more than 8 DXCC entities exist. A zero-value "Other" must never appear.
- **unique_dxcc computed before truncation:** Count distinct entity ISO codes before taking the top-8 subset.
- **Inline JSON safety:** Use `| tojson` filter on every single inline data variable — never `| safe`, never bare substitution. Entity names contain commas and quotes; `| safe` is an XSS vector.
- **Canvas sizing:** Wrap each `<canvas>` in `<div class="relative h-64 w-full">` and set `maintainAspectRatio: false` in Chart.js options to prevent zero-width collapse in Tailwind flex/grid.
- **Stale canvas guard:** Call `Chart.getChart(canvas)?.destroy()` before every `new Chart(...)` call — required on bfcache restore and theme re-init.
- **Dark mode chart re-init:** Read `document.documentElement.classList.contains('dark')` at chart creation time to pick color palettes. On `toggleTheme()`, destroy and recreate all three charts.
- **`{% block extra_scripts %}`:** Add to `templates/base.html` immediately before `</body>`. Confirm exact closing-tag structure of `base.html` before editing to avoid double-`</body>`.
- **`toggleTheme()` location:** Confirm exact function name and location in `base_app.html` before wiring dark mode re-init wrapper.
- **No new Python dependencies:** All aggregation uses existing Motor collection access and existing `lookup_prefix()` + `pycountry`. `requirements.txt` does not change.
- **Files to change (complete list):** `app/qso/service.py`, `app/qso/ui_router.py`, `templates/log/stats.html` (new), `templates/base_app.html`, `templates/base.html`

### Known Tech Debt

- `QSO.find_active()` in models.py — dead production code
- `from_mongo_dt()` in utils.py — tested, not called in production
- Docker end-to-end verification pending (requires live Docker environment)

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-15T20:19:58.114Z
Stopped at: Phase 42 context gathered
Resume file: .planning/phases/42-stats-aggregation-backend/42-CONTEXT.md
Next: `/gsd-plan-phase 42` to plan Phase 42 (Stats Aggregation Backend)
