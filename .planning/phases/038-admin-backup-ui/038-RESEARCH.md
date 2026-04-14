# Phase 38: Admin Backup UI - Research

**Researched:** 2026-04-13
**Domain:** FastAPI Jinja2 UI — admin page + sidebar nav + file download
**Confidence:** HIGH

## Summary

Phase 38 is a pure UI-wiring task. The backend download endpoint already exists (`GET /admin/ui/backup/download` with `FileResponse`, auth via `require_admin_cookie`). The work is: (1) add a sidebar nav link in `backup.html`, (2) create `backup.html` following the `users.html` pattern exactly, and (3) register a `GET /admin/ui/backup` route in `ui_router.py`. No new CSS classes are needed — every token required (`card`, `card-header`, `card-title`, `card-body`, `btn-primary`, `nav-item`, `nav-item-active`) is already compiled into `static/css/output.css`. No `npm run build` is required.

The critical architecture constraint is well-supported by the codebase: the download anchor must be a plain `<a href="/admin/ui/backup/download" class="btn-primary">` with **no** `hx-*` attributes. HTMX silently discards binary responses; browser-native anchor navigation handles the file save dialog correctly.

**Primary recommendation:** Model `backup.html` entirely on `users.html`. Override `{% block sidebar_nav %}` to add both Operators and Backup links (Backup active). The page route is trivially simple — no query parameters, no form processing, one Depends call.

## Standard Stack

### Core (already present in the project)
| Component | Location | Purpose |
|-----------|----------|---------|
| `FastAPI` + `APIRouter` | `app/admin/ui_router.py` | Route registration for `/admin/ui/*` |
| `Jinja2Templates` | `app/admin/ui_router.py` (`templates = Jinja2Templates(directory="templates")`) | HTML rendering |
| `require_admin_cookie` | `app/auth/dependencies.py` | Cookie-JWT auth guard for admin UI routes |
| Tailwind component tokens | `static/css/input.css` + compiled `static/css/output.css` | All visual classes |

No new dependencies. No installation needed.

## Architecture Patterns

### Template Inheritance Chain

```
base.html
  └── base_app.html   (sidebar layout, JS, theme toggle)
        └── admin/users.html    ← pattern to follow
        └── admin/backup.html   ← NEW (follows users.html exactly)
```

### How Admin Pages Override the Sidebar

Admin pages do **not** use the `active_page` / `ap ==` conditional in `base_app.html`. They override `{% block sidebar_nav %}` entirely with a self-contained nav block. This is the pattern from `users.html`:

```html
{% block sidebar_nav %}
<a href="/admin/ui/users"
   class="nav-item">           {# or nav-item-active when on users page #}
  <!-- SVG icon -->
  Operators
</a>
{% endblock %}
```

For `backup.html`, the `sidebar_nav` block must include **both** nav items — Operators (inactive) and Backup (active). This is the only way to render a two-item admin sidebar without modifying `users.html`.

### Recommended Project Structure (no changes)

```
templates/
└── admin/
    ├── login.html
    ├── users.html          (existing — no modification needed)
    ├── users_table.html    (existing — no modification needed)
    └── backup.html         ← NEW (only new file)

app/admin/
└── ui_router.py            ← ADD one route
```

### Pattern 1: Admin page route (from ui_router.py)

The `users_page` handler is the model:

```python
@ui_router.get("/backup", response_class=HTMLResponse)
async def backup_page(
    request: Request,
    _user: User = Depends(require_admin_cookie),
):
    """Render the admin backup page."""
    return templates.TemplateResponse(
        request,
        "admin/backup.html",
        {},
    )
```

No context variables are needed beyond the request (Jinja2 templates have access to `request` automatically via the first positional arg).

### Pattern 2: backup.html template structure

Model: `templates/admin/users.html`. Key blocks to override:

| Block | Value |
|-------|-------|
| `{% block title %}` | `Backup — ollog Admin` |
| `{% block active_page %}` | `backup` (unused by admin sidebar_nav override, but harmless) |
| `{% block sidebar_class %}` | `dark:bg-surface-dark` (same as users.html) |
| `{% block sidebar_nav %}` | Both Operators and Backup links; Backup has `nav-item-active` |
| `{% block sidebar_user %}` | Admin user badge (copy from users.html verbatim) |
| `{% block sidebar_logout %}` | Logout link (copy from users.html verbatim) |
| `{% block content %}` | Single `.card` with download button |

### Pattern 3: Plain anchor download button (LOCKED)

```html
<!-- Source: phase 38 architecture decision, confirmed against ui_router.py -->
<a href="/admin/ui/backup/download" class="btn-primary">
  <!-- optional SVG icon -->
  Download Backup
</a>
```

No `hx-get`, `hx-post`, `hx-boost`, or any other `hx-*` attribute. The browser navigates directly to the endpoint; `FileResponse` with `Content-Disposition: attachment` triggers the OS file save dialog. HTMX is on the page (loaded in `base.html`) but only intercepts XHR/fetch requests — a plain anchor causes a standard browser navigation that HTMX does not intercept.

### Anti-Patterns to Avoid

- **Adding `hx-get` to the download anchor:** HTMX intercepts the response, tries to parse binary gzip as HTML, silently discards it. No file save dialog appears. The endpoint exists and works; the anchor must be plain.
- **Modifying `users.html` sidebar_nav to add the Backup link:** `users.html` hardcodes `nav-item-active` directly on the Operators link (not conditionally). If you add Backup there, both pages would look right except users.html would show Backup as inactive. This is acceptable but fragile. Cleaner: each page owns its own sidebar_nav block.
- **Creating a new CSS class:** All needed tokens are already in `output.css`. Adding `dark:` utility classes or any new Tailwind utility to `backup.html` requires `npm run build`. Sticking to existing component tokens (`.card`, `.btn-primary`, etc.) avoids this entirely.
- **Adding `backup.html` to a different templates subdirectory:** Templates directory is flat at `templates/admin/`. Follow this convention.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Auth guard | Custom cookie parsing | `Depends(require_admin_cookie)` |
| File download | Streaming response handler | `FileResponse` (already in `/backup/download`) |
| CSS styling | New utility classes | Existing `.card`, `.btn-primary`, `.card-header`, `.card-title`, `.card-body` |

## Common Pitfalls

### Pitfall 1: HTMX intercepts the download anchor
**What goes wrong:** Developer adds `hx-get` (or `hx-boost` on a parent element) to the download link. Browser makes an XHR to the endpoint; HTMX receives the binary gzip response and either errors silently or tries to swap it as HTML. No file dialog appears.
**Why it happens:** HTMX's default `hx-boost` on a parent `<body>` or `<main>` would boost all anchors. In this project `hx-boost` is NOT applied globally (verified in `base_app.html` — no `hx-boost` on body or main). So a plain `<a href>` is safe.
**How to avoid:** Use a plain `<a>` with no `hx-*` attributes. Confirmed safe by inspecting `base_app.html` — no `hx-boost` at the page level.
**Warning signs:** Download button click produces no OS dialog; network tab shows XHR request to `/admin/ui/backup/download`.

### Pitfall 2: New Tailwind utility classes require rebuild
**What goes wrong:** Developer adds a Tailwind utility class that isn't already in `output.css` (e.g., a new `dark:` variant or a one-off color). The class silently has no effect.
**Why it happens:** Tailwind purges unused classes at build time. `output.css` only contains classes that appeared as complete literal strings in `./templates/**/*.html` at the last build.
**How to avoid:** Use only existing component tokens (`.card`, `.btn-primary`, `.card-header`, `.card-title`, `.card-body`, `.nav-item`, `.nav-item-active`). These are already compiled. No `npm run build` needed.
**Warning signs:** Style applied in source template has no visual effect; class missing from `output.css`.

### Pitfall 3: Forgetting `require_admin_cookie` on the page route
**What goes wrong:** `GET /admin/ui/backup` renders without auth, leaking the backup page to unauthenticated users.
**Why it happens:** The download endpoint at `/backup/download` already has `Depends(require_admin_cookie)`, but a careless copy of the login route (which intentionally has no auth dependency) could omit it from the page route.
**How to avoid:** Follow the `users_page` handler signature exactly — `_user: User = Depends(require_admin_cookie)`.

### Pitfall 4: `sidebar_nav` block shows wrong active state
**What goes wrong:** On the backup page, "Operators" nav item is shown as active instead of "Backup".
**Why it happens:** Copy-paste from `users.html` sidebar_nav without updating which link gets `nav-item-active`.
**How to avoid:** In `backup.html`'s `sidebar_nav` block, Operators link gets `class="nav-item"` (no active) and Backup link gets `class="nav-item nav-item-active"`.

## Code Examples

### Complete route addition (ui_router.py)

```python
# Source: pattern from existing users_page handler in app/admin/ui_router.py
@ui_router.get("/backup", response_class=HTMLResponse)
async def backup_page(
    request: Request,
    _user: User = Depends(require_admin_cookie),
):
    """Render the admin backup page."""
    return templates.TemplateResponse(
        request,
        "admin/backup.html",
        {},
    )
```

This goes in the `# Backup download` section of `ui_router.py`, above the existing `backup_download` endpoint.

### sidebar_nav block for backup.html

```html
{% block sidebar_nav %}
<a href="/admin/ui/users"
   class="nav-item">
  <svg class="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
  </svg>
  Operators
</a>
<a href="/admin/ui/backup"
   class="nav-item nav-item-active">
  <svg class="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
  </svg>
  Backup
</a>
{% endblock %}
```

Note: The SVG path above is the HeroIcons "circle-stack" (database) icon — appropriate for backup. Any HeroIcons outline icon works.

### content block for backup.html

```html
{% block content %}
<div class="max-w-5xl mx-auto space-y-6">

  <!-- Page header -->
  <div>
    <h1 class="text-xl font-bold text-gray-900 dark:text-white">Backup</h1>
    <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
      Download a full MongoDB backup of all operator data
    </p>
  </div>

  <!-- Download card -->
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">Download Backup</h2>
    </div>
    <div class="card-body">
      <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Creates a compressed backup of the database and downloads it as a .gz file.
      </p>
      <a href="/admin/ui/backup/download" class="btn-primary">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
        </svg>
        Download Backup
      </a>
    </div>
  </div>

</div>
{% endblock %}
```

## File Change Map

| File | Change Type | What |
|------|-------------|------|
| `app/admin/ui_router.py` | Modify | Add `GET /backup` route handler above existing `backup_download` |
| `templates/admin/backup.html` | Create | New page template (no existing file) |
| `static/css/output.css` | None | No rebuild needed — all tokens already compiled |
| `templates/admin/users.html` | None | Not modified — backup page owns its own sidebar_nav |

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Inline `style=` attributes | Apple component tokens (`.card`, `.btn-primary`) | All styling via CSS classes only |
| HTMX for file download | Plain `<a href>` anchor | Browser handles binary responses correctly |
| Global `active_page` conditional | Per-page `sidebar_nav` block override | Admin pages own their entire sidebar nav |

## Open Questions

None. All architecture decisions are locked by the phase description. All implementation patterns are verified by reading the actual source files.

## Sources

### Primary (HIGH confidence)
- `/Users/royco/ollog/app/admin/ui_router.py` — exact handler signatures, route prefixes, auth dependencies, FileResponse usage
- `/Users/royco/ollog/app/auth/dependencies.py` — `require_admin_cookie` implementation and signature
- `/Users/royco/ollog/templates/admin/users.html` — sidebar_nav block pattern, block overrides, component token usage
- `/Users/royco/ollog/templates/base_app.html` — sidebar block structure, `active_page` / `ap` pattern, confirmed no `hx-boost` on body/main
- `/Users/royco/ollog/static/css/input.css` — all component token definitions (`.card`, `.btn-primary`, `.card-header`, `.card-title`, `.card-body`, `.nav-item`, `.nav-item-active`)
- `/Users/royco/ollog/static/css/output.css` — confirmed all required tokens are compiled (grep verified)
- `/Users/royco/ollog/tailwind.config.js` — content glob is `./templates/**/*.html`; confirms new backup.html will be scanned on next build
- `/Users/royco/ollog/package.json` — build script confirmed: `npm run build` compiles input.css to output.css

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified by reading actual source files
- Architecture: HIGH — verified exact handler pattern from ui_router.py, confirmed base_app.html block structure
- Pitfalls: HIGH — verified by reading base_app.html (no hx-boost), output.css (tokens compiled), users.html (active state pattern)

**Research date:** 2026-04-13
**Valid until:** Stable — changes only if admin UI architecture changes
