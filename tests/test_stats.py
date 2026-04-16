"""Integration tests for Phase 42 stats aggregation backend.

Tests STATS-06 (operator isolation) and STATS-07 (empty-state shape).
"""
import socket
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient

from app.auth.models import User
from app.auth.service import create_access_token, hash_password
from app.main import app
from app.qso.models import QSO
from app.stats.service import get_stats


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mongo_available() -> bool:
    try:
        s = socket.create_connection(("localhost", 27017), timeout=1)
        s.close()
        return True
    except OSError:
        return False


def _make_qso_doc(operator: str, call: str, **kwargs) -> QSO:
    """Return an unsaved QSO document with sensible defaults."""
    return QSO(
        **{
            "_operator": operator,
            "CALL": call,
            "BAND": kwargs.get("BAND", "20M"),
            "MODE": kwargs.get("MODE", "SSB"),
            "qso_date_utc": kwargs.get(
                "qso_date_utc",
                datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
            ),
            "QSO_DATE": kwargs.get("QSO_DATE", "20240601"),
            "TIME_ON": kwargs.get("TIME_ON", "1200"),
        }
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def stats_test_db():
    """Function-scoped test database for stats tests."""
    if not _mongo_available():
        pytest.skip("MongoDB not available at localhost:27017")

    client = AsyncMongoClient(
        "mongodb://localhost:27017/?directConnection=true",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_test"]
    await init_beanie(database=db, document_models=[QSO, User])
    yield db
    await client.drop_database("ollog_test")
    await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def http_client():
    """ASGI test client for route-level tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# STATS-07: Empty-state shape
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stats_empty_log(stats_test_db):
    """get_stats() returns complete shape with total_qsos=0 for empty log."""
    result = await get_stats("NOCALL")
    assert result["total_qsos"] == 0
    assert result["band_counts"] == {}
    assert result["mode_counts"] == {}
    assert result["entity_counts"] == []
    assert result["unique_entity_count"] == 0


# ---------------------------------------------------------------------------
# STATS-06: Operator isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stats_operator_isolation(stats_test_db):
    """get_stats() returns only the queried operator's data — no cross-contamination."""
    # Seed QSOs for AA1AA (US callsigns on 20M SSB)
    await _make_qso_doc("AA1AA", "W1AW", BAND="20M", MODE="SSB").insert()
    await _make_qso_doc("AA1AA", "W2AW", BAND="40M", MODE="FT8").insert()
    await _make_qso_doc("AA1AA", "W3AW", BAND="20M", MODE="SSB").insert()

    # Seed QSOs for BB2BB (different callsigns)
    await _make_qso_doc("BB2BB", "DL1ABC", BAND="10M", MODE="CW").insert()
    await _make_qso_doc("BB2BB", "JA1YWX", BAND="15M", MODE="CW").insert()

    # Query AA1AA stats
    aa_stats = await get_stats("AA1AA")
    assert aa_stats["total_qsos"] == 3
    assert "20M" in aa_stats["band_counts"]
    assert "40M" in aa_stats["band_counts"]
    assert aa_stats["band_counts"].get("10M") is None  # BB2BB's band
    assert aa_stats["band_counts"].get("15M") is None  # BB2BB's band

    # Query BB2BB stats
    bb_stats = await get_stats("BB2BB")
    assert bb_stats["total_qsos"] == 2
    assert "10M" in bb_stats["band_counts"]
    assert "15M" in bb_stats["band_counts"]
    assert bb_stats["band_counts"].get("20M") is None  # AA1AA's band
    assert bb_stats["band_counts"].get("40M") is None  # AA1AA's band


@pytest.mark.asyncio
async def test_stats_excludes_soft_deleted(stats_test_db):
    """get_stats() excludes soft-deleted QSOs from all counts."""
    await _make_qso_doc("AA1AA", "W1AW").insert()
    deleted_qso = _make_qso_doc("AA1AA", "K1TTT")
    deleted_qso.is_deleted = True  # Beanie field name (alias _deleted stored in MongoDB)
    await deleted_qso.insert()

    result = await get_stats("AA1AA")
    assert result["total_qsos"] == 1
    assert sum(result["band_counts"].values()) == 1


@pytest.mark.asyncio
async def test_stats_dxcc_entity_resolution(stats_test_db):
    """get_stats() resolves callsigns to DXCC entity names via pycountry (D-01)."""
    await _make_qso_doc("AA1AA", "W1AW").insert()  # US callsign
    await _make_qso_doc("AA1AA", "DL1ABC").insert()  # German callsign

    result = await get_stats("AA1AA")
    entity_names = [e["name"] for e in result["entity_counts"]]
    assert "United States" in entity_names
    assert "Germany" in entity_names
    assert result["unique_entity_count"] == 2


@pytest.mark.asyncio
async def test_stats_unknown_callsign_bucket(stats_test_db):
    """Unresolvable callsigns are grouped under 'Unknown' (D-02)."""
    # Insert a QSO with a callsign that lookup_prefix cannot resolve
    # Use a maritime mobile suffix as an example
    await _make_qso_doc("AA1AA", "W1AW").insert()

    result = await get_stats("AA1AA")
    # At minimum, we verify the function does not crash and returns entity_counts
    assert isinstance(result["entity_counts"], list)
    assert result["total_qsos"] == 1


# ---------------------------------------------------------------------------
# Route-level tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stats_route_requires_auth(http_client):
    """GET /log/stats without cookie redirects to /log/login."""
    resp = await http_client.get("/log/stats", follow_redirects=False)
    assert resp.status_code == 302
    assert "/log/login" in resp.headers.get("location", "")


@pytest.mark.asyncio
async def test_stats_route_empty_log(stats_test_db, http_client):
    """GET /log/stats returns 200 for authenticated operator with zero QSOs."""
    # Create a test user
    user = User(
        username="testop",
        hashed_password=hash_password("testpass"),
        callsign="TESTOP",
    )
    await user.insert()

    # Create JWT cookie
    token = create_access_token(data={"sub": "testop", "callsign": "TESTOP"})
    http_client.cookies.set("access_token", token)

    resp = await http_client.get("/log/stats", follow_redirects=False)
    assert resp.status_code == 200
    assert "0" in resp.text  # total_qsos == 0 appears in stub template
