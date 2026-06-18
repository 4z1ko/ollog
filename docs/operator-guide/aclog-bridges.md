# ACLog Bridges

ollog can collect live QSOs from N3FJP ACLog through ACLog's TCP API. Each
operator can configure one or more ACLog bridge locations from their own profile
page.

## How It Works

When ACLog saves a contact, its API emits an `ENTEREVENT` message. ollog keeps a
background TCP connection open to each enabled bridge, then asks ACLog for the
latest full record with `LIST INCLUDEALL`. If the full-record response matches
the saved event, ollog imports the enriched record for the operator who
configured the bridge. ollog only imports the record when the full ACLog record
contains a matching station/operator identity. If ACLog does not return a
matching full record, or if the full record is missing or has a different
station/operator identity, ollog skips the event instead of falling back to the original
`ENTEREVENT` data.

Imported ACLog QSOs use the same QSO rules as other live ingestion paths:

- `CALL`, `QSO_DATE`, `TIME_ON`, `BAND`, and `MODE` are required.
- Numeric ACLog bands such as `20` are stored as ADIF-style bands such as `20M`.
- `FREQ`, `RST_SENT`, `RST_RCVD`, and other non-empty ACLog fields are imported
  when ACLog provides them.
- ACLog Other fields are mapped to the operator's configured Custom QSO Fields
  when configured; otherwise they remain preserved as `OTHER_1` through
  `OTHER_8`.
- ACLog identity matching uses local station identity first, then operator
  identity. `MYCALL`, when ACLog returns it, or ACLog's setup **Call** value from
  `GETUSERSETTINGS` can match your ollog profile `station_callsign` or account
  callsign. If no station identity is available, ollog falls back to the
  record-level `OPERATOR` field matching your ollog operator callsign.
- The QSO `CALL` field is never used for routing. In QSO records, `CALL` is the
  contacted station.
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

## Shared ACLog Computers

Multiple ollog operators can point saved bridges at the same remote ACLog
computer. To keep those operators isolated, ollog treats ACLog station/operator
identity as the import gate:

- If ACLog returns `MYCALL`, or if ollog can read ACLog's setup **Call** value
  with `GETUSERSETTINGS`, that value is compared to your profile
  `station_callsign` and account callsign first.
- If no station identity is available, `OPERATOR` is compared to your ollog
  callsign as the fallback.
- If the available station/operator identity is missing, blank, or belongs to a
  different callsign, the QSO is skipped and counted.
- `CALL` in a QSO record means the contacted station. It is deliberately ignored
  for routing so a QSO with `CALL=W1AW` is not mistaken for a QSO from station
  `W1AW`.

Before sharing one ACLog API endpoint between operators, confirm that either the
ACLog setup **Call** value maps to the intended ollog profile station callsign,
or that saved ACLog records include an `OPERATOR` value for each contact. N3FJP
documents that `GETUSERSETTINGS` returns setup values including `CALL` and
`OPERATOR`, and that `LIST INCLUDEALL` returns populated record fields, but QSO
field availability can still depend on how the ACLog database and records are
configured.

## Manual Sync

Saved bridge rows also show a **Sync** button. Pressing Sync asks that ACLog API
location for all logged records with `<CMD><LIST><INCLUDEALL></CMD>`, then
imports only QSOs that are missing from the signed-in operator's ollog
collection and whose ACLog `OPERATOR` identity matches the signed-in operator.
When ACLog's setup **Call** value is available, manual sync uses that station
call first and falls back to `OPERATOR` only when station identity is unavailable.

Manual sync is additive only. It does not update, merge, or delete existing local
QSOs. If you run Sync again against the same ACLog database, records already in
ollog are reported as already present instead of being inserted a second time.
The result appears inline on the Profile page with counts for missing QSOs
imported, already-present records, missing-operator skips, unmatched-operator
skips, and any errors.

The sync report includes:

| Report line | Meaning |
|-------------|---------|
| Remote records received | Number of QSO records returned by ACLog |
| Missing QSOs imported | Records inserted into your ollog collection |
| Already present | Records skipped because ollog already had them |
| Missing operator | Records skipped because ACLog did not return a record-level operator identity |
| Unmatched operator | Records skipped because ACLog returned a different operator identity |
| Errors | Records rejected because required fields were missing or invalid |

If ACLog is offline, the host/port is wrong, or the API does not respond before
the fixed timeout, ollog shows `ACLog sync failed` with a reminder to confirm
that ACLog is running and the API port is reachable. The error stays on the
Profile page; it does not navigate away or clear your bridge settings.

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
   `ACLog bridge ... identity_field=... disposition=` messages.
5. Confirm the contact saved in ACLog includes `CALL`, `BAND`, `MODE`,
   `QSO_DATE`, and `TIME_ON`.
6. Confirm ACLog's setup **Call** value matches your ollog profile
   `station_callsign` or account callsign, or confirm the contact saved in ACLog
   includes `OPERATOR` matching your ollog callsign. Missing or unmatched
   station/operator values are skipped by design.
7. If frequency, RST, or Other field values are missing, confirm ACLog is sending
   full-record responses for `LIST INCLUDEALL` or field update notifications.
   Restarting the bridge connection usually refreshes this state.

If ollog logs a QSO as `duplicate`, the contact matched an existing QSO for the
same operator, call, band, mode, and time window.
