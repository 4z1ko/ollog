"""Integration tests for NOTIFY_SOUND injection in log_view()."""

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
async def log_view_db():
    client = AsyncMongoClient(
        "mongodb://localhost:27017", serverSelectionTimeoutMS=2000, directConnection=True
    )
    db = client["ollog_log_view_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_log_view_test")
    await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def operator(log_view_db):
    user = User(
        username="testop",
        hashed_password=hash_password("testpass"),
        callsign="W1AW",
    )
    await user.insert()
    return user


@pytest_asyncio.fixture(scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_notify_sound_false_injected(client, operator, log_view_db):
    """SND-01: log_view() injects NOTIFY_SOUND='false' when user.notify_sound is False."""
    token = create_access_token(
        {"sub": operator.username, "callsign": operator.callsign, "role": operator.role}
    )
    resp = await client.get(
        "/log/view",
        headers={"Cookie": f"access_token={token}"},
    )
    assert resp.status_code == 200
    assert 'const NOTIFY_SOUND = "false"' in resp.text


@pytest.mark.asyncio
async def test_notify_sound_true_injected(client, operator, log_view_db):
    """SND-01: log_view() injects NOTIFY_SOUND='true' when user.notify_sound is True."""
    operator.notify_sound = True
    await operator.save()

    token = create_access_token(
        {"sub": operator.username, "callsign": operator.callsign, "role": operator.role}
    )
    resp = await client.get(
        "/log/view",
        headers={"Cookie": f"access_token={token}"},
    )
    assert resp.status_code == 200
    assert 'const NOTIFY_SOUND = "true"' in resp.text
