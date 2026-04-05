# Stack Research

**Domain:** Documentation milestone — REST API docs + application/operator workflow docs for ollog (FastAPI + HTMX ham radio logbook)
**Researched:** 2026-04-04
**Confidence:** HIGH for FastAPI OpenAPI layer (official docs); HIGH for MkDocs Material stack (PyPI-verified); MEDIUM for Docker integration pattern (community practice, structurally sound)

---

## Context: What Already Exists (Do Not Re-Research)

Existing validated stack: FastAPI 0.135+, Beanie 2.1+, pymongo 4.16+, Jinja2, HTMX 2.0.4, Python 3.12, Docker Compose, MongoDB 7 replica set, uv package manager.

The `app/main.py` already creates `FastAPI(title="ollog", version="0.1.0")`. The built-in `/docs` (Swagger UI) and `/redoc` (ReDoc) endpoints are live with zero additional packages — FastAPI includes them automatically via `fastapi[standard]`.

---

## Two Distinct Documentation Problems

This milestone has two separate concerns that require different tooling:

| Problem | Solution Layer | Tooling |
|---------|---------------|---------|
| REST API reference (endpoints, request/response schemas, auth) | FastAPI built-in OpenAPI generation | No new packages — enrich existing code |
| Narrative docs (operator workflow, admin setup, ADIF import/export guide) | Static site generator | MkDocs + Material theme |

Do not conflate these. The API reference is auto-generated from Python code; narrative docs are handwritten Markdown. They are complementary, not competing.

---

## Recommended Stack (New Additions Only)

### Core Documentation Tools

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `mkdocs-material` | `==9.*` (currently 9.7.6, March 2026) | Static site generator for narrative docs — operator guide, admin setup, workflow reference | FastAPI itself uses Material for MkDocs for its own docs. Actively maintained (released March 19, 2026). Single `pip install` pulls MkDocs 1.6.1, Pygments, pymdown-extensions 10.21.2 automatically. Markdown-native, no RST learning curve, excellent code blocks and tabbed content for showing auth examples. |
| `pymdown-extensions` | pulled as mkdocs-material dep (10.21.2) | Admonitions, code tabs, keyboard shortcut display, highlight | Bundled with mkdocs-material install; no separate install. Extensions like `pymdownx.tabbed`, `pymdownx.highlight`, `pymdownx.superfences`, and `admonition` are the primary ones needed for API reference pages. |

**No additional packages needed for the API layer.** FastAPI's built-in OpenAPI generation handles the REST API documentation entirely. All enrichment is done by annotating existing Python code.

### No New Packages Required For

| Capability | Mechanism | Reason |
|------------|-----------|--------|
| Interactive API reference (Swagger UI) | FastAPI built-in `/docs` | Included in `fastapi[standard]`. Already running. |
| Machine-readable spec | FastAPI built-in `/openapi.json` | No export step needed; live at runtime. |
| API reference (read-only) | FastAPI built-in `/redoc` | Included in `fastapi[standard]`. ReDoc renders cleaner for sharing. |
| Endpoint summaries | Function docstrings (first line) | FastAPI extracts the first line of the function docstring as the summary automatically. |
| Endpoint descriptions | Function docstrings (body after first line) | FastAPI uses the full docstring as the Markdown description in Swagger UI. |
| Tag-based grouping | `tags=` parameter on route decorators | Already a FastAPI feature — `@router.get("/qsos/", tags=["QSO"])` creates grouped sections. |
| Tag descriptions | `openapi_tags` list on `FastAPI()` constructor | Pass a list of dicts to enrich tag groups with Markdown descriptions in the rendered docs. |
| Response schema documentation | Pydantic models (already used) | FastAPI auto-generates schema from existing Pydantic response models. No extra annotation needed. |

---

## FastAPI API Documentation Enrichment (No New Packages)

The following changes to **existing code** are the API documentation work. They require no new packages.

### Constructor-Level Changes (`app/main.py`)

```python
app = FastAPI(
    title="ollog",
    version="0.1.0",
    summary="Self-hosted ADIF-native ham radio logbook REST API",
    description="""
Multi-operator ham radio logbook with QSO CRUD, ADIF import/export,
JWT authentication (cookie and Bearer), SSE live station feed, and
operator profile management.

## Authentication

All API endpoints (except `/auth/login` and `/health`) require a JWT.
Provide it as a `Bearer` token in `Authorization`, or as an `access_token`
cookie for browser sessions.
""",
    openapi_tags=[
        {"name": "Auth", "description": "Login, logout, token lifecycle."},
        {"name": "QSO", "description": "Create, read, update, delete contact log entries."},
        {"name": "ADIF", "description": "Bulk import (.adi/.adif) and full-log export."},
        {"name": "Profile", "description": "Operator profile and station details."},
        {"name": "Admin", "description": "Account management — admin role required."},
        {"name": "Feed", "description": "SSE stream of real-time QSO events."},
        {"name": "Health", "description": "Liveness check."},
    ],
)
```

### Route-Level Changes (Across Routers)

```python
@router.post(
    "/qsos/",
    tags=["QSO"],
    summary="Log a new QSO",
    response_description="The newly created QSO document",
    status_code=201,
)
async def create_qso(body: QSOCreate, ...):
    """Log a new QSO contact.

    Records a radio contact with another station. The `CALL` field is
    required. All ADIF fields are optional — omit fields that are not
    known at log time.

    Requires a valid operator JWT (cookie or Bearer).
    """
```

The pattern is: **first line of docstring = summary** (FastAPI extracts this automatically if no `summary=` kwarg is given), **rest of docstring = Markdown description**, `tags=` routes to the correct grouped section.

---

## MkDocs Setup (Narrative Docs)

### Installation (Dev Dependency Only)

```bash
# Add to [dependency-groups] dev in pyproject.toml, not [project] dependencies
uv add --dev "mkdocs-material==9.*"
```

`mkdocs-material` is a **dev-only** dependency. It is not needed at runtime by the FastAPI application. Do not add it to `[project]` dependencies — it would bloat the production Docker image.

### Project Layout

```
ollog/
  mkdocs.yml           # MkDocs configuration
  docs/
    index.md           # Overview / what is ollog
    getting-started.md # Docker Compose quick start
    operator/
      logging-qsos.md  # How to log contacts
      import-export.md # ADIF import and export workflow
      live-feed.md     # Station feed / multi-op setup
    admin/
      setup.md         # First-run admin bootstrap
      accounts.md      # User management
    api/
      overview.md      # Links to /docs and /redoc, auth explanation
      authentication.md
      endpoints.md     # Narrative description of each route group
    reference/
      adif-fields.md   # Supported ADIF field list
      config.md        # Environment variable reference
```

### `mkdocs.yml` Baseline

```yaml
site_name: ollog Documentation
site_description: Self-hosted ADIF-native ham radio logbook
repo_url: https://github.com/ollog/ollog   # update if public

theme:
  name: material
  palette:
    - scheme: default
      primary: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      primary: indigo
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.top
    - content.code.copy

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite
  - tables
  - toc:
      permalink: true

nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - Operator Guide:
    - Logging QSOs: operator/logging-qsos.md
    - ADIF Import & Export: operator/import-export.md
    - Live Station Feed: operator/live-feed.md
  - Admin Guide:
    - Initial Setup: admin/setup.md
    - Account Management: admin/accounts.md
  - API Reference:
    - Overview: api/overview.md
    - Authentication: api/authentication.md
    - Endpoints: api/endpoints.md
  - Reference:
    - ADIF Fields: reference/adif-fields.md
    - Configuration: reference/config.md
```

### Local Preview

```bash
# From repo root — docs rebuild on file save
uv run mkdocs serve
```

### Static Build

```bash
# Outputs to site/ directory
uv run mkdocs build --strict
```

`--strict` converts warnings (broken links, missing pages) to errors. Use it in CI.

---

## Docker Integration

### Option A: Build Docs Outside Docker (Recommended)

Run `mkdocs build` locally or in CI. Commit the `site/` output (or publish to GitHub Pages / Netlify). The FastAPI Docker container has no awareness of docs — docs are a separate static artifact.

**Why this is correct:** The FastAPI app serves an interactive API at `/docs` (runtime, always current). The narrative MkDocs site is static HTML that can be hosted anywhere. Coupling them in one Docker image adds 150MB+ of Python doc tooling to a production image for no operational benefit.

**Implementation:** Add `mkdocs build` as a CI step. Publish `site/` to GitHub Pages or any static host. The built-in `/docs` and `/redoc` endpoints remain the primary API reference for live deployments.

### Option B: Serve MkDocs Alongside App (If Self-Hosted Static Docs Required)

If the operator needs docs accessible on the same Docker Compose stack (e.g., air-gapped deployment), add a separate Nginx service to serve the built `site/` directory:

```yaml
# Addition to docker-compose.yml
  docs:
    image: nginx:alpine
    volumes:
      - ./site:/usr/share/nginx/html:ro
    ports:
      - "8080:80"
```

This requires running `mkdocs build` before `docker compose up`. The `site/` directory is gitignored and rebuilt as needed. The Nginx container is tiny and has no Python dependency.

**Do not** serve `mkdocs serve` (dev server) in production. It is not designed for production use.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Narrative docs | MkDocs Material | Sphinx | Sphinx uses reStructuredText by default (additional learning curve); autodoc requires docstring format discipline across all modules (RST format), which this project doesn't currently use; heavier setup for what is primarily user-facing narrative docs rather than library API reference. MkDocs Material is Markdown-native and used by FastAPI's own documentation project. |
| Narrative docs | MkDocs Material | Plain Markdown in `docs/` (no generator) | No navigation, search, or code highlighting. Fine for a README but insufficient for multi-page operator + admin guide. |
| API reference | FastAPI built-in `/docs` | Redocly, Stoplight, Postman | Adds external tooling with accounts and licensing for a self-hosted app. FastAPI's built-in Swagger UI already covers interactive testing; ReDoc covers read-only reference. No third-party SaaS needed. |
| API reference enrichment | Docstring + decorator annotations | `fastapi-utils` or schema override tools | FastAPI's own annotation surface covers all needed cases. Adding schema override tools increases maintenance complexity with no meaningful benefit. |
| Doc hosting | CI-built static site | In-app served MkDocs | Bloats production Docker image; `mkdocs serve` is a dev server. Static build + Nginx sidecar is the correct production pattern if self-hosted docs are required. |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `mkdocs-material[imaging]` extras | Requires `cairo`, `pngquant`, `pillow` system dependencies — only needed for social card image generation. Unnecessary for a self-hosted logbook. | Plain `mkdocs-material==9.*` |
| `mkdocstrings` + `mkdocstrings-python` | Auto-generates Python API reference from docstrings — this is a library tool, not a REST API user guide tool. Pulls significant dependency tree (griffe, etc.). The FastAPI `/docs` endpoint already serves the interactive API reference. | FastAPI built-in `/docs` |
| Sphinx | RST-based, heavier setup, autodoc coupling to internal docstring format. Wrong tool for operator/user-facing narrative docs. | MkDocs Material |
| Redocly CLI / OpenAPI bundler | Adds Node.js toolchain to a pure-Python project for no benefit over the built-in `/redoc` endpoint. | FastAPI built-in `/redoc` |
| `pycountry` (for this milestone) | Already researched in prior milestone; already added. Not a documentation package. | (already in stack) |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `mkdocs-material==9.*` (9.7.6) | Python 3.12, uv, pyproject.toml | Dev dependency only. Pulls mkdocs 1.6.1, pymdown-extensions 10.21.2, Pygments automatically. Pin to `9.*` (not `>=9`) to prevent unreviewed major-version upgrades per official Material docs recommendation. |
| `mkdocs` 1.6.1 | Python 3.12 | Pulled as a transitive dependency of mkdocs-material. Do not pin separately. |
| `pymdown-extensions` 10.21.2 | mkdocs-material 9.7.6, Python 3.12 | Pulled as transitive dependency. Do not pin separately. |
| FastAPI OpenAPI enrichment | FastAPI 0.135+, Pydantic v2 | No new packages. `openapi_tags`, `summary`, `description` on `FastAPI()` constructor are stable API. Route-level `tags=`, `summary=`, `response_description=`, docstring extraction all stable. |

---

## Recommended `pyproject.toml` Change

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
    # NEW for documentation milestone:
    "mkdocs-material==9.*",
]
```

One new dev dependency. Production `[project]` dependencies are unchanged.

---

## Sources

- [mkdocs-material on PyPI](https://pypi.org/project/mkdocs-material/) — v9.7.6, released March 19, 2026. HIGH confidence.
- [Material for MkDocs installation guide](https://squidfunk.github.io/mkdocs-material/getting-started/) — confirmed deps bundled (mkdocs, Pygments, pymdown-extensions), version pinning recommendation `9.*`. HIGH confidence.
- [pymdown-extensions on PyPI](https://pypi.org/project/pymdown-extensions/) — v10.21.2, released March 29, 2026. HIGH confidence.
- [mkdocs on PyPI](https://pypi.org/project/mkdocs/) — v1.6.1, current stable, pulled transitively. HIGH confidence.
- [FastAPI Metadata and Docs URLs](https://fastapi.tiangolo.com/tutorial/metadata/) — `openapi_tags`, `summary`, `description`, `contact`, `license_info` constructor params. HIGH confidence.
- [FastAPI Extending OpenAPI](https://fastapi.tiangolo.com/advanced/extending-openapi/) — `openapi_extra`, schema override patterns. HIGH confidence.
- [FastAPI Custom Docs UI Static Assets](https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/) — self-hosting `/docs` assets pattern. HIGH confidence.
- [MkDocs Writing Your Docs](https://www.mkdocs.org/user-guide/writing-your-docs/) — `docs/` directory convention, `nav:` structure. HIGH confidence.
- [How to Generate OpenAPI Documentation in FastAPI](https://oneuptime.com/blog/post/2026-02-02-fastapi-openapi-documentation/view) — current year (Feb 2026) tutorial confirming built-in patterns. MEDIUM confidence (third-party).
- [Sphinx vs MkDocs comparison](https://pythonbiellagroup.it/en/learning/mkdocs_tutorial/mkdocs_vs_sphinx/) — rationale for MkDocs for user-facing narrative docs. MEDIUM confidence.

---

*Stack research for: API documentation + operator/admin narrative docs milestone (ollog)*
*Researched: 2026-04-04*
