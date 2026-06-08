"""Tests for Phase 55: Admin Clear Operator Log feature.

Covers ACLR-01 through ACLR-05 plus a zero-QSO path test.
Wave 0 (RED state) — implementation routes and templates do not yet exist.
Tests are expected to fail until Plan 02 ships the implementation.
"""
import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient
from pymongo.errors import ServerSelectionTimeoutError
from datetime import datetime, timezone

from app import database
from app.admin_main import app
from app.auth.models import User
from app.auth.service import create_access_token, hash_password
from app.config import settings
from app.qso.collections import ensure_user_qso_collection_indexes, get_user_qso_collection
from app.qso.models import QSO
from app.qso.service import qso_to_mongo_doc


@pytest_asyncio.fixture(scope="function")
async def admin_clear_log_db(monkeypatch):
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
        directConnection=True,
    )
    db_name = "ollog_admin_clearlog_test"
    try:
        await client.admin.command("ping")
    except ServerSelectionTimeoutError as exc:
        await client.aclose()
        pytest.skip(f"MongoDB not available for admin clear-log integration tests: {exc}")

    db = client[db_name]
    monkeypatch.setattr(database, "_client", client)
    monkeypatch.setattr(settings, "mongodb_db", db_name)
    await init_beanie(database=db, document_models=[User, QSO])
    try:
        yield db
    finally:
        await client.drop_database(db_name)
        await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def http_client(admin_clear_log_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def admin(admin_clear_log_db):
    user = User(
        username="adminuser",
        hashed_password=hash_password("adminpass"),
        callsign="W1ADM",
        role="admin",
        enabled=True,
    )
    await user.insert()
    await ensure_user_qso_collection_indexes(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def operator(admin_clear_log_db):
    user = User(
        username="testop",
        hashed_password=hash_password("oppass"),
        callsign="W1AW",
        role="operator",
        enabled=True,
    )
    await user.insert()
    await ensure_user_qso_collection_indexes(user)
    return user


def _admin_cookie(admin_user: User) -> dict:
    token = create_access_token(
        {"sub": admin_user.username, "callsign": admin_user.callsign, "role": admin_user.role}
    )
    return {"Cookie": f"admin_token={token}"}


async def _seed_qsos(operator: User, n: int) -> None:
    collection = get_user_qso_collection(operator)
    for i in range(n):
        qso = QSO(
            CALL=f"K{i}TEST",
            BAND="20m",
            MODE="FT8",
            QSO_DATE="20260507",
            TIME_ON="120000",
            qso_date_utc=datetime.now(timezone.utc),
            _operator=operator.callsign,
            _deleted=False,
        )
        await collection.insert_one(qso_to_mongo_doc(qso))


@pytest.mark.asyncio
async def test_clear_log_button_visible(http_client, admin, operator):
    """ACLR-01: 'Clear log' button is visible in the operator row on /admin/ui/users."""
    resp = await http_client.get("/admin/ui/users", headers=_admin_cookie(admin))
    assert resp.status_code == 200
    body = resp.text
    assert "Clear log" in body
    assert f"/admin/ui/users/{operator.username}/clear-log/modal" in body


@pytest.mark.asyncio
async def test_modal_shows_callsign_and_count(http_client, admin, operator):
    """ACLR-02: GET modal endpoint returns fragment with target callsign, QSO count, password field."""
    await _seed_qsos(operator, 3)
    resp = await http_client.get(
        f"/admin/ui/users/{operator.username}/clear-log/modal",
        headers=_admin_cookie(admin),
    )
    assert resp.status_code == 200
    body = resp.text
    assert operator.callsign in body
    assert "3" in body
    assert 'name="password"' in body


@pytest.mark.asyncio
async def test_clear_correct_password(http_client, admin, operator):
    """ACLR-03: Correct admin password permanently deletes all target operator QSOs."""
    collection = get_user_qso_collection(operator)
    await _seed_qsos(operator, 5)
    resp = await http_client.post(
        f"/admin/ui/users/{operator.username}/clear-log",
        headers=_admin_cookie(admin),
        data={"password": "adminpass"},
    )
    assert resp.status_code == 200
    post_count = await collection.count_documents({"_operator": operator.callsign, "_deleted": False})
    assert post_count == 0


@pytest.mark.asyncio
async def test_success_fragment_content(http_client, admin, operator):
    """ACLR-04: Success fragment shows operator callsign + deleted count, wraps in #admin-clear-log-modal."""
    await _seed_qsos(operator, 5)
    resp = await http_client.post(
        f"/admin/ui/users/{operator.username}/clear-log",
        headers=_admin_cookie(admin),
        data={"password": "adminpass"},
    )
    assert resp.status_code == 200
    body = resp.text
    assert operator.callsign in body
    assert "5" in body
    assert 'id="admin-clear-log-modal"' in body


@pytest.mark.asyncio
async def test_wrong_password_no_delete(http_client, admin, operator):
    """ACLR-05: Wrong admin password returns inline error, no deletion, modal stays open."""
    collection = get_user_qso_collection(operator)
    await _seed_qsos(operator, 5)
    resp = await http_client.post(
        f"/admin/ui/users/{operator.username}/clear-log",
        headers=_admin_cookie(admin),
        data={"password": "wrongpass"},
    )
    assert resp.status_code == 200
    body = resp.text
    assert "Incorrect password" in body
    assert 'id="admin-clear-log-modal"' in body
    post_count = await collection.count_documents({"_operator": operator.callsign, "_deleted": False})
    assert post_count == 5


@pytest.mark.asyncio
async def test_clear_zero_qsos(http_client, admin, operator):
    """ACLR-05 zero-QSO path: Operator with no QSOs clears without error."""
    resp = await http_client.post(
        f"/admin/ui/users/{operator.username}/clear-log",
        headers=_admin_cookie(admin),
        data={"password": "adminpass"},
    )
    assert resp.status_code == 200
    body = resp.text
    assert operator.callsign in body
    assert "0" in body
