import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db, close_db, get_client

logger = logging.getLogger(__name__)


async def _bootstrap_admin() -> None:
    """Create the initial admin user from environment variables if not present.

    Called once after init_beanie during lifespan startup. Idempotent —
    if the admin user already exists it is left untouched.
    """
    if not (settings.admin_username and settings.admin_password and settings.admin_callsign):
        logger.info("Admin bootstrap skipped — ADMIN_USERNAME/PASSWORD/CALLSIGN not set")
        return

    # Import here to avoid circular imports at module load time
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _bootstrap_admin()
    yield
    await close_db()


app = FastAPI(title="ollog", version="0.1.0", lifespan=lifespan)

# Auth router
from app.auth.router import router as auth_router  # noqa: E402
from app.auth.dependencies import get_current_operator_callsign  # noqa: E402

app.include_router(auth_router)

# Admin router
from app.admin.router import router as admin_router  # noqa: E402

app.include_router(admin_router)

# Admin UI router (browser-based, cookie auth, Jinja2 templates)
from app.admin.ui_router import ui_router  # noqa: E402

app.include_router(ui_router)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(HTTPException)
async def ui_auth_redirect(request: Request, exc: HTTPException):
    """Redirect 401/403 errors from /admin/ui/* to the login page.

    All other HTTP exceptions return JSON as normal.
    """
    if request.url.path.startswith("/admin/ui/") and exc.status_code in (401, 403):
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


@app.get("/api/whoami")
async def whoami(callsign: str = Depends(get_current_operator_callsign)):
    """Protected endpoint that returns the operator callsign from the JWT.

    Proves the full auth chain works — callsign comes from JWT, never from request.
    This endpoint will be replaced by real endpoints in later phases.
    """
    return {"callsign": callsign}
