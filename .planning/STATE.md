# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04 after v1.2 milestone start)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v1.2 Phase 11 — Prefix Resolver Module

## Current Position

Phase: 11 of 12 (Prefix Resolver Module)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-04-04 — v1.2 roadmap created (phases 11–12)

Progress: [██████████] 100% v1.0+v1.1 complete; v1.2 starting

## Performance Metrics

**v1.0 Velocity:**
- Total plans completed: 19
- Average duration: ~7.5 min/plan
- Total execution time: ~2.4 hours

**v1.1 Velocity:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 07-01 | 1/1 | ~4 min | ~4 min |
| 07-02 | 1/1 | ~3 min | ~3 min |
| 08-01 | 1/1 | ~3 min | ~3 min |
| 08-02 | 1/1 | ~8 min | ~8 min |
| 09-01 | 1/1 | ~16 min | ~16 min |
| 10-01 | 1/1 | ~2 min | ~2 min |
| 10-02 | 1/1 | ~1 min | ~1 min |

*v1.2 metrics will populate after first plan completion*

## Accumulated Context

### Key Decisions (summary — full log in PROJECT.md)

- Prefix data bundled as static Python list literal in `app/callsign/prefixes.py` — loaded once at import, zero I/O per call
- `pycountry>=26.2.16` added as new dependency for ITU-name-to-ISO mapping at data-build time (not at request time)
- Flag SVGs served via `<img>` tag only — inline SVG breaks HTMX partial swaps (confirmed htmx issue #2761)
- Static file path mismatch: `StaticFiles` mount serves project-root `static/`; SVGs are at `app/static/flags/` — fix via `git mv app/static/flags static/flags` at Phase 12 start
- ISO code NOT stored in QSO records — render-time lookup is correct; stored codes would go stale as ITU allocations change
- Longest-prefix-match required (not flat scan) — ITU has overlapping sub-ranges (3DA–3DM vs 3DN–3DZ)
- `/MM` and `/AM` treated as unresolvable operating suffixes — not resolved as MM=Scotland or AM=Spain

### Known Tech Debt

- QSO.find_active() in models.py — dead production code
- from_mongo_dt() in utils.py — tested, not called in production
- Docker end-to-end verification pending

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-04
Stopped at: v1.2 roadmap created — phases 11 and 12 defined, REQUIREMENTS.md traceability confirmed, ready to plan Phase 11
Resume file: None
