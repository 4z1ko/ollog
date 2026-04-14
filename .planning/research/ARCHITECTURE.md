# Architecture Research

**Domain:** MongoDB backup download endpoint — FastAPI admin sub-app integration
**Researched:** 2026-04-13
**Confidence:** HIGH (code-verified from live codebase; HTMX download limitation MEDIUM from official issue tracker and community patterns)

---

## Summary

The admin sub-app already has a fully working backup engine (`app/backup/dump.py`) and the correct auth dependency (`require_admin_cookie`). Adding a download button requires:

1. One new GET endpoint in `app/admin/ui_router.py`
2. A plain `<a>` anchor tag in `templates/admin/users.html` (not an HTMX request)
3. A `backups` volume mount added to the `admin` service in `docker-compose.yml`

HTMX cannot handle binary responses. The download must be a plain browser GET, not an HTMX-initiated XHR. The existing `run_backup(settings)` function is called directly — no new service layer, no subprocess, no mongodump.

---

## System Overview

```
Browser (Admin UI — port 8001)
        │
        │  Admin clicks "Download Backup"
        │  <a href="/admin/ui/backup/download" class="btn-primary">
        │  (plain browser GET — bypasses HTMX entirely)
        │
        ▼
admin_main.py — FastAPI sub-app on port 8001
        │
        │  GET /admin/ui/backup/download
        │  Dependency: require_admin_cookie
        │
        ▼
get_current_admin_cookie (app/auth/dependencies.py)
        │  reads:   Cookie: admin_token=<JWT>   (sent automatically by browser)
        │  decodes: decode_access_token(admin_token)
        │  checks:  user.role == "admin"
        │  raises:  401/403 on failure (exception handler redirects to /admin/ui/login)
        │
        ▼
run_backup(settings)  (app/backup/dump.py)
        │  Creates own AsyncMongoClient(settings.mongodb_uri)
        │  Lists all collection names
        │  For each collection: find({}).to_list() → EJSON NDJSON lines → gzip
        │  Writes to /app/backups/20260413T142301Z.gz
        │  Closes client
        │  Returns Path
        │
        ▼
FileResponse(path=backup_path, media_type="application/gzip", filename=...)
        │
        │  HTTP 200
        │  Content-Type: application/gzip
        │  Content-Disposition: attachment; filename="ollog-backup-20260413T142301Z.gz"
        │  Content-Length: <bytes>
        │
        ▼
Browser opens Save dialog / saves to Downloads/
```

---

## Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `app/admin/ui_router.py` | Add `GET /admin/ui/backup/download`; apply `require_admin_cookie`; call `run_backup`; return `FileResponse` | **Modified — new endpoint** |
| `app/backup/dump.py` | Produces the `.gz` file; `run_backup(settings)` returns `Path` | **Unchanged — reused as-is** |
| `templates/admin/users.html` | Add download anchor styled as `btn-primary` — plain `<a>`, no HTMX attributes | **Modified — new button** |
| `docker-compose.yml` | Add `- ./backups:/app/backups` volume mount to `admin` service | **Modified — volume mount** |
| `app/auth/dependencies.py` | `require_admin_cookie` reads `admin_token` cookie, decodes JWT, checks `role == "admin"` | **Unchanged — reused as-is** |
| `app/config.py` | `settings.backup_dir`, `settings.mongodb_uri`, `settings.mongodb_db` already present | **Unchanged** |

---

## Recommended Project Structure

No new files required. Changes are additions to existing files only:

```
app/
├── admin/
│   └── ui_router.py          # ADD: GET /admin/ui/backup/download endpoint
├── backup/
│   └── dump.py               # UNCHANGED — run_backup() reused directly
└── auth/
    └── dependencies.py       # UNCHANGED — require_admin_cookie reused

templates/
└── admin/
    └── users.html            # MODIFIED — add download button (plain <a> anchor)

docker-compose.yml            # MODIFIED — add backups volume to admin service
```

### Structure Rationale

- **No new router file:** One endpoint does not justify a new file. All admin UI routes live in `ui_router.py`; the download endpoint belongs there.
- **No new service layer:** `run_backup(settings)` already does exactly the right thing. No wrapper, no adapter.
- **No new template partial:** The download is a browser navigation, not an HTMX swap. No partial template is involved.

---

## Architectural Patterns

### Pattern 1: Plain Anchor Tag Bypasses HTMX for File Downloads

**What:** HTMX intercepts clicks on elements with `hx-*` attributes and sends them via XHR. XHR responses with `Content-Disposition: attachment` are not acted upon by the browser — the binary data is received by the HTMX XHR machinery and then discarded because it cannot be swapped into the DOM. The download never reaches the user.

A plain `<a href="...">` with **no HTMX attributes** triggers a standard browser navigation. The browser sends the request with all cookies (including `admin_token`), receives the `Content-Disposition: attachment` response, and initiates the file save. This is the correct and complete pattern.

**When to use:** Any binary file download from an HTMX-enabled page. Never use `hx-get` or `hx-post` for endpoints that return files.

**Trade-offs:** Loses HTMX loading indicators during the backup generation (which may take 1-5 seconds for large databases). Acceptable for an infrequent admin operation. The browser's native loading indicator (tab spinner, status bar) is visible. If a loading indicator is required, the workaround is a two-step pattern: HTMX POST to start generation → server returns a link to the file → user clicks the link. This is overkill for this use case.

**Example (template):**
```html
<!-- Plain anchor — no hx-* attributes. Cookies sent automatically. -->
<a href="/admin/ui/backup/download" class="btn-primary">
  <svg class="w-4 h-4" ...><!-- download icon --></svg>
  Download Backup
</a>
```

**What NOT to do:**
```html
<!-- WRONG — HTMX receives binary response, cannot swap, download is lost -->
<button hx-get="/admin/ui/backup/download" hx-target="#result" hx-swap="innerHTML">
  Download Backup
</button>
```

**Confidence:** MEDIUM — verified via htmx/issues/474 and htmx/discussions/2741. HTMX maintainers confirmed no native Content-Disposition attachment support. Plain anchor is the established workaround across the community.

---

### Pattern 2: run_backup Creates Its Own AsyncMongoClient — Reuse Directly

**What:** `run_backup(settings)` in `dump.py` does not call `get_client()`. It opens its own `AsyncMongoClient(settings.mongodb_uri)` and closes it in a `finally` block. This was designed for the CLI context (`python -m app.backup`) where the app lifespan has not run and `get_client()` returns `None`. The same design is valid from a request handler — no special adaptation needed.

**When to use:** Call `await run_backup(settings)` directly from the endpoint handler. Do not try to inject a shared client from `get_client()`.

**Trade-offs:** Each backup request opens and closes a MongoDB connection. For an infrequent admin-only operation, this is acceptable overhead. The connection pool behavior of `AsyncMongoClient` means the actual TCP handshake may be skipped if the driver reuses an existing connection.

**Confidence:** HIGH — verified from `app/backup/dump.py` source.

---

### Pattern 3: Timestamped Filename Derived from backup_path.stem

**What:** `run_backup` writes to `Path(settings.backup_dir) / f"{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.gz"`. The `.stem` of the returned path is the ISO-format timestamp (e.g., `20260413T142301Z`). The download filename is built as `f"ollog-backup-{backup_path.stem}.gz"`.

Do not generate a second timestamp independently — that creates a race condition where the Content-Disposition filename could differ from the actual file on disk by one second.

**Example:**
```python
backup_path = await run_backup(settings)
# backup_path == Path("/app/backups/20260413T142301Z.gz")
# backup_path.stem == "20260413T142301Z"
download_name = f"ollog-backup-{backup_path.stem}.gz"
# Result: "ollog-backup-20260413T142301Z.gz"
```

**Content-Disposition header value:**
```
Content-Disposition: attachment; filename="ollog-backup-20260413T142301Z.gz"
```

**Confidence:** HIGH — derived directly from `dump.py` strftime format and Path API.

---

### Pattern 4: Auth via require_admin_cookie on the Download Endpoint

**What:** `require_admin_cookie` (already imported and used throughout `ui_router.py`) reads the `admin_token` HttpOnly cookie, decodes the JWT, and checks `user.role == "admin"`. Because the download is a plain browser GET, cookies are sent automatically — no configuration needed.

On 401/403, the exception handler in `admin_main.py` matches `path.startswith("/admin/ui/")` and returns a 302 redirect to `/admin/ui/login`. An unauthenticated download attempt redirects to login rather than returning a file or a JSON error — correct behavior.

**Example:**
```python
@ui_router.get("/backup/download")
async def download_backup(_user: User = Depends(require_admin_cookie)):
    backup_path = await run_backup(settings)
    download_name = f"ollog-backup-{backup_path.stem}.gz"
    return FileResponse(
        path=backup_path,
        media_type="application/gzip",
        filename=download_name,
    )
```

**Cookie name is `admin_token`** (not `access_token`). Verified in `dependencies.py` line 112: `admin_token: str | None = Cookie(default=None)`.

**Confidence:** HIGH — verified in `app/auth/dependencies.py` and `app/admin_main.py`.

---

### Pattern 5: FileResponse for On-Disk Files

**What:** Use `FileResponse` (from `fastapi.responses`) rather than `StreamingResponse`. `run_backup` writes the complete `.gz` file to disk before returning the path. `FileResponse` reads the file, sets `Content-Length` from the actual file size, and streams it in chunks. It also sets `Content-Disposition: attachment; filename=...` automatically when `filename=` is provided.

**When to use:** When the file exists on disk before the response starts. `StreamingResponse` is for generating bytes on-the-fly without touching disk.

**Additional import needed in ui_router.py:**
```python
from fastapi.responses import FileResponse  # add alongside HTMLResponse, RedirectResponse
from app.backup.dump import run_backup
from app.config import settings
```

**Confidence:** HIGH — FastAPI official documentation pattern.

---

## Critical Integration Constraint: Volume Mount

The `admin` service in `docker-compose.yml` has no `backups` volume mount. The `api` service does:

```yaml
# api service — has the volume
api:
  volumes:
    - ./backups:/app/backups   # present

# admin service — missing the volume
admin:
  build: .
  command: uvicorn app.admin_main:app --host 0.0.0.0 --port 8001
  ports:
    - "8001:8001"
  # NO volumes: block
```

`run_backup` writes to `settings.backup_dir` (default: `/app/backups`) and calls `mkdir(parents=True, exist_ok=True)`. Without the volume mount, it succeeds — but the file is written to the admin container's ephemeral overlay filesystem. `FileResponse` can serve it within the same request, but the file is lost on container restart, and scheduled backups from the `api` container are not visible to `admin`.

**Required fix to docker-compose.yml:**
```yaml
admin:
  volumes:
    - ./backups:/app/backups
```

This makes both containers share the same host directory. On-demand downloads from admin and scheduled backups from api land in the same place and persist across restarts.

**Confidence:** HIGH — verified from docker-compose.yml and dump.py source.

---

## Data Flow

### Happy Path: Button Click to Downloaded File

```
[Admin clicks <a href="/admin/ui/backup/download">]
        │
        │  Browser: GET /admin/ui/backup/download HTTP/1.1
        │  Host: localhost:8001
        │  Cookie: admin_token=eyJ...  (HttpOnly, sent automatically)
        │
        ▼
[admin_main.py routes to ui_router GET /admin/ui/backup/download]
        │
        ▼
[require_admin_cookie dependency]
        │  admin_token cookie present? YES
        │  decode_access_token(admin_token) → payload
        │  User.find_one({"username": payload["sub"]}) → user
        │  user.enabled? YES — user.role == "admin"? YES
        │  returns User object
        │
        ▼
[run_backup(settings)]
        │  AsyncMongoClient(settings.mongodb_uri) → connects to mongodb:27017
        │  db.list_collection_names() → ["qsos", "users", "api_tokens"]
        │  for each collection: find({}).to_list() → documents
        │  gzip.open("/app/backups/20260413T142301Z.gz", "wt") → write EJSON NDJSON
        │  client.close()
        │  returns Path("/app/backups/20260413T142301Z.gz")
        │
        ▼
[FileResponse(path, media_type="application/gzip", filename="ollog-backup-20260413T142301Z.gz")]
        │
        │  HTTP/1.1 200 OK
        │  Content-Type: application/gzip
        │  Content-Disposition: attachment; filename="ollog-backup-20260413T142301Z.gz"
        │  Content-Length: 84321
        │
        ▼
[Browser receives response — opens Save dialog or auto-saves to ~/Downloads/]
```

### Error Path: Unauthenticated Access

```
[Request with no admin_token cookie, or expired JWT]
        │
        ▼
[require_admin_cookie raises HTTP 401]
        │
        ▼
[admin_main.py exception handler]
        │  path == "/admin/ui/backup/download"
        │  path.startswith("/admin/ui/") → TRUE
        │  status_code == 401 → TRUE
        │
        ▼
[302 Redirect → /admin/ui/login]
[Browser navigates to login page — user is prompted to authenticate]
```

---

## Build Order Within the Milestone

Step 1 must come before Step 2 so that the volume mount is in place when the endpoint is tested. Step 3 can be done in any order relative to Step 2.

**Step 1 — docker-compose.yml (infrastructure prerequisite)**
Add `- ./backups:/app/backups` to the `admin` service. This is the prerequisite for the endpoint to work correctly in Docker. Without it, the endpoint functions but files are ephemeral.

**Step 2 — app/admin/ui_router.py (endpoint)**
Add `GET /admin/ui/backup/download`. Imports to add: `FileResponse` from `fastapi.responses`, `run_backup` from `app.backup.dump`, `settings` from `app.config`.

**Step 3 — templates/admin/users.html (UI)**
Add download button. A new card section below the existing operator management card is the natural location. Use a plain `<a href="/admin/ui/backup/download" class="btn-primary">` — no HTMX attributes.

**Step 4 — Smoke test**
Restart admin container, navigate to `/admin/ui/users`, click button, verify `.gz` file downloads and can be decompressed (`gunzip -c ollog-backup-*.gz | head -5`).

---

## Anti-Patterns

### Anti-Pattern 1: Using hx-get or hx-post for the Download Trigger

**What people do:** Wire the button as `<button hx-get="/admin/ui/backup/download" hx-target="#status">`.

**Why it's wrong:** HTMX sends an XHR request. The browser does not act on `Content-Disposition: attachment` in XHR responses — the binary payload is received and dropped. The file never downloads. There is no HTMX configuration that makes this work in 2.0.4.

**Do this instead:** Plain `<a href="/admin/ui/backup/download" class="btn-primary">`. No HTMX attributes. Cookies are sent automatically.

---

### Anti-Pattern 2: Calling get_client() to Obtain a MongoDB Handle

**What people do:** Inject the shared app-level client with `client = get_client()` and pass it into a custom export function.

**Why it's wrong:** `run_backup` already manages its own client lifecycle correctly and has been tested in the CLI context. Using `get_client()` would bypass that and couple the endpoint to the admin app's lifespan-managed client. If the export fails partway, exception handling against a shared client adds unnecessary risk.

**Do this instead:** Call `await run_backup(settings)` directly. It handles client creation, iteration, and cleanup.

---

### Anti-Pattern 3: Generating a Second Timestamp for the Download Filename

**What people do:**
```python
backup_path = await run_backup(settings)
ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
filename = f"ollog-backup-{ts}.gz"  # WRONG — different timestamp than the file
```

**Why it's wrong:** There is a small but real race window between when `run_backup` stamped the file and when the endpoint generates its timestamp. The Content-Disposition filename and the on-disk filename will not match.

**Do this instead:** `filename = f"ollog-backup-{backup_path.stem}.gz"`. The stem is the canonical timestamp from the actual file.

---

### Anti-Pattern 4: Using StreamingResponse to Generate Bytes On-the-Fly

**What people do:** Skip `run_backup` and write an async generator that queries MongoDB and yields gzip chunks directly as the response body.

**Why it's wrong:** If the generator fails mid-stream, the browser receives a partial `.gz` file. Partial gzip files are typically not decompressible. The user gets a corrupted download with no error message (the HTTP 200 was already sent). `run_backup` writes to disk first, giving a verifiable complete file before serving begins.

**Do this instead:** `FileResponse` after `run_backup` completes. The additional latency (disk write before serve) is negligible for typical amateur radio log sizes and provides crash safety.

---

### Anti-Pattern 5: Shelling Out to mongodump

**What people do:** Use `subprocess.run(["mongodump", ...])` to produce a BSON archive.

**Why it's wrong:** The Docker image is `python:3.12-slim` — mongodump is not installed. Installing it requires adding the MongoDB Database Tools package to the Dockerfile, adding ~50MB to the image, and pinning a separate tool version. The existing `run_backup` already uses pymongo to produce a complete, restorable EJSON NDJSON gzip archive with zero additional dependencies. There is no benefit to introducing mongodump.

**Do this instead:** `run_backup(settings)` — already implemented, already tested.

---

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `ui_router.py` → `dump.py` | Direct `await run_backup(settings)` | No service layer needed |
| `ui_router.py` → `dependencies.py` | `Depends(require_admin_cookie)` | Same dependency used by all admin UI routes |
| `admin_main.py` exception handler → login redirect | Catches 401/403 on `/admin/ui/*` | Unauthenticated download attempts → 302 to login |
| `admin` container ↔ `./backups/` host volume | `FileResponse` reads from `/app/backups/*.gz` | Requires volume mount in docker-compose.yml |
| `admin` container → MongoDB | `run_backup` opens its own `AsyncMongoClient` | Uses `settings.mongodb_uri` already configured in admin service env |

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| MongoDB | `run_backup` opens direct `AsyncMongoClient` | Same URI as rest of app — no special network config needed |
| Host filesystem | `FileResponse` serves `/app/backups/*.gz` | Requires volume mount; directory created by `run_backup` with `mkdir(parents=True, exist_ok=True)` |

---

## Sources

- `/Users/royco/ollog/app/admin_main.py` — exception handler scope (`/admin/ui/` prefix check), lifespan, sub-app structure (code verified, HIGH confidence)
- `/Users/royco/ollog/app/admin/ui_router.py` — existing endpoint pattern, `require_admin_cookie` import and usage (code verified, HIGH confidence)
- `/Users/royco/ollog/app/auth/dependencies.py` — `require_admin_cookie`, `get_current_admin_cookie`, `admin_token` cookie name (code verified, HIGH confidence)
- `/Users/royco/ollog/app/backup/dump.py` — `run_backup` signature, client lifecycle, path format from `strftime('%Y%m%dT%H%M%SZ')` (code verified, HIGH confidence)
- `/Users/royco/ollog/docker-compose.yml` — volume mounts per service, admin service definition (code verified, HIGH confidence)
- `/Users/royco/ollog/app/config.py` — `backup_dir`, `mongodb_uri`, `mongodb_db` settings (code verified, HIGH confidence)
- `/Users/royco/ollog/Dockerfile` — `python:3.12-slim` base image confirming mongodump absence (code verified, HIGH confidence)
- [htmx/issues/474](https://github.com/bigskysoftware/htmx/issues/474) — HTMX maintainer confirms no Content-Disposition attachment support; HX-Redirect and plain anchor workarounds (MEDIUM confidence)
- [htmx/discussions/2741](https://github.com/bigskysoftware/htmx/discussions/2741) — Community pattern: plain anchor or two-step HTMX → link approach (MEDIUM confidence)
- [FastAPI Custom Response docs](https://fastapi.tiangolo.com/advanced/custom-response/) — `FileResponse` usage for on-disk files (HIGH confidence)

---

*Architecture research for: MongoDB backup download endpoint — FastAPI admin sub-app*
*Researched: 2026-04-13*
