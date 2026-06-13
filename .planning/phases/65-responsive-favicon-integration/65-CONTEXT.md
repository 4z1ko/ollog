# Phase 65: Responsive Favicon Integration - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 65 adds favicon support across ollog web surfaces using the existing `favicon/favicon.ico` bundle as the source. The phase must make the favicon available to operator pages, admin pages, and the MkDocs `/guide` pages without changing application behavior, layout, authentication, HTMX partials, or mobile UI.

</domain>

<decisions>
## Implementation Decisions

### Static Path
- **D-01:** Use the existing `/static` serving pattern. Copy the favicon files needed for this phase into `static/favicon/`, rather than adding a new `/favicon` mount.
- **D-02:** The operator app and admin app already mount `/static`, so downstream planning should prefer shared static files over separate app-specific routing.

### Metadata Set
- **D-03:** Add ICO-only browser metadata for app pages: one shared `<link rel="icon" href="/static/favicon/favicon.ico">` in `templates/base.html`.
- **D-04:** Do not add PNG, Apple touch icon, or web manifest tags to the app page head in this phase, even though the source bundle contains those files.

### Guide Coverage
- **D-05:** Include MkDocs `/guide` pages in this phase. Planning should determine the least-churn MkDocs-compatible way to give docs pages the same favicon and rebuild `site/` if generated output changes.
- **D-06:** Keep the favicon based on `favicon/favicon.ico` for both app pages and guide pages.

### the agent's Discretion
- The agent may choose the exact file-copy mechanics for `static/favicon/` as long as `favicon/favicon.ico` remains the source of truth and the implementation is committed intentionally.
- The agent may choose the MkDocs Material favicon wiring mechanism after checking the existing `mkdocs.yml` and local docs build conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and Requirements
- `.planning/REQUIREMENTS.md` — v3.4 favicon requirements `FAV-01` through `FAV-07`.
- `.planning/ROADMAP.md` — Phase 65 goal, dependencies, requirements, and success criteria.
- `.planning/research/v3.4-favicon-page-scan.md` — template/page scan and favicon asset inventory.

### Existing Code
- `templates/base.html` — shared page head; favicon metadata should be added here for operator/admin app pages.
- `templates/base_app.html` — app shell extends `base.html`; confirms app pages inherit shared head metadata.
- `app/main.py` — operator app `/static` and `/guide` mounts.
- `app/admin_main.py` — admin app `/static` mount.
- `mkdocs.yml` — MkDocs Material configuration for `/guide` output.
- `favicon/favicon.ico` — source favicon requested by the user.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `favicon/favicon.ico`: existing source icon bundle, verified as an ICO file with multiple embedded icon sizes.
- `favicon/` bundle: includes PNG touch/manifest assets, but user chose ICO-only metadata for app pages.
- `/static` mounts: both app entry points already expose the `static/` directory.

### Established Patterns
- `templates/base.html` owns the `<head>` for login pages and all pages extending `base_app.html`.
- `templates/base_app.html` extends `base.html`, so full-page operator and admin templates should inherit one favicon link automatically.
- HTMX fragments are partial templates and should not receive standalone `<head>` metadata.
- MkDocs output is committed under `site/` and served at `/guide` through `StaticFiles(directory="site", html=True)`.

### Integration Points
- Add app-page favicon metadata in `templates/base.html`.
- Place served favicon asset under `static/favicon/favicon.ico`.
- Add guide favicon wiring through `mkdocs.yml` or the existing MkDocs source/build path, then rebuild `site/` if needed.

</code_context>

<specifics>
## Specific Ideas

- User explicitly chose `favicon/favicon.ico` as the favicon basis.
- User chose `/static/favicon/...` instead of adding new FastAPI static mounts.
- User chose ICO-only app metadata instead of the full responsive web manifest bundle.
- User chose to include MkDocs `/guide` favicon coverage.

</specifics>

<deferred>
## Deferred Ideas

- Full responsive app metadata using PNG icons, Apple touch icon, and web manifest remains out of scope for app pages in this phase.
- Dynamic per-operator or environment-specific favicon variants remain future work.

</deferred>

---

*Phase: 65-Responsive Favicon Integration*
*Context gathered: 2026-06-13*
