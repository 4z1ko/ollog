"""Tests for the admin account management API endpoints.

Uses a separate test database (ollog_test) with its own init_beanie call
that includes both User and QSO models.
Does NOT modify conftest.py.

Integration tests require a live MongoDB at localhost:27017 and are skipped
if unavailable.
"""
import socket

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient

from app.auth.models import User
from app.auth.service import hash_password
from app.qso.models import QSO


# ---------------------------------------------------------------------------
# MongoDB availability guard
# ---------------------------------------------------------------------------

def _mongo_available() -> bool:
    """Quick synchronous check if MongoDB is reachable at localhost:27017."""
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
# Database fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def admin_db():
    """Function-scoped test database with User and QSO registered."""
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_test")
    await client.aclose()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_user(
    username: str,
    password: str,
    callsign: str,
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


async def _get_token(client: AsyncClient, username: str, password: str) -> str:
    resp = await client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )
    return resp.json()["access_token"]


async def _admin_headers(client: AsyncClient) -> dict:
    token = await _get_token(client, "admin_user", "AdminPass1!")
    return {"Authorization": f"Bearer {token}"}


async def _operator_headers(client: AsyncClient) -> dict:
    token = await _get_token(client, "op_user", "OpPass1!")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Create user tests
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_create_user_success(admin_db):
    await _create_user("admin_user", "AdminPass1!", "K0ADM", role="admin")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hdrs = await _admin_headers(client)
        resp = await client.post(
            "/admin/users/",
            json={"username": "new_op", "callsign": "W1NEW", "password": "NewPass1!"},
            headers=hdrs,
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "new_op"
    assert body["callsign"] == "W1NEW"
    assert body["enabled"] is True
    assert body["role"] == "operator"

    # Verify the new user can log in
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_resp = await client.post(
            "/auth/token",
            data={"username": "new_op", "password": "NewPass1!"},
        )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


@mongo_required
@pytest.mark.asyncio
async def test_create_user_duplicate_username(admin_db):
    await _create_user("admin_user", "AdminPass1!", "K0ADM", role="admin")
    await _create_user("existing_op", "OpPass1!", "W1EXI")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hdrs = await _admin_headers(client)
        resp = await client.post(
            "/admin/users/",
            json={"username": "existing_op", "callsign": "W1DUP", "password": "DupPass1!"},
            headers=hdrs,
        )
    assert resp.status_code == 409


@mongo_required
@pytest.mark.asyncio
async def test_create_user_callsign_uppercased(admin_db):
    await _create_user("admin_user", "AdminPass1!", "K0ADM", role="admin")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hdrs = await _admin_headers(client)
        resp = await client.post(
            "/admin/users/",
            json={"username": "op_lower", "callsign": "ab1cd", "password": "LowerPass1!"},
            headers=hdrs,
        )
    assert resp.status_code == 201
    assert resp.json()["callsign"] == "AB1CD"


@mongo_required
@pytest.mark.asyncio
async def test_create_user_forbidden_for_operator(admin_db):
    await _create_user("op_user", "OpPass1!", "W1OP")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hdrs = await _operator_headers(client)
        resp = await client.post(
            "/admin/users/",
            json={"username": "another_op", "callsign": "W1AOP", "password": "Pass1!"},
            headers=hdrs,
        )
    assert resp.status_code == 403


@mongo_required
@pytest.mark.asyncio
async def test_create_user_unauthorized(admin_db):
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/admin/users/",
            json={"username": "any", "callsign": "W1ANY", "password": "Pass1!"},
        )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Toggle enabled tests
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_disable_user(admin_db):
    await _create_user("admin_user", "AdminPass1!", "K0ADM", role="admin")
    await _create_user("op_user", "OpPass1!", "W1OP")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hdrs = await _admin_headers(client)
        resp = await client.patch(
            "/admin/users/op_user/enabled",
            json={"enabled": False},
            headers=hdrs,
        )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

    # Verify disabled user cannot log in
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_resp = await client.post(
            "/auth/token",
            data={"username": "op_user", "password": "OpPass1!"},
        )
    assert login_resp.status_code == 401


@mongo_required
@pytest.mark.asyncio
async def test_enable_user(admin_db):
    await _create_user("admin_user", "AdminPass1!", "K0ADM", role="admin")
    await _create_user("op_user", "OpPass1!", "W1OP", enabled=False)

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hdrs = await _admin_headers(client)
        resp = await client.patch(
            "/admin/users/op_user/enabled",
            json={"enabled": True},
            headers=hdrs,
        )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True

    # Verify re-enabled user can log in
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_resp = await client.post(
            "/auth/token",
            data={"username": "op_user", "password": "OpPass1!"},
        )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


@mongo_required
@pytest.mark.asyncio
async def test_disable_last_admin_refused(admin_db):
    """Disabling the only enabled admin must return 409."""
    await _create_user("admin_user", "AdminPass1!", "K0ADM", role="admin")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hdrs = await _admin_headers(client)
        resp = await client.patch(
            "/admin/users/admin_user/enabled",
            json={"enabled": False},
            headers=hdrs,
        )
    assert resp.status_code == 409
    assert "last enabled admin" in resp.json()["detail"].lower()


@mongo_required
@pytest.mark.asyncio
async def test_disable_nonexistent_user(admin_db):
    await _create_user("admin_user", "AdminPass1!", "K0ADM", role="admin")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hdrs = await _admin_headers(client)
        resp = await client.patch(
            "/admin/users/ghost_user/enabled",
            json={"enabled": False},
            headers=hdrs,
        )
    assert resp.status_code == 404


@mongo_required
@pytest.mark.asyncio
async def test_toggle_forbidden_for_operator(admin_db):
    await _create_user("op_user", "OpPass1!", "W1OP")
    await _create_user("target_op", "TargetPass1!", "W1TGT")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hdrs = await _operator_headers(client)
        resp = await client.patch(
            "/admin/users/target_op/enabled",
            json={"enabled": False},
            headers=hdrs,
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Reset password tests
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_reset_password_success(admin_db):
    await _create_user("admin_user", "AdminPass1!", "K0ADM", role="admin")
    await _create_user("op_user", "OpPass1!", "W1OP")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hdrs = await _admin_headers(client)
        resp = await client.post(
            "/admin/users/op_user/reset-password",
            json={"password": "NewOpPass99!"},
            headers=hdrs,
        )
    assert resp.status_code == 200
    assert resp.json()["password_reset"] is True

    # Verify operator can log in with new password
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        new_login = await client.post(
            "/auth/token",
            data={"username": "op_user", "password": "NewOpPass99!"},
        )
        assert new_login.status_code == 200

        # Cannot log in with old password
        old_login = await client.post(
            "/auth/token",
            data={"username": "op_user", "password": "OpPass1!"},
        )
        assert old_login.status_code == 401


@mongo_required
@pytest.mark.asyncio
async def test_reset_password_nonexistent_user(admin_db):
    await _create_user("admin_user", "AdminPass1!", "K0ADM", role="admin")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hdrs = await _admin_headers(client)
        resp = await client.post(
            "/admin/users/ghost/reset-password",
            json={"password": "SomePass1!"},
            headers=hdrs,
        )
    assert resp.status_code == 404


@mongo_required
@pytest.mark.asyncio
async def test_reset_password_forbidden_for_operator(admin_db):
    await _create_user("op_user", "OpPass1!", "W1OP")
    await _create_user("target_op", "TargetPass1!", "W1TGT")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hdrs = await _operator_headers(client)
        resp = await client.post(
            "/admin/users/target_op/reset-password",
            json={"password": "Hacked1!"},
            headers=hdrs,
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# List users tests
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_list_users(admin_db):
    await _create_user("admin_user", "AdminPass1!", "K0ADM", role="admin")
    await _create_user("op_user", "OpPass1!", "W1OP")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hdrs = await _admin_headers(client)
        resp = await client.get("/admin/users/", headers=hdrs)

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    usernames = {u["username"] for u in body}
    assert "admin_user" in usernames
    assert "op_user" in usernames

    # hashed_password must NOT appear in any response item
    for item in body:
        assert "hashed_password" not in item


@mongo_required
@pytest.mark.asyncio
async def test_list_users_forbidden_for_operator(admin_db):
    await _create_user("op_user", "OpPass1!", "W1OP")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        hdrs = await _operator_headers(client)
        resp = await client.get("/admin/users/", headers=hdrs)

    assert resp.status_code == 403
