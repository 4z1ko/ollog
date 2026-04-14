# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-14)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v2.1 Database Restore — Phase 40: Restore UI

## Current Position

Phase: 40 of 40 (Restore UI)
Plan: 1 of 1 — at checkpoint:human-verify
Milestone: v2.1 Database Restore — in progress
Status: Phase 40 Plan 01 tasks complete — awaiting human verification checkpoint
Last activity: 2026-04-14 — Phase 40 Plan 01 executed: restore UI shell built, awaiting visual verification

Progress: [x] Phase 37 [x] Phase 38 [x] Phase 39 [~] Phase 40 (checkpoint)

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
**Phase 39 metrics:** 3 min, 2 tasks, 7 files modified
**Phase 40 metrics (partial):** 4 min, 2 tasks, 6 files modified (checkpoint pending)

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

### Phase 40 Decisions (restore UI)

- **#restore-modal sibling placement**: `#restore-modal` must be a sibling of `#restore-result`, not nested in form — required by HTMX outerHTML swap for Cancel button
- **GET /restore dual-render**: Returns `<div id="restore-modal"></div>` on hx_request header — clears modal without page reload
- **backdrop-filter raw CSS**: `.modal-backdrop` uses raw `-webkit-backdrop-filter: blur(4px)` (not @apply) — consistent with glass-card Safari fix pattern

### Phase 39 Decisions (restore backend)

- **bson.json_util.loads** must be used for restore deserialization (not json.loads) — preserves ObjectId, datetime, and all BSON types with correct types
- **Auto-backup before drop** (OPS-01): run_backup is called before any db.drop() in restore_confirm; failure response includes auto-backup filename
- **HTMX error fragments return HTTP 200** — HTMX 2.x ignores response body on 4xx, which silently drops error HTML
- **Path traversal guard**: resolve(temp_path).startswith(gettempdir()), .gz suffix, and .exists() checks — all three required before file access

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-14
Stopped at: 040-01-PLAN.md checkpoint:human-verify — 2/2 auto tasks done, awaiting visual verification of restore page
Resume file: None
