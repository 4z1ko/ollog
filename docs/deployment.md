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
| MONGODB_URI | No | `mongodb://mongodb:27017/?replicaSet=rs0` | MongoDB connection string. The docker-compose.yml sets this to include `replicaSet=rs0`, which overrides the code default. |
| MONGODB_DB | No | `ollog` | Database name |
| JWT_EXPIRE_MINUTES | No | `60` | Token lifetime in minutes |
| ADMIN_USERNAME | No | (none) | Bootstrap admin username (one-time, first startup only) |
| ADMIN_PASSWORD | No | (none) | Bootstrap admin password (one-time, first startup only) |
| ADMIN_CALLSIGN | No | (none) | Bootstrap admin callsign (one-time, first startup only) |
| UDP_ENABLED | No | `false` | Set to `true` to start the UDP ADIF listener. |
| UDP_PORT | No | `2399` | UDP port the listener binds to. Must match the Docker port mapping if changed. |
| UDP_BIND_HOST | No | `127.0.0.1` | Address the UDP socket binds to. Inside Docker, set to `0.0.0.0` so host traffic reaches the container. |
| UDP_OPERATOR | No | (none) | Operator callsign assigned to QSOs received via UDP. Required when `UDP_ENABLED=true`. |

Sample `.env` file:

```
SECRET_KEY=change-me-to-a-long-random-string
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123
ADMIN_CALLSIGN=N0CALL
```

## Bootstrap Admin Account

On first startup, if `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ADMIN_CALLSIGN` are all set, the app creates an admin account automatically. This only happens once — if an account with that username already exists, the variables are ignored.

After the first startup you can remove the `ADMIN_*` variables from `.env`. The account persists in the database.

## Enabling the UDP Listener

ollog ships with a UDP ADIF listener that accepts datagrams from logging software such as WSJT-X, N1MM+, and Log4OM. The listener is disabled by default and is enabled via environment variables.

To enable UDP in Docker Compose, add the following to the `api` service in your `docker-compose.yml` (the port mapping is already present in the default file):

```yaml
services:
  api:
    ports:
      - "2399:2399/udp"   # UDP ADIF listener port
    environment:
      - UDP_ENABLED=true
      - UDP_BIND_HOST=0.0.0.0   # required inside Docker
      - UDP_OPERATOR=N0CALL     # replace with the operator's callsign
```

`UDP_OPERATOR` must be set to a callsign that has an existing operator account in ollog. QSOs received via UDP are logged under that callsign. If the callsign is not found, the listener logs a WARNING and drops the datagram.

If you change `UDP_PORT` from the default `2399`, update the Docker port mapping to match (e.g., `2400:2400/udp`).

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

The `site/` directory is pre-built and included in the Docker image, so MkDocs does not need to be installed at runtime.

## MongoDB Replica Set

ollog uses MongoDB change streams to power the live station feed (SSE). Change streams require MongoDB to run as a replica set.

The `docker-compose.yml` starts MongoDB with `--replSet rs0` and auto-initializes the replica set via a healthcheck. The API container waits for MongoDB to report healthy before starting.

If you are connecting to an external MongoDB instance, set `MONGODB_URI` to point at it and ensure that instance is already configured as a replica set. A standalone MongoDB instance will not work.
