# Quickstart

This guide covers deploying ollog with Docker Compose and verifying that everything is working.

## Prerequisites

- Docker and Docker Compose v2 installed
- A machine or VM with port 8000 available
- Git

## Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/ollog.git
cd ollog
```

## Step 2: Create a .env File

Create a `.env` file in the project root with the required variables:

```
SECRET_KEY=change-me-to-a-long-random-string
API_TOKEN_SECRET=change-me-to-another-long-random-string
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123
ADMIN_CALLSIGN=N0CALL
```

See [Environment Variables](../reference/environment-variables.md) for a complete list of available variables.

## Step 3: Start the Stack

```bash
docker compose up -d
```

This starts the API (port 8000) and MongoDB containers. MongoDB is automatically configured as a replica set, which is required for the live station feed.

## Step 4: Verify the API is Up

```bash
curl http://localhost:8000/auth/me
```

Expected: `401 Unauthorized` — this confirms the API is responding.

## Step 5: Open the Docs

Open the documentation site in your browser: `http://localhost:8000/guide`

## Step 6: Log In

**Browser:** Navigate to `http://localhost:8000`, enter your username and password.

**API:** Use the OAuth2 token endpoint to obtain a Bearer token:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=youruser&password=yourpass" | jq -r .access_token)
```

The token is valid for `JWT_EXPIRE_MINUTES` (default 480 minutes / 8 hours). For browser sessions, a cookie is set automatically and you do not need to manage tokens manually.

## Bootstrap Admin Account

On first startup, if `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ADMIN_CALLSIGN` are all set, the app creates an admin account automatically. This only happens once — if an account with that username already exists, the variables are ignored.

After the first startup you can remove the `ADMIN_*` variables from `.env`. The account persists in the database.

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

## Next Steps

- [First QSO](first-qso.md) — Log your first contact
- [Operator Guide](../operator-guide/index.md) — All operator features
- [Admin Guide](../admin-guide/index.md) — Managing operators, backup, admin container
