<div align="center">

# ollog

### Self-hosted, ADIF-native, multi-operator ham radio logbook

ollog helps amateur radio operators log QSOs from the browser, REST API, UDP ADIF datagrams, and N3FJP ACLog while keeping each operator's log isolated in its own MongoDB collection.

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135%2B-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-7-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

[Quick Start](#quick-start) | [Features](#features) | [Integrations](#integrations) | [Architecture](#architecture) | [Docs](#documentation) | [Configuration](#configuration)

</div>

---

## What Is ollog?

ollog is a self-hosted online logbook for amateur radio stations, clubs, field days, and multi-operator environments. It stores QSO data using ADIF field names, supports full ADIF import/export, provides a browser UI and REST API, and can ingest contacts from external logging software.

The important bit: each user writes to a dedicated MongoDB collection named `<username>_qsos`, while QSO records still preserve the operator callsign fields expected by ADIF and radio logging workflows.

## New In v3.7: Admin Log Controls

v3.7 adds administrator controls to the **Application Logs** page:

- **Pause/Start live feed:** Pause Recent Logs live row insertion and near-live polling in the current browser tab only. Server-side logging, MongoDB storage, broadcasts, and other browser tabs continue normally.
- **Immediate resume:** Start restores live updates and refreshes the table so missed recent records appear without a full page reload.
- **Clear Log Messages:** Admins can clear stored application log records after a confirmation modal. This clears the application log collection only; QSO records, users, API tokens, backups, log settings, retention configuration, and future logging are preserved.
- **Audit continuity:** When possible, ollog writes a fresh `application_logs_cleared` audit record after clearing logs, including the admin username and deleted record count.

No new environment variables, public REST API changes, or package version changes are required for this milestone. The operational change is limited to MongoDB-backed application log records and the admin Logs UI.

## Feature Highlights

| Area | What ollog provides |
|------|---------------------|
| Multi-operator logging | Admin-managed operator accounts, per-user QSO collections, callsign-based profile stamping, and isolation across browser, API, UDP, stats, import/export, and admin workflows. |
| Browser logbook | QSO entry form, sortable/filterable log view, inline edit/delete, UTC date/time helpers, configurable visible columns, live updates, and light/dark UI. |
| ADIF-native storage | Required ADIF fields are validated, extra ADIF fields are preserved, imports/exports round-trip cleanly, and duplicate review is available during import. |
| REST API | OAuth2/JWT login, API-key support, CRUD endpoints for QSOs, ADIF import/export endpoints, profile endpoints, and Swagger UI at `/docs`. |
| Real-time feed | Server-Sent Events announce new QSOs so operators can see station activity live. |
| UDP ADIF listener | Optional UDP listener accepts raw ADIF datagrams from compatible logging software and routes each QSO by token, OPERATOR field, or fallback config. |
| ACLog bridge | Per-user N3FJP ACLog TCP bridges import saved contacts, request `LIST INCLUDEALL` full-record data, preserve Other fields, and fall back safely to `ENTEREVENT`. |
| Operator profiles | Callsign, station callsign, name/email/QTH, grid square, lat/lon, rig, antenna, TX power, custom QSO fields, API tokens, sound alerts, and ACLog bridges. |
| Admin tools | Operator management, enable/disable, password reset, full database backup/restore, admin clear-log controls, and MongoDB-backed application log viewing/configuration. |
| Documentation | Built-in MkDocs site served at `/guide`, including deployment, operator, admin, API, ADIF, environment, and troubleshooting guides. |

## Quick Start

### 1. Clone

```bash
git clone https://github.com/4z1ko/ollog.git
cd ollog
```

### 2. Create `.env`

```bash
SECRET_KEY=change-me-to-a-long-random-string
API_TOKEN_SECRET=change-me-to-another-long-random-string

# First-start admin bootstrap
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme123
ADMIN_CALLSIGN=N0CALL
```

### 3. Start the stack

```bash
docker compose up -d
```

The default compose stack starts:

| Service | URL / port | Purpose |
|---------|------------|---------|
| Operator app | `http://localhost:8000` | Browser logbook, REST API, built-in docs |
| MongoDB | `localhost:27017` | Replica-set MongoDB for app data and change streams |
| UDP listener | `2399/udp` | Optional ADIF datagram ingestion when enabled |
| Admin app | `http://localhost:8001` | Optional standalone admin console via Compose profile |

### 4. Verify

```bash
curl http://localhost:8000/auth/me
```

Expected result: `401 Unauthorized`. That means the API is alive and waiting for authentication.

Open:

- App: `http://localhost:8000`
- Guide: `http://localhost:8000/guide`
- API docs: `http://localhost:8000/docs`

## Integrations

### ADIF Import And Export

- Import `.adi` / `.adif` files through the browser or API.
- Export each operator's active logbook as ADIF.
- Preserve additional ADIF fields beyond the core schema.
- Review duplicates during import before accepting or skipping records.

### REST API

Use JWT bearer tokens or per-operator API keys.

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=changeme123" | jq -r .access_token)

curl -X POST http://localhost:8000/api/qsos/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "CALL": "W1AW",
    "BAND": "20m",
    "MODE": "SSB",
    "QSO_DATE": "20260609",
    "TIME_ON": "123000",
    "FREQ": "14.250",
    "RST_SENT": "59",
    "RST_RCVD": "59"
  }'
```

### UDP ADIF

Enable the UDP listener in `.env`:

```bash
UDP_ENABLED=true
UDP_BIND_HOST=0.0.0.0
UDP_PORT=2399
```

Then send an ADIF datagram:

```bash
printf '<CALL:4>W1AW<BAND:3>20M<MODE:3>SSB<QSO_DATE:8>20260609<TIME_ON:6>123000<OPERATOR:6>N0CALL<EOR>' \
  | nc -u -w1 localhost 2399
```

If your datagram includes `APP_OLLOG_TOKEN`, ollog can route it by API token. If it includes `OPERATOR`, ollog routes by callsign. `UDP_OPERATOR` can be used as a fallback for datagrams that omit operator identity.

### N3FJP ACLog Bridge

Operators can configure ACLog bridges from Profile Settings. ollog connects to ACLog's TCP API, listens for saved-QSO events, requests full-record data with `LIST INCLUDEALL`, and imports the enriched QSO when the response matches the pending event.

ACLog Other fields are preserved as `OTHER_1` through `OTHER_8` unless the operator maps them to custom QSO fields.

## Architecture

```text
Browser UI / HTMX        REST API clients          UDP ADIF clients        ACLog TCP API
       |                       |                         |                      |
       v                       v                         v                      v
  FastAPI operator app  <---- auth / routing / ingest services ---->  background bridges
       |
       v
  MongoDB replica set
       |
       +-- users, tokens, profiles, backups metadata
       +-- <username>_qsos collections for per-operator QSO logs
       +-- change-stream/app broadcasts for live station feed
```

### Technology Stack

| Layer | Tools |
|-------|-------|
| Backend | Python 3.12, FastAPI, Pydantic, Beanie, PyMongo |
| Database | MongoDB 7 replica set |
| Frontend | Jinja templates, HTMX, Tailwind CSS |
| Auth | JWT browser/API auth, HMAC-SHA256 API tokens, Argon2 password hashing |
| Docs | MkDocs Material, Swagger/OpenAPI |
| Operations | Docker Compose, compressed EJSON backups, optional S3 upload |

## Data Model And Isolation

ollog stores QSO documents with ADIF-native field names such as `CALL`, `BAND`, `MODE`, `QSO_DATE`, `TIME_ON`, `RST_SENT`, and `RST_RCVD`.

Isolation rules:

- Every user gets a dedicated QSO collection: `<username>_qsos`.
- Runtime queries derive the collection from the authenticated or resolved `User.username`.
- `_operator` remains the radio callsign for ADIF compatibility and display.
- REST, browser, ADIF, UDP, ACLog, stats, clear-log, and backup/restore workflows are collection-aware.
- Legacy shared-collection data can be migrated idempotently into per-user collections.

## Configuration

Core variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | yes | none | JWT signing key. Changing it invalidates sessions. |
| `API_TOKEN_SECRET` | yes | none | HMAC key for API token hashing. Changing it invalidates API tokens. |
| `MONGODB_URI` | no | compose-provided | MongoDB connection string. Must point to a replica set for live feed support. |
| `MONGODB_DB` | no | `ollog` | Database name. |
| `JWT_EXPIRE_MINUTES` | no | `480` | Browser/API token lifetime in minutes. |
| `ADMIN_USERNAME` | first start only | none | Bootstrap admin username. |
| `ADMIN_PASSWORD` | first start only | none | Bootstrap admin password. |
| `ADMIN_CALLSIGN` | first start only | none | Bootstrap admin callsign. |

Optional integrations:

| Variable | Default | Purpose |
|----------|---------|---------|
| `UDP_ENABLED` | `false` | Start the UDP ADIF listener. |
| `UDP_PORT` | `2399` | UDP listener port in Docker Compose. |
| `UDP_BIND_HOST` | `127.0.0.1` | Use `0.0.0.0` inside Docker for host/LAN datagrams. |
| `UDP_OPERATOR` | none | Fallback operator callsign for UDP datagrams without identity. |
| `ACLOG_ENABLED` | `true` | Start the global ACLog bridge manager. |
| `ACLOG_RECONNECT_SECONDS` | `5` | Delay before reconnecting to dropped ACLog TCP sessions. |
| `ACLOG_SCAN_SECONDS` | `10` | How often bridge settings are reloaded from profiles. |
| `BACKUP_DIR` | `/app/backups` | Local backup directory. |
| `BACKUP_SCHEDULE` | none | Optional cron expression for scheduled backups. |
| `BACKUP_S3_BUCKET` | none | Optional S3 destination for backup uploads. |

See the full reference in [`docs/reference/environment-variables.md`](docs/reference/environment-variables.md).

## Admin Console

The optional admin console is a separate FastAPI app on port `8001`:

```bash
docker compose --profile admin up -d
```

Use it to manage operators, reset passwords, run backups, restore backups, clear an operator's log with admin password confirmation, and inspect application logs.

### Application Logs

The admin **Logs** page stores and displays internal application log records from MongoDB. Admins can:

- Configure the minimum stored log level and retention period.
- Filter logs by level, source, text, and date/time range.
- Pause or restart live Recent Logs updates in the current browser tab.
- Clear stored application log messages after confirmation.

Clearing application log messages does not delete QSO records, users, API tokens, backups, or log settings. It removes records from the application logs collection and then attempts to write a fresh audit message.

## Backup And Restore

ollog includes pure-Python backup/restore tooling:

- Compressed EJSON database dumps.
- Browser-triggered admin backup downloads.
- Optional scheduled backups.
- Optional S3 upload through the standard AWS credential chain.
- Restore flow with integrity validation, password confirmation, and automatic pre-restore backup.

## Development

Install dependencies with your Python environment manager of choice. The project is configured for Python 3.12+ and lists development dependencies in `pyproject.toml`.

Common commands:

```bash
# Run tests when pytest is installed
python -m pytest

# Build frontend CSS
npm run build

# Build documentation locally
python -m mkdocs build --strict
```

The Docker image runs:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Documentation

When the app is running, open `http://localhost:8000/guide`.

Repo docs:

- [`docs/getting-started/quickstart.md`](docs/getting-started/quickstart.md)
- [`docs/operator-guide/index.md`](docs/operator-guide/index.md)
- [`docs/admin-guide/index.md`](docs/admin-guide/index.md)
- [`docs/api-reference/index.md`](docs/api-reference/index.md)
- [`docs/reference/adif-field-reference.md`](docs/reference/adif-field-reference.md)
- [`docs/reference/environment-variables.md`](docs/reference/environment-variables.md)
- [`docs/troubleshooting/index.md`](docs/troubleshooting/index.md)

## Project Status

Current shipped milestone: **v3.7 Admin Log Controls**.

Recent milestones:

| Version | Focus |
|---------|-------|
| v3.7 | Admin Recent Logs Pause/Start and Clear Log Messages controls. |
| v3.6 | MongoDB-backed internal application logging, admin viewer, live updates, and instrumentation. |
| v3.5 | Shared remote ACLog operator identity routing. |
| v3.4 | Responsive favicon integration. |
| v3.3 | Manual ACLog bridge synchronization from Profile Settings. |
| v3.2 | ACLog full-record import through `LIST INCLUDEALL`. |
| v3.1 | Per-user MongoDB QSO collections. |
| v3.0 | Configurable QSO Log View columns and custom fields. |

See [`.planning/MILESTONES.md`](.planning/MILESTONES.md) for the full internal milestone history.

## License

MIT License. See [`LICENSE`](LICENSE).
