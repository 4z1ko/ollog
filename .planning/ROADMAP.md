# Roadmap: ollog — Ham Radio Online Logbook

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-04)
- ✅ **v1.1 Operator & Station Profiles** — Phases 7–10 (shipped 2026-04-04)
- ✅ **v1.2 Callsign Entity Lookup & Country Flags** — Phases 11–12 (shipped 2026-04-04)
- 🚧 **v1.3 Documentation** — Phases 13–15 (in progress)


## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–6) — SHIPPED 2026-04-04</summary>

- [x] Phase 1: Foundation (4/4 plans) — completed 2026-04-03
- [x] Phase 2: Admin & Accounts (2/2 plans) — completed 2026-04-03
- [x] Phase 3: QSO Entry & Log View (4/4 plans) — completed 2026-04-03
- [x] Phase 4: ADIF Import & Export (4/4 plans) — completed 2026-04-03
- [x] Phase 5: Multi-Operator & Live Feed (4/4 plans) — completed 2026-04-04
- [x] Phase 6: Navigation Fix (1/1 plan) — completed 2026-04-04

Full archive: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 Operator & Station Profiles (Phases 7–10) — SHIPPED 2026-04-04</summary>

- [x] Phase 7: Profile Data Model and Grid Utility (2/2 plans) — completed 2026-04-04
- [x] Phase 8: Profile Service, Schemas, and API Router (2/2 plans) — completed 2026-04-04
- [x] Phase 9: QSO Auto-Stamping (1/1 plan) — completed 2026-04-04
- [x] Phase 10: Profile UI (2/2 plans) — completed 2026-04-04

Full archive: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 Callsign Entity Lookup & Country Flags (Phases 11–12) — SHIPPED 2026-04-04</summary>

- [x] Phase 11: Prefix Resolver Module — completed 2026-04-04
- [x] Phase 12: Flag Display Integration — completed 2026-04-04

Full archive: `.planning/milestones/v1.2-ROADMAP.md`

</details>

### 🚧 v1.3 Documentation (In Progress)

**Milestone Goal:** Create comprehensive documentation for ollog — accurate OpenAPI schema at `/docs`, narrative operator/admin guides at `/guide`, and a full API reference with curl examples.

- [x] **Phase 13: OpenAPI Schema Cleanup** — Annotate all REST routes with typed response models, exclude HTMX-only routes, and document error responses and ADIF field formats — completed 2026-04-04
- [x] **Phase 14: MkDocs Infrastructure** — Install tooling, build pipeline, commit `site/`, mount at `/guide`, wire Dockerfile — completed 2026-04-04
- [ ] **Phase 15: Narrative Documentation Content** — Write all Markdown content: deployment guide, operator walkthrough, admin guide, API reference, ADIF field reference, troubleshooting

**Phase execution note:** Phases 13 and 14 touch different files (app/ routers vs docs/ and mkdocs.yml) and can run in parallel. Phase 15 must come after both — it requires accurate Swagger (Phase 13) and a working `/guide` endpoint (Phase 14).

---

### Phase 13: OpenAPI Schema Cleanup

**Goal**: The `/docs` and `/redoc` Swagger UI accurately describes every REST endpoint — typed response models, documented error responses, ADIF field format notes, and HTMX-only routes excluded from the schema.
**Depends on**: Nothing (code-only annotations, no new dependencies)
**Requirements**: OAPI-01, OAPI-02, OAPI-03, OAPI-04, OAPI-05, OAPI-06
**Success Criteria** (what must be TRUE):
  1. Every QSO endpoint in Swagger shows a fully typed response schema — no empty `{}` objects
  2. HTMX browser routes (`/log/*`, `/admin/ui/*`) are absent from Swagger UI and the raw `/openapi.json`
  3. `POST /api/qsos` in Swagger shows the 409 response with `DuplicateQSOError` schema and `force=true` query parameter with description
  4. ADIF import and export endpoints show typed responses: `ADIFImportReport` model for import, `text/plain` content type for export
  5. ADIF request fields carry description strings that explain format conventions (YYYYMMDD, HHMM/HHMMSS, band designators, OPERATOR vs STATION_CALLSIGN)
**Plans:** 2 plans
Plans:
- [ ] 13-01-PLAN.md — QSO endpoint response models, 409 error schema, field descriptions, soft-delete disclosure
- [ ] 13-02-PLAN.md — ADIF import/export annotations, exclude HTMX and feed routes from schema

---

### Phase 14: MkDocs Infrastructure

**Goal**: The MkDocs build pipeline is operational, `site/` is committed to the repo and copied into the Docker image, and the narrative docs site is reachable at `/guide` in both local dev and Docker Compose deployments.
**Depends on**: Nothing (touches different files than Phase 13 — can run in parallel)
**Requirements**: MKDOCS-01, MKDOCS-02, MKDOCS-03, MKDOCS-04, MKDOCS-05, MKDOCS-06, MKDOCS-07, MKDOCS-08
**Success Criteria** (what must be TRUE):
  1. `uv run mkdocs build --strict` completes without errors and produces a `site/` directory
  2. Navigating to `/guide` in a running app returns the MkDocs index page — CSS and JS assets load without 404s
  3. `mkdocs-material==9.*` appears in `pyproject.toml` under `[dependency-groups].dev` only (not production dependencies)
  4. The Dockerfile includes `COPY site/ site/` so the built docs are in the production Docker image without MkDocs installed
**Plans:** 2 plans
Plans:
- [ ] 14-01-PLAN.md — Install mkdocs-material, create mkdocs.yml and scaffold docs, build site/
- [ ] 14-02-PLAN.md — Mount site/ at /guide in FastAPI, update Dockerfile

---

### Phase 15: Narrative Documentation Content

**Goal**: A self-hosted deployment of ollog provides complete human-readable documentation at `/guide` covering deployment, operator workflow, admin account management, full API reference with curl examples, ADIF field format reference, and troubleshooting for the three most common failure modes.
**Depends on**: Phase 13 (Swagger must be accurate before narrative docs cross-reference it), Phase 14 (working `/guide` mount needed to verify rendering while writing)
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, DOCS-05, DOCS-06, DOCS-07
**Success Criteria** (what must be TRUE):
  1. An operator can follow the deployment guide to stand up ollog from scratch using only the `/guide` documentation — prerequisites, `.env` setup, `docker compose up -d`, bootstrap admin account, and verification all covered
  2. An operator new to ollog can complete the full getting-started walkthrough: login, profile setup (with OPERATOR vs STATION_CALLSIGN explained), first QSO via UI, first QSO via REST API, ADIF import, ADIF export, and viewing the station feed
  3. An admin can manage operator accounts using the admin guide — create, enable/disable, reset password, and understand the last-admin lockout guard
  4. A developer or scripter can use the API reference to call any of the 13 endpoints, including understanding both auth flows (Bearer token and HTTP-only cookie) and finding one curl example per endpoint
  5. An operator can look up key ADIF field formats (QSO_DATE, TIME_ON, BAND, MODE, OPERATOR vs STATION_CALLSIGN) and diagnose common failures (SSE not updating, login fails after restart, import returns all duplicates)
**Plans**: TBD

---

## Progress

**Execution Order:**
Phases 13 and 14 can run in parallel. Phase 15 runs after both complete: 13 || 14 -> 15

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 4/4 | ✓ Complete | 2026-04-03 |
| 2. Admin & Accounts | v1.0 | 2/2 | ✓ Complete | 2026-04-03 |
| 3. QSO Entry & Log View | v1.0 | 4/4 | ✓ Complete | 2026-04-03 |
| 4. ADIF Import & Export | v1.0 | 4/4 | ✓ Complete | 2026-04-03 |
| 5. Multi-Operator & Live Feed | v1.0 | 4/4 | ✓ Complete | 2026-04-04 |
| 6. Navigation Fix | v1.0 | 1/1 | ✓ Complete | 2026-04-04 |
| 7. Profile Data Model and Grid Utility | v1.1 | 2/2 | ✓ Complete | 2026-04-04 |
| 8. Profile Service, Schemas, and API Router | v1.1 | 2/2 | ✓ Complete | 2026-04-04 |
| 9. QSO Auto-Stamping | v1.1 | 1/1 | ✓ Complete | 2026-04-04 |
| 10. Profile UI | v1.1 | 2/2 | ✓ Complete | 2026-04-04 |
| 11. Prefix Resolver Module | v1.2 | 1/1 | ✓ Complete | 2026-04-04 |
| 12. Flag Display Integration | v1.2 | 1/1 | ✓ Complete | 2026-04-04 |
| 13. OpenAPI Schema Cleanup | v1.3 | 2/2 | ✓ Complete | 2026-04-04 |
| 14. MkDocs Infrastructure | v1.3 | 2/2 | ✓ Complete | 2026-04-04 |
| 15. Narrative Documentation Content | v1.3 | 0/TBD | Not started | - |
