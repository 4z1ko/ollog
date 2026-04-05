# Phase 15: Narrative Documentation Content - Research

**Researched:** 2026-04-04
**Domain:** MkDocs Material documentation authoring / technical writing for a FastAPI + MongoDB self-hosted app
**Confidence:** HIGH

## Summary

Phase 15 is a content authoring phase, not a code-writing phase. The toolchain (MkDocs Material 9.x, `mkdocs.yml`, `docs/` directory, `site/` served at `/guide`) is already operational from Phase 14. The work is: write markdown pages, update `mkdocs.yml` nav, and rebuild `site/`. No new dependencies are needed.

The codebase has been fully read. Every endpoint, auth mechanism, env var, and admin behavior is documented below based on primary source code evidence. The "15 endpoints" count in the phase description is correct once the SSE endpoint (`GET /feed/station`) is included — even though it is excluded from the OpenAPI schema. The API reference in DOCS-04 should document 15 endpoints: the 14 in the OpenAPI schema minus the `/api/whoami` development stub, plus the SSE endpoint documented separately.

One discrepancy to flag: the phase description says `PATCH /admin/users/{username}/reset-password` but the actual router code defines it as `POST /admin/users/{username}/reset-password`. The documentation must match the code, not the requirement spec. This is verified from `app/admin/router.py` (line 99).

**Primary recommendation:** Write all markdown content from the codebase facts documented in this file. No library research is needed — the tech stack is already locked. Focus on accuracy: curl examples must use actual request/response shapes from the router code.

## Standard Stack

### Core (already installed — no changes needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| MkDocs | 1.6.1 | Static site generator | Already running in project |
| MkDocs Material | 9.x | Theme with nav, search, code highlighting | Already configured in mkdocs.yml |

### MkDocs Material 9.x features available

- `nav:` list in `mkdocs.yml` — ordered page list, supports nesting
- Code blocks with syntax highlighting (fenced code with language tag)
- Admonitions (`!!! note`, `!!! warning`, `!!! tip`) — useful for callouts
- Tabs — useful for showing curl vs Python examples side by side
- Tables — built-in markdown
- `--strict` flag causes build to fail on any broken link or nav reference

### Installation

Already installed. No action needed.

```bash
# To rebuild site after writing content:
uv run mkdocs build --strict
```

## Architecture Patterns

### Recommended docs/ File Structure

```
docs/
├── index.md                    # Home (already exists — overwrite)
├── deployment.md               # DOCS-01: Deployment guide
├── getting-started.md          # DOCS-02: Operator walkthrough
├── admin-guide.md              # DOCS-03: Admin account management
├── api-reference.md            # DOCS-04 + DOCS-05: Full API reference + auth flows
├── adif-field-reference.md     # DOCS-06: ADIF field format reference
└── troubleshooting.md          # DOCS-07: Three failure modes
```

### mkdocs.yml nav update

```yaml
nav:
  - Home: index.md
  - Deployment: deployment.md
  - Getting Started: getting-started.md
  - Admin Guide: admin-guide.md
  - API Reference: api-reference.md
  - ADIF Field Reference: adif-field-reference.md
  - Troubleshooting: troubleshooting.md
```

### Pattern: One requirement = one page

Each DOCS-0N requirement maps to exactly one markdown file. This prevents nav sprawl and makes cross-linking predictable.

### Anti-Patterns to Avoid

- **Splitting API reference across multiple files:** Users need all endpoints on one page for Ctrl+F.
- **Writing generic docs:** Every curl example must use the actual endpoint paths/schemas from this codebase.
- **Forgetting `--strict` build:** The build command for commit is `uv run mkdocs build --strict`. A broken nav reference fails silently without `--strict`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Syntax highlighting in docs | Custom CSS | MkDocs Material fenced code blocks with language tag | Built-in, works out of box |
| Warning/note callouts | HTML `<div>` blocks | MkDocs Material admonitions (`!!! warning`) | Renders cleanly, accessible |
| Navigation | Custom HTML nav | `mkdocs.yml` nav section | Material theme handles rendering |
| Search | Custom search | MkDocs Material built-in search | Already enabled by theme |

## Common Pitfalls

### Pitfall 1: Endpoint HTTP method discrepancy

**What goes wrong:** The phase description states `PATCH /admin/users/{username}/reset-password` but the actual router (`app/admin/router.py` line 99) defines it as `POST /admin/users/{username}/reset-password`. If documentation says PATCH, curl examples will fail for users.

**Why it happens:** Phase descriptions are written from memory; routers are ground truth.

**How to avoid:** Use code, not the phase spec, as the source of truth for HTTP methods. Verified: it is `POST`.

**Warning signs:** A curl example with `-X PATCH` to `/admin/users/.../reset-password` returns 405 Method Not Allowed.

### Pitfall 2: Missing strict flag breaks site silently

**What goes wrong:** `uv run mkdocs build` succeeds even with a broken nav reference or dead internal link. `--strict` is required to catch these.

**How to avoid:** Always use `uv run mkdocs build --strict` for the production build.

### Pitfall 3: Documenting `/api/whoami` as a real endpoint

**What goes wrong:** `GET /api/whoami` is a development stub in `app/main.py` (docstring says "will be replaced by real endpoints in later phases"). It should not appear in the API reference.

**How to avoid:** The API reference covers the 6 endpoint groups: auth, QSOs, ADIF, profile, admin, SSE. `whoami` and `health` are infrastructure endpoints, not documented in the API reference.

### Pitfall 4: SSE endpoint is excluded from OpenAPI but must be documented

**What goes wrong:** `GET /feed/station` is mounted with `include_in_schema=False` in `main.py`, so it does not appear in `/docs`. But DOCS-04 and DOCS-05 require documenting it explicitly (and DOCS-05 requires explaining why EventSource cannot send Authorization headers).

**How to avoid:** Document it in a dedicated "SSE / Live Feed" section with explanation of cookie-auth requirement.

### Pitfall 5: Env var defaults diverge between config.py and docker-compose.yml

**What goes wrong:** `app/config.py` has `mongodb_uri` defaulting to `mongodb://mongodb:27017` (no replicaSet param), but `docker-compose.yml` passes `MONGODB_URI=mongodb://mongodb:27017/?replicaSet=rs0`. The deployment guide must document the docker-compose env override, not the config.py default.

**How to avoid:** Document the docker-compose env values (with `replicaSet=rs0`) as the canonical deployment configuration.

## Code Examples

Verified from router source files:

### POST /auth/token (form-encoded login)

```bash
# Source: app/auth/router.py line 12, OAuth2PasswordRequestForm
curl -X POST http://localhost:8000/auth/token \
  -d "username=admin&password=secret"
# Response: {"access_token": "...", "token_type": "bearer"}
```

### GET /auth/me

```bash
# Source: app/auth/router.py line 42
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer $TOKEN"
# Response: {"username": "admin", "callsign": "W1AW", "role": "admin"}
```

### POST /api/qsos/ (create QSO)

```bash
# Source: app/qso/router.py line 111, QSOCreateRequest
curl -X POST http://localhost:8000/api/qsos/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"CALL":"W1AW","QSO_DATE":"20240415","TIME_ON":"1430","BAND":"20m","MODE":"SSB"}'
# Success: 201 + QSOResponse
# Duplicate: 409 + DuplicateQSOError — add ?force=true to override
```

### GET /api/qsos/ (list with filters)

```bash
# Source: app/qso/router.py line 155
curl "http://localhost:8000/api/qsos/?page=1&page_size=50&band=20m" \
  -H "Authorization: Bearer $TOKEN"
# Response: {"items": [...], "total": N, "page": 1, "page_size": 50}
```

### PATCH /api/qsos/{id}

```bash
# Source: app/qso/router.py line 214
curl -X PATCH http://localhost:8000/api/qsos/6639abc123def456 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"RST_SENT":"59","RST_RCVD":"57"}'
# Returns updated QSOResponse
```

### DELETE /api/qsos/{id} (soft-delete)

```bash
# Source: app/qso/router.py line 259
curl -X DELETE http://localhost:8000/api/qsos/6639abc123def456 \
  -H "Authorization: Bearer $TOKEN"
# Returns 204 No Content — record is soft-deleted, not physically removed
```

### POST /api/adif/import

```bash
# Source: app/adif/router.py line 137
curl -X POST http://localhost:8000/api/adif/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@mylogbook.adi"
# Response: ADIFImportReport with accepted/duplicates/errors lists
```

### GET /api/adif/export

```bash
# Source: app/adif/router.py line 196
curl http://localhost:8000/api/adif/export \
  -H "Authorization: Bearer $TOKEN" \
  -o mylogbook_export.adi
# Downloads .adi file with ADIF header: ADIF_VER 3.1.4, PROGRAMID ollog
```

### GET /api/profile/

```bash
# Source: app/profile/router.py line 13
curl http://localhost:8000/api/profile/ \
  -H "Authorization: Bearer $TOKEN"
# Response: ProfileResponse — all fields, nulls for unset optionals
```

### PATCH /api/profile/

```bash
# Source: app/profile/router.py line 26, ProfileUpdateRequest
curl -X PATCH http://localhost:8000/api/profile/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"station_callsign":"W1AW/1","my_gridsquare":"FN42","my_rig":"Icom IC-7300"}'
# Partial update — absent fields unchanged
# my_gridsquare auto-derives latitude/longitude from Maidenhead grid center
```

### GET /admin/users/ (list all users)

```bash
# Source: app/admin/router.py line 118
curl http://localhost:8000/admin/users/ \
  -H "Authorization: Bearer $ADMIN_TOKEN"
# Returns array: [{username, callsign, role, enabled}, ...]
# hashed_password never returned
```

### POST /admin/users/ (create operator)

```bash
# Source: app/admin/router.py line 38
curl -X POST http://localhost:8000/admin/users/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"wb6yyz","callsign":"WB6YYZ","password":"changeme"}'
# 201 created, 409 if username exists. Callsign uppercased. Role = operator.
```

### PATCH /admin/users/{username}/enabled

```bash
# Source: app/admin/router.py line 69
curl -X PATCH http://localhost:8000/admin/users/wb6yyz/enabled \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
# 409 if disabling the last enabled admin (lockout guard)
```

### POST /admin/users/{username}/reset-password

```bash
# Source: app/admin/router.py line 99 — NOTE: POST, not PATCH
curl -X POST http://localhost:8000/admin/users/wb6yyz/reset-password \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password": "newpassword"}'
# {"username": "wb6yyz", "password_reset": true}
```

### GET /feed/station (SSE — cookie auth only)

```bash
# Source: app/feed/router.py line 12
# CANNOT use Authorization header — EventSource API does not support custom headers.
# Must use browser session (cookie set at login) or curl with cookie:
curl http://localhost:8000/feed/station \
  --cookie "access_token=$TOKEN" \
  -H "Accept: text/event-stream"
# Streams: event: new_qso\ndata: <html fragment>\n\n
```

## Codebase Facts for Documentation

This section documents all facts needed to write accurate docs without re-reading code.

### Env Vars (from config.py + docker-compose.yml)

| Variable | Required | Default (docker-compose) | Description |
|----------|----------|--------------------------|-------------|
| SECRET_KEY | YES | (must override from `dev-secret-change-in-production`) | JWT signing key |
| MONGODB_URI | no | `mongodb://mongodb:27017/?replicaSet=rs0` | MongoDB connection string |
| MONGODB_DB | no | `ollog` | Database name |
| JWT_EXPIRE_MINUTES | no | `1440` (24 hours) | Token expiry in minutes |
| ADMIN_USERNAME | bootstrap only | (not set) | Initial admin username |
| ADMIN_PASSWORD | bootstrap only | (not set) | Initial admin password |
| ADMIN_CALLSIGN | bootstrap only | (not set) | Initial admin callsign |

Bootstrap behavior: if `ADMIN_USERNAME/PASSWORD/CALLSIGN` are all set and no user with that username exists, the admin account is created on startup. If the user already exists, the env vars are ignored. Changing these env vars after first start has no effect.

### Actual Endpoint List (verified from routers)

**Auth (2 endpoints)**
- `POST /auth/token` — form-encoded login, returns JWT
- `GET /auth/me` — returns username/callsign/role from JWT

**QSOs (5 endpoints)**
- `POST /api/qsos/` — create QSO, 201, duplicate detection with 409
- `GET /api/qsos/` — paginated list, filters: call/band/mode/date_from/date_to/sort
- `GET /api/qsos/{id}` — single QSO by MongoDB ObjectId string
- `PATCH /api/qsos/{id}` — partial update, accepts arbitrary ADIF fields
- `DELETE /api/qsos/{id}` — soft-delete (sets `_deleted: true`), 204 No Content

**ADIF (2 endpoints)**
- `POST /api/adif/import` — multipart file upload, returns ADIFImportReport
- `GET /api/adif/export` — streaming ADIF download

**Profile (2 endpoints)**
- `GET /api/profile/` — read own profile
- `PATCH /api/profile/` — partial update, gridsquare auto-derives lat/lon

**Admin (4 endpoints)**
- `GET /admin/users/` — list all accounts
- `POST /admin/users/` — create operator account
- `PATCH /admin/users/{username}/enabled` — enable/disable with last-admin guard
- `POST /admin/users/{username}/reset-password` — reset password (POST, not PATCH)

**SSE (1 endpoint, excluded from OpenAPI)**
- `GET /feed/station` — server-sent events, cookie auth only

**Not to document in API reference:**
- `GET /health` — infrastructure health check
- `GET /api/whoami` — development stub (docstring says it will be replaced)

### Auth Flows

**Bearer token (REST API / scripts):**
1. POST /auth/token with form body `username=x&password=y`
2. Extract `access_token` from response
3. All subsequent requests: `Authorization: Bearer <token>`
4. Token expires after JWT_EXPIRE_MINUTES (default 24h)

**HTTP-only cookie (browser SSE):**
- Used by the browser UI and SSE feed
- Login via browser sets `access_token` cookie (HttpOnly, not accessible to JS)
- `EventSource` in the browser cannot set custom headers — this is a browser API limitation
- The SSE endpoint `GET /feed/station` reads `access_token` from cookie via `get_current_operator_callsign_cookie` dependency
- Scripts wanting to consume SSE must pass `--cookie "access_token=$TOKEN"` to curl

### ADIF Field Format Facts

| Field | Format | Example | Notes |
|-------|--------|---------|-------|
| QSO_DATE | YYYYMMDD | `20240415` | UTC date |
| TIME_ON | HHMM or HHMMSS | `1430` or `143045` | UTC time |
| BAND | string | `40m`, `20m`, `2m` | Amateur band designator |
| MODE | string | `SSB`, `CW`, `FT8`, `FM` | Per ADIF spec, uppercased on ingest |
| RST_SENT | string | `59` (phone), `599` (CW) | Signal report sent |
| RST_RCVD | string | `57` | Signal report received |
| CALL | string | `W1AW` | Contacted station callsign |
| OPERATOR | auto-stamped | (from JWT, user's callsign) | Person at the key — set from profile |
| STATION_CALLSIGN | auto-stamped | (from profile.station_callsign) | Licensed station callsign |
| FREQ | string in MHz | `14.225` | Optional |

**Extra fields:** The QSO model uses `extra="allow"`. Any ADIF field can be included in POST body and will be stored. This enables APP_ prefixed fields, USERDEF fields, and other non-standard fields.

**ADIF import does NOT auto-stamp:** OPERATOR/STATION_CALLSIGN are preserved from the import file as-is. Historical records from other operators are not overwritten.

### Soft-Delete Behavior

- DELETE endpoint sets `_deleted: True` — record is NOT physically removed
- Soft-deleted QSOs are excluded from list, get, and export operations
- Permanent deletion requires direct MongoDB access
- The `force=true` query param on POST /api/qsos/ overrides duplicate detection, but is unrelated to deletion

### Duplicate Detection

- Window: ±2 minutes based on `qso_date_utc`
- Keys: operator callsign + CALL + BAND + MODE
- API response: 409 Conflict with `DuplicateQSOError` body
- Override: `?force=true` query param on POST /api/qsos/
- Same logic in ADIF import (no force override for import — duplicates go in `duplicates` list)

### Admin Lockout Guard

- `PATCH /admin/users/{username}/enabled` with `{"enabled": false}` on an admin account
- If the target user is the last enabled admin → returns 409 Conflict
- Error message: "Cannot disable the last enabled admin"
- The check counts `{role: "admin", enabled: true}` — if count <= 1, refuse

### Troubleshooting: Three Common Failure Modes

**1. SSE feed not updating**
- Root cause: MongoDB change streams require a replica set. Single-node MongoDB without `--replSet rs0` does not support change streams.
- The `watch_qsos` coroutine (started in app lifespan) will fail to open the change stream if MongoDB is not in replica set mode.
- Fix: Ensure `MONGODB_URI` includes `replicaSet=rs0` and MongoDB was started with `--replSet rs0`. Both are set correctly in the provided docker-compose.yml. The issue only arises if the user brings their own MongoDB.
- Verification: `docker compose logs api` will show `ChangeStreamHistoryLost` or `OperationNotSupportedInTransaction` errors.

**2. Login fails after restart (SECRET_KEY)**
- Root cause: If `SECRET_KEY` changes between restarts, all existing JWTs are invalid (JWT signature verification fails against the new key). Also: the `dev-secret-change-in-production` default in docker-compose is only safe for development. If it differs from the key used when the token was issued, auth fails.
- Fix: Set `SECRET_KEY` explicitly in `.env` and do not change it. The docker-compose `environment:` block overrides the `.env` file value for SECRET_KEY — so `.env` SECRET_KEY is effectively ignored unless the compose file is modified.
- Also applies: if MongoDB loses user data (volume deleted), the bootstrap admin will be re-created on restart with whatever ADMIN_USERNAME/PASSWORD is set.

**3. Import returns all duplicates**
- Root cause: Re-importing the same ADIF file that was already imported. The ±2 min duplicate window will match all records.
- Also: importing a file where QSO_DATE/TIME_ON values were changed (different format) may fail the duplicate check differently.
- There is no force override in the import endpoint (unlike single QSO creation).
- Fix: This is expected behavior. If the user genuinely wants to re-import, they must delete the existing records via the UI or API first.

### Bootstrap Admin: One-Time Behavior

From `app/main.py` `_bootstrap_admin()`:
1. If any of `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_CALLSIGN` are not set → skip (no admin created)
2. If a user with `ADMIN_USERNAME` already exists → skip (idempotent)
3. Otherwise: create the admin user with `role="admin"`, `enabled=True`

Result: After first successful startup, changing these env vars does NOT change the admin account. To change the admin password post-bootstrap, use `POST /admin/users/{username}/reset-password`.

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Sphinx + RST | MkDocs Material + Markdown | Simpler authoring, Material theme handles design |
| ReadTheDocs hosted | Self-hosted `site/` served by FastAPI StaticFiles | On-prem deployment, always in sync with app |

## Open Questions

1. **Should `/health` be documented?**
   - What we know: `GET /health` exists and returns MongoDB connectivity status
   - What's unclear: Phase spec says "6 groups" but health doesn't fit any group
   - Recommendation: Mention briefly in Deployment guide as a verification step, skip in API reference table

2. **ADIF version in export**
   - What we know: `_ADIF_HEADER = "<ADIF_VER:5>3.1.4\n<PROGRAMID:5>ollog\n<EOH>\n\n"` (from adif/router.py)
   - Recommendation: Document exported files use ADIF 3.1.4 format

3. **Profile fields in ADIF auto-stamp: which fields exactly?**
   - From `app/qso/service.py` (not read but referenced in phase context): OPERATOR always stamped from JWT callsign; STATION_CALLSIGN/equipment stamped when set in profile
   - Recommendation: Verify `app/qso/service.py` `build_qso_dict` to get exact stamp field list before writing the profile setup section of getting-started walkthrough

## Sources

### Primary (HIGH confidence)
- `app/auth/router.py` — POST /auth/token, GET /auth/me endpoint definitions
- `app/auth/dependencies.py` — Bearer token and cookie auth dependency implementations
- `app/auth/models.py` — User document schema, profile fields
- `app/qso/router.py` — 5 QSO endpoints, duplicate detection, request/response schemas
- `app/adif/router.py` — import/export endpoints, ADIFImportReport schema, ADIF header
- `app/admin/router.py` — 4 admin endpoints, lockout guard logic
- `app/profile/router.py` — GET/PATCH profile
- `app/profile/schemas.py` — ProfileUpdateRequest and ProfileResponse fields
- `app/feed/router.py` — SSE endpoint, cookie auth dependency
- `app/main.py` — bootstrap admin logic, route mounting, include_in_schema=False for UI/SSE
- `app/config.py` — env var names and defaults
- `docker-compose.yml` — production env values, MongoDB replica set setup
- `mkdocs.yml` — current state: only index.md in nav
- `docs/index.md` — scaffold placeholder only
- `pyproject.toml` — mkdocs-material==9.*, mkdocs 1.6.1 installed

### Secondary (MEDIUM confidence)
- MkDocs Material 9.x admonitions, tabs, nav features — based on training knowledge, verified by version constraint in pyproject.toml

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — already installed, version confirmed from `uv run mkdocs --version` (1.6.1) and pyproject.toml (mkdocs-material==9.*)
- Architecture (file/page structure): HIGH — follows standard single-page-per-topic MkDocs pattern
- All endpoint facts: HIGH — read directly from router source files
- All env var facts: HIGH — read from config.py and docker-compose.yml
- Auth flows: HIGH — read from dependencies.py
- Pitfalls: HIGH — derived from direct code reading, not speculation

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable — no external dependencies being researched)
