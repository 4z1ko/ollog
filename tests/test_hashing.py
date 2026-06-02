from datetime import datetime, timezone

from app.hashing import canonical_document_hash


def test_same_object_different_key_order_same_hash():
    left = {"CALL": "W1AW", "BAND": "20M", "nested": {"b": 2, "a": 1}}
    right = {"nested": {"a": 1, "b": 2}, "BAND": "20M", "CALL": "W1AW"}

    assert canonical_document_hash(left) == canonical_document_hash(right)


def test_different_values_different_hash():
    base = {"CALL": "W1AW", "BAND": "20M"}
    changed = {"CALL": "W1AW", "BAND": "40M"}

    assert canonical_document_hash(base) != canonical_document_hash(changed)


def test_metadata_fields_do_not_affect_hash():
    base = {"CALL": "W1AW", "BAND": "20M"}
    with_metadata = {
        **base,
        "_id": "abc",
        "id": "def",
        "rowHash": "old",
        "_created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "updatedAt": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    assert canonical_document_hash(base) == canonical_document_hash(with_metadata)


def test_soft_delete_flag_affects_hash():
    active = {"CALL": "W1AW", "BAND": "20M", "_deleted": False}
    deleted = {"CALL": "W1AW", "BAND": "20M", "_deleted": True}

    assert canonical_document_hash(active) != canonical_document_hash(deleted)


def test_date_values_are_stable():
    aware = {"qso_date_utc": datetime(2024, 1, 15, 14, 30, tzinfo=timezone.utc)}
    naive = {"qso_date_utc": datetime(2024, 1, 15, 14, 30)}

    assert canonical_document_hash(aware) == canonical_document_hash(naive)


def test_array_order_is_preserved():
    first = {"values": ["20M", "40M"]}
    second = {"values": ["40M", "20M"]}

    assert canonical_document_hash(first) != canonical_document_hash(second)
