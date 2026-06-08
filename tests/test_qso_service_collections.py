from datetime import datetime, timezone

import pytest
from pymongo.errors import DuplicateKeyError

from app.qso.service import (
    clear_operator_log,
    find_duplicate,
    get_qso_by_id,
    get_qso_page,
    insert_qso_dict,
    soft_delete_qso,
    update_qso_fields,
)


class FakeInsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeUpdateResult:
    modified_count = 1


class FakeDeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


def _matches(doc, query):
    for key, expected in query.items():
        actual = doc.get(key)
        if isinstance(expected, dict):
            if "$gte" in expected and actual < expected["$gte"]:
                return False
            if "$lte" in expected and actual > expected["$lte"]:
                return False
            if "$exists" in expected and (key in doc) is not expected["$exists"]:
                return False
            if "$ne" in expected and actual == expected["$ne"]:
                return False
            if "$regex" in expected:
                import re

                flags = re.I if expected.get("$options") == "i" else 0
                if re.search(expected["$regex"], str(actual), flags) is None:
                    return False
        elif actual != expected:
            return False
    return True


class FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, sort_spec):
        for key, direction in reversed(sort_spec):
            self.docs.sort(key=lambda doc: doc.get(key), reverse=direction < 0)
        return self

    def skip(self, count):
        self.docs = self.docs[count:]
        return self

    def limit(self, count):
        self.docs = self.docs[:count]
        return self

    async def to_list(self, length=None):
        return self.docs if length is None else self.docs[:length]


class FakeCollection:
    def __init__(self):
        self.docs = {}

    async def insert_one(self, doc):
        row_hash = doc.get("rowHash")
        for existing in self.docs.values():
            if row_hash and existing.get("rowHash") == row_hash:
                raise DuplicateKeyError("duplicate rowHash")
        self.docs[doc["_id"]] = dict(doc)
        return FakeInsertResult(doc["_id"])

    async def find_one(self, query, sort=None):
        docs = [doc for doc in self.docs.values() if _matches(doc, query)]
        if sort:
            for key, direction in reversed(sort):
                docs.sort(key=lambda doc: doc.get(key), reverse=direction < 0)
        return docs[0] if docs else None

    def find(self, query):
        return FakeCursor([doc for doc in self.docs.values() if _matches(doc, query)])

    async def count_documents(self, query):
        return len([doc for doc in self.docs.values() if _matches(doc, query)])

    async def update_one(self, query, update_doc):
        doc = await self.find_one(query)
        if doc is None:
            return FakeUpdateResult()
        updates = update_doc.get("$set", {})
        if "rowHash" in updates:
            for existing_id, existing in self.docs.items():
                if existing_id != doc["_id"] and existing.get("rowHash") == updates["rowHash"]:
                    raise DuplicateKeyError("duplicate rowHash")
        doc.update(updates)
        return FakeUpdateResult()

    async def delete_many(self, query):
        ids = [_id for _id, doc in self.docs.items() if _matches(doc, query)]
        for _id in ids:
            self.docs.pop(_id)
        return FakeDeleteResult(len(ids))


def _qso_dict(call="K1ABC", operator="W1AW", qso_date="20260607", time_on="120000"):
    return {
        "CALL": call,
        "QSO_DATE": qso_date,
        "TIME_ON": time_on,
        "BAND": "20M",
        "MODE": "SSB",
        "qso_date_utc": datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc),
        "operator_callsign": operator,
        "is_deleted": False,
        "COMMENT": "extra",
    }


@pytest.mark.asyncio
async def test_insert_broadcasts_app_created_qso(monkeypatch):
    collection = FakeCollection()
    broadcasted = []

    async def _capture_broadcast(qso):
        broadcasted.append(qso)

    monkeypatch.setattr("app.feed.manager.broadcast_qso", _capture_broadcast)

    inserted = await insert_qso_dict(_qso_dict(call="K4LIVE"), collection=collection)

    assert inserted.status == "inserted"
    assert [qso.CALL for qso in broadcasted] == ["K4LIVE"]


@pytest.mark.asyncio
async def test_insert_duplicate_scope_is_per_collection():
    first = FakeCollection()
    second = FakeCollection()
    qso_dict = _qso_dict()

    first_result = await insert_qso_dict(qso_dict, collection=first)
    duplicate_result = await insert_qso_dict(qso_dict, collection=first)
    second_result = await insert_qso_dict(qso_dict, collection=second)

    assert first_result.status == "inserted"
    assert duplicate_result.status == "duplicate"
    assert second_result.status == "inserted"


@pytest.mark.asyncio
async def test_find_duplicate_uses_supplied_collection_only():
    first = FakeCollection()
    second = FakeCollection()
    inserted = await insert_qso_dict(_qso_dict(), collection=first)

    assert await find_duplicate(
        "W1AW", "K1ABC", "20M", "SSB", inserted.qso.qso_date_utc, collection=first
    )
    assert await find_duplicate(
        "W1AW", "K1ABC", "20M", "SSB", inserted.qso.qso_date_utc, collection=second
    ) is None


@pytest.mark.asyncio
async def test_get_qso_page_filters_sorts_and_hydrates():
    collection = FakeCollection()
    await insert_qso_dict(_qso_dict(call="K2BBB", time_on="120000"), collection=collection)
    await insert_qso_dict(_qso_dict(call="K1AAA", time_on="120100"), collection=collection)

    items, total = await get_qso_page(
        "W1AW",
        callsign_filter="K",
        sort_by="CALL",
        collection=collection,
    )

    assert total == 2
    assert [item.CALL for item in items] == ["K1AAA", "K2BBB"]
    assert items[0].model_extra["COMMENT"] == "extra"


@pytest.mark.asyncio
async def test_update_and_soft_delete_use_supplied_collection():
    collection = FakeCollection()
    inserted = await insert_qso_dict(_qso_dict(), collection=collection)
    qso = await get_qso_by_id(inserted.qso.id, collection)

    updated = await update_qso_fields(qso, {"CALL": "K9XYZ"}, collection)
    await soft_delete_qso(updated, collection)
    deleted = await get_qso_by_id(inserted.qso.id, collection)

    assert updated.CALL == "K9XYZ"
    assert deleted.is_deleted is True
    assert deleted.row_hash != qso.row_hash


@pytest.mark.asyncio
async def test_clear_operator_log_deletes_only_active_operator_docs():
    collection = FakeCollection()
    await insert_qso_dict(_qso_dict(operator="W1AW", call="K1AAA"), collection=collection)
    other = await insert_qso_dict(_qso_dict(operator="K0RY", call="K2BBB"), collection=collection)
    deleted_doc = await insert_qso_dict(_qso_dict(operator="W1AW", call="K3CCC"), collection=collection)
    await soft_delete_qso(deleted_doc.qso, collection)

    deleted = await clear_operator_log("W1AW", collection=collection)

    assert deleted == 1
    assert await get_qso_by_id(other.qso.id, collection) is not None
    assert await get_qso_by_id(deleted_doc.qso.id, collection) is not None
