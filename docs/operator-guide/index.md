# Operator Guide

This section is for licensed amateur radio operators using ollog to log QSOs. It covers all day-to-day features: logging contacts, configuring the Log View, importing and exporting ADIF files, syncing with ACLog, managing API tokens for automation, configuring your station profile, and sending QSOs over UDP.

## In This Section

- [Logging QSOs](logging-qsos.md) — Log contacts via the web UI or REST API; covers UTC date/time, configurable columns, duplicate detection, and pagination
- [ADIF Import/Export](adif-import-export.md) — Bulk import from existing logbooks and export your log as ADIF 3.1.4
- [API Tokens](api-tokens.md) — Create long-lived tokens for scripts, automation, and UDP per-datagram authentication
- [Profile](profile.md) — Set your station callsign, gridsquare, custom QSO fields, ACLog bridges, and sound preferences
- [ACLog Bridges](aclog-bridges.md) — Import live ACLog saves and manually sync missing QSOs from a configured ACLog API bridge
- [UDP ADIF](udp-adif.md) — Send QSOs from Log4OM and other software via UDP ADIF datagrams

## Data Isolation

Each operator's log is stored in a dedicated MongoDB collection named from the
login username. Browser views, REST API calls, ADIF import/export, UDP ingest,
ACLog live ingest, and ACLog manual sync all route to the signed-in operator's
own collection.

## Authentication Quick Reference

| Method | Header / Field | Use Case |
|--------|---------------|----------|
| JWT Bearer | `Authorization: Bearer <token>` | Browser sessions, interactive API use |
| X-API-Key | `X-API-Key: <token>` | Scripts, automation, long-lived access |
| APP_OLLOG_TOKEN ADIF field | UDP datagram field | Per-datagram UDP authentication |

See [API Reference](../api-reference/index.md) for a complete endpoint listing.
