# Operator Guide

This section is for licensed amateur radio operators using ollog to log QSOs. It covers all day-to-day features: logging contacts, importing and exporting ADIF files, managing API tokens for automation, configuring your station profile, and sending QSOs over UDP.

## In This Section

- [Logging QSOs](logging-qsos.md) — Log contacts via the web UI or REST API; covers all fields, duplicate detection, and pagination
- [ADIF Import/Export](adif-import-export.md) — Bulk import from existing logbooks and export your log as ADIF 3.1.4
- [API Tokens](api-tokens.md) — Create long-lived tokens for scripts, automation, and UDP per-datagram authentication
- [Profile](profile.md) — Set your station callsign, gridsquare, and other fields; understand auto-stamping behavior
- [UDP ADIF](udp-adif.md) — Send QSOs from Log4OM and other software via UDP ADIF datagrams

## Authentication Quick Reference

| Method | Header / Field | Use Case |
|--------|---------------|----------|
| JWT Bearer | `Authorization: Bearer <token>` | Browser sessions, interactive API use |
| X-API-Key | `X-API-Key: <token>` | Scripts, automation, long-lived access |
| APP_OLLOG_TOKEN ADIF field | UDP datagram field | Per-datagram UDP authentication |

See [API Reference](../api-reference/index.md) for a complete endpoint listing.
