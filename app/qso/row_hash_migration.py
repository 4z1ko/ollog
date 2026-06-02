"""Backfill and index helpers for QSO rowHash."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

import pymongo
from pymongo import UpdateOne

from app.hashing import canonical_document_hash

logger = logging.getLogger(__name__)


async def ensure_qso_row_hash_index() -> None:
    """Create the QSO rowHash unique index idempotently."""
    from app.qso.models import QSO

    collection = QSO.get_pymongo_collection()
    await collection.create_index(
        [("rowHash", pymongo.ASCENDING)],
        name="row_hash_unique_idx",
        unique=True,
        sparse=True,
    )


async def backfill_qso_row_hash(report_path: str | Path | None = None) -> dict[str, Any]:
    """Backfill missing QSO rowHash values without overwriting existing hashes.

    Duplicate groups are reported and skipped so no existing records are deleted,
    merged, or silently rewritten. Safe to run repeatedly.
    """
    from app.qso.models import QSO

    collection = QSO.get_pymongo_collection()
    missing_cursor = collection.find({"rowHash": {"$exists": False}})

    hashes: dict[str, list[Any]] = defaultdict(list)
    async for doc in missing_cursor:
        hashes[canonical_document_hash(doc)].append(doc["_id"])

    if not hashes:
        report: dict[str, Any] = {
            "updated": 0,
            "skipped_duplicates": 0,
            "duplicate_groups": [],
        }
        logger.info("rowHash backfill: 0 documents — already up to date")
        _write_report(report_path, report)
        await ensure_qso_row_hash_index()
        return report

    existing_cursor = collection.find(
        {"rowHash": {"$in": list(hashes)}},
        {"_id": 1, "rowHash": 1},
    )
    existing_by_hash: dict[str, list[Any]] = defaultdict(list)
    async for doc in existing_cursor:
        existing_by_hash[doc["rowHash"]].append(doc["_id"])

    ops: list[UpdateOne] = []
    duplicate_groups: list[dict[str, Any]] = []
    for row_hash, missing_ids in hashes.items():
        existing_ids = existing_by_hash.get(row_hash, [])
        all_ids = [*existing_ids, *missing_ids]
        if len(all_ids) > 1:
            duplicate_groups.append({
                "rowHash": row_hash,
                "ids": [str(_id) for _id in all_ids],
            })
            continue
        ops.append(
            UpdateOne(
                {"_id": missing_ids[0], "rowHash": {"$exists": False}},
                {"$set": {"rowHash": row_hash}},
            )
        )

    updated = 0
    if ops:
        result = await collection.bulk_write(ops, ordered=False)
        updated = result.modified_count

    report = {
        "updated": updated,
        "skipped_duplicates": sum(len(group["ids"]) for group in duplicate_groups),
        "duplicate_groups": duplicate_groups,
    }
    if duplicate_groups:
        logger.warning(
            "rowHash backfill: %d documents updated, %d duplicate group(s) skipped",
            updated,
            len(duplicate_groups),
        )
    else:
        logger.info("rowHash backfill: %d documents updated", updated)

    _write_report(report_path, report)
    await ensure_qso_row_hash_index()
    return report


def _write_report(report_path: str | Path | None, report: dict[str, Any]) -> None:
    if report_path is None:
        return
    path = Path(report_path)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Backfill QSO rowHash values")
    parser.add_argument(
        "--report",
        default="rowhash-backfill-report.json",
        help="Path to write duplicate/report JSON",
    )
    args = parser.parse_args()

    from beanie import init_beanie
    from pymongo import AsyncMongoClient

    from app.config import settings
    from app.qso.models import QSO

    client = AsyncMongoClient(settings.mongodb_uri)
    try:
        await init_beanie(
            database=client[settings.mongodb_db],
            document_models=[QSO],
            skip_indexes=True,
        )
        report = await backfill_qso_row_hash(args.report)
        print(json.dumps(report, indent=2, sort_keys=True))
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(_main())
