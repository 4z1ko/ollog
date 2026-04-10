"""Integration tests for X-API-Key authentication on QSO REST endpoints.

All fixtures are local — this file does NOT modify tests/conftest.py.
Integration tests require a live MongoDB at localhost:27017 and are skipped
if unavailable.

Tests cover:
- Valid API key auth on all 5 QSO CRUD endpoints
- Operator isolation via API key (two operators cannot see each other's QSOs)
- HTTP 401 for invalid, expired, disabled, and missing credentials
- JWT regression (JWT path still works after dep swap)
- Admin endpoint still rejects API keys (no accidental dep swap)
"""
import socket
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient

from app.auth.models import User
from app.auth.service import hash_password
from app.qso.models import QSO
from app.tokens.models import ApiToken
from app.tokens.service import generate_api_token, hash_api_token


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
async def qso_apikey_db():
    """Function-scoped test database with User, QSO, and ApiToken registered."""
    client = AsyncMongoClient(
        "mongodb://localhost:27017/?directConnection=true",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_apikey_test"]
    await init_beanie(database=db, document_models=[User, QSO, ApiToken])
    yield db
    await client.drop_database("ollog_apikey_test")
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


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_api_key(
    user: User,
    *,
    name: str = "test-key",
    enabled: bool = True,
    expires_at: datetime | None = None,
) -> str:
    """Create and persist an ApiToken for user. Returns the full raw token string."""
    full_token, prefix = generate_api_token()
    hashed_token = hash_api_token(full_token)
    token_doc = ApiToken(
        user_id=user.id,
        name=name,
        token_prefix=prefix,
        hashed_token=hashed_token,
        enabled=enabled,
        expires_at=expires_at,
    )
    await token_doc.insert()
    return full_token


# Minimal valid QSO payload
_BASE_QSO = {
    "CALL": "W1AW",
    "QSO_DATE": "20240115",
    "TIME_ON": "1430",
    "BAND": "20m",
    "MODE": "SSB",
}


# ---------------------------------------------------------------------------
# Test 1: GET /api/qsos/ with valid API key
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_list_qsos_with_api_key(qso_apikey_db):
    """GET /api/qsos/ succeeds with X-API-Key header (no Authorization)."""
    user = await _create_user("op1", "Pass1234!", "VK2ABC")
    api_key = await _create_api_key(user)

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Insert a QSO via JWT first so we have something to list
        jwt_token = await _get_token(client, "op1", "Pass1234!")
        await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(jwt_token))
        # List using API key only (no Authorization header)
        resp = await client.get("/api/qsos/", headers={"X-API-Key": api_key})

    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert body["total"] == 1


# ---------------------------------------------------------------------------
# Test 2: POST /api/qsos/ with valid API key
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_create_qso_with_api_key(qso_apikey_db):
    """POST /api/qsos/ creates a QSO using X-API-Key header (no JWT)."""
    user = await _create_user("op1", "Pass1234!", "VK2ABC")
    api_key = await _create_api_key(user)

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/qsos/",
            json=_BASE_QSO,
            headers={"X-API-Key": api_key},
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["CALL"] == "W1AW"


# ---------------------------------------------------------------------------
# Test 3: GET /api/qsos/{id} with valid API key
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_get_qso_with_api_key(qso_apikey_db):
    """GET /api/qsos/{id} returns QSO data using X-API-Key header."""
    user = await _create_user("op1", "Pass1234!", "VK2ABC")
    api_key = await _create_api_key(user)

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create via API key
        create_resp = await client.post(
            "/api/qsos/",
            json=_BASE_QSO,
            headers={"X-API-Key": api_key},
        )
        qso_id = create_resp.json()["id"]
        # Get by ID via API key
        resp = await client.get(f"/api/qsos/{qso_id}", headers={"X-API-Key": api_key})

    assert resp.status_code == 200
    assert resp.json()["id"] == qso_id


# ---------------------------------------------------------------------------
# Test 4: PATCH /api/qsos/{id} with valid API key
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_patch_qso_with_api_key(qso_apikey_db):
    """PATCH /api/qsos/{id} updates QSO using X-API-Key header."""
    user = await _create_user("op1", "Pass1234!", "VK2ABC")
    api_key = await _create_api_key(user)

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/qsos/",
            json=_BASE_QSO,
            headers={"X-API-Key": api_key},
        )
        qso_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/qsos/{qso_id}",
            json={"BAND": "40m"},
            headers={"X-API-Key": api_key},
        )

    assert resp.status_code == 200
    assert resp.json()["BAND"] == "40M"


# ---------------------------------------------------------------------------
# Test 5: DELETE /api/qsos/{id} with valid API key
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_delete_qso_with_api_key(qso_apikey_db):
    """DELETE /api/qsos/{id} soft-deletes QSO using X-API-Key header."""
    user = await _create_user("op1", "Pass1234!", "VK2ABC")
    api_key = await _create_api_key(user)

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/qsos/",
            json=_BASE_QSO,
            headers={"X-API-Key": api_key},
        )
        qso_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/qsos/{qso_id}", headers={"X-API-Key": api_key})

    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Test 6: Operator isolation via API key
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_api_key_operator_isolation(qso_apikey_db):
    """Each operator's API key returns only that operator's QSOs.

    Create two operators (AA1AA, BB2BB) each with their own API key and QSO.
    Verify GET /api/qsos/ with AA1AA's key returns only AA1AA's QSO and vice versa.
    """
    user_aa = await _create_user("aa1aa", "Pass1234!", "AA1AA")
    user_bb = await _create_user("bb2bb", "Pass1234!", "BB2BB")
    key_aa = await _create_api_key(user_aa, name="aa-key")
    key_bb = await _create_api_key(user_bb, name="bb-key")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # AA1AA logs a QSO
        await client.post(
            "/api/qsos/",
            json={**_BASE_QSO, "CALL": "W1AW"},
            headers={"X-API-Key": key_aa},
        )
        # BB2BB logs a different QSO
        await client.post(
            "/api/qsos/",
            json={**_BASE_QSO, "CALL": "K1TTT"},
            headers={"X-API-Key": key_bb},
        )

        # AA1AA's list should contain only W1AW
        resp_aa = await client.get("/api/qsos/", headers={"X-API-Key": key_aa})
        # BB2BB's list should contain only K1TTT
        resp_bb = await client.get("/api/qsos/", headers={"X-API-Key": key_bb})

    assert resp_aa.status_code == 200
    aa_items = resp_aa.json()["items"]
    assert len(aa_items) == 1, f"AA1AA expected 1 QSO, got {len(aa_items)}"
    assert aa_items[0]["CALL"] == "W1AW"

    assert resp_bb.status_code == 200
    bb_items = resp_bb.json()["items"]
    assert len(bb_items) == 1, f"BB2BB expected 1 QSO, got {len(bb_items)}"
    assert bb_items[0]["CALL"] == "K1TTT"


# ---------------------------------------------------------------------------
# Test 7: Invalid API key returns 401
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_invalid_api_key_returns_401(qso_apikey_db):
    """GET /api/qsos/ with invalid API key returns exactly 401 (NOT 403)."""
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/qsos/",
            headers={"X-API-Key": "ollog_invalid000000000000000000000000000000000000000"},
        )

    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Test 8: Missing credentials return 401
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_missing_credentials_returns_401(qso_apikey_db):
    """GET /api/qsos/ with no credentials at all returns exactly 401."""
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/qsos/")

    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Test 9: Expired API key returns 401
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_expired_api_key_returns_401(qso_apikey_db):
    """GET /api/qsos/ with an expired API key returns 401."""
    user = await _create_user("op1", "Pass1234!", "VK2ABC")
    api_key = await _create_api_key(
        user,
        name="expired-key",
        expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
    )

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/qsos/", headers={"X-API-Key": api_key})

    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Test 10: Disabled API key returns 401
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_disabled_api_key_returns_401(qso_apikey_db):
    """GET /api/qsos/ with a disabled API key returns 401."""
    user = await _create_user("op1", "Pass1234!", "VK2ABC")
    api_key = await _create_api_key(user, name="disabled-key", enabled=False)

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/qsos/", headers={"X-API-Key": api_key})

    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Test 11: JWT still works on QSO endpoints (regression)
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_jwt_still_works_on_qso_endpoints(qso_apikey_db):
    """JWT Bearer auth still works on /api/qsos/ after dep swap (regression test)."""
    await _create_user("op1", "Pass1234!", "VK2ABC")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        jwt_token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.get("/api/qsos/", headers=_bearer(jwt_token))

    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body


# ---------------------------------------------------------------------------
# Test 12: Admin endpoint rejects API key
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_admin_endpoint_rejects_api_key(qso_apikey_db):
    """GET /admin/users/ with only X-API-Key header returns 401 or 403.

    Admin routes use get_current_user (JWT-only via oauth2_scheme with
    auto_error=True). API keys must not bypass admin auth.
    """
    user = await _create_user("adminop", "Pass1234!", "VK9ADM", role="admin")
    api_key = await _create_api_key(user, name="admin-key")

    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/admin/users/",
            headers={"X-API-Key": api_key},
        )

    assert resp.status_code in (401, 403), (
        f"Admin endpoint should reject API key with 401 or 403, got {resp.status_code}: {resp.text}"
    )
