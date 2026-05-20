"""Integration tests for the ADIF export endpoint (04-03).

Tests GET /api/adif/export — streaming .adi file download.

All fixtures are local — this file does NOT modify tests/conftest.py.
Integration tests require a live MongoDB at localhost:27017 and are skipped
if unavailable.

Tests cover:
1. Export with QSOs: 3 QSOs (including APP_ extra field) → valid ADIF, all 3 present
2. Export excludes soft-deleted QSOs
3. Export excludes other operators' QSOs (operator isolation)
4. qso_date_utc does NOT appear in exported ADIF text
5. APP_ field preserved through export/parse round-trip
"""
import io
import socket

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient

from app.adif.parser import parse_adi
from app.auth.models import User
from app.auth.service import hash_password
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
# Local fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def export_db():
    """Function-scoped test database with User and QSO registered."""
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_adif_export_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_adif_export_test")
    await client.aclose()


async def _create_user(
    username: str,
    password: str,
    callsign: str,
    role: str = "operator",
) -> User:
    user = User(
        username=username,
        hashed_password=hash_password(password),
        callsign=callsign,
        role=role,
        enabled=True,
    )
    await user.insert()
    return user


async def _get_token(client: AsyncClient, username: str, password: str) -> str:
    resp = await client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _insert_qso(operator: str, call: str, band: str, mode: str,
                      qso_date: str, time_on: str, extra: dict | None = None) -> QSO:
    """Helper to insert a QSO using build_qso_dict for consistent field handling."""
    record = {
        "CALL": call,
        "BAND": band,
        "MODE": mode,
        "QSO_DATE": qso_date,
        "TIME_ON": time_on,
    }
    if extra:
        record.update(extra)
    qso_dict = build_qso_dict(record, operator)
    # build_qso_dict doesn't include extra ADIF fields — merge them manually
    if extra:
        for k, v in extra.items():
            if k not in qso_dict and v is not None:
                qso_dict[k] = v
    qso = QSO(**qso_dict)
    await qso.insert()
    return qso


# ---------------------------------------------------------------------------
# Test 1: Export with QSOs — 3 records, including APP_ extra field
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_export_three_qsos_valid_adif(export_db):
    """Export 3 QSOs (one with APP_ field) → valid ADIF, all 3 records present."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app

    # Insert QSOs directly into the DB
    qso1_dict = build_qso_dict(
        {"CALL": "W1AW", "BAND": "20m", "MODE": "SSB", "QSO_DATE": "20240115", "TIME_ON": "1430"},
        "VK2ABC",
    )
    qso1_dict["QSO_DATE"] = "20240115"
    qso1_dict["TIME_ON"] = "1430"
    await QSO(**qso1_dict).insert()

    qso2_dict = build_qso_dict(
        {"CALL": "K1ABC", "BAND": "40m", "MODE": "CW", "QSO_DATE": "20240115", "TIME_ON": "1500"},
        "VK2ABC",
    )
    qso2_dict["QSO_DATE"] = "20240115"
    qso2_dict["TIME_ON"] = "1500"
    await QSO(**qso2_dict).insert()

    # Third QSO includes an APP_ extra field
    qso3_dict = build_qso_dict(
        {"CALL": "VK2XYZ", "BAND": "15m", "MODE": "FT8", "QSO_DATE": "20240115", "TIME_ON": "1600"},
        "VK2ABC",
    )
    qso3_dict["QSO_DATE"] = "20240115"
    qso3_dict["TIME_ON"] = "1600"
    qso3_dict["APP_MYLOGGER_SCORE"] = "100"
    await QSO(**qso3_dict).insert()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.get("/api/adif/export", headers=_bearer(token))

    assert resp.status_code == 200
    content_disp = resp.headers.get("content-disposition", "")
    assert "attachment" in content_disp
    assert "VK2ABC_logbook.adi" in content_disp

    adi_text = resp.text
    records, errors = parse_adi(adi_text)
    assert len(errors) == 0, f"Unexpected parse errors: {errors}"
    assert len(records) == 3, f"Expected 3 records, got {len(records)}"

    calls = {r["CALL"] for r in records}
    assert calls == {"W1AW", "K1ABC", "VK2XYZ"}


# ---------------------------------------------------------------------------
# Test 2: Export excludes soft-deleted QSOs
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_export_excludes_soft_deleted(export_db):
    """Insert 2 QSOs, soft-delete one → export contains only 1."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app

    qso1_dict = build_qso_dict(
        {"CALL": "W1AW", "BAND": "20m", "MODE": "SSB", "QSO_DATE": "20240115", "TIME_ON": "1430"},
        "VK2ABC",
    )
    qso1_dict["QSO_DATE"] = "20240115"
    qso1_dict["TIME_ON"] = "1430"
    qso1 = QSO(**qso1_dict)
    await qso1.insert()

    qso2_dict = build_qso_dict(
        {"CALL": "K1ABC", "BAND": "40m", "MODE": "CW", "QSO_DATE": "20240115", "TIME_ON": "1500"},
        "VK2ABC",
    )
    qso2_dict["QSO_DATE"] = "20240115"
    qso2_dict["TIME_ON"] = "1500"
    qso2 = QSO(**qso2_dict)
    await qso2.insert()

    # Soft-delete the second QSO
    await qso2.update({"$set": {"_deleted": True}})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.get("/api/adif/export", headers=_bearer(token))

    assert resp.status_code == 200
    adi_text = resp.text
    records, errors = parse_adi(adi_text)
    assert len(errors) == 0
    assert len(records) == 1, f"Expected 1 (non-deleted) record, got {len(records)}"
    assert records[0]["CALL"] == "W1AW"


# ---------------------------------------------------------------------------
# Test 3: Export excludes other operators' QSOs (operator isolation)
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_export_operator_isolation(export_db):
    """QSO for operator B does not appear in operator A's export."""
    await _create_user("op_a", "Pass1234!", "VK2ABC")
    await _create_user("op_b", "Pass5678!", "W1XYZ")
    from app.main import app

    # Insert QSO for operator A
    qso_a_dict = build_qso_dict(
        {"CALL": "K1ABC", "BAND": "20m", "MODE": "SSB", "QSO_DATE": "20240115", "TIME_ON": "1000"},
        "VK2ABC",
    )
    qso_a_dict["QSO_DATE"] = "20240115"
    qso_a_dict["TIME_ON"] = "1000"
    await QSO(**qso_a_dict).insert()

    # Insert QSO for operator B
    qso_b_dict = build_qso_dict(
        {"CALL": "VK3ZZZ", "BAND": "40m", "MODE": "CW", "QSO_DATE": "20240115", "TIME_ON": "1100"},
        "W1XYZ",
    )
    qso_b_dict["QSO_DATE"] = "20240115"
    qso_b_dict["TIME_ON"] = "1100"
    await QSO(**qso_b_dict).insert()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op_a", "Pass1234!")
        resp = await client.get("/api/adif/export", headers=_bearer(token))

    assert resp.status_code == 200
    adi_text = resp.text
    records, errors = parse_adi(adi_text)
    assert len(errors) == 0
    assert len(records) == 1, f"Expected only operator A's QSO, got {len(records)}"
    assert records[0]["CALL"] == "K1ABC", "Only operator A's QSO should appear"
    # Operator B's callsign must not appear anywhere in the output
    assert "VK3ZZZ" not in adi_text


# ---------------------------------------------------------------------------
# Test 4: qso_date_utc does NOT appear in exported ADIF text
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_export_excludes_qso_date_utc_field(export_db):
    """The internal qso_date_utc field must not appear as an ADIF field in output."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app

    qso_dict = build_qso_dict(
        {"CALL": "W1AW", "BAND": "20m", "MODE": "SSB", "QSO_DATE": "20240115", "TIME_ON": "1430"},
        "VK2ABC",
    )
    qso_dict["QSO_DATE"] = "20240115"
    qso_dict["TIME_ON"] = "1430"
    await QSO(**qso_dict).insert()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.get("/api/adif/export", headers=_bearer(token))

    assert resp.status_code == 200
    adi_text = resp.text
    # qso_date_utc must not appear as a field name anywhere in the ADIF output
    assert "qso_date_utc" not in adi_text, (
        f"Internal field 'qso_date_utc' found in exported ADIF: {adi_text!r}"
    )


# ---------------------------------------------------------------------------
# Test 5: APP_ field preserved through export/parse round-trip
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_export_app_field_preserved(export_db):
    """QSO with APP_CONTEST_ID field: export → parse → APP_CONTEST_ID present with correct value."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app

    qso_dict = build_qso_dict(
        {"CALL": "W1AW", "BAND": "20m", "MODE": "SSB", "QSO_DATE": "20240115", "TIME_ON": "1430"},
        "VK2ABC",
    )
    qso_dict["QSO_DATE"] = "20240115"
    qso_dict["TIME_ON"] = "1430"
    qso_dict["APP_CONTEST_ID"] = "ARRL-SWEEPSTAKES-2024"
    await QSO(**qso_dict).insert()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.get("/api/adif/export", headers=_bearer(token))

    assert resp.status_code == 200
    adi_text = resp.text
    records, errors = parse_adi(adi_text)
    assert len(errors) == 0
    assert len(records) == 1
    record = records[0]
    assert "APP_CONTEST_ID" in record, (
        f"APP_CONTEST_ID not found in exported record: {record}"
    )
    assert record["APP_CONTEST_ID"] == "ARRL-SWEEPSTAKES-2024", (
        f"APP_CONTEST_ID value mismatch: {record['APP_CONTEST_ID']!r}"
    )
