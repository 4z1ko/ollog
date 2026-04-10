from datetime import datetime, timezone

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jwt import InvalidTokenError

from app.auth.models import User
from app.auth.service import decode_access_token
from app.tokens.models import ApiToken
from app.tokens.service import token_is_active, verify_api_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Private scheme objects used ONLY by dual-auth dependencies.
# auto_error=False so neither raises before the other can run.
# The existing oauth2_scheme (auto_error=True) is NOT changed.
_oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
_apikey_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


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


async def get_current_admin_cookie(
    admin_token: str | None = Cookie(default=None),
) -> User:
    """FastAPI dependency: decode JWT from HttpOnly admin_token cookie.

    Used by admin UI routes served by the admin container (port 8001).
    Raises 401 if the cookie is missing, invalid, expired, or the user
    is not found / disabled.
    """
    if admin_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = decode_access_token(admin_token)
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    user = await User.find_one({"username": username})
    if user is None or not user.enabled:
        raise credentials_exception

    return user


async def require_admin_cookie(
    user: User = Depends(get_current_admin_cookie),
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


async def _resolve_user_from_api_key(api_key: str) -> User | None:
    """Private helper: resolve a User from a raw X-API-Key header value.

    Never raises HTTPException — returns None on any failure. Callers are
    responsible for raising the appropriate HTTP error if None is returned.

    Lookup strategy:
    1. Guard: reject obviously-invalid keys without a DB call.
    2. Extract the 8-char prefix for a fast indexed DB lookup.
    3. For each candidate token: check active first (cheap), then HMAC-verify.
    4. On match: load the user, check enabled, fire-and-forget last_used_at update.
    """
    # Guard: all valid ollog tokens start with "ollog_" and have at least
    # 6 + 8 = 14 characters (prefix + at least the 8-char lookup prefix).
    if not api_key.startswith("ollog_") or len(api_key) < 14:
        return None

    # Extract the first 8 chars of the token body (after the "ollog_" sentinel)
    prefix = api_key[6:14]

    candidates = await ApiToken.find(ApiToken.token_prefix == prefix).to_list()

    for candidate in candidates:
        if not token_is_active(candidate):
            continue
        if not verify_api_token(api_key, candidate.hashed_token):
            continue
        # Candidate verified — load user
        user = await User.find_one({"_id": candidate.user_id})
        if user is not None and user.enabled:
            # Fire-and-forget last_used_at timestamp update
            await candidate.set({ApiToken.last_used_at: datetime.now(tz=timezone.utc)})
            return user

    return None


async def get_current_user_jwt_or_apikey(
    bearer_token: str | None = Depends(_oauth2_scheme_optional),
    api_key: str | None = Depends(_apikey_scheme),
) -> User:
    """Dual-auth dependency for QSO REST endpoints.

    Accepts either JWT Bearer token or X-API-Key header.
    Returns the authenticated User with identical operator isolation
    to get_current_user. Raises HTTP 401 (not 403) for all failure modes.

    Do NOT use this dependency on admin, profile, or token management routes —
    those must remain JWT-only via get_current_user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Path 1: JWT Bearer (tried first — existing behaviour for JWT callers)
    if bearer_token is not None:
        try:
            payload = decode_access_token(bearer_token)
            username: str | None = payload.get("sub")
            if username is None:
                raise credentials_exception
        except InvalidTokenError:
            raise credentials_exception
        user = await User.find_one({"username": username})
        if user is None or not user.enabled:
            raise credentials_exception
        return user

    # Path 2: X-API-Key header
    if api_key is not None:
        user = await _resolve_user_from_api_key(api_key)
        if user is not None:
            return user

    # Both paths failed — raise 401 (NOT 403)
    raise credentials_exception


async def get_current_operator_callsign_jwt_or_apikey(
    user: User = Depends(get_current_user_jwt_or_apikey),
) -> str:
    """Dual-auth callsign injection for QSO list/get/patch/delete endpoints.

    Thin wrapper over get_current_user_jwt_or_apikey, mirroring
    get_current_operator_callsign. Callsign is NEVER taken from the request.
    """
    return user.callsign
