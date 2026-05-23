import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from bson import ObjectId
from pymongo import UpdateOne
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database import init_db, close_db, get_client
from app.auth.bootstrap import _bootstrap_admin

_templates = Jinja2Templates(directory="templates")

logger = logging.getLogger(__name__)


async def backfill_created_at():
    """One-time idempotent migration: stamp _created_at on QSOs that lack it.

    For each document missing _created_at, derives the timestamp from the
    ObjectId's embedded creation time. Falls back to now(UTC) for non-ObjectId _id values.
    """
    from app.qso.models import QSO
    collection = QSO.get_pymongo_collection()
    cursor = collection.find(
        {"_created_at": {"$exists": False}},
        {"_id": 1},
    )
    ops = []
    async for doc in cursor:
        oid = doc["_id"]
        if isinstance(oid, ObjectId):
            ts = oid.generation_time.replace(tzinfo=timezone.utc)
        else:
            ts = datetime.now(timezone.utc)
        ops.append(UpdateOne({"_id": oid}, {"$set": {"_created_at": ts}}))

    if ops:
        result = await collection.bulk_write(ops, ordered=False)
        logger.info("_created_at backfill: %d documents updated", result.modified_count)
    else:
        logger.info("_created_at backfill: 0 documents — already up to date")


async def normalize_time_on():
    """One-time idempotent migration: pad 4-digit HHMM TIME_ON values to HHMM00.

    Uses an anchored regex filter (^\\d{4}$) to match only exactly-4-digit strings,
    preventing double-padding on repeated runs. Aggregation pipeline $concat appends
    "00" server-side — no Python loop required.
    """
    from app.qso.models import QSO
    collection = QSO.get_pymongo_collection()
    result = await collection.update_many(
        {"TIME_ON": {"$regex": r"^\d{4}$"}},
        [{"$set": {"TIME_ON": {"$concat": ["$TIME_ON", "00"]}}}],
    )
    if result.modified_count:
        logger.info("TIME_ON migration: %d documents updated", result.modified_count)
    else:
        logger.info("TIME_ON migration: 0 documents — already up to date")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _bootstrap_admin()
    await backfill_created_at()   # D-05: one-time idempotent migration
    await normalize_time_on()     # Phase 52 (D-02): pad 4-digit TIME_ON to 6-digit
    # Start change stream watcher for live feed
    client = get_client()
    app.state.watcher_task = None
    if client is not None:
        from app.feed.manager import manager as feed_manager, watch_qsos  # noqa: E402
        collection = client[settings.mongodb_db]["qsos"]
        app.state.watcher_task = asyncio.create_task(
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

    aclog_bridge_manager = None
    if settings.aclog_enabled:
        from app.aclog.manager import ACLogBridgeManager

        aclog_bridge_manager = ACLogBridgeManager(
            scan_seconds=settings.aclog_scan_seconds,
            reconnect_seconds=settings.aclog_reconnect_seconds,
        )
        aclog_bridge_manager.start()
        logger.info("ACLog bridge manager started")

    # Start backup scheduler (conditional on BACKUP_SCHEDULE env var)
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
    if app.state.watcher_task is not None:
        app.state.watcher_task.cancel()
        try:
            await app.state.watcher_task
        except asyncio.CancelledError:
            pass
    if aclog_bridge_manager is not None:
        await aclog_bridge_manager.stop()
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

# Stats UI router (browser-based, cookie auth, Jinja2 templates)
from app.stats.router import stats_router  # noqa: E402

app.include_router(stats_router, include_in_schema=False)

# Documentation site (served before /static — mount order is load-bearing in FastAPI)
# html=True is load-bearing: MkDocs use_directory_urls:true generates subdirectory
# index.html files (e.g. site/admin-guide/index.html). Without html=True, FastAPI
# returns 404 for clean URLs like /guide/admin-guide/ — DO NOT remove this flag.
app.mount("/guide", StaticFiles(directory="site", html=True), name="guide")

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# llms.txt endpoints — static content served from disk via FileResponse.
# Routes are excluded from the OpenAPI schema (LLMS-03).
# Editing static/llms.txt or static/llms-full.txt and restarting the app
# serves updated content with no Python code change (LLMS-04).
@app.get("/llms.txt", include_in_schema=False)
async def llms_index():
    """LLM tooling index — project title, description, section links."""
    return FileResponse(
        path="static/llms.txt",
        media_type="text/plain; charset=utf-8",
    )


@app.get("/llms-full.txt", include_in_schema=False)
async def llms_full():
    """Full LLM reference — API docs, ADIF field guide, getting started."""
    return FileResponse(
        path="static/llms-full.txt",
        media_type="text/plain; charset=utf-8",
    )


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
