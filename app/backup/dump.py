import gzip
import logging
from datetime import datetime
from pathlib import Path

from bson.json_util import dumps, CANONICAL_JSON_OPTIONS
from pymongo import AsyncMongoClient

logger = logging.getLogger(__name__)


async def run_backup(settings) -> Path:
    """Export all MongoDB collections to a gzip NDJSON file using EJSON encoding.

    Creates its own AsyncMongoClient — does NOT use app.database.get_client()
    because get_client() returns None in CLI context where lifespan has not run.

    Returns the Path to the created .gz file.
    """
    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]

    backup_path = (
        Path(settings.backup_dir)
        / f"{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.gz"
    )
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with gzip.open(backup_path, "wt", encoding="utf-8") as gz:
            for coll_name in sorted(await db.list_collection_names()):
                docs = await db[coll_name].find({}).to_list(length=None)
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

    if settings.backup_s3_bucket is not None:
        from app.backup.upload import upload_to_s3

        key = f"{settings.backup_s3_prefix}{backup_path.name}"
        await upload_to_s3(backup_path, settings.backup_s3_bucket, key)

    return backup_path
