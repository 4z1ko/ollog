"""Tests for QSO duplicate detection (03-02).

All fixtures are local — this file does NOT modify tests/conftest.py.
Integration tests require a live MongoDB at localhost:27017 and are skipped
if unavailable.

Duplicate detection rules:
- Same CALL, BAND, MODE within +/-2 minutes triggers 409
- Soft-deleted QSOs do not count
- Another operator's QSOs do not count
- force=true skips the check and returns 201
"""
import socket
from typing import AsyncGenerator

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
# Local fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def qso_db():
    """Function-scoped test database with User and QSO registered."""
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_dupdet_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_dupdet_test")
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Default QSO payload — all tests build on this
_BASE_QSO = {
    "CALL": "W1AW",
    "QSO_DATE": "20240115",
    "TIME_ON": "1430",
    "BAND": "20m",
    "MODE": "SSB",
}


async def create_qso(client: AsyncClient, token: str, **overrides) -> dict:
    """POST a QSO with default _BASE_QSO values, overriding fields as needed.

    Returns the parsed response JSON on success.
    """
    payload = {**_BASE_QSO, **overrides}
    resp = await client.post("/api/qsos/", json=payload, headers=_bearer(token))
    assert resp.status_code == 201, f"create_qso failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Tests: Duplicate DETECTED (expect 409)
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_duplicate_within_2min_window(qso_db):
    """QSO at 14:31 is a duplicate of one at 14:30 (1 min apart)."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        # Create original QSO at 14:30
        await create_qso(client, token, TIME_ON="1430")
        # Post duplicate at 14:31 — within 2 min window
        resp = await client.post(
            "/api/qsos/",
            json={**_BASE_QSO, "TIME_ON": "1431"},
            headers=_bearer(token),
        )
    assert resp.status_code == 409
    body = resp.json()
    assert body["detail"]["duplicate"] is True
    assert "existing_id" in body["detail"]


@mongo_required
@pytest.mark.asyncio
async def test_duplicate_exact_same_time(qso_db):
    """Identical QSO POSTed twice returns 409 on second attempt."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        await create_qso(client, token)
        resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(token))
    assert resp.status_code == 409
    body = resp.json()
    assert body["detail"]["duplicate"] is True
    assert body["detail"]["existing_call"] == "W1AW"
    assert body["detail"]["existing_band"] == "20M"
    assert body["detail"]["existing_mode"] == "SSB"
    assert body["detail"]["existing_date"] is not None


@mongo_required
@pytest.mark.asyncio
async def test_duplicate_at_boundary_2min(qso_db):
    """QSO at exactly +2 min is inside the inclusive window ($lte) — expect 409."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        await create_qso(client, token, TIME_ON="1430")
        # Exactly 2 min later — boundary inclusive
        resp = await client.post(
            "/api/qsos/",
            json={**_BASE_QSO, "TIME_ON": "1432"},
            headers=_bearer(token),
        )
    assert resp.status_code == 409
    assert resp.json()["detail"]["duplicate"] is True


# ---------------------------------------------------------------------------
# Tests: No duplicate (expect 201)
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_no_duplicate_outside_window(qso_db):
    """QSO at 14:33 is not a duplicate of one at 14:30 (3 min apart)."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        await create_qso(client, token, TIME_ON="1430")
        resp = await client.post(
            "/api/qsos/",
            json={**_BASE_QSO, "TIME_ON": "1433"},
            headers=_bearer(token),
        )
    assert resp.status_code == 201


@mongo_required
@pytest.mark.asyncio
async def test_no_duplicate_different_call(qso_db):
    """Different CALL at same time/band/mode — not a duplicate."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        await create_qso(client, token, CALL="W1AW")
        resp = await client.post(
            "/api/qsos/",
            json={**_BASE_QSO, "CALL": "K1ABC"},
            headers=_bearer(token),
        )
    assert resp.status_code == 201


@mongo_required
@pytest.mark.asyncio
async def test_no_duplicate_different_band(qso_db):
    """Different BAND at same CALL/MODE/time — not a duplicate."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        await create_qso(client, token, BAND="20m")
        resp = await client.post(
            "/api/qsos/",
            json={**_BASE_QSO, "BAND": "40m"},
            headers=_bearer(token),
        )
    assert resp.status_code == 201


@mongo_required
@pytest.mark.asyncio
async def test_no_duplicate_different_mode(qso_db):
    """Different MODE at same CALL/BAND/time — not a duplicate."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        await create_qso(client, token, MODE="SSB")
        resp = await client.post(
            "/api/qsos/",
            json={**_BASE_QSO, "MODE": "CW"},
            headers=_bearer(token),
        )
    assert resp.status_code == 201


@mongo_required
@pytest.mark.asyncio
async def test_no_duplicate_deleted_qso(qso_db):
    """Soft-deleted QSO does not trigger duplicate warning."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        # Create and immediately soft-delete the original QSO
        created = await create_qso(client, token)
        qso_id = created["id"]
        del_resp = await client.delete(f"/api/qsos/{qso_id}", headers=_bearer(token))
        assert del_resp.status_code == 204
        # Post identical QSO — deleted QSOs should not trigger 409
        resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(token))
    assert resp.status_code == 201


@mongo_required
@pytest.mark.asyncio
async def test_no_duplicate_other_operator(qso_db):
    """QSO logged by op1 does not trigger duplicate for op2 (operator isolation)."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    await _create_user("op2", "Pass1234!", "VK3XYZ")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tok1 = await _get_token(client, "op1", "Pass1234!")
        tok2 = await _get_token(client, "op2", "Pass1234!")
        # op1 creates a QSO
        await create_qso(client, tok1)
        # op2 posts identical QSO — should succeed (different operator)
        resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(tok2))
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Tests: Force override (expect 201 despite duplicate)
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_force_skips_duplicate_check(qso_db):
    """force=true bypasses duplicate check and saves the QSO."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        await create_qso(client, token)
        # Same QSO again with force=true — should bypass the 409
        resp = await client.post(
            "/api/qsos/?force=true",
            json=_BASE_QSO,
            headers=_bearer(token),
        )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["CALL"] == "W1AW"
