# Project Research Summary

**Project:** ollog — documentation milestone (v1.3)
**Domain:** REST API documentation + operator/admin narrative docs for a self-hosted FastAPI + HTMX + MongoDB ham radio logbook
**Researched:** 2026-04-04
**Confidence:** HIGH

---

## Executive Summary

The ollog documentation milestone divides cleanly into two non-overlapping problems: (1) enriching the auto-generated OpenAPI schema that FastAPI already produces, and (2) writing and serving human-authored narrative documentation for operators and admins. These require different tooling and different phases of work. The API schema work is pure code annotation — no new packages, no new infrastructure — and must come first because the narrative docs will cross-reference Swagger UI. The narrative docs require one new dev dependency (`mkdocs-material==9.*`) and a StaticFiles mount that serves the built site at `/guide`, preserving `/docs` as Swagger UI.

The recommended architecture is a single-process model: FastAPI serves both the OpenAPI reference (at `/docs`) and the built MkDocs site (at `/guide`) from the same Docker Compose service. There is no separate docs container, no CI deploy, no external hosting required. The MkDocs `site/` output is committed to the repo and copied into the Docker image via one new `COPY site/ site/` line in the Dockerfile. This keeps operational complexity at zero while giving self-hosted deployments access to narrative docs without internet access.

The primary risk is trust destruction from an incorrect or incomplete OpenAPI schema. The existing codebase has six confirmed schema gaps: QSO endpoints return untyped `dict` (OpenAPI shows `{}`), ADIF import/export responses are undocumented, the 409 duplicate response has no schema, the health endpoint has no 503 documented, soft-delete is not disclosed, and HTMX cookie-auth routes appear alongside REST endpoints without distinction. All six must be resolved before narrative docs are written — narrative docs that say "see /docs for the response schema" are false advertising if Swagger shows empty objects.

---

## Key Findings

### Recommended Stack

The existing stack requires exactly one new dev dependency: `mkdocs-material==9.*` (currently 9.7.6, released March 19, 2026). This single install transitively pulls MkDocs 1.6.1, pymdown-extensions 10.21.2, and Pygments — no further packages needed. All other documentation work (OpenAPI enrichment, route annotations, tag descriptions) uses FastAPI's built-in annotation surface with no new packages at all.

MkDocs Material is the correct choice for this project: FastAPI itself uses it, it is Markdown-native, `mkdocs build` produces standalone static HTML that can be mounted via `StaticFiles`, and it is a dev-only dependency that does not bloat the production Docker image.

**Core technologies:**
- `mkdocs-material==9.*`: Static site generator for narrative docs — dev dependency only, pin to `9.*` per official recommendation to prevent unreviewed major-version upgrades
- FastAPI built-in OpenAPI: API reference via `/docs` (Swagger UI) and `/redoc` — zero new packages, enriched by annotating existing code with `response_model=`, `responses={}`, `openapi_tags`, `Field(description=...)`
- `StaticFiles(directory="site", html=True)`: Serves built MkDocs output at `/guide` within the existing FastAPI process — no new container, no new service

**What NOT to add:** `mkdocstrings` (library tool, not REST API user guide tool), Sphinx (RST-based, wrong audience), Redocly CLI (adds Node.js to a pure-Python project), `mkdocs-material[imaging]` extras (requires system dependencies for social card generation), any SaaS doc hosting.

### Expected Features

This milestone produces documentation, not application features. The content scope is well-defined and derived directly from codebase inspection.

**Must have (table stakes) — all P1:**
- REST API endpoint reference: all 13 routes across 6 groups (auth, QSOs, ADIF, profile, admin, SSE feed), each with method + path, auth requirement, request schema, response schema, HTTP status codes, and one curl example
- Auth flow documentation: Bearer token path (POST `/auth/token`, `Authorization: Bearer`) and cookie path (browser SSE, why EventSource cannot send custom headers) documented separately and clearly
- Deployment guide: Docker Compose prerequisites, `.env` setup, `docker compose up -d`, bootstrap admin account explanation, verification steps
- Environment variable reference: `SECRET_KEY` (required, must change), `MONGODB_URI`, `MONGODB_DB`, `JWT_EXPIRE_MINUTES`, `ADMIN_USERNAME/PASSWORD/CALLSIGN` (one-time bootstrap only, not re-read after first startup)
- Operator getting-started walkthrough: login → profile setup → first QSO via UI → first QSO via API → ADIF import → ADIF export → station feed
- Admin account management guide: create/enable/disable/reset password, last-admin lockout guard explanation
- Duplicate detection behavior: ±2 minute window, 409 response structure, `force=true` override
- ADIF import report schema: `total_records`, `accepted`, `duplicates`, `errors` — shape of each field
- Replica set requirement: why `--replSet rs0` is in docker-compose.yml, what fails if it is absent

**Should have (differentiators) — P2:**
- Profile auto-stamp behavior (OPERATOR, STATION_CALLSIGN, MY_GRIDSQUARE injected from profile on QSO creation — operators may think the API is broken if this is undocumented)
- Soft-delete semantics for `DELETE /api/qsos/{qso_id}`
- Extra ADIF field extensibility (`extra="allow"` — any valid ADIF field accepted beyond the declared set)
- Troubleshooting section (SSE feed not updating, login fails after restart, import returns all duplicates)

**Defer to v2+:**
- FLdigi / WSJT-X integration examples
- Published `openapi.json` spec file for tool integration
- Documentation versioning tied to application version tags
- Multi-language documentation

### Architecture Approach

Documentation is served by the existing single FastAPI process via two mechanisms: the built-in OpenAPI endpoint at `/docs` (augmented via `FastAPI()` constructor metadata and route annotations) and a StaticFiles mount at `/guide` serving the MkDocs-built `site/` directory. No separate container, no external hosting, no CI pipeline required. The `site/` directory is built locally with `uv run mkdocs build --strict` and committed to the repo. The Dockerfile gains one line: `COPY site/ site/`. Mount order in `app/main.py` is critical — `/guide` must be registered before `/static`.

**Major components:**
1. OpenAPI metadata (`app/main.py` `FastAPI()` constructor) — `description` and `openapi_tags` with per-group Markdown descriptions; enriches `/docs` and `/redoc` with zero logic changes
2. Route annotations (across all `router.py` files) — `summary=`, `response_model=`, `responses={409: ...}`, `Field(description=...)` on ADIF fields, `include_in_schema=False` on HTMX routes; all additive, zero runtime behavior change
3. MkDocs source (`docs/` directory + `mkdocs.yml`) — Markdown source for operator guide, admin guide, API tutorials, ADIF field reference, deployment guide
4. Built site (`site/` directory) — MkDocs output committed to repo, served at `/guide` via StaticFiles mount with `html=True`
5. Dockerfile addition — `COPY site/ site/` ensures the built docs artifact is in the production image

### Critical Pitfalls

All six critical pitfalls are confirmed from direct codebase inspection (HIGH confidence). Every one must be resolved in the OpenAPI schema cleanup phase before narrative docs are written.

1. **QSO endpoints return untyped `dict` — Swagger shows `{}`** — Add `response_model` Pydantic classes with `model_config = ConfigDict(extra="allow")` or use `openapi_extra` to inject hand-authored response schemas. The runtime `_qso_to_dict()` serialization does not need to change.

2. **Cookie-auth HTMX routes appear alongside REST endpoints in Swagger** — Apply `include_in_schema=False` to all `/log/*` and `/admin/ui/*` routes. Document both auth flows explicitly in narrative docs: Bearer token for REST/scripts, cookie for browser SSE.

3. **ADIF import/export response schemas missing** — Create `ADIFImportReport` Pydantic response model for `POST /api/adif/import`; use `openapi_extra` to declare `text/plain` content type for `GET /api/adif/export` (which returns a StreamingResponse and cannot be typed via `response_model`).

4. **409 duplicate detection undocumented** — Add `responses={409: {"model": DuplicateQSOError}}` to `create_qso`; add `Query(description=...)` to the `force` parameter explaining when to use it.

5. **ADIF field names and formats unexplained** — Add `Field(description=...)` to every ADIF field in request models. Critical formats: `QSO_DATE` is YYYYMMDD (not ISO 8601), `TIME_ON` is HHMM or HHMMSS, `BAND` uses amateur radio band designators (`"20m"`, `"40m"`, not frequencies), ADIF field names are uppercase by ADIF convention.

6. **Soft-delete not disclosed in DELETE endpoint** — Add "soft-delete — record is marked deleted in the database but not physically removed" to the `DELETE /api/qsos/{qso_id}` endpoint description. Affects duplicate detection behavior (soft-deleted QSOs are excluded from `find_duplicate`).

Additionally: mount narrative docs at `/guide`, not `/docs`. Shadowing FastAPI's conventional Swagger UI path causes silent confusion for API consumers — they hit the MkDocs index page instead of Swagger with no error message.

---

## Implications for Roadmap

The milestone decomposes into three sequential phases. Phases 1 and 2 can be worked in parallel (they touch different files with no overlap); Phase 3 must come after both.

### Phase 1: OpenAPI Schema Cleanup

**Rationale:** All six critical pitfalls live in the OpenAPI schema layer. Fixing them requires only code annotations — no new packages, no infrastructure. This work must precede narrative documentation because the operator guide, API reference, and auth sections will cross-reference `/docs`. If Swagger shows `{}` for QSO responses when narrative docs say "see the schema in /docs," the docs actively mislead readers.

**Delivers:** A complete, accurate, self-consistent OpenAPI schema at `/docs` and `/redoc`. Every endpoint has a non-empty response schema. ADIF fields have `description` strings and format notes. 409 and 503 error responses are declared. Cookie-auth routes are excluded from the schema. The app-level description and tag descriptions give Swagger users orientation without opening any other documentation.

**Addresses:** REST API endpoint reference (table stakes), auth flow documentation (table stakes), HTTP status codes and error payloads (table stakes), duplicate detection behavior (P1), soft-delete disclosure (P2)

**Avoids:** All six critical pitfalls from PITFALLS.md

**No deeper research needed.** All annotation APIs (`response_model=`, `responses={}`, `openapi_extra`, `Field(description=...)`, `include_in_schema=False`, `openapi_tags`) are in FastAPI official documentation.

### Phase 2: MkDocs Infrastructure and Deployment Guide

**Rationale:** Before narrative content can be written, the serving infrastructure must be verified end-to-end. This phase is deliberately narrow — install tooling, wire the StaticFiles mount, confirm `/guide` works in both `uvicorn` and `docker compose` contexts. The deployment guide is included here because it has no dependency on a stable UI and is entirely factual content (env vars, Docker commands, bootstrap steps) that can be written once the infrastructure validates.

**Delivers:** Working MkDocs pipeline (`uv run mkdocs serve` for local preview, `uv run mkdocs build --strict` for production build), `site/` committed to repo, `/guide` StaticFiles mount registered in `app/main.py` before `/static`, `COPY site/ site/` in Dockerfile, `mkdocs-material==9.*` in `[dependency-groups].dev` in `pyproject.toml`, and a complete deployment guide.

**Uses:** `mkdocs-material==9.*`, StaticFiles mount pattern (FastAPI official docs), `html=True` for directory index serving

**Implements:** Architecture components 3, 4, and 5 (MkDocs source, built site, Dockerfile addition)

**Avoids:** Over-engineering pitfall — infrastructure is one dev dependency and one mount line; `mkdocs-material` as a runtime dependency (add to dev group only); mount order pitfall (register `/guide` before `/static`)

**No deeper research needed.** StaticFiles mount pattern is in FastAPI official docs. MkDocs build/serve workflow is in MkDocs Material official docs.

**Watch for:** MkDocs generates relative asset paths by default. Verify that CSS and JS assets load correctly when the site is mounted at `/guide` (not `/`). If assets 404, set `use_directory_urls: true` (the default) and verify StaticFiles `html=True` is in place. The ARCHITECTURE.md notes this as a MEDIUM-confidence community finding — confirm with a live test before writing content.

### Phase 3: Narrative Documentation Content

**Rationale:** Content must come last, after OpenAPI is correct (Phase 1 — so narrative can reference accurate schema) and the MkDocs infrastructure works (Phase 2 — so authors can verify rendering as they write). PITFALLS.md explicitly warns against writing workflow docs before the UI is in a stable committed state (Pitfall 8). Writing narrative content in Phase 3 eliminates this risk entirely.

**Delivers:** Complete operator getting-started walkthrough, admin account management guide, full API reference in Markdown (supplementing Swagger with auth flow explanation, curl examples, ADIF field format reference), auth section explaining both flows in plain language (not developer-centric JWT/OAuth2 terminology for operator-facing sections), and troubleshooting entries for the three most common failure modes.

**Addresses:** All P1 features (operator walkthrough, admin guide, auth flows, ADIF import/export instructions, duplicate detection, replica set explanation); P2 features (profile auto-stamp, soft-delete, extra ADIF fields, troubleshooting)

**Avoids:** JWT dual-auth under-documentation (Pitfall 4), ADIF field format opacity (Pitfall 5), workflow docs written before UI is stable (Pitfall 8), developer-centric language in operator sections (UX pitfall), documenting admin credentials as example values (security pitfall), using obviously fake tokens in examples

**Content order within Phase 3:** Write deployment guide first (no UI dependency), then API reference (references Phase 1 schema — already done), then operator walkthrough and admin guide last (must be written against a stable UI — do a final pass confirming each documented step against the live app before committing).

**No deeper research needed.** Content quality depends on domain knowledge (ham radio ADIF conventions, deployment patterns) which is fully documented in FEATURES.md and PITFALLS.md.

### Phase Ordering Rationale

- Phase 1 must precede Phase 3: narrative auth documentation, API usage tutorials, and the ADIF field reference all say "see /docs" — that requires Swagger to be accurate first.
- Phase 2 must precede Phase 3: content authors need a working `/guide` endpoint to verify cross-links and rendering as they write.
- Phases 1 and 2 can run in parallel: Phase 1 touches `app/` router files; Phase 2 touches `docs/`, `mkdocs.yml`, `site/`, and the Dockerfile. No file overlap, no sequencing constraint between them.
- Within Phase 3, write deployment guide and API reference before operator/admin workflow docs to avoid the workflow-before-stable-UI pitfall.

### Research Flags

Phases with standard, well-documented patterns (skip `/gsd:research-phase`):
- **Phase 1 (OpenAPI Schema Cleanup):** All annotation APIs are in FastAPI official docs and confirmed against codebase. No unknowns remain.
- **Phase 2 (MkDocs Infrastructure):** StaticFiles mount pattern is in FastAPI official docs. MkDocs build/serve workflow is in MkDocs Material official docs. One thing to verify live: asset paths at the `/guide` sub-path mount point.
- **Phase 3 (Narrative Content):** Content writing does not require technical research. ADIF field formats, ham radio conventions, and deployment patterns are fully specified in FEATURES.md and PITFALLS.md.

No phase requires `/gsd:research-phase`. All necessary technical patterns are resolved by existing research.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | `mkdocs-material` version verified on PyPI (9.7.6, March 19, 2026). FastAPI annotation APIs verified against official docs. One new dev dependency is a minimal-risk change. |
| Features | HIGH | Derived from direct codebase inspection of all router files and `app/config.py`. Content scope is factual, not speculative. |
| Architecture | HIGH | Based on direct codebase inspection (`app/main.py`, Dockerfile, `pyproject.toml`) + FastAPI official StaticFiles documentation. Mount order behavior confirmed from FastAPI docs. `/guide` vs `/docs` conflict resolution is clearly specified. |
| Pitfalls | HIGH | All six critical pitfalls confirmed by reading the actual source files (`app/qso/router.py`, `app/adif/router.py`, `app/auth/dependencies.py`, `app/main.py`). Not inferred — directly observed in the code. |

**Overall confidence:** HIGH

### Gaps to Address

- **Asset paths at `/guide` sub-path:** MkDocs generates relative asset links. StaticFiles with `html=True` handles directory indexes, but verify CSS/JS assets load correctly when mounted at `/guide` (not at root `/`). If assets 404, the fix is straightforward (confirm `use_directory_urls: true` default is set, or use a path prefix plugin). Validate with a live test as the first step of Phase 2 before writing any content.

- **Complete list of HTMX routes to exclude from schema:** ARCHITECTURE.md and PITFALLS.md agree that `/log/*` and `/admin/ui/*` routes should be marked `include_in_schema=False`. During Phase 1, enumerate all route files containing `tags=["log-ui"]` or `tags=["admin-ui"]` to ensure complete exclusion. No routes should appear in Swagger that cannot be called via Bearer token.

- **Troubleshooting content requires live testing:** The three troubleshooting topics (SSE feed not updating, login fails after restart, import returns all duplicates) need to be reproduced against the running app to document accurately. They cannot be written from code inspection alone. Flag these as the last items in Phase 3.

---

## Sources

### Primary (HIGH confidence)

- ollog codebase (direct inspection, 2026-04-04): `app/main.py`, `app/qso/router.py`, `app/adif/router.py`, `app/auth/dependencies.py`, `app/auth/router.py`, `app/admin/router.py`, `app/profile/router.py`, `app/feed/router.py`, `app/config.py`, `docker-compose.yml`, `Dockerfile`, `pyproject.toml`
- [FastAPI Metadata and Docs URLs](https://fastapi.tiangolo.com/tutorial/metadata/) — `openapi_tags`, `description`, `docs_url`
- [FastAPI Static Files](https://fastapi.tiangolo.com/tutorial/static-files/) — StaticFiles mount, `html=True`
- [FastAPI Additional Responses](https://fastapi.tiangolo.com/advanced/additional-responses/) — `responses={409: ...}` pattern
- [FastAPI Response Model](https://fastapi.tiangolo.com/tutorial/response-model/) — `response_model=`, `include_in_schema=False`
- [FastAPI OAuth2 Simple Password Bearer](https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/) — `tokenUrl` wires Swagger UI Authorize button
- [mkdocs-material on PyPI](https://pypi.org/project/mkdocs-material/) — v9.7.6, March 19, 2026
- [Material for MkDocs installation guide](https://squidfunk.github.io/mkdocs-material/getting-started/) — dependency tree, version pinning recommendation

### Secondary (MEDIUM confidence)

- [CloudLog API wiki](https://github.com/magicbug/Cloudlog/wiki/API) — comparable self-hosted ham radio API doc format; confirms curl examples are the right format for this user population
- [n8n Docker Compose self-hosted guide](https://docs.n8n.io/hosting/installation/server-setups/docker-compose/) — deployment guide structure (prerequisites, env vars, verification steps)
- [Supabase self-hosting Docker guide](https://supabase.com/docs/guides/self-hosting/docker) — env var reference format, bootstrap account pattern, "CHANGEME" marking convention
- [FastAPI x MkDocs integration pattern](https://rakuichi4817.github.io/posts/2023/fastapi-mkdocs/) — community-verified `app.mount("/devdocs", StaticFiles(directory=site_dir, html=True))` pattern
- [MkDocs discussion: sub-path mounting](https://github.com/squidfunk/mkdocs-material/discussions/6784) — relative URL considerations when MkDocs site is mounted at a sub-path

### Tertiary (LOW confidence)

None — all significant findings have HIGH or MEDIUM confidence backing.

---
*Research completed: 2026-04-04*
*Ready for roadmap: yes*
