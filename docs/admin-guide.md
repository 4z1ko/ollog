# Admin Guide

Admin accounts can create operator accounts, enable or disable them, and reset passwords. All admin endpoints require a valid Bearer token from an admin account.

## Authentication

Get a token by logging in:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=yourpassword" | jq -r .access_token)
```

Use this `$TOKEN` variable in every subsequent request. Tokens expire after `JWT_EXPIRE_MINUTES` minutes (default: 60).

## List Users

```bash
curl http://localhost:8000/admin/users/ \
  -H "Authorization: Bearer $TOKEN"
```

Returns an array of user objects. Each object contains:

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

The API prevents disabling the last remaining enabled admin account. If you attempt it, you receive a `409 Conflict` response with the message "Cannot disable the last enabled admin." This ensures you cannot accidentally lock yourself out entirely. To disable an admin account, first promote another user to admin or ensure at least one other admin account is enabled.

## Reset a User's Password

```bash
curl -X POST http://localhost:8000/admin/users/op1/reset-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password": "newpass123"}'
```

Returns `200 OK` with `{"username": "op1", "password_reset": true}`. The new password takes effect immediately. The user's existing tokens remain valid until they expire — a password reset does not immediately revoke active sessions.
