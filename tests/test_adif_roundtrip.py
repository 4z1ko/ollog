"""Round-trip tests for ADIF parser + serializer, plus integration tests for the
full import → export → reimport cycle (04-04).

Unit tests (no MongoDB):
1. test_roundtrip_sample_file — parser/serializer round-trip on sample fixture
2. test_roundtrip_non_ascii — UTF-8 multibyte chars survive round-trip
3. test_roundtrip_app_fields — APP_ fields survive parse/serialize round-trip

Integration tests (require live MongoDB at localhost:27017):
4. test_full_roundtrip_zero_changes — import → export → reimport produces 0 accepted, N duplicates
5. test_app_fields_preserved — APP_MYLOGGER_SCORE and APP_CONTEST_ID survive import/export/parse
6. test_userdef_fields_preserved — MY_ANTENNA/MY_RIG survive import/export/parse
7. test_missing_eoh_file — no_eoh_sample.adi imports successfully (parser tolerates missing EOH)
8. test_case_insensitive_field_names — mixed-case field names normalized to UPPERCASE
9. test_whitespace_around_eor — extra newlines between fields accepted without errors
10. test_export_does_not_contain_internal_fields — internal fields absent from exported ADIF
"""
from __future__ import annotations

import io
import socket
from pathlib import Path

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient

from app.adif.parser import parse_adi
from app.adif.serializer import serialize_adi
from app.auth.models import User
from app.auth.service import hash_password
from app.qso.models import QSO

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Unit tests — no MongoDB required
# ---------------------------------------------------------------------------


def test_roundtrip_sample_file():
    """Parse sample.adi, serialize, parse again — record dicts must be identical."""
    original_text = (FIXTURES_DIR / "sample.adi").read_text(encoding="utf-8")
    records1, errors1 = parse_adi(original_text)
    assert len(records1) > 0, "sample.adi must contain at least one record"

    serialized = serialize_adi(records1)
    records2, errors2 = parse_adi(serialized)

    assert len(records1) == len(records2)
    for r1, r2 in zip(records1, records2):
        assert r1 == r2, f"Round-trip dict mismatch:\nOriginal: {r1}\nAfter round-trip: {r2}"


def test_roundtrip_non_ascii():
    """Records with non-ASCII values must survive round-trip via UTF-8 byte-length."""
    records_in = [
        {"CALL": "DL1AB", "NAME": "André", "QTH": "München"},
    ]
    serialized = serialize_adi(records_in)
    records_out, errors = parse_adi(serialized)

    assert len(records_out) == 1
    assert records_out[0]["NAME"] == "André"
    assert records_out[0]["QTH"] == "München"


def test_roundtrip_app_fields():
    """APP_ fields must survive round-trip without being dropped."""
    records_in = [
        {
            "CALL": "W1AW",
            "APP_MYLOGGER_SCORE": "100",
            "APP_MYLOGGER_MULT": "5",
        }
    ]
    serialized = serialize_adi(records_in)
    records_out, errors = parse_adi(serialized)

    assert len(records_out) == 1
    assert records_out[0]["APP_MYLOGGER_SCORE"] == "100"
    assert records_out[0]["APP_MYLOGGER_MULT"] == "5"


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
# Shared integration test helpers
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def roundtrip_db():
    """Function-scoped test database for round-trip integration tests."""
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_adif_roundtrip_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_adif_roundtrip_test")
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


def _upload(content: str | bytes, filename: str = "test.adi") -> dict:
    """Build an httpx multipart file dict for upload."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return {"file": (filename, io.BytesIO(content), "application/octet-stream")}


# ---------------------------------------------------------------------------
# Test 4: Full import → export → reimport produces zero new records (ADIF-05)
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_full_roundtrip_zero_changes(roundtrip_db):
    """Import fixture → export → reimport: 0 accepted, all records as duplicates.

    Proves lossless round-trip guarantee (ADIF-05): an ADIF file exported from
    ollog and re-imported produces zero data changes — all records flagged as
    duplicates.
    """
    await _create_user("op1", "Pass1234!", "VK2TEST")
    fixture_bytes = (FIXTURES_DIR / "roundtrip_sample.adi").read_bytes()
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        headers = _bearer(token)

        # Step 1: Import the fixture file
        resp1 = await client.post(
            "/api/adif/import",
            files=_upload(fixture_bytes, "roundtrip_sample.adi"),
            headers=headers,
        )
        assert resp1.status_code == 200, f"Initial import failed: {resp1.text}"
        body1 = resp1.json()
        n_accepted = len(body1["accepted"])
        assert n_accepted > 0, "Initial import should accept at least 1 record"
        assert len(body1["duplicates"]) == 0, "Initial import should have 0 duplicates"
        assert len(body1["errors"]) == 0, f"Initial import errors: {body1['errors']}"

        # Step 2: Export
        resp_export = await client.get("/api/adif/export", headers=headers)
        assert resp_export.status_code == 200, f"Export failed: {resp_export.text}"
        exported_text = resp_export.text

        # Verify exported ADIF is parseable
        exported_records, export_errors = parse_adi(exported_text)
        assert len(export_errors) == 0, f"Export ADIF parse errors: {export_errors}"
        assert len(exported_records) == n_accepted, (
            f"Exported record count ({len(exported_records)}) != imported ({n_accepted})"
        )

        # Step 3: Re-import the exported ADIF
        resp2 = await client.post(
            "/api/adif/import",
            files=_upload(exported_text, "reexport.adi"),
            headers=headers,
        )
    assert resp2.status_code == 200, f"Re-import failed: {resp2.text}"
    body2 = resp2.json()
    assert len(body2["accepted"]) == 0, (
        f"Re-import should accept 0 records (all duplicates), got {len(body2['accepted'])}"
    )
    assert len(body2["duplicates"]) == n_accepted, (
        f"Re-import should flag all {n_accepted} records as duplicates, "
        f"got {len(body2['duplicates'])}"
    )
    assert len(body2["errors"]) == 0, f"Re-import errors: {body2['errors']}"


# ---------------------------------------------------------------------------
# Test 5: APP_ fields preserved through import → export → parse cycle (ADIF-03)
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_app_fields_preserved(roundtrip_db):
    """APP_MYLOGGER_SCORE and APP_CONTEST_ID survive import → export → parse.

    Validates ADIF-03: APP_ prefixed fields must pass through the full
    import/export cycle with identical values.
    """
    await _create_user("op1", "Pass1234!", "VK2TEST")
    fixture_bytes = (FIXTURES_DIR / "roundtrip_sample.adi").read_bytes()
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        headers = _bearer(token)

        resp_import = await client.post(
            "/api/adif/import",
            files=_upload(fixture_bytes, "roundtrip_sample.adi"),
            headers=headers,
        )
        assert resp_import.status_code == 200, f"Import failed: {resp_import.text}"
        assert len(resp_import.json()["errors"]) == 0

        resp_export = await client.get("/api/adif/export", headers=headers)
        assert resp_export.status_code == 200

    exported_records, _ = parse_adi(resp_export.text)

    # Locate the record with APP_ fields (JA1ABC in fixture record 2)
    app_record = next(
        (r for r in exported_records if r.get("CALL") == "JA1ABC"),
        None,
    )
    assert app_record is not None, (
        f"JA1ABC record not found in exported records: {[r.get('CALL') for r in exported_records]}"
    )

    assert "APP_MYLOGGER_SCORE" in app_record, (
        f"APP_MYLOGGER_SCORE missing from exported record: {app_record}"
    )
    assert app_record["APP_MYLOGGER_SCORE"] == "250", (
        f"APP_MYLOGGER_SCORE value mismatch: {app_record['APP_MYLOGGER_SCORE']!r}"
    )
    assert "APP_CONTEST_ID" in app_record, (
        f"APP_CONTEST_ID missing from exported record: {app_record}"
    )
    assert app_record["APP_CONTEST_ID"] == "ARRL-SWEEPSTAKES-24", (
        f"APP_CONTEST_ID value mismatch: {app_record['APP_CONTEST_ID']!r}"
    )


# ---------------------------------------------------------------------------
# Test 6: USERDEF/custom fields preserved through import → export → parse (ADIF-03)
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_userdef_fields_preserved(roundtrip_db):
    """MY_ANTENNA and MY_RIG survive import → export → parse cycle.

    Validates ADIF-03: non-standard (USERDEF-style) fields must pass through
    the full import/export cycle with identical values.
    """
    await _create_user("op1", "Pass1234!", "VK2TEST")
    fixture_bytes = (FIXTURES_DIR / "roundtrip_sample.adi").read_bytes()
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        headers = _bearer(token)

        resp_import = await client.post(
            "/api/adif/import",
            files=_upload(fixture_bytes, "roundtrip_sample.adi"),
            headers=headers,
        )
        assert resp_import.status_code == 200, f"Import failed: {resp_import.text}"
        assert len(resp_import.json()["errors"]) == 0

        resp_export = await client.get("/api/adif/export", headers=headers)
        assert resp_export.status_code == 200

    exported_records, _ = parse_adi(resp_export.text)

    # Locate the record with USERDEF-style custom fields (DL1XYZ in fixture record 3)
    userdef_record = next(
        (r for r in exported_records if r.get("CALL") == "DL1XYZ"),
        None,
    )
    assert userdef_record is not None, (
        f"DL1XYZ record not found in exported records: {[r.get('CALL') for r in exported_records]}"
    )

    assert "MY_ANTENNA" in userdef_record, (
        f"MY_ANTENNA missing from exported record: {userdef_record}"
    )
    assert userdef_record["MY_ANTENNA"] == "Dipole", (
        f"MY_ANTENNA value mismatch: {userdef_record['MY_ANTENNA']!r}"
    )
    assert "MY_RIG" in userdef_record, (
        f"MY_RIG missing from exported record: {userdef_record}"
    )
    assert userdef_record["MY_RIG"] == "Icom IC-7300", (
        f"MY_RIG value mismatch: {userdef_record['MY_RIG']!r}"
    )


# ---------------------------------------------------------------------------
# Test 7: Parser handles file with missing EOH tag (ADIF-06)
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_missing_eoh_file(roundtrip_db):
    """Importing no_eoh_sample.adi succeeds — parser tolerates absent EOH tag.

    Validates ADIF-06: a file with no EOH tag must be treated as all-records
    (no header section), and records must be accepted without errors.
    """
    await _create_user("op1", "Pass1234!", "VK2TEST")
    fixture_bytes = (FIXTURES_DIR / "no_eoh_sample.adi").read_bytes()
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.post(
            "/api/adif/import",
            files=_upload(fixture_bytes, "no_eoh_sample.adi"),
            headers=_bearer(token),
        )

    assert resp.status_code == 200, f"Import failed: {resp.text}"
    body = resp.json()
    assert body["total_records"] > 0, "No-EOH file should contain parseable records"
    assert len(body["accepted"]) > 0, "Records from no-EOH file should be accepted"
    assert len(body["errors"]) == 0, f"Import errors on no-EOH file: {body['errors']}"


# ---------------------------------------------------------------------------
# Test 8: Case-insensitive field names normalized to UPPERCASE (ADIF-06)
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_case_insensitive_field_names(roundtrip_db):
    """Fixture record 4 has mixed-case field names (<call:5>, <Band:3>, <Freq:6>).

    Validates ADIF-06: parser must normalize field names to UPPERCASE so the
    record is imported and exported with standard UPPERCASE ADIF field names.
    """
    await _create_user("op1", "Pass1234!", "VK2TEST")
    fixture_bytes = (FIXTURES_DIR / "roundtrip_sample.adi").read_bytes()
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        headers = _bearer(token)

        resp_import = await client.post(
            "/api/adif/import",
            files=_upload(fixture_bytes, "roundtrip_sample.adi"),
            headers=headers,
        )
        assert resp_import.status_code == 200, f"Import failed: {resp_import.text}"
        body = resp_import.json()
        assert len(body["errors"]) == 0, (
            f"Import errors (mixed-case record should be accepted): {body['errors']}"
        )

        # VK2AB is the record with mixed-case field names in fixture record 4
        accepted_calls = {item["call"] for item in body["accepted"]}
        assert "VK2AB" in accepted_calls, (
            f"VK2AB (mixed-case record) not accepted: {accepted_calls}"
        )

        resp_export = await client.get("/api/adif/export", headers=headers)
        assert resp_export.status_code == 200

    exported_text = resp_export.text
    exported_records, _ = parse_adi(exported_text)

    # Field names in exported ADIF must be UPPERCASE — verify by checking raw text
    assert "<call:" not in exported_text, (
        "Exported ADIF contains lowercase '<call:' — field names must be UPPERCASE"
    )
    assert "<Band:" not in exported_text, (
        "Exported ADIF contains mixed-case '<Band:' — field names must be UPPERCASE"
    )
    assert "<Freq:" not in exported_text, (
        "Exported ADIF contains mixed-case '<Freq:' — field names must be UPPERCASE"
    )

    # Verify VK2AB record is present with normalized UPPERCASE field name
    vk2ab_record = next(
        (r for r in exported_records if r.get("CALL") == "VK2AB"),
        None,
    )
    assert vk2ab_record is not None, (
        "VK2AB record (mixed-case fixture) not found in exported ADIF"
    )


# ---------------------------------------------------------------------------
# Test 9: Extra whitespace and newlines between fields accepted (ADIF-06)
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_whitespace_around_eor(roundtrip_db):
    """Fixture record 5 (K1DEF) has a newline between each field and before EOR.

    Validates ADIF-06: parser tolerates whitespace/newlines between ADIF tags
    and after EOR without producing errors.
    """
    await _create_user("op1", "Pass1234!", "VK2TEST")
    fixture_bytes = (FIXTURES_DIR / "roundtrip_sample.adi").read_bytes()
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.post(
            "/api/adif/import",
            files=_upload(fixture_bytes, "roundtrip_sample.adi"),
            headers=_bearer(token),
        )

    assert resp.status_code == 200, f"Import failed: {resp.text}"
    body = resp.json()
    assert len(body["errors"]) == 0, (
        f"Import errors (whitespace record should be accepted): {body['errors']}"
    )

    # K1DEF is the record with extra whitespace/newlines in fixture record 5
    accepted_calls = {item["call"] for item in body["accepted"]}
    assert "K1DEF" in accepted_calls, (
        f"K1DEF (whitespace/newline record) not accepted: {accepted_calls}"
    )


# ---------------------------------------------------------------------------
# Test 10: Internal fields excluded from exported ADIF (ADIF-05, ADIF-06)
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_export_does_not_contain_internal_fields(roundtrip_db):
    """Exported ADIF must not contain internal application fields.

    qso_date_utc, _operator, and _deleted are internal MongoDB fields and
    must never appear in the ADIF export output.
    """
    await _create_user("op1", "Pass1234!", "VK2TEST")
    fixture_bytes = (FIXTURES_DIR / "roundtrip_sample.adi").read_bytes()
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        headers = _bearer(token)

        resp_import = await client.post(
            "/api/adif/import",
            files=_upload(fixture_bytes, "roundtrip_sample.adi"),
            headers=headers,
        )
        assert resp_import.status_code == 200, f"Import failed: {resp_import.text}"
        assert len(resp_import.json()["accepted"]) > 0

        resp_export = await client.get("/api/adif/export", headers=headers)
        assert resp_export.status_code == 200

    adi_text = resp_export.text

    assert "qso_date_utc" not in adi_text, (
        f"Internal field 'qso_date_utc' found in exported ADIF"
    )
    assert "_operator" not in adi_text, (
        f"Internal field '_operator' found in exported ADIF"
    )
    assert "_deleted" not in adi_text, (
        f"Internal field '_deleted' found in exported ADIF"
    )
