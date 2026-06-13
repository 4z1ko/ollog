# ollog — Ham Radio Online Logbook

ollog is a self-hosted, multi-operator ham radio logbook with ADIF import/export, live station feed, REST API, ACLog integration, configurable operator fields, and automated database backup.

## Quick Links

- [Getting Started](getting-started/quickstart.md) — Deploy and log your first QSO
- [Operator Guide](operator-guide/index.md) — Logging QSOs, ADIF, ACLog bridges, API tokens, UDP ADIF
- [Admin Guide](admin-guide/index.md) — Deployment, admin container, backup, account management
- [API Reference](api-reference/index.md) — All endpoints with interactive Swagger UI
- [Reference](reference/index.md) — ADIF field reference and environment variables
- [Troubleshooting](troubleshooting/index.md) — Common issues and fixes

## Features

- Multi-operator: each operator writes to and sees only their own QSO collection
- ADIF 3.1.4 import and export
- Configurable Log View columns and custom QSO fields
- Live station feed via Server-Sent Events
- REST API with interactive Swagger docs at [/guide/api-reference/interactive/](api-reference/interactive.md)
- Auto-stamping of OPERATOR and STATION_CALLSIGN
- Duplicate QSO detection with deterministic rowHash protection
- API tokens for programmatic/automation access (v1.7)
- ACLog live bridge ingestion and manual all-record sync via `LIST INCLUDEALL`
- Separate admin container on port 8001 with independent lifecycle (v1.8)
- Database backup CLI with cron scheduling and S3 upload (v1.8)
