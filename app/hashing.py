"""Deterministic document hashing utilities."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from typing import Any


DEFAULT_HASH_EXCLUDED_FIELDS: frozenset[str] = frozenset({
    "_id",
    "id",
    "rowHash",
    "row_hash",
    "createdAt",
    "updatedAt",
    "deletedAt",
    "importBatchId",
    "_created_at",
    "created_at",
    "_updated_at",
    "updated_at",
    "_deleted_at",
    "deleted_at",
})


def canonical_document_hash(
    document: Mapping[str, Any],
    *,
    excluded_fields: frozenset[str] = DEFAULT_HASH_EXCLUDED_FIELDS,
) -> str:
    """Return a deterministic SHA-256 hash for a document-like mapping.

    Object keys are sorted recursively, array order is preserved, datetime/date
    values are normalized to stable ISO strings, and known identity/audit fields
    are excluded from equality. The input mapping is never mutated.
    """
    canonical = _canonicalize(document, excluded_fields=excluded_fields)
    payload = json.dumps(
        canonical,
        default=str,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonicalize(value: Any, *, excluded_fields: frozenset[str]) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _canonicalize(value[key], excluded_fields=excluded_fields)
            for key in sorted(value)
            if key not in excluded_fields
        }
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_canonicalize(item, excluded_fields=excluded_fields) for item in value]
    return value
