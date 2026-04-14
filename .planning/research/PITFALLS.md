# Pitfalls Research

**Domain:** MongoDB backup download endpoint — FastAPI + pymongo async + HTMX 2.0.4 + Docker Compose
**Researched:** 2026-04-13
**Confidence:** HIGH (all critical pitfalls verified against official FastAPI docs, HTMX GitHub issues, Python changelog, and code inspection of this project's existing `app/backup/dump.py`)

---

## Summary

This milestone adds a "Download Backup" button to the existing admin UI. The feature looks simple
but sits at the intersection of four integration layers — each with a non-obvious failure mode:

1. **HTMX** intercepts every `hx-*` triggered request and attempts a DOM swap. Binary file
   responses cannot be swapped; HTMX silently discards them. The button must use a plain anchor
   or a `window.location` redirect, not an `hx-get`.

2. **Asyncio / FastAPI** event loop blocking. The existing `run_backup()` in `app/backup/dump.py`
   uses synchronous `gzip.open` writes inside an `async def`. In the scheduled CLI context this is
   fine. Inside a FastAPI request handler it blocks every concurrent request for the duration of
   the backup.

3. **Memory** — `run_backup()` calls `to_list(length=None)` on every collection, materialising the
   entire database in RAM before writing a single byte. For the logbook's expected scale (~10k QSO
   records) this is acceptable today but will silently fail if the operator imports an ADIF archive.

4. **Auth** — the backup file contains every collection including `users` (hashed passwords,
   callsigns, roles). Any authentication gap on the download endpoint is a complete data dump.

The most dangerous pitfall is the HTMX binary response one: it produces no error, no 5xx, no
console output — the button just appears to do nothing. The developer will likely waste hours
debugging the server before realising the client is the problem.

---

## Critical Pitfalls

### Pitfall 1: HTMX Intercepts the Binary Response — Download Never Starts

**What goes wrong:**
The admin presses "Download Backup." Nothing happens. No download dialog appears. No error. The
server correctly generates the `.gz` file and sends it with `Content-Disposition: attachment`, but
HTMX has intercepted the XHR response and attempted a DOM swap. Binary data is not valid HTML; HTMX
discards it silently. `hx-swap="none"` does not help — the response still travels through HTMX's
XHR pipeline and cannot trigger the browser's native download handler.

**Why it happens:**
HTMX replaces the browser's default request behaviour with XHR (XMLHttpRequest). The browser's
native file-download mechanism — the one that opens a "Save As" dialog — is only triggered for
top-level navigations (full-page requests), not for XHR responses. HTMX issue #474 (raised 2021,
closed without native support) confirmed that respecting `Content-Disposition: attachment` in XHR
is architecturally out of scope for HTMX.

This is confirmed by the HTMX maintainers in GitHub Discussion #2741: "HTMX can't return a file
directly — a full request is needed to get a file."

**How to avoid:**
Do not use any `hx-*` attribute to trigger the download. Use one of:

- **Option A (simplest):** A plain `<a href="/admin/ui/backup/download" download>` anchor tag.
  The browser navigates directly; auth cookie is sent automatically. No JavaScript needed.
- **Option B (with spinner feedback):** Use `hx-get` to a *trigger* endpoint that responds with
  an `HX-Redirect` header pointing to the download URL. The browser follows the redirect as a
  full-page navigation and the download starts. The HTMX request shows a loading state; the
  redirect delivers the file.
- **Option C:** An inline `<script>` that sets `window.location.href` to the download URL on
  button click. The navigation is a full request; the cookie is included.

In all cases, the actual file-serving endpoint must be a standard GET, protected by
`require_admin_cookie`, and return `FileResponse` or `StreamingResponse` with the correct headers.

**Warning signs:**
- The backup button uses `hx-get="/admin/ui/backup/download"` or `hx-post="..."`.
- The download endpoint returns `StreamingResponse` with `Content-Disposition: attachment` but
  the button is an HTMX-wired element.
- Console shows no network error; server logs show the request completed 200; browser shows nothing.
- `hx-swap="none"` was added to "fix" the no-swap, but download still does not start.

**Phase to address:** Backup UI implementation — design the button as a plain anchor or
window.location redirect before writing any server-side handler.

---

### Pitfall 2: Blocking the Asyncio Event Loop with Synchronous gzip I/O

**What goes wrong:**
The backup endpoint calls `run_backup()` directly from an `async def` FastAPI route handler.
`run_backup()` in `app/backup/dump.py` uses `gzip.open(path, "wt")` — a synchronous, blocking
file write. While the gzip write runs (potentially several seconds for a large database), the
entire uvicorn event loop is blocked. No other request — including health checks, admin UI page
loads, and any concurrent operator request — can be served until the write completes.

**Why it happens:**
`async def` in FastAPI does not mean "run in a thread." It means "run in the event loop." Any
call to a synchronous blocking function inside `async def` — including `gzip.open`, standard
`open()`, and `time.sleep()` — occupies the loop. FastAPI's documentation explicitly states:
"If you are calling a blocking library, use `run_in_threadpool` or `asyncio.to_thread`."

The existing `run_backup()` was designed for the CLI (`python -m app.backup`) and the APScheduler
scheduler, both of which run their own event loops and are not shared with uvicorn. Calling the
same function from a uvicorn async route handler changes its blocking profile.

**How to avoid:**
Wrap the synchronous parts of `run_backup()` in `asyncio.to_thread()` (Python 3.9+):

```python
import asyncio

@ui_router.get("/backup/download")
async def download_backup(_user: User = Depends(require_admin_cookie)):
    path = await asyncio.to_thread(run_backup_sync, settings)
    return FileResponse(path, filename=path.name, media_type="application/gzip",
                        headers={"Content-Disposition": f'attachment; filename="{path.name}"'})
```

Or refactor `run_backup()` to use `aiofiles` for the gzip write so it can remain in the async
context without blocking. The MongoDB reads (`to_list`) are already async via pymongo's async
driver and do not block.

**Warning signs:**
- `run_backup()` (or any function that calls `gzip.open`) is awaited directly in an `async def`
  route handler without `asyncio.to_thread` or `run_in_threadpool`.
- The admin UI becomes unresponsive for several seconds after pressing "Download Backup."
- A uvicorn warning appears: "Blocking operation detected in async context."
- Integration test shows other endpoints returning 503 or timing out during a backup.

**Phase to address:** Backup endpoint implementation — wrap sync I/O before wiring the route.

---

### Pitfall 3: Auth Not Applied to the Download Endpoint (Complete Data Exposure)

**What goes wrong:**
The backup `.gz` file contains every MongoDB collection, including `users` (hashed passwords via
bcrypt, usernames, callsigns, roles). An unauthenticated or insufficiently-authorised request to
the download endpoint returns the full database dump.

**Why it happens:**
Three specific failure modes for this project:

1. **Wrong dependency:** The developer uses `require_admin` (Bearer JWT) instead of
   `require_admin_cookie` (HttpOnly cookie). The admin UI uses cookie auth. A route guarded by
   `require_admin` will raise HTTP 401 for every browser-initiated download because the browser
   sends the cookie, not a Bearer header.

2. **Missing dependency altogether:** The endpoint is added to `ui_router` without a `Depends`
   guard. It works in testing because the developer is logged in, but an unauthenticated path is
   left open.

3. **Auth exception handler intercepts:** `admin_main.py` has a global exception handler that
   redirects 401/403 for `/admin/ui/` paths to `/admin/ui/login`. If the download endpoint
   raises 401 due to wrong dependency type, the browser follows the redirect, the developer sees
   the login page, and incorrectly concludes "auth is working" — but the redirect means the auth
   failure is being silently swallowed for non-browser clients.

**How to avoid:**
- Apply `_user: User = Depends(require_admin_cookie)` to the download route — same dependency
  used on all other `ui_router` routes.
- Write an explicit unauthenticated-access test: clear cookies, request `/admin/ui/backup/download`,
  assert HTTP 302 redirect to `/admin/ui/login` (not 200).
- Never use `require_admin` (Bearer) on any route under `ui_router` — that router is browser-only,
  cookie-auth only.
- Verify with `curl -v http://localhost:8001/admin/ui/backup/download` (no cookie) — must return
  302, not 200 or any file content.

**Warning signs:**
- The download route uses `Depends(require_admin)` instead of `Depends(require_admin_cookie)`.
- Accessing the download URL in a private browser window (no cookies) returns a file or a 200.
- No automated test for unauthenticated access to the download endpoint.
- The route is defined in `ui_router` but has no `Depends` at all.

**Phase to address:** Backup endpoint implementation — apply auth guard as the first line of the
route handler, before any other logic.

---

### Pitfall 4: `to_list(length=None)` Loads Entire Database into RAM

**What goes wrong:**
`run_backup()` in `app/backup/dump.py` (line 35) calls `await db[coll_name].find({}).to_list(length=None)`
for every collection. This materialises every document from every collection into a Python list in
memory before writing a single byte. For a logbook with 50,000 QSO records at ~500 bytes each,
that is ~25 MB in RAM per collection — acceptable. But if an operator imports a large ADIF file
(ARRL Contest exports can exceed 100,000 QSOs at 1–2 KB each), the RAM footprint is 100–200 MB
for the `qso` collection alone, plus the overhead of BSON-to-Python-dict conversion and the
intermediate EJSON string before gzip compression. Peak RAM during backup can easily reach 3–5x
the raw collection size.

**Why it happens:**
`to_list(length=None)` is the simplest cursor-to-list call in pymongo/motor. The existing
implementation was written for correctness and simplicity, not memory efficiency. The scheduled
backup at 02:00 UTC is fine — it runs in isolation. The download endpoint hits the same code
path during normal operating hours with users active.

**How to avoid:**
Replace `to_list(length=None)` with an `async for` cursor iteration that writes one document at a
time to the gzip stream:

```python
async with gzip.open(backup_path, "wt", encoding="utf-8") as gz:
    async for doc in db[coll_name].find({}):
        gz.write(dumps({"collection": coll_name, "doc": doc}, ...) + "\n")
```

This keeps RAM usage proportional to one document at a time rather than the entire collection.
Note: `gzip.open` in `"wt"` mode buffers internally (~64 KB), so the write calls are not
individually expensive even though they happen per-document.

**Warning signs:**
- `to_list(length=None)` appears in the backup code path that serves the HTTP download endpoint.
- The admin container's RSS memory spikes sharply (use `docker stats`) when backup is triggered.
- Large ADIF imports cause the download endpoint to return 500 or timeout.
- The scheduled backup succeeds but the on-demand download fails with `MemoryError` in logs.

**Phase to address:** Backup endpoint implementation — evaluate whether to refactor `run_backup()`
or provide a separate streaming path for the on-demand download.

---

### Pitfall 5: `datetime.utcnow()` in Filenames — Deprecated in Python 3.12

**What goes wrong:**
`run_backup()` uses `datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')` to generate the filename
(e.g., `20260413T143000Z.gz`). Python 3.12 (the version in this project's Dockerfile) emits a
`DeprecationWarning` for `datetime.utcnow()` and it is scheduled for removal in a future Python
version. The filename suffix `Z` incorrectly implies an RFC 3339 UTC-aware datetime but the object
returned by `utcnow()` is timezone-naive (no `tzinfo`), which can produce incorrect results in
any code that does datetime arithmetic on the value.

**Why it happens:**
`utcnow()` has been in the standard library since Python 2.3. Its deprecation in 3.12 is recent
and many tutorials and examples still use it. The issue is not a bug today but a forward
compatibility problem: the `DeprecationWarning` already appears in Python 3.12 logs and the
function will be removed in Python 3.14 or later.

**How to avoid:**
Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` throughout the backup module:

```python
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
```

The strftime output is identical; the object is now timezone-aware. This change is confined to
`app/backup/dump.py` — one line.

**Warning signs:**
- `DeprecationWarning: datetime.utcnow() is deprecated` appears in Docker logs during backup.
- `app/backup/dump.py` imports `datetime` and calls `.utcnow()` anywhere.
- Python version in Dockerfile is 3.12 or higher (already the case).

**Phase to address:** Backup endpoint implementation — fix alongside the endpoint work; it is a
one-line change in the shared `run_backup()` function.

---

### Pitfall 6: Content-Disposition Header Format Errors Prevent Download Dialog

**What goes wrong:**
The browser receives the response but does not open a download dialog. The file either opens
inline in the browser (displayed as garbled binary) or the browser ignores the header and treats
the response as a page navigation. Alternatively, the filename in the download dialog is wrong
(e.g., `"20260413T143000Z.gz"` with literal quote characters in the filename, or `download`
as the generic filename).

**Why it happens:**
Three common mistakes:

1. `Content-Disposition: attachment; filename=20260413T143000Z.gz` — no quotes around the
   filename. RFC 6266 requires the filename to be quoted when it contains special characters.
   Although letters, digits, hyphens, and underscores technically do not require quoting, many
   browsers behave inconsistently without quotes.

2. `Content-Disposition: attachment; filename="20260413T143000Z.gz"` — correct format, but if
   the header is set via a FastAPI response `headers=` dict that is overridden by
   `GZipMiddleware`, the middleware may strip or replace it.

3. Using `StreamingResponse` with `media_type="application/gzip"` but omitting
   `Content-Disposition` entirely — the browser receives binary data with no instruction to save
   it and either shows gibberish or triggers a MIME-type download with a generic filename.

**How to avoid:**
Use `FileResponse` for files already written to disk (the current `run_backup()` approach). It
handles `Content-Length`, `Last-Modified`, and `ETag` automatically. Set the filename explicitly:

```python
from fastapi.responses import FileResponse

return FileResponse(
    path=str(backup_path),
    media_type="application/gzip",
    filename=backup_path.name,  # FastAPI sets Content-Disposition: attachment; filename="..."
)
```

`FileResponse`'s `filename` parameter automatically produces a correctly-formatted
`Content-Disposition: attachment; filename="..."` header. Do not manually construct the header
unless you need non-ASCII characters (which require RFC 5987 `filename*` encoding).

Verify after implementation: `curl -I http://localhost:8001/admin/ui/backup/download` (with cookie)
must show `content-disposition: attachment; filename="20260413T143000Z.gz"`.

**Warning signs:**
- Browser opens the `.gz` file inline or shows binary content instead of a dialog.
- The download filename is `download` instead of the timestamped name.
- The `Content-Disposition` header is absent from `curl -I` output.
- `GZipMiddleware` is present in `admin_main.py` (it would interfere with a `StreamingResponse`).

**Phase to address:** Backup endpoint implementation — verify headers with `curl -I` before closing
the phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Call `run_backup()` directly in async route (no `asyncio.to_thread`) | No refactoring needed | Blocks event loop; all admin requests stall during backup generation | Never for a production route; acceptable only in a CLI/scheduler context |
| `to_list(length=None)` for all collections | Simple, one-liner | RAM spike proportional to database size; can exhaust container memory on large imports | Acceptable for scheduled backup (isolated); unacceptable for on-demand HTTP download |
| Serve the backup from a pre-generated file on disk (keep the scheduled dump path) | Reuses existing infrastructure; no streaming complexity | File may be stale (hours old); disk space accumulates if old backups are not pruned | Acceptable as V1 for a logbook with a small number of operators; add pruning logic |
| No expiry / one-time token for the download URL | Simpler auth (same cookie-based guard as the rest of the UI) | If the admin copies the URL and shares it, the file is accessible to anyone with a valid admin session | Acceptable — the download URL is session-scoped via `require_admin_cookie`; that is sufficient |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| HTMX + binary response | Use `hx-get` or `hx-post` to trigger download | Use `<a href="..." download>` or `window.location.href`; no HTMX attributes on the download trigger |
| FastAPI + `FileResponse` + `GZipMiddleware` | `GZipMiddleware` re-compresses an already-gzip file, corrupting it | Do not add `GZipMiddleware` to `admin_main.py`; the `.gz` file is already compressed |
| pymongo async + gzip sync write | Calling `gzip.open` inside `async def` without offloading | Wrap in `asyncio.to_thread()` or use `aiofiles` for the write loop |
| `require_admin` vs `require_admin_cookie` | Using Bearer-JWT dependency on a browser download route | All `ui_router` routes must use `require_admin_cookie` — browser sends cookie, not Bearer header |
| Docker Compose hostname | If `mongodump` were used, connecting to `mongodb:27017` requires the Docker Compose network — not localhost | The existing Python-native `run_backup()` avoids this entirely by using the pymongo URI from `settings.mongodb_uri`, which already uses the correct hostname |
| `datetime.utcnow()` deprecation | Generates a `DeprecationWarning` on Python 3.12+ in every backup run | Replace with `datetime.now(timezone.utc)` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Synchronous gzip write blocking event loop | Admin UI unresponsive for backup duration; 30s+ latency on other endpoints | Wrap in `asyncio.to_thread()`; or refactor to aiofiles | Immediately on any backup request; worse as DB grows |
| `to_list(length=None)` on large collections | Container OOM kill (`docker stats` shows RAM spike); 500 error on download | Stream documents via `async for` cursor iteration | ~50k QSOs (~25 MB) is manageable; 200k+ QSOs can exceed container RAM limit |
| Multiple concurrent backup requests | Two admins pressing download simultaneously doubles memory and disk usage | Add a simple in-memory lock (`asyncio.Lock`) or check for in-progress backup before starting | Immediately with two concurrent admin sessions |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| No auth on download endpoint | Complete database dump (all users, hashed passwords, all QSOs) accessible without login | Apply `Depends(require_admin_cookie)` to the route; write an unauthenticated test |
| Wrong auth dependency (`require_admin` instead of `require_admin_cookie`) | Browser cannot authenticate (no Bearer header); 401 is silently swallowed by the app exception handler redirect; appears to work but is a no-op guard | Use `require_admin_cookie` exclusively on all `ui_router` routes |
| Backup file left world-readable on disk | If the `backups/` volume is ever exposed via a static file server or a misconfigured volume mount, files are readable without auth | Keep `backup_dir` outside the `static/` directory tree; verify `StaticFiles` mount in `admin_main.py` does not cover `backups/` |
| Unbound backup accumulation | Disk fills up silently; Docker volume exhaustion causes container failure | Add backup pruning (keep last N files) or delete the on-demand file after streaming |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No feedback while backup generates | Admin presses button, nothing happens for 5–30s; assumes the button is broken and presses again (double backup) | Show a loading spinner or disable the button on click; re-enable on completion |
| Download starts immediately but file is corrupt | Admin gets a `.gz` that gunzip rejects — no error was visible | Verify with a smoke test: `gunzip -t <file>` and `wc -l <file>` after generation; surface server errors as a toast |
| Stale backup served (pre-generated file) | Admin downloads a "backup" that is 23 hours old without knowing it | Display the backup file's timestamp prominently near the button; include it in the filename (already done) |
| No confirmation that backup is "complete" | Admin does not know if the download represents the current database state | After download completes, show a toast with the timestamp and approximate size |

---

## "Looks Done But Isn't" Checklist

- [ ] **HTMX not used for download:** The backup button is a plain `<a>` or uses `window.location`, not `hx-get`/`hx-post`. Verify in the template source.
- [ ] **Auth guard present and correct:** Route has `Depends(require_admin_cookie)`. Verify with `curl -v` (no cookie) → must return 302, not 200.
- [ ] **Content-Disposition header correct:** `curl -I` (with valid cookie) shows `content-disposition: attachment; filename="20260413T143000Z.gz"` (exact format, no stray quotes in filename).
- [ ] **File is a valid gzip:** After download, run `gunzip -t <downloaded-file>` — must exit 0.
- [ ] **Event loop not blocked:** While backup runs, load `/admin/ui/users` in another tab — must respond in under 1 second.
- [ ] **`utcnow()` removed:** `grep -r "utcnow" app/backup/` returns nothing.
- [ ] **Unauthenticated access test exists:** A test (or manual `curl` verification) confirms the download URL returns 302 without a valid admin cookie.
- [ ] **No GZipMiddleware on the admin app:** `grep "GZipMiddleware" app/admin_main.py` returns nothing.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| HTMX intercepts download (silent no-op) | LOW | Replace `hx-get` attribute with `href` on an anchor tag; remove HTMX attributes from the button element |
| Event loop blocking discovered post-deploy | LOW | Wrap `run_backup()` call in `asyncio.to_thread()`; redeploy; no data migration needed |
| Auth gap found after deployment | HIGH (data already potentially exposed) | Rotate all user passwords immediately; add `Depends(require_admin_cookie)` to route; redeploy; audit access logs |
| Memory OOM during backup | MEDIUM | Refactor `to_list(length=None)` to `async for` cursor; redeploy; adjust Docker container memory limit as temporary guard |
| Corrupt download (bad Content-Disposition) | LOW | Switch to `FileResponse(filename=...)` and remove any manual header construction; re-test with `curl -I` |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| HTMX binary response interception | Backup UI implementation — design button as plain anchor | Template source has no `hx-*` on download trigger; download dialog appears on click |
| Asyncio event loop blocking | Backup endpoint implementation — wrap sync I/O | Load admin users page while backup generates; response time under 1s |
| Auth bypass on download endpoint | Backup endpoint implementation — apply auth guard first | `curl -v` (no cookie) → 302; `curl -v` (with cookie) → 200 + file |
| RAM exhaustion from `to_list(length=None)` | Backup endpoint implementation — evaluate streaming vs. bulk | `docker stats` shows stable RAM during backup; large ADIF import does not OOM |
| `datetime.utcnow()` deprecation | Backup endpoint implementation — one-line fix | `grep -r "utcnow" app/backup/` returns nothing; no DeprecationWarning in logs |
| Content-Disposition header format | Backup endpoint implementation — use FileResponse.filename | `curl -I` shows correctly formatted header; file opens with correct name |

---

## Sources

- [HTMX issue #474: respect content-download headers — closed without native support](https://github.com/bigskysoftware/htmx/issues/474) — HIGH confidence (official HTMX repo, maintainer response)
- [HTMX Discussion #2741: how to download a file the HTMX way](https://github.com/bigskysoftware/htmx/discussions/2741) — HIGH confidence (official HTMX repo)
- [FastAPI custom responses — FileResponse, StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/) — HIGH confidence (official FastAPI docs)
- [FastAPI concurrency and async/await — blocking I/O guidance](https://fastapi.tiangolo.com/async/) — HIGH confidence (official FastAPI docs)
- [Python 3.12 datetime.utcnow() deprecation — DeprecationWarning](https://andreas.scherbaum.la/post/2024-08-05_deprecationwarning-datetime-datetime-utcnow-is-deprecated-and-scheduled-for-removal-in-a-future-version-use-timezone-aware-objects-to-represent-datetimes-in-utc-datetime-datetime-now-datetime-utc/) — HIGH confidence (aligns with Python 3.12 changelog)
- [FastAPI GZipMiddleware does not compress StreamingResponse — issue #4739](https://github.com/fastapi/fastapi/issues/4739) — HIGH confidence (FastAPI GitHub)
- [PyMongo cursor to_list memory risk — official PyMongo docs and community discussion](https://pymongo.readthedocs.io/en/stable/api/pymongo/cursor.html) — HIGH confidence (official pymongo docs)
- [FastAPI difference between run_in_executor and run_in_threadpool — Sentry](https://sentry.io/answers/fastapi-difference-between-run-in-executor-and-run-in-threadpool/) — MEDIUM confidence (verified against FastAPI docs)
- Project source: `app/backup/dump.py` — code inspection, HIGH confidence
- Project source: `app/admin/ui_router.py` — auth pattern verification, HIGH confidence
- Project source: `app/auth/dependencies.py` — `require_admin` vs `require_admin_cookie` distinction, HIGH confidence
- Project source: `docker-compose.yml` — container topology and volume mounts, HIGH confidence

---
*Pitfalls research for: MongoDB backup download endpoint — FastAPI + pymongo async + HTMX 2.0.4 + Docker*
*Researched: 2026-04-13*
