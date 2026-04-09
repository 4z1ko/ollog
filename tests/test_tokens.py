"""Tests for the ApiToken model and token service helpers.

Static tests run without MongoDB.
Integration tests require a live MongoDB at localhost:27017 and are skipped
if unavailable.

API_TOKEN_SECRET must be set before app.config is imported.  We set it here
via os.environ so that pydantic-settings picks it up at Settings() instantiation
time (the .env file value also works in a running app).
"""
import os

# Set before any app imports so pydantic-settings picks it up
os.environ.setdefault("API_TOKEN_SECRET", "test-token-secret-for-unit-tests")

import pytest
import pytest_asyncio
from beanie import init_beanie, PydanticObjectId
from pymongo import AsyncMongoClient

from app.tokens.models import ApiToken
from app.tokens.service import (
    generate_api_token,
    hash_api_token,
    verify_api_token,
    validate_token_name,
)
from app.auth.models import User
from app.qso.models import QSO


# ---------------------------------------------------------------------------
# Static / import-only tests — no MongoDB required
# ---------------------------------------------------------------------------


def test_api_token_collection_name():
    """ApiToken documents are stored in the 'api_tokens' collection."""
    assert ApiToken.Settings.name == "api_tokens"


def test_api_token_has_compound_index():
    """ApiToken model declares a compound index on (token_prefix, user_id)."""
    assert len(ApiToken.Settings.indexes) == 1
    idx = ApiToken.Settings.indexes[0]
    key_doc = idx.document["key"]
    assert "token_prefix" in key_doc
    assert "user_id" in key_doc


def test_api_token_default_enabled():
    """ApiToken.enabled defaults to True."""
    assert ApiToken.model_fields["enabled"].default is True


def test_generate_token_format():
    """generate_api_token() returns correct format and lengths."""
    full_token, token_prefix = generate_api_token()
    assert full_token.startswith("ollog_"), "full token must start with 'ollog_'"
    assert len(full_token) == 49, f"expected 49 chars, got {len(full_token)}"
    assert len(token_prefix) == 8, f"expected 8-char prefix, got {len(token_prefix)}"
    assert token_prefix == full_token[6:14], "prefix must be chars 6-14 of full token"


def test_generate_token_uniqueness():
    """Two successive generate_api_token() calls produce different tokens."""
    token1, _ = generate_api_token()
    token2, _ = generate_api_token()
    assert token1 != token2


def test_hash_api_token_returns_hex():
    """hash_api_token() returns a 64-char lowercase hex string (SHA-256)."""
    result = hash_api_token("ollog_test")
    assert len(result) == 64, f"expected 64-char hex, got {len(result)}"
    assert all(c in "0123456789abcdef" for c in result), "result must be hex"


def test_verify_api_token_roundtrip():
    """hash + verify roundtrip returns True for the same token."""
    full_token, _ = generate_api_token()
    stored_hash = hash_api_token(full_token)
    assert verify_api_token(full_token, stored_hash) is True


def test_verify_api_token_rejects_wrong():
    """verify_api_token() returns False for a different token."""
    full_token, _ = generate_api_token()
    other_token, _ = generate_api_token()
    stored_hash = hash_api_token(full_token)
    assert verify_api_token(other_token, stored_hash) is False


def test_validate_token_name_accepts_valid():
    """validate_token_name() accepts legal names and returns them unchanged."""
    assert validate_token_name("my-token") == "my-token"
    assert validate_token_name("my_token") == "my_token"
    assert validate_token_name("a") == "a"
    eighty_chars = "A" * 80
    assert validate_token_name(eighty_chars) == eighty_chars


def test_validate_token_name_rejects_invalid():
    """validate_token_name() raises ValueError for illegal names."""
    with pytest.raises(ValueError):
        validate_token_name("")
    with pytest.raises(ValueError):
        validate_token_name("A" * 81)
    with pytest.raises(ValueError):
        validate_token_name("has spaces")
    with pytest.raises(ValueError):
        validate_token_name("has!bang")


# ---------------------------------------------------------------------------
# MongoDB availability check
# ---------------------------------------------------------------------------


def _mongo_available() -> bool:
    """Quick synchronous check if MongoDB is reachable at localhost:27017."""
    import socket
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
# Database fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def tokens_db():
    """Function-scoped test database with QSO, User, and ApiToken registered."""
    import socket
    try:
        s = socket.create_connection(("localhost", 27017), timeout=1)
        s.close()
    except OSError:
        pytest.skip("MongoDB not available at localhost:27017")

    client = AsyncMongoClient(
        "mongodb://localhost:27017/?directConnection=true",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_test"]
    await init_beanie(database=db, document_models=[QSO, User, ApiToken])
    yield db
    await client.drop_database("ollog_test")
    await client.aclose()


# ---------------------------------------------------------------------------
# Integration tests (MongoDB required)
# ---------------------------------------------------------------------------


@mongo_required
@pytest.mark.asyncio
async def test_api_token_insert_and_find(tokens_db):
    """ApiToken can be inserted into MongoDB and retrieved by token_prefix."""
    dummy_user_id = PydanticObjectId()
    token = ApiToken(
        user_id=dummy_user_id,
        name="test-token",
        token_prefix="abcd1234",
        hashed_token="deadbeef" * 8,
        enabled=True,
    )
    await token.insert()

    found = await ApiToken.find_one(ApiToken.token_prefix == "abcd1234")
    assert found is not None
    assert found.name == "test-token"
    assert found.user_id == dummy_user_id
    assert found.hashed_token == "deadbeef" * 8
    assert found.enabled is True
