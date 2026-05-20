from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError  # noqa: F401 — re-exported for convenience
from pwdlib import PasswordHash

from app.config import settings

# Argon2 via pwdlib — recommended() selects Argon2 as the best available hasher
password_hash = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    """Hash a plaintext password using Argon2."""
    return password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored Argon2 hash."""
    return password_hash.verify(plain, hashed)


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT token.

    Expected keys in data: sub (username), callsign, role.
    The 'exp' claim is added automatically.
    Returns a compact JWT string.
    """
    to_encode = data.copy()
    if expires_delta is not None:
        expire = datetime.now(tz=timezone.utc) + expires_delta
    else:
        expire = datetime.now(tz=timezone.utc) + timedelta(
            minutes=settings.jwt_expire_minutes
        )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT token.

    Returns the payload dict on success.
    Raises jwt.InvalidTokenError (or subclass) on failure (expired, bad sig, etc).
    """
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
    )
