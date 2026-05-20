import asyncio
import gzip
import logging

from bson.json_util import loads as bson_loads
from pymongo import MongoClient

logger = logging.getLogger(__name__)


def _restore_from_file(backup_path: str, settings) -> None:
    """Sync helper: drop all collections and restore from gzip NDJSON backup.

    Uses a synchronous MongoClient so it can be called inside asyncio.to_thread
    without blocking the event loop. Uses bson.json_util.loads (NOT json.loads)
    to restore ObjectId, datetime, and all BSON types with correct types.
    """
    client = MongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]

    docs_by_collection: dict[str, list] = {}
    with gzip.open(backup_path, "rt", encoding="utf-8") as gz:
        for line in gz:
            line = line.strip()
            if not line:
                continue
            record = bson_loads(line)
            coll = record["collection"]
            doc = record["doc"]
            docs_by_collection.setdefault(coll, []).append(doc)

    try:
        for coll_name, docs in docs_by_collection.items():
            db[coll_name].drop()
            if docs:
                db[coll_name].insert_many(docs)
    finally:
        client.close()


async def run_restore(backup_path: str, settings) -> None:
    """Async orchestrator: run restore in a thread pool.

    Wraps _restore_from_file in asyncio.to_thread to avoid blocking the
    event loop during synchronous gzip I/O and MongoDB writes.
    """
    await asyncio.to_thread(_restore_from_file, backup_path, settings)
