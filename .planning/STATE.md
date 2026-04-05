# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** Phase 13 — OpenAPI Schema Cleanup

## Current Position

Phase: 13 of 15 (OpenAPI Schema Cleanup)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-04-04 — v1.3 roadmap created (phases 13–15)

Progress: [████████░░░░░░░░░░░░] ~40% (v1.0+v1.1+v1.2 complete; v1.3 starting)

## Performance Metrics

**Velocity:**
- Total plans completed: 23 (v1.0: 19, v1.1: 7 [corrected], v1.2: 2 [includes 11–12])
- Average duration: ~5–16 min/plan
- Total execution time: ~3–4 hours estimated

**By Phase:**

| Phase | Plans | Milestone |
|-------|-------|-----------|
| 1–6 | 19 | v1.0 |
| 7–10 | 7 | v1.1 |
| 11–12 | 2 | v1.2 |
| 13–15 | TBD | v1.3 |

**Recent Trend:** Stable

## Accumulated Context

### Key Decisions (summary — full log in PROJECT.md)

- v1.3: Serve MkDocs `site/` at `/guide` — preserves `/docs` as Swagger UI, no path shadow
- v1.3: `mkdocs-material==9.*` dev-only dependency — not in production Docker image
- v1.3: `site/` committed to repo; Dockerfile gains `COPY site/ site/` — no CI pipeline, no external hosting
- v1.3: Register `/guide` StaticFiles mount before `/static` in app/main.py — order is load-bearing
- v1.2: ISO code not stored in QSO records — render-time lookup, stored codes go stale with ITU reallocations
- v1.2: `_NOTFOUND` sentinel in range lookup distinguishes "no match" from "found, iso=None" (non-country entities)

### Known Tech Debt

- QSO.find_active() in models.py — dead production code
- from_mongo_dt() in utils.py — tested, not called in production
- Docker end-to-end verification pending

### Blockers/Concerns

- Phase 14: Verify CSS/JS assets load at `/guide` sub-path before writing content — needs live test (MEDIUM confidence)
- Phase 15: Troubleshooting items require reproduction against running app — write last

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-04
Stopped at: v1.3 roadmap created — phases 13, 14, 15 defined
Resume file: None
