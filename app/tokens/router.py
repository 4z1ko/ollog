"""REST CRUD router for API tokens — /api/tokens.

Bearer JWT auth only. Returns JSON. Used by external REST and UDP ADIF callers
to create, list, and revoke their own API tokens.
"""
from datetime import datetime, timezone
from typing import Annotated, Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.internal_logs.service import app_logger
from app.tokens.models import ApiToken
from app.tokens.service import generate_api_token, hash_api_token, validate_token_name

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    id: str
    name: str
    token_prefix: str
    created_at: datetime
    expires_at: Optional[datetime]
    enabled: bool


class TokenCreateResponse(TokenResponse):
    full_token: str  # present only in POST response — never returned again


# ---------------------------------------------------------------------------
# POST /api/tokens — create a token (201)
# ---------------------------------------------------------------------------


@router.post("/", status_code=201, response_model=TokenCreateResponse)
async def create_token(
    user: Annotated[User, Depends(get_current_user)],
    name: Annotated[str, Form()],
    expires_at: Annotated[Optional[str], Form()] = None,
):
    """Create a new API token for the authenticated user.

    Returns the full plaintext token exactly once in the response body.
    The raw token is never stored — only the HMAC-SHA256 hash is persisted.
    """
    try:
        validate_token_name(name)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    expires_at_dt: Optional[datetime] = None
    if expires_at and expires_at.strip():
        try:
            expires_at_dt = datetime.strptime(expires_at.strip(), "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid date format: use YYYY-MM-DD",
            ) from exc

    full_token, token_prefix = generate_api_token()
    hashed_token = hash_api_token(full_token)

    doc = ApiToken(
        user_id=user.id,
        name=name,
        token_prefix=token_prefix,
        hashed_token=hashed_token,
        expires_at=expires_at_dt,
    )
    await doc.insert()
    from app.udp.token_cache import token_cache
    token_cache.notify_refresh()
    await app_logger.info(
        "API token created",
        source="app.tokens.router",
        event_type="api_token_created",
        transport="HTTP",
        metadata={
            "username": user.username,
            "callsign": user.callsign,
            "token_id": str(doc.id),
            "token_name": doc.name,
            "token_prefix": doc.token_prefix,
        },
    )

    return TokenCreateResponse(
        id=str(doc.id),
        name=doc.name,
        token_prefix=doc.token_prefix,
        created_at=doc.created_at,
        expires_at=doc.expires_at,
        enabled=doc.enabled,
        full_token=full_token,
    )


# ---------------------------------------------------------------------------
# GET /api/tokens — list active tokens (200)
# ---------------------------------------------------------------------------


@router.get("/", status_code=200, response_model=list[TokenResponse])
async def list_tokens(
    user: Annotated[User, Depends(get_current_user)],
):
    """Return all active (non-revoked) tokens for the authenticated user."""
    tokens = (
        await ApiToken.find(
            ApiToken.user_id == user.id,
            ApiToken.enabled == True,  # noqa: E712
        )
        .sort(-ApiToken.created_at)
        .to_list()
    )
    return [
        TokenResponse(
            id=str(t.id),
            name=t.name,
            token_prefix=t.token_prefix,
            created_at=t.created_at,
            expires_at=t.expires_at,
            enabled=t.enabled,
        )
        for t in tokens
    ]


# ---------------------------------------------------------------------------
# DELETE /api/tokens/{token_id} — revoke a token (204)
# ---------------------------------------------------------------------------


@router.delete("/{token_id}", status_code=204)
async def revoke_token(
    token_id: str,
    user: Annotated[User, Depends(get_current_user)],
):
    """Revoke (disable) a token owned by the authenticated user.

    Sets enabled=False — the token can no longer be used for authentication.
    Returns 204 No Content on success; 404 if not found or not owned by caller.
    """
    try:
        oid = PydanticObjectId(token_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        ) from exc

    token = await ApiToken.get(oid)
    if token is None or token.user_id != user.id or not token.enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        )

    await token.set({ApiToken.enabled: False})
    from app.udp.token_cache import token_cache
    token_cache.notify_refresh()
    await app_logger.info(
        "API token revoked",
        source="app.tokens.router",
        event_type="api_token_revoked",
        transport="HTTP",
        metadata={
            "username": user.username,
            "callsign": user.callsign,
            "token_id": str(token.id),
            "token_name": token.name,
            "token_prefix": token.token_prefix,
        },
    )
    return Response(status_code=204)
