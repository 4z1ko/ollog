# Backup

ollog includes a built-in backup CLI that exports the entire MongoDB database to a compressed EJSON file. No external `mongodump` tool is required.

## What the Backup Does

The backup CLI:

1. Connects to MongoDB using the configured `MONGODB_URI`
2. Exports all collections (QSOs, users, API tokens) as EJSON-encoded data using PyMongo's `bson.json_util.dumps()`
3. Writes a gzip-compressed file to `BACKUP_DIR` with a timestamp filename (e.g., `backup_20240415_020001.gz`)

The pure-Python approach using PyMongo means the backup works inside the `python:3.12-slim` Docker image without needing `mongodump` installed.

## Running a Manual Backup

Run a one-shot backup with Docker Compose:

```bash
docker compose exec app python -m app.backup
```

If running outside Docker:

```bash
python -m app.backup
```

The command prints the path of the created backup file on success:

```
Backup written to /app/backups/backup_20240415_020001.gz (1.2 MB)
```

## Backup File Location

The `docker-compose.yml` includes a bind mount:

```yaml
volumes:
  - ./backups:/app/backups
```

This means backup files are written to the host `./backups/` directory and survive container restarts. The files are accessible directly on the host — no need to copy them out of the container.

## Automated Scheduled Backups

Set the `BACKUP_SCHEDULE` environment variable to a cron expression to enable automatic backups. The scheduler does not start if `BACKUP_SCHEDULE` is absent.

Example — nightly backup at 02:00 UTC:

```
BACKUP_SCHEDULE=0 2 * * *
```

Add this to your `.env` file and restart the stack:

```bash
docker compose down && docker compose up -d
```

On startup, you will see a log line confirming the scheduler is active:

```
Backup scheduler started (cron: 0 2 * * *)
```

Cron expression format: `minute hour day month weekday`. Standard cron syntax is supported (e.g., `*/6 * * * *` for every 6 hours).

## S3 Upload

If `BACKUP_S3_BUCKET` is set, the backup file is automatically uploaded to S3 after creation. The upload uses the standard boto3/aioboto3 credential chain (environment variables, `~/.aws/credentials`, IAM instance role).

To enable S3 upload, add to your `.env`:

```
BACKUP_S3_BUCKET=my-backup-bucket
BACKUP_S3_PREFIX=ollog/backups/
AWS_ACCESS_KEY_ID=your-key-id
AWS_SECRET_ACCESS_KEY=your-secret
AWS_DEFAULT_REGION=us-east-1
```

The S3 key is: `{BACKUP_S3_PREFIX}{filename}`, e.g., `ollog/backups/backup_20240415_020001.gz`.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| BACKUP_DIR | No | `/app/backups` | Local directory for backup files |
| BACKUP_SCHEDULE | No | (none) | Cron expression; scheduler not started if absent |
| BACKUP_S3_BUCKET | No | (none) | S3 bucket for upload; upload skipped if absent |
| BACKUP_S3_PREFIX | No | `backups/` | S3 key prefix |
| AWS_ACCESS_KEY_ID | No* | — | AWS credentials (boto3 credential chain) |
| AWS_SECRET_ACCESS_KEY | No* | — | AWS credentials (boto3 credential chain) |
| AWS_DEFAULT_REGION | No* | — | AWS region (required for S3 upload) |

(*Required when using S3 upload without an IAM instance role)

## Restoring from a Backup

To restore from a backup file:

1. Copy the `.gz` file to your host (it is already in `./backups/` if using the default bind mount).
2. Restore into the running MongoDB container:

```bash
# Copy the backup file into the MongoDB container
docker compose cp ./backups/backup_20240415_020001.gz mongodb:/tmp/

# Restore using mongorestore (available inside the MongoDB container)
docker compose exec mongodb mongorestore \
  --uri="mongodb://localhost:27017/?replicaSet=rs0" \
  --gzip --archive=/tmp/backup_20240415_020001.gz \
  --drop
```

The `--drop` flag drops existing collections before restoring. Omit it to merge instead of replace.

**Warning:** Restoring will overwrite existing data. Take a fresh backup before restoring if needed.
