# Architecture Patterns

**Domain:** Documentation milestone — API docs + narrative app docs for existing FastAPI + HTMX + MongoDB ham radio logging app
**Researched:** 2026-04-04
**Confidence:** HIGH — based on direct codebase inspection + FastAPI official documentation

---

## Context: What Already Exists

| Existing Component | Location | Notes |
|-------------------|----------|-------|
| FastAPI app instance | `app/main.py` line 71 | `FastAPI(title="ollog", version="0.1.0", lifespan=lifespan)` — no metadata beyond title/version |
| `OAuth2PasswordBearer` | `app/auth/dependencies.py` line 8 | `tokenUrl="/auth/token"` — already wires Swagger UI "Authorize" button to the correct token endpoint |
| Router tags | All routers | `tags=["auth"]`, `tags=["qsos"]`, `tags=["admin"]`, `tags=["adif"]`, `tags=["profile"]`, `tags=["log-ui"]` — tags exist but have no descriptions |
| Static files mount | `app/main.py` line 115 | `app.mount("/static", StaticFiles(directory="static"), name="static")` — mount order matters; `/static` must be last |
| Dockerfile | `Dockerfile` | Copies `app/`, `templates/`, `static/` into image — any new directories added to root must be added here |
| docker-compose.yml | `docker-compose.yml` | Single `api` service; no sidecar; no separate docs service |
| UI routes | `app/qso/ui_router.py`, `app/admin/ui_router.py` | Cookie-auth, Jinja2+HTMX; `/log/*` and `/admin/ui/*` paths |
| REST API routes | All `router.py` files | Bearer JWT auth; `/api/*`, `/auth/*`, `/admin/users/*` paths |

---

## Architecture Decision: Layered Documentation

Documentation for this project separates into two concerns with different technical approaches:

**Layer 1 — API Reference (OpenAPI/Swagger UI):** Machine-generated from the existing FastAPI routers. Already exists at `/docs` and `/redoc`. Needs augmentation with descriptions, security info, and grouped tag metadata — but does NOT need a new framework or new service.

**Layer 2 — Narrative Documentation (Markdown):** Human-authored guides covering: operator workflow, admin workflow, deployment/configuration, API usage tutorials. Cannot be generated from code. Needs a home in the repo and a serving mechanism.

Both layers are served by the existing FastAPI app process. No separate docs service. No CI/CD-built static site deployed separately.

---

## System Overview

```
Browser
  │
  ├── GET /docs          → Swagger UI (FastAPI built-in, augmented)
  ├── GET /redoc         → ReDoc (FastAPI built-in, augmented)
  ├── GET /docs/...      → Narrative docs (MkDocs-built site, mounted via StaticFiles)
  │
  ├── GET /log/*         → HTMX/Jinja2 UI (existing, unchanged)
  ├── GET /admin/ui/*    → HTMX/Jinja2 admin UI (existing, unchanged)
  └── /api/*             → REST API endpoints (existing, unchanged)

FastAPI app (one process)
  ├── app/main.py        → FastAPI() with openapi_tags + description metadata
  ├── All existing routers (unchanged endpoints)
  ├── app.mount("/docs", StaticFiles(directory="site", html=True))   ← NEW
  └── app.mount("/static", StaticFiles(directory="static"))          ← existing (must stay last)

Build pipeline (local, not CI)
  └── mkdocs build → site/           ← built artifact committed to repo
```

---

## Component Boundaries

### New Components

| Component | Location | Responsibility |
|-----------|----------|---------------|
| MkDocs source | `docs/` (repo root) | Markdown source files for narrative docs: operator guide, admin guide, API usage, deployment |
| MkDocs config | `mkdocs.yml` (repo root) | MkDocs + Material theme config; sets `site_dir: site` |
| Built site | `site/` (repo root) | MkDocs output; committed to repo; served via StaticFiles mount |
| Docs mount in main.py | `app/main.py` | `app.mount("/docs", StaticFiles(directory="site", html=True))` — new line before `/static` mount |
| OpenAPI metadata | `app/main.py` | `description`, `openapi_tags` added to `FastAPI()` constructor |

### Modified Components

| Component | What Changes | Why |
|-----------|-------------|-----|
| `app/main.py` | Add `description`, `openapi_tags` to `FastAPI()` constructor; add `/docs` StaticFiles mount before `/static` mount | API reference enrichment + narrative docs serving |
| `Dockerfile` | Add `COPY site/ site/` line | Built docs artifact must be in image |
| `pyproject.toml` | Add `mkdocs-material` to `[project.optional-dependencies].dev` or a new `docs` group | MkDocs is a dev/build tool only, not a runtime dep |

No changes to any router, model, service, template, or authentication logic.

---

## Layer 1: API Reference Augmentation

### What FastAPI's Built-In Docs Already Provide

FastAPI auto-generates `/docs` (Swagger UI) and `/redoc` (ReDoc) from the OpenAPI schema. For this app the schema already includes:

- All endpoints with paths, HTTP methods, request/response shapes
- Bearer auth "Authorize" button — works because `OAuth2PasswordBearer(tokenUrl="/auth/token")` is already declared in `app/auth/dependencies.py`
- Tag groupings — all routers declare tags

**What they are missing:** `description` on each tag (shown in Swagger UI tag groups), app-level `description` (shown at the top of `/docs`), and operator-friendly guidance on how to authenticate and what the endpoints are for.

### What Needs to Be Added

**In `app/main.py` — `FastAPI()` constructor:**

```python
description = """
ollog REST API. All endpoints require Bearer JWT authentication.

## Authentication

1. POST `/auth/token` with `username` and `password` (form fields)
2. Copy the `access_token` from the response
3. Click **Authorize** in Swagger UI and paste the token

## Operator Isolation

All QSO data is scoped to the authenticated operator's callsign.
The callsign is derived from the JWT — never from request body.
"""

tags_metadata = [
    {
        "name": "auth",
        "description": "Login and token management. POST `/auth/token` to receive a Bearer JWT.",
    },
    {
        "name": "qsos",
        "description": "QSO CRUD operations. All endpoints require Bearer JWT. Callsign is injected from JWT.",
    },
    {
        "name": "adif",
        "description": "ADIF import (POST) and export (GET streaming). Import accepts `.adi` files up to 10 MB.",
    },
    {
        "name": "profile",
        "description": "Operator profile fields (OPERATOR, STATION_CALLSIGN, gridsquare, etc.). GET and PATCH.",
    },
    {
        "name": "admin",
        "description": "Admin-only operator account management. Requires admin role JWT.",
    },
]

app = FastAPI(
    title="ollog",
    version="0.1.0",
    description=description,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)
```

The `log-ui` tag (HTMX/cookie routes) should be excluded from `openapi_tags` or given a clear description that it is browser-only. These routes appear in the schema but are not useful to API consumers.

### What the Built-In /docs Cannot Do

Swagger UI has no concept of multi-page narrative documentation, screenshots, workflow guides, or deployment instructions. For that, a separate Markdown-based site is required.

---

## Layer 2: Narrative Documentation

### Technology Choice: MkDocs + Material Theme

**Recommended:** `mkdocs-material` (MkDocs + Material theme).

Rationale:
- FastAPI itself uses MkDocs Material — the toolchain is well-understood in the Python ecosystem
- pip-installable dev dependency: `pip install mkdocs-material`
- `mkdocs build` produces a `site/` directory of static HTML/CSS/JS
- FastAPI can serve `site/` directly via `StaticFiles(directory="site", html=True)`
- No separate process, no Node.js toolchain, no GitHub Pages required
- Self-hosted deployment model matches the rest of the app

**Not recommended:** Docusaurus (Node.js dependency, overkill), Sphinx (RST-first, wrong audience), Gitbook (SaaS), serving raw Markdown at runtime via a Python Markdown parser (no navigation, no search, no theme).

### File Locations

```
ollog/                         ← repo root
├── docs/                      ← MkDocs source (Markdown, images)
│   ├── index.md               ← Home page / overview
│   ├── operator/
│   │   ├── getting-started.md ← First login, logging a QSO
│   │   ├── log-view.md        ← Using the log table, filters, pagination
│   │   ├── import-export.md   ← ADIF import/export workflow
│   │   └── profile.md         ← Setting profile fields
│   ├── admin/
│   │   ├── setup.md           ← Docker Compose, environment variables
│   │   ├── user-management.md ← Creating/enabling/disabling operators
│   │   └── deployment.md      ← Production deployment considerations
│   └── api/
│       ├── authentication.md  ← Bearer JWT workflow, token endpoint
│       ├── qsos.md            ← QSO CRUD walkthrough
│       └── adif.md            ← ADIF import/export API usage
├── mkdocs.yml                 ← MkDocs config
├── site/                      ← MkDocs build output (committed)
├── app/
├── templates/
└── static/
```

### mkdocs.yml

```yaml
site_name: ollog Documentation
site_description: Ham Radio Online Logbook
docs_dir: docs
site_dir: site

theme:
  name: material
  palette:
    scheme: default
  features:
    - navigation.sections
    - navigation.top
    - search.highlight

nav:
  - Home: index.md
  - Operator Guide:
    - Getting Started: operator/getting-started.md
    - Log View: operator/log-view.md
    - Import & Export: operator/import-export.md
    - Profile: operator/profile.md
  - Admin Guide:
    - Setup: admin/setup.md
    - User Management: admin/user-management.md
    - Deployment: admin/deployment.md
  - API Reference:
    - Authentication: api/authentication.md
    - QSOs: api/qsos.md
    - ADIF: api/adif.md
```

### Serving the Built Site from FastAPI

The built `site/` directory is mounted in `app/main.py`:

```python
# Mount narrative docs — must come BEFORE /static mount
app.mount("/docs", StaticFiles(directory="site", html=True), name="docs")

# Static files (existing — must remain last)
app.mount("/static", StaticFiles(directory="static"), name="static")
```

**Mount order is critical.** FastAPI evaluates mounts in registration order. `/docs` must be registered before `/static` to avoid the wildcard static handler intercepting requests to `/docs/...`.

**`html=True` is required.** This causes StaticFiles to serve `index.html` for requests to directories (e.g., `GET /docs/operator/` serves `site/operator/index.html`). Without it, directory paths return 404.

**Conflict with existing `/docs` route:** FastAPI's default Swagger UI is mounted at `/docs`. Mounting a StaticFiles application at `/docs` will shadow the built-in Swagger UI. Two options:

- Option A: Move narrative docs to `/manual` or `/guide` — preserves `/docs` as Swagger UI (recommended for self-hosted developer audience that uses the API)
- Option B: Rename Swagger UI to `/api/docs` via `FastAPI(docs_url="/api/docs")` — makes the narrative docs the primary `/docs` endpoint

**Recommendation: Option A — serve narrative docs at `/guide`.** The self-hosted ham radio operator audience who installs this app will use it via the web UI, not the API. Swagger UI at `/docs` is the convention API consumers expect. Narrative docs at `/guide` is explicit and unambiguous.

```python
# app/main.py
app = FastAPI(
    title="ollog",
    version="0.1.0",
    description=description,
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    # docs_url="/docs" is the default — leave it; Swagger UI stays at /docs
)

# Narrative docs — after all routers, before /static
app.mount("/guide", StaticFiles(directory="site", html=True), name="guide")
app.mount("/static", StaticFiles(directory="static"), name="static")
```

---

## HTMX UI Documentation Strategy

The HTMX-based UI (`/log/*`, `/admin/ui/*`) does not have a programmatic API — it is a browser-only interface. Documentation for it belongs in the narrative docs (`docs/operator/` and `docs/admin/`), not in the OpenAPI schema.

The `log-ui` tag and `admin-ui` routes that appear in `/docs` (Swagger UI) should be explained in the app-level description or tag description as "browser-only routes, not REST API endpoints." This prevents API consumers from trying to call them programmatically.

For HTMX-specific workflow documentation:

- **Operator workflow docs** describe the complete browser workflow: login → log a QSO → edit inline → paginate/filter → import/export ADIF
- **Screenshots** go in `docs/` as images referenced from Markdown (`![Alt](../images/log-view.png)`)
- **Partial HTMX responses** (`HX-Request` header paths) do not need separate documentation — they are internal implementation details, not user-facing behaviors

---

## Data Flow

### Doc Build Pipeline

```
Author edits docs/*.md
  → mkdocs build (local)
  → site/ (static HTML/CSS/JS)
  → git commit site/
  → docker-compose build (COPY site/ site/)
  → FastAPI serves site/ at /guide
```

This is a commit-triggered rebuild, not a live-reload pipeline. For a self-hosted single-operator or small-group app this is acceptable — docs do not change on every deploy.

### API Reference Request Flow

```
GET /docs
  → FastAPI built-in Swagger UI
  → fetches /openapi.json (auto-generated from routers)
  → renders tag groups with descriptions from openapi_tags
  → "Authorize" button POSTs to /auth/token
  → Bearer token injected into subsequent test requests
```

### Narrative Docs Request Flow

```
GET /guide/operator/getting-started
  → StaticFiles mount (directory="site", html=True)
  → serves site/operator/getting-started/index.html
  → all CSS/JS assets served from site/assets/
  → no Python logic involved
```

---

## Recommended Project Structure Changes

```
ollog/
├── docs/                          NEW — MkDocs source files
│   ├── index.md
│   ├── operator/
│   │   ├── getting-started.md
│   │   ├── log-view.md
│   │   ├── import-export.md
│   │   └── profile.md
│   ├── admin/
│   │   ├── setup.md
│   │   ├── user-management.md
│   │   └── deployment.md
│   └── api/
│       ├── authentication.md
│       ├── qsos.md
│       └── adif.md
├── mkdocs.yml                     NEW — MkDocs config
├── site/                          NEW — MkDocs built output (committed)
├── app/
│   └── main.py                    MODIFIED — description, openapi_tags, /guide mount
├── Dockerfile                     MODIFIED — COPY site/ site/
├── pyproject.toml                 MODIFIED — mkdocs-material dev dependency
├── templates/                     unchanged
└── static/                        unchanged
```

---

## Architectural Patterns

### Pattern 1: Built Site Committed to Repo

**What:** `mkdocs build` output (`site/`) is committed to the repo rather than built during Docker image construction.

**Why:** The Dockerfile currently uses `pip install` + `COPY` — it has no MkDocs build step. Adding `mkdocs build` to the Dockerfile requires `mkdocs-material` to be a runtime pip dependency (it is 50+ MB). Committing `site/` keeps it as a dev-only tool and keeps the Docker image lean.

**Trade-off:** `site/` in the repo adds ~1-3 MB of generated HTML per doc set. Acceptable for a self-hosted project. If repo size becomes a concern, add `site/` to `.gitignore` and add a `mkdocs build` step to the Dockerfile or a CI job.

### Pattern 2: Single-Process Documentation Serving

**What:** Narrative docs are served by the same FastAPI process that serves the API and UI, via a StaticFiles mount.

**Why:** The deployment model is Docker Compose with a single `api` service. Adding a separate Nginx or documentation service adds operational complexity (another container, another port, another failure point) with no benefit for a self-hosted single-operator app.

**Trade-off:** A restart of the FastAPI app briefly takes down the docs. Acceptable — the docs are static and the restart is fast.

### Pattern 3: openapi_tags Descriptions as the API's First-Page UX

**What:** Tag descriptions in `openapi_tags` appear in Swagger UI before any endpoint is expanded. This is the first thing an API consumer reads.

**Why:** Without tag descriptions, Swagger UI shows raw tag names (`auth`, `qsos`, `adif`) with no context. With descriptions, each section explains what it does and what auth is required.

**Implementation:** Descriptions support CommonMark Markdown. Use `**bold**` for key terms (token endpoint URL, role names).

---

## Anti-Patterns

### Anti-Pattern 1: Serving Raw Markdown at Runtime

**What people do:** Add a `/docs/{page}` route that reads `.md` files from disk, renders them via `python-markdown` or `mistune`, and returns HTML.

**Why it's wrong:** No navigation, no search, no consistent styling, no cross-linking. Every page render hits the filesystem. HTMX-style partial updates do not work with runtime-rendered docs.

**Do this instead:** `mkdocs build` once, commit `site/`, mount with StaticFiles. Full navigation and search with zero Python code.

### Anti-Pattern 2: Shadowing Swagger UI with the Narrative Docs Mount

**What people do:** Mount `StaticFiles(directory="site")` at `/docs`, overriding FastAPI's built-in Swagger UI.

**Why it's wrong:** `/docs` is the conventional and expected Swagger UI path. API consumers, curl examples, and team members will expect Swagger UI there. The StaticFiles mount silently replaces it with the narrative site's `index.html`, giving no error — only confusion.

**Do this instead:** Mount narrative docs at `/guide` (or `/manual`). Leave `/docs` as Swagger UI. If you genuinely want the narrative docs at `/docs`, rename Swagger UI to `/api/docs` via `FastAPI(docs_url="/api/docs")` and document the new path explicitly.

### Anti-Pattern 3: Adding `mkdocs-material` as a Runtime Dependency

**What people do:** Add `mkdocs-material` to `[project.dependencies]` in `pyproject.toml`.

**Why it's wrong:** MkDocs is a build tool, not a runtime library. Adding it to runtime deps bloats the Docker image by 50+ MB and installs it in production where it is never used.

**Do this instead:** Add to `[project.optional-dependencies].docs` or `[dependency-groups].docs`. Install with `pip install -e ".[docs]"` locally. Do not install in the production Docker image.

### Anti-Pattern 4: Mount Order with /static Before /docs or /guide

**What people do:** Add the StaticFiles mount for the docs directory after the `/static` mount, or add it without checking the existing mount registration order.

**Why it's wrong:** FastAPI evaluates mounts in registration order. The `/static` mount is a wildcard handler for any path under `/static`. If the docs mount path starts with a prefix that doesn't conflict (`/guide`), order doesn't matter. But if the docs mount overlaps with any existing route prefix, incorrect order causes silent 404s.

**Do this instead:** Register the docs StaticFiles mount immediately before the `/static` mount, after all APIRouters. Verify by checking that `GET /guide/` returns the docs index, not a 404.

---

## Build Order for This Milestone

Documentation work decomposes into two independent tracks that can proceed in parallel, with a small integration step at the end.

```
Track A: OpenAPI Augmentation
  1. Write openapi_tags metadata (descriptions for auth, qsos, adif, profile, admin)
  2. Write app-level description string
  3. Add both to FastAPI() constructor in app/main.py
  4. Verify at /docs — tag sections show descriptions, Authorize works

  Dependencies: none (pure metadata, zero logic changes)
  Risk: LOW — additive metadata only

Track B: Narrative Docs
  1. Install mkdocs-material (dev dependency)
  2. Create mkdocs.yml
  3. Create docs/ directory with stub index.md
  4. mkdocs build → site/ generated
  5. Commit site/
  6. Add /guide StaticFiles mount to app/main.py (after routers, before /static)
  7. Add COPY site/ site/ to Dockerfile
  8. Write content: operator guide, admin guide, API tutorials

  Dependencies within track: steps 1-5 must complete before step 6 (site/ must exist)
  Risk: LOW for serving; MEDIUM for content quality (content is the hard part)

Integration step (after both tracks complete):
  9. Verify /docs shows augmented API reference
  10. Verify /guide serves narrative docs
  11. Verify /log/* and /admin/ui/* are unaffected
  12. docker-compose build && docker-compose up — verify both endpoints work in container
```

---

## Integration Point Risk Summary

| Integration Point | Change Type | Risk |
|-------------------|-------------|------|
| `FastAPI()` — add `description` + `openapi_tags` | Additive metadata | LOW — no logic change; worst case is a typo in the description string |
| `app.mount("/guide", StaticFiles(...))` | New mount | LOW — does not touch existing routes; failure mode is 404 (not a 500) |
| Mount order (`/guide` before `/static`) | Mount ordering | MEDIUM — incorrect order is silent; must verify manually |
| `Dockerfile` — add `COPY site/ site/` | New COPY line | LOW — if `site/` is missing the image build fails (loud error, not silent) |
| `site/` committed to repo | New committed directory | LOW — adds build artifact to repo; document in contributing guide |
| All existing routes | No change | NONE |
| MongoDB schema | No change | NONE |
| Auth / operator isolation | No change | NONE |
| HTMX UI behavior | No change | NONE |

---

## Sources

**HIGH confidence (official documentation):**
- [FastAPI Metadata and Docs URLs](https://fastapi.tiangolo.com/tutorial/metadata/) — `openapi_tags`, `description`, `docs_url`, `redoc_url` parameters (verified 2026-04-04)
- [FastAPI Custom Docs UI Assets (Self-Hosting)](https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/) — `docs_url=None`, custom `get_swagger_ui_html()` pattern
- [FastAPI Static Files](https://fastapi.tiangolo.com/tutorial/static-files/) — `StaticFiles`, `html=True`, mount pattern
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) — theme capabilities, `mkdocs build`, `site_dir`
- [FastAPI OAuth2 Simple Password Bearer](https://fastapi.tiangolo.com/tutorial/security/simple-oauth2/) — `tokenUrl` wires Swagger UI Authorize button

**MEDIUM confidence (verified against official source + community use):**
- [FastAPI × MkDocs integration pattern](https://rakuichi4817.github.io/posts/2023/fastapi-mkdocs/) — `app.mount("/devdocs", StaticFiles(directory=site_dir, html=True))` pattern; community-verified but not in official FastAPI docs
- [MkDocs discussion: Publish via FastAPI](https://github.com/squidfunk/mkdocs-material/discussions/6784) — relative URL considerations when MkDocs site is mounted at a sub-path

**Direct codebase inspection (HIGH confidence):**
- `app/main.py` — existing `FastAPI()` constructor, mount order, `OAuth2PasswordBearer` declaration
- `app/auth/dependencies.py` — `OAuth2PasswordBearer(tokenUrl="/auth/token")` already in place
- All `router.py` files — existing `tags=["..."]` declarations
- `Dockerfile` — `COPY` structure, no existing docs build step
- `pyproject.toml` — current dependencies, no MkDocs

---

*Architecture research for: documentation milestone — FastAPI + HTMX + MongoDB ham radio logbook*
*Researched: 2026-04-04*
