# Phase 2: Admin & Accounts - Research

**Researched:** 2026-04-03
**Domain:** FastAPI admin API + HTMX/Jinja2 web UI for user account management
**Confidence:** HIGH (API layer), MEDIUM (HTMX/cookie-auth UI layer)

## Summary

Phase 2 builds on top of Phase 1's auth foundation — `User` model, `require_admin` dependency, `hash_password`, and `get_current_user` are already in place. The API layer (plan 02-01) is straightforward: a new `APIRouter` under `/admin/users` with three operations (create, toggle enabled, reset password), all gated by `Depends(require_admin)`. Beanie's `.set()` / `await doc.save()` patterns handle field mutations cleanly.

The web UI layer (plan 02-02) requires new infrastructure: Jinja2Templates, a `templates/` directory, static file mounting, and a cookie-based JWT auth flow parallel to the existing Bearer flow. The existing `oauth2_scheme` + Authorization header approach won't work for browser-rendered pages — browsers don't send Bearer tokens natively. The solution is a second auth dependency that reads the JWT from an HttpOnly cookie, used exclusively by UI routes.

The HTMX interaction model is simple for this phase: form POSTs that return partial HTML fragments to replace the user table or show inline status messages. No complex out-of-band updates are needed — the admin panel is a single-page table plus a "create" form.

**Primary recommendation:** Build the API endpoints first (02-01), then layer the UI (02-02) on top — the UI routes call the same business logic as the API, not the API endpoints themselves.

## Standard Stack

### Core (already in pyproject.toml)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi[standard] | >=0.135.0 | Web framework + Jinja2Templates | `fastapi[standard]` already includes Jinja2 and python-multipart |
| beanie | >=2.1.0 | MongoDB ODM for User document ops | Already in use; `.set()` / `.save()` cover all update needs |
| pwdlib[argon2] | >=0.3.0 | Password hashing | Already in use; `hash_password()` already exists |
| pyjwt | >=2.12.0 | JWT decode for cookie auth dependency | Already in use |

### Supporting (need to add)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| jinja2 | >=3.1 (transitive) | Template rendering | Pulled in by `fastapi[standard]`; no explicit install needed |
| python-multipart | >=0.0.9 (transitive) | Form parsing for HTMX POST | Also pulled in by `fastapi[standard]` |

**No new dependencies required.** `fastapi[standard]` already bundles Jinja2 and python-multipart.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HttpOnly cookie for UI auth | Session middleware (starlette) | Cookie+JWT is stateless and matches existing JWT infrastructure; session adds server-side state |
| Inline partial templates | Separate JS-driven SPA | HTMX avoids frontend build tooling; fits roadmap intent |
| fasthx decorator library | Plain HX-Request header detection | fasthx adds a dependency; HX-Request detection is 3 lines and more explicit |

### Installation

No new packages needed. `fastapi[standard]` already provides Jinja2 and python-multipart.

```bash
# Nothing to add — existing pyproject.toml is sufficient
```

The `Dockerfile` only copies `app/` and `pyproject.toml`. Templates and static files live outside `app/`, so the `COPY` instruction needs updating:

```dockerfile
# Add these lines before CMD:
COPY templates/ templates/
COPY static/ static/
```

## Architecture Patterns

### Recommended Project Structure

```
app/
├── admin/
│   ├── __init__.py
│   ├── router.py        # API routes: /admin/users (JSON)
│   └── ui_router.py     # UI routes: /admin/ui/* (HTML)
├── auth/
│   ├── dependencies.py  # add: get_current_user_cookie dependency
│   └── ...existing...
templates/
├── base.html            # shared layout with HTMX CDN script tag
└── admin/
    ├── users.html       # full admin panel page
    └── users_table.html # partial: just the <tbody> rows (HTMX target)
static/
└── (empty or minimal CSS)
```

The `admin/` module splits cleanly into two routers: JSON API router (02-01) and HTML UI router (02-02). Both import the same service functions — no duplication.

### Pattern 1: Admin API Router (02-01)

**What:** APIRouter with `prefix="/admin/users"`, three endpoints, all `Depends(require_admin)`.
**When to use:** Machine-to-machine or curl/httpie calls with Bearer token.

```python
# app/admin/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.auth.dependencies import require_admin
from app.auth.models import User
from app.auth.service import hash_password

router = APIRouter(prefix="/admin/users", tags=["admin"])

class CreateUserRequest(BaseModel):
    username: str
    callsign: str
    password: str

class ResetPasswordRequest(BaseModel):
    password: str

@router.post("/", status_code=201)
async def create_user(
    body: CreateUserRequest,
    _admin: User = Depends(require_admin),
):
    existing = await User.find_one({"username": body.username})
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(
        username=body.username,
        callsign=body.callsign.upper(),
        hashed_password=hash_password(body.password),
        role="operator",
        enabled=True,
    )
    await user.insert()
    return {"username": user.username, "callsign": user.callsign}

@router.patch("/{username}/enabled")
async def set_enabled(
    username: str,
    enabled: bool,
    _admin: User = Depends(require_admin),
):
    user = await User.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await user.set({User.enabled: enabled})
    return {"username": username, "enabled": enabled}

@router.post("/{username}/reset-password")
async def reset_password(
    username: str,
    body: ResetPasswordRequest,
    _admin: User = Depends(require_admin),
):
    user = await User.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await user.set({User.hashed_password: hash_password(body.password)})
    return {"username": username, "reset": True}
```

Source: Beanie docs (beanie-odm.dev/tutorial/updating-&-deleting/), FastAPI docs (fastapi.tiangolo.com/advanced/templates/)

### Pattern 2: Cookie-Based JWT Auth Dependency (for UI routes)

**What:** A second auth dependency that reads the JWT from a cookie named `access_token` instead of the `Authorization` header.
**When to use:** All UI routes (`/admin/ui/*`) — browsers don't send Bearer tokens.

```python
# app/auth/dependencies.py (add alongside existing get_current_user)
from fastapi import Cookie, HTTPException, status

async def get_current_user_cookie(
    access_token: str | None = Cookie(default=None),
) -> User:
    """Auth dependency for browser-rendered UI routes — reads JWT from HttpOnly cookie."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )
    if access_token is None:
        raise credentials_exception
    try:
        payload = decode_access_token(access_token)
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    user = await User.find_one({"username": username})
    if user is None or not user.enabled:
        raise credentials_exception
    return user

async def require_admin_cookie(user: User = Depends(get_current_user_cookie)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
```

The login endpoint for the UI must set the cookie on success:

```python
# In ui_router.py — login POST handler
from fastapi.responses import RedirectResponse

@ui_router.post("/login")
async def ui_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = await User.find_one({"username": username})
    if not user or not user.enabled or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="admin/login.html",
            context={"error": "Invalid credentials"},
        )
    token = create_access_token({"sub": user.username, "callsign": user.callsign, "role": user.role})
    response = RedirectResponse(url="/admin/ui/users", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True, samesite="lax")
    return response
```

Source: FastAPI docs (fastapi.tiangolo.com/advanced/response-cookies/), retz.dev/blog/jwt-and-cookie-auth-in-fastapi/

### Pattern 3: HTMX Partial Responses

**What:** UI routes detect `HX-Request` header; return fragment HTML for HTMX calls, full page for direct browser navigation.
**When to use:** Any route that HTMX will call to update a portion of the page.

```python
# app/admin/ui_router.py
from fastapi import APIRouter, Depends, Form, Header, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated

templates = Jinja2Templates(directory="templates")
ui_router = APIRouter(prefix="/admin/ui", tags=["admin-ui"])

@ui_router.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    hx_request: Annotated[str | None, Header()] = None,
    admin: User = Depends(require_admin_cookie),
):
    users = await User.find_all().to_list()
    if hx_request:
        return templates.TemplateResponse(
            request=request,
            name="admin/users_table.html",
            context={"users": users},
        )
    return templates.TemplateResponse(
        request=request,
        name="admin/users.html",
        context={"users": users},
    )
```

Template for HTMX target (fragment only):

```html
<!-- templates/admin/users_table.html -->
{% for user in users %}
<tr>
  <td>{{ user.username }}</td>
  <td>{{ user.callsign }}</td>
  <td>{{ "enabled" if user.enabled else "disabled" }}</td>
  <td>
    <button hx-post="/admin/ui/users/{{ user.username }}/toggle"
            hx-target="#users-table-body"
            hx-swap="innerHTML">
      {{ "Disable" if user.enabled else "Enable" }}
    </button>
  </td>
</tr>
{% endfor %}
```

Source: htmx.org/docs/, testdriven.io/blog/fastapi-htmx/

### Pattern 4: Jinja2Templates Setup in main.py / static files

**What:** Mount static files directory and create the `Jinja2Templates` instance.
**When to use:** Once, during app initialization.

```python
# app/main.py additions
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app.mount("/static", StaticFiles(directory="static"), name="static")
```

`Jinja2Templates(directory="templates")` should be instantiated once in the UI router module (or a shared `app/templates.py` singleton), not re-created per request.

Source: FastAPI official docs (fastapi.tiangolo.com/advanced/templates/)

### Anti-Patterns to Avoid

- **Using `oauth2_scheme` (Bearer) for UI routes:** Browsers don't send Authorization headers on navigation. Cookie auth is required for browser-based admin UI.
- **Storing JWT in localStorage in the template:** Defeats XSS protection. Use HttpOnly cookies only.
- **Re-creating `Jinja2Templates(...)` per request:** Instantiate once at module level.
- **Returning 401/403 as JSON for UI routes:** The browser will show raw JSON. UI routes that fail auth should redirect to `/admin/ui/login`.
- **Calling the admin JSON API from the UI router via HTTP:** The UI router should call the same service functions (or Beanie queries) directly, not make internal HTTP requests to its own API.
- **Full-page replace on every HTMX action:** Use targeted partial responses (`hx-target="#users-table-body"`) to avoid jarring reloads.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom bcrypt/argon2 wrapper | `hash_password()` (already in `app/auth/service.py`) | Already implemented and tested |
| JWT decode for cookies | Custom cookie parsing | `fastapi.Cookie` + existing `decode_access_token()` | 5 lines with existing tools |
| Admin role check | Inline `if user.role != "admin"` in every route | `require_admin` / `require_admin_cookie` dependency | DRY, consistent 403 response |
| User field updates | Raw pymongo `update_one()` | Beanie `.set({User.field: value})` | Type-safe, validates against model |
| Form data parsing | Manual `request.body()` parse | FastAPI `Form(...)` parameter | Built into `fastapi[standard]` |

**Key insight:** The Phase 1 foundation already provides all the hard parts. Phase 2 is wiring — not infrastructure.

## Common Pitfalls

### Pitfall 1: Two Auth Schemes Not Being Kept Separate

**What goes wrong:** UI routes accidentally use Bearer-based `get_current_user`; all HTMX requests return 401 with no feedback to the user.
**Why it happens:** Developers reach for the existing dependency without realizing it reads `Authorization: Bearer` headers, which browsers don't send.
**How to avoid:** Create `get_current_user_cookie` and `require_admin_cookie` as distinct dependencies. Name them clearly. UI router imports only cookie variants.
**Warning signs:** Admin panel works in Swagger but returns 401 in browser.

### Pitfall 2: 401/403 Responses Surfacing as JSON in the Browser

**What goes wrong:** When the cookie is missing or expired, FastAPI returns `{"detail": "Not authenticated"}` which the browser renders as raw JSON.
**Why it happens:** Default `HTTPException` returns JSON.
**How to avoid:** In UI routes, catch auth failures and return a `RedirectResponse` to the login page instead of raising `HTTPException`. Or use a custom exception handler for the UI router prefix.
**Warning signs:** Browser shows `{"detail": ...}` text page after cookie expires.

### Pitfall 3: HTMX Redirect After Successful Form POST

**What goes wrong:** After a create/toggle/reset POST, the server returns 200 with a fragment, but the admin wants a full redirect or page confirmation.
**Why it happens:** HTMX follows 200 responses normally (swapping content). `RedirectResponse` 302 is also followed automatically by HTMX, but it replaces only `hx-target`, not the whole page.
**How to avoid:** To trigger a full-page redirect from an HTMX POST response, use the `HX-Redirect` response header:
```python
from fastapi.responses import HTMLResponse
response = HTMLResponse(content="", status_code=200)
response.headers["HX-Redirect"] = "/admin/ui/users"
return response
```
For simple in-place updates (toggle enable/disable), return the updated table fragment directly — no redirect needed.
**Warning signs:** Page appears stale after action, or browser URL doesn't update.

### Pitfall 4: Disabling the Last Admin Account

**What goes wrong:** Admin disables themselves or resets the only admin's password to unknown, locking out the system.
**Why it happens:** No guard on the disable endpoint.
**How to avoid:** In the enable/disable endpoint, check `if not enabled and user.role == "admin"`: count admins with `enabled=True`, refuse if count == 1.
**Warning signs:** System unreachable without restarting with fresh `ADMIN_PASSWORD` env var.

### Pitfall 5: Beanie `.set()` Field Reference Syntax

**What goes wrong:** Using string keys in `.set()` instead of field references causes silent failures or type errors.
**Why it happens:** Beanie supports both `{User.enabled: False}` (field expression) and `{"enabled": False}` (string). Mixed usage creates confusion.
**How to avoid:** Use the field-expression form `{User.enabled: False}` consistently — it's type-checked and refactor-safe.

### Pitfall 6: Templates Not Found in Docker

**What goes wrong:** App works locally but crashes in Docker because `templates/` directory is not copied.
**Why it happens:** The Dockerfile only copies `app/` and `pyproject.toml`. `templates/` and `static/` are outside `app/`.
**How to avoid:** Add `COPY templates/ templates/` and `COPY static/ static/` to the Dockerfile before the `CMD` line.
**Warning signs:** `jinja2.exceptions.TemplateNotFound` in Docker logs.

## Code Examples

Verified patterns from official sources:

### Beanie Field Update (two equivalent styles)

```python
# Style 1: field expression (preferred — type-safe)
user = await User.find_one({"username": username})
await user.set({User.enabled: False})

# Style 2: $set operator (MongoDB native)
await User.find_one({"username": username}).update({"$set": {"enabled": False}})
```

Source: beanie-odm.dev/tutorial/updating-&-deleting/

### FastAPI Cookie Dependency

```python
from fastapi import Cookie

async def get_current_user_cookie(
    access_token: str | None = Cookie(default=None),
) -> User:
    ...
```

Source: FastAPI docs (fastapi.tiangolo.com/advanced/response-cookies/)

### Setting HttpOnly Cookie on Login

```python
response = RedirectResponse(url="/admin/ui/users", status_code=302)
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    samesite="lax",
    # secure=True  # add in production (HTTPS only)
)
return response
```

Source: FastAPI response cookies docs

### HTMX HX-Request Detection

```python
from typing import Annotated
from fastapi import Header

async def my_route(
    request: Request,
    hx_request: Annotated[str | None, Header()] = None,
):
    if hx_request:
        return templates.TemplateResponse(request=request, name="partial.html", context={...})
    return templates.TemplateResponse(request=request, name="full.html", context={...})
```

Source: testdriven.io/blog/fastapi-htmx/

### HTMX Full-Page Redirect from POST Handler

```python
from fastapi.responses import HTMLResponse

response = HTMLResponse(content="", status_code=200)
response.headers["HX-Redirect"] = "/admin/ui/users"
return response
```

Source: htmx.org/docs/ (HX-Redirect response header)

### Jinja2Templates Initialization

```python
# Instantiate once at module level, not per request
templates = Jinja2Templates(directory="templates")

@router.get("/page", response_class=HTMLResponse)
async def page(request: Request):
    return templates.TemplateResponse(
        request=request,        # required — pass as keyword arg (FastAPI >= 0.108)
        name="admin/users.html",
        context={"users": users},
    )
```

Source: fastapi.tiangolo.com/advanced/templates/

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `TemplateResponse(name, {"request": request, ...})` | `TemplateResponse(request=request, name=..., context={...})` | FastAPI 0.108.0 | New signature avoids forgetting to include request in context dict |
| Motor directly | Beanie ODM | Beanie 1.x+ | Document-level API, Pydantic validation built in |

**Deprecated/outdated:**
- Positional `TemplateResponse(name, context)` with `request` inside context dict: still works but the new keyword-arg form is cleaner and consistent with FastAPI >= 0.108.

## Open Questions

1. **Should the admin UI have its own login page, or reuse the existing `/auth/token` flow?**
   - What we know: The existing `/auth/token` is an OAuth2 form endpoint returning JSON — not suitable for browser redirect flow.
   - What's unclear: Phase description says "protected web UI" but doesn't specify a login UX.
   - Recommendation: Add a minimal `/admin/ui/login` page (GET renders form, POST sets cookie + redirects). Keep it simple — the admin can also use the API directly with Bearer if preferred.

2. **CSRF protection for HTMX form POSTs?**
   - What we know: `samesite="lax"` on the cookie provides basic CSRF protection for same-origin requests. HTMX sends `HX-Request: true` header which can serve as a CSRF signal for same-origin SPA usage.
   - What's unclear: Whether the threat model requires full CSRF tokens for this internal admin tool.
   - Recommendation: `samesite="lax"` is sufficient for an internal admin panel on the same domain. Skip CSRF tokens in Phase 2; note it as future hardening.

3. **Template CDN vs. bundled HTMX?**
   - What we know: CDN (unpkg.com/htmx.org) is simplest; bundled in `static/` works offline.
   - Recommendation: CDN is fine for a development/internal tool. Use CDN in Phase 2.

## Sources

### Primary (HIGH confidence)
- fastapi.tiangolo.com/advanced/templates/ — Jinja2Templates setup, TemplateResponse signature
- fastapi.tiangolo.com/advanced/response-cookies/ — `response.set_cookie()` API
- beanie-odm.dev/tutorial/updating-&-deleting/ — `.set()`, `.save()`, `$set` operator
- htmx.org/docs/ — `HX-Request` header, `hx-target`, `hx-swap`, `HX-Redirect` response header

### Secondary (MEDIUM confidence)
- testdriven.io/blog/fastapi-htmx/ — HX-Request detection pattern, project structure (verified against HTMX and FastAPI official docs)
- retz.dev/blog/jwt-and-cookie-auth-in-fastapi/ — Cookie JWT pattern (cross-verified with FastAPI cookie docs)
- medium.com/@ancilartech — HttpOnly cookie JWT (cross-verified with FastAPI official docs)

### Tertiary (LOW confidence)
- johal.in/fastapi-templating-jinja2-server-rendered-ml-dashboards-with-htmx-2025/ — HTMX/FastAPI 2025 trends (marketing-heavy, patterns match primary sources)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already in pyproject.toml; `fastapi[standard]` bundles Jinja2 and multipart; verified against official docs
- Architecture (API layer): HIGH — `require_admin` dependency already exists; Beanie update patterns verified from official docs
- Architecture (UI/HTMX): MEDIUM — cookie auth + HTMX partial patterns cross-verified from multiple sources; `HX-Redirect` header verified from htmx.org/docs
- Pitfalls: MEDIUM — auth scheme mismatch, Docker template copy, and last-admin guard are well-reasoned from the codebase; HTMX redirect behavior from official docs

**Research date:** 2026-04-03
**Valid until:** 2026-07-01 (stable stack; Beanie and FastAPI APIs change slowly)
