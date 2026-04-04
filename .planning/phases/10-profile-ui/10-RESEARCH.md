# Phase 10: Profile UI - Research

**Researched:** 2026-04-04
**Domain:** FastAPI + Jinja2 + HTMX UI patterns (server-rendered HTML, cookie auth, inline updates)
**Confidence:** HIGH — all findings come from direct codebase inspection of the existing working implementation

## Summary

Phase 10 adds a profile settings page at `/log/profile` to the existing log UI. The codebase has a clear, consistent pattern for all existing log UI pages: extend `base.html`, render a nav bar, use HTMX for inline updates without full-page reloads, and protect routes with `get_current_user_cookie` or `get_current_operator_callsign_cookie` dependencies. This pattern is already established for the QSO form, log view, and ADIF import — the profile page is a fourth instance of the same pattern.

The profile data model is fully defined: `ProfileResponse` and `ProfileUpdateRequest` schemas exist in `app/profile/schemas.py`, and `update_profile()` service is in `app/profile/service.py`. For the UI routes, there is no need to call the API endpoint over HTTP — the UI routes can call the service function directly, exactly as the QSO submit route does with QSO services.

HTMX 2.0.4 is already loaded globally in `base.html`. The established pattern for inline confirmations is to return a small HTML partial that gets swapped into a target div (see `qso_result.html`). The profile POST route should follow the same pattern: return `200 OK` with a success partial into a `#profile-result` div.

**Primary recommendation:** Add `GET /log/profile` and `POST /log/profile` routes to `app/qso/ui_router.py` (the existing log UI router), create `templates/log/profile.html`, and add a `Profile` nav link to `form.html`, `log.html`, and `import.html` following the exact nav pattern already in those files.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | Route handling, form parsing, deps | Already the web framework |
| Jinja2 | existing | HTML templating via `Jinja2Templates` | Already wired in `ui_router.py` |
| HTMX | 2.0.4 | Inline form submission / partial swap | Already in `base.html` globally |
| Beanie/Motor | existing | User document access | Already used for all auth/profile ops |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `app/profile/service.py` | existing | `update_profile()` — applies partial updates, auto-derives lat/lon | Call directly from POST handler |
| `app/profile/schemas.py` | existing | `ProfileUpdateRequest`, `ProfileResponse` | For field validation in POST |
| `app/auth/dependencies.py` | existing | `get_current_user_cookie` — returns full `User` doc | Use for GET (need all profile fields, not just callsign) |

## Architecture Patterns

### Existing Route Pattern (HIGH confidence)

All log UI GET routes follow this exact structure:

```python
@ui_router.get("/import", response_class=HTMLResponse)
async def import_page(
    request: Request,
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    return templates.TemplateResponse(
        request,
        "log/import.html",
        {"callsign": callsign},
    )
```

For the profile GET, use `get_current_user_cookie` instead of `get_current_operator_callsign_cookie` because the template needs all profile field values to pre-populate the form, not just the callsign string.

### Profile GET Pattern

```python
@ui_router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    user: User = Depends(get_current_user_cookie),
):
    return templates.TemplateResponse(
        request,
        "log/profile.html",
        {"user": user, "callsign": user.callsign},
    )
```

### Profile POST Pattern

POST should accept form fields, call `update_profile()` directly (not via HTTP to `/api/profile`), then return a small success partial swapped into `#profile-result`. Must return HTTP 200 always (HTMX 2.x does not swap on 4xx responses — confirmed from existing code comments).

```python
@ui_router.post("/profile", response_class=HTMLResponse)
async def profile_submit(
    request: Request,
    # form fields as Annotated[Optional[str], Form()] = None
    user: User = Depends(get_current_user_cookie),
):
    updates = {k: v for k, v in {...}.items() if v is not None}
    await update_profile(user, updates)
    return templates.TemplateResponse(
        request,
        "log/profile_result.html",   # or inline HTML response
        {"success": True},
    )
```

### HTMX Inline Submit Pattern (HIGH confidence)

The QSO form demonstrates the pattern:
- Form has `hx-post="/log/profile"`, `hx-target="#profile-result"`, `hx-swap="innerHTML"`
- Handler returns 200 always
- A `#profile-result` div below the form receives the partial

From `form.html`:
```html
<form id="qso-form"
      hx-post="/log/qsos"
      hx-target="#qso-result"
      hx-swap="innerHTML">
  ...
</form>
<div id="qso-result"></div>
```

### Nav Pattern (HIGH confidence)

All three existing log pages (`form.html`, `log.html`, `import.html`) have an identical inline nav block. The nav is not in a shared partial — it is copy-pasted into each template. Adding a Profile link means editing all three files. Example from `form.html`:

```html
<nav>
  <h1>ollog</h1>
  <div style="display:flex;gap:1rem;align-items:center;">
    <span>Logged in as <strong>{{ callsign }}</strong></span>
    <a href="/log/view">Log View</a>
    <a href="/log/import">Import</a>
    <a href="/log/export">Export</a>
    <a href="/log/logout">Logout</a>
  </div>
</nav>
```

Profile link goes between Export and Logout (consistent placement), or after Export as `<a href="/log/profile">Profile</a>`.

### Cookie Auth Pattern (HIGH confidence)

- `get_current_user_cookie` — returns full `User` Beanie document; use when POST handler needs profile write access
- `get_current_operator_callsign_cookie` — returns just the callsign string; use when only callsign needed
- 401/403 from `/log/*` paths are automatically redirected to `/log/login` by the app-level exception handler in `main.py` — no special handling needed in new routes

### Template Extension Pattern

All log templates follow:
```html
{% extends "base.html" %}
{% block title %}ollog - [Page Name]{% endblock %}
{% block content %}
...
{% endblock %}
```

`base.html` loads HTMX globally. No additional script includes needed in `profile.html`.

### Profile Field Labeling

The `User` model has:
- `callsign` — the operator's personal callsign, stored at account creation, sourced from JWT, never editable via profile form
- `station_callsign` — optional club/event callsign, set in `ProfileUpdateRequest`

The form must make this distinction explicit. Suggested HTML pattern:
```html
<label>
  OPERATOR (your callsign — read-only)
  <input type="text" value="{{ user.callsign }}" disabled>
  <small>Your personal call. To change, contact admin.</small>
</label>
<label>
  STATION_CALLSIGN (optional club or event call)
  <input type="text" name="station_callsign" value="{{ user.station_callsign or '' }}">
  <span title="Used when operating as a club or event station. Leave blank for personal calls.">?</span>
</label>
```

Or use the HTML `title` attribute for the tooltip (no JS needed).

### Direct Service Call vs. HTTP API Call

Do NOT make an internal HTTP request to `PATCH /api/profile` from the UI route. The existing pattern calls service functions directly:
- `submit_qso` calls `build_qso_dict()` and `find_duplicate()` directly
- `import_submit` calls `process_import()` directly

For profile POST: call `update_profile(user, updates)` directly from `app.profile.service`.

### Handling blank station_callsign

`ProfileUpdateRequest.normalize_station_callsign` converts empty string to `None`. The UI form POST handler must handle this: when the user clears the station_callsign field, the form sends an empty string — the handler should pass it through to `ProfileUpdateRequest` validation, which normalizes it to `None`, preventing empty-string storage.

### `tx_pwr` field type

`tx_pwr` is `Optional[float]` in both `User` and `ProfileUpdateRequest`. The form input should be `type="number"` or `type="text"`. The POST handler must parse it from the form string to float (or pass to `ProfileUpdateRequest` for coercion). Pydantic will coerce `"100"` → `100.0` if using schema validation.

### Registration in main.py

The new routes are added to `ui_router` in `app/qso/ui_router.py` — no change to `main.py` needed because `qso_ui_router` is already mounted at `/log`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Profile update logic | Custom MongoDB update in UI route | `update_profile()` from `app.profile.service` | Handles lat/lon derivation, $set pattern |
| Cookie JWT decode | Manual cookie parsing | `get_current_user_cookie` dependency | Already handles missing cookie, decode errors, disabled users |
| Profile field validation | Manual string checks | `ProfileUpdateRequest` from `app.profile.schemas` | Has gridsquare regex validation, station_callsign normalization |
| Tooltip | JS tooltip library | HTML `title` attribute | Zero dependencies, meets requirements |

## Common Pitfalls

### Pitfall 1: HTMX 2.x won't swap on 4xx
**What goes wrong:** If the POST handler returns a 4xx status code on validation error, HTMX 2.x ignores the response and does not update the target div — the user sees nothing.
**Why it happens:** HTMX 2.x changed default behavior vs 1.x — non-2xx responses are not swapped by default.
**How to avoid:** Always return HTTP 200 from HTMX-targeted handlers, even on errors. Encode error state in the HTML response body (like `qso_result.html` does with the duplicate warning).

### Pitfall 2: Using callsign-only dep for GET profile
**What goes wrong:** If `get_current_operator_callsign_cookie` is used for the GET route, only the callsign string is available — none of the profile fields exist to pre-populate the form.
**How to avoid:** Use `get_current_user_cookie` for both GET and POST profile routes to get the full `User` document.

### Pitfall 3: Nav links not updated in all three templates
**What goes wrong:** Adding Profile link to `form.html` but forgetting `log.html` and `import.html` — operators navigating from Log View or Import won't see the Profile link.
**How to avoid:** The nav block is duplicated in `form.html`, `log.html`, and `import.html` — all three need the same Profile link added.

### Pitfall 4: tx_pwr form value type mismatch
**What goes wrong:** Form fields are always strings; `tx_pwr` is `Optional[float]`. Passing an empty string to Pydantic float field raises a validation error.
**How to avoid:** Strip and check each form field before building the updates dict. Treat empty string as `None` for optional numeric fields.

### Pitfall 5: station_callsign blank vs. None
**What goes wrong:** Storing an empty string `""` instead of `None` for station_callsign causes LoTW/POTA upload failures (per prior decision).
**How to avoid:** Route through `ProfileUpdateRequest` validation which has `normalize_station_callsign` — empty string → None. Or manually strip/None-coerce in the handler.

## Code Examples

### Template TemplateResponse with full User object
```python
# From app/qso/ui_router.py — form_page pattern adapted for profile
return templates.TemplateResponse(
    request,
    "log/profile.html",
    {"user": user, "callsign": user.callsign},
)
```

### HTMX form targeting a result div (from form.html)
```html
<form hx-post="/log/profile"
      hx-target="#profile-result"
      hx-swap="innerHTML">
  ...
</form>
<div id="profile-result"></div>
```

### Success partial pattern (from qso_result.html)
```html
{% if success %}
<div class="success-msg">Profile saved.</div>
{% endif %}
```

### Direct service call pattern (adapted from submit_qso)
```python
from app.profile.service import update_profile

updated = await update_profile(user, updates)
```

### Existing nav block to extend (from form.html)
```html
<nav>
  <h1>ollog</h1>
  <div style="display:flex;gap:1rem;align-items:center;">
    <span>Logged in as <strong>{{ callsign }}</strong></span>
    <a href="/log/view">Log View</a>
    <a href="/log/import">Import</a>
    <a href="/log/export">Export</a>
    <a href="/log/profile">Profile</a>
    <a href="/log/logout">Logout</a>
  </div>
</nav>
```

## Open Questions

1. **Single result partial or inline HTML string for profile save confirmation?**
   - What we know: `qso_result.html` is a separate partial file. Some routes return inline `HTMLResponse(content=...)`.
   - What's unclear: Whether to create `log/profile_result.html` or just return an inline success/error HTML string.
   - Recommendation: Create `templates/log/profile_result.html` to match the qso_result pattern for consistency.

2. **Should tx_pwr input be `type="number"` or `type="text"`?**
   - What we know: Other form inputs in existing templates use `type="text"` for everything, including numeric-ish fields like FREQ.
   - Recommendation: Use `type="text"` for consistency, validate/coerce in the handler.

3. **Error display for validation failures (e.g. bad gridsquare format)?**
   - What we know: The profile POST should return 200 always. If `ProfileUpdateRequest` raises a validation error (bad gridsquare), the route must catch it and return an error partial.
   - Recommendation: Wrap the update in try/except for `ValidationError`, return an error HTML partial into `#profile-result`.

## Sources

### Primary (HIGH confidence)
- `/Users/royco/ollog/app/qso/ui_router.py` — all existing UI route patterns, cookie auth usage, HTMX integration, direct service calls
- `/Users/royco/ollog/app/profile/router.py` — GET/PATCH profile API (Bearer auth — UI will NOT call this directly)
- `/Users/royco/ollog/app/profile/schemas.py` — `ProfileUpdateRequest`, `ProfileResponse` fields and validators
- `/Users/royco/ollog/app/profile/service.py` — `update_profile()` signature and behavior
- `/Users/royco/ollog/app/auth/models.py` — `User` document fields
- `/Users/royco/ollog/app/auth/dependencies.py` — all cookie/bearer auth dependencies
- `/Users/royco/ollog/app/main.py` — router mounting, exception handler for 401/403 redirect
- `/Users/royco/ollog/templates/base.html` — HTMX version, CSS classes, template structure
- `/Users/royco/ollog/templates/log/form.html` — nav block pattern, HTMX form pattern
- `/Users/royco/ollog/templates/log/log.html` — nav block pattern (slightly different active links)
- `/Users/royco/ollog/templates/log/import.html` — nav block pattern, hx-post form pattern
- `/Users/royco/ollog/templates/log/qso_result.html` — success/error partial pattern

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — directly verified from codebase
- Architecture: HIGH — all patterns verified from working code
- Pitfalls: HIGH — HTMX 2.x behavior documented in existing code comments; others verified from model inspection

**Research date:** 2026-04-04
**Valid until:** Stable — findings based on codebase, not external docs. Valid until codebase changes.
