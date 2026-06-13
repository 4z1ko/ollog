from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from app.database import init_db, close_db, get_client
from app.auth.bootstrap import _bootstrap_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _bootstrap_admin()
    yield
    await close_db()


app = FastAPI(title="ollog-admin", version="0.1.0", lifespan=lifespan)

from app.auth.router import router as auth_router  # noqa: E402
from app.admin.router import router as admin_router  # noqa: E402
from app.admin.ui_router import ui_router  # noqa: E402

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(ui_router, include_in_schema=False)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/favicon", StaticFiles(directory="favicon"), name="favicon")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    return FileResponse(path="favicon/favicon.ico")


@app.exception_handler(HTTPException)
async def ui_auth_redirect(request: Request, exc: HTTPException):
    path = request.url.path
    if path.startswith("/admin/ui/") and exc.status_code in (401, 403):
        return RedirectResponse(url="/admin/ui/login", status_code=302)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health")
async def health():
    client = get_client()
    if client is None:
        return JSONResponse(status_code=503, content={"status": "error", "mongodb": "disconnected"})
    try:
        await client.admin.command("ping")
        return {"status": "ok", "mongodb": "connected"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "error", "mongodb": "disconnected"})
