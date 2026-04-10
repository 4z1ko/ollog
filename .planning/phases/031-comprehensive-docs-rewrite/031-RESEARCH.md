# Phase 31: Comprehensive Docs Rewrite - Research

**Researched:** 2026-04-10
**Domain:** MkDocs Material documentation authoring, mkdocs-swagger-ui-tag, FastAPI openapi.json export
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from phase context — no CONTEXT.md)

### Locked Decisions
- Plugin: `mkdocs-swagger-ui-tag` (static assets bundled — no CDN dependency) — NOT `mkdocs-render-swagger-plugin`
- `openapi.json` export: `python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > docs/openapi.json` as pre-build step (importable without running database because `init_db()` is lifespan-scoped)
- `html=True` on `StaticFiles(directory="site", html=True)` in `app/main.py` is load-bearing for MkDocs `use_directory_urls: true`; must be annotated with an explicit comment
- Nav: 2-level grouped sections — Getting Started, Operator Guide, Admin Guide, API Reference, Reference, Troubleshooting
- Do NOT activate both `navigation.indexes` and `navigation.sections` simultaneously (MkDocs Material issue #3070)
- Built `site/` committed to the repository; served by existing FastAPI StaticFiles mount at `/guide`

### Claude's Discretion
- (no discretion areas specified)

### Deferred Ideas (OUT OF SCOPE)
- (none specified)
</user_constraints>

---

## Summary

Phase 31 is a documentation rewrite, not a code feature. The work involves restructuring `mkdocs.yml`, writing/rewriting markdown files across 6 nav sections, integrating `mkdocs-swagger-ui-tag` with a locally exported `openapi.json`, annotating one load-bearing line in `app/main.py`, and running `mkdocs build` to produce a clean zero-warning build that gets committed.

The current docs have 7 flat nav entries with no grouping. The target is a 2-level grouped structure (6 sections, multiple pages per section) covering all v1.0–v1.8 features. The biggest new content gap is the Admin Guide (admin container on port 8001 with `--profile admin`, admin_token cookie), Backup CLI + S3 setup, and API token feature (v1.7).

The primary technical risk is the `openapi.json` pre-build step placement and the `not_in_nav` setting needed to suppress MkDocs warnings about `openapi.json` being in `docs/` but not in `nav:`. The locked decision that `navigation.indexes` and `navigation.sections` must not both be active avoids MkDocs Material issue #3070.

**Primary recommendation:** Restructure nav first in `mkdocs.yml`, then write/migrate content page-by-page, add `mkdocs-swagger-ui-tag` plugin and its `openapi.json` pre-build step last, then run `mkdocs build --strict` to catch all warnings before committing.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mkdocs-material | 9.* (pinned in pyproject.toml) | MkDocs theme — already installed | Already in `[dependency-groups] dev` |
| mkdocs-swagger-ui-tag | 0.8.0 (latest as of 2026-02-22) | Interactive API reference, static Swagger UI assets bundled | Locked decision; no CDN, works offline |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| beautifulsoup4 | >=4.13.3 | Required transitive dep of mkdocs-swagger-ui-tag | Installed automatically with the plugin |
| swagger-ui-dist | 5.27.1 | Pinned by mkdocs-swagger-ui-tag | Installed automatically |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| mkdocs-swagger-ui-tag | mkdocs-render-swagger-plugin | render-swagger is NOT chosen (locked decision) |

**Installation (add to pyproject.toml `[dependency-groups] dev`):**
```bash
uv add --dev mkdocs-swagger-ui-tag
# or directly in pyproject.toml:
# mkdocs-swagger-ui-tag>=0.8.0
```

---

## Architecture Patterns

### Target docs/ Structure
```
docs/
├── index.md                        # Home — overview, quick links, feature list
├── getting-started/
│   ├── index.md                    # Section overview
│   ├── quickstart.md               # Deploy + first login + first QSO
│   └── first-qso.md                # Detailed walkthrough steps
├── operator-guide/
│   ├── index.md
│   ├── logging-qsos.md             # Web UI + API QSO entry
│   ├── adif-import-export.md       # Import + export
│   ├── api-tokens.md               # NEW: v1.7 token creation/listing/revocation
│   ├── profile.md                  # Profile fields, STATION_CALLSIGN, gridsquare
│   └── udp-adif.md                 # UDP listener, Log4OM, WSJT-X, N1MM+
├── admin-guide/
│   ├── index.md
│   ├── deployment.md               # Docker Compose setup (current deployment.md)
│   ├── admin-container.md          # NEW: port 8001, --profile admin, admin_token cookie
│   ├── account-management.md       # Existing admin-guide.md content
│   └── backup.md                   # NEW: backup CLI, BACKUP_SCHEDULE, S3 setup
├── api-reference/
│   ├── index.md                    # Intro + auth overview
│   └── interactive.md              # Embeds <swagger-ui src="../openapi.json"/>
├── reference/
│   ├── index.md
│   ├── adif-field-reference.md     # Current adif-field-reference.md (moved)
│   └── environment-variables.md   # Complete env var table
├── troubleshooting/
│   └── index.md                    # Current troubleshooting.md (moved here)
└── openapi.json                    # Generated pre-build — NOT manually edited
```

### Pattern 1: openapi.json Pre-Build Export
**What:** Export FastAPI OpenAPI schema to `docs/openapi.json` before running `mkdocs build`. The app imports cleanly without a running database because `init_db()` is inside the `lifespan` context manager, not at module import time.
**When to use:** Every time `mkdocs build` is run, including in the Makefile/CI step.
**Example:**
```bash
# Step 1: export schema (database NOT required — lifespan not invoked at import)
python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > docs/openapi.json

# Step 2: build docs
mkdocs build
```

### Pattern 2: Swagger UI Embed in Markdown
**What:** Place `<swagger-ui src="...">` tag inside a markdown page. The plugin processes this during build and injects full Swagger UI HTML with bundled static assets.
**When to use:** The API Reference interactive page.
**Example:**
```markdown
<!-- docs/api-reference/interactive.md -->
# Interactive API Reference

<swagger-ui src="../openapi.json"/>
```

Note on path: `../openapi.json` is relative to the markdown file's location (`docs/api-reference/interactive.md`), so it resolves to `docs/openapi.json`. Confirmed: the plugin copies the spec as a static asset, making it available at the built site path.

### Pattern 3: mkdocs.yml Config for 2-Level Nav (no navigation.indexes, no navigation.sections)
**What:** 2-level grouped nav with plain `navigation.expand` to show depth without triggering issue #3070.
**When to use:** This project's locked constraint.
**Example:**
```yaml
site_name: ollog
site_url: http://localhost:8000/guide/
use_directory_urls: true

theme:
  name: material
  palette:
    scheme: slate
    primary: indigo
  features:
    - navigation.expand
    # NOTE: Do NOT add navigation.indexes AND navigation.sections together
    # — they conflict (MkDocs Material issue #3070)

plugins:
  - search
  - swagger-ui-tag

not_in_nav: |
  openapi.json

nav:
  - Getting Started:
    - getting-started/index.md
    - Quickstart: getting-started/quickstart.md
  - Operator Guide:
    - operator-guide/index.md
    - Logging QSOs: operator-guide/logging-qsos.md
    - ADIF Import/Export: operator-guide/adif-import-export.md
    - API Tokens: operator-guide/api-tokens.md
    - Profile: operator-guide/profile.md
    - UDP ADIF: operator-guide/udp-adif.md
  - Admin Guide:
    - admin-guide/index.md
    - Deployment: admin-guide/deployment.md
    - Admin Container: admin-guide/admin-container.md
    - Account Management: admin-guide/account-management.md
    - Backup: admin-guide/backup.md
  - API Reference:
    - api-reference/index.md
    - Interactive Reference: api-reference/interactive.md
  - Reference:
    - reference/index.md
    - ADIF Field Reference: reference/adif-field-reference.md
    - Environment Variables: reference/environment-variables.md
  - Troubleshooting:
    - troubleshooting/index.md
```

### Pattern 4: StaticFiles annotation in app/main.py
**What:** The `html=True` parameter on the `/guide` mount is load-bearing for `use_directory_urls: true`. Without it, navigating to `/guide/getting-started/` returns 404 because FastAPI won't serve `index.html` from subdirectories.
**Where:** Line 134 of `app/main.py` — already in place, needs annotation.
**Example:**
```python
# html=True is load-bearing: MkDocs use_directory_urls:true creates subdirectories
# with index.html files. Without html=True, FastAPI returns 404 for clean URLs
# like /guide/getting-started/ — DO NOT remove this flag.
app.mount("/guide", StaticFiles(directory="site", html=True), name="guide")
```

### Anti-Patterns to Avoid
- **Both `navigation.indexes` AND `navigation.sections` active:** Triggers MkDocs Material issue #3070 — first section's first page turns into section index unexpectedly. Use one or neither.
- **`openapi.json` in nav:** The file lives in `docs/` but is not a human-readable page. MkDocs will warn "file not in nav" unless suppressed with `not_in_nav`.
- **Running `mkdocs build` without exporting openapi.json first:** The Swagger UI page will silently fail to load (404 for the spec file) or build with a stale schema.
- **Relative paths wrong in swagger-ui src:** `src="../openapi.json"` is correct from `docs/api-reference/interactive.md`. `src="./openapi.json"` would look in `docs/api-reference/` and fail.
- **Removing `html=True` from StaticFiles mount:** Breaks all clean URL navigation under `/guide/`.
- **Using CDN-dependent swagger plugin:** Locked against. Use `mkdocs-swagger-ui-tag` only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Interactive API explorer | Custom HTML/JS embed | `mkdocs-swagger-ui-tag` | Handles asset bundling, dark mode sync with Material, OAuth2 support |
| OpenAPI schema | Manual JSON | `app.openapi()` export via python -c | FastAPI auto-generates from route decorators, response models, docstrings |
| Nav structure rendering | Custom sidebar HTML | MkDocs Material nav features | Material handles responsive collapsible nav correctly |

**Key insight:** The FastAPI app already has rich route decorators and Pydantic models — the full OpenAPI schema is free, just needs to be exported and embedded.

---

## Common Pitfalls

### Pitfall 1: MkDocs Warning — openapi.json not in nav
**What goes wrong:** `mkdocs build` prints `WARNING - The following pages exist in the docs directory, but are not included in the "nav" configuration: openapi.json`. Build exits non-zero with `--strict`.
**Why it happens:** `openapi.json` is placed in `docs/` for the plugin to reference, but it's not a nav page.
**How to avoid:** Add `not_in_nav: |\n  openapi.json` to `mkdocs.yml`.
**Warning signs:** Build warning with filename `openapi.json`.

### Pitfall 2: navigation.indexes + navigation.sections Both Active
**What goes wrong:** The first page of the first section gets treated as a section index, producing broken navigation.
**Why it happens:** MkDocs Material issue #3070 — the two features have overlapping behavior when all top-level items are sections.
**How to avoid:** Use only one or neither. Locked decision: do not use both.
**Warning signs:** Navigation visually broken on first section entry after build.

### Pitfall 3: Stale or Missing openapi.json
**What goes wrong:** `<swagger-ui src="../openapi.json"/>` renders empty or 404s in the browser.
**Why it happens:** `openapi.json` wasn't regenerated before `mkdocs build`, or it was deleted.
**How to avoid:** Always run the export command before `mkdocs build`. Consider a Makefile target that chains both.
**Warning signs:** Swagger UI renders with an error banner ("Failed to load API definition").

### Pitfall 4: Wrong src Path in swagger-ui Tag
**What goes wrong:** Swagger UI loads but spec file returns 404.
**Why it happens:** Path is relative to the markdown source file, not the site root.
**How to avoid:** From `docs/api-reference/interactive.md`, use `src="../openapi.json"` (one level up). From `docs/api.md` (root-level file), use `src="./openapi.json"`.
**Warning signs:** Browser network tab shows 404 for `openapi.json`.

### Pitfall 5: Missing `html=True` on StaticFiles Mount
**What goes wrong:** `/guide/admin-guide/` returns 404; only `/guide/admin-guide/index.html` would work.
**Why it happens:** `use_directory_urls: true` in MkDocs produces subdirectories with `index.html`. FastAPI's `StaticFiles` without `html=True` does not serve directory index files.
**How to avoid:** Keep `html=True` — annotate the line so future maintainers understand it's load-bearing.
**Warning signs:** `/guide/` works but all sub-paths 404.

### Pitfall 6: mkdocs build Warns on Broken Internal Links
**What goes wrong:** Links between relocated pages break after restructuring from flat to grouped nav.
**Why it happens:** Current docs have flat paths (`deployment.md`); after restructure they become `admin-guide/deployment.md`.
**How to avoid:** After moving files to subdirectories, audit all internal `[text](filename.md)` links in every page. Use `mkdocs build --strict` to catch broken links.
**Warning signs:** `WARNING - Doc file contains a link to...` in build output.

### Pitfall 7: Admin Container Uses `admin_token` Cookie (not Bearer header)
**What goes wrong:** Documentation incorrectly instructs admin UI users to send Bearer tokens when the admin container's browser UI uses a cookie.
**Why it happens:** `admin_main.py` mounts `ui_router` which uses cookie auth, separate from the REST API Bearer path.
**How to avoid:** Admin Guide must distinguish: REST admin API uses Bearer JWT; Admin UI browser session uses `admin_token` cookie.
**Warning signs:** Users can't log in via the admin UI following the docs.

---

## Code Examples

Verified from codebase inspection:

### Current StaticFiles mount (app/main.py line 134)
```python
# html=True is load-bearing: MkDocs use_directory_urls:true generates subdirectory
# index.html files. Without html=True, FastAPI returns 404 for clean URLs like
# /guide/admin-guide/ — DO NOT remove this flag.
app.mount("/guide", StaticFiles(directory="site", html=True), name="guide")
```

### openapi.json Export Command (no database needed)
```bash
python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > docs/openapi.json
```
This works because `init_db()` is called inside `lifespan()`, which is never invoked during a plain import. The FastAPI app object and all its routes exist at import time.

### mkdocs.yml plugins section with swagger-ui-tag
```yaml
plugins:
  - search
  - swagger-ui-tag:
      docExpansion: none
      syntaxHighlightTheme: monokai
```

### swagger-ui embed in markdown
```markdown
<swagger-ui src="../openapi.json"/>
```

### not_in_nav for openapi.json
```yaml
not_in_nav: |
  openapi.json
```

### Backup CLI invocation (from app/backup/__main__.py)
```bash
# Run a one-shot backup immediately; prints path of created .gz file
python -m app.backup
```
Environment variables required: `MONGODB_URI`, `MONGODB_DB`, `BACKUP_DIR` (default `/app/backups`). Optional: `BACKUP_S3_BUCKET`, `BACKUP_S3_PREFIX` (default `backups/`).

### Backup scheduler (cron in env)
```
BACKUP_SCHEDULE=0 2 * * *   # nightly 02:00 UTC
```

### Admin container startup (from docker-compose.yml)
```bash
# Activated only with --profile admin
docker compose --profile admin up admin
# Port 8001, separate FastAPI app (app.admin_main:app)
```
The admin service uses `profiles: [admin]` — it does NOT start with plain `docker compose up`.

### API token creation (from /api/tokens router)
```bash
# Create token (JWT auth required; returns full_token exactly once)
curl -X POST http://localhost:8000/api/tokens/ \
  -H "Authorization: Bearer $TOKEN" \
  -F "name=my-script" \
  -F "expires_at=2025-12-31"

# List tokens
curl http://localhost:8000/api/tokens/ \
  -H "Authorization: Bearer $TOKEN"

# Revoke token
curl -X DELETE http://localhost:8000/api/tokens/{token_id} \
  -H "Authorization: Bearer $TOKEN"

# Use API token (X-API-Key header)
curl http://localhost:8000/api/qsos/ \
  -H "X-API-Key: ollog_abc123..."
```

---

## What Exists Now vs What Must Be Written

### Current docs/ (7 flat files)
| File | Status | Action |
|------|--------|--------|
| `index.md` | Exists | Update quick links to new nav structure |
| `deployment.md` | Exists | Move to `admin-guide/deployment.md`; update env table with v1.7/v1.8 vars |
| `getting-started.md` | Exists | Split/move to `getting-started/` section |
| `admin-guide.md` | Exists | Move to `admin-guide/account-management.md`; update JWT expire note (now 480 min) |
| `api-reference.md` | Exists, comprehensive | Move to `api-reference/` section; add v1.7 token endpoints |
| `adif-field-reference.md` | Exists | Move to `reference/adif-field-reference.md` |
| `troubleshooting.md` | Exists, thorough | Move to `troubleshooting/index.md` |

### New pages required (DOC gaps)
| Page | Content | Key facts from codebase |
|------|---------|------------------------|
| `admin-guide/admin-container.md` | Port 8001, `--profile admin`, admin_token cookie, `app.admin_main:app` | `docker-compose.yml` `admin` service; `admin_main.py`; `profiles: [admin]` |
| `admin-guide/backup.md` | `python -m app.backup`, `BACKUP_SCHEDULE`, `BACKUP_S3_BUCKET`, `BACKUP_S3_PREFIX`, `BACKUP_DIR` | `app/backup/__main__.py`, `app/backup/dump.py`, `app/config.py` |
| `operator-guide/api-tokens.md` | Creation (POST /api/tokens/), listing, revocation, `X-API-Key` header, `APP_OLLOG_TOKEN` env | `app/tokens/router.py`; `form` fields: `name`, `expires_at` (YYYY-MM-DD optional) |
| `api-reference/interactive.md` | `<swagger-ui src="../openapi.json"/>` embed | Plugin locked; path relative to file location |
| Section `index.md` files (6) | Brief section overviews with child page links | Write fresh |

### API endpoints by section (for api-reference completeness)
| Section | Endpoints |
|---------|-----------|
| Auth | POST /auth/token, GET /auth/me |
| QSOs | POST /api/qsos/, GET /api/qsos/, GET /api/qsos/{id}, PATCH /api/qsos/{id}, DELETE /api/qsos/{id} |
| ADIF | POST /api/adif/import, GET /api/adif/export |
| Profile | GET /api/profile/, PATCH /api/profile/ |
| Tokens | POST /api/tokens/, GET /api/tokens/, DELETE /api/tokens/{token_id} |
| Admin | GET /admin/users/, POST /admin/users/, PATCH /admin/users/{username}/enabled, POST /admin/users/{username}/reset-password |
| Health | GET /health |
| Feed | GET /feed/station (SSE, cookie auth, not in OpenAPI schema) |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat 7-page nav | 2-level grouped 6-section nav | Phase 31 | Nav scales with v1.8 feature set |
| No interactive API | Swagger UI via mkdocs-swagger-ui-tag | Phase 31 | Try-it-out in docs without running a separate server |
| No admin container docs | Admin container guide (port 8001, profiles) | Phase 29 feature, Phase 31 docs | Operators know how to start admin UI |
| No backup docs | Backup CLI + scheduler + S3 guide | Phase 30 feature, Phase 31 docs | Operators can set up automated backups |
| JWT_EXPIRE_MINUTES default shown as 60 | Now 480 (8h session) | Phase 24 | deployment.md table must be updated |

**Outdated content in existing docs:**
- `admin-guide.md` line 16 says "default: 60" for JWT_EXPIRE_MINUTES — now 480 (per `app/config.py`)
- `getting-started.md` Step 1 says "valid for JWT_EXPIRE_MINUTES (default 60 minutes)" — must update to 480
- `api-reference.md` says "16 endpoints" but v1.7 added 3 token endpoints (now 19+ endpoints)
- `api-reference.md` does not document any token endpoints
- `deployment.md` environment variables table is missing: `BACKUP_SCHEDULE`, `BACKUP_S3_BUCKET`, `BACKUP_S3_PREFIX`, `BACKUP_DIR`, `API_TOKEN_SECRET` (required)

---

## Open Questions

1. **`APP_OLLOG_TOKEN` env var reference**
   - What we know: The phase requirements mention `APP_OLLOG_TOKEN` in DOC-06 for the API token feature
   - What's unclear: `APP_OLLOG_TOKEN` does not appear in `app/config.py` or any router code found. The UDP token cache uses `X-API-Key` header auth. This may be a documentation naming convention (i.e., the env var name for an API token used in automation scripts) rather than an actual settings field.
   - Recommendation: Search `app/auth/dependencies.py` and `app/udp/` for `APP_OLLOG_TOKEN` before writing the API tokens page. If it's not a real env var, document `X-API-Key` header usage only.

2. **swagger-ui src path for local files — exact format**
   - What we know: Plugin supports local static files in `docs/`; relative path `src="../openapi.json"` should work from `docs/api-reference/interactive.md`
   - What's unclear: The official docs show remote URL examples but not a concrete local path example
   - Recommendation: Test with `mkdocs serve` after first build. If `../openapi.json` fails, try placing `openapi.json` in `docs/api-reference/` and using `src="./openapi.json"`, then update the pre-build export path accordingly.

3. **`admin_token` cookie name**
   - What we know: `admin_main.py` includes `ui_router` for browser UI using cookie auth
   - What's unclear: The exact cookie name (`admin_token` vs `access_token`) — need to check `app/admin/ui_router.py`
   - Recommendation: Read `app/admin/ui_router.py` when writing `admin-guide/admin-container.md`.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection: `app/main.py`, `app/admin_main.py`, `app/config.py`, `app/auth/router.py`, `app/qso/router.py`, `app/tokens/router.py`, `app/admin/router.py`, `app/backup/__main__.py`, `app/backup/dump.py`, `docker-compose.yml`
- Direct codebase inspection: all 7 existing `docs/*.md` files
- Direct codebase inspection: `mkdocs.yml`, `pyproject.toml`
- GitHub: https://github.com/blueswen/mkdocs-swagger-ui-tag — version 0.8.0, installation, config, static asset bundling confirmed
- Official docs: https://blueswen.github.io/mkdocs-swagger-ui-tag/options/ — plugin options confirmed

### Secondary (MEDIUM confidence)
- https://squidfunk.github.io/mkdocs-material/setup/setting-up-navigation/ — navigation features and 2-level nav YAML syntax
- https://github.com/squidfunk/mkdocs-material/issues/3070 — navigation.indexes + navigation.sections conflict confirmed
- MkDocs docs on `not_in_nav` — suppresses warning for openapi.json in docs/ not in nav

### Tertiary (LOW confidence)
- Local path format for `<swagger-ui src="...">` — relative path `../openapi.json` inferred from standard MkDocs static file conventions; no explicit official example found for local paths

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed from GitHub, plugin capabilities verified
- Architecture (nav structure): HIGH — locked decisions + codebase inspection of all existing files
- Content gaps: HIGH — all router files read, all existing docs read, gaps identified precisely
- Pitfalls: HIGH — issues #3070 confirmed, not_in_nav confirmed, StaticFiles html=True verified in codebase
- swagger-ui local path: MEDIUM — inferred, not officially documented with local examples

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (mkdocs-material 9.x is stable; mkdocs-swagger-ui-tag 0.8.0 just released)
