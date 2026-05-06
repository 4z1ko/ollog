"""Tests for Phase 54: Operator Clear Log feature.

Covers CLR-01 through CLR-05 plus a unit test for the service function.
Mirrors the cookie-auth UI route test pattern from test_log_view_notify_sound.py.
"""
import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient

from app.auth.models import User
from app.auth.service import create_access_token, hash_password
from app.main import app
from app.qso.models import QSO


@pytest_asyncio.fixture(scope="function")
async def clear_log_db():
    client = AsyncMongoClient(
        "mongodb://localhost:27017", serverSelectionTimeoutMS=2000, directConnection=True
    )
    db = client["ollog_clearlog_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_clearlog_test")
    await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def operator(clear_log_db):
    user = User(
        username="testop",
        hashed_password=hash_password("testpass"),
        callsign="W1AW",
    )
    await user.insert()
    return user


@pytest_asyncio.fixture(scope="function")
async def http_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _auth_cookie(user: User) -> dict:
    token = create_access_token(
        {"sub": user.username, "callsign": user.callsign, "role": user.role}
    )
    return {"Cookie": f"access_token={token}"}


async def _seed_qsos(operator_callsign: str, n: int) -> None:
    """Insert n QSOs for the given operator."""
    from datetime import datetime, timezone
    for i in range(n):
        qso = QSO(
            CALL=f"K{i}TEST",
            BAND="20m",
            MODE="FT8",
            QSO_DATE="20260506",
            TIME_ON="120000",
            qso_date_utc=datetime.now(timezone.utc),
            _operator=operator_callsign,
            _deleted=False,
        )
        await qso.insert()


@pytest.mark.asyncio
async def test_danger_zone_visible(http_client, operator, clear_log_db):
    """CLR-01: Danger Zone card with 'Clear my log' button is visible on /log/profile."""
    resp = await http_client.get("/log/profile", headers=_auth_cookie(operator))
    assert resp.status_code == 200
    body = resp.text
    assert "Danger Zone" in body
    assert "Clear my log" in body
    assert 'id="clear-log-modal"' in body


@pytest.mark.asyncio
async def test_modal_shows_count(http_client, operator, clear_log_db):
    """CLR-02: GET /log/profile/clear/modal returns fragment with QSO count."""
    await _seed_qsos(operator.callsign, 3)
    resp = await http_client.get(
        "/log/profile/clear/modal", headers=_auth_cookie(operator)
    )
    assert resp.status_code == 200
    body = resp.text
    assert "3" in body  # count appears
    assert 'name="password"' in body
    assert 'role="dialog"' in body
    assert 'aria-modal="true"' in body


@pytest.mark.asyncio
async def test_clear_correct_password(http_client, operator, clear_log_db):
    """CLR-03: Correct password permanently deletes all operator QSOs."""
    await _seed_qsos(operator.callsign, 5)
    pre_count = await QSO.find({"_operator": operator.callsign, "_deleted": False}).count()
    assert pre_count == 5

    resp = await http_client.post(
        "/log/profile/clear",
        headers=_auth_cookie(operator),
        data={"password": "testpass"},
    )
    assert resp.status_code == 200

    post_count = await QSO.find({"_operator": operator.callsign, "_deleted": False}).count()
    assert post_count == 0


@pytest.mark.asyncio
async def test_success_fragment_count(http_client, operator, clear_log_db):
    """CLR-04: Success fragment shows actual deleted count."""
    await _seed_qsos(operator.callsign, 4)
    resp = await http_client.post(
        "/log/profile/clear",
        headers=_auth_cookie(operator),
        data={"password": "testpass"},
    )
    assert resp.status_code == 200
    body = resp.text
    assert "4" in body
    assert "deleted" in body.lower()
    assert 'id="clear-log-modal"' in body  # outerHTML target wrapper


@pytest.mark.asyncio
async def test_wrong_password_no_delete(http_client, operator, clear_log_db):
    """CLR-05: Wrong password returns error fragment; no QSOs deleted."""
    await _seed_qsos(operator.callsign, 2)
    resp = await http_client.post(
        "/log/profile/clear",
        headers=_auth_cookie(operator),
        data={"password": "WRONG"},
    )
    assert resp.status_code == 200  # HTMX requires 200
    body = resp.text
    assert "Incorrect password" in body
    assert 'id="clear-log-modal"' in body  # modal still rendered
    # And no deletion happened:
    post_count = await QSO.find({"_operator": operator.callsign, "_deleted": False}).count()
    assert post_count == 2


@pytest.mark.asyncio
async def test_clear_operator_log_service(clear_log_db, operator):
    """Unit test: clear_operator_log() returns deleted_count and removes records."""
    from app.qso.service import clear_operator_log
    await _seed_qsos(operator.callsign, 7)
    # Also insert a QSO for a different operator — must NOT be deleted
    other = QSO(
        CALL="OTHER",
        BAND="20m",
        MODE="FT8",
        QSO_DATE="20260506",
        TIME_ON="120000",
        _operator="K0RY",
        _deleted=False,
    )
    await other.insert()

    deleted = await clear_operator_log(operator.callsign)
    assert deleted == 7

    remaining_self = await QSO.find({"_operator": operator.callsign, "_deleted": False}).count()
    assert remaining_self == 0
    remaining_other = await QSO.find({"_operator": "K0RY", "_deleted": False}).count()
    assert remaining_other == 1  # cross-operator isolation
