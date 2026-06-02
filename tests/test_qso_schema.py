"""Integration tests for the QSO Beanie Document model.

Tests verify:
- Collection name and index definitions (static)
- Compound unique index is created by init_beanie
- Arbitrary ADIF extra fields stored and retrieved via extra='allow'
- Duplicate insertion raises DuplicateKeyError
- Soft-delete flag (_deleted in MongoDB)
- _operator and _deleted appear as MongoDB field names (not Python aliases)
- find_active() excludes soft-deleted QSOs
- from_mongo_dt() UTC re-attachment utility

Tests requiring MongoDB are skipped if a live instance is not available.
"""

import pytest
from datetime import datetime, timezone, timedelta

from pymongo.errors import DuplicateKeyError

from app.qso.models import QSO
from app.utils import from_mongo_dt


# ---------------------------------------------------------------------------
# Static / import-only tests — no MongoDB required
# ---------------------------------------------------------------------------

def test_qso_collection_name():
    """QSO documents are stored in the 'qsos' collection."""
    assert QSO.Settings.name == "qsos"


def test_qso_has_five_indexes():
    """QSO model declares exactly 5 indexes."""
    assert len(QSO.Settings.indexes) == 5


def test_qso_compound_index_definition():
    """The compound index definition matches the locked decision (unique=True dropped in 03-02).

    Per 03-02 decision: unique=True removed from compound index to support soft-delete
    re-insertion and force=True use cases. App-level find_duplicate() is the enforcement.
    """
    compound_idx = next(
        (idx for idx in QSO.Settings.indexes if idx.document.get("name") == "operator_qso_compound"),
        None,
    )
    assert compound_idx is not None, "operator_qso_compound index not found"
    # unique=True was intentionally dropped in 03-02 — app-level enforcement instead
    assert compound_idx.document.get("unique") is not True
    keys = compound_idx.document["key"]
    # pymongo IndexModel stores keys as a dict (SON) — verify all required fields
    assert "_operator" in keys
    assert "CALL" in keys
    assert "qso_date_utc" in keys
    assert "BAND" in keys
    assert "MODE" in keys


def test_qso_extra_allow_config():
    """QSO model has extra='allow' to accept arbitrary ADIF fields."""
    assert QSO.model_config.get("extra") == "allow"


def test_qso_populate_by_name_config():
    """QSO model has populate_by_name=True for alias compatibility."""
    assert QSO.model_config.get("populate_by_name") is True


def test_qso_operator_field_has_serialization_alias():
    """operator_callsign field uses serialization_alias '_operator'."""
    field_info = QSO.model_fields["operator_callsign"]
    assert field_info.serialization_alias == "_operator"


def test_qso_deleted_field_has_serialization_alias():
    """is_deleted field uses serialization_alias '_deleted'."""
    field_info = QSO.model_fields["is_deleted"]
    assert field_info.serialization_alias == "_deleted"


def test_qso_created_at_field_has_serialization_alias():
    """created_at field uses serialization_alias '_created_at'."""
    field_info = QSO.model_fields["created_at"]
    assert field_info.serialization_alias == "_created_at"


def test_qso_row_hash_field_has_serialization_alias():
    """row_hash field uses serialization_alias 'rowHash'."""
    field_info = QSO.model_fields["row_hash"]
    assert field_info.serialization_alias == "rowHash"


def test_qso_created_at_default_factory():
    """created_at field has a default_factory that produces a UTC-aware datetime.

    Uses model_construct() to bypass Beanie's __init__ (which calls get_pymongo_collection()
    and requires DB init), following the established pattern for unit tests that only
    need to verify Pydantic field defaults.
    """
    from datetime import datetime, timezone
    qso = QSO.model_construct(
        operator_callsign="W1AW",
        CALL="VK2XYZ",
        BAND="20M",
        MODE="SSB",
        created_at=QSO.model_fields["created_at"].default_factory(),
    )
    assert qso.created_at is not None
    assert qso.created_at.tzinfo is not None
    # Should be very close to now (within 5 seconds)
    delta = abs((datetime.now(timezone.utc) - qso.created_at).total_seconds())
    assert delta < 5, f"created_at is {delta}s from now, expected < 5s"


def test_qso_has_find_active_method():
    """QSO has a find_active classmethod."""
    assert callable(getattr(QSO, "find_active", None))


# ---------------------------------------------------------------------------
# from_mongo_dt utility tests — no MongoDB required
# ---------------------------------------------------------------------------

def test_from_mongo_dt_naive():
    """Naive datetime gains UTC tzinfo."""
    naive = datetime(2024, 1, 15, 14, 30, 0)
    result = from_mongo_dt(naive)
    assert result is not None
    assert result.tzinfo is not None
    assert result.tzinfo == timezone.utc
    assert result.replace(tzinfo=None) == naive


def test_from_mongo_dt_aware():
    """Already-aware datetime is returned unchanged."""
    aware = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
    result = from_mongo_dt(aware)
    assert result is aware


def test_from_mongo_dt_aware_non_utc():
    """Already-aware datetime with non-UTC zone is returned as-is (not converted)."""
    eastern = timezone(timedelta(hours=-5))
    aware = datetime(2024, 1, 15, 14, 30, 0, tzinfo=eastern)
    result = from_mongo_dt(aware)
    assert result is aware
    assert result.tzinfo == eastern


def test_from_mongo_dt_none():
    """None input returns None."""
    assert from_mongo_dt(None) is None


# ---------------------------------------------------------------------------
# MongoDB integration tests — require live MongoDB
# ---------------------------------------------------------------------------

pytestmark_mongo = pytest.mark.asyncio


@pytest.fixture
def sample_qso_data():
    """Minimal valid QSO field values."""
    return {
        "operator_callsign": "W1AW",
        "CALL": "VK2XYZ",
        "BAND": "20M",
        "MODE": "SSB",
        "qso_date_utc": datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc),
    }


@pytest.mark.asyncio
async def test_qso_compound_index_exists(test_db):
    """After init_beanie, the compound index exists in MongoDB (non-unique, per 03-02 decision)."""
    indexes = await test_db["qsos"].index_information()
    assert "operator_qso_compound" in indexes, (
        f"operator_qso_compound index not found. Available indexes: {list(indexes.keys())}"
    )
    idx = indexes["operator_qso_compound"]
    # unique=True was removed in 03-02 — app-level find_duplicate() is the enforcement
    assert idx.get("unique") is not True
    index_keys = [k for k, _ in idx["key"]]
    for expected_key in ["_operator", "CALL", "qso_date_utc", "BAND", "MODE"]:
        assert expected_key in index_keys, f"Expected key '{expected_key}' not in index"


@pytest.mark.asyncio
async def test_qso_row_hash_unique_index_exists(test_db):
    """After init_beanie, the rowHash unique index exists in MongoDB."""
    indexes = await test_db["qsos"].index_information()
    assert "row_hash_unique_idx" in indexes, (
        f"row_hash_unique_idx index not found. Available indexes: {list(indexes.keys())}"
    )
    idx = indexes["row_hash_unique_idx"]
    assert idx.get("unique") is True
    index_keys = [k for k, _ in idx["key"]]
    assert index_keys == ["rowHash"]


@pytest.mark.asyncio
async def test_qso_extra_fields_stored(test_db, sample_qso_data):
    """Extra ADIF fields (RST_SENT, COMMENT) are stored and retrieved."""
    qso = QSO(
        **sample_qso_data,
        RST_SENT="59",
        RST_RCVD="59",
        COMMENT="Great DX contact",
    )
    await qso.insert()

    fetched = await QSO.get(qso.id)
    assert fetched is not None

    # Extra fields should be accessible via model_extra
    extra = fetched.model_extra or {}
    assert extra.get("RST_SENT") == "59"
    assert extra.get("RST_RCVD") == "59"
    assert extra.get("COMMENT") == "Great DX contact"


@pytest.mark.asyncio
async def test_qso_duplicate_rejected(test_db, sample_qso_data):
    """Inserting two QSOs with identical effective values raises DuplicateKeyError."""
    qso1 = QSO(**sample_qso_data)
    await qso1.insert()

    qso2 = QSO(**sample_qso_data)
    with pytest.raises(DuplicateKeyError):
        await qso2.insert()


@pytest.mark.asyncio
async def test_qso_insert_stores_row_hash(test_db, sample_qso_data):
    """Raw MongoDB document has rowHash after insert."""
    qso = QSO(**sample_qso_data)
    await qso.insert()

    raw_doc = await test_db["qsos"].find_one({"_id": qso.id})
    assert raw_doc is not None
    assert "rowHash" in raw_doc
    assert isinstance(raw_doc["rowHash"], str)
    assert len(raw_doc["rowHash"]) == 64


@pytest.mark.asyncio
async def test_qso_soft_delete_flag(test_db, sample_qso_data):
    """QSO can be soft-deleted by setting is_deleted=True."""
    qso = QSO(**sample_qso_data)
    await qso.insert()
    raw_before = await test_db["qsos"].find_one({"_id": qso.id})
    original_hash = raw_before["rowHash"]

    assert qso.is_deleted is False

    # Soft-delete
    await qso.set({"is_deleted": True})
    fetched = await QSO.get(qso.id)
    assert fetched is not None
    assert fetched.is_deleted is True
    raw_after = await test_db["qsos"].find_one({"_id": qso.id})
    assert raw_after["rowHash"] != original_hash


@pytest.mark.asyncio
async def test_qso_operator_field_in_mongodb(test_db, sample_qso_data):
    """Raw MongoDB document has '_operator' as field name, not 'operator_callsign'."""
    qso = QSO(**sample_qso_data)
    await qso.insert()

    raw_doc = await test_db["qsos"].find_one({"_id": qso.id})
    assert raw_doc is not None
    assert "_operator" in raw_doc, (
        f"Expected '_operator' in raw MongoDB doc. Keys found: {list(raw_doc.keys())}"
    )
    assert raw_doc["_operator"] == "W1AW"
    # Must NOT have the Python field name
    assert "operator_callsign" not in raw_doc


@pytest.mark.asyncio
async def test_qso_deleted_field_in_mongodb(test_db, sample_qso_data):
    """Raw MongoDB document has '_deleted' as field name, not 'is_deleted'."""
    qso = QSO(**sample_qso_data)
    await qso.insert()

    raw_doc = await test_db["qsos"].find_one({"_id": qso.id})
    assert raw_doc is not None
    assert "_deleted" in raw_doc, (
        f"Expected '_deleted' in raw MongoDB doc. Keys found: {list(raw_doc.keys())}"
    )
    assert raw_doc["_deleted"] is False
    # Must NOT have the Python field name
    assert "is_deleted" not in raw_doc


@pytest.mark.asyncio
async def test_created_at_in_mongodb(test_db, sample_qso_data):
    """Raw MongoDB document has '_created_at' as field name after insert."""
    qso = QSO(**sample_qso_data)
    await qso.insert()
    raw_doc = await test_db["qsos"].find_one({"_id": qso.id})
    assert "_created_at" in raw_doc, (
        f"Expected '_created_at' in raw MongoDB doc. Keys found: {list(raw_doc.keys())}"
    )
    assert "created_at" not in raw_doc


@pytest.mark.asyncio
async def test_operator_created_at_index_exists(test_db):
    """After init_beanie, the operator_created_at_idx index exists in MongoDB."""
    indexes = await test_db["qsos"].index_information()
    assert "operator_created_at_idx" in indexes, (
        f"operator_created_at_idx index not found. Available indexes: {list(indexes.keys())}"
    )


@pytest.mark.asyncio
async def test_patch_does_not_overwrite_created_at(test_db, sample_qso_data):
    """REST PATCH with _created_at in body does not modify the stored value."""
    qso = QSO(**sample_qso_data)
    await qso.insert()
    raw_before = await test_db["qsos"].find_one({"_id": qso.id})
    original_ts = raw_before["_created_at"]

    # Simulate a PATCH with _created_at — strip it, then update
    body = {"BAND": "40M", "_created_at": datetime(2000, 1, 1, tzinfo=timezone.utc), "created_at": datetime(2000, 1, 1, tzinfo=timezone.utc)}
    for protected in ("_operator", "operator_callsign", "_deleted", "is_deleted", "_id",
                      "_created_at", "created_at"):
        body.pop(protected, None)
    if body:
        await qso.update({"$set": body})

    raw_after = await test_db["qsos"].find_one({"_id": qso.id})
    assert raw_after["_created_at"] == original_ts, (
        f"_created_at was modified: {original_ts} -> {raw_after['_created_at']}"
    )
    assert raw_after["BAND"] == "40M"


@pytest.mark.asyncio
async def test_backfill_stamps_missing_created_at(test_db, sample_qso_data):
    """backfill_created_at sets _created_at from ObjectId timestamp for docs that lack it."""
    # Insert a QSO, then manually remove its _created_at to simulate a pre-migration doc
    qso = QSO(**sample_qso_data)
    await qso.insert()
    await test_db["qsos"].update_one(
        {"_id": qso.id}, {"$unset": {"_created_at": ""}}
    )
    raw = await test_db["qsos"].find_one({"_id": qso.id})
    assert "_created_at" not in raw, "Setup: _created_at should be absent"

    # Run the backfill
    from app.main import backfill_created_at
    await backfill_created_at()

    raw_after = await test_db["qsos"].find_one({"_id": qso.id})
    assert "_created_at" in raw_after, "_created_at should be present after backfill"
    # The backfilled timestamp should come from the ObjectId.
    # Normalize both sides to naive UTC for comparison: MongoDB test client uses
    # tz_aware=False so stored values are naive; generation_time may be aware or naive.
    def _to_naive_utc(dt):
        if dt.tzinfo is not None:
            return dt.replace(tzinfo=None)
        return dt
    expected_ts = _to_naive_utc(qso.id.generation_time)
    stored_ts = _to_naive_utc(raw_after["_created_at"])
    assert stored_ts == expected_ts


@pytest.mark.asyncio
async def test_backfill_is_idempotent(test_db, sample_qso_data):
    """Running backfill_created_at twice does not modify already-stamped documents."""
    qso = QSO(**sample_qso_data)
    await qso.insert()
    raw_before = await test_db["qsos"].find_one({"_id": qso.id})
    original_ts = raw_before["_created_at"]

    from app.main import backfill_created_at
    await backfill_created_at()

    raw_after = await test_db["qsos"].find_one({"_id": qso.id})
    assert raw_after["_created_at"] == original_ts, "Backfill should not modify existing _created_at"


@pytest.mark.asyncio
async def test_backfill_row_hash_does_not_overwrite_existing(test_db, sample_qso_data):
    """backfill_qso_row_hash leaves existing rowHash values untouched."""
    qso = QSO(**sample_qso_data)
    await qso.insert()
    await test_db["qsos"].update_one(
        {"_id": qso.id},
        {"$set": {"rowHash": "manual-hash"}},
    )

    from app.qso.row_hash_migration import backfill_qso_row_hash
    report = await backfill_qso_row_hash()

    raw_after = await test_db["qsos"].find_one({"_id": qso.id})
    assert raw_after["rowHash"] == "manual-hash"
    assert report["updated"] == 0


@pytest.mark.asyncio
async def test_backfill_row_hash_reports_duplicates_without_deleting(test_db, sample_qso_data):
    """backfill_qso_row_hash reports duplicate groups and leaves data intact."""
    first = QSO(**sample_qso_data)
    second = QSO(**sample_qso_data)
    await first.insert()
    await test_db["qsos"].update_one({"_id": first.id}, {"$unset": {"rowHash": ""}})
    await second.insert()
    await test_db["qsos"].update_one({"_id": second.id}, {"$unset": {"rowHash": ""}})

    from app.qso.row_hash_migration import backfill_qso_row_hash
    report = await backfill_qso_row_hash()

    assert report["updated"] == 0
    assert len(report["duplicate_groups"]) == 1
    assert {str(first.id), str(second.id)} == set(report["duplicate_groups"][0]["ids"])
    assert await test_db["qsos"].count_documents({}) == 2


@pytest.mark.asyncio
async def test_find_active_excludes_deleted(test_db):
    """find_active() returns only QSOs where _deleted=False."""
    operator = "K1TEST"
    base_dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)

    # Active QSO
    active_qso = QSO(
        operator_callsign=operator,
        CALL="VK2ACTIVE",
        BAND="40M",
        MODE="CW",
        qso_date_utc=base_dt,
        is_deleted=False,
    )
    await active_qso.insert()

    # Soft-deleted QSO (different time to avoid duplicate key)
    deleted_qso = QSO(
        operator_callsign=operator,
        CALL="VK2DELETED",
        BAND="40M",
        MODE="CW",
        qso_date_utc=base_dt + timedelta(hours=1),
        is_deleted=True,
    )
    await deleted_qso.insert()

    results = await QSO.find_active(operator)
    result_ids = [r.id for r in results]

    assert active_qso.id in result_ids, "Active QSO should be in find_active results"
    assert deleted_qso.id not in result_ids, "Deleted QSO should NOT be in find_active results"
    assert len(results) == 1
