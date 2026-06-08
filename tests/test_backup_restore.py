from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId

from app.backup import dump, restore


class FakeSyncCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    def find(self, _query):
        return list(self.docs)

    def drop(self):
        self.docs.clear()

    def insert_many(self, docs):
        self.docs.extend(docs)


class FakeSyncDatabase:
    def __init__(self, collections=None):
        self.collections = {
            name: FakeSyncCollection(docs)
            for name, docs in (collections or {}).items()
        }

    def list_collection_names(self):
        return list(self.collections)

    def __getitem__(self, name):
        self.collections.setdefault(name, FakeSyncCollection())
        return self.collections[name]


class FakeMongoClient:
    def __init__(self, db):
        self.db = db
        self.closed = False

    def __getitem__(self, _name):
        return self.db

    def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_backup_restore_includes_dynamic_qso_collections(monkeypatch, tmp_path):
    qso_id = ObjectId()
    qso_time = datetime(2026, 6, 8, 4, 30, tzinfo=timezone.utc)
    source_db = FakeSyncDatabase({
        "users": [{"_id": ObjectId(), "username": "alice"}],
        "alice_qsos": [{
            "_id": qso_id,
            "_operator": "W1AW",
            "CALL": "K1ABC",
            "qso_date_utc": qso_time,
        }],
        "bob_qsos": [{
            "_id": ObjectId(),
            "_operator": "K0RY",
            "CALL": "K2XYZ",
            "qso_date_utc": qso_time,
        }],
    })
    restored_db = FakeSyncDatabase()
    settings = SimpleNamespace(
        mongodb_uri="mongodb://test",
        mongodb_db="ollog_test",
        backup_dir=str(tmp_path),
        backup_s3_bucket=None,
        backup_s3_prefix="backups/",
    )

    monkeypatch.setattr(dump, "MongoClient", lambda _uri: FakeMongoClient(source_db))
    backup_path = await dump.run_backup(settings)

    monkeypatch.setattr(restore, "MongoClient", lambda _uri: FakeMongoClient(restored_db))
    await restore.run_restore(str(backup_path), settings)

    assert set(restored_db.collections) == {"users", "alice_qsos", "bob_qsos"}
    restored_qso = restored_db["alice_qsos"].docs[0]
    assert restored_qso["_id"] == qso_id
    assert restored_qso["qso_date_utc"] == qso_time.replace(tzinfo=None)
    assert restored_qso["CALL"] == "K1ABC"
