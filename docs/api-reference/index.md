# API Reference

ollog exposes a REST API at the base URL (e.g., `http://localhost:8000`). This section documents all available endpoints.

## Authentication Methods

### Bearer Token (JWT)

Obtain a JWT by logging in via POST /auth/token. Send it as `Authorization: Bearer <token>` on all subsequent requests.

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=youruser&password=yourpass" | jq -r .access_token)
```

Token lifetime is controlled by `JWT_EXPIRE_MINUTES` (default 480 minutes / 8 hours).

### X-API-Key (API Tokens)

For scripts and automation, use a long-lived API token as the `X-API-Key` header. All endpoints that accept JWT Bearer also accept X-API-Key. API tokens are revocable and named.

```bash
curl http://localhost:8000/api/qsos/ -H "X-API-Key: ollog_abc123..."
```

See [API Tokens](../operator-guide/api-tokens.md) for how to create and manage tokens.

### HTTP-Only Cookie (SSE Only)

The station feed endpoint (`GET /feed/station`) uses cookie authentication. The browser sets the session cookie automatically at login. This endpoint is not available from Swagger UI.

## Endpoint Groups

| Group | Prefix | Description |
|-------|--------|-------------|
| Auth | `/auth/` | Login, current user info |
| QSOs | `/api/qsos/` | CRUD for QSO records |
| ADIF | `/api/adif/` | Import and export ADIF files |
| Profile | `/api/profile/` | Operator profile management |
| Tokens | `/api/tokens/` | API token creation, listing, revocation |
| Admin | `/admin/` | User account management (admin role required) |
| Health | `/health` | Health check |

## Interactive Reference

Explore and try all endpoints directly in your browser:

[Interactive API Reference](interactive.md)

The interactive reference embeds Swagger UI with the complete OpenAPI schema. All API token and JWT authentication methods are available in the UI.
