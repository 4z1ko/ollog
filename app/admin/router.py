"""Admin API router — operator account management.

All endpoints require an admin-role JWT via require_admin dependency.
Mounted at /admin/users by app/main.py.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.dependencies import require_admin
from app.auth.models import User
from app.auth.service import hash_password

router = APIRouter(prefix="/admin/users", tags=["admin"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CreateUserRequest(BaseModel):
    username: str
    callsign: str
    password: str


class ResetPasswordRequest(BaseModel):
    password: str


class SetEnabledRequest(BaseModel):
    enabled: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/", status_code=201, dependencies=[Depends(require_admin)])
async def create_user(body: CreateUserRequest):
    """Create a new operator account.

    Raises 409 if the username already exists.
    Callsign is stored uppercased. Account is enabled immediately.
    """
    existing = await User.find_one({"username": body.username})
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    user = User(
        username=body.username,
        callsign=body.callsign.upper(),
        hashed_password=hash_password(body.password),
        role="operator",
        enabled=True,
    )
    await user.insert()

    return {
        "username": user.username,
        "callsign": user.callsign,
        "enabled": user.enabled,
        "role": user.role,
    }


@router.patch("/{username}/enabled", dependencies=[Depends(require_admin)])
async def set_user_enabled(username: str, body: SetEnabledRequest):
    """Enable or disable an operator account.

    Raises 404 if the user does not exist.
    Raises 409 if disabling the last enabled admin (lockout guard).
    """
    user = await User.find_one({"username": username})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Last-admin lockout guard: refuse to disable the last enabled admin
    if not body.enabled and user.role == "admin":
        enabled_admin_count = await User.find(
            {"role": "admin", "enabled": True}
        ).count()
        if enabled_admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot disable the last enabled admin",
            )

    await user.set({User.enabled: body.enabled})

    return {"username": username, "enabled": body.enabled}


@router.post("/{username}/reset-password", dependencies=[Depends(require_admin)])
async def reset_password(username: str, body: ResetPasswordRequest):
    """Reset an operator's password.

    Raises 404 if the user does not exist.
    The new password is usable immediately after reset.
    """
    user = await User.find_one({"username": username})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await user.set({User.hashed_password: hash_password(body.password)})

    return {"username": username, "password_reset": True}


@router.get("/", dependencies=[Depends(require_admin)])
async def list_users():
    """List all user accounts.

    Returns username, callsign, role, and enabled for each user.
    hashed_password is never included in the response.
    """
    users = await User.find_all().to_list()
    return [
        {
            "username": u.username,
            "callsign": u.callsign,
            "role": u.role,
            "enabled": u.enabled,
        }
        for u in users
    ]
