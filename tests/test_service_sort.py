"""SORT-04 integration tests: get_qso_page() sort allowlist validation.

Tests:
  - Invalid sort fields are rejected, fallback to default, and WARNING is logged
  - All 10 allowed sort values are accepted without fallback
  - WARNING log includes both the rejected field name and operator callsign
  - _ALLOWED_SORT_FIELDS constant has exactly 10 values

Requires MongoDB reachable at localhost:27017.
"""
import logging
import socket
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.qso.models import QSO
from app.qso.service import _ALLOWED_SORT_FIELDS, get_qso_page


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
async def sort_test_db():
    """Function-scoped test database for sort allowlist tests.

    Skips if MongoDB is not reachable. Drops ollog_sort_test on teardown.
    """
    if not _mongo_available():
        pytest.skip("MongoDB not available at localhost:27017")

    from app.auth.models import User

    client = AsyncMongoClient(
        "mongodb://localhost:27017/?directConnection=true",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_sort_test"]
    await init_beanie(database=db, document_models=[QSO, User])
    yield db
    await client.drop_database("ollog_sort_test")
    await client.aclose()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_sort_falls_back_to_default(sort_test_db, caplog):
    """SORT-04: Invalid sort field falls back to default and returns results.

    get_qso_page() with sort_by='_deleted' (not in allowlist) must:
    - Not raise an error
    - Return items (fallback sort is applied)
    - Emit exactly 1 WARNING from app.qso.service
    - Include the rejected field name in the warning message
    - Include the operator callsign in the warning message
    """
    dt1 = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    dt2 = datetime(2024, 6, 2, 14, 0, 0, tzinfo=timezone.utc)
    await _make_qso_doc("W1AW", "K1TTT", qso_date_utc=dt1).insert()
    await _make_qso_doc("W1AW", "N2KNU", qso_date_utc=dt2).insert()

    with caplog.at_level(logging.WARNING, logger="app.qso.service"):
        items, total = await get_qso_page("W1AW", sort_by="_deleted")

    assert total >= 2, "Expected at least 2 QSOs to be returned after fallback"
    assert len(items) >= 1, "Expected items to be returned with fallback sort"

    warning_records = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and r.name == "app.qso.service"
    ]
    assert len(warning_records) == 1, (
        f"Expected exactly 1 WARNING from app.qso.service, got {len(warning_records)}"
    )
    assert "_deleted" in warning_records[0].message, (
        "WARNING must contain the rejected field name '_deleted'"
    )
    assert "W1AW" in warning_records[0].message, (
        "WARNING must contain the operator callsign 'W1AW'"
    )


@pytest.mark.asyncio
async def test_all_allowed_sort_values_accepted(sort_test_db, caplog):
    """SORT-04: All 10 allowed sort values are accepted without emitting a WARNING.

    Each value in _ALLOWED_SORT_FIELDS must pass through get_qso_page()
    without triggering the fallback guard.
    """
    dt1 = datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    dt2 = datetime(2024, 6, 2, 11, 0, 0, tzinfo=timezone.utc)
    dt3 = datetime(2024, 6, 3, 12, 0, 0, tzinfo=timezone.utc)
    await _make_qso_doc("W1AW", "AA1AA", BAND="20M", MODE="SSB", qso_date_utc=dt1).insert()
    await _make_qso_doc("W1AW", "BB2BB", BAND="40M", MODE="FT8", qso_date_utc=dt2).insert()
    await _make_qso_doc("W1AW", "CC3CC", BAND="15M", MODE="CW", qso_date_utc=dt3).insert()

    with caplog.at_level(logging.WARNING, logger="app.qso.service"):
        for sort_value in _ALLOWED_SORT_FIELDS:
            await get_qso_page("W1AW", sort_by=sort_value)

    service_warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and r.name == "app.qso.service"
    ]
    assert len(service_warnings) == 0, (
        f"Expected 0 WARNINGs for allowed sort values, got {len(service_warnings)}: "
        + str([r.message for r in service_warnings])
    )


@pytest.mark.asyncio
async def test_warning_contains_field_and_operator(sort_test_db, caplog):
    """SORT-04: WARNING log contains both the rejected field and the operator callsign."""
    await _make_qso_doc("K0RY", "W1AW").insert()

    with caplog.at_level(logging.WARNING, logger="app.qso.service"):
        await get_qso_page("K0RY", sort_by="hashed_password")

    warning_records = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and r.name == "app.qso.service"
    ]
    assert len(warning_records) == 1, (
        f"Expected exactly 1 WARNING, got {len(warning_records)}"
    )
    assert "hashed_password" in warning_records[0].message, (
        "WARNING must contain the rejected field name 'hashed_password'"
    )
    assert "K0RY" in warning_records[0].message, (
        "WARNING must contain the operator callsign 'K0RY'"
    )


def test_allowed_sort_fields_constant_has_10_values():
    """SORT-04: _ALLOWED_SORT_FIELDS frozenset has exactly 10 values."""
    expected = {
        "-qso_date_utc", "qso_date_utc",
        "-CALL", "CALL",
        "-BAND", "BAND",
        "-MODE", "MODE",
        "-_created_at", "_created_at",
    }
    assert len(_ALLOWED_SORT_FIELDS) == 10, (
        f"Expected 10 allowed sort fields, got {len(_ALLOWED_SORT_FIELDS)}: {_ALLOWED_SORT_FIELDS}"
    )
    assert _ALLOWED_SORT_FIELDS == expected, (
        f"_ALLOWED_SORT_FIELDS does not match expected set.\n"
        f"  Missing: {expected - _ALLOWED_SORT_FIELDS}\n"
        f"  Extra:   {_ALLOWED_SORT_FIELDS - expected}"
    )
