"""Copy legacy shared QSO documents into per-user collections."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from beanie import init_beanie
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError

from app import database
from app.auth.models import User
from app.config import settings
from app.qso.collections import ensure_user_qso_indexes, qso_collection_name
from app.qso.models import QSO
from app.tokens.models import ApiToken

logger = logging.getLogger(__name__)

LEGACY_QSO_COLLECTION = "qsos"


def _normalize_callsign(callsign: Any) -> str:
    if not isinstance(callsign, str):
        return ""
    return callsign.strip().upper()


def _doc_ref(doc: dict[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        "id": str(doc.get("_id")),
        "operator": doc.get("_operator"),
        "reason": reason,
    }


def _empty_report(*, dry_run: bool) -> dict[str, Any]:
    return {
        "dry_run": dry_run,
        "scanned": 0,
        "would_migrate": 0,
        "migrated": 0,
        "already_present": 0,
        "unresolved": [],
        "ambiguous": [],
        "conflicts": [],
        "failed": [],
        "collections_initialized": [],
        "collections_would_initialize": [],
    }


def _user_callsign_map(users: Iterable[Any]) -> dict[str, list[Any]]:
    callsigns: dict[str, list[Any]] = defaultdict(list)
    for user in users:
        normalized = _normalize_callsign(getattr(user, "callsign", None))
        if normalized:
            callsigns[normalized].append(user)
    return callsigns


async def _load_users() -> list[User]:
    return await User.find_all().to_list()


def _get_database() -> Any:
    client = database.get_client()
    if client is None:
        raise RuntimeError("MongoDB client is not initialized")
    return client[settings.mongodb_db]


async def migrate_shared_qsos_to_user_collections(
    *,
    db: Any | None = None,
    users: Iterable[Any] | None = None,
    dry_run: bool = False,
    report_path: str | Path | None = None,
) -> dict[str, Any]:
    """Copy documents from shared ``qsos`` into per-user QSO collections.

    The migration is copy-only and insert-only: existing target documents with
    the same ``_id`` are left untouched, which makes reruns safe.
    """
    db = db if db is not None else _get_database()
    users = list(users) if users is not None else await _load_users()
    users_by_callsign = _user_callsign_map(users)
    source = db[LEGACY_QSO_COLLECTION]
    report = _empty_report(dry_run=dry_run)
    initialized_usernames: set[str] = set()

    cursor = source.find({})
    async for raw_doc in cursor:
        doc = dict(raw_doc)
        report["scanned"] += 1

        operator_key = _normalize_callsign(doc.get("_operator"))
        if not operator_key:
            report["unresolved"].append(_doc_ref(doc, reason="missing_operator"))
            continue

        matches = users_by_callsign.get(operator_key, [])
        if not matches:
            report["unresolved"].append(_doc_ref(doc, reason="unknown_operator"))
            continue
        if len(matches) > 1:
            entry = _doc_ref(doc, reason="ambiguous_operator")
            entry["usernames"] = [getattr(user, "username", None) for user in matches]
            report["ambiguous"].append(entry)
            continue

        user = matches[0]
        username = user.username
        collection_name = qso_collection_name(username)
        if username not in initialized_usernames:
            if dry_run:
                report["collections_would_initialize"].append(collection_name)
            else:
                await ensure_user_qso_indexes(db[collection_name])
                report["collections_initialized"].append(collection_name)
            initialized_usernames.add(username)

        if dry_run:
            report["would_migrate"] += 1
            continue

        target = db[collection_name]
        insert_doc = dict(doc)
        insert_doc.pop("_id", None)
        try:
            result = await target.update_one(
                {"_id": doc["_id"]},
                {"$setOnInsert": insert_doc},
                upsert=True,
            )
        except DuplicateKeyError as exc:
            entry = _doc_ref(doc, reason="duplicate_key")
            entry["error"] = str(exc)
            report["conflicts"].append(entry)
            continue
        except Exception as exc:  # pragma: no cover - defensive operational report
            entry = _doc_ref(doc, reason="write_failed")
            entry["error"] = str(exc)
            report["failed"].append(entry)
            continue

        if getattr(result, "upserted_id", None) is not None:
            report["migrated"] += 1
        else:
            report["already_present"] += 1

    _write_report(report_path, report)
    logger.info(
        "QSO collection migration: scanned=%d migrated=%d already_present=%d "
        "would_migrate=%d unresolved=%d ambiguous=%d conflicts=%d failed=%d",
        report["scanned"],
        report["migrated"],
        report["already_present"],
        report["would_migrate"],
        len(report["unresolved"]),
        len(report["ambiguous"]),
        len(report["conflicts"]),
        len(report["failed"]),
    )
    return report


def _write_report(report_path: str | Path | None, report: dict[str, Any]) -> None:
    if report_path is None:
        return
    path = Path(report_path)
    path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")


async def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy shared qsos documents into per-user <username>_qsos collections"
    )
    parser.add_argument(
        "--report",
        default="qso-collection-migration-report.json",
        help="Path to write migration report JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would migrate without writing target collections",
    )
    args = parser.parse_args()

    client = AsyncMongoClient(settings.mongodb_uri)
    try:
        await init_beanie(
            database=client[settings.mongodb_db],
            document_models=[QSO, User, ApiToken],
            skip_indexes=True,
        )
        db = client[settings.mongodb_db]
        report = await migrate_shared_qsos_to_user_collections(
            db=db,
            dry_run=args.dry_run,
            report_path=args.report,
        )
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(_main())
