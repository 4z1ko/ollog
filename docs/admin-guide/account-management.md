# Account Management

Admin accounts can create operator accounts, enable or disable them, and reset passwords. All admin endpoints require a valid Bearer token from an admin account.

Admin operations are available both via the REST API (documented here) and via the admin web UI at `http://localhost:8001`. See [Admin Container](admin-container.md) for how to start the admin container.

## Authentication

Get an admin token by logging in via the admin API:

```bash
TOKEN=$(curl -s -X POST http://localhost:8001/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=yourpassword" | jq -r .access_token)
```

Tokens expire after `JWT_EXPIRE_MINUTES` minutes (default: 480).

Alternatively, if you are using the operator API on port 8000 with an admin account:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=yourpassword" | jq -r .access_token)
```

## List Users

```bash
curl http://localhost:8000/admin/users/ \
  -H "Authorization: Bearer $TOKEN"
```

Returns an array of user objects:

| Field | Type | Description |
|-------|------|-------------|
| username | string | Login username |
| callsign | string | Amateur radio callsign (uppercased) |
| role | string | `admin` or `operator` |
| enabled | boolean | Whether the account can log in |

## Create an Operator Account

```bash
curl -X POST http://localhost:8000/admin/users/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username": "op1", "password": "securepass", "callsign": "W1AW"}'
```

Returns `201 Created` with the new user object. The callsign is stored uppercased automatically. If the username already exists, you will receive a `409 Conflict` response.

## Enable / Disable an Account

```bash
curl -X PATCH http://localhost:8000/admin/users/op1/enabled \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

Set `enabled` to `true` to re-enable an account. Disabling prevents that user from logging in. Note: a disabled user's existing token still works until it expires — disabling does not immediately revoke active sessions.

### Last-Admin Lockout Guard

The API prevents disabling the last remaining enabled admin account. If you attempt it, you receive a `409 Conflict` response with the message "Cannot disable the last enabled admin." To disable an admin account, first ensure at least one other admin account is enabled.

## Reset a User's Password

```bash
curl -X POST http://localhost:8000/admin/users/op1/reset-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password": "newpass123"}'
```

Returns `200 OK` with `{"username": "op1", "password_reset": true}`. The new password takes effect immediately. The user's existing tokens remain valid until they expire — a password reset does not immediately revoke active sessions.
