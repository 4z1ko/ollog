import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

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
