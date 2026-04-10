"""Tests for the JWT authentication service.

Uses a separate test database (ollog_test) with its own init_beanie call
that includes the User model.  Does NOT modify conftest.py (owned by 01-02).

Static tests run without MongoDB.
Integration tests require a live MongoDB at localhost:27017 and are skipped
if unavailable.
"""
import os
from datetime import timedelta

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient

from app.auth.models import User
from app.auth.service import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.qso.models import QSO


# ---------------------------------------------------------------------------
# Static / import-only tests — no MongoDB required
# ---------------------------------------------------------------------------

def test_user_collection_name():
    """User documents are stored in the 'users' collection."""
    assert User.Settings.name == "users"


def test_user_has_unique_username_index():
    """User model declares a unique index on username."""
    assert len(User.Settings.indexes) == 1
    idx = User.Settings.indexes[0]
    assert idx.document.get("unique") is True
    assert "username" in idx.document["key"]


def test_user_default_role_is_operator():
    """User.role defaults to 'operator'."""
    assert User.model_fields["role"].default == "operator"


def test_user_enabled_defaults_to_true():
    """User.enabled defaults to True."""
    assert User.model_fields["enabled"].default is True


def test_hash_and_verify_password():
    """hash_password() and verify_password() round-trip correctly."""
    plain = "hunter2"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrong", hashed)


def test_create_access_token_contains_required_claims():
    """JWT token contains sub, callsign, role, and exp claims."""
    token = create_access_token(
        data={"sub": "testop", "callsign": "W1TEST", "role": "operator"}
    )
    payload = decode_access_token(token)
    assert payload["sub"] == "testop"
    assert payload["callsign"] == "W1TEST"
    assert payload["role"] == "operator"
    assert "exp" in payload


def test_create_access_token_with_custom_expiry():
    """Token with positive timedelta is valid; expired token raises."""
    import jwt as pyjwt

    valid_token = create_access_token(
        data={"sub": "testop", "callsign": "W1TEST", "role": "operator"},
        expires_delta=timedelta(minutes=5),
    )
    payload = decode_access_token(valid_token)
    assert payload["sub"] == "testop"

    expired_token = create_access_token(
        data={"sub": "testop", "callsign": "W1TEST", "role": "operator"},
        expires_delta=timedelta(minutes=-1),
    )
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_access_token(expired_token)


def test_no_jose_import():
    """Ensure python-jose is not imported anywhere in app.auth."""
    import app.auth.service as svc_module
    import app.auth.dependencies as dep_module
    import inspect

    svc_src = inspect.getsource(svc_module)
    dep_src = inspect.getsource(dep_module)

    assert "from jose" not in svc_src, "python-jose must NOT be used in service"
    assert "from jose" not in dep_src, "python-jose must NOT be used in dependencies"
    assert "import jose" not in svc_src
    assert "import jose" not in dep_src


def test_no_passlib_import():
    """Ensure passlib is not imported anywhere in app.auth."""
    import app.auth.service as svc_module
    import inspect

    svc_src = inspect.getsource(svc_module)
    assert "passlib" not in svc_src, "passlib must NOT be used — use pwdlib"


# ---------------------------------------------------------------------------
# MongoDB availability check
# ---------------------------------------------------------------------------

def _mongo_available() -> bool:
    """Quick synchronous check if MongoDB is reachable at localhost:27017."""
    import socket
    try:
        sock = socket.create_connection(("localhost", 27017), timeout=1)
        sock.close()
        return True
    except OSError:
        return False


mongo_required = pytest.mark.skipif(
    not _mongo_available(),
    reason="MongoDB not available at localhost:27017",
)


# ---------------------------------------------------------------------------
# Database fixture — includes both QSO and User so init_beanie is complete
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def auth_db():
    """Function-scoped test database with both QSO and User registered."""
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_test"]
    await init_beanie(database=db, document_models=[QSO, User])
    yield db
    await client.drop_database("ollog_test")
    client.close()


# ---------------------------------------------------------------------------
# Helper: create a test user directly in the database
# ---------------------------------------------------------------------------

async def _create_test_user(
    username: str = "testop",
    password: str = "secret123",
    callsign: str = "W1TEST",
    role: str = "operator",
    enabled: bool = True,
) -> User:
    user = User(
        username=username,
        hashed_password=hash_password(password),
        callsign=callsign,
        role=role,
        enabled=enabled,
    )
    await user.insert()
    return user


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_login_valid_credentials(auth_db):
    await _create_test_user()
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/auth/token",
            data={"username": "testop", "password": "secret123"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@mongo_required
@pytest.mark.asyncio
async def test_login_invalid_password(auth_db):
    await _create_test_user()
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/auth/token",
            data={"username": "testop", "password": "wrongpassword"},
        )
    assert resp.status_code == 401


@mongo_required
@pytest.mark.asyncio
async def test_login_nonexistent_user(auth_db):
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/auth/token",
            data={"username": "nobody", "password": "secret123"},
        )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /auth/me tests
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_me_authenticated(auth_db):
    await _create_test_user(callsign="W1TEST", role="operator")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login_resp = await ac.post(
            "/auth/token",
            data={"username": "testop", "password": "secret123"},
        )
        token = login_resp.json()["access_token"]
        me_resp = await ac.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
    assert me_resp.status_code == 200
    body = me_resp.json()
    assert body["username"] == "testop"
    assert body["callsign"] == "W1TEST"
    assert body["role"] == "operator"


@mongo_required
@pytest.mark.asyncio
async def test_me_no_token(auth_db):
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/auth/me")
    assert resp.status_code == 401


@mongo_required
@pytest.mark.asyncio
async def test_me_invalid_token(auth_db):
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(
            "/auth/me", headers={"Authorization": "Bearer totalgarbage.not.valid"}
        )
    assert resp.status_code == 401


@mongo_required
@pytest.mark.asyncio
async def test_me_expired_token(auth_db):
    await _create_test_user()
    # Create a token that expired one minute ago
    expired_token = create_access_token(
        data={"sub": "testop", "callsign": "W1TEST", "role": "operator"},
        expires_delta=timedelta(minutes=-1),
    )
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(
            "/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
        )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /api/whoami — callsign from JWT, not request
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_protected_endpoint_returns_callsign(auth_db):
    await _create_test_user(callsign="W1TEST")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login_resp = await ac.post(
            "/auth/token",
            data={"username": "testop", "password": "secret123"},
        )
        token = login_resp.json()["access_token"]
        whoami_resp = await ac.get(
            "/api/whoami", headers={"Authorization": f"Bearer {token}"}
        )
    assert whoami_resp.status_code == 200
    assert whoami_resp.json()["callsign"] == "W1TEST"


# ---------------------------------------------------------------------------
# Admin bootstrap test
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_admin_bootstrap(auth_db):
    """Admin user is created when env vars are set and startup runs."""
    os.environ["ADMIN_USERNAME"] = "bootstrapadmin"
    os.environ["ADMIN_PASSWORD"] = "AdminPass99!"
    os.environ["ADMIN_CALLSIGN"] = "K0ADM"

    try:
        from app.auth import bootstrap as bootstrap_module
        from importlib import reload
        import app.config as config_module
        reload(config_module)
        from app.config import Settings
        patched_settings = Settings()
        # Temporarily replace settings used by _bootstrap_admin
        original_settings = bootstrap_module._bootstrap_admin.__globals__.get("settings")
        bootstrap_module._bootstrap_admin.__globals__["settings"] = patched_settings

        await bootstrap_module._bootstrap_admin()

        admin = await User.find_one({"username": "bootstrapadmin"})
        assert admin is not None
        assert admin.role == "admin"
        assert admin.callsign == "K0ADM"
    finally:
        for key in ("ADMIN_USERNAME", "ADMIN_PASSWORD", "ADMIN_CALLSIGN"):
            os.environ.pop(key, None)
        if original_settings is not None:
            bootstrap_module._bootstrap_admin.__globals__["settings"] = original_settings


# ---------------------------------------------------------------------------
# Disabled user tests
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_disabled_user_rejected_at_login(auth_db):
    """A disabled user cannot log in."""
    await _create_test_user(enabled=False)
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/auth/token",
            data={"username": "testop", "password": "secret123"},
        )
    assert resp.status_code == 401


@mongo_required
@pytest.mark.asyncio
async def test_disabled_user_rejected_via_token(auth_db):
    """A token for a disabled user is rejected at /auth/me."""
    # Create a token manually (bypassing login) for a disabled user
    disabled_token = create_access_token(
        data={"sub": "testop", "callsign": "W1TEST", "role": "operator"},
    )
    await _create_test_user(enabled=False)
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get(
            "/auth/me", headers={"Authorization": f"Bearer {disabled_token}"}
        )
    assert resp.status_code == 401
