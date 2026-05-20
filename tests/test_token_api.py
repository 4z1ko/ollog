"""Integration tests for the REST token CRUD API.

All tests require a live MongoDB at localhost:27017 and are skipped if unavailable.
Mirrors the fixture pattern established in tests/test_qso_api.py.

API_TOKEN_SECRET must be set before app.config is imported.
"""
import os
import socket

# Set before any app imports so pydantic-settings picks it up at Settings() instantiation time
os.environ.setdefault("API_TOKEN_SECRET", "test-token-secret-for-unit-tests")

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient

from app.auth.models import User
from app.auth.service import hash_password
from app.qso.models import QSO
from app.tokens.models import ApiToken


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
# Local fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def token_api_db():
    """Function-scoped test database with User, QSO, and ApiToken registered."""
    try:
        s = socket.create_connection(("localhost", 27017), timeout=1)
        s.close()
    except OSError:
        pytest.skip("MongoDB not available at localhost:27017")

    client = AsyncMongoClient(
        "mongodb://localhost:27017/?directConnection=true",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_token_api_test"]
    await init_beanie(database=db, document_models=[User, QSO, ApiToken])
    yield db
    await client.drop_database("ollog_token_api_test")
    await client.aclose()


async def _create_user(
    username: str,
    password: str,
    callsign: str,
    role: str = "operator",
) -> User:
    user = User(
        username=username,
        hashed_password=hash_password(password),
        callsign=callsign,
        role=role,
        enabled=True,
    )
    await user.insert()
    return user


async def _get_token(client: AsyncClient, username: str, password: str) -> str:
    resp = await client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def _bearer(jwt: str) -> dict:
    return {"Authorization": f"Bearer {jwt}"}


# ---------------------------------------------------------------------------
# Test 1: POST creates token, returns full_token exactly once
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_create_token_returns_full_token(token_api_db):
    """POST /api/tokens returns 201 with full_token starting with 'ollog_'."""
    await _create_user("op1", "Pass1234!", "W1AAA")
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        jwt = await _get_token(client, "op1", "Pass1234!")
        resp = await client.post(
            "/api/tokens/",
            data={"name": "my-logger"},
            headers=_bearer(jwt),
        )

    assert resp.status_code == 201
    body = resp.json()
    assert "full_token" in body, "POST response must include full_token"
    assert body["full_token"].startswith("ollog_"), "full_token must start with 'ollog_'"
    assert len(body["token_prefix"]) == 8, "token_prefix must be 8 chars"
    assert body["name"] == "my-logger"
    assert body["enabled"] is True


# ---------------------------------------------------------------------------
# Test 2: POST with expiry sets expires_at
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_create_token_with_expiry(token_api_db):
    """POST /api/tokens with expires_at='2099-12-31' sets expires_at to non-None."""
    await _create_user("op2", "Pass1234!", "W2BBB")
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        jwt = await _get_token(client, "op2", "Pass1234!")
        resp = await client.post(
            "/api/tokens/",
            data={"name": "expiring-token", "expires_at": "2099-12-31"},
            headers=_bearer(jwt),
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["expires_at"] is not None, "expires_at should be set"
    assert "2099" in body["expires_at"], "expires_at should contain 2099"


# ---------------------------------------------------------------------------
# Test 3: POST with invalid name returns 422
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_create_token_invalid_name(token_api_db):
    """POST /api/tokens with invalid name (spaces) returns 422."""
    await _create_user("op3", "Pass1234!", "W3CCC")
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        jwt = await _get_token(client, "op3", "Pass1234!")
        resp = await client.post(
            "/api/tokens/",
            data={"name": "has spaces"},
            headers=_bearer(jwt),
        )

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Test 4: GET on fresh user returns empty list
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_list_tokens_empty(token_api_db):
    """GET /api/tokens on a fresh user returns 200 and empty list."""
    await _create_user("op4", "Pass1234!", "W4DDD")
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        jwt = await _get_token(client, "op4", "Pass1234!")
        resp = await client.get("/api/tokens/", headers=_bearer(jwt))

    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Test 5: GET after create returns list with 1 entry, no full_token in items
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_list_tokens_after_create(token_api_db):
    """GET /api/tokens after creating one returns list with 1 entry, no full_token."""
    await _create_user("op5", "Pass1234!", "W5EEE")
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        jwt = await _get_token(client, "op5", "Pass1234!")
        await client.post(
            "/api/tokens/",
            data={"name": "op5-token"},
            headers=_bearer(jwt),
        )
        resp = await client.get("/api/tokens/", headers=_bearer(jwt))

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1, f"Expected 1 token, got {len(items)}"
    assert items[0]["name"] == "op5-token"
    assert "full_token" not in items[0], "list response must NOT contain full_token"


# ---------------------------------------------------------------------------
# Test 6: DELETE revokes token; token no longer appears in list
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_revoke_token(token_api_db):
    """DELETE /api/tokens/{id} returns 204; token absent from subsequent GET."""
    await _create_user("op6", "Pass1234!", "W6FFF")
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        jwt = await _get_token(client, "op6", "Pass1234!")
        create_resp = await client.post(
            "/api/tokens/",
            data={"name": "revoke-me"},
            headers=_bearer(jwt),
        )
        assert create_resp.status_code == 201
        token_id = create_resp.json()["id"]

        delete_resp = await client.delete(f"/api/tokens/{token_id}", headers=_bearer(jwt))
        assert delete_resp.status_code == 204

        list_resp = await client.get("/api/tokens/", headers=_bearer(jwt))
        assert list_resp.status_code == 200
        ids = [t["id"] for t in list_resp.json()]
        assert token_id not in ids, "Revoked token should not appear in active list"


# ---------------------------------------------------------------------------
# Test 7: DELETE another user's token returns 404
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_revoke_other_users_token_returns_404(token_api_db):
    """DELETE /api/tokens/{id} with a token owned by a different user returns 404."""
    await _create_user("user_a", "Pass1234!", "W7GGG")
    await _create_user("user_b", "Pass1234!", "W7HHH")
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        jwt_a = await _get_token(client, "user_a", "Pass1234!")
        jwt_b = await _get_token(client, "user_b", "Pass1234!")

        # user_a creates a token
        create_resp = await client.post(
            "/api/tokens/",
            data={"name": "user-a-token"},
            headers=_bearer(jwt_a),
        )
        assert create_resp.status_code == 201
        token_id = create_resp.json()["id"]

        # user_b attempts to delete user_a's token
        delete_resp = await client.delete(f"/api/tokens/{token_id}", headers=_bearer(jwt_b))
        assert delete_resp.status_code == 404


# ---------------------------------------------------------------------------
# Test 8: POST without auth returns 401 or 403
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_create_token_requires_auth(token_api_db):
    """POST /api/tokens without Authorization header returns 401 or 403."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/tokens/", data={"name": "no-auth"})

    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Test 9: GET without auth returns 401 or 403
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_list_tokens_requires_auth(token_api_db):
    """GET /api/tokens without Authorization header returns 401 or 403."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/tokens/")

    assert resp.status_code in (401, 403)
