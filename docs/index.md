# ollog -- Ham Radio Online Logbook

ollog is a self-hosted, multi-operator ham radio logbook with ADIF import/export, live station feed, and REST API.

## Quick Links

- [Deployment](deployment.md) -- Set up ollog with Docker Compose
- [Getting Started](getting-started.md) -- Your first QSO in 7 steps
- [Admin Guide](admin-guide.md) -- Manage operator accounts
- [API Reference](api-reference.md) -- All 16 endpoints with curl examples
- [ADIF Field Reference](adif-field-reference.md) -- Field format lookup
- [Troubleshooting](troubleshooting.md) -- Common issues and fixes

## Features

- Multi-operator: each operator sees only their own QSOs
- ADIF 3.1.4 import and export
- Live station feed via Server-Sent Events
- REST API with Swagger docs at /docs
- Auto-stamping of OPERATOR and STATION_CALLSIGN
- Duplicate QSO detection with force override
