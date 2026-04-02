from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.models import User
from app.auth.service import create_access_token, verify_password
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2-compatible login endpoint.

    Accepts username + password as form fields.
    Returns a JWT access token on success, 401 on bad credentials.
    """
    user = await User.find_one({"username": form_data.username})
    if user is None or not user.enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        data={
            "sub": user.username,
            "callsign": user.callsign,
            "role": user.role,
        }
    )
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return {
        "username": current_user.username,
        "callsign": current_user.callsign,
        "role": current_user.role,
    }
