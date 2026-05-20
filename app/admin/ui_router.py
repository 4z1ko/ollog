"""Admin UI router — browser-based operator account management.

Serves HTML pages and HTMX partial responses for the admin panel.
All protected routes require cookie-based JWT auth (require_admin_cookie).
Auth failures (401/403) are caught by the app-level exception handler in
main.py and redirected to /admin/ui/login as HTML responses.

Mounted at /admin/ui by app/main.py.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Header, Request, Response, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.dependencies import require_admin_cookie
from app.auth.models import User
from app.auth.service import create_access_token, hash_password, verify_password
from app.qso.models import QSO
from app.qso.service import clear_operator_log
from app.udp.operator_cache import operator_cache

templates = Jinja2Templates(directory="templates")

ui_router = APIRouter(prefix="/admin/ui", tags=["admin-ui"])


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

@ui_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render the admin login form."""
    return templates.TemplateResponse(
        request,
        "admin/login.html",
        {"error": None},
    )


@ui_router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    """Process login form submission.

    On success: set HttpOnly JWT cookie and redirect to users page.
    On failure: re-render login page with error message.
    """
    error = "Invalid credentials or insufficient permissions"

    user = await User.find_one({"username": username})
    if user is None or not user.enabled or user.role != "admin":
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            {"error": error},
            status_code=401,
        )

    if not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            {"error": error},
            status_code=401,
        )

    token = create_access_token(
        data={"sub": user.username, "callsign": user.callsign, "role": user.role}
    )

    response = RedirectResponse(url="/admin/ui/users", status_code=302)
    response.set_cookie(
        key="admin_token",
        value=token,
        httponly=True,
        samesite="lax",
    )
    return response


@ui_router.get("/logout")
async def logout():
    """Clear the auth cookie and redirect to the login page."""
    response = RedirectResponse(url="/admin/ui/login", status_code=302)
    response.delete_cookie(key="admin_token")
    return response


# ---------------------------------------------------------------------------
# Users management
# ---------------------------------------------------------------------------

@ui_router.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    hx_request: Annotated[str | None, Header()] = None,
    _user: User = Depends(require_admin_cookie),
):
    """Render the users management page (full or HTMX partial)."""
    users = await User.find_all().to_list()

    if hx_request:
        return templates.TemplateResponse(
            request,
            "admin/users_table.html",
            {"users": users, "error": None},
        )

    return templates.TemplateResponse(
        request,
        "admin/users.html",
        {"users": users, "error": None},
    )


@ui_router.post("/users/create", response_class=HTMLResponse)
async def create_user(
    request: Request,
    username: Annotated[str, Form()],
    callsign: Annotated[str, Form()],
    password: Annotated[str, Form()],
    _user: User = Depends(require_admin_cookie),
):
    """Create a new operator account and return the updated table partial."""
    existing = await User.find_one({"username": username})
    if existing is not None:
        users = await User.find_all().to_list()
        return templates.TemplateResponse(
            request,
            "admin/users_table.html",
            {"users": users, "error": f"Username '{username}' already exists"},
            status_code=409,
        )

    new_user = User(
        username=username,
        callsign=callsign.upper(),
        hashed_password=hash_password(password),
        role="operator",
        enabled=True,
    )
    await new_user.insert()
    operator_cache.notify_refresh()

    users = await User.find_all().to_list()
    return templates.TemplateResponse(
        request,
        "admin/users_table.html",
        {"users": users, "error": None},
    )


@ui_router.post("/users/{username}/toggle", response_class=HTMLResponse)
async def toggle_user(
    username: str,
    request: Request,
    _user: User = Depends(require_admin_cookie),
):
    """Toggle enabled/disabled status for an operator and return the updated table partial."""
    user = await User.find_one({"username": username})
    if user is None:
        users = await User.find_all().to_list()
        return templates.TemplateResponse(
            request,
            "admin/users_table.html",
            {"users": users, "error": f"User '{username}' not found"},
            status_code=404,
        )

    new_enabled = not user.enabled

    # Last-admin lockout guard: refuse to disable the last enabled admin
    if not new_enabled and user.role == "admin":
        enabled_admin_count = await User.find(
            {"role": "admin", "enabled": True}
        ).count()
        if enabled_admin_count <= 1:
            users = await User.find_all().to_list()
            return templates.TemplateResponse(
                request,
                "admin/users_table.html",
                {"users": users, "error": "Cannot disable the last enabled admin"},
                status_code=409,
            )

    await user.set({User.enabled: new_enabled})
    operator_cache.notify_refresh()

    users = await User.find_all().to_list()
    return templates.TemplateResponse(
        request,
        "admin/users_table.html",
        {"users": users, "error": None},
    )


@ui_router.post("/users/{username}/reset-password", response_class=HTMLResponse)
async def reset_password(
    username: str,
    request: Request,
    password: Annotated[str, Form()],
    _user: User = Depends(require_admin_cookie),
):
    """Reset an operator's password and return the updated table partial."""
    user = await User.find_one({"username": username})
    if user is None:
        users = await User.find_all().to_list()
        return templates.TemplateResponse(
            request,
            "admin/users_table.html",
            {"users": users, "error": f"User '{username}' not found"},
            status_code=404,
        )

    await user.set({User.hashed_password: hash_password(password)})

    users = await User.find_all().to_list()
    return templates.TemplateResponse(
        request,
        "admin/users_table.html",
        {"users": users, "error": None, "success": f"Password reset for {username}"},
    )


# ---------------------------------------------------------------------------
# Backup download
# ---------------------------------------------------------------------------

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


@ui_router.get("/backup/download")
async def backup_download(
    _user: User = Depends(require_admin_cookie),
):
    """Trigger a full MongoDB backup and return it as a .gz file download."""
    from app.backup.dump import run_backup
    from app.config import settings

    backup_path = await run_backup(settings)
    return FileResponse(
        path=backup_path,
        media_type="application/gzip",
        filename=f"ollog-backup-{backup_path.stem}.gz",
    )


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------

@ui_router.get("/restore", response_class=HTMLResponse)
async def restore_page(
    request: Request,
    hx_request: Annotated[str | None, Header()] = None,
    _user: User = Depends(require_admin_cookie),
):
    """Render restore page (full) or empty modal div (HTMX cancel).

    When the Cancel button in password_modal.html fires hx-get="/admin/ui/restore"
    with hx-target="#restore-modal" + hx-swap="outerHTML", return a bare
    <div id="restore-modal"></div> to clear the modal without a full page reload.
    """
    if hx_request:
        return HTMLResponse(content='<div id="restore-modal"></div>')
    return templates.TemplateResponse(request, "admin/restore.html", {})


@ui_router.post("/restore/upload", response_class=HTMLResponse)
async def restore_upload(
    request: Request,
    file: UploadFile,
    _user: User = Depends(require_admin_cookie),
):
    """Receive a .gz backup file, validate it, return modal or error fragment.

    Returns HTTP 200 always — HTMX 2.x ignores body on 4xx responses.
    On success: password_modal.html with temp_path embedded in hidden field.
    On failure: upload_error.html inline error; tempfile is deleted.
    """
    import os
    import tempfile
    import gzip
    import json

    raw = await file.read()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".gz")
    try:
        tmp.write(raw)
        tmp.close()
        temp_path = tmp.name

        # Validate: gzip decompressibility + NDJSON backup structure
        try:
            with gzip.open(temp_path, "rt", encoding="utf-8") as gz:
                first_line = gz.readline()
            record = json.loads(first_line)
            if "collection" not in record or "doc" not in record:
                raise ValueError("Missing required keys in backup format")
        except (OSError, EOFError, ValueError):
            # OSError: bad gzip magic bytes (gzip.BadGzipFile is an OSError)
            # EOFError: truncated/corrupt gzip file
            # ValueError: json.JSONDecodeError or explicit key check failure
            os.unlink(temp_path)
            return templates.TemplateResponse(
                request,
                "admin/restore/upload_error.html",
                {"error": "Invalid backup file: not a valid ollog backup"},
                status_code=200,
            )

        # Validation passed — return modal with temp_path in hidden field
        return templates.TemplateResponse(
            request,
            "admin/restore/password_modal.html",
            {"temp_path": temp_path},
        )
    except Exception:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise


@ui_router.post("/restore/confirm", response_class=HTMLResponse)
async def restore_confirm(
    request: Request,
    password: Annotated[str, Form()],
    temp_path: Annotated[str, Form()],
    current_user: User = Depends(require_admin_cookie),
):
    """Verify password, auto-backup, drop all collections, restore from file.

    Path traversal guard runs before any file access.
    Auto-backup runs before any db.drop() operation (OPS-01).
    Temp file is deleted in finally block regardless of outcome.
    Returns HTTP 200 always — HTMX 2.x ignores body on 4xx responses.
    """
    import os
    import pathlib
    import tempfile
    from app.backup.dump import run_backup
    from app.backup.restore import run_restore
    from app.config import settings

    # Path traversal guard — MUST run before any file access
    try:
        p = pathlib.Path(temp_path).resolve()
        tmpdir = pathlib.Path(tempfile.gettempdir()).resolve()
        if not str(p).startswith(str(tmpdir)) or p.suffix != ".gz" or not p.exists():
            raise ValueError("Invalid temp_path")
    except (ValueError, OSError):
        return HTMLResponse(content="<p>Invalid request</p>", status_code=400)

    # Password check — current_user already hydrated by require_admin_cookie
    if not verify_password(password, current_user.hashed_password):
        return templates.TemplateResponse(
            request,
            "admin/restore/password_error.html",
            {"error": "Incorrect password", "temp_path": temp_path},
            status_code=200,
        )

    # Auto-backup before any destructive operation (OPS-01)
    try:
        auto_backup_path = await run_backup(settings)
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "admin/restore/restore_failure.html",
            {"error": f"Auto-backup failed: {exc}", "backup_path": None},
            status_code=200,
        )

    # Restore
    try:
        await run_restore(str(p), settings)
        return templates.TemplateResponse(
            request,
            "admin/restore/restore_success.html",
            {"backup_path": auto_backup_path.name},
            status_code=200,
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "admin/restore/restore_failure.html",
            {"error": str(exc), "backup_path": auto_backup_path.name},
            status_code=200,
        )
    finally:
        if p.exists():
            os.unlink(p)


@ui_router.get("/users/{username}/clear-log/modal", response_class=HTMLResponse)
async def admin_clear_log_modal(
    username: str,
    request: Request,
    current_user: User = Depends(require_admin_cookie),
):
    """Return confirmation modal fragment with target operator's QSO count.

    Always HTTP 200 — HTMX 2.x will not swap on 4xx.
    On not-found, returns the empty placeholder so the UI degrades gracefully.
    """
    target_user = await User.find_one({"username": username})
    if target_user is None:
        return HTMLResponse(
            content='<div id="admin-clear-log-modal"></div>',
            status_code=200,
        )

    count = await QSO.find(
        {"_operator": target_user.callsign, "_deleted": False}
    ).count()
    return templates.TemplateResponse(
        request,
        "admin/clear_log_modal.html",
        {
            "username": username,
            "callsign": target_user.callsign,
            "count": count,
            "error": None,
        },
    )


@ui_router.post("/users/{username}/clear-log", response_class=HTMLResponse)
async def admin_clear_log_confirm(
    username: str,
    request: Request,
    password: Annotated[str, Form()],
    current_user: User = Depends(require_admin_cookie),
):
    """Verify admin password and delete all target operator's QSOs.

    Always HTTP 200 — HTMX 2.x ignores body on 4xx.
    current_user is the admin (from the dependency); target_user is the operator
    being cleared (looked up by URL path param).

    SECURITY: password is verified against current_user.hashed_password
    (the admin's OWN password), NOT target_user.hashed_password.
    """
    target_user = await User.find_one({"username": username})
    if target_user is None:
        return HTMLResponse(
            content='<div id="admin-clear-log-modal"></div>',
            status_code=200,
        )

    if not verify_password(password, current_user.hashed_password):
        count = await QSO.find(
            {"_operator": target_user.callsign, "_deleted": False}
        ).count()
        return templates.TemplateResponse(
            request,
            "admin/clear_log_modal.html",
            {
                "username": username,
                "callsign": target_user.callsign,
                "count": count,
                "error": "Incorrect password. No QSOs were deleted.",
            },
            status_code=200,
        )

    deleted = await clear_operator_log(target_user.callsign)
    return templates.TemplateResponse(
        request,
        "admin/clear_log_success.html",
        {"callsign": target_user.callsign, "deleted": deleted},
        status_code=200,
    )


@ui_router.get("/users/{username}/clear-log/cancel", response_class=HTMLResponse)
async def admin_clear_log_cancel(
    username: str,
    _user: User = Depends(require_admin_cookie),
):
    """Clear the modal without a page reload."""
    return HTMLResponse(content='<div id="admin-clear-log-modal"></div>')
