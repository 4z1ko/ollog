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
