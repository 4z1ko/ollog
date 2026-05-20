import asyncio
import gzip
import logging
from datetime import datetime, timezone
from pathlib import Path

from bson.json_util import dumps, CANONICAL_JSON_OPTIONS
from pymongo import MongoClient

logger = logging.getLogger(__name__)


def _write_backup(settings) -> Path:
    """Sync helper: dump all MongoDB collections to a gzip NDJSON file.

    Uses a synchronous MongoClient so it can be called inside asyncio.to_thread
    without blocking the event loop.
    """
    client = MongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]

    backup_path = (
        Path(settings.backup_dir)
        / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H-%M-%S')}.gz"
    )
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with gzip.open(backup_path, "wt", encoding="utf-8") as gz:
            for coll_name in sorted(db.list_collection_names()):
                docs = list(db[coll_name].find({}))
                for doc in docs:
                    line = (
                        dumps(
                            {"collection": coll_name, "doc": doc},
                            json_options=CANONICAL_JSON_OPTIONS,
                        )
                        + "\n"
                    )
                    gz.write(line)
    finally:
        client.close()

    logger.info("Backup written to %s", backup_path)
    return backup_path


async def run_backup(settings) -> Path:
    """Async orchestrator: run backup in a thread pool and optionally upload to S3.

    Wraps _write_backup in asyncio.to_thread to avoid blocking the event loop
    during synchronous gzip I/O and MongoDB reads.

    Returns the Path to the created .gz file.
    """
    backup_path = await asyncio.to_thread(_write_backup, settings)

    if settings.backup_s3_bucket is not None:
        from app.backup.upload import upload_to_s3

        key = f"{settings.backup_s3_prefix}{backup_path.name}"
        await upload_to_s3(backup_path, settings.backup_s3_bucket, key)

    return backup_path
