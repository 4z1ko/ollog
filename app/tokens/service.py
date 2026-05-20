"""Token generation, hashing, verification, and name validation.

All cryptographic operations use stdlib only (hmac, hashlib, secrets).
No third-party crypto dependencies.
"""
import hmac
import hashlib
import re
import secrets
from typing import Any

from app.config import settings

_PREFIX_LEN = 8
_TOKEN_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,80}$")


def generate_api_token() -> tuple[str, str]:
    """Generate a new API token.

    Returns a tuple of (full_token, token_prefix) where:
    - full_token is "ollog_" + 43-char URL-safe body (256 bits of entropy)
    - token_prefix is the first 8 chars of the body, used for fast DB lookup
    """
    body = secrets.token_urlsafe(32)
    full_token = f"ollog_{body}"
    token_prefix = body[:_PREFIX_LEN]
    return full_token, token_prefix


def hash_api_token(token: str) -> str:
    """Return HMAC-SHA256 hex digest of token using api_token_secret.

    The raw token is NEVER stored — only this hash is persisted.
    """
    key = settings.api_token_secret.get_secret_value().encode()
    return hmac.new(key, token.encode(), hashlib.sha256).hexdigest()


def verify_api_token(token: str, hashed: str) -> bool:
    """Constant-time verification of a raw token against its stored hash.

    Uses hmac.compare_digest to prevent timing attacks.
    """
    return hmac.compare_digest(hash_api_token(token), hashed)


def validate_token_name(name: str) -> str:
    """Validate API token name and return it unchanged if valid.

    Raises ValueError if name is outside alphanumeric + hyphen/underscore,
    or is not 1-80 characters long.
    """
    if not _TOKEN_NAME_RE.match(name):
        raise ValueError(
            "Token name must be 1-80 characters: alphanumeric, hyphens, underscores only"
        )
    return name


def token_is_active(token: Any) -> bool:
    """Return True if token is enabled and not expired.

    Checks both enabled flag (set to False on revoke) and expires_at
    (None means never expires). Used by Phase 27 X-API-Key auth dependency.

    Accepts any object with .enabled (bool) and .expires_at (datetime | None)
    attributes — uses duck typing to avoid circular imports at module load time.
    """
    from datetime import datetime, timezone

    if not token.enabled:
        return False
    if token.expires_at is not None:
        expires = token.expires_at
        # MongoDB may return timezone-naive datetimes stored as UTC; normalise to
        # aware UTC before comparison to avoid TypeError on Python 3.12+.
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= datetime.now(tz=timezone.utc):
            return False
    return True
