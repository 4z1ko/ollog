"""Tests for the HTMX operator profile settings form."""

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient
from pymongo.errors import ServerSelectionTimeoutError
from starlette.requests import Request

from app import database
from app.auth.models import User
from app.auth.service import create_access_token, hash_password
from app.config import settings
from app.main import app
from app.qso.ui_router import profile_update
from app.qso.models import QSO


@pytest_asyncio.fixture(scope="function")
async def profile_ui_db(monkeypatch):
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
        directConnection=True,
    )
    db_name = "ollog_profile_ui_test"
    try:
        await client.admin.command("ping")
    except ServerSelectionTimeoutError as exc:
        await client.aclose()
        pytest.skip(f"MongoDB not available for profile UI tests: {exc}")

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
async def operator(profile_ui_db):
    user = User(
        username="profileop",
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


@pytest.mark.asyncio
async def test_profile_update_invalid_tx_pwr_does_not_raise_without_mongo():
    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/log/profile",
        "headers": [],
    })
    user = User.model_construct(
        username="profileop",
        hashed_password=hash_password("testpass"),
        callsign="W1AW",
    )

    resp = await profile_update(request, user=user, tx_pwr="100W")

    assert resp.status_code == 200
    assert "TX power must be a number" in resp.body.decode()


@pytest.mark.asyncio
async def test_profile_update_saves_operator_profile(http_client, operator, profile_ui_db):
    resp = await http_client.post(
        "/log/profile",
        headers=_auth_cookie(operator),
        data={
            "station_callsign": "K1ABC",
            "name": "Test Operator",
            "my_gridsquare": "FN31pr",
            "tx_pwr": "100",
            "notify_sound": "true",
        },
    )

    assert resp.status_code == 200
    assert "Profile updated successfully" in resp.text

    refreshed = await User.get(operator.id)
    assert refreshed is not None
    assert refreshed.station_callsign == "K1ABC"
    assert refreshed.name == "Test Operator"
    assert refreshed.my_gridsquare == "FN31PR"
    assert refreshed.tx_pwr == 100
    assert refreshed.notify_sound is True


@pytest.mark.asyncio
async def test_profile_update_invalid_tx_pwr_returns_htmx_error(
    http_client,
    operator,
    profile_ui_db,
):
    resp = await http_client.post(
        "/log/profile",
        headers=_auth_cookie(operator),
        data={"tx_pwr": "100W"},
    )

    assert resp.status_code == 200
    assert "TX power must be a number" in resp.text
