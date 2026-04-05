# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** Phase 15 — Narrative Documentation Content

## Current Position

Phase: 15 of 15 (Narrative Documentation Content)
Plan: 2 of N in current phase
Status: Plan complete
Last activity: 2026-04-05 — 15-02 getting-started operator walkthrough

Progress: [████████████████░░░░] ~78% (v1.0+v1.1+v1.2 complete; v1.3 phases 13-15-P02 done)

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
| Phase 13-openapi-schema-cleanup P02 | 2 | 2 tasks | 2 files |
| Phase 14-mkdocs-infrastructure P01 | 8 | 2 tasks | 54 files |
| Phase 14-mkdocs-infrastructure P02 | 6 | 1 tasks | 2 files |
| Phase 15 P01 | 2 | 2 tasks | 2 files |
| Phase 15 P02 | 2 | 1 tasks | 1 files |

## Accumulated Context

### Key Decisions (summary — full log in PROJECT.md)

- v1.3: Serve MkDocs `site/` at `/guide` — preserves `/docs` as Swagger UI, no path shadow
- v1.3: `mkdocs-material==9.*` dev-only dependency — not in production Docker image
- v1.3: `site/` committed to repo; Dockerfile gains `COPY site/ site/` — no CI pipeline, no external hosting
- v1.3: Register `/guide` StaticFiles mount before `/static` in app/main.py — order is load-bearing
- v1.2: ISO code not stored in QSO records — render-time lookup, stored codes go stale with ITU reallocations
- v1.2: `_NOTFOUND` sentinel in range lookup distinguishes "no match" from "found, iso=None" (non-country entities)
- v1.3 (13-01): QSOResponse uses Field(alias='_operator'/'_deleted') because _qso_to_dict uses model_dump(by_alias=True) — alias required for response validation to populate those fields
- v1.3 (13-01): extra='ignore' on QSOResponse silently drops arbitrary ADIF model_extra fields to avoid 500 validation errors
- v1.3 (13-02): ADIFRecordError.call is Optional[str] — parse errors have no call key; per-record errors do
- v1.3 (13-02): Export endpoint annotated with responses= (not response_model=) — StreamingResponse cannot be Pydantic-validated
- v1.3 (13-02): Feed router excluded from OpenAPI schema — /feed/station uses cookie auth and cannot be exercised from Swagger UI
- v1.3 (14-01): site_url ends in /guide/ with trailing slash — prevents broken relative asset paths when served at sub-path
- v1.3 (14-01): site/ committed to repo (not gitignored) — Dockerfile can COPY site/ without installing MkDocs in production image
- v1.3 (14-02): /guide StaticFiles mount registered before /static with html=True — order is load-bearing; html=True enables automatic index.html serving at directory paths
- v1.3 (14-02): COPY site/ site/ in Dockerfile — pre-built docs in production image, no MkDocs install needed
- v1.3 (15-01): admin-guide.md reset-password uses {password} field (not new_password) — matched actual ResetPasswordRequest model in router.py
- v1.3 (15-02): getting-started.md uses my_gridsquare (not grid_square) — matched ProfileUpdateRequest field name in app/profile/schemas.py

### Known Tech Debt

- QSO.find_active() in models.py — dead production code
- from_mongo_dt() in utils.py — tested, not called in production
- Docker end-to-end verification pending

### Blockers/Concerns

- Phase 15: Troubleshooting items require reproduction against running app — write last

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-05
Stopped at: Completed 15-02-PLAN.md — getting-started operator walkthrough
Resume file: None
