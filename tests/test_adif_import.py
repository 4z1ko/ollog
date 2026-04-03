"""Integration tests for the ADIF import endpoint (04-02).

Tests POST /api/adif/import with duplicate detection wired in.

All fixtures are local — this file does NOT modify tests/conftest.py.
Integration tests require a live MongoDB at localhost:27017 and are skipped
if unavailable.

Tests cover:
1. Basic import: 3 valid records → 3 accepted, 0 duplicates, 0 errors
2. Duplicate detection: re-import same file → 0 accepted, 3 duplicates
3. Missing required field: 1 record missing CALL → 1 error, rest accepted
4. File size guard: > 10 MB payload → 413
5. Parse error handling: malformed tag → error appears in report
"""
import io
import socket

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient

from app.auth.models import User
from app.auth.service import hash_password
from app.qso.models import QSO


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
async def adif_db():
    """Function-scoped test database with User and QSO registered."""
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_adif_import_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_adif_import_test")
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
# ADIF test fixtures (strings)
# ---------------------------------------------------------------------------

# 3-record ADIF with distinct callsigns and times — all valid
_THREE_RECORD_ADIF = (
    "<CALL:4>W1AW<QSO_DATE:8>20240115<TIME_ON:4>1430<BAND:3>20m<MODE:3>SSB<EOR>"
    "<CALL:5>K1ABC<QSO_DATE:8>20240115<TIME_ON:4>1500<BAND:3>40m<MODE:2>CW<EOR>"
    "<CALL:6>VK2XYZ<QSO_DATE:8>20240115<TIME_ON:4>1600<BAND:3>15m<MODE:3>FT8<EOR>"
)

# Same 3 records — importing twice proves idempotency
_THREE_RECORD_ADIF_DUPLICATE = _THREE_RECORD_ADIF

# 2 valid records + 1 missing CALL
_MISSING_CALL_ADIF = (
    "<CALL:4>W1AW<QSO_DATE:8>20240115<TIME_ON:4>0800<BAND:3>20m<MODE:3>SSB<EOR>"
    "<QSO_DATE:8>20240115<TIME_ON:4>0900<BAND:3>40m<MODE:2>CW<EOR>"
    "<CALL:5>K1ABC<QSO_DATE:8>20240115<TIME_ON:4>1000<BAND:3>15m<MODE:3>FT8<EOR>"
)

# ADIF with a malformed tag (invalid byte length) to trigger parse error
_MALFORMED_ADIF = (
    "<CALL:4>W1AW<QSO_DATE:8>20240115<TIME_ON:4>1430<BAND:3>20m<MODE:3>SSB<EOR>"
    "<CALL:NOTANUMBER>BAD<QSO_DATE:8>20240116<TIME_ON:4>1200<BAND:3>40m<MODE:2>CW<EOR>"
)


# ---------------------------------------------------------------------------
# Test 1: Basic import — 3 accepted, 0 duplicates, 0 errors
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_basic_import_three_records(adif_db):
    """Upload a valid 3-record ADIF file — all 3 accepted, no duplicates, no errors."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.post(
            "/api/adif/import",
            files=_upload(_THREE_RECORD_ADIF),
            headers=_bearer(token),
        )
    assert resp.status_code == 200, f"Import failed: {resp.text}"
    body = resp.json()
    assert body["total_records"] == 3
    assert len(body["accepted"]) == 3
    assert len(body["duplicates"]) == 0
    assert len(body["errors"]) == 0
    # Verify accepted entries have the expected shape
    for item in body["accepted"]:
        assert "record_index" in item
        assert "call" in item
        assert "id" in item


# ---------------------------------------------------------------------------
# Test 2: Re-import same file → 0 accepted, all duplicates (idempotency)
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_reimport_same_file_all_duplicates(adif_db):
    """Second import of the same file produces 0 accepted and 3 duplicates."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        # First import — all accepted
        resp1 = await client.post(
            "/api/adif/import",
            files=_upload(_THREE_RECORD_ADIF),
            headers=_bearer(token),
        )
        assert resp1.status_code == 200
        body1 = resp1.json()
        assert len(body1["accepted"]) == 3
        assert len(body1["duplicates"]) == 0

        # Second import — all duplicates
        resp2 = await client.post(
            "/api/adif/import",
            files=_upload(_THREE_RECORD_ADIF_DUPLICATE),
            headers=_bearer(token),
        )
    assert resp2.status_code == 200, f"Second import failed: {resp2.text}"
    body2 = resp2.json()
    assert body2["total_records"] == 3
    assert len(body2["accepted"]) == 0, "Re-import should produce zero accepted"
    assert len(body2["duplicates"]) == 3, "Re-import should detect all 3 as duplicates"
    assert len(body2["errors"]) == 0
    # Each duplicate entry must carry record_index, call, existing_id
    for item in body2["duplicates"]:
        assert "record_index" in item
        assert "call" in item
        assert "existing_id" in item
        assert len(item["existing_id"]) > 0


# ---------------------------------------------------------------------------
# Test 3: Missing required field — error for bad record, rest accepted
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_missing_required_field_produces_error(adif_db):
    """ADIF with one record missing CALL: that record errors, the rest are accepted."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.post(
            "/api/adif/import",
            files=_upload(_MISSING_CALL_ADIF),
            headers=_bearer(token),
        )
    assert resp.status_code == 200, f"Import failed: {resp.text}"
    body = resp.json()
    assert body["total_records"] == 3
    assert len(body["accepted"]) == 2, "2 valid records should be accepted"
    assert len(body["errors"]) == 1, "1 record missing CALL should error"
    assert len(body["duplicates"]) == 0
    # Error entry should mention the missing field
    err = body["errors"][0]
    assert "CALL" in err["error"]


# ---------------------------------------------------------------------------
# Test 4: File size guard — > 10 MB → 413
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_file_size_guard_413(adif_db):
    """Payload exceeding 10 MB returns 413."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    # Build a payload just over 10 MB
    oversized = b"X" * (10 * 1024 * 1024 + 1)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.post(
            "/api/adif/import",
            files=_upload(oversized),
            headers=_bearer(token),
        )
    assert resp.status_code == 413, f"Expected 413, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# Test 5: Parse error handling — malformed tag appears in errors
# ---------------------------------------------------------------------------

@mongo_required
@pytest.mark.asyncio
async def test_parse_error_in_report(adif_db):
    """ADIF with malformed tag: parse error surfaces in report errors list."""
    await _create_user("op1", "Pass1234!", "VK2ABC")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await _get_token(client, "op1", "Pass1234!")
        resp = await client.post(
            "/api/adif/import",
            files=_upload(_MALFORMED_ADIF),
            headers=_bearer(token),
        )
    assert resp.status_code == 200, f"Import failed: {resp.text}"
    body = resp.json()
    # The valid first record should be accepted
    assert len(body["accepted"]) == 1
    # There should be at least one error from the malformed tag
    assert len(body["errors"]) >= 1
    error_texts = [e["error"] for e in body["errors"]]
    # At least one error references the malformed tag or the missing required field
    # that results from the parse error consuming the bad record
    assert any(
        "Invalid byte length" in t or "Missing required" in t
        for t in error_texts
    ), f"Expected parse or required-field error, got: {error_texts}"
