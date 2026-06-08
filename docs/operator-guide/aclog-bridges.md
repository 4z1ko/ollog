# ACLog Bridges

ollog can collect live QSOs from N3FJP ACLog through ACLog's TCP API. Each
operator can configure one or more ACLog bridge locations from their own profile
page.

## How It Works

When ACLog saves a contact, its API emits an `ENTEREVENT` message. ollog keeps a
background TCP connection open to each enabled bridge, then asks ACLog for the
latest full record with `LIST INCLUDEALL`. If the full-record response matches
the saved event, ollog imports the enriched record for the operator who
configured the bridge. If ACLog does not return a matching full record, ollog
falls back to the original `ENTEREVENT` data.

Imported ACLog QSOs use the same QSO rules as other live ingestion paths:

- `CALL`, `QSO_DATE`, `TIME_ON`, `BAND`, and `MODE` are required.
- Numeric ACLog bands such as `20` are stored as ADIF-style bands such as `20M`.
- `FREQ`, `RST_SENT`, `RST_RCVD`, and other non-empty ACLog fields are imported
  when ACLog provides them.
- ACLog Other fields are mapped to the operator's configured Custom QSO Fields
  when configured; otherwise they remain preserved as `OTHER_1` through
  `OTHER_8`.
- Duplicate detection uses the same per-operator ±2 minute window.
- Profile stamping still applies, including `OPERATOR`, `STATION_CALLSIGN`,
  `MY_GRIDSQUARE`, `MY_RIG`, `MY_ANTENNA`, and `TX_PWR` when those profile fields
  are set.

To capture frequency, reports, and Other field values even when full-record
enrichment is unavailable, ollog asks ACLog for all text-box updates after
connecting and keeps the latest frequency, sent report, received report, and
Other slot values in memory until the next `ENTEREVENT` arrives.

## Enable the ACLog API

In ACLog:

1. Open **Settings**.
2. Open **Application Program Interface**.
3. Enable the API server.
4. Confirm the TCP port. ACLog commonly uses port `1100`.
5. Allow the connection through Windows Firewall if ollog runs on another machine.

If ollog runs in Docker on a different computer, use the Windows PC's LAN IP
address as the bridge host.

## Add a Bridge in ollog

1. Sign in to ollog.
2. Open **Profile**.
3. In **ACLog Bridges**, enter:
   - **Name**: any label, such as `Shack PC`
   - **Host**: the ACLog computer hostname or IP address
   - **Port**: the ACLog API TCP port, usually `1100`
   - **Enabled**: checked when ollog should connect
4. Click **Save Bridges**.

You can add more than one bridge. This is useful when the same operator logs from
multiple ACLog installations, such as a shack PC and a laptop.

## Connection Behavior

ollog scans configured bridges periodically and starts one background TCP client
per enabled bridge. If ACLog closes or restarts, ollog retries automatically.

The scan and retry timing are controlled by environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ACLOG_ENABLED` | `true` | Starts or disables the ACLog bridge manager globally |
| `ACLOG_SCAN_SECONDS` | `10` | How often ollog reloads per-user bridge settings |
| `ACLOG_RECONNECT_SECONDS` | `5` | Delay before reconnecting a dropped ACLog TCP connection |

Per-user bridge changes take effect on the next scan interval. Restarting ollog
is not required after editing bridge rows.

## Troubleshooting

If QSOs do not appear:

1. Confirm ACLog's API is enabled and listening on the configured port.
2. Confirm the bridge host is reachable from the machine or container running
   ollog.
3. Confirm Windows Firewall allows inbound connections to the ACLog API port.
4. Check ollog logs for `ACLog bridge connected`, `ACLog bridge error`, or
   `ACLog bridge ... disposition=` messages.
5. Confirm the contact saved in ACLog includes `CALL`, `BAND`, `MODE`,
   `QSO_DATE`, and `TIME_ON`.
6. If frequency, RST, or Other field values are missing, confirm ACLog is sending
   full-record responses for `LIST INCLUDEALL` or field update notifications.
   Restarting the bridge connection usually refreshes this state.

If ollog logs a QSO as `duplicate`, the contact matched an existing QSO for the
same operator, call, band, mode, and time window.
