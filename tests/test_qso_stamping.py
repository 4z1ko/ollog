"""Tests for QSO auto-stamping behaviour in build_qso_dict.

Tests 1–7 are synchronous unit tests of build_qso_dict() — no MongoDB connection
required. User objects are constructed directly (no .insert()/.save() calls).

The stamping_db fixture is included for future endpoint-level integration tests
but is not used by the current test suite.
"""
import socket
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.auth.models import User
from app.qso.models import QSO
from app.qso.service import build_qso_dict


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
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def stamping_db():
    """Function-scoped test database for future endpoint-level stamping tests."""
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_stamping_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_stamping_test")
    await client.aclose()


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

_BASE_BODY = {
    "CALL": "K2ABC",
    "QSO_DATE": "20240101",
    "TIME_ON": "1200",
    "BAND": "20M",
    "MODE": "SSB",
}


def _make_user(**kwargs) -> User:
    """Construct a User without Beanie initialisation (uses model_construct to skip DB checks)."""
    defaults = {
        "username": "w1aw",
        "hashed_password": "x",
        "callsign": "W1AW",
        "role": "operator",
        "enabled": True,
        "station_callsign": None,
        "name": None,
        "email": None,
        "qth": None,
        "state": None,
        "country": None,
        "my_gridsquare": None,
        "latitude": None,
        "longitude": None,
        "my_rig": None,
        "my_antenna": None,
        "tx_pwr": None,
    }
    defaults.update(kwargs)
    return User.model_construct(**defaults)


# ---------------------------------------------------------------------------
# Unit tests — synchronous (build_qso_dict is a plain function)
# ---------------------------------------------------------------------------

def test_stamp_operator_from_profile():
    """STAMP-01: OPERATOR is set to profile.callsign when profile is provided."""
    user = _make_user(callsign="W1AW")
    result = build_qso_dict(dict(_BASE_BODY), "w1aw", profile=user)
    assert result["OPERATOR"] == "W1AW"


def test_stamp_station_callsign_present():
    """STAMP-02: STATION_CALLSIGN is present when profile.station_callsign is set."""
    user = _make_user(callsign="W1AW", station_callsign="W1AW/M")
    result = build_qso_dict(dict(_BASE_BODY), "w1aw", profile=user)
    assert result["STATION_CALLSIGN"] == "W1AW/M"


def test_stamp_station_callsign_absent_when_none():
    """STAMP-02: STATION_CALLSIGN is absent entirely when profile.station_callsign is None."""
    user = _make_user(callsign="W1AW", station_callsign=None)
    result = build_qso_dict(dict(_BASE_BODY), "w1aw", profile=user)
    assert "STATION_CALLSIGN" not in result


def test_stamp_all_profile_fields():
    """All optional profile fields are stamped when set."""
    user = _make_user(
        callsign="W1AW",
        station_callsign="W1AW/P",
        my_gridsquare="FN31pr",
        my_rig="IC-7300",
        my_antenna="Dipole",
        tx_pwr=100.0,
    )
    result = build_qso_dict(dict(_BASE_BODY), "w1aw", profile=user)
    assert result["STATION_CALLSIGN"] == "W1AW/P"
    assert result["MY_GRIDSQUARE"] == "FN31pr"
    assert result["MY_RIG"] == "IC-7300"
    assert result["MY_ANTENNA"] == "Dipole"
    assert result["TX_PWR"] == "100.0"


def test_stamp_tx_pwr_zero_is_valid():
    """TX_PWR=0.0 must be stamped — zero watts is a valid value (QRP beacon, receive-only)."""
    user = _make_user(callsign="W1AW", tx_pwr=0.0)
    result = build_qso_dict(dict(_BASE_BODY), "w1aw", profile=user)
    assert result["TX_PWR"] == "0.0"


def test_no_profile_no_stamp():
    """STAMP-03: No profile-derived fields appear when profile=None (ADIF import path)."""
    result = build_qso_dict(dict(_BASE_BODY), "w1aw", profile=None)
    assert "OPERATOR" not in result
    assert "STATION_CALLSIGN" not in result
    assert "MY_GRIDSQUARE" not in result


def test_bare_user_no_extra_fields():
    """Operator with only required User fields — OPERATOR stamped, no other profile fields."""
    user = _make_user(callsign="W1AW")
    # All profile fields default to None — none should appear except OPERATOR
    result = build_qso_dict(dict(_BASE_BODY), "w1aw", profile=user)
    assert result["OPERATOR"] == "W1AW"
    assert "STATION_CALLSIGN" not in result
    assert "MY_GRIDSQUARE" not in result
    assert "MY_RIG" not in result
    assert "MY_ANTENNA" not in result
    assert "TX_PWR" not in result
