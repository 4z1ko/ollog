---
gsd_state_version: 1.0
milestone: v2.8
milestone_name: Clear Log
status: in_progress
stopped_at: ""
last_updated: "2026-05-06T00:00:00.000Z"
last_activity: 2026-05-06
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-06)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v2.8 Clear Log — defining requirements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-05-06 — Milestone v2.8 started

```
v2.8 Progress: [                    ] 0% (0/? phases)
```

## Performance Metrics

**Velocity (historical):**

- Total plans completed: 81 plans across v1.0–v2.6
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
| v2.6 | 51 | 3 |
| v2.7 | 52–53 | 3 |
| v2.8 | 54–? | TBD |

## Accumulated Context

### Roadmap Evolution

- v2.6 milestone complete: llms.txt Support (Phase 51, 2026-04-25)
- v2.7 milestone complete: UTC Date/Time Entry (Phases 52–53, 2026-05-02)
- v2.8 milestone started: Clear Log (2026-05-06)

### Key Decisions for v2.7

- All changes fit in two existing files: `templates/log/form.html` and `app/main.py`
- No new dependencies — browser-native JS + existing HTMX hooks + existing PyMongo migration pattern
- Phase 52 (backend only): idempotent `normalize_time_on()` startup migration in `app/main.py` pads HHMM → HHMM00 using anchored regex `^\d{4}$` to prevent double-padding
- Phase 53 (frontend only): all form enhancements in `templates/log/form.html`
- `readonly` (not `disabled`) on locked fields — `disabled` silently drops field value from POST body
- Live clock uses `Date.getUTC*()` exclusively — never `getHours()`/`getDate()`/etc. which return local timezone
- HHMM normalization fires in `htmx:beforeRequest` hook (already present in form.html)
- Post-submit behavior toggle reads/writes `localStorage`
- `hx-target="#qso-result"` points at a sibling div — form DOM, event listeners, and setInterval survive every submit; no re-initialization hook needed
- `parse_adif_datetime()` in service.py already handles both HHMM and HHMMSS — DB-02 is a server-side validation confirmation, not a code change

### Critical Build Rules (carried forward)

- **FOUC prevention:** The inline IIFE in `base.html` `<head>` is load-bearing. Never move it, add `defer`/`async`, or extract it to an external file.
- **Tailwind purge:** New `dark:` classes must appear as complete literal strings in scanned template files. Always run `npm run build` + grep verification for new classes before committing templates or `input.css`.
- **Safari backdrop-filter:** Declare `-webkit-backdrop-filter` explicitly in `@layer components` for glass card classes. Use fixed pixel values, not CSS variable references.
- **PostCSS autoprefixer:** Always configure `postcss.config.js` with `autoprefixer({ remove: false })` when writing explicit webkit prefixes in source CSS.
- **FastAPI sub-app StaticFiles:** Every FastAPI sub-app that serves HTML must have its own `StaticFiles` mount for `/static`. The main app mount does not propagate.
- **apscheduler<4 upper bound is load-bearing:** Do not touch `pyproject.toml` APScheduler constraints.

### v2.7 Critical Pitfalls (from research)

- `disabled` vs `readonly` — `disabled` silently drops `QSO_DATE`/`TIME_ON` from POST body; always use `.readOnly = true/false`
- Local timezone leakage — `getHours()`, `getDate()` return local time; every UTC access must use `getUTC*()`
- `form.reset()` clears auto-populated fields — must call `initDateTime()` immediately after reset to re-populate and re-apply `readonly`
- Migration double-padding — use anchored regex `^\d{4}$` and aggregation pipeline `[{$set: {TIME_ON: {$concat: ["$TIME_ON", "00"]}}}]`
- HTMX swap scope — never change `hx-target` to point at the form or any ancestor of `#qso-form`; destroys the form DOM and all attached timers

### Known Tech Debt

- `QSO.find_active()` in models.py — dead production code
- `from_mongo_dt()` in utils.py — tested, not called in production
- Docker end-to-end verification pending (requires live Docker environment)

### Pending Todos

None.

## Session Continuity

Last session: 2026-05-06
Stopped at: v2.8 milestone started — requirements and roadmap being defined
Next: `/gsd-plan-phase 54`
