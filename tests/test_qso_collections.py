import pytest

from app.qso import collections


def test_qso_collection_name_uses_username_suffix_exactly():
    assert collections.qso_collection_name("john_doe") == "john_doe_qsos"


@pytest.mark.parametrize(
    ("username", "expected"),
    [
        ("roy", "roy_qsos"),
        ("N0CALL", "N0CALL_qsos"),
        ("john-doe", "john-doe_qsos"),
        ("user_123", "user_123_qsos"),
    ],
)
def test_qso_collection_name_preserves_safe_username(username, expected):
    assert collections.qso_collection_name(username) == expected


@pytest.mark.parametrize(
    "username",
    [
        "",
        " john",
        "john ",
        "john.doe",
        "john/doe",
        "john\\doe",
        "john$doe",
        "john\x00doe",
        "john doe",
        "system.users",
        None,
        123,
    ],
)
def test_qso_collection_name_rejects_unsafe_username(username):
    with pytest.raises(ValueError):
        collections.qso_collection_name(username)


def test_qso_index_models_match_dynamic_collection_requirements():
    indexes = collections.qso_index_models()

    assert [idx.document["name"] for idx in indexes] == [
        "operator_qso_compound",
        "operator_idx",
        "operator_active_idx",
        "operator_created_at_idx",
        "row_hash_unique_idx",
    ]

    compound_keys = indexes[0].document["key"]
    for expected_key in ["_operator", "CALL", "qso_date_utc", "BAND", "MODE"]:
        assert expected_key in compound_keys

    created_at_keys = indexes[3].document["key"]
    assert created_at_keys["_operator"] == 1
    assert created_at_keys["_created_at"] == -1

    row_hash_index = indexes[4].document
    assert row_hash_index["key"] == {"rowHash": 1}
    assert row_hash_index["unique"] is True
    assert row_hash_index["sparse"] is True


def test_qso_index_models_returns_fresh_instances():
    first = collections.qso_index_models()
    second = collections.qso_index_models()

    assert first is not second
    assert first[0] is not second[0]


class FakeCollection:
    def __init__(self) -> None:
        self.created_indexes = None

    async def create_indexes(self, indexes):
        self.created_indexes = indexes
        return [idx.document["name"] for idx in indexes]


class FakeDatabase:
    def __init__(self) -> None:
        self.collections = {}
        self.requested_collection = None

    def __getitem__(self, collection_name):
        self.requested_collection = collection_name
        collection = FakeCollection()
        self.collections[collection_name] = collection
        return collection


class FakeClient:
    def __init__(self) -> None:
        self.databases = {}
        self.requested_database = None

    def __getitem__(self, database_name):
        self.requested_database = database_name
        database = FakeDatabase()
        self.databases[database_name] = database
        return database


class FakeUser:
    def __init__(self, username: str) -> None:
        self.username = username


def test_get_qso_collection_for_username_uses_configured_database(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(collections.database, "get_client", lambda: fake_client)
    monkeypatch.setattr(collections.settings, "mongodb_db", "ollog_test")

    collection = collections.get_qso_collection_for_username("john_doe")

    assert isinstance(collection, FakeCollection)
    assert fake_client.requested_database == "ollog_test"
    assert fake_client.databases["ollog_test"].requested_collection == "john_doe_qsos"


def test_get_user_qso_collection_reads_username_from_user(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(collections.database, "get_client", lambda: fake_client)
    monkeypatch.setattr(collections.settings, "mongodb_db", "ollog_test")

    collections.get_user_qso_collection(FakeUser("alice"))

    assert fake_client.databases["ollog_test"].requested_collection == "alice_qsos"


def test_get_qso_collection_requires_initialized_client(monkeypatch):
    monkeypatch.setattr(collections.database, "get_client", lambda: None)

    with pytest.raises(RuntimeError, match="MongoDB client is not initialized"):
        collections.get_qso_collection_for_username("john_doe")


def test_get_user_qso_collection_requires_username_attribute():
    with pytest.raises(ValueError, match="username"):
        collections.get_user_qso_collection(object())


@pytest.mark.asyncio
async def test_ensure_user_qso_indexes_creates_expected_indexes():
    collection = FakeCollection()

    names = await collections.ensure_user_qso_indexes(collection)

    assert names == [
        "operator_qso_compound",
        "operator_idx",
        "operator_active_idx",
        "operator_created_at_idx",
        "row_hash_unique_idx",
    ]
    assert collection.created_indexes is not None
    assert collection.created_indexes[-1].document["unique"] is True
    assert collection.created_indexes[-1].document["sparse"] is True


@pytest.mark.asyncio
async def test_ensure_user_qso_collection_indexes_routes_then_indexes(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(collections.database, "get_client", lambda: fake_client)
    monkeypatch.setattr(collections.settings, "mongodb_db", "ollog_test")

    names = await collections.ensure_user_qso_collection_indexes(FakeUser("alice"))

    database = fake_client.databases["ollog_test"]
    assert database.requested_collection == "alice_qsos"
    assert names[-1] == "row_hash_unique_idx"
    assert database.collections["alice_qsos"].created_indexes is not None

