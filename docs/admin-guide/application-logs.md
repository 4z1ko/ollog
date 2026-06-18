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

QSO field names keep their ADIF meaning:

- `CALL` is the contacted station's callsign.
- `MYCALL` or station-call fields identify the local station when supplied by a
  remote logging program.
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
