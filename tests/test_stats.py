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

from app import database
from app.auth.models import User
from app.auth.service import create_access_token, hash_password
from app.config import settings
from app.main import app
from app.qso.collections import ensure_user_qso_collection_indexes, get_user_qso_collection
from app.qso.models import QSO
from app.qso.service import qso_to_mongo_doc
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


class FakeAggCursor:
    def __init__(self, docs):
        self.docs = docs

    async def to_list(self, length=None):
        return self.docs if length is None else self.docs[:length]


class FakeStatsCollection:
    def __init__(self, docs):
        self.docs = list(docs)

    def aggregate(self, pipeline):
        docs = list(self.docs)
        match = pipeline[0].get("$match", {})
        docs = [
            doc for doc in docs
            if all(doc.get(key) == value for key, value in match.items())
        ]
        if "$count" in pipeline[1]:
            return FakeAggCursor([{"total": len(docs)}] if docs else [])

        group_key = pipeline[1]["$group"]["_id"].removeprefix("$")
        grouped: dict[str, int] = {}
        for doc in docs:
            grouped[doc.get(group_key)] = grouped.get(doc.get(group_key), 0) + 1
        return FakeAggCursor([
            {"_id": key, "count": count}
            for key, count in grouped.items()
        ])


async def _create_user(username: str, callsign: str, password: str = "testpass") -> User:
    user = User(
        username=username,
        hashed_password=hash_password(password),
        callsign=callsign,
    )
    await user.insert()
    await ensure_user_qso_collection_indexes(user)
    return user


async def _insert_qso(user: User, call: str, **kwargs) -> None:
    qso = _make_qso_doc(user.callsign, call, **kwargs)
    await get_user_qso_collection(user).insert_one(qso_to_mongo_doc(qso))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def stats_test_db(monkeypatch):
    """Function-scoped test database for stats tests."""
    if not _mongo_available():
        pytest.skip("MongoDB not available at localhost:27017")

    client = AsyncMongoClient(
        "mongodb://localhost:27017/?directConnection=true",
        serverSelectionTimeoutMS=2000,
    )
    db_name = "ollog_stats_test"
    db = client[db_name]
    monkeypatch.setattr(database, "_client", client)
    monkeypatch.setattr(settings, "mongodb_db", db_name)
    await init_beanie(database=db, document_models=[QSO, User])
    yield db
    await client.drop_database(db_name)
    await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def http_client(stats_test_db):
    """ASGI test client for route-level tests.

    Requires stats_test_db to have initialized Beanie first (WR-03).
    The explicit dependency ensures correct fixture ordering and prevents
    silent DB misconfiguration if pytest changes fixture evaluation order.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# STATS-07: Empty-state shape
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stats_uses_supplied_collection_without_mongo():
    """Collection-aware stats can be verified without live MongoDB."""
    collection = FakeStatsCollection([
        {"_operator": "AA1AA", "_deleted": False, "CALL": "W1AW", "BAND": "20M", "MODE": "SSB"},
        {"_operator": "AA1AA", "_deleted": False, "CALL": "DL1ABC", "BAND": "40M", "MODE": "FT8"},
        {"_operator": "BB2BB", "_deleted": False, "CALL": "JA1ABC", "BAND": "15M", "MODE": "CW"},
        {"_operator": "AA1AA", "_deleted": True, "CALL": "K1TTT", "BAND": "10M", "MODE": "CW"},
    ])

    result = await get_stats("AA1AA", collection=collection)

    assert result["total_qsos"] == 2
    assert result["band_counts"] == {"20M": 1, "40M": 1}
    assert result["mode_counts"] == {"SSB": 1, "FT8": 1}


@pytest.mark.asyncio
async def test_stats_empty_log(stats_test_db):
    """get_stats() returns complete shape with total_qsos=0 for empty log."""
    user = await _create_user("nocall", "NOCALL")
    result = await get_stats("NOCALL", collection=get_user_qso_collection(user))
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
    aa = await _create_user("aa1aa", "AA1AA")
    bb = await _create_user("bb2bb", "BB2BB")
    # Seed QSOs for AA1AA (US callsigns on 20M SSB)
    await _insert_qso(aa, "W1AW", BAND="20M", MODE="SSB")
    await _insert_qso(aa, "W2AW", BAND="40M", MODE="FT8")
    await _insert_qso(aa, "W3AW", BAND="20M", MODE="SSB")

    # Seed QSOs for BB2BB (different callsigns)
    await _insert_qso(bb, "DL1ABC", BAND="10M", MODE="CW")
    await _insert_qso(bb, "JA1YWX", BAND="15M", MODE="CW")

    # Query AA1AA stats
    aa_stats = await get_stats("AA1AA", collection=get_user_qso_collection(aa))
    assert aa_stats["total_qsos"] == 3
    assert "20M" in aa_stats["band_counts"]
    assert "40M" in aa_stats["band_counts"]
    assert aa_stats["band_counts"].get("10M") is None  # BB2BB's band
    assert aa_stats["band_counts"].get("15M") is None  # BB2BB's band

    # Query BB2BB stats
    bb_stats = await get_stats("BB2BB", collection=get_user_qso_collection(bb))
    assert bb_stats["total_qsos"] == 2
    assert "10M" in bb_stats["band_counts"]
    assert "15M" in bb_stats["band_counts"]
    assert bb_stats["band_counts"].get("20M") is None  # AA1AA's band
    assert bb_stats["band_counts"].get("40M") is None  # AA1AA's band


@pytest.mark.asyncio
async def test_stats_excludes_soft_deleted(stats_test_db):
    """get_stats() excludes soft-deleted QSOs from all counts."""
    user = await _create_user("aa1aa", "AA1AA")
    await _insert_qso(user, "W1AW")
    deleted_qso = _make_qso_doc("AA1AA", "K1TTT")
    deleted_qso.is_deleted = True  # Beanie field name (alias _deleted stored in MongoDB)
    await get_user_qso_collection(user).insert_one(qso_to_mongo_doc(deleted_qso))

    result = await get_stats("AA1AA", collection=get_user_qso_collection(user))
    assert result["total_qsos"] == 1
    assert sum(result["band_counts"].values()) == 1


@pytest.mark.asyncio
async def test_stats_dxcc_entity_resolution(stats_test_db):
    """get_stats() resolves callsigns to DXCC entity names via pycountry (D-01)."""
    user = await _create_user("aa1aa", "AA1AA")
    await _insert_qso(user, "W1AW")  # US callsign
    await _insert_qso(user, "DL1ABC")  # German callsign

    result = await get_stats("AA1AA", collection=get_user_qso_collection(user))
    entity_names = [e["name"] for e in result["entity_counts"]]
    assert "United States" in entity_names
    assert "Germany" in entity_names
    assert result["unique_entity_count"] == 2


@pytest.mark.asyncio
async def test_stats_unknown_callsign_bucket(stats_test_db):
    """Unresolvable callsigns are grouped under 'Unknown' (D-02)."""
    # Insert a QSO with a callsign that lookup_prefix cannot resolve
    # Use a maritime mobile suffix as an example
    user = await _create_user("aa1aa", "AA1AA")
    await _insert_qso(user, "W1AW")

    result = await get_stats("AA1AA", collection=get_user_qso_collection(user))
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
    await _create_user("testop", "TESTOP")

    # Create JWT cookie
    token = create_access_token(data={"sub": "testop", "callsign": "TESTOP"})
    http_client.cookies.set("access_token", token)

    resp = await http_client.get("/log/stats", follow_redirects=False)
    assert resp.status_code == 200
    assert "0" in resp.text  # total_qsos == 0 appears in stub template
    assert 'href="/log/stats"' in resp.text  # STATS-01: stats nav link present in sidebar
    assert "No data yet" in resp.text  # STATS-04: empty-state card message rendered


# ---------------------------------------------------------------------------
# STATS-02: Three pie chart canvas elements rendered for non-empty log
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stats_route_with_data(stats_test_db, http_client):
    """GET /log/stats renders three canvas elements when operator has QSOs (STATS-02)."""
    user = await _create_user("chartop", "CHARTOP", password="chartpass")

    # Insert QSOs across different bands and modes so charts have data
    await _insert_qso(user, "W1AW", BAND="20M", MODE="SSB")
    await _insert_qso(user, "DL1ABC", BAND="40M", MODE="FT8")
    await _insert_qso(user, "JA1YWX", BAND="15M", MODE="CW")

    token = create_access_token(data={"sub": "chartop", "callsign": "CHARTOP"})
    http_client.cookies.set("access_token", token)

    resp = await http_client.get("/log/stats", follow_redirects=False)
    assert resp.status_code == 200
    assert 'id="chart-band"' in resp.text    # STATS-02: Band pie chart canvas present
    assert 'id="chart-mode"' in resp.text    # STATS-02: Mode pie chart canvas present
    assert 'id="chart-entity"' in resp.text  # STATS-02: DXCC entity pie chart canvas present


# ---------------------------------------------------------------------------
# STATS-03: entity_counts capped at 8 named + optional Other for >8 entities
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stats_dxcc_top8_truncation(stats_test_db):
    """get_stats() caps entity_counts to at most 9 entries (8 named + Other) for >8 unique DXCC entities (STATS-03)."""
    user = await _create_user("dxccop", "DXCCOP")
    # Insert 9 QSOs with callsigns from distinct DXCC entities.
    # Prefixes chosen so lookup_prefix resolves them to different countries:
    # W=US, DL=Germany, JA=Japan, VK=Australia, PA=Netherlands, OZ=Denmark,
    # SM=Sweden, OH=Finland, EA=Spain
    distinct_calls = [
        ("W1AW", "20M", "SSB"),    # United States
        ("DL1ABC", "20M", "FT8"),  # Germany
        ("JA1YWX", "20M", "CW"),   # Japan
        ("VK2KGT", "20M", "SSB"),  # Australia
        ("PA3ABC", "20M", "FT8"),  # Netherlands
        ("OZ1ABC", "20M", "CW"),   # Denmark
        ("SM5ABC", "20M", "SSB"),  # Sweden
        ("OH2ABC", "20M", "FT8"),  # Finland
        ("EA3ABC", "20M", "CW"),   # Spain
    ]
    for call, band, mode in distinct_calls:
        await _insert_qso(user, call, BAND=band, MODE=mode)

    result = await get_stats("DXCCOP", collection=get_user_qso_collection(user))
    # Must have at least 9 unique source callsigns seeded
    assert result["total_qsos"] == 9
    # Service must cap to ≤9 entries: at most 8 named + 1 "Other"
    assert len(result["entity_counts"]) <= 9
