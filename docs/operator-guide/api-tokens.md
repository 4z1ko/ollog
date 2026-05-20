# API Tokens

API tokens are long-lived, named credentials for programmatic and automation access to ollog. Unlike JWT sessions (which expire after `JWT_EXPIRE_MINUTES`, default 480 minutes), API tokens are revocable and persist until explicitly deleted.

API tokens are suited for:

- Shell scripts that log QSOs
- Automation pipelines
- UDP ADIF datagrams that require per-datagram authentication
- Any integration that cannot handle browser-based JWT login

## Creating a Token

### Via the Web UI

Navigate to the profile page at `/profile`. Under the **Manage API Tokens** panel, enter a name, an optional expiry date, and click **Create Token**. The full token value is shown once — copy it immediately.

### Via the API

**POST /api/tokens/**

Requires JWT Bearer authentication (log in first, then use the JWT to create a token).

```bash
curl -X POST http://localhost:8000/api/tokens/ \
  -H "Authorization: Bearer $JWT" \
  -F "name=my-script" \
  -F "expires_at=2025-12-31"
```

Fields:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Human-readable label for this token |
| `expires_at` | No | Expiry date in `YYYY-MM-DD` format. If absent, the token does not expire. |

Response (201 Created):

```json
{
  "id": "6614a2b3e4f5c6d7e8f90123",
  "name": "my-script",
  "token": "ollog_abc123xyz...",
  "expires_at": "2025-12-31"
}
```

**The `token` value is returned exactly once.** Copy it before closing the response. It cannot be retrieved again.

## Listing Tokens

**GET /api/tokens/**

```bash
curl http://localhost:8000/api/tokens/ \
  -H "Authorization: Bearer $JWT"
```

Returns token metadata — name, id, created_at, expires_at. The token value itself is never returned.

```json
[
  {
    "id": "6614a2b3e4f5c6d7e8f90123",
    "name": "my-script",
    "created_at": "2024-04-15T14:30:00Z",
    "expires_at": "2025-12-31"
  }
]
```

## Revoking a Token

**DELETE /api/tokens/{token_id}**

```bash
curl -X DELETE http://localhost:8000/api/tokens/6614a2b3e4f5c6d7e8f90123 \
  -H "Authorization: Bearer $JWT"
```

Returns 204 No Content on success. The token is immediately invalidated — any subsequent API call using that token receives 401 Unauthorized.

## Using a Token in REST API Calls

Send the token as the `X-API-Key` header on any API request:

```bash
# List QSOs using an API token
curl http://localhost:8000/api/qsos/ \
  -H "X-API-Key: ollog_abc123xyz..."

# Log a QSO using an API token
curl -X POST http://localhost:8000/api/qsos/ \
  -H "X-API-Key: ollog_abc123xyz..." \
  -H "Content-Type: application/json" \
  -d '{"CALL": "DL1ABC", "BAND": "20m", "MODE": "SSB", "QSO_DATE": "20240415", "TIME_ON": "1430"}'
```

All endpoints that accept `Authorization: Bearer <jwt>` also accept `X-API-Key`. The token is validated against the API token store on every request.

## Using a Token in UDP ADIF Datagrams

For UDP ADIF per-datagram authentication, include the `APP_OLLOG_TOKEN` ADIF field in the datagram.

`APP_OLLOG_TOKEN` is an **ADIF field name** (using the ADIF `APP_` prefix convention for application-specific fields). It is **not an environment variable** and does not appear in the environment variables table. When present in a UDP datagram, ollog validates the field value against the API token store.

Example ADIF datagram with token:

```
<APP_OLLOG_TOKEN:20>ollog_abc123xyz...<CALL:6>DL1ABC<BAND:3>20m<MODE:3>FT8<QSO_DATE:8>20240415<TIME_ON:4>1430<EOR>
```

Replace the token length (`20` in the example) with the actual byte count of your token value.

See [UDP ADIF](udp-adif.md) for full UDP listener configuration.

## Token Security

- Tokens are stored as HMAC-SHA256 hashes in the database. The plaintext token value is never stored and cannot be recovered.
- Set `API_TOKEN_SECRET` in your `.env` to a strong random value. This is the HMAC key. If changed, all existing tokens become invalid.
- Revoke tokens that are no longer needed.
- For scripts, prefer tokens over storing JWT credentials (username/password) in plaintext.
