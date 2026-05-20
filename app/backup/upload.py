import logging
from pathlib import Path

import aioboto3

logger = logging.getLogger(__name__)


async def upload_to_s3(local_path: Path, bucket: str, key: str) -> None:
    """Upload a local file to S3 asynchronously.

    Catches all exceptions, logs ERROR, and never re-raises — S3 failure must
    not propagate to the caller.  AWS credentials are read from the standard
    boto3 credential chain (env vars, ~/.aws, IAM role, etc.).
    """
    try:
        session = aioboto3.Session()
        async with session.client("s3") as s3:
            with local_path.open("rb") as fp:
                await s3.upload_fileobj(fp, bucket, key)
        logger.info("Uploaded %s to s3://%s/%s", local_path, bucket, key)
    except Exception as exc:
        logger.error("S3 upload failed for %s: %s", local_path, exc)
