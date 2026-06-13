# Logging QSOs

ollog supports logging QSOs via the web UI, the REST API, ADIF file import, UDP
datagrams, and ACLog bridges. This page covers the web UI, Log View, and REST
API methods.

## Web UI

1. Log in at `http://localhost:8000`
2. Click **Log QSO** in the navigation bar
3. Fill in the form fields:
   - **Callsign** — the station you worked (required)
   - **Band** — e.g., `20m`, `40m`, `2m` (required)
   - **Mode** — e.g., `SSB`, `CW`, `FT8` (required)
   - **RST Sent / Received** — signal reports (optional)
   - **Date / Time** — UTC date and time; lock the clock for live logging or unlock it for past QSOs
   - Any enabled **Custom QSO Fields** from your profile
4. Click **Submit**

Your OPERATOR callsign and configured profile fields are auto-stamped — you do
not enter them manually.

## Log View

The Log View shows your own QSOs only. Use the filter controls to narrow by call,
band, mode, or date range. The table supports pagination and sorting by the
current sortable fields.

Use the column chooser to select which fields are visible. The defaults are kept
for a compact logbook view, and additional ADIF/custom fields can be added as
columns when you need them. Your browser remembers the selected columns locally.

## REST API

### POST /api/qsos/

Create a new QSO record.

- **Auth:** Bearer token or X-API-Key
- **Request:** JSON body. Required fields: `CALL`, `QSO_DATE` (YYYYMMDD), `TIME_ON` (HHMM or HHMMSS), `BAND`, `MODE`. Optional: `FREQ`, `RST_SENT`, `RST_RCVD`, and any other standard ADIF fields.
- **Response:** 201 with QSO object including generated `id` and auto-stamped `_operator`
- **Errors:**
  - 409 if a duplicate is detected (same CALL+BAND+MODE+operator within +/-2 min, or an exact rowHash duplicate)
  - 422 if required fields are missing or validation fails

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

### GET /api/qsos/

List QSOs with pagination and optional filters.

- **Auth:** Bearer token or X-API-Key
- **Query params:** `page` (default 1), `page_size` (default 50, max 500), `call`, `band`, `mode`, `date_from` (YYYYMMDD), `date_to` (YYYYMMDD), `sort` (default `-qso_date_utc`)
- **Response:** 200 with `{"items": [...], "total": N, "page": N, "page_size": N}`

```bash
curl "http://localhost:8000/api/qsos/?page=1&page_size=50&band=20m" \
  -H "Authorization: Bearer $TOKEN"
```

### GET /api/qsos/{id}

Get a single QSO by MongoDB ObjectId.

```bash
curl http://localhost:8000/api/qsos/66123abc... \
  -H "Authorization: Bearer $TOKEN"
```

### PATCH /api/qsos/{id}

Partially update a QSO record.

- `BAND` and `MODE` are uppercased automatically
- If `QSO_DATE` or `TIME_ON` changes, `qso_date_utc` is recalculated
- Protected fields (`_operator`, `_deleted`, `_id`) cannot be changed

```bash
curl -X PATCH http://localhost:8000/api/qsos/66123abc... \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"RST_SENT": "57"}'
```

### DELETE /api/qsos/{id}

Soft-delete a QSO (sets `_deleted=true` — the record is not physically removed).

```bash
curl -X DELETE http://localhost:8000/api/qsos/66123abc... \
  -H "Authorization: Bearer $TOKEN"
```

Returns 204 No Content.

## Auto-Stamped Fields

| Field | Source | Notes |
|-------|--------|-------|
| OPERATOR | JWT callsign (account) | Always stamped. Cannot be overridden. |
| STATION_CALLSIGN | Profile `station_callsign` | Stamped when profile has `station_callsign` set. |

## Duplicate Detection

ollog checks for duplicate QSOs on every new record:

- **Window:** +/- 2 minutes on `QSO_DATE` + `TIME_ON`
- **Match fields:** `CALL` + `BAND` + `MODE` + operator
- **Exact duplicate guard:** every QSO also gets a deterministic `rowHash`; exact duplicate documents are rejected even if they arrive through another import path
- **Response:** 409 Conflict with `existing_id`, `existing_call`, `existing_band`, `existing_mode`
- **Override:** Append `?force=true` to the POST URL to bypass for single QSO creation

## Extra ADIF Fields

ollog accepts any standard ADIF field beyond the required set. Extra fields are stored verbatim and included in ADIF exports. Examples: `FREQ`, `TX_PWR`, `COMMENT`, `QTH`, `GRIDSQUARE`, `CONTEST_ID`.
