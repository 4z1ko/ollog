"""Helpers for username-routed QSO MongoDB collections."""
from __future__ import annotations

import re
from typing import Any

import pymongo
from pymongo import IndexModel

from app import database
from app.config import settings

_SAFE_USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_QSO_COLLECTION_SUFFIX = "_qsos"


def qso_collection_name(username: str) -> str:
    """Return the per-user QSO collection name for a safe username."""
    if not isinstance(username, str):
        raise ValueError("username must be a string")
    if not username:
        raise ValueError("username must not be empty")
    if username != username.strip():
        raise ValueError("username must not contain leading or trailing whitespace")
    if not _SAFE_USERNAME_RE.fullmatch(username):
        raise ValueError(
            "username may only contain ASCII letters, digits, underscore, and hyphen"
        )

    collection_name = f"{username}{_QSO_COLLECTION_SUFFIX}"
    if "\x00" in collection_name or "$" in collection_name or collection_name.startswith("system."):
        raise ValueError("username produces an unsafe MongoDB collection name")
    return collection_name


def qso_index_models() -> list[IndexModel]:
    """Return index definitions required by per-user QSO collections."""
    return [
        IndexModel(
            [
                ("_operator", pymongo.ASCENDING),
                ("CALL", pymongo.ASCENDING),
                ("qso_date_utc", pymongo.ASCENDING),
                ("BAND", pymongo.ASCENDING),
                ("MODE", pymongo.ASCENDING),
            ],
            name="operator_qso_compound",
        ),
        IndexModel(
            [("_operator", pymongo.ASCENDING)],
            name="operator_idx",
        ),
        IndexModel(
            [("_operator", pymongo.ASCENDING), ("_deleted", pymongo.ASCENDING)],
            name="operator_active_idx",
        ),
        IndexModel(
            [
                ("_operator", pymongo.ASCENDING),
                ("_created_at", pymongo.DESCENDING),
            ],
            name="operator_created_at_idx",
        ),
        IndexModel(
            [("rowHash", pymongo.ASCENDING)],
            name="row_hash_unique_idx",
            unique=True,
            sparse=True,
        ),
    ]


def _username_from_user_or_username(user_or_username: Any) -> str:
    if isinstance(user_or_username, str):
        return user_or_username

    username = getattr(user_or_username, "username", None)
    if isinstance(username, str):
        return username

    raise ValueError("expected a username string or object with a username attribute")


def get_qso_collection_for_username(username: str) -> Any:
    """Return the raw MongoDB collection for a username's QSO log."""
    client = database.get_client()
    if client is None:
        raise RuntimeError("MongoDB client is not initialized")

    return client[settings.mongodb_db][qso_collection_name(username)]


def get_user_qso_collection(user_or_username: Any) -> Any:
    """Return the raw MongoDB QSO collection for a User-like object or username."""
    return get_qso_collection_for_username(_username_from_user_or_username(user_or_username))


async def ensure_user_qso_indexes(collection: Any) -> list[str]:
    """Create per-user QSO indexes idempotently on a raw MongoDB collection."""
    return await collection.create_indexes(qso_index_models())


async def ensure_user_qso_collection_indexes(user_or_username: Any) -> list[str]:
    """Create per-user QSO indexes for a User-like object or username."""
    collection = get_user_qso_collection(user_or_username)
    return await ensure_user_qso_indexes(collection)

