"""Tests for Phase 52 TIME_ON DB migration.

Integration tests require MongoDB available at localhost:27017.
All integration tests are skipped automatically when MongoDB is unreachable.

Covers:
- DB-01: normalize_time_on() pads 4-digit HHMM values to 6-digit HHMM00
- DB-01: normalize_time_on() is idempotent (running twice is a no-op)
- DB-01: normalize_time_on() skips already-6-digit values (anchored regex)
- DB-02: parse_adif_datetime() accepts HHMM (4-digit) input
- DB-02: parse_adif_datetime() accepts HHMMSS (6-digit) input
"""
import socket

import pytest
import pytest_asyncio
from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.main import normalize_time_on
from app.qso.models import QSO
from app.qso.service import parse_adif_datetime


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
async def migration_db():
    # NOTE: init_beanie() rebinds QSO collection globally. Run migration tests
    # in isolation (`pytest tests/test_migration.py`) to avoid cross-fixture
    # Beanie state collisions with other test files that use a different database.
    client = AsyncMongoClient(
        "mongodb://localhost:27017/?directConnection=true",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_migration_test"]
    await init_beanie(database=db, document_models=[QSO])
    yield db
    await client.drop_database("ollog_migration_test")
    await client.aclose()


# ---------------------------------------------------------------------------
# Tests: DB-01 — normalize_time_on() migration
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_normalize_time_on_pads_4digit(migration_db):
    """DB-01: 4-digit TIME_ON values are padded to 6-digit HHMM00."""
    collection = QSO.get_pymongo_collection()
    await collection.insert_many([
        {"_operator": "W1AW", "CALL": "K1A", "BAND": "20M", "MODE": "SSB",
         "QSO_DATE": "20240115", "TIME_ON": "1430", "_deleted": False},
        {"_operator": "W1AW", "CALL": "K2B", "BAND": "20M", "MODE": "SSB",
         "QSO_DATE": "20240115", "TIME_ON": "0900", "_deleted": False},
    ])
    await normalize_time_on()
    docs = await collection.find({"_operator": "W1AW"}).to_list(length=None)
    assert len(docs) == 2
    times = sorted(d["TIME_ON"] for d in docs)
    assert times == ["090000", "143000"]


@mongo_required
@pytest.mark.asyncio
async def test_normalize_time_on_idempotent(migration_db):
    """DB-01: Running normalize_time_on twice produces no additional changes."""
    collection = QSO.get_pymongo_collection()
    await collection.insert_one(
        {"_operator": "W1AW", "CALL": "K1A", "BAND": "20M", "MODE": "SSB",
         "QSO_DATE": "20240115", "TIME_ON": "1430", "_deleted": False}
    )
    await normalize_time_on()
    after_first = [d["TIME_ON"] for d in await collection.find({"_operator": "W1AW"}).to_list(length=None)]
    await normalize_time_on()
    after_second = [d["TIME_ON"] for d in await collection.find({"_operator": "W1AW"}).to_list(length=None)]
    assert after_first == after_second == ["143000"]


@mongo_required
@pytest.mark.asyncio
async def test_normalize_time_on_skips_already_6digit(migration_db):
    """DB-01: Anchored regex ^\\d{4}$ must not match 6-digit values (no double-padding)."""
    collection = QSO.get_pymongo_collection()
    await collection.insert_one(
        {"_operator": "W1AW", "CALL": "K1A", "BAND": "20M", "MODE": "SSB",
         "QSO_DATE": "20240115", "TIME_ON": "143000", "_deleted": False}
    )
    await normalize_time_on()
    doc = await collection.find_one({"_operator": "W1AW"})
    assert doc["TIME_ON"] == "143000"


# ---------------------------------------------------------------------------
# Tests: DB-02 — parse_adif_datetime() accepts both HHMM and HHMMSS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parse_adif_datetime_accepts_hhmm():
    """DB-02: parse_adif_datetime accepts 4-digit HHMM input."""
    from datetime import timezone
    dt = parse_adif_datetime("20240115", "1430")
    assert dt.hour == 14
    assert dt.minute == 30
    assert dt.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_parse_adif_datetime_accepts_hhmmss():
    """DB-02: parse_adif_datetime accepts 6-digit HHMMSS input."""
    from datetime import timezone
    dt = parse_adif_datetime("20240115", "143000")
    assert dt.hour == 14
    assert dt.minute == 30
    assert dt.second == 0
    assert dt.tzinfo == timezone.utc
