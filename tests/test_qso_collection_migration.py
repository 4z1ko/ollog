from datetime import datetime, timezone

import pytest
from pymongo.errors import DuplicateKeyError

from app.qso.collection_migration import migrate_shared_qsos_to_user_collections


class FakeUpdateResult:
    def __init__(self, upserted_id=None) -> None:
        self.upserted_id = upserted_id


class FakeCursor:
    def __init__(self, docs) -> None:
        self.docs = list(docs)

    def __aiter__(self):
        self._iter = iter(self.docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class FakeCollection:
    def __init__(self, name, docs=None, op_log=None) -> None:
        self.name = name
        self.docs = {doc["_id"]: dict(doc) for doc in docs or []}
        self.op_log = op_log if op_log is not None else []

    def find(self, _filter):
        return FakeCursor(self.docs.values())

    async def create_indexes(self, indexes):
        self.op_log.append(("create_indexes", self.name))
        return [idx.document["name"] for idx in indexes]

    async def update_one(self, filter_doc, update_doc, *, upsert=False):
        self.op_log.append(("update_one", self.name, filter_doc["_id"]))
        doc_id = filter_doc["_id"]
        if doc_id in self.docs:
            return FakeUpdateResult()

        if not upsert:
            return FakeUpdateResult()

        new_doc = {"_id": doc_id, **dict(update_doc["$setOnInsert"])}
        row_hash = new_doc.get("rowHash")
        if row_hash is not None:
            for existing in self.docs.values():
                if existing.get("rowHash") == row_hash:
                    raise DuplicateKeyError("duplicate rowHash")

        self.docs[doc_id] = new_doc
        return FakeUpdateResult(upserted_id=doc_id)


class FakeDatabase:
    def __init__(self, source_docs) -> None:
        self.op_log = []
        self.collections = {
            "qsos": FakeCollection("qsos", source_docs, self.op_log),
        }

    def __getitem__(self, collection_name):
        if collection_name not in self.collections:
            self.collections[collection_name] = FakeCollection(
                collection_name,
                op_log=self.op_log,
            )
        return self.collections[collection_name]


class FakeUser:
    def __init__(self, username, callsign) -> None:
        self.username = username
        self.callsign = callsign


def _doc(doc_id, operator="W1AW", **extra):
    doc = {
        "_id": doc_id,
        "_operator": operator,
        "CALL": "K1ABC",
        "BAND": "20M",
        "MODE": "SSB",
        "_deleted": False,
        "_created_at": datetime(2026, 6, 7, tzinfo=timezone.utc),
        "rowHash": f"hash-{doc_id}",
        "COMMENT": "legacy extra",
        "STATION_CALLSIGN": "W1AW/P",
        "CUSTOM_FIELD_1": "custom",
    }
    doc.update(extra)
    return doc


@pytest.mark.asyncio
async def test_migration_copies_docs_to_username_collections():
    db = FakeDatabase([
        _doc("q1", operator="W1AW"),
        _doc("q2", operator="K1ABC"),
    ])

    report = await migrate_shared_qsos_to_user_collections(
        db=db,
        users=[
            FakeUser("john_doe", "W1AW"),
            FakeUser("alice", "K1ABC"),
        ],
    )

    assert report["scanned"] == 2
    assert report["migrated"] == 2
    assert db["john_doe_qsos"].docs["q1"]["_operator"] == "W1AW"
    assert db["alice_qsos"].docs["q2"]["_operator"] == "K1ABC"
    assert db["john_doe_qsos"].docs["q1"]["COMMENT"] == "legacy extra"


@pytest.mark.asyncio
async def test_migration_is_idempotent_and_does_not_overwrite_existing_target():
    db = FakeDatabase([_doc("q1", operator="W1AW", COMMENT="source")])
    target = db["john_doe_qsos"]
    target.docs["q1"] = _doc("q1", operator="W1AW", COMMENT="target edit")

    report = await migrate_shared_qsos_to_user_collections(
        db=db,
        users=[FakeUser("john_doe", "W1AW")],
    )

    assert report["migrated"] == 0
    assert report["already_present"] == 1
    assert target.docs["q1"]["COMMENT"] == "target edit"


@pytest.mark.asyncio
async def test_migration_reports_unresolved_operators_without_copying():
    db = FakeDatabase([
        _doc("q1", operator=""),
        _doc("q2", operator="UNKNOWN"),
    ])

    report = await migrate_shared_qsos_to_user_collections(
        db=db,
        users=[FakeUser("john_doe", "W1AW")],
    )

    assert report["migrated"] == 0
    assert [entry["reason"] for entry in report["unresolved"]] == [
        "missing_operator",
        "unknown_operator",
    ]
    assert db["john_doe_qsos"].docs == {}


@pytest.mark.asyncio
async def test_migration_reports_ambiguous_callsigns_without_guessing():
    db = FakeDatabase([_doc("q1", operator="W1AW")])

    report = await migrate_shared_qsos_to_user_collections(
        db=db,
        users=[
            FakeUser("first", "W1AW"),
            FakeUser("second", "W1AW"),
        ],
    )

    assert report["migrated"] == 0
    assert report["ambiguous"][0]["reason"] == "ambiguous_operator"
    assert report["ambiguous"][0]["usernames"] == ["first", "second"]
    assert db["first_qsos"].docs == {}
    assert db["second_qsos"].docs == {}


@pytest.mark.asyncio
async def test_migration_preserves_soft_delete_and_raw_fields():
    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    source = _doc(
        "q1",
        operator="W1AW",
        _deleted=True,
        _created_at=created_at,
        rowHash="preserved-hash",
        MY_RIG="IC-7300",
    )
    db = FakeDatabase([source])

    await migrate_shared_qsos_to_user_collections(
        db=db,
        users=[FakeUser("john_doe", "W1AW")],
    )

    migrated = db["john_doe_qsos"].docs["q1"]
    assert migrated["_id"] == "q1"
    assert migrated["_deleted"] is True
    assert migrated["_created_at"] == created_at
    assert migrated["rowHash"] == "preserved-hash"
    assert migrated["STATION_CALLSIGN"] == "W1AW/P"
    assert migrated["CUSTOM_FIELD_1"] == "custom"
    assert migrated["MY_RIG"] == "IC-7300"


@pytest.mark.asyncio
async def test_migration_initializes_indexes_before_writes():
    db = FakeDatabase([_doc("q1", operator="W1AW")])

    await migrate_shared_qsos_to_user_collections(
        db=db,
        users=[FakeUser("john_doe", "W1AW")],
    )

    assert db.op_log[0] == ("create_indexes", "john_doe_qsos")
    assert db.op_log[1] == ("update_one", "john_doe_qsos", "q1")


@pytest.mark.asyncio
async def test_migration_dry_run_reports_without_writing_or_indexing():
    db = FakeDatabase([_doc("q1", operator="W1AW")])

    report = await migrate_shared_qsos_to_user_collections(
        db=db,
        users=[FakeUser("john_doe", "W1AW")],
        dry_run=True,
    )

    assert report["would_migrate"] == 1
    assert report["migrated"] == 0
    assert report["collections_would_initialize"] == ["john_doe_qsos"]
    assert report["collections_initialized"] == []
    assert db["john_doe_qsos"].docs == {}
    assert db.op_log == []


@pytest.mark.asyncio
async def test_migration_reports_row_hash_conflicts():
    db = FakeDatabase([_doc("q1", operator="W1AW", rowHash="same")])
    db["john_doe_qsos"].docs["other"] = _doc("other", operator="W1AW", rowHash="same")

    report = await migrate_shared_qsos_to_user_collections(
        db=db,
        users=[FakeUser("john_doe", "W1AW")],
    )

    assert report["migrated"] == 0
    assert report["conflicts"][0]["reason"] == "duplicate_key"
