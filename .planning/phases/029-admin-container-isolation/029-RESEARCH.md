# Phase 29: Admin Container Isolation - Research

**Researched:** 2026-04-10
**Domain:** FastAPI multi-entry-point architecture, Docker Compose profiles, cookie isolation, Pydantic settings validation
**Confidence:** HIGH

## Summary

This phase extracts the admin subsystem into a separate Docker Compose service (`admin`) running on port 8001 with its own FastAPI application entry point (`app/admin_main.py`). The operator app on port 8000 (`app/main.py`) remains completely untouched. The two services share the same Docker image and MongoDB instance but run independent Python processes.

The central implementation task is writing `app/admin_main.py` — a minimal FastAPI app whose lifespan calls only `init_db()` and `_bootstrap_admin()`, then mounts only `auth_router`, `admin_router`, `ui_router`, and a `/health` endpoint. Because both containers read the same `SECRET_KEY` from `.env`, JWTs issued by either service are mutually valid (ADM-05). Cookie name collision between the two containers is prevented by renaming the admin cookie from `access_token` to `admin_token` — a change required in `app/auth/dependencies.py` (adding a new `get_current_admin_cookie` dependency) and in `app/admin/ui_router.py` (where `set_cookie` and `delete_cookie` are called).

The Docker Compose side is straightforward: add an `admin` service that uses the same `build: .` target, overrides `command` to point at `app.admin_main:app` on port 8001, applies `profiles: [admin]`, and removes the hardcoded `SECRET_KEY=dev-secret-change-in-production` line from the existing `api` service. Since `config.py` already declares `secret_key: str` with no default, omitting it from `.env` will cause Pydantic to raise a `ValidationError` at startup — satisfying ADM-06.

**Primary recommendation:** Create `app/auth/bootstrap.py` (extracting `_bootstrap_admin` from `main.py`) first, then update tests, then write `admin_main.py`, then handle the cookie rename, then update `docker-compose.yml`. Each step is independently verifiable.

---

## Locked Architecture Decisions

The following decisions are fixed and must not be revisited:

- Entry point is `app/admin_main.py` (standalone FastAPI app — NOT `app/main.py` with a mode flag)
- `admin_main.py` must never import from `app.main`
- Admin cookie renamed to `admin_token`; operator `access_token` cookie is untouched
- Admin lifespan calls `init_db()` and `_bootstrap_admin()` only — no UDP listener, no SSE change-stream watcher
- `init_beanie()` called with full `document_models=[QSO, User, ApiToken]` list to prevent `CollectionWasNotInitialized` on any shared code path
- `SECRET_KEY=dev-secret-change-in-production` default removed from `docker-compose.yml`; value must come from `.env`
- Docker Compose `profiles: [admin]` gates the admin service (opt-in)

---

## Codebase Findings (HIGH confidence — sourced directly from codebase)

### `app/main.py` — What admin_main.py must NOT replicate

The operator `lifespan` in `main.py` does six things beyond `init_db()` and `_bootstrap_admin()`:

1. Fetches `client = get_client()` for the change-stream watcher
2. Starts `asyncio.create_task(watch_qsos(...))` (SSE live feed)
3. Conditionally starts the UDP listener via `start_udp_listener()`
4. Manages `watcher_task.cancel()` on shutdown
5. Closes UDP transport on shutdown
6. Calls `close_db()` on shutdown

`admin_main.py` lifespan must do only: `init_db()`, `_bootstrap_admin()`, `yield`, `close_db()`. Nothing else.

The operator app also mounts these routers that must NOT appear in `admin_main.py`:
- `qso_router` (`/qso/`)
- `qso_ui_router`
- `adif_router`
- `feed_router`
- `profile_router`
- `token_router`
- Static mounts: `/guide`, `/static`

The exception handler for `401/403` on `/admin/ui/*` paths must be replicated in `admin_main.py` — it currently lives in `main.py` and redirects to `/admin/ui/login`.

### `app/database.py` — What admin_main.py calls

```python
# init_db() already calls init_beanie() with the full document_models list:
await init_beanie(
    database=_client[settings.mongodb_db],
    document_models=[QSO, User, ApiToken],
)
```

`admin_main.py` simply calls `await init_db()` — no need to call `init_beanie()` separately. The `_bootstrap_admin()` function is defined inside `main.py` and must be moved to `app/auth/bootstrap.py` (since `admin_main.py` must never import from `app.main`).

### `_bootstrap_admin()` — Test suite constraint on extraction

`tests/test_auth.py` currently imports and calls `_bootstrap_admin` via:

```python
from app import main as main_module
await main_module._bootstrap_admin()
# and patches via:
main_module._bootstrap_admin.__globals__["settings"] = patched_settings
```

This means the test references `app.main._bootstrap_admin` by attribute access. When `_bootstrap_admin` is moved to `app/auth/bootstrap.py`, the test must be updated to import from the new location:

```python
from app.auth import bootstrap as bootstrap_module
await bootstrap_module._bootstrap_admin()
bootstrap_module._bootstrap_admin.__globals__["settings"] = patched_settings
```

The `__globals__` patching pattern will still work as long as the import source is updated — the function's `__globals__` dict is the module-level namespace of wherever the function is defined.

**After moving `_bootstrap_admin` to `app/auth/bootstrap.py`**, `app/main.py` must import it:

```python
from app.auth.bootstrap import _bootstrap_admin
```

This is the only change to `main.py` — function body and all other routers remain untouched (ADM-07 satisfied).

### `app/auth/dependencies.py` — Cookie name change impact

The `get_current_user_cookie` dependency reads the cookie by name:

```python
async def get_current_user_cookie(
    access_token: str | None = Cookie(default=None),
) -> User:
```

The parameter name `access_token` is the cookie key FastAPI extracts. This dependency is used by **both** the operator UI (`/log/` routes via `get_current_operator_callsign_cookie`) and the admin UI (`/admin/ui/` routes via `require_admin_cookie`).

Renaming the parameter inside `get_current_user_cookie` would break the operator UI. **Resolution:** Create a new, separate cookie dependency for admin routes only:

- `get_current_user_cookie` — remains unchanged, reads `access_token` (operator UI)
- `get_current_admin_cookie` — new function, reads `admin_token` (admin UI only)

Then update `require_admin_cookie` to depend on `get_current_admin_cookie` instead of `get_current_user_cookie`.

**Confirmed:** `require_admin_cookie` is only used in `app/admin/ui_router.py` (4 endpoints). No `/log/` route uses it. The dependency chain change is safe.

### `app/admin/ui_router.py` — Cookie write/delete locations

Two exact locations must change from `access_token` to `admin_token`:

**Line 79 — login success:**
```python
response.set_cookie(
    key="access_token",   # <-- change to "admin_token"
    value=token,
    httponly=True,
    samesite="lax",
)
```

**Line 87 — logout:**
```python
response.delete_cookie(key="access_token")   # <-- change to "admin_token"
```

### `app/config.py` — SECRET_KEY already has no default

```python
class Settings(BaseSettings):
    secret_key: str   # no default — Pydantic will raise ValidationError if absent
```

This is already correct. The only action needed is removing the Docker Compose override `SECRET_KEY=dev-secret-change-in-production` from the `api` service's `environment:` block. After removal, `secret_key` must come from `.env` for startup to succeed (ADM-06).

### `docker-compose.yml` — Current state

```yaml
services:
  mongodb:  # no change
  api:
    build: .
    ports:
      - "8000:8000"
      - "2399:2399/udp"
    environment:
      - SECRET_KEY=dev-secret-change-in-production  # <-- DELETE THIS LINE
      - MONGODB_URI=mongodb://mongodb:27017/?replicaSet=rs0
      - MONGODB_DB=ollog
```

The `admin` service to add:

```yaml
  admin:
    build: .
    command: ["uvicorn", "app.admin_main:app", "--host", "0.0.0.0", "--port", "8001"]
    ports:
      - "8001:8001"
    depends_on:
      mongodb:
        condition: service_healthy
    env_file: .env
    environment:
      - MONGODB_URI=mongodb://mongodb:27017/?replicaSet=rs0
      - MONGODB_DB=ollog
    profiles:
      - admin
```

Note: no `SECRET_KEY` default in `environment:` — it comes from `.env` only.

### `Dockerfile` — CMD override pattern

The Dockerfile uses:
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Docker Compose's `command:` key overrides `CMD` at runtime without rebuilding the image. The admin service needs:
```yaml
command: ["uvicorn", "app.admin_main:app", "--host", "0.0.0.0", "--port", "8001"]
```

This is the standard Docker pattern — same image, different runtime command. No Dockerfile changes needed.

---

## Architecture Patterns

### Pattern 1: Shared Image, Different Entry Points

**What:** Both services use `build: .` in the same compose file but run different Python modules via `command:` override.

**When to use:** When two services share the same codebase/dependencies but serve different subsets of routes.

**Key constraint:** The image must contain both entry point modules. The Dockerfile already copies all of `app/` so `app/admin_main.py` will be included automatically once created.

### Pattern 2: Docker Compose Profiles

**What:** `profiles: [admin]` in a service definition makes it opt-in. It does not start with `docker compose up` but does start with `docker compose --profile admin up`.

**Behavior:** Stable Docker Compose v2 feature. A service with `profiles:` does NOT start unless its profile is explicitly activated. Running `docker compose up` with no profile flag will start `mongodb` and `api` only. Running `docker compose --profile admin up` starts all three.

**Services without a `profiles:` key are always started** (e.g., `mongodb` and `api`).

### Pattern 3: Minimal Lifespan for Derived Entry Point

**What:** `admin_main.py` lifespan is intentionally narrower than `main.py` lifespan.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _bootstrap_admin()
    yield
    await close_db()
```

No UDP, no SSE watcher. This is a correct and safe pattern — MongoDB change streams and UDP are operator-only concerns.

### Pattern 4: Splitting Cookie Auth by Name

**What:** Two FastAPI `Cookie()` dependencies with different parameter names, both sharing the same token-decode logic.

```python
# For operator UI (/log/ routes) — unchanged
async def get_current_user_cookie(
    access_token: str | None = Cookie(default=None),
) -> User:
    ...

# New — for admin UI (/admin/ui/ routes)
async def get_current_admin_cookie(
    admin_token: str | None = Cookie(default=None),
) -> User:
    ...
```

Both call `decode_access_token()` identically. The only difference is the cookie key name.

### Anti-Patterns to Avoid

- **Importing from `app.main` in `admin_main.py`:** `_bootstrap_admin()` is currently defined in `main.py`. Do NOT import it from there — it will transitively pull in the entire operator app module. Move it to `app/auth/bootstrap.py`.
- **Using a mode flag on `main.py`:** The locked decision prohibits this pattern. Two separate files is the required approach.
- **Sharing `SECRET_KEY` via Docker Compose `environment:` hardcoding:** Both services must rely on `.env` only. The hardcoded default must be removed.
- **Initializing Beanie with a partial document_models list:** If `init_db()` only registered `User`, any code path touching `QSO` or `ApiToken` would raise `CollectionWasNotInitialized`. The existing `init_db()` already uses the full list — this is already correct.
- **Renaming the parameter of `get_current_user_cookie`:** This would break operator UI cookie auth. Add a new `get_current_admin_cookie` instead.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cookie name parameter binding | Manual `request.cookies` lookup | `Cookie(default=None)` FastAPI parameter | FastAPI's dependency injection handles type coercion, `None` default, and schema docs |
| Docker multi-service same image | Multiple Dockerfiles | `command:` override in compose + `profiles:` | Standard compose pattern, no rebuild needed |
| Pydantic required field validation | Custom startup check | `secret_key: str` with no default | Pydantic raises `ValidationError` before app starts — fail-fast by design |
| Admin bootstrap idempotency | Custom "is bootstrapped" flag | The existing `_bootstrap_admin()` already checks `User.find_one()` | Already implemented correctly — just needs to be extractable |

---

## Common Pitfalls

### Pitfall 1: Cookie Sharing Between Ports on Localhost

**What goes wrong:** RFC 6265 does not scope cookies by port. A cookie set by `localhost:8001` is sent to `localhost:8000` and vice versa. If both cookies are named `access_token`, the admin JWT would overwrite the operator JWT in the browser's cookie jar.

**Why it happens:** Browsers treat `localhost:8000` and `localhost:8001` as the same origin for cookie purposes.

**How to avoid:** The locked decision already addresses this: admin cookie is named `admin_token`. With distinct cookie names, both can coexist without conflict.

**Warning signs:** If the operator app suddenly sees admin-role JWTs, the cookie names have collided.

### Pitfall 2: Forgetting `close_db()` in Admin Lifespan Shutdown

**What goes wrong:** MongoDB connection leaks if `close_db()` is not called in the post-yield block of the admin lifespan.

**How to avoid:** The `asynccontextmanager` pattern ensures post-yield code runs on shutdown. Always call `await close_db()` after `yield`.

### Pitfall 3: `_bootstrap_admin()` Still in `app/main.py` When Writing `admin_main.py`

**What goes wrong:** If `admin_main.py` imports `_bootstrap_admin` from `app.main`, it will transitively import the entire operator app — including feed manager, UDP listener, static mounts — violating the "never import from app.main" constraint.

**How to avoid:** Move `_bootstrap_admin()` to `app/auth/bootstrap.py` before writing `admin_main.py`. Update `tests/test_auth.py` to import from the new location. Then update `main.py` to import from `app.auth.bootstrap`.

### Pitfall 4: Test Suite Breaks After `_bootstrap_admin` Move

**What goes wrong:** `tests/test_auth.py` accesses `_bootstrap_admin` via `main_module._bootstrap_admin`. After moving the function, this attribute no longer exists on `app.main`.

**How to avoid:** After moving to `app/auth/bootstrap.py`, update the test's import:
```python
# Before:
from app import main as main_module
main_module._bootstrap_admin.__globals__["settings"] = patched_settings
await main_module._bootstrap_admin()

# After:
from app.auth import bootstrap as bootstrap_module
bootstrap_module._bootstrap_admin.__globals__["settings"] = patched_settings
await bootstrap_module._bootstrap_admin()
```

### Pitfall 5: Exception Handler for `/admin/ui/` 401/403 Redirect Missing from admin_main.py

**What goes wrong:** The browser-facing redirect for auth failures on `/admin/ui/*` paths is currently defined in `app/main.py`'s `@app.exception_handler(HTTPException)` handler. If `admin_main.py` doesn't include an equivalent handler, cookie-authed admin UI requests will return raw JSON 401/403 instead of redirecting to `/admin/ui/login`.

**How to avoid:** Include the same exception handler in `admin_main.py` (only the `/admin/ui/` branch is needed — the `/log/` branch is operator-only).

### Pitfall 6: `profiles:` Service Still Reachable via `docker compose run`

**What goes wrong:** `docker compose run admin` will start the admin service even without `--profile admin`. This is a known Docker Compose behavior — profiles only gate `docker compose up`.

**How to avoid:** Document this behavior. The `docker compose up` vs. `docker compose --profile admin up` distinction satisfies the success criteria.

### Pitfall 7: `.env` File Not Present → Both Services Fail

**What goes wrong:** After removing the `SECRET_KEY` hardcoded default, if `.env` doesn't contain `SECRET_KEY`, both `api` and `admin` containers will fail to start with a Pydantic `ValidationError`.

**How to avoid:** This failure mode is desired (ADM-06). Ensure `.env.example` includes `SECRET_KEY=` so developers know to set it.

---

## Code Examples

### admin_main.py skeleton

```python
# Source: derived from app/main.py + locked architecture decisions
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.database import init_db, close_db, get_client
from app.auth.bootstrap import _bootstrap_admin  # moved from app/main.py

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _bootstrap_admin()
    yield
    await close_db()


app = FastAPI(title="ollog-admin", version="0.1.0", lifespan=lifespan)

from app.auth.router import router as auth_router   # noqa: E402
from app.admin.router import router as admin_router  # noqa: E402
from app.admin.ui_router import ui_router            # noqa: E402

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(ui_router, include_in_schema=False)


@app.exception_handler(HTTPException)
async def ui_auth_redirect(request: Request, exc: HTTPException):
    path = request.url.path
    if path.startswith("/admin/ui/") and exc.status_code in (401, 403):
        return RedirectResponse(url="/admin/ui/login", status_code=302)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.get("/health")
async def health():
    client = get_client()
    if client is None:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "mongodb": "disconnected"},
        )
    try:
        await client.admin.command("ping")
        return {"status": "ok", "mongodb": "connected"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "mongodb": "disconnected"},
        )
```

### app/auth/bootstrap.py (extracted function)

```python
# Source: moved verbatim from app/main.py lines 18-45
import logging
from app.config import settings

logger = logging.getLogger(__name__)


async def _bootstrap_admin() -> None:
    """Create the initial admin user from environment variables if not present.

    Called once after init_beanie during lifespan startup. Idempotent —
    if the admin user already exists it is left untouched.
    """
    if not (settings.admin_username and settings.admin_password and settings.admin_callsign):
        logger.info("Admin bootstrap skipped — ADMIN_USERNAME/PASSWORD/CALLSIGN not set")
        return

    from app.auth.models import User
    from app.auth.service import hash_password

    existing = await User.find_one({"username": settings.admin_username})
    if existing is not None:
        logger.info("Admin user already exists: %s", settings.admin_username)
        return

    admin = User(
        username=settings.admin_username,
        hashed_password=hash_password(settings.admin_password),
        callsign=settings.admin_callsign.upper(),
        role="admin",
        enabled=True,
    )
    await admin.insert()
    logger.info("Admin user bootstrapped: %s (%s)", settings.admin_username, settings.admin_callsign)
```

### New cookie dependency for admin routes

```python
# Source: app/auth/dependencies.py — new function alongside existing get_current_user_cookie
async def get_current_admin_cookie(
    admin_token: str | None = Cookie(default=None),
) -> User:
    """FastAPI dependency: decode JWT from HttpOnly 'admin_token' cookie.

    Used exclusively by admin UI routes on port 8001.
    Raises 401 if the cookie is missing, invalid, expired, or the user is not found / disabled.
    """
    if admin_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = decode_access_token(admin_token)
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    user = await User.find_one({"username": username})
    if user is None or not user.enabled:
        raise credentials_exception
    return user
```

### Updated require_admin_cookie

```python
async def require_admin_cookie(
    user: User = Depends(get_current_admin_cookie),  # changed from get_current_user_cookie
) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
```

### docker-compose.yml admin service addition

```yaml
  admin:
    build: .
    command: ["uvicorn", "app.admin_main:app", "--host", "0.0.0.0", "--port", "8001"]
    ports:
      - "8001:8001"
    depends_on:
      mongodb:
        condition: service_healthy
    env_file: .env
    environment:
      - MONGODB_URI=mongodb://mongodb:27017/?replicaSet=rs0
      - MONGODB_DB=ollog
    profiles:
      - admin
```

### Removing hardcoded SECRET_KEY from api service

```yaml
# Before:
  api:
    environment:
      - SECRET_KEY=dev-secret-change-in-production  # DELETE THIS LINE
      - MONGODB_URI=...
      - MONGODB_DB=ollog

# After:
  api:
    environment:
      - MONGODB_URI=...
      - MONGODB_DB=ollog
```

---

## File Change Map

| File | Change Type | What Changes |
|------|-------------|--------------|
| `app/auth/bootstrap.py` | CREATE | `_bootstrap_admin()` moved here from `app/main.py` |
| `app/admin_main.py` | CREATE | Standalone FastAPI app for admin container |
| `app/main.py` | MODIFY | Replace inline `_bootstrap_admin` definition with `from app.auth.bootstrap import _bootstrap_admin` |
| `app/auth/dependencies.py` | MODIFY | Add `get_current_admin_cookie` (reads `admin_token`); update `require_admin_cookie` to depend on it |
| `app/admin/ui_router.py` | MODIFY | Change `set_cookie(key="access_token")` and `delete_cookie(key="access_token")` to `"admin_token"` |
| `docker-compose.yml` | MODIFY | Add `admin` service with profile; remove hardcoded `SECRET_KEY` default from `api` service |
| `tests/test_auth.py` | MODIFY | Update `_bootstrap_admin` test to import from `app.auth.bootstrap` instead of `app.main` |

**Recommended implementation order:**
1. Create `app/auth/bootstrap.py` + update `tests/test_auth.py` + update `app/main.py` import (atomic step — tests must pass after this)
2. Write `app/admin_main.py`
3. Update `app/auth/dependencies.py` (add `get_current_admin_cookie`, update `require_admin_cookie`)
4. Update `app/admin/ui_router.py` (cookie rename)
5. Update `docker-compose.yml` (add admin service, remove SECRET_KEY default)

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Single app serves all routes | Separate FastAPI apps per concern | Admin can be stopped/started without affecting operator |
| Hardcoded `SECRET_KEY` default in compose | No default; must come from `.env` | Fail-fast at startup if secret not set |
| `access_token` cookie for admin UI | `admin_token` cookie for admin UI | Prevents cookie collision on localhost dev |

---

## Open Questions

1. **Is there a `.env.example` or similar template that documents required environment variables?**
   - What we know: removing the hardcoded `SECRET_KEY` default shifts the burden to `.env`
   - What's unclear: whether a `.env.example` exists and needs updating
   - Recommendation: check for `.env.example` at project root; if it exists, add/update `SECRET_KEY=` entry; if it does not exist, consider creating one or noting this in docs

2. **Should the admin service also expose a UDP port mapping?**
   - What we know: the admin lifespan explicitly does NOT start the UDP listener
   - Recommendation: no UDP port mapping in the admin service definition — omitting it is correct

---

## Sources

### Primary (HIGH confidence)
- Direct codebase reads: `app/main.py`, `app/database.py`, `app/config.py`, `app/auth/dependencies.py`, `app/admin/ui_router.py`, `app/admin/router.py`, `app/auth/router.py`, `docker-compose.yml`, `Dockerfile`, `tests/test_auth.py`
- All findings sourced from actual codebase — no external documentation required for this phase

### Secondary (MEDIUM confidence)
- Docker Compose profiles behavior: stable Compose v2 feature, documented at https://docs.docker.com/compose/how-tos/profiles/ — confirmed by locked decisions referencing `profiles: [admin]`
- RFC 6265 cookie port scoping: cookies not scoped by port on same host — this is the explicit rationale for the `admin_token` rename in the locked decisions

---

## Metadata

**Confidence breakdown:**
- File changes required: HIGH — sourced directly from codebase reads; all change locations identified exactly
- Docker Compose profiles syntax: HIGH — stable feature, confirmed by project locked decisions
- Cookie isolation mechanism: HIGH — RFC 6265 behavior well-established, confirmed by locked decision rationale
- Test suite update requirement: HIGH — verified by reading `tests/test_auth.py` lines 323-343
- `_bootstrap_admin` extraction: HIGH — function body is self-contained, no circular imports identified

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable domain — FastAPI, Docker Compose, Pydantic)
