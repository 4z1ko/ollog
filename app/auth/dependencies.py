from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError

from app.auth.models import User
from app.auth.service import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """FastAPI dependency: decode JWT and return the authenticated User.

    Raises 401 if the token is missing, invalid, expired, or the user
    is not found / disabled.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    user = await User.find_one({"username": username})
    if user is None or not user.enabled:
        raise credentials_exception

    return user


async def get_current_operator_callsign(
    user: User = Depends(get_current_user),
) -> str:
    """FastAPI dependency: return the callsign injected from the JWT.

    This is the single authoritative callsign injection point for all QSO
    operations.  Callsign is NEVER taken from request body or query params.
    """
    return user.callsign


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency: require the authenticated user to have role='admin'.

    Raises 403 Forbidden for non-admin users.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def get_current_user_cookie(
    access_token: str | None = Cookie(default=None),
) -> User:
    """FastAPI dependency: decode JWT from HttpOnly cookie and return the authenticated User.

    Used by UI routes that receive auth via cookie instead of Authorization header.
    Raises 401 if the cookie is missing, invalid, expired, or the user is not found / disabled.
    """
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = decode_access_token(access_token)
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    user = await User.find_one({"username": username})
    if user is None or not user.enabled:
        raise credentials_exception

    return user


async def get_current_operator_callsign_cookie(
    user: User = Depends(get_current_user_cookie),
) -> str:
    """Cookie-auth version of callsign injection for UI routes under /log/."""
    return user.callsign


async def require_admin_cookie(
    user: User = Depends(get_current_user_cookie),
) -> User:
    """FastAPI dependency: require cookie-authenticated user to have role='admin'.

    Raises 403 Forbidden for non-admin users.
    Used by UI routes — auth failures are caught by the app exception handler
    and redirected to /admin/ui/login instead of returning JSON.
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user
