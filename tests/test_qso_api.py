"""Tests for the QSO REST API endpoints.

All fixtures are local — this file does NOT modify tests/conftest.py.
Integration tests require a live MongoDB at localhost:27017 and are skipped
if unavailable.
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
    db = client["ollog_qso_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_qso_test")
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


# Minimal valid QSO payload
_BASE_QSO = {
    "CALL": "W1AW",
    "QSO_DATE": "20240115",
    "TIME_ON": "1430",
    "BAND": "20m",
    "MODE": "SSB",
}


# ---------------------------------------------------------------------------
# POST /api/qsos/ — Create QSO
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_create_qso_success(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(token))
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["CALL"] == "W1AW"
    assert body["BAND"] == "20M"   # uppercased
    assert body["MODE"] == "SSB"   # already uppercase
    assert "qso_date_utc" in body
    # qso_date_utc should be a valid ISO datetime string
    from datetime import datetime
    dt = datetime.fromisoformat(body["qso_date_utc"])
    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 15


@mongo_required
@pytest.mark.asyncio
async def test_create_qso_extra_adif_fields(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        payload = {**_BASE_QSO, "COMMENT": "test comment"}
        resp = await client.post("/api/qsos/", json=payload, headers=_bearer(token))
    assert resp.status_code == 201
    assert resp.json().get("COMMENT") == "test comment"


@mongo_required
@pytest.mark.asyncio
async def test_create_qso_missing_required_field(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        payload = {k: v for k, v in _BASE_QSO.items() if k != "CALL"}
        resp = await client.post("/api/qsos/", json=payload, headers=_bearer(token))
    assert resp.status_code == 422


@mongo_required
@pytest.mark.asyncio
async def test_create_qso_unauthorized(qso_db):
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/qsos/", json=_BASE_QSO)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/qsos/ — List QSOs
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_get_qsos_empty(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.get("/api/qsos/", headers=_bearer(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


@mongo_required
@pytest.mark.asyncio
async def test_get_qsos_returns_own_only(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    await _create_user("op2", "Pass1234!", "VK3XYZ")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tok1 = await _get_token(client, "op1", "Pass1234!")
        tok2 = await _get_token(client, "op2", "Pass1234!")
        # op1 creates a QSO
        await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(tok1))
        # op2 creates a different QSO
        await client.post("/api/qsos/", json={**_BASE_QSO, "CALL": "K1XYZ"}, headers=_bearer(tok2))
        # op1 lists — should see only own QSO
        resp = await client.get("/api/qsos/", headers=_bearer(tok1))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["CALL"] == "W1AW"


@mongo_required
@pytest.mark.asyncio
async def test_get_qsos_excludes_deleted(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        # Create then delete
        create_resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(token))
        qso_id = create_resp.json()["id"]
        await client.delete(f"/api/qsos/{qso_id}", headers=_bearer(token))
        # List should be empty
        resp = await client.get("/api/qsos/", headers=_bearer(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@mongo_required
@pytest.mark.asyncio
async def test_get_qsos_pagination(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        # Create 3 QSOs with different callsigns and times to avoid unique index collision
        for i, (call, time_on) in enumerate([("W1AW", "1430"), ("K1ABC", "1500"), ("VK2TEST", "1530")]):
            await client.post(
                "/api/qsos/",
                json={**_BASE_QSO, "CALL": call, "TIME_ON": time_on},
                headers=_bearer(token),
            )
        # Page 1 with page_size=2
        resp1 = await client.get("/api/qsos/?page=1&page_size=2", headers=_bearer(token))
        assert resp1.status_code == 200
        body1 = resp1.json()
        assert body1["total"] == 3
        assert len(body1["items"]) == 2
        # Page 2
        resp2 = await client.get("/api/qsos/?page=2&page_size=2", headers=_bearer(token))
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert len(body2["items"]) == 1


@mongo_required
@pytest.mark.asyncio
async def test_get_qsos_filter_by_call(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        await client.post("/api/qsos/", json={**_BASE_QSO, "CALL": "W1AW", "TIME_ON": "1430"}, headers=_bearer(token))
        await client.post("/api/qsos/", json={**_BASE_QSO, "CALL": "K1ABC", "TIME_ON": "1500"}, headers=_bearer(token))
        resp = await client.get("/api/qsos/?call=W1AW", headers=_bearer(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["CALL"] == "W1AW"


@mongo_required
@pytest.mark.asyncio
async def test_get_qsos_filter_by_band(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        await client.post("/api/qsos/", json={**_BASE_QSO, "BAND": "20m", "TIME_ON": "1430"}, headers=_bearer(token))
        await client.post("/api/qsos/", json={**_BASE_QSO, "CALL": "K1ABC", "BAND": "40m", "TIME_ON": "1500"}, headers=_bearer(token))
        resp = await client.get("/api/qsos/?band=20M", headers=_bearer(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["BAND"] == "20M"


@mongo_required
@pytest.mark.asyncio
async def test_get_qsos_filter_by_mode(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        await client.post("/api/qsos/", json={**_BASE_QSO, "MODE": "SSB", "TIME_ON": "1430"}, headers=_bearer(token))
        await client.post("/api/qsos/", json={**_BASE_QSO, "CALL": "K1ABC", "MODE": "CW", "TIME_ON": "1500"}, headers=_bearer(token))
        resp = await client.get("/api/qsos/?mode=CW", headers=_bearer(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["MODE"] == "CW"


# ---------------------------------------------------------------------------
# GET /api/qsos/{qso_id} — Get by ID
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_get_qso_by_id(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        create_resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(token))
        qso_id = create_resp.json()["id"]
        resp = await client.get(f"/api/qsos/{qso_id}", headers=_bearer(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == qso_id
    assert body["CALL"] == "W1AW"
    assert body["BAND"] == "20M"


@mongo_required
@pytest.mark.asyncio
async def test_get_qso_not_found(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    fake_id = "000000000000000000000000"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.get(f"/api/qsos/{fake_id}", headers=_bearer(token))
    assert resp.status_code == 404


@mongo_required
@pytest.mark.asyncio
async def test_get_qso_other_operator(qso_db):
    """QSO owned by op1 returns 404 when fetched as op2 (operator isolation)."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    await _create_user("op2", "Pass1234!", "VK3XYZ")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tok1 = await _get_token(client, "op1", "Pass1234!")
        tok2 = await _get_token(client, "op2", "Pass1234!")
        create_resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(tok1))
        qso_id = create_resp.json()["id"]
        resp = await client.get(f"/api/qsos/{qso_id}", headers=_bearer(tok2))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/qsos/{qso_id} — Partial update
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_patch_qso_update_call(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        create_resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(token))
        qso_id = create_resp.json()["id"]
        resp = await client.patch(f"/api/qsos/{qso_id}", json={"CALL": "K1ABC"}, headers=_bearer(token))
    assert resp.status_code == 200
    assert resp.json()["CALL"] == "K1ABC"


@mongo_required
@pytest.mark.asyncio
async def test_patch_qso_update_extra_field(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        create_resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(token))
        qso_id = create_resp.json()["id"]
        resp = await client.patch(f"/api/qsos/{qso_id}", json={"COMMENT": "updated"}, headers=_bearer(token))
    assert resp.status_code == 200
    assert resp.json().get("COMMENT") == "updated"


@mongo_required
@pytest.mark.asyncio
async def test_patch_qso_strips_protected_fields(qso_db):
    """Patching _operator does not change the actual operator callsign."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        create_resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(token))
        qso_id = create_resp.json()["id"]
        resp = await client.patch(
            f"/api/qsos/{qso_id}",
            json={"_operator": "HACKER", "CALL": "W9OK"},
            headers=_bearer(token),
        )
    assert resp.status_code == 200
    body = resp.json()
    # _operator should remain VK2ABC (the JWT callsign)
    assert body.get("_operator") == "VK2ABC"
    assert body["CALL"] == "W9OK"


@mongo_required
@pytest.mark.asyncio
async def test_patch_qso_other_operator(qso_db):
    """PATCH on op1's QSO as op2 returns 404."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    await _create_user("op2", "Pass1234!", "VK3XYZ")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tok1 = await _get_token(client, "op1", "Pass1234!")
        tok2 = await _get_token(client, "op2", "Pass1234!")
        create_resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(tok1))
        qso_id = create_resp.json()["id"]
        resp = await client.patch(f"/api/qsos/{qso_id}", json={"CALL": "K1XYZ"}, headers=_bearer(tok2))
    assert resp.status_code == 404


@mongo_required
@pytest.mark.asyncio
async def test_patch_qso_recalculates_datetime(qso_db):
    """PATCH with TIME_ON update recalculates qso_date_utc."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        create_resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(token))
        qso_id = create_resp.json()["id"]
        original_dt = create_resp.json()["qso_date_utc"]
        resp = await client.patch(
            f"/api/qsos/{qso_id}",
            json={"TIME_ON": "1530", "QSO_DATE": "20240115"},
            headers=_bearer(token),
        )
    assert resp.status_code == 200
    new_dt = resp.json()["qso_date_utc"]
    assert new_dt != original_dt
    from datetime import datetime
    parsed = datetime.fromisoformat(new_dt)
    assert parsed.hour == 15
    assert parsed.minute == 30


# ---------------------------------------------------------------------------
# DELETE /api/qsos/{qso_id} — Soft delete
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_delete_qso(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        create_resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(token))
        qso_id = create_resp.json()["id"]
        del_resp = await client.delete(f"/api/qsos/{qso_id}", headers=_bearer(token))
        assert del_resp.status_code == 204
        # GET by ID should now return 404
        get_resp = await client.get(f"/api/qsos/{qso_id}", headers=_bearer(token))
    assert get_resp.status_code == 404


@mongo_required
@pytest.mark.asyncio
async def test_delete_qso_other_operator(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    await _create_user("op2", "Pass1234!", "VK3XYZ")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tok1 = await _get_token(client, "op1", "Pass1234!")
        tok2 = await _get_token(client, "op2", "Pass1234!")
        create_resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(tok1))
        qso_id = create_resp.json()["id"]
        resp = await client.delete(f"/api/qsos/{qso_id}", headers=_bearer(tok2))
    assert resp.status_code == 404


@mongo_required
@pytest.mark.asyncio
async def test_delete_qso_not_found(qso_db):
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    fake_id = "000000000000000000000000"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.delete(f"/api/qsos/{fake_id}", headers=_bearer(token))
    assert resp.status_code == 404


@mongo_required
@pytest.mark.asyncio
async def test_delete_qso_already_deleted(qso_db):
    """Second DELETE on same QSO returns 404."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        create_resp = await client.post("/api/qsos/", json=_BASE_QSO, headers=_bearer(token))
        qso_id = create_resp.json()["id"]
        await client.delete(f"/api/qsos/{qso_id}", headers=_bearer(token))
        resp = await client.delete(f"/api/qsos/{qso_id}", headers=_bearer(token))
    assert resp.status_code == 404
