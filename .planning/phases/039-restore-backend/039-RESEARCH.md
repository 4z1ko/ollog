# Phase 39: Restore Backend - Research

**Researched:** 2026-04-14
**Domain:** FastAPI — file upload, gzip validation, EJSON decode, sync/async MongoClient, HTMX fragment responses
**Confidence:** HIGH

## Summary

Phase 39 implements a two-endpoint restore API in `app/backup/restore.py` + `app/admin/ui_router.py`. The work mirrors `dump.py` exactly for the sync/async split: a synchronous `_restore_from_file(backup_path, settings)` that uses `MongoClient` (not Beanie) wrapped by an `async run_restore(backup_path, settings)` that calls `asyncio.to_thread`. All architecture decisions are fully locked by the phase description and are verified against the actual codebase.

The critical implementation detail is EJSON decoding: backup files are written using `bson.json_util.dumps` with `CANONICAL_JSON_OPTIONS`, which serializes ObjectId as `{"$oid": "..."}` and datetime as `{"$date": {"$numberLong": "..."}}`. Standard `json.loads` would restore these as plain dicts, breaking `_id` integrity. `bson.json_util.loads` must be used — it restores ObjectId, datetime, and all other BSON types correctly. Documents returned by `bson.json_util.loads` are insert-ready for `collection.insert_many()` without further transformation.

The confirm endpoint's password check is simpler than it appears: `require_admin_cookie` already returns a `User` document with `hashed_password` attached. No separate DB lookup is needed — just call `verify_password(password, current_user.hashed_password)` directly on the dependency-injected user. The `temp_path` hidden form field requires a path traversal guard: validate that the resolved path is within `tempfile.gettempdir()` before accessing it.

**Primary recommendation:** Mirror `dump.py` exactly for `restore.py` structure. Use `bson.json_util.loads` (not `json.loads`) for every line in the backup file. Validate `temp_path` with `pathlib.Path.resolve()` + startswith check against `tempfile.gettempdir()` before file access.

## Standard Stack

### Core (all already present in project — no new dependencies)

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `pymongo` (sync `MongoClient`) | 4.16.0 | Sync DB operations in `_restore_from_file` | Same pattern as `_write_backup` in dump.py — sync MongoClient inside asyncio.to_thread avoids event loop blocking |
| `bson.json_util.loads` | via pymongo | Deserialize EJSON backup lines with type restoration | `json.loads` would return `{"$oid": "..."}` dicts; `bson.json_util.loads` restores `ObjectId`, `datetime`, etc. |
| `asyncio.to_thread` | stdlib | Wrap sync `_restore_from_file` for async callers | Exact mirror of how `run_backup` wraps `_write_backup` |
| `gzip` | stdlib | Read/validate `.gz` files in upload endpoint | `gzip.open(path, 'rt')` for validation; same module used in `dump.py` |
| `tempfile.NamedTemporaryFile` | stdlib | Persist uploaded bytes between the two POST requests | `delete=False, suffix='.gz'` so file persists after context exit |
| `pathlib.Path` | stdlib | Path validation and manipulation | Used for path traversal guard on `temp_path` |
| `json` | stdlib | First-line NDJSON check in upload validation | `json.loads(first_line)` to check `"collection"` and `"doc"` keys |

### Already-used project imports (no additions needed)

| Import | Location | Used For |
|--------|----------|---------|
| `from app.auth.dependencies import require_admin_cookie` | `ui_router.py` | Auth guard on both restore endpoints |
| `from app.auth.service import verify_password` | `ui_router.py` (already imported) | Password check in confirm endpoint |
| `from app.backup.dump import run_backup` | `ui_router.py` | Auto-backup before restore |
| `from app.config import settings` | Already in router via lazy import | MongoClient URI and DB name |
| `fastapi.UploadFile` | Already imported in adif router | Receive `.gz` file upload |
| `fastapi.Form` | Already in `ui_router.py` | Receive `password` + `temp_path` form fields |

**No `pip install` required.** All libraries are present.

## Architecture Patterns

### Module Structure

```
app/backup/
├── dump.py         (existing — do not modify)
├── restore.py      (NEW — mirrors dump.py structure exactly)
├── upload.py       (existing)
└── scheduler.py    (existing)

app/admin/
└── ui_router.py    (MODIFY — add two POST routes in new Restore section)

templates/admin/
└── restore/        (NEW directory — fragment templates)
    ├── upload_error.html     (VAL-03: inline error for bad file)
    ├── password_modal.html   (AUTH-01/02: modal with hidden temp_path field)
    ├── password_error.html   (AUTH-03: inline error inside modal)
    ├── restore_success.html  (OPS-03: success banner with backup filename)
    └── restore_failure.html  (OPS-04: error banner with backup filename)
```

### Pattern 1: Sync/Async Split (mirror of dump.py exactly)

**What:** Sync function does blocking I/O; async wrapper uses `asyncio.to_thread`.
**When to use:** Any MongoDB operation that must run on a sync `MongoClient` within FastAPI's async event loop.

```python
# Source: app/backup/dump.py — exact pattern to mirror

def _restore_from_file(backup_path: str, settings) -> None:
    """Sync helper: drop all collections and restore from gzip NDJSON backup.

    Uses a synchronous MongoClient so it can be called inside asyncio.to_thread
    without blocking the event loop.
    """
    from bson.json_util import loads as bson_loads
    import gzip
    from pathlib import Path

    client = MongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]

    # Group records by collection name (read entire file first)
    docs_by_collection: dict[str, list] = {}
    with gzip.open(backup_path, "rt", encoding="utf-8") as gz:
        for line in gz:
            line = line.strip()
            if not line:
                continue
            record = bson_loads(line)
            coll = record["collection"]
            doc = record["doc"]
            docs_by_collection.setdefault(coll, []).append(doc)

    try:
        # Drop each collection and reinsert
        for coll_name, docs in docs_by_collection.items():
            db[coll_name].drop()
            if docs:
                db[coll_name].insert_many(docs, ordered=False)
    finally:
        client.close()


async def run_restore(backup_path: str, settings) -> None:
    """Async orchestrator: run restore in a thread pool."""
    await asyncio.to_thread(_restore_from_file, backup_path, settings)
```

### Pattern 2: Upload Endpoint with Validation

**What:** Receives UploadFile, writes to tempfile, validates, returns modal or error fragment.
**When to use:** Two-phase file-based workflows where the file must persist between requests.

```python
# Source: derived from app/adif/router.py UploadFile pattern + dump.py gzip usage

@ui_router.post("/restore/upload", response_class=HTMLResponse)
async def restore_upload(
    request: Request,
    file: UploadFile,
    _user: User = Depends(require_admin_cookie),
):
    raw = await file.read()

    # Write to tempfile (persists after context exit due to delete=False)
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".gz")
    try:
        tmp.write(raw)
        tmp.close()
        temp_path = tmp.name

        # Validate: gzip decompressibility + NDJSON structure
        try:
            import gzip, json
            with gzip.open(temp_path, "rt", encoding="utf-8") as gz:
                first_line = gz.readline()
            record = json.loads(first_line)
            if "collection" not in record or "doc" not in record:
                raise ValueError("Missing required keys")
        except (OSError, EOFError, ValueError):
            os.unlink(temp_path)
            return templates.TemplateResponse(
                request, "admin/restore/upload_error.html",
                {"error": "Invalid backup file: not a valid ollog backup"},
                status_code=200,  # HTMX requires 200 for swap
            )

        # Validation passed: return modal with temp_path embedded
        return templates.TemplateResponse(
            request, "admin/restore/password_modal.html",
            {"temp_path": temp_path},
        )
    except Exception:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
        raise
```

### Pattern 3: Confirm Endpoint with Password Check + Restore

**What:** Receives form fields `password` + `temp_path`, validates path, checks password, runs backup then restore.

```python
# Source: login_submit in ui_router.py for verify_password pattern;
#         backup_download for run_backup pattern

@ui_router.post("/restore/confirm", response_class=HTMLResponse)
async def restore_confirm(
    request: Request,
    password: Annotated[str, Form()],
    temp_path: Annotated[str, Form()],
    current_user: User = Depends(require_admin_cookie),
):
    import tempfile, pathlib, os
    from app.backup.dump import run_backup
    from app.backup.restore import run_restore
    from app.auth.service import verify_password
    from app.config import settings

    # Path traversal guard — MUST run before any file access
    try:
        p = pathlib.Path(temp_path).resolve()
        tmpdir = pathlib.Path(tempfile.gettempdir()).resolve()
        if not str(p).startswith(str(tmpdir)) or p.suffix != ".gz" or not p.exists():
            raise ValueError("Invalid temp_path")
    except (ValueError, OSError):
        return HTMLResponse(content="<p>Invalid request</p>", status_code=400)

    # Password check — uses hashed_password from the cookie-authenticated user
    if not verify_password(password, current_user.hashed_password):
        return templates.TemplateResponse(
            request, "admin/restore/password_error.html",
            {"error": "Incorrect password", "temp_path": temp_path},
            status_code=200,
        )

    # Auto-backup before wipe
    try:
        auto_backup_path = await run_backup(settings)
    except Exception as exc:
        return templates.TemplateResponse(
            request, "admin/restore/restore_failure.html",
            {"error": f"Auto-backup failed: {exc}", "backup_path": None},
        )

    # Restore
    try:
        await run_restore(str(p), settings)
        return templates.TemplateResponse(
            request, "admin/restore/restore_success.html",
            {"backup_path": auto_backup_path.name},
        )
    except Exception as exc:
        return templates.TemplateResponse(
            request, "admin/restore/restore_failure.html",
            {"error": str(exc), "backup_path": auto_backup_path.name},
        )
    finally:
        if p.exists():
            os.unlink(p)
```

### Pattern 4: HTMX Fragment Response Conventions

From the existing codebase (ui_router.py, users_table.html):

- Fragment templates use `alert-error` and `alert-success` CSS classes (confirmed in `users_table.html`)
- All HTMX POST responses return HTTP 200 (HTMX 2.x does not swap on 4xx)
- Inline errors stay within the target `<div>` specified in the HTMX `hx-target` attribute
- The upload form target is a `<div id="restore-result">` or similar; modal appears inside that div
- Password error target is inside the modal itself (so modal stays open, error appears inline)

### Anti-Patterns to Avoid

- **Using `json.loads` instead of `bson.json_util.loads`:** ObjectId restores as `{"$oid": "..."}` dict, not an ObjectId. `insert_many` with wrong `_id` type causes duplicate key errors or schema violations. Always use `bson.json_util.loads`.
- **Using Beanie inside `_restore_from_file`:** Beanie is async and requires an active event loop. The sync thread pool context does not have one. Use `pymongo.MongoClient` (sync) only — exactly as `_write_backup` does.
- **Deleting the tempfile before `confirm` runs:** The upload endpoint must NOT delete the tempfile on success. It embeds the path in the modal's hidden form field. The confirm endpoint handles cleanup in a `finally` block.
- **Returning 4xx from HTMX-targeted endpoints:** HTMX 2.x ignores response body on 4xx by default. All fragment responses must return 200, even for validation errors.
- **Not cleaning up tempfile on validation failure:** The upload endpoint must `os.unlink(temp_path)` when validation fails. Only the confirm endpoint holds the reference on success.
- **Skipping the path traversal guard:** `temp_path` is a user-supplied string in a hidden form field. Without validation, a crafted request could read/delete arbitrary filesystem paths. Always resolve and check against tempdir.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| BSON/EJSON deserialization | Custom `$oid` parser | `bson.json_util.loads` | Handles ObjectId, datetime, Binary, Decimal128, Int64, all BSON types |
| Password hashing/verification | Custom Argon2 | `verify_password` from `app.auth.service` | Already implemented, tested, uses pwdlib with Argon2 |
| Async DB wrapping | Custom threading | `asyncio.to_thread` | Standard stdlib pattern; exact same approach as `run_backup` |
| Auth guard | Custom cookie parsing | `Depends(require_admin_cookie)` | Already implemented, handles expiry/invalid token/403 |
| Auto-backup | Custom dump logic | `run_backup(settings)` from `app.backup.dump` | Already implemented and tested |

**Key insight:** Every major subproblem (auth, backup, password, BSON decode) already has a solution in this codebase. Phase 39 is a wiring task, not a new-capability task.

## Common Pitfalls

### Pitfall 1: json.loads instead of bson.json_util.loads
**What goes wrong:** Documents insert with `_id` as a plain dict `{"$oid": "..."}` instead of a real `ObjectId`. MongoDB treats this as a valid document (dict is a valid BSON value), so no error is thrown at insert time. The restored database appears to work but has broken `_id` fields — all queries by `_id`, Beanie model hydration, and unique index enforcement silently malfunction.
**Why it happens:** The backup format uses CANONICAL_JSON_OPTIONS which writes extended JSON. Standard `json.loads` does not know about BSON type annotations.
**How to avoid:** Always `from bson.json_util import loads as bson_loads` and use `bson_loads(line)` for every line in the backup file.
**Warning signs:** After restore, documents have `_id: {"$oid": "..."}` (dict) instead of ObjectId when inspected in mongosh.

### Pitfall 2: Tempfile Leak on Validation Failure
**What goes wrong:** Upload endpoint writes the tempfile, validation fails, but the file is not deleted. Every failed upload leaks a `.gz` file in `/tmp`. In a long-running container, this accumulates.
**Why it happens:** The `delete=False` flag on `NamedTemporaryFile` means Python never auto-deletes it.
**How to avoid:** In the upload endpoint, call `os.unlink(temp_path)` in the validation failure branch before returning the error fragment.
**Warning signs:** Growing number of `.gz` files in `/tmp` after failed uploads.

### Pitfall 3: Gzip Exception Surface
**What goes wrong:** Only `gzip.BadGzipFile` is caught, but truncated/corrupt gzip files raise `EOFError`. The `EOFError` propagates as a 500 instead of showing the user a validation error.
**Why it happens:** Gzip can fail in two distinct ways: bad magic bytes (`BadGzipFile` which is an `OSError`) and premature EOF (`EOFError`).
**How to avoid:** Catch `(OSError, EOFError, ValueError)` together. `OSError` covers `BadGzipFile`, `EOFError` covers truncated files, `ValueError` covers `json.JSONDecodeError` from malformed NDJSON.
**Warning signs:** 500 errors when uploading truncated or partially corrupted gzip files.

### Pitfall 4: Missing Path Traversal Guard on temp_path
**What goes wrong:** The confirm endpoint accepts `temp_path` as a form field without validation. A crafted POST request with `temp_path=/etc/passwd.gz` causes `_restore_from_file` to attempt reading `/etc/passwd.gz` — and if that file exists, deletes it in the finally block.
**Why it happens:** Hidden form fields are client-controlled. `require_admin_cookie` only verifies identity, not the contents of form fields.
**How to avoid:** Before any file access in the confirm handler, resolve the path and verify it starts with `tempfile.gettempdir()` and has `.gz` suffix and exists. Return 400 on failure.
**Warning signs:** Able to trigger file access/deletion outside of `/tmp` by manipulating `temp_path` form field.

### Pitfall 5: Beanie Not Available in Sync Context
**What goes wrong:** Developer calls `User.find_one(...)` inside `_restore_from_file` (sync thread), which triggers an async Beanie operation without an event loop. Gets `RuntimeError: no running event loop`.
**Why it happens:** Beanie operations are coroutines. `asyncio.to_thread` runs the function in a thread where no event loop is active.
**How to avoid:** `_restore_from_file` must only use `MongoClient` (sync pymongo). All Beanie/async operations happen in the async handler before handing off to `asyncio.to_thread`. The password check is done in the async confirm handler using the already-hydrated User object from `require_admin_cookie`.

### Pitfall 6: Not Returning 200 for HTMX Error Fragments
**What goes wrong:** Upload endpoint returns 422 for validation errors. HTMX 2.x drops the response body and shows nothing in the target div. The user sees a blank result area with no error message.
**Why it happens:** Default FastAPI HTTP semantics conflict with HTMX 2.x swap behavior.
**How to avoid:** Always return `status_code=200` from HTMX-targeted endpoints, even for error fragments. Error state is communicated through the HTML fragment content, not the HTTP status code.
**Warning signs:** HTMX POST result div goes blank; browser dev tools show 4xx response but no DOM update.

## Code Examples

### EJSON Round-Trip (verified by running against project venv)

```python
# Source: verified against /Users/royco/ollog/.venv

from bson.json_util import loads as bson_loads, dumps, CANONICAL_JSON_OPTIONS
from bson import ObjectId
from datetime import datetime, timezone

# dump.py writes with CANONICAL_JSON_OPTIONS
doc = {"_id": ObjectId(), "CALL": "W1ABC", "created_at": datetime.now(timezone.utc)}
line = dumps({"collection": "qsos", "doc": doc}, json_options=CANONICAL_JSON_OPTIONS)
# Produces: {"collection": "qsos", "doc": {"_id": {"$oid": "..."}, "created_at": {"$date": {"$numberLong": "..."}}}}

# restore.py reads back with bson_loads
record = bson_loads(line)
restored_doc = record["doc"]
# restored_doc["_id"] is ObjectId (not dict)
# restored_doc["created_at"] is datetime (not dict)
# Insert-ready: collection.insert_many([restored_doc])
```

### verify_password Pattern (from ui_router.py login_submit — already used)

```python
# Source: app/admin/ui_router.py login_submit (line 61)
# The confirm endpoint uses the SAME pattern with the cookie-authenticated user

# In confirm handler:
current_user: User = Depends(require_admin_cookie)
# current_user.hashed_password is available directly — no extra DB lookup

if not verify_password(password, current_user.hashed_password):
    return templates.TemplateResponse(
        request, "admin/restore/password_error.html",
        {"error": "Incorrect password", "temp_path": temp_path},
        status_code=200,
    )
```

### Path Traversal Guard (verified by running against project venv)

```python
# Source: verified by running pathlib.Path.resolve() against /Users/royco/ollog/.venv

import tempfile, pathlib

def _validate_temp_path(temp_path: str) -> pathlib.Path:
    """Validate temp_path is within system temp directory and is a .gz file."""
    p = pathlib.Path(temp_path).resolve()
    tmpdir = pathlib.Path(tempfile.gettempdir()).resolve()
    # Note: on macOS, /var/folders/... resolves via /private/var/folders/...
    # str().startswith() handles symlinked temp directories correctly after resolve()
    if not str(p).startswith(str(tmpdir)):
        raise ValueError("temp_path not in temp directory")
    if p.suffix != ".gz":
        raise ValueError("temp_path must be a .gz file")
    if not p.exists():
        raise ValueError("temp_path does not exist")
    return p
```

### Gzip Validation Exception Set (verified)

```python
# Source: verified by testing against project venv

try:
    import gzip, json
    with gzip.open(temp_path, "rt", encoding="utf-8") as gz:
        first_line = gz.readline()
    record = json.loads(first_line)
    if "collection" not in record or "doc" not in record:
        raise ValueError("Missing required keys in backup format")
except (OSError, EOFError, ValueError):
    # OSError covers gzip.BadGzipFile (bad magic bytes)
    # EOFError covers truncated/corrupt gzip
    # ValueError covers json.JSONDecodeError and the explicit check above
    os.unlink(temp_path)
    return error_fragment(...)
```

### UploadFile → Tempfile Pattern (derived from adif/router.py)

```python
# Source: app/adif/router.py + app/qso/ui_router.py UploadFile pattern

@ui_router.post("/restore/upload", response_class=HTMLResponse)
async def restore_upload(
    request: Request,
    file: UploadFile,
    _user: User = Depends(require_admin_cookie),
):
    raw = await file.read()  # returns bytes

    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".gz")
    tmp.write(raw)
    tmp.close()
    temp_path = tmp.name
    # temp_path persists on disk after context exit (delete=False)
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Two-step: validate then confirm in one request | Two-phase: upload returns modal, confirm runs restore | Enables password confirmation UX without re-uploading the file |
| Store file content in session | Store file path in hidden form field | Stateless — no session infrastructure needed |
| Standard json.loads for BSON data | bson.json_util.loads | Required for ObjectId/datetime type fidelity |
| Direct async MongoDB in sync handler | asyncio.to_thread wrapping sync MongoClient | Avoids event loop blocking during gzip I/O and MongoDB writes |

## Open Questions

1. **Batch size for insert_many**
   - What we know: `pymongo.collection.Collection.insert_many` has no `batch_size` parameter. pymongo handles internal BSON document size limits (16MB per doc) automatically. The `ordered=False` flag allows bulk operation to continue past individual document errors.
   - What's unclear: Whether `ordered=True` (default) or `ordered=False` is safer for restore semantics. With `ordered=True`, a single bad document aborts the rest; with `ordered=False`, bad documents are skipped and the rest insert.
   - Recommendation: Use `ordered=True` (default) so any restore corruption is immediately visible as an exception rather than silently partial. The entire restore operation is wrapped in a try/except that returns the failure fragment.

2. **What happens if backup was empty (no collections)**
   - What we know: If the backup file has no lines, `docs_by_collection` is empty. The `for coll_name, docs in ...` loop does nothing. No collections are dropped, no data is inserted.
   - What's unclear: Is a zero-collection restore valid? Existing DB would remain untouched.
   - Recommendation: The phase spec says "groups records by collection name, drops each collection, inserts documents." If no records exist, nothing is dropped. This is a valid edge case — treat as success (no-op restore).

3. **HTMX target structure for the two-phase flow**
   - What we know: The upload form targets some `<div>` on the restore page. On success, that div is replaced with the password modal. The modal contains a form that targets a different div for password errors.
   - What's unclear: The exact `hx-target` / `hx-swap` structure — this is a UI concern belonging to Phase 40, but the confirm endpoint must return fragments that match what Phase 40 will wire up.
   - Recommendation: The backend endpoints return named fragment templates. Phase 40 decides which divs are targets. The confirm endpoint should return complete self-contained fragments for success/failure/password-error that Phase 40 can target anywhere.

## Sources

### Primary (HIGH confidence)
- `/Users/royco/ollog/app/backup/dump.py` — exact sync/async split pattern, MongoClient usage, gzip.open, CANONICAL_JSON_OPTIONS
- `/Users/royco/ollog/app/auth/service.py` — `verify_password(plain, hashed) -> bool` signature (lines 18-20), pwdlib Argon2
- `/Users/royco/ollog/app/auth/dependencies.py` — `require_admin_cookie` implementation (lines 145-159), User object structure
- `/Users/royco/ollog/app/auth/models.py` — User.hashed_password field (line 18), Beanie Document
- `/Users/royco/ollog/app/admin/ui_router.py` — all existing route patterns, Form/UploadFile/Annotated imports, Jinja2Templates usage, HTMLResponse pattern
- `/Users/royco/ollog/app/adif/router.py` — UploadFile pattern (`raw = await file.read()`)
- `/Users/royco/ollog/app/qso/ui_router.py` — UploadFile in UI router context, `status_code=200` on HTMX error responses
- `/Users/royco/ollog/app/config.py` — `settings.mongodb_uri`, `settings.mongodb_db` fields
- `/Users/royco/ollog/.planning/REQUIREMENTS.md` — VAL-01/02/03, AUTH-02/03, OPS-01/02/03/04 definitions
- Python venv at `/Users/royco/ollog/.venv` — runtime verification of `bson.json_util.loads` EJSON round-trip, `gzip.BadGzipFile`/`EOFError` exception hierarchy, `tempfile.NamedTemporaryFile(delete=False)` path behavior, path traversal guard correctness

### Secondary (MEDIUM confidence)
- `/Users/royco/ollog/templates/admin/users_table.html` — `alert-error`, `alert-success` CSS class usage in fragment templates

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries read directly from pyproject.toml and verified via project venv
- Architecture: HIGH — restore.py structure derived directly from dump.py; route patterns verified against ui_router.py
- EJSON decode: HIGH — verified via `bson.json_util.loads` round-trip test in project venv; ObjectId/datetime type restoration confirmed
- Path traversal guard: HIGH — verified `pathlib.Path.resolve()` + startswith logic in project venv
- Gzip exception surface: HIGH — verified `BadGzipFile`/`EOFError`/`JSONDecodeError` exception types in project venv
- Pitfalls: HIGH — each pitfall verified by code inspection or runtime test

**Research date:** 2026-04-14
**Valid until:** Stable — changes only if dump.py format or ui_router.py patterns change significantly
