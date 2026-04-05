# Phase 14: MkDocs Infrastructure - Research

**Researched:** 2026-04-04
**Domain:** MkDocs Material static site generation + FastAPI StaticFiles sub-path mounting
**Confidence:** HIGH (stack and patterns); MEDIUM (sub-path asset loading — requires live verification)

---

## Summary

This phase adds MkDocs Material documentation infrastructure to the ollog project. The core
challenge is not MkDocs itself — the tool is well-understood — but correctly serving the built
`site/` directory at the `/guide` sub-path from FastAPI so that Material's CSS and JS assets
load without 404 errors.

The critical technical insight is that MkDocs generates **relative or absolute** asset paths
depending on the `site_url` setting. When `site_url` is set to a sub-path (e.g., `http://localhost:8000/guide/`),
MkDocs generates absolute asset URLs anchored to that prefix, which means requests to
`/guide/assets/...` resolve correctly via FastAPI's `StaticFiles` mount at `/guide`. Without
`site_url`, generated asset paths resolve relative to the document root and 404 under a sub-path.

The stack is: `mkdocs-material==9.*` as a `[dependency-groups] dev` dependency, `uv run mkdocs build`
for the build step, `app.mount("/guide", StaticFiles(directory="site", html=True))` in FastAPI,
and `COPY site/ site/` in the Dockerfile. The `site/` directory is committed to the repo so the
Docker image never needs MkDocs installed.

**Primary recommendation:** Set `site_url: http://localhost:8000/guide/` in `mkdocs.yml`, mount
`StaticFiles(directory="site", html=True)` at `/guide` BEFORE the existing `/static` mount, and
verify asset loading manually after the first build.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mkdocs-material | `9.*` (latest 9.7.6 as of Apr 2026) | MkDocs theme + plugin suite | Official project requirement; most complete Material Design MkDocs theme |
| mkdocs | bundled with mkdocs-material | Static site generator | Pulled in transitively; no separate pin needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| starlette StaticFiles | bundled with fastapi | Serve built site/ directory | Already present in project via fastapi[standard] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| mkdocs-material | plain mkdocs with no theme | Less visual polish; project spec mandates Material |
| committing site/ to repo | building in Dockerfile | Adds MkDocs to production image; more complex multi-stage build |

**Installation (dev dependency only):**
```bash
uv add --dev "mkdocs-material==9.*"
```

This adds to `[dependency-groups] dev` in `pyproject.toml`, NOT to `[project.dependencies]` or
`[project.optional-dependencies]`. The `pip install .` step in the Dockerfile installs only
`[project.dependencies]`, so MkDocs will never be present in the production image.

---

## Architecture Patterns

### Recommended Project Structure
```
/                        # project root
├── mkdocs.yml           # MkDocs configuration
├── docs/                # Markdown source files
│   └── index.md         # Homepage (required)
├── site/                # Built output — committed to repo
│   ├── index.html
│   └── assets/
├── pyproject.toml       # mkdocs-material in [dependency-groups].dev
└── Dockerfile           # COPY site/ site/ added here
```

### Pattern 1: site_url for Sub-path Asset Resolution
**What:** MkDocs uses `site_url` to decide whether to emit relative or absolute asset URLs.
When `site_url` contains a sub-path, all asset href/src values in generated HTML are prefixed
with that sub-path (e.g., `/guide/assets/stylesheets/main.css` instead of `assets/stylesheets/main.css`).
**When to use:** Whenever the site is served under a path prefix, not at the domain root.
**Example:**
```yaml
# mkdocs.yml
site_name: ollog Guide
site_url: http://localhost:8000/guide/
theme:
  name: material
docs_dir: docs
site_dir: site
nav:
  - Home: index.md
```
Source: https://www.mkdocs.org/user-guide/configuration/ (site_url section)

### Pattern 2: FastAPI StaticFiles html=True at /guide
**What:** `html=True` tells Starlette's StaticFiles to serve `index.html` automatically when a
directory path is requested (e.g., `/guide/` serves `site/index.html`). Without `html=True`,
directory requests return 404.
**When to use:** Any time you serve a pre-built HTML site with an index.html.
**Example:**
```python
# app/main.py — add BEFORE the existing /static mount
app.mount("/guide", StaticFiles(directory="site", html=True), name="guide")
app.mount("/static", StaticFiles(directory="static"), name="static")
```
Source: https://www.starlette.io/staticfiles/ (html mode section)

### Pattern 3: Mount Order in FastAPI
**What:** `app.mount()` calls are evaluated in registration order. A StaticFiles mount at `/guide`
is a "sub-application" that intercepts all paths beginning with `/guide`. It must be registered
before any catch-all-style mounts. The existing `/static` mount is already scoped; order between
`/guide` and `/static` should not matter for correctness, but the project spec requires `/guide`
first to be safe.
**When to use:** Always validate mount order when adding new mounts.

### Anti-Patterns to Avoid
- **Omitting site_url:** Without `site_url` set to a sub-path, asset references in the built HTML
  are relative (e.g., `assets/stylesheets/main.css`), which resolves correctly only from
  `/guide/` but fails from `/guide/some-page/` because the browser interprets it relative to the
  current path depth.
- **Building in CI without committing site/:** The project spec mandates `site/` in the repo and
  copied into Docker. A CI-only build requires multi-stage Docker builds and more complexity.
- **Adding mkdocs-material to [project.dependencies]:** This installs MkDocs into the production
  Docker image unnecessarily, bloating the image.
- **No trailing slash on site_url:** `site_url: http://localhost:8000/guide` (no trailing slash)
  causes incorrect absolute URL generation for assets. Always include the trailing slash.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML documentation rendering | Custom Jinja2 templates for docs pages | mkdocs-material build pipeline | Material handles search, navigation, responsive layout, syntax highlighting |
| Sub-path asset rewriting | URL rewriting middleware | Correct site_url in mkdocs.yml | MkDocs handles this natively via site_url |
| Static file serving with index fallback | Custom route handler | StaticFiles(html=True) | Starlette handles index.html serving and 404.html fallback |

**Key insight:** The only real complexity is configuring `site_url` correctly. Everything else
(theme, search, navigation) is handled by mkdocs-material with no custom code.

---

## Common Pitfalls

### Pitfall 1: Assets 404 Under /guide Sub-path
**What goes wrong:** CSS, JS, and image assets return 404. The page loads but appears unstyled.
**Why it happens:** When `site_url` is not set (or set to a bare domain without sub-path), MkDocs
generates relative asset paths like `assets/stylesheets/main.css`. From `/guide/`, this resolves
correctly to `/guide/assets/...`. But from `/guide/some-page/`, the browser resolves it to
`/guide/some-page/assets/...` — which doesn't exist.
**How to avoid:** Set `site_url: http://localhost:8000/guide/` (with trailing slash). MkDocs will
emit absolute paths like `/guide/assets/stylesheets/main.css` that work from any depth.
**Warning signs:** Blank white page, 404s in browser DevTools Network tab for `.css` and `.js` files.

### Pitfall 2: /guide Returns 404 Instead of index.html
**What goes wrong:** Navigating to `http://localhost:8000/guide` or `http://localhost:8000/guide/`
returns a 404.
**Why it happens:** `StaticFiles` without `html=True` does not serve `index.html` for directory
paths. The `html=True` parameter is required.
**How to avoid:** Always use `StaticFiles(directory="site", html=True)`.
**Warning signs:** 404 on the root URL; direct requests to `site/index.html` work but `/guide` does not.

### Pitfall 3: mkdocs build --strict Fails on Warnings
**What goes wrong:** Build succeeds locally (warnings visible but ignored) but fails with
`--strict` because a plugin emits a deprecation warning or a nav entry references a missing file.
**Why it happens:** `--strict` converts any warning into a build error. Common triggers: deprecated
config keys, broken internal links, nav referencing a file that doesn't exist.
**How to avoid:** Scaffold all files referenced in the `nav:` section. Run `uv run mkdocs build --strict`
locally during setup, not just during CI.
**Warning signs:** `WARNING` lines in mkdocs output that don't fail a non-strict build.

### Pitfall 4: uv add Targets Wrong Dependency Section
**What goes wrong:** `mkdocs-material` ends up in `[project.dependencies]` (production) instead
of `[dependency-groups] dev`.
**Why it happens:** Using `pip install` or `uv add` without the `--dev` flag.
**How to avoid:** Always use `uv add --dev "mkdocs-material==9.*"`. Verify `pyproject.toml` after
adding to confirm placement.
**Warning signs:** Success criteria #3 fails — `mkdocs-material` appears in `[project.dependencies]`.

### Pitfall 5: site/ Not Present When Docker Image Builds
**What goes wrong:** `COPY site/ site/` in Dockerfile fails because `site/` hasn't been built
and committed yet.
**Why it happens:** The build step (`uv run mkdocs build --strict`) was not run before committing.
**How to avoid:** Run the build, verify `site/` was generated, commit it to the repo. The
Dockerfile COPY must come after the app code COPYs.
**Warning signs:** Docker build error: `COPY failed: file not found in build context`.

---

## Code Examples

### Minimal mkdocs.yml (verified pattern)
```yaml
# Source: https://squidfunk.github.io/mkdocs-material/getting-started/
site_name: ollog Guide
site_url: http://localhost:8000/guide/
theme:
  name: material
docs_dir: docs
site_dir: site
nav:
  - Home: index.md
```

### FastAPI mount (add before /static)
```python
# Source: https://www.starlette.io/staticfiles/
from fastapi.staticfiles import StaticFiles

# Mount /guide BEFORE /static
app.mount("/guide", StaticFiles(directory="site", html=True), name="guide")
app.mount("/static", StaticFiles(directory="static"), name="static")
```

### Dockerfile addition
```dockerfile
# After existing COPY lines, before EXPOSE
COPY site/ site/
```

### uv add command
```bash
# Source: https://docs.astral.sh/uv/concepts/projects/dependencies/
uv add --dev "mkdocs-material==9.*"
```

### Resulting pyproject.toml section
```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
    "mkdocs-material==9.*",
]
```

### Build and verify command
```bash
uv run mkdocs build --strict
# Produces: site/ directory
# Verify: site/index.html exists, site/assets/ exists
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pip install` dev deps in separate requirements-dev.txt | `[dependency-groups] dev` in pyproject.toml | PEP 735, uv adopted ~2024 | `uv add --dev` targets the right section automatically |
| Rebuilding docs in Dockerfile | Commit site/ to repo, COPY in Dockerfile | Established pattern | Simpler Dockerfile; no MkDocs in production |

**Deprecated/outdated:**
- `requirements-dev.txt`: The project already uses `[dependency-groups]` in pyproject.toml — add mkdocs-material there, not in a separate file.

---

## Open Questions

1. **site_url for production Docker Compose deployment**
   - What we know: `site_url` is used to generate asset paths at build time; it's baked into the built HTML
   - What's unclear: In Docker Compose, the app is accessed at `http://localhost:8000` — same as dev. But if ever deployed behind a reverse proxy with a different host, the baked-in `site_url` host would be wrong for canonical URLs (though asset paths would still work if the sub-path `/guide` is preserved)
   - Recommendation: For this phase, use `http://localhost:8000/guide/` which covers both local dev and Docker Compose. Document that production deployments behind a reverse proxy should rebuild with a production `site_url` if canonical URLs matter.

2. **uv.lock update after uv add --dev**
   - What we know: `uv add --dev` updates both `pyproject.toml` and `uv.lock`
   - What's unclear: The project's Dockerfile uses `pip install --no-cache-dir .` (not `uv sync`), so the lock file is not used during Docker build — the dev dependency does not leak into the image regardless
   - Recommendation: Confirm this by inspecting the Dockerfile after the change; no action needed beyond the standard `uv add --dev` workflow.

3. **docs/ content scope**
   - What we know: MKDOCS-03 requires scaffold Markdown files; no content is specified
   - What's unclear: What pages to include beyond `index.md`
   - Recommendation: Start with `index.md` only. Navigation can be extended in a future phase. Minimal nav prevents missing-file warnings in `--strict` mode.

---

## Sources

### Primary (HIGH confidence)
- https://www.mkdocs.org/user-guide/configuration/ — site_url behavior, use_directory_urls, --strict flag
- https://squidfunk.github.io/mkdocs-material/getting-started/ — installation command, version 9 confirmation
- https://docs.astral.sh/uv/concepts/projects/dependencies/ — uv add --dev targets [dependency-groups].dev
- https://www.starlette.io/staticfiles/ — html=True parameter behavior for StaticFiles

### Secondary (MEDIUM confidence)
- https://github.com/squidfunk/mkdocs-material/issues/2520 — site_url trailing slash and sub-path asset resolution details
- https://github.com/squidfunk/mkdocs-material/discussions/6784 — FastAPI + MkDocs sub-path asset path issues and root cause analysis
- https://fastapi.tiangolo.com/tutorial/static-files/ — StaticFiles mount behavior, mount order implications

### Tertiary (LOW confidence)
- PyPI mkdocs-material page — version 9.7.6 as latest in 9.x series (search result, not directly fetched)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — uv add --dev, mkdocs-material 9.*, StaticFiles(html=True) all verified with official docs
- Architecture: HIGH — mkdocs.yml structure, FastAPI mount pattern, Dockerfile COPY are all verified
- Sub-path asset loading: MEDIUM — site_url mechanism is well-documented, but the exact behavior with StaticFiles at /guide requires live verification after first build; multiple sources confirm the site_url trailing slash is the fix
- Pitfalls: HIGH — all pitfalls derived from official docs and primary sources

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (mkdocs-material 9.x is stable; FastAPI/Starlette StaticFiles API is stable)
