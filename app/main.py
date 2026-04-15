import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import init_db, close_db, get_client
from app.auth.bootstrap import _bootstrap_admin

_templates = Jinja2Templates(directory="templates")

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _bootstrap_admin()
    # Start change stream watcher for live feed
    client = get_client()
    watcher_task = None
    if client is not None:
        from app.feed.manager import manager as feed_manager, watch_qsos  # noqa: E402
        collection = client[settings.mongodb_db]["qsos"]
        watcher_task = asyncio.create_task(
            watch_qsos(collection, feed_manager, _templates)
        )
    # Start UDP listener (conditional on UDP_ENABLED)
    udp_transport = None
    if settings.udp_enabled:
        from app.udp.token_cache import token_cache
        from app.udp.operator_cache import operator_cache
        await token_cache.load()
        await operator_cache.load()
        from app.auth.models import User as UserModel
        from app.udp.server import start_udp_listener

        udp_user: UserModel | None = None
        udp_op: str | None = settings.udp_operator
        if udp_op:
            udp_op = udp_op.upper()  # normalise callsign casing
            udp_user = await UserModel.find_one({"callsign": udp_op})
            if udp_user is None:
                logger.warning(
                    "UDP_OPERATOR callsign %r not found in DB — profile stamping disabled",
                    udp_op,
                )

        udp_transport, _ = await start_udp_listener(
            settings.udp_bind_host,
            settings.udp_port,
            operator=udp_op,
            user=udp_user,
        )

    # Start backup scheduler (conditional on BACKUP_SCHEDULE env var)
    backup_task = None
    backup_scheduler = None
    if settings.backup_schedule:
        from app.backup.scheduler import make_scheduler
        from app.backup.dump import run_backup

        async def _backup_job():
            await run_backup(settings)

        backup_scheduler = make_scheduler(settings.backup_schedule, _backup_job)
        backup_scheduler.start()
        logger.info("Backup scheduler started (cron: %s)", settings.backup_schedule)

    yield

    # Shutdown order: UDP first, then change-stream watcher, then backup scheduler, then database.
    # transport.close() is synchronous — do NOT await it.
    if udp_transport is not None:
        udp_transport.close()
    if watcher_task is not None:
        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass
    if backup_task is not None:
        backup_task.cancel()
        try:
            await backup_task
        except asyncio.CancelledError:
            pass
    if backup_scheduler is not None and backup_scheduler.running:
        backup_scheduler.shutdown(wait=False)
    await close_db()


app = FastAPI(title="ollog", version="0.1.0", lifespan=lifespan)

# Auth router
from app.auth.router import router as auth_router  # noqa: E402
from app.auth.dependencies import get_current_operator_callsign  # noqa: E402

app.include_router(auth_router)

# QSO REST API router
from app.qso.router import router as qso_router  # noqa: E402

app.include_router(qso_router)

# QSO UI router (browser-based, cookie auth, Jinja2 templates)
from app.qso.ui_router import ui_router as qso_ui_router  # noqa: E402

app.include_router(qso_ui_router, include_in_schema=False)

# ADIF import/export router
from app.adif.router import router as adif_router  # noqa: E402

app.include_router(adif_router)

# Feed SSE router
from app.feed.router import router as feed_router  # noqa: E402

app.include_router(feed_router, include_in_schema=False)

# Profile API router
from app.profile.router import router as profile_router  # noqa: E402

app.include_router(profile_router)

# Token API router
from app.tokens.router import router as token_router  # noqa: E402

app.include_router(token_router)

# Documentation site (served before /static — mount order is load-bearing in FastAPI)
# html=True is load-bearing: MkDocs use_directory_urls:true generates subdirectory
# index.html files (e.g. site/admin-guide/index.html). Without html=True, FastAPI
# returns 404 for clean URLs like /guide/admin-guide/ — DO NOT remove this flag.
app.mount("/guide", StaticFiles(directory="site", html=True), name="guide")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(HTTPException)
async def ui_auth_redirect(request: Request, exc: HTTPException):
    """Redirect 401/403 errors from /log/* to the operator login page.

    All other HTTP exceptions return JSON as normal.
    """
    path = request.url.path
    if path.startswith("/log/") and exc.status_code in (401, 403):
        return RedirectResponse(url="/log/login", status_code=302)
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
