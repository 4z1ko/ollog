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

## Clear Operator Log

Admins can permanently delete all QSOs for any operator from the operators management
page. This action is available in the admin web UI only — there is no REST API endpoint for it.

1. In the admin web UI, navigate to the **Operators** management page.
2. Find the operator whose log you want to clear.
3. Click the **Clear log** button in that operator's row, alongside the existing
   enable/disable and reset-password actions.
4. A confirmation modal opens showing the operator's callsign and the number of QSOs
   that will be deleted.
5. Enter your admin password in the **Your admin password** field.
6. Click **Delete N QSOs** (where N is the count shown) to confirm, or **Keep log**
   to cancel.

!!! danger "This cannot be undone"
    Clearing an operator's log permanently deletes all their QSOs from the database.
    There is no undo and no recovery from the UI. If you need to recover deleted QSOs,
    restore from a backup taken before the clear operation.
