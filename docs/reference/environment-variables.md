# Environment Variables

Complete reference for all environment variables available in ollog. Set these in your `.env` file at the project root.

## Core Application

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| SECRET_KEY | Yes | (none) | JWT signing key. Set a strong random value. If changed, all existing JWT tokens invalidate immediately. |
| MONGODB_URI | No | `mongodb://mongodb:27017/?replicaSet=rs0` | MongoDB connection string. The docker-compose.yml sets this to include `replicaSet=rs0`. |
| MONGODB_DB | No | `ollog` | MongoDB database name |
| JWT_EXPIRE_MINUTES | No | `480` | JWT token lifetime in minutes. Default covers an 8-hour session. |

## Bootstrap Admin Account

These variables create the initial admin account on first startup only. If an account with `ADMIN_USERNAME` already exists, these variables are ignored.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| ADMIN_USERNAME | No | (none) | Bootstrap admin username (one-time, first startup only) |
| ADMIN_PASSWORD | No | (none) | Bootstrap admin password (one-time, first startup only) |
| ADMIN_CALLSIGN | No | (none) | Bootstrap admin callsign (one-time, first startup only) |

After the first startup, you may remove these from `.env`. The account persists in the database.

## API Tokens (v1.7)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| API_TOKEN_SECRET | Yes | (none) | HMAC-SHA256 key for API token hashing. Required for the API token feature. If changed, all existing API tokens become invalid. |

Note: `APP_OLLOG_TOKEN` is an **ADIF field name** used inside UDP datagrams — it is not an environment variable. See [ADIF Field Reference](adif-field-reference.md).

## UDP ADIF Listener

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| UDP_ENABLED | No | `false` | Set to `true` to start the UDP ADIF listener. |
| UDP_PORT | No | `2237` | UDP port the listener binds to. Update the Docker port mapping if changed. |
| UDP_BIND_HOST | No | `127.0.0.1` | Address the UDP socket binds to. Inside Docker, set to `0.0.0.0` so host traffic reaches the container. |
| UDP_OPERATOR | No | (none) | Fallback operator callsign for UDP QSOs that do not include an `OPERATOR` field. Optional — if every datagram includes an `OPERATOR` field, this variable is not needed. |

## ACLog Bridges

Per-user ACLog bridge hosts and ports are configured from the operator profile
page. These environment variables control the global bridge manager.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| ACLOG_ENABLED | No | `true` | Starts the ACLog bridge manager. Set to `false` to disable all ACLog bridge connections globally. |
| ACLOG_RECONNECT_SECONDS | No | `5` | Delay before retrying a dropped ACLog TCP API connection. |
| ACLOG_SCAN_SECONDS | No | `10` | How often ollog reloads enabled per-user ACLog bridge rows from the database. |

## Database Backup (v1.8)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| BACKUP_DIR | No | `/app/backups` | Local directory for backup files. Bind-mounted to `./backups` on the host in docker-compose.yml. |
| BACKUP_SCHEDULE | No | (none) | Cron expression for automatic backups (e.g., `0 2 * * *` for nightly at 02:00 UTC). Scheduler not started if absent. |
| BACKUP_S3_BUCKET | No | (none) | S3 bucket name for backup upload. Upload skipped if absent. |
| BACKUP_S3_PREFIX | No | `backups/` | S3 key prefix for uploaded backup files. |

## AWS Credentials (for S3 backup)

These follow the standard boto3/aioboto3 credential chain. Environment variables take precedence over `~/.aws/credentials` and IAM instance roles.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| AWS_ACCESS_KEY_ID | No* | — | AWS access key ID |
| AWS_SECRET_ACCESS_KEY | No* | — | AWS secret access key |
| AWS_DEFAULT_REGION | No* | — | AWS region (required for S3 upload) |

(*Required when using S3 backup upload without an IAM instance role)

## Sample .env File

```
# Core (required)
SECRET_KEY=change-me-to-a-long-random-string
API_TOKEN_SECRET=change-me-to-another-long-random-string

# Bootstrap admin (first startup only — can remove after)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123
ADMIN_CALLSIGN=N0CALL

# Optional: UDP ADIF listener
# UDP_ENABLED=true
# UDP_PORT=2237
# UDP_BIND_HOST=0.0.0.0
# UDP_OPERATOR=W1AW  # optional fallback when datagrams omit OPERATOR field

# Optional: ACLog TCP API bridge manager
# ACLOG_ENABLED=true
# ACLOG_RECONNECT_SECONDS=5
# ACLOG_SCAN_SECONDS=10

# Optional: scheduled backup
# BACKUP_SCHEDULE=0 2 * * *
# BACKUP_S3_BUCKET=my-backup-bucket
# BACKUP_S3_PREFIX=ollog/
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_DEFAULT_REGION=us-east-1
```
