# Application Logs

ollog stores internal application logs in MongoDB so administrators can inspect
QSO ingestion, bridge connectivity, startup, shutdown, and admin actions from
the admin UI.

Open the admin container and go to **Logs**:

```bash
docker compose --profile admin up -d admin
```

The Logs page shows recent records, updates live while the page is open, and
supports filtering by level, source, text, and date/time range.

Use **Previous** and **Next** at the bottom of the table to page through older
records while keeping the active filters. Structured metadata and error details
are collapsed by default and expand as formatted JSON for easier inspection.

## Log Levels

The default minimum level is **Info**. When the minimum level is set to
**Warn**, only Warn, Error, and Fatal records are stored and displayed.

| Level | Meaning |
|-------|---------|
| Trace | Deep execution tracing for narrow debugging. |
| Debug | Diagnostic information useful to developers and administrators. |
| Info | Routine operational events, such as startup, listener start, bridge connection, or QSO insert. |
| Warn | Odd or degraded behavior that recovered automatically, such as retrying a bridge connection or rejecting malformed optional input. |
| Error | A specific operation failed and likely needs administrator attention. |
| Fatal | Reserved for unsafe states that force shutdown or prevent safe continuation. |

## Stored Fields

Each application log record includes a timestamp, level, message, source module,
event type, transport, optional correlation ID, optional QSO ID, optional bridge
or remote logging software names, structured metadata, and error details when
available.

## Logged Flows

The exact records depend on the active minimum log level. Representative event
types include:

| Flow | Representative events |
|------|-----------------------|
| Service and database lifecycle | `service_startup_started`, `service_startup_completed`, `service_shutdown_started`, `mongodb_connected`, `mongodb_closing` |
| UDP listener lifecycle and ingest | `udp_listener_started`, `udp_listener_bound`, `udp_datagram_received`, `udp_parse_rejected`, `udp_unknown_operator`, `udp_no_user_resolved`, `udp_transport_error` |
| HTTP/API QSO writes | `qso_http_received`, `qso_inserted`, `qso_duplicate`, `qso_validation_rejected`, `qso_update_failed`, `qso_updated`, `qso_deleted` |
| ADIF import | `qso_import_started`, `qso_import_completed`, `qso_import_request_completed`, `qso_import_failed` |
| ACLog live bridge | `bridge_connecting`, `bridge_connected`, `bridge_disconnected`, `bridge_reconnect_scheduled`, `bridge_qso_skipped`, `bridge_qso_processed` |
| ACLog manual sync | `bridge_sync_started`, `bridge_sync_records_received`, `bridge_sync_qso_processed`, `bridge_sync_qso_skipped`, `bridge_sync_failed`, `bridge_sync_completed` |
| Authentication and token actions | `operator_login_succeeded`, `operator_login_failed`, `oauth_login_succeeded`, `oauth_login_failed`, `api_token_created`, `api_token_revoked`, `operator_api_token_created`, `operator_api_token_revoked` |
| Admin actions and settings | `admin_login_succeeded`, `admin_login_failed`, `admin_user_created`, `admin_user_updated`, `admin_user_deleted`, `log_settings_updated`, backup and restore events |

QSO field names keep their ADIF meaning:

- `CALL` is the contacted station's callsign.
- `MYCALL`, ACLog setup **Call**, or station-call fields identify the local
  station when supplied by a remote logging program.
- `OPERATOR` identifies the operator value.

The application logger does not use contacted-station `CALL` as the source
station identifier.

## Sensitive Data

The logger masks sensitive metadata keys such as passwords, tokens, API keys,
authorization headers, secrets, credentials, and connection strings. MongoDB
connection strings are also masked if they appear inside an error detail.

Avoid putting secrets in log messages. Prefer structured metadata with safe
operational identifiers such as username, callsign, bridge name, transport, and
QSO ID.

## Retention

Logs expire through a MongoDB TTL index. The default retention period is 30 days
and can be changed from the Logs page. Retention applies to newly written log
records.
