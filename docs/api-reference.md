# API Reference

ollog exposes a REST API at the base URL (e.g., `http://localhost:8000`). Interactive Swagger docs are available at `/docs`. This page provides a complete reference with curl examples covering all 16 endpoints.

---

## Authentication

Two auth mechanisms are supported.

### Bearer Token (Primary)

Most endpoints use Bearer token auth.

1. POST to `/auth/token` with form-encoded `username` and `password`
2. Extract `access_token` from the JSON response
3. Send as `Authorization: Bearer <token>` on every subsequent request

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=yourpassword" | jq -r .access_token)
```

Token expiry is controlled by the `JWT_EXPIRE_MINUTES` environment variable (default: 60 minutes). After expiry, repeat the above to obtain a fresh token.

### HTTP-Only Cookie (SSE Only)

The station feed endpoint (`GET /feed/station`) uses cookie authentication. The browser's `EventSource` API cannot send custom `Authorization` headers, so the JWT is stored in an HttpOnly cookie at browser login instead. When accessing the API directly via curl or scripts, the station feed is not easily usable outside a browser session — it is designed primarily for browser consumption.

---

## Auth Endpoints

### POST /auth/token

Obtain a JWT access token.

- **Auth:** None — this is the login endpoint
- **Request:** `application/x-www-form-urlencoded` body with `username` and `password` fields
- **Response:** 200 `{"access_token": "...", "token_type": "bearer"}`
- **Errors:** 401 if credentials are invalid or account is disabled

```bash
curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=yourpassword"
```

### GET /auth/me

Get the current authenticated user's info.

- **Auth:** Bearer token
- **Response:** 200 with user object: `{"username": "...", "callsign": "...", "role": "..."}`
- **Errors:** 401 if not authenticated

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## QSO Endpoints

### POST /api/qsos/

Create a new QSO record.

- **Auth:** Bearer token
- **Request:** JSON body. Required fields: `CALL`, `QSO_DATE` (YYYYMMDD), `TIME_ON` (HHMM or HHMMSS), `BAND`, `MODE`. Optional fields: `FREQ`, `RST_SENT`, `RST_RCVD`. Additional ADIF fields are accepted and stored verbatim. Do not include `OPERATOR` or `STATION_CALLSIGN` — these are auto-stamped from the authenticated user's profile.
- **Response:** 201 with QSO object including generated `id` and auto-stamped `_operator`
- **Errors:**
  - 409 if a duplicate is detected (same CALL+BAND+MODE+operator within ±2 min). Response body includes `existing_id`, `existing_call`, `existing_band`, `existing_mode`. Add `?force=true` query param to override.
  - 422 if required fields are missing or validation fails

```bash
curl -X POST http://localhost:8000/api/qsos/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"CALL": "DL1ABC", "BAND": "20m", "MODE": "SSB", "QSO_DATE": "20240415", "TIME_ON": "1430", "RST_SENT": "59", "RST_RCVD": "59"}'
```

### GET /api/qsos/

List QSOs for the authenticated operator with pagination and optional filters.

- **Auth:** Bearer token
- **Query params:** `page` (default 1), `page_size` (default 50, max 500), `call`, `band`, `mode`, `date_from` (YYYYMMDD), `date_to` (YYYYMMDD), `sort` (default `-qso_date_utc`)
- **Response:** 200 with `{"items": [...], "total": N, "page": N, "page_size": N}`. Only returns QSOs where `_operator` matches the authenticated user. Soft-deleted QSOs are excluded.

```bash
curl "http://localhost:8000/api/qsos/?page=1&page_size=50" \
  -H "Authorization: Bearer $TOKEN"
```

### GET /api/qsos/{id}

Get a single QSO by ID.

- **Auth:** Bearer token
- **Path param:** `id` — MongoDB ObjectId string
- **Response:** 200 with QSO object
- **Errors:** 404 if not found, soft-deleted, or owned by a different operator

```bash
curl http://localhost:8000/api/qsos/66123abc... \
  -H "Authorization: Bearer $TOKEN"
```

### PATCH /api/qsos/{id}

Partially update a QSO record.

- **Auth:** Bearer token
- **Path param:** `id` — MongoDB ObjectId string
- **Request:** JSON body with any fields to update. `BAND` and `MODE` are uppercased automatically. If `QSO_DATE` or `TIME_ON` changes, `qso_date_utc` is recalculated. Protected fields (`_operator`, `_deleted`, `_id`) are stripped and cannot be changed.
- **Response:** 200 with updated QSO object
- **Errors:** 404 if not found, soft-deleted, or owned by a different operator

```bash
curl -X PATCH http://localhost:8000/api/qsos/66123abc... \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"RST_SENT": "57"}'
```

### DELETE /api/qsos/{id}

Soft-delete a QSO (sets `_deleted=true` — the record is not physically removed from the database).

- **Auth:** Bearer token
- **Path param:** `id` — MongoDB ObjectId string
- **Response:** 204 No Content
- **Errors:** 404 if not found, already deleted, or owned by a different operator

```bash
curl -X DELETE http://localhost:8000/api/qsos/66123abc... \
  -H "Authorization: Bearer $TOKEN"
```

---

## ADIF Endpoints

### POST /api/adif/import

Import QSOs from an ADIF (.adi or .adif) file.

- **Auth:** Bearer token
- **Request:** `multipart/form-data` with a `file` field containing the ADIF file (max 10 MB)
- **Response:** 200 with an `ADIFImportReport` object:
  ```json
  {
    "total_records": N,
    "accepted": [{"record_index": N, "call": "...", "id": "..."}],
    "duplicates": [{"record_index": N, "call": "...", "existing_id": "..."}],
    "errors": [{"record_index": N, "call": "..." | null, "error": "..."}]
  }
  ```
  Each `error` entry includes `record_index`, `call` (null for parse errors where no CALL key was found), and `error` (description of the problem).
- **Errors:** 413 if the file exceeds 10 MB
- **Notes:**
  - Duplicate detection uses the same ±2 minute window as the QSO create endpoint
  - Import preserves file values for OPERATOR and STATION_CALLSIGN — they are NOT auto-stamped from the authenticated user's profile (preserving historical record fidelity)
  - All per-record errors are accumulated and returned — no records are silently dropped

```bash
curl -X POST http://localhost:8000/api/adif/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@mylog.adi"
```

### GET /api/adif/export

Export the authenticated operator's log as an ADIF 3.1.4 file.

- **Auth:** Bearer token
- **Response:** 200 with `text/plain` streaming body (Content-Disposition: attachment). The filename is `{callsign}_logbook.adi`. Only the authenticated operator's QSOs are included. Soft-deleted records are excluded.
- **Notes:** The response is a StreamingResponse and is not Pydantic-validated. The ADIF header specifies `ADIF_VER:3.1.4` and `PROGRAMID:ollog`.

```bash
curl http://localhost:8000/api/adif/export \
  -H "Authorization: Bearer $TOKEN" \
  -o mylog.adi
```

---

## Profile Endpoints

### GET /api/profile/

Get the authenticated operator's profile.

- **Auth:** Bearer token
- **Response:** 200 with profile object:
  ```json
  {
    "callsign": "W1AW",
    "station_callsign": "W1AW" | null,
    "name": "..." | null,
    "email": "..." | null,
    "qth": "..." | null,
    "state": "..." | null,
    "country": "..." | null,
    "my_gridsquare": "FN31pr" | null,
    "latitude": 41.5 | null,
    "longitude": -72.75 | null,
    "my_rig": "..." | null,
    "my_antenna": "..." | null,
    "tx_pwr": 100.0 | null
  }
  ```
  A user with no profile fields set receives all-null optional fields — not an error.

```bash
curl http://localhost:8000/api/profile/ \
  -H "Authorization: Bearer $TOKEN"
```

### PATCH /api/profile/

Update the authenticated operator's profile fields.

- **Auth:** Bearer token
- **Request:** JSON body with any combination of: `station_callsign`, `name`, `email`, `qth`, `state`, `country`, `my_gridsquare`, `my_rig`, `my_antenna`, `tx_pwr`. Only provided fields are updated (partial update). Absent fields are left unchanged.
- **Response:** 200 with updated profile object (same shape as GET /api/profile/)
- **Notes:**
  - `my_gridsquare` must be a valid Maidenhead locator (4- or 6-character format, e.g. `FN31pr`). When set, `latitude` and `longitude` are auto-computed from the grid center.
  - `station_callsign` is auto-stamped on future QSOs as `STATION_CALLSIGN`.

```bash
curl -X PATCH http://localhost:8000/api/profile/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"station_callsign": "W1AW", "my_gridsquare": "FN31pr"}'
```

---

## Admin Endpoints

All admin endpoints require a Bearer token from an admin-role account.

### GET /admin/users/

List all user accounts.

- **Auth:** Bearer token (admin role required)
- **Response:** 200 with array of user objects: `[{"username": "...", "callsign": "...", "role": "...", "enabled": true|false}, ...]`. `hashed_password` is never included.

```bash
curl http://localhost:8000/admin/users/ \
  -H "Authorization: Bearer $TOKEN"
```

### POST /admin/users/

Create a new operator account.

- **Auth:** Bearer token (admin role required)
- **Request:** JSON with `username` (string), `callsign` (string, stored uppercased), `password` (string)
- **Response:** 201 with created user object: `{"username": "...", "callsign": "...", "enabled": true, "role": "operator"}`
- **Errors:** 409 if `username` already exists

```bash
curl -X POST http://localhost:8000/admin/users/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "op1", "password": "securepass", "callsign": "W1AW"}'
```

### PATCH /admin/users/{username}/enabled

Enable or disable an operator account.

- **Auth:** Bearer token (admin role required)
- **Path param:** `username`
- **Request:** JSON with `enabled` (bool)
- **Response:** 200 with `{"username": "...", "enabled": true|false}`
- **Errors:**
  - 404 if user not found
  - 409 if attempting to disable the last enabled admin account (lockout guard)

```bash
curl -X PATCH http://localhost:8000/admin/users/op1/enabled \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### POST /admin/users/{username}/reset-password

Reset a user's password.

- **Auth:** Bearer token (admin role required)
- **Path param:** `username`
- **Request:** JSON with `password` (string — the new password)
- **Response:** 200 with `{"username": "...", "password_reset": true}`
- **Errors:** 404 if user not found
- **Notes:** This endpoint is POST, not PATCH. The new password is usable immediately.

```bash
curl -X POST http://localhost:8000/admin/users/op1/reset-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password": "newpass123"}'
```

---

## SSE Endpoint

### GET /feed/station

Server-Sent Events stream broadcasting new QSOs across all operators.

- **Auth:** HTTP-only cookie (NOT Bearer token — see Authentication section above)
- **Response:** `text/event-stream`. Each event has `event: new_qso` and `data` containing an HTML fragment rendered for the station feed UI.
- **Notes:**
  - This endpoint is excluded from the OpenAPI schema (`/docs`) because it uses cookie auth and cannot be exercised from Swagger UI.
  - The SSE stream is designed for browser consumption. The browser sets the session cookie automatically at login.
  - Clients stay connected and receive events as QSOs are logged. The stream does not terminate on its own.

```bash
# Browser: EventSource connects automatically using the HttpOnly cookie set at login.
# curl (requires cookie from an active browser session):
curl -N --cookie "access_token=YOUR_JWT_VALUE" http://localhost:8000/feed/station
```
