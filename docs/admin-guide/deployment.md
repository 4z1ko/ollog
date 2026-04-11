# Deployment

This guide covers deploying ollog using Docker Compose. The stack includes the API and MongoDB — no separate database install is needed.

## Prerequisites

- Docker and Docker Compose v2 installed
- A machine or VM with port 8000 available
- Git

## Quick Start

1. Clone the repository:

   ```bash
   git clone https://github.com/your-org/ollog.git
   cd ollog
   ```

2. Create a `.env` file in the project root (see [Environment Variables](#environment-variables) below):

   ```
   SECRET_KEY=change-me-to-a-long-random-string
   API_TOKEN_SECRET=change-me-to-another-long-random-string
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=changeme123
   ADMIN_CALLSIGN=N0CALL
   ```

3. Start the stack:

   ```bash
   docker compose up -d
   ```

4. Verify the API is up:

   ```bash
   curl http://localhost:8000/auth/me
   ```

   Expected: `401 Unauthorized` — this confirms the API is responding.

5. Open the documentation site in your browser: `http://localhost:8000/guide`

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| SECRET_KEY | Yes | (none) | JWT signing key. Set a strong random value. If changed, all existing tokens invalidate. |
| API_TOKEN_SECRET | Yes | (none) | HMAC-SHA256 key for API token hashing. Required for the API token feature. |
| MONGODB_URI | No | `mongodb://mongodb:27017/?replicaSet=rs0` | MongoDB connection string. |
| MONGODB_DB | No | `ollog` | Database name |
| JWT_EXPIRE_MINUTES | No | `480` | Token lifetime in minutes (default covers an 8-hour session) |
| ADMIN_USERNAME | No | (none) | Bootstrap admin username (one-time, first startup only) |
| ADMIN_PASSWORD | No | (none) | Bootstrap admin password (one-time, first startup only) |
| ADMIN_CALLSIGN | No | (none) | Bootstrap admin callsign (one-time, first startup only) |
| UDP_ENABLED | No | `false` | Set to `true` to start the UDP ADIF listener. |
| UDP_PORT | No | `2237` | UDP port the listener binds to. Must match the Docker port mapping if changed. |
| UDP_BIND_HOST | No | `127.0.0.1` | Address the UDP socket binds to. Inside Docker, set to `0.0.0.0`. |
| UDP_OPERATOR | No | (none) | Operator callsign assigned to QSOs received via UDP. Required when `UDP_ENABLED=true`. |
| BACKUP_SCHEDULE | No | (none) | Cron expression (e.g. `0 2 * * *`) for automatic backups; scheduler not started if absent |
| BACKUP_S3_BUCKET | No | (none) | S3 bucket name for backup upload; upload skipped if absent |
| BACKUP_S3_PREFIX | No | `backups/` | S3 key prefix for uploaded backup files |
| BACKUP_DIR | No | `/app/backups` | Local directory for backup files |

For the full environment variable reference including AWS credential variables, see [Environment Variables](../reference/environment-variables.md).

## Bootstrap Admin Account

On first startup, if `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ADMIN_CALLSIGN` are all set, the app creates an admin account automatically. This only happens once — if an account with that username already exists, the variables are ignored.

After the first startup you can remove the `ADMIN_*` variables from `.env`. The account persists in the database.

## Enabling the UDP Listener

ollog ships with a UDP ADIF listener disabled by default. To enable it in Docker Compose:

```yaml
services:
  api:
    ports:
      - "2237:2237/udp"
    environment:
      - UDP_ENABLED=true
      - UDP_BIND_HOST=0.0.0.0
      - UDP_OPERATOR=N0CALL
```

See [UDP ADIF](../operator-guide/udp-adif.md) for full configuration details.

## Verification Steps

1. Check both services are running and healthy:

   ```bash
   docker compose ps
   ```

2. Confirm the API is responding:

   ```bash
   curl http://localhost:8000/auth/me
   ```

   Expected: `401 Unauthorized`

3. Log in with the admin account:

   ```bash
   curl -X POST http://localhost:8000/auth/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=changeme123"
   ```

   Expected: JSON response containing `access_token`

4. Open `http://localhost:8000/guide` in a browser — the documentation site should load.

5. Open `http://localhost:8000/docs` in a browser — the Swagger UI should load.

## Updating

Pull the latest code, rebuild, and restart:

```bash
git pull
docker compose build
docker compose up -d
```

The `site/` directory is pre-built and included in the Docker image.

## MongoDB Replica Set

ollog uses MongoDB change streams to power the live station feed (SSE). Change streams require MongoDB to run as a replica set.

The `docker-compose.yml` starts MongoDB with `--replSet rs0` and auto-initializes the replica set via a healthcheck. The API container waits for MongoDB to report healthy before starting.

If you are connecting to an external MongoDB instance, set `MONGODB_URI` to point at it and ensure that instance is already configured as a replica set. A standalone MongoDB instance will not work.
