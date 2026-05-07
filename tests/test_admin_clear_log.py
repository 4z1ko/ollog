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
from datetime import datetime, timezone

from app.admin_main import app
from app.auth.models import User
from app.auth.service import create_access_token, hash_password
from app.qso.models import QSO


@pytest_asyncio.fixture(scope="function")
async def admin_clear_log_db():
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
        directConnection=True,
    )
    db = client["ollog_admin_clearlog_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_admin_clearlog_test")
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
    return user


def _admin_cookie(admin_user: User) -> dict:
    token = create_access_token(
        {"sub": admin_user.username, "callsign": admin_user.callsign, "role": admin_user.role}
    )
    return {"Cookie": f"admin_token={token}"}


async def _seed_qsos(operator_callsign: str, n: int) -> None:
    for i in range(n):
        qso = QSO(
            CALL=f"K{i}TEST",
            BAND="20m",
            MODE="FT8",
            QSO_DATE="20260507",
            TIME_ON="120000",
            qso_date_utc=datetime.now(timezone.utc),
            _operator=operator_callsign,
            _deleted=False,
        )
        await qso.insert()


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
    await _seed_qsos(operator.callsign, 3)
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
    await _seed_qsos(operator.callsign, 5)
    resp = await http_client.post(
        f"/admin/ui/users/{operator.username}/clear-log",
        headers=_admin_cookie(admin),
        data={"password": "adminpass"},
    )
    assert resp.status_code == 200
    post_count = await QSO.find({"_operator": operator.callsign, "_deleted": False}).count()
    assert post_count == 0


@pytest.mark.asyncio
async def test_success_fragment_content(http_client, admin, operator):
    """ACLR-04: Success fragment shows operator callsign + deleted count, wraps in #admin-clear-log-modal."""
    await _seed_qsos(operator.callsign, 5)
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
    await _seed_qsos(operator.callsign, 5)
    resp = await http_client.post(
        f"/admin/ui/users/{operator.username}/clear-log",
        headers=_admin_cookie(admin),
        data={"password": "wrongpass"},
    )
    assert resp.status_code == 200
    body = resp.text
    assert "Incorrect password" in body
    assert 'id="admin-clear-log-modal"' in body
    post_count = await QSO.find({"_operator": operator.callsign, "_deleted": False}).count()
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
