"""Profile API router — GET and PATCH /api/profile."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.profile.schemas import ProfileResponse, ProfileUpdateRequest
from app.profile.service import update_profile
from app.qso.custom_fields import custom_fields_for_user

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/", response_model=ProfileResponse, status_code=200)
async def get_profile(
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    """Return the authenticated operator's profile.

    Operator identity is derived exclusively from the JWT — no callsign
    parameter is accepted. A user with no profile fields set receives
    all-null optional fields (not an error).
    """
    data = user.model_dump()
    data["custom_qso_fields"] = [field.model_dump() for field in custom_fields_for_user(user)]
    return ProfileResponse.model_validate(data)


@router.patch("/", response_model=ProfileResponse, status_code=200)
async def patch_profile(
    body: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    """Update the authenticated operator's profile fields.

    Only fields present in the request body are updated (partial update).
    Absent fields are left unchanged. If my_gridsquare is updated,
    latitude and longitude are auto-computed from the grid center.
    """
    updates = body.model_dump(exclude_unset=True)
    updated_user = await update_profile(user, updates)
    data = updated_user.model_dump()
    data["custom_qso_fields"] = [
        field.model_dump() for field in custom_fields_for_user(updated_user)
    ]
    return ProfileResponse.model_validate(data)
