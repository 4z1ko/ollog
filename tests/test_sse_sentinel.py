"""SORT-03 integration tests: SSE auto-refresh sentinel rendering.

Tests:
  - Sentinel rendered for -_created_at sort (newest-entered first)
  - Sentinel rendered for default -qso_date_utc sort (regression check)
  - Sentinel NOT rendered for non-newest-first sorts (e.g. CALL)
  - Sentinel NOT rendered when filters are active with -_created_at sort

Requires MongoDB reachable at localhost:27017.
"""
import socket

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient

from app.auth.models import User
from app.auth.service import create_access_token, hash_password
from app.main import app
from app.qso.models import QSO


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mongo_available() -> bool:
    """Return True if MongoDB is reachable at localhost:27017."""
    try:
        s = socket.create_connection(("localhost", 27017), timeout=1)
        s.close()
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def sentinel_db():
    """Function-scoped test database for SSE sentinel tests."""
    if not _mongo_available():
        pytest.skip("MongoDB not available at localhost:27017")
    client = AsyncMongoClient(
        "mongodb://localhost:27017", serverSelectionTimeoutMS=2000, directConnection=True
    )
    db = client["ollog_sse_sentinel_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_sse_sentinel_test")
    await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def operator(sentinel_db):
    """Create and return a test operator user."""
    user = User(
        username="testop",
        hashed_password=hash_password("testpass"),
        callsign="W1AW",
    )
    await user.insert()
    return user


@pytest_asyncio.fixture(scope="function")
async def client():
    """Return an async HTTP client pointed at the ASGI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sentinel_rendered_for_created_at_sort(client, operator, sentinel_db):
    """SORT-03: SSE sentinel is rendered when sort=-_created_at on page 1 with no filters."""
    token = create_access_token(
        {"sub": operator.username, "callsign": operator.callsign, "role": operator.role}
    )
    resp = await client.get(
        "/log/view?sort=-_created_at",
        headers={"Cookie": f"access_token={token}"},
    )
    assert resp.status_code == 200
    assert 'id="auto-refresh-ok"' in resp.text, (
        "SSE sentinel must be rendered for sort=-_created_at on page 1 with no filters"
    )


@pytest.mark.asyncio
async def test_sentinel_rendered_for_default_sort(client, operator, sentinel_db):
    """SORT-03: SSE sentinel is rendered for default -qso_date_utc sort (regression check)."""
    token = create_access_token(
        {"sub": operator.username, "callsign": operator.callsign, "role": operator.role}
    )
    resp = await client.get(
        "/log/view",
        headers={"Cookie": f"access_token={token}"},
    )
    assert resp.status_code == 200
    assert 'id="auto-refresh-ok"' in resp.text, (
        "SSE sentinel must still be rendered for the default -qso_date_utc sort"
    )


@pytest.mark.asyncio
async def test_sentinel_not_rendered_for_call_sort(client, operator, sentinel_db):
    """SORT-03: SSE sentinel is NOT rendered for non-newest-first sort (CALL)."""
    token = create_access_token(
        {"sub": operator.username, "callsign": operator.callsign, "role": operator.role}
    )
    resp = await client.get(
        "/log/view?sort=CALL",
        headers={"Cookie": f"access_token={token}"},
    )
    assert resp.status_code == 200
    assert 'id="auto-refresh-ok"' not in resp.text, (
        "SSE sentinel must NOT be rendered for sort=CALL (non-newest-first)"
    )


@pytest.mark.asyncio
async def test_sentinel_not_rendered_with_filter_active(client, operator, sentinel_db):
    """SORT-03: SSE sentinel is NOT rendered when a call filter is active."""
    token = create_access_token(
        {"sub": operator.username, "callsign": operator.callsign, "role": operator.role}
    )
    resp = await client.get(
        "/log/view?sort=-_created_at&call=W1AW",
        headers={"Cookie": f"access_token={token}"},
    )
    assert resp.status_code == 200
    assert 'id="auto-refresh-ok"' not in resp.text, (
        "SSE sentinel must NOT be rendered when filters are active, even with newest-first sort"
    )
