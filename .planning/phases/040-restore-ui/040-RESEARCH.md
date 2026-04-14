# Phase 40: Restore UI - Research

**Researched:** 2026-04-14
**Domain:** Jinja2 admin templates, HTMX file upload, CSS component classes, FastAPI route
**Confidence:** HIGH

## Summary

Phase 40 adds the `GET /admin/ui/restore` route and creates `templates/admin/restore.html` — the page shell that wraps the Phase 39 fragment templates. All backend POST endpoints already exist in `ui_router.py` (lines 262–386). No new CSS component classes are needed: `.btn`, `.btn-danger`, `.btn-secondary`, `.alert`, `.alert-error`, `.alert-success`, `.card`, `.card-header`, `.card-body`, `.card-title`, `.form-input`, `.nav-item`, `.nav-item-active` are all defined in `static/css/input.css` and compiled into `output.css`.

The Phase 39 fragment templates use six undeclared CSS classes: `modal-backdrop`, `modal-box`, `modal-title`, `modal-body`, `modal-actions`, and `form-control`. None of these exist in `input.css` or `output.css`. Phase 40 must add them to `input.css` and rebuild `output.css`. Without these classes the modal will have no layout or styling.

The cancel button in `password_modal.html` fires `hx-get="/admin/ui/restore"` with `hx-target="#restore-modal"` + `hx-swap="outerHTML"`. The GET route must therefore return a bare `<div id="restore-modal"></div>` (empty replacement) when it detects an HTMX request header, and the full `restore.html` page when it is a full-page request. This is the same dual-render pattern already used in the `/users` GET route.

**Primary recommendation:** Add GET route with dual-render pattern, add modal/form-control component classes to `input.css`, rebuild CSS, create `restore.html` mirroring `backup.html` structure with all three sidebar nav links.

## Standard Stack

### Core (already in use — no new installs)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | project version | Route registration, `Depends`, `Header` | Already used for all UI routes |
| Jinja2Templates | project version | Server-side HTML rendering | All pages use `TemplateResponse` |
| HTMX | project version | File upload, modal swap, cancel reset | Already loaded in base template |
| Tailwind CSS | 3.4.17 | Utility classes for new component styles | Project standard, `npm run build` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| HeroIcons v2 (inline SVG) | n/a | Nav icon for Restore link | Inline SVG, no install needed |

**Installation:** None required. All dependencies already present.

## Architecture Patterns

### Pattern 1: Admin page template structure (from `backup.html` and `users.html`)

Every admin page template:
1. Extends `base_app.html`
2. Sets `{% block active_page %}restore{% endblock %}` (page identifier string)
3. Sets `{% block sidebar_class %}dark:bg-surface-dark{% endblock %}` (same on all admin pages)
4. Overrides `{% block sidebar_nav %}` with ALL three nav links — Operators, Backup, Restore — applying `nav-item-active` only to the current page's link
5. Overrides `{% block sidebar_user %}` with the static Admin / Administrator block (same on all admin pages)
6. Overrides `{% block sidebar_logout %}` with the Admin logout link `/admin/ui/logout` (same on all admin pages)
7. Defines `{% block content %}` with the page body using `.card` layout

**Critical detail:** The admin pages do NOT use `{{ 'nav-item-active' if ap == 'X' else '' }}` template logic. They hard-code the active class on the correct link inside the `{% block sidebar_nav %}` override. This is verified in both `backup.html` (line 14: `class="nav-item nav-item-active"`) and `users.html` (line 9: `class="nav-item nav-item-active"`).

### Pattern 2: HTMX dual-render GET route (from `/users` route, `ui_router.py` lines 95-115)

```python
# Source: app/admin/ui_router.py lines 95-115
@ui_router.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    hx_request: Annotated[str | None, Header()] = None,
    _user: User = Depends(require_admin_cookie),
):
    users = await User.find_all().to_list()
    if hx_request:
        return templates.TemplateResponse(
            request, "admin/users_table.html", {"users": users, "error": None},
        )
    return templates.TemplateResponse(
        request, "admin/users.html", {"users": users, "error": None},
    )
```

The restore GET route must follow this same pattern. When `hx_request` is truthy (HTMX cancel button), it returns a bare `<div id="restore-modal"></div>` fragment. When falsy (full page load), it renders the full `restore.html`.

### Pattern 3: HTMX file upload form (from `templates/log/import.html` lines 23-26)

```html
<!-- Source: templates/log/import.html lines 23-26 -->
<form enctype="multipart/form-data"
      hx-post="/log/import"
      hx-target="#import-result"
      hx-encoding="multipart/form-data">
```

The restore upload form must use the same dual-attribute pattern: `enctype="multipart/form-data"` AND `hx-encoding="multipart/form-data"` — both are required for HTMX to correctly send the file.

### Pattern 4: Modal div wiring for HTMX swap

The page needs two target divs:
- `<div id="restore-result"></div>` — target for the upload form (`hx-target="#restore-result"`). The upload endpoint swaps in either `upload_error.html` (an `.alert-error` div) or `password_modal.html` (the `#restore-modal` div).
- `<div id="restore-modal"></div>` — initially empty. The `password_modal.html` fragment has `id="restore-modal"` so when it is swapped into `#restore-result`, it replaces `#restore-result`'s inner content. Then the cancel button's `hx-target="#restore-modal"` + `hx-swap="outerHTML"` replaces the entire modal div with `<div id="restore-modal"></div>` from the GET route.

**Critical design issue — target chain:** The upload form targets `#restore-result` with `hx-swap="innerHTML"` (default). The `password_modal.html` response has `id="restore-modal"` at its root. After the swap, `#restore-result` contains `<div id="restore-modal">...</div>`. The cancel button then targets `#restore-modal` with `hx-swap="outerHTML"`, replacing the modal div. This means the GET `/admin/ui/restore` cancel response must return `<div id="restore-modal"></div>` (not a full page).

### Recommended Project Structure (new files only)

```
templates/admin/
└── restore.html          # NEW: full page shell

app/admin/
└── ui_router.py          # MODIFY: add GET /restore route

static/css/
└── input.css             # MODIFY: add modal + form-control component classes

static/css/
└── output.css            # REBUILD: npm run build
```

### Anti-Patterns to Avoid

- **Using `{{ 'nav-item-active' if ap == 'restore' else '' }}` in sidebar_nav block:** Admin pages hard-code the active class — the base template's `ap` variable is irrelevant inside the overridden `{% block sidebar_nav %}`.
- **Omitting `enctype="multipart/form-data"` from the upload form:** HTMX's `hx-encoding` alone is not sufficient for file upload in all browsers.
- **Returning full page from GET /restore when HTMX cancel hits it:** The cancel button targets `#restore-modal` with `outerHTML` swap — returning a full HTML page would corrupt the DOM.
- **Adding inline `style=""` for modal backdrop blur:** The Phase 39 templates use `.modal-backdrop` and `.modal-box` classes. Styling must go in `input.css` as `@layer components` entries so Tailwind generates them in `output.css`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSS-only modal overlay | Custom `<style>` tags in template | `@layer components` entries in `input.css` + `npm run build` | Project uses compiled Tailwind — inline styles bypass dark mode, break consistency |
| HTMX file upload wiring | Custom JS FormData handler | `hx-encoding="multipart/form-data"` + `enctype="multipart/form-data"` | Already proven in `import.html` |
| Active state detection | Jinja2 conditional in overridden block | Hard-coded `nav-item-active` on correct `<a>` | Matches the established pattern in `backup.html` and `users.html` |

## Common Pitfalls

### Pitfall 1: Missing modal CSS classes
**What goes wrong:** `modal-backdrop`, `modal-box`, `modal-title`, `modal-body`, `modal-actions`, `form-control`, `form-group` are used in Phase 39 fragment templates but are not defined anywhere in `input.css` or compiled into `output.css`. The modal will render with no layout or visual styling.
**Why it happens:** Phase 39 created the templates with forward-declared class names, expecting Phase 40 to add the definitions.
**How to avoid:** Add all six classes as `@layer components` entries in `input.css` before running `npm run build`.
**Warning signs:** Modal appears with no backdrop, no centering, no box styling.

### Pitfall 2: Cancel button breaks with full-page response
**What goes wrong:** If `GET /admin/ui/restore` returns a full HTML page unconditionally, the cancel button (which fires HTMX and targets `#restore-modal` with `outerHTML` swap) will inject an entire HTML document into the middle of the page body.
**Why it happens:** The cancel button is an HTMX request with a specific swap target, not a page navigation.
**How to avoid:** Check `hx_request` header in the GET route. When truthy, return only `<div id="restore-modal"></div>`.
**Warning signs:** Page becomes visually broken after clicking Cancel; dev tools show nested `<html>` tags.

### Pitfall 3: Sidebar nav shows only two links
**What goes wrong:** Copying `backup.html` sidebar verbatim gives only Operators + Backup links.
**Why it happens:** The Restore nav link didn't exist when those pages were written.
**How to avoid:** Add the Restore link to ALL THREE admin pages: `users.html`, `backup.html`, and the new `restore.html`.
**Warning signs:** Restore page accessible via URL but unreachable from sidebar navigation.

### Pitfall 4: backdrop-blur utility not compiled
**What goes wrong:** Using Tailwind utility class `backdrop-blur-sm` in a template won't work — it is not currently present in `output.css` (no template uses it yet, so Tailwind's content scanner hasn't generated it).
**Why it happens:** Tailwind only includes classes it finds in scanned template files.
**How to avoid:** Use raw CSS in `@layer components` for backdrop-filter: `backdrop-filter: blur(8px);` and `-webkit-backdrop-filter: blur(8px);` (same pattern as `.glass-card` in `input.css` lines 182-186).
**Warning signs:** Backdrop has no blur in Safari even though it appears correct in Chrome (Safari requires `-webkit-` prefix AND literal pixel values, not CSS variable references — see `input.css` comments lines 177-179).

## Code Examples

### GET /restore route (to add to ui_router.py)

```python
# Pattern: mirrors /users route (ui_router.py lines 95-115)
# Location: add after /backup/download route, before the existing /restore/upload POST
@ui_router.get("/restore", response_class=HTMLResponse)
async def restore_page(
    request: Request,
    hx_request: Annotated[str | None, Header()] = None,
    _user: User = Depends(require_admin_cookie),
):
    """Render restore page (full) or empty modal div (HTMX cancel)."""
    if hx_request:
        # Cancel button fires hx-get="/admin/ui/restore" targeting #restore-modal outerHTML
        return HTMLResponse(content='<div id="restore-modal"></div>')
    return templates.TemplateResponse(request, "admin/restore.html", {})
```

### Sidebar nav block for restore.html

```html
{# In restore.html — all three links, restore is active #}
{% block sidebar_nav %}
<a href="/admin/ui/users" class="nav-item">
  <svg class="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
  </svg>
  Operators
</a>
<a href="/admin/ui/backup" class="nav-item">
  <svg class="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
  </svg>
  Backup
</a>
<a href="/admin/ui/restore" class="nav-item nav-item-active">
  <svg class="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.731l3.181 3.182m0-4.991v4.99" />
  </svg>
  Restore
</a>
{% endblock %}
```

### Upload form wiring in restore.html content block

```html
{# In restore.html {% block content %} #}
<form enctype="multipart/form-data"
      hx-post="/admin/ui/restore/upload"
      hx-target="#restore-result"
      hx-encoding="multipart/form-data">
  <!-- file input here -->
  <input type="file" name="file" accept=".gz" required>
  <button type="submit" class="btn-primary">Upload Backup</button>
</form>

<div id="restore-result"></div>
<div id="restore-modal"></div>
```

### Modal component classes to add to input.css

```css
/* Add inside @layer components { ... } in static/css/input.css */

/* Modal overlay */
.modal-backdrop {
  @apply fixed inset-0 bg-black/50 z-40;
  -webkit-backdrop-filter: blur(4px);
  backdrop-filter: blur(4px);
}

/* Modal box */
.modal-box {
  @apply fixed inset-0 z-50 flex items-center justify-center p-4;
}

/* Inner modal content container */
.modal-box > * {
  @apply bg-surface-light dark:bg-surface-dark rounded-xl shadow-2xl p-6 w-full max-w-md;
}

/* Modal typography */
.modal-title {
  @apply text-lg font-semibold text-gray-900 dark:text-white mb-2;
}
.modal-body {
  @apply text-sm text-gray-600 dark:text-gray-400 mb-4;
}

/* Modal action buttons row */
.modal-actions {
  @apply flex gap-3 justify-end mt-4;
}

/* Form elements used in modal */
.form-group {
  @apply mb-4;
}
.form-control {
  @apply form-input;
}
```

**Note:** The `modal-backdrop` and `modal-box` approach above needs careful review. Looking at `password_modal.html` (line 1-37), the structure is:
- `<div id="restore-modal">` (outer wrapper, also the HTMX swap target)
  - `<div class="modal-backdrop">` (overlay / dimmer)
  - `<div class="modal-box">` (centered content box)

This means `modal-backdrop` should be a fixed full-screen dimmer, and `modal-box` should be the centered content wrapper. The two divs are siblings, not nested — `modal-box` must handle its own fixed positioning and centering.

### Updated (structurally accurate) modal CSS

```css
/* modal-backdrop: full-screen dim layer behind the box */
.modal-backdrop {
  @apply fixed inset-0 bg-black/50 z-40;
  -webkit-backdrop-filter: blur(4px);
  backdrop-filter: blur(4px);
}

/* modal-box: centered content panel above backdrop */
.modal-box {
  @apply fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50
         bg-surface-light dark:bg-surface-dark rounded-xl shadow-2xl p-6 w-full max-w-md;
}
```

### Restore link to add to users.html and backup.html sidebar_nav blocks

```html
{# Add after the Backup <a> in users.html and backup.html sidebar_nav blocks #}
<a href="/admin/ui/restore" class="nav-item">
  <svg class="w-6 h-6 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.731l3.181 3.182m0-4.991v4.99" />
  </svg>
  Restore
</a>
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Sidebar active state via Jinja2 `ap` variable | Hard-coded `nav-item-active` in overridden block | Admin pages bypass base template's nav logic entirely |
| CSS Modules / separate modal library | Component classes in `@layer components` | Single compiled file, no extra JS bundle |

## Open Questions

1. **Modal structure alignment with `password_modal.html`**
   - What we know: `modal-backdrop` and `modal-box` are sibling divs inside `#restore-modal`. `modal-backdrop` is first (visually behind), `modal-box` is second (visually on top).
   - What's unclear: Whether `modal-box` should use `position: fixed` centering or if `#restore-modal` itself should be a flex container. The CSS must match the sibling structure.
   - Recommendation: Use fixed positioning on both (`modal-backdrop` full-screen, `modal-box` centered via `top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2`). This is the standard approach and works without adding `position: relative` to the parent.

2. **`form-group` label styling**
   - What we know: `password_modal.html` uses `<div class="form-group">` wrapping a `<label>` and `<input class="form-control">`.
   - What's unclear: Whether `form-group` needs a bottom margin only or also label styling.
   - Recommendation: `form-group` = `@apply mb-4;`. The `<label>` inside it needs no special class (or use `form-label` which is already defined) — but `password_modal.html` uses bare `<label>`, so `form-group` should add label styling via descendant selector or just use `mb-4`.

3. **`restore_success.html` and `restore_failure.html` as swap targets**
   - What we know: These are returned by `/restore/confirm` and target `#restore-modal` with `hx-swap="outerHTML"`. The alert divs don't have `id="restore-modal"`, so after swap the `#restore-modal` element is gone from the DOM.
   - What's unclear: Whether this is intentional (modal dismissed, result shown inside the card) or if the alerts should be wrapped in `<div id="restore-modal">`.
   - Recommendation: This is intentional per Phase 39's design. The result replaces the modal entirely. Phase 40 should not modify Phase 39 fragment templates.

## Sources

### Primary (HIGH confidence)
- Direct file reads — `templates/admin/backup.html`, `templates/admin/users.html`, `templates/base_app.html`
- Direct file reads — all 5 files in `templates/admin/restore/`
- Direct file reads — `app/admin/ui_router.py` (complete)
- Direct file reads — `static/css/input.css` (complete component class inventory)
- Direct file reads — `static/css/output.css` (grep confirms no modal/form-control classes compiled)
- Direct file reads — `tailwind.config.js`, `package.json`

### Secondary (MEDIUM confidence)
- HeroIcons v2 `arrow-path` outline SVG path — standard HeroIcons path data, widely documented
- Safari backdrop-filter prefix requirement — documented in `input.css` lines 177-179 with GitHub issue references

## Metadata

**Confidence breakdown:**
- Route pattern: HIGH — copied directly from existing `/users` route
- Template structure: HIGH — copied directly from `backup.html` and `users.html`
- Missing CSS classes: HIGH — grep confirmed 0 matches in both `input.css` and `output.css`
- Modal CSS values: MEDIUM — structural inference from template markup; exact pixel values are implementation choices
- HeroIcons arrow-path path: MEDIUM — standard published path, unverified against live CDN today

**Research date:** 2026-04-14
**Valid until:** 2026-05-14 (stable codebase, no fast-moving dependencies)
