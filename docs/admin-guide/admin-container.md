# Admin Container

ollog ships with a separate admin container that provides admin-only routes. It shares the same Docker image as the operator API but runs as an independent service on port 8001, with its own lifecycle.

## What the Admin Container Is

The admin container runs `app.admin_main:app` — a standalone FastAPI application that is separate from the operator app at port 8000. It exposes admin-only endpoints and uses a different cookie name to prevent session collision.

Key properties:

- **Port:** 8001
- **Routes:** `/admin/*` (user management), `/auth` (admin login), `/health`
- **Cookie name:** `admin_token` — distinct from the operator app's `access_token` cookie. This prevents cookie collision between ports 8000 and 8001 (per RFC 6265, cookies do not scope to port, so without distinct names a login on 8001 would overwrite the 8000 cookie).
- **Shares the database** with the operator app. Changes to users are reflected immediately.

## Starting the Admin Container

The admin container uses `profiles: [admin]` in `docker-compose.yml`. It does NOT start with plain `docker compose up` — you must pass `--profile admin` explicitly.

```bash
docker compose --profile admin up -d admin
```

This starts only the admin container without affecting the operator app on port 8000 (if it is already running).

To start the entire stack plus the admin container in one command:

```bash
docker compose --profile admin up -d
```

## Stopping the Admin Container

Stop only the admin container (operator app continues running):

```bash
docker compose --profile admin stop admin
```

Or bring down the admin container and remove its containers:

```bash
docker compose --profile admin down
```

This does NOT affect the operator app on port 8000 or the MongoDB container.

## First Login

1. Start the admin container as shown above.
2. Navigate to `http://hostname:8001/` in your browser.
3. Log in with the `ADMIN_USERNAME` and `ADMIN_PASSWORD` from your `.env` file.

The admin container bootstraps the admin account from the same environment variables as the operator app. If the account already exists in the database (e.g., created by the operator app), the bootstrap is skipped.

## Admin REST API

Admin REST API calls to port 8001 use `Authorization: Bearer <jwt>`:

```bash
TOKEN=$(curl -s -X POST http://localhost:8001/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=yourpassword" | jq -r .access_token)

curl http://localhost:8001/admin/users/ \
  -H "Authorization: Bearer $TOKEN"
```

You can also use admin endpoints via the operator API on port 8000 if you are logged in as an admin-role user:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=yourpassword" | jq -r .access_token)

curl http://localhost:8000/admin/users/ \
  -H "Authorization: Bearer $TOKEN"
```

See [Account Management](account-management.md) for the full admin endpoint reference.

## Security Note

Do NOT expose port 8001 publicly. The admin container provides unrestricted account management capabilities. Restrict access to trusted networks using a firewall rule or reverse proxy:

```
# Example: iptables rule to allow only local network access to port 8001
iptables -A INPUT -p tcp --dport 8001 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 8001 -j DROP
```

In production, the operator API on port 8000 is the only port that should be publicly accessible.
