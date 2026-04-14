"""Admin UI router — browser-based operator account management.

Serves HTML pages and HTMX partial responses for the admin panel.
All protected routes require cookie-based JWT auth (require_admin_cookie).
Auth failures (401/403) are caught by the app-level exception handler in
main.py and redirected to /admin/ui/login as HTML responses.

Mounted at /admin/ui by app/main.py.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Header, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.dependencies import require_admin_cookie
from app.auth.models import User
from app.auth.service import create_access_token, hash_password, verify_password

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
