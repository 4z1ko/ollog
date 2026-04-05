# Requirements: ollog

**Defined:** 2026-04-04
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss

## v1.3 Requirements

Requirements for the Documentation milestone. Each maps to roadmap phases.

### OpenAPI Schema

- [ ] **OAPI-01**: QSO endpoints return typed response models (not untyped `dict`) — Swagger shows full QSO schema at all 5 QSO endpoints
- [ ] **OAPI-02**: HTMX browser-only routes (`/log/*`, `/admin/ui/*`) are excluded from Swagger (`include_in_schema=False`)
- [ ] **OAPI-03**: 409 duplicate detection response is declared on `POST /api/qsos` with a `DuplicateQSOError` model and `force=true` query parameter documented
- [ ] **OAPI-04**: ADIF import response declares `ADIFImportReport` model; export endpoint declares `text/plain` content type via `openapi_extra`
- [ ] **OAPI-05**: ADIF request fields carry `Field(description=...)` with format notes: `QSO_DATE` (YYYYMMDD), `TIME_ON` (HHMM or HHMMSS), `BAND` (amateur designator e.g. "20m"), `MODE` (ADIF enum), OPERATOR vs STATION_CALLSIGN distinction
- [ ] **OAPI-06**: `DELETE /api/qsos/{qso_id}` description discloses soft-delete semantics (record marked deleted, not physically removed)

### MkDocs Infrastructure

- [ ] **MKDOCS-01**: `mkdocs-material==9.*` added as dev dependency in `pyproject.toml`; not in production dependencies
- [ ] **MKDOCS-02**: `mkdocs.yml` created at project root with Material theme, site name, and navigation structure
- [ ] **MKDOCS-03**: `docs/` directory created with scaffold Markdown files
- [ ] **MKDOCS-04**: `uv run mkdocs build --strict` produces `site/` directory without errors
- [ ] **MKDOCS-05**: `site/` committed to the repo
- [ ] **MKDOCS-06**: FastAPI mounts `site/` at `/guide` via `StaticFiles(html=True)` — mount registered before `/static`
- [ ] **MKDOCS-07**: Dockerfile gains `COPY site/ site/` so production image serves docs without MkDocs installed
- [ ] **MKDOCS-08**: CSS/JS assets load correctly when site is served at `/guide` sub-path (not root `/`)

### Narrative Documentation

- [ ] **DOCS-01**: Deployment guide covers Docker Compose prerequisites, `.env` setup (all env vars with description and required/optional), `docker compose up -d`, bootstrap admin account (one-time only behavior), and verification steps
- [ ] **DOCS-02**: Operator getting-started walkthrough covers: login → profile setup (OPERATOR vs STATION_CALLSIGN explained) → log first QSO via UI → log first QSO via REST API → ADIF import → ADIF export → view station feed
- [ ] **DOCS-03**: Admin guide covers: create operator, enable/disable operator, reset password, last-admin lockout guard explanation
- [ ] **DOCS-04**: Full API reference covers all 13 endpoints across 6 groups (auth, QSOs, ADIF, profile, admin, SSE) with: method + path, auth requirement, request schema summary, response schema summary, notable HTTP status codes, and one curl example per endpoint
- [ ] **DOCS-05**: Auth section explicitly documents both auth flows: Bearer token (REST API / scripts) and HTTP-only cookie (browser SSE — why EventSource cannot send Authorization headers)
- [ ] **DOCS-06**: ADIF field format reference documents key field formats and conventions: `QSO_DATE`, `TIME_ON`, `BAND`, `MODE`, `RST_SENT`/`RST_RCVD`, OPERATOR vs STATION_CALLSIGN, extra field extensibility (`extra="allow"`)
- [ ] **DOCS-07**: Troubleshooting section covers the three most common failure modes: SSE feed not updating, login fails after restart (replica set / SECRET_KEY), import returns all duplicates

## v2 Requirements

Deferred to future release.

### Documentation Extensions

- **DOCS-EXT-01**: Published `openapi.json` spec file for tool integration (FLdigi, WSJT-X, TQSL)
- **DOCS-EXT-02**: Documentation versioning tied to application version tags
- **DOCS-EXT-03**: FLdigi / WSJT-X integration examples

## Out of Scope

| Feature | Reason |
|---------|--------|
| mkdocstrings (Python autodoc) | ollog needs REST API user guide, not library reference; FastAPI's /docs already covers the schema layer |
| Sphinx | RST-based, wrong audience for self-hosted ham radio ops |
| External SaaS doc hosting (GitBook, Stoplight, etc.) | Self-hosted deployment; docs must work without internet |
| MkDocs social card generation (`mkdocs-material[imaging]`) | Requires system-level Pillow/Cairo dependencies; not worth it for this audience |
| Node.js tooling (Redocly CLI) | Adds Node.js to a pure-Python project for no gain |
| Troubleshooting content that requires app reproduction without a running instance | Flag as Phase 3 last items; skip if unable to reproduce cleanly |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| OAPI-01 | Phase 13 | Pending |
| OAPI-02 | Phase 13 | Pending |
| OAPI-03 | Phase 13 | Pending |
| OAPI-04 | Phase 13 | Pending |
| OAPI-05 | Phase 13 | Pending |
| OAPI-06 | Phase 13 | Pending |
| MKDOCS-01 | Phase 14 | Pending |
| MKDOCS-02 | Phase 14 | Pending |
| MKDOCS-03 | Phase 14 | Pending |
| MKDOCS-04 | Phase 14 | Pending |
| MKDOCS-05 | Phase 14 | Pending |
| MKDOCS-06 | Phase 14 | Pending |
| MKDOCS-07 | Phase 14 | Pending |
| MKDOCS-08 | Phase 14 | Pending |
| DOCS-01 | Phase 15 | Pending |
| DOCS-02 | Phase 15 | Pending |
| DOCS-03 | Phase 15 | Pending |
| DOCS-04 | Phase 15 | Pending |
| DOCS-05 | Phase 15 | Pending |
| DOCS-06 | Phase 15 | Pending |
| DOCS-07 | Phase 15 | Pending |

**Coverage:**
- v1.3 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-04 — traceability filled after roadmap creation*
