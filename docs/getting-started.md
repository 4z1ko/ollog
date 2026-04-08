# Getting Started

This walkthrough takes you through the complete ollog workflow: from first login through live station feed.

**Prerequisites:** A running ollog instance and an operator account. See the [Deployment guide](deployment.md) for setup instructions. Your administrator creates your account and sets your OPERATOR callsign.

---

## Step 1: Log In

**Browser:** Navigate to `http://localhost:8000`, enter your username and password.

**API:** Use the OAuth2 token endpoint to obtain a Bearer token:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=youruser&password=yourpass" | jq -r .access_token)
```

The token is valid for `JWT_EXPIRE_MINUTES` (default 60 minutes). For browser sessions, a cookie is set automatically and you do not need to manage tokens manually.

---

## Step 2: Set Up Your Profile

Before logging QSOs, understand the two callsign fields in ollog:

- **OPERATOR** — your personal callsign. This is set by the administrator at account creation and auto-stamped on every QSO you log. You cannot change it via the API.
- **STATION_CALLSIGN** — the station you are operating *from* (for example, a club callsign or special event call such as `W1AW`). This is optional and you set it yourself.

Update your profile via the API:

```bash
curl -X PATCH http://localhost:8000/api/profile/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"station_callsign": "W1AW", "my_gridsquare": "FN31pr", "name": "Your Name"}'
```

If `station_callsign` is set, it is auto-stamped on new QSOs alongside your OPERATOR callsign. You can update or clear it at any time by patching `station_callsign` to `null` or an empty string.

Other editable profile fields include: `name`, `email`, `qth`, `state`, `country`, `my_rig`, `my_antenna`, and `tx_pwr`.

---

## Step 3: Log a QSO via the Web UI

1. Click **Log QSO** in the navigation bar.
2. Fill in the form:
   - **Callsign** — the station you worked (e.g., `DL1ABC`)
   - **Band** — e.g., `20m`
   - **Mode** — e.g., `SSB`
   - **RST Sent / Received** — signal reports
3. Date and time default to now (UTC). Adjust if logging a past QSO.
4. Click **Submit**.

Your OPERATOR callsign is stamped automatically — you do not enter it.

---

## Step 4: Log a QSO via the API

```bash
curl -X POST http://localhost:8000/api/qsos/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "CALL": "DL1ABC",
    "BAND": "20m",
    "MODE": "SSB",
    "QSO_DATE": "20240415",
    "TIME_ON": "1430",
    "RST_SENT": "59",
    "RST_RCVD": "59"
  }'
```

Field notes:
- `QSO_DATE` format is `YYYYMMDD` (UTC).
- `TIME_ON` format is `HHMM` or `HHMMSS` (UTC).
- `OPERATOR` is auto-stamped from your JWT — do not include it in the request body.
- Returns `201 Created` with the full QSO object on success.

**Duplicate detection:** If a QSO with the same `CALL`, `BAND`, `MODE`, and operator already exists within a ±2 minute window, you receive `409 Conflict`. To force creation anyway, append `?force=true` to the URL:

```bash
curl -X POST "http://localhost:8000/api/qsos/?force=true" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"CALL": "DL1ABC", "BAND": "20m", "MODE": "SSB", "QSO_DATE": "20240415", "TIME_ON": "1430"}'
```

---

## Step 5: Import QSOs from an ADIF File

If you have an existing logbook in ADIF format, import it with a single command:

```bash
curl -X POST http://localhost:8000/api/adif/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@mylog.adi"
```

The response is a JSON report showing:
- `accepted` — records successfully created
- `duplicates` — records that matched existing QSOs (skipped)
- `errors` — records that could not be parsed or were missing required fields

**Important:** ADIF import does *not* auto-stamp `OPERATOR` or `STATION_CALLSIGN`. Values are preserved exactly as they appear in the file, which is correct for historical records. Duplicate detection uses the same ±2 minute window as manual entry.

The maximum file size is 10 MB.

---

## Step 6: Export Your Log as ADIF

```bash
curl http://localhost:8000/api/adif/export \
  -H "Authorization: Bearer $TOKEN" \
  -o mylog.adi
```

Exports only *your* QSOs (operator-isolated — you cannot see other operators' logs). Output is ADIF 3.1.4 format, compatible with standard logging software. Soft-deleted QSOs are excluded.

---

## Step 7: Watch the Station Feed

The station feed is a live **Server-Sent Events (SSE)** stream. It shows QSOs as they are logged by *any* operator on the instance, in real time.

**Browser:** Navigate to the log page — live updates appear automatically. No configuration required.

**API / curl:** The SSE endpoint at `/feed/station` requires **cookie authentication**, not a Bearer token. This is because the browser's native `EventSource` API cannot send custom headers, so the JWT is read from an HttpOnly cookie set during browser login. In the browser this works transparently. From curl, pass the session cookie:

```bash
curl -N --cookie "session=<your-session-cookie>" http://localhost:8000/feed/station
```

The session cookie is set when you log in via the browser. This endpoint is intentionally excluded from the Swagger UI because it cannot be exercised with Bearer tokens.

---

## Step 8: Send QSOs via UDP

ollog includes a UDP listener that accepts raw ADIF text datagrams. Each arriving QSO is logged under the **`UDP_OPERATOR`** callsign configured in your deployment environment — no authentication token is required by the sender.

Before using this feature, confirm with your administrator that `UDP_ENABLED=true` and `UDP_OPERATOR` are set in the deployment environment. The listener binds to `UDP_BIND_HOST` on `UDP_PORT` (default `2399`). See the [Deployment guide](deployment.md) for configuration details.

**Required ADIF fields:** Every datagram must contain `CALL`, `QSO_DATE`, `TIME_ON`, `BAND`, and `MODE`. Datagrams missing any of these fields are discarded.

### Testing with nc

The fastest way to verify your UDP listener is working is to send a minimal ADIF datagram using `nc`:

```bash
echo -n '<CALL:6>DL1ABC<BAND:3>20m<MODE:3>FT8<QSO_DATE:8>20240415<TIME_ON:4>1430<EOR>' \
  | nc -u -w1 127.0.0.1 2399
```

Replace `127.0.0.1` with the hostname of your ollog instance if it is remote. The `-u` flag selects UDP (not TCP) and `-w1` causes nc to exit after 1 second (required because UDP is connectionless). On Linux with GNU netcat, use `-q1` instead of `-w1`.

After sending, check your log — a new QSO from `DL1ABC` should appear under the `UDP_OPERATOR` callsign.

**Note on ADIF field format:** Each field tag is `<FIELDNAME:N>value` where `N` is the byte count of `value`. For ASCII callsigns, bands, modes, and dates, byte count equals character count. Getting the count wrong causes the parser to read truncated values.

### Log4OM

Log4OM 2 can broadcast QSOs as raw ADIF text over UDP, which is directly compatible with ollog's UDP listener.

1. In Log4OM, go to **Setup > Connections**.
2. In the right panel (Outbound/Broadcast connections), add a new entry:
   - **Port:** `2399`
   - **IP:** `127.0.0.1` (or the IP address of the machine running ollog)
   - **Name:** `ollog` (or any label you prefer)
3. Enable the **Broadcast** checkbox and confirm ADIF is selected as the message type.
4. Click the green **+** button to save the connection.

From this point, each QSO you save in Log4OM is broadcast to ollog over UDP. The exact field labels in Log4OM's UI vary by version — consult the Log4OM documentation if the steps above do not match your installed version.

### WSJT-X

WSJT-X's UDP output uses a **binary-framed protocol**, not raw ADIF text. It is not directly compatible with ollog's UDP listener.

For reference, the UDP Server setting is located at **File > Settings (F2) > Reporting > UDP Server**. The default WSJT-X port is `2237`. Do not point this at ollog's port (`2399`) — the binary frames will not be parsed correctly.

**To get WSJT-X QSOs into ollog:** Use the ADIF file import path from Step 5. WSJT-X writes a running log to `WSJTX_LOG.ADI` in its data directory. Periodically import this file:

```bash
curl -X POST http://localhost:8000/api/adif/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/WSJTX_LOG.ADI"
```

### N1MM+ (N1MM Logger Plus)

N1MM+ broadcasts contact data as **XML**, not ADIF text. It is not directly compatible with ollog's UDP listener.

For reference, the broadcast settings are at **Config > Config Ports, Mode Control, Audio, Other > Broadcast Data tab**. The default N1MM+ broadcast port is `12060`. Do not point this at ollog's port — the XML format will not be parsed as ADIF.

**To get N1MM+ QSOs into ollog:** Export to ADIF from N1MM+ via **File > Export to ADIF**, then import using the Step 5 file import command:

```bash
curl -X POST http://localhost:8000/api/adif/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/your-log.adi"
```

---

## Next Steps

- [API Reference](api-reference.md) — full endpoint documentation with all parameters and response schemas
- [ADIF Field Reference](adif-field-reference.md) — field format details and supported ADIF fields
- [Admin Guide](admin-guide.md) — managing operator accounts, setting callsigns, enabling/disabling users
- [Troubleshooting](troubleshooting.md) — common issues and fixes
