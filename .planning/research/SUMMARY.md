# Project Research Summary

**Project:** ollog admin backup download endpoint
**Domain:** FastAPI admin sub-app — on-demand MongoDB backup download button
**Researched:** 2026-04-13
**Confidence:** HIGH

## Executive Summary

This milestone is intentionally narrow. The backup engine (`app/backup/dump.py::run_backup(settings)`) is already fully implemented, tested, and used by the scheduled backup and the CLI entry point. The entire milestone consists of three wiring steps: one new GET endpoint in `app/admin/ui_router.py`, one plain anchor tag in `templates/admin/users.html`, and one volume mount line in `docker-compose.yml`. No new Python dependencies are needed. No new files are created. The research across all four areas converges on the same conclusion: do not build anything new — plug in what already exists.

The recommended approach is to call `await run_backup(settings)` directly from the new endpoint, derive the download filename from the returned `Path.stem` (avoiding a second timestamp call), and return a `FileResponse` with `media_type="application/gzip"` and `filename=` set so FastAPI generates the correct `Content-Disposition` header automatically. Auth is applied via the existing `require_admin_cookie` dependency already used on every other admin UI route. The button in the template must be a plain `<a href>` with no HTMX attributes — HTMX intercepts XHR responses and silently discards binary content, so file downloads cannot go through HTMX.

The highest-risk pitfall is invisible: using `hx-get` on the download button produces no error, no console output, and no server-side failure — the button appears to do nothing while the server completes successfully. The second structural risk is the missing volume mount on the `admin` service, which causes backups to land in the container's ephemeral filesystem and vanish on restart. Both are caught by two verification commands after implementation: `curl -I` with a valid cookie (confirms `Content-Disposition` header) and `gunzip -t` on the downloaded file (confirms integrity).

---

## Key Findings

### Recommended Stack

All required libraries are already in `pyproject.toml`. Zero additions needed. The key technologies for this specific endpoint are `fastapi.responses.FileResponse` (serves the on-disk `.gz` file with correct headers, sets `Content-Length` automatically) and `app/auth/dependencies.require_admin_cookie` (HttpOnly cookie auth already wired to all admin UI routes). `StreamingResponse` is used elsewhere in the codebase for ADIF export but is less appropriate here because `run_backup` writes a complete file to disk before returning — `FileResponse` reads that file by path and handles all response headers correctly in one call.

The critical version constraint to preserve is `apscheduler>=3.10,<4`. APScheduler v4 removed `AsyncIOScheduler` entirely. The upper bound in `pyproject.toml` is load-bearing and must not be relaxed.

**Core technologies:**
- `fastapi[standard] >=0.135.0`: `FileResponse` and dependency injection — already installed, no change
- `pymongo >=4.16.0`: `AsyncMongoClient` used inside `run_backup`; `bson.json_util` handles EJSON serialization — already installed, no change
- `app/backup/dump.py::run_backup`: the complete backup engine — already implemented and tested
- `app/auth/dependencies::require_admin_cookie`: cookie-based admin auth — already used on all admin UI routes, applied via `Depends`
- `apscheduler >=3.10,<4`: existing scheduled backup (unchanged) — `<4` upper bound is load-bearing

See `.planning/research/STACK.md` for full rationale and version compatibility table.

### Expected Features

The feature surface is minimal. Everything in the P1 column requires zero new infrastructure — it is wiring of existing parts.

**Must have (table stakes):**
- `GET /admin/ui/backup/download` route — calls `run_backup(settings)`, returns `FileResponse` with `application/gzip` and `Content-Disposition: attachment`
- Auth gate via `require_admin_cookie` — the backup contains all collections including `users`; this is a complete data dump and must be admin-only
- Error handling — if `run_backup` raises, return an HTMX-compatible error partial (consistent with how toggle/reset errors surface in `users_table.html`)
- "Download Backup" button/link in admin UI — plain `<a href="/admin/ui/backup/download" class="btn-primary">`, no HTMX attributes

**Should have (post-launch polish):**
- Human-readable filename prefix — `ollog-backup-20260413T142301Z.gz` instead of `20260413T142301Z.gz`; trivial one-liner: `f"ollog-backup-{backup_path.stem}.gz"` in the `filename=` argument
- Last backup timestamp and file size displayed on the page — requires a secondary `GET /admin/ui/backup/status` endpoint that stats the most recent `.gz` in `backup_dir`

**Defer (v2+):**
- Backup history table (list all `.gz` files with sizes and dates) — mini file manager, disproportionate to milestone scope
- Progress bar or SSE streaming — unnecessary at hobby scale; browser tab spinner is sufficient for sub-5-second dumps
- Restore via UI — significantly more complex; belongs as a separate documented CLI tool

See `.planning/research/FEATURES.md` for full prioritization matrix and anti-feature rationale.

### Architecture Approach

No new files are required. Changes touch three existing files plus `docker-compose.yml`. The admin sub-app (`admin_main.py`, port 8001) already mounts `ui_router`; the new endpoint is an addition to that router. The template change is one card section added below the existing operator management card. The Docker change is one volume line.

**Modified components:**
1. `app/admin/ui_router.py` — add `GET /admin/ui/backup/download`; import `FileResponse`, `run_backup`, `settings`
2. `templates/admin/users.html` — add download button as plain `<a href>` with no HTMX attributes
3. `docker-compose.yml` — add `- ./backups:/app/backups` volume mount to the `admin` service

**Unchanged components (reused as-is):**
1. `app/backup/dump.py::run_backup` — called directly; no wrapper, no adapter, no modification
2. `app/auth/dependencies::require_admin_cookie` — `Depends(require_admin_cookie)` on the new route

**Recommended build order within the milestone:** docker-compose fix first (infrastructure prerequisite), then endpoint, then template button, then smoke test.

See `.planning/research/ARCHITECTURE.md` for full data-flow diagrams, code-level patterns, and anti-pattern catalog.

### Critical Pitfalls

1. **HTMX intercepts binary response — download never starts.** Using `hx-get` or `hx-post` sends the request via XHR; browsers do not act on `Content-Disposition: attachment` in XHR responses. HTMX silently discards the binary payload. No error is produced anywhere. Prevention: the button must be a plain `<a href>` with no `hx-*` attributes. Verify by clicking in the browser — the Save dialog must appear.

2. **Missing volume mount on admin service.** Without `- ./backups:/app/backups` in the `admin` service `volumes` block, `run_backup` writes to the container's ephemeral overlay filesystem. The file is served correctly within the same request but is lost on container restart, and is not co-located with scheduled backups from the `api` service. Prevention: add the volume mount before any endpoint testing.

3. **Wrong auth dependency.** The admin UI uses cookie auth (`require_admin_cookie`). Using `require_admin` (Bearer JWT) instead causes 401 on every browser download request because the browser sends a cookie, not an Authorization header. The app's exception handler then silently converts 401 to a 302 login redirect, masking the failure. Prevention: use `Depends(require_admin_cookie)` exclusively. Verify with `curl -v` (no cookie) — must return 302.

4. **Synchronous gzip I/O blocking the asyncio event loop.** `run_backup` uses `gzip.open` (synchronous) inside `async def`. In the CLI/scheduler context this is harmless. Called from a uvicorn route handler it blocks all concurrent requests for the duration of the write. Prevention: wrap the `run_backup` call in `asyncio.to_thread()` in the endpoint handler.

5. **`datetime.utcnow()` deprecation.** `run_backup` uses `datetime.utcnow()` which emits `DeprecationWarning` on Python 3.12 (already the project's runtime) and is scheduled for removal. Fix is one line in `app/backup/dump.py`: replace with `datetime.now(timezone.utc)`. Address alongside the endpoint work since the two files are touched in the same phase.

See `.planning/research/PITFALLS.md` for the full pitfall catalog, "Looks Done But Isn't" checklist, and recovery strategies.

---

## Implications for Roadmap

This milestone does not warrant multiple phases in the traditional sense — the entire scope is three file edits and one docker-compose line. The structure below presents it as one phase with ordered sub-tasks whose dependency ordering matters. A roadmapper can represent this as a single phase or as micro-tasks within a phase; either framing is correct.

### Phase 1: Infrastructure Fix (docker-compose.yml)

**Rationale:** The volume mount must exist before the endpoint is tested end-to-end in Docker. Without it, `run_backup` writes to the container's ephemeral overlay filesystem — the endpoint appears to work (file is served) but the backup does not persist and the on-demand backup is invisible to the `api` service's scheduled backup directory. Fixing infrastructure before writing code avoids a misleading debugging session.

**Delivers:** Persistent shared `./backups` volume accessible to both `api` and `admin` services.

**Addresses:** Pitfall 2 (missing volume mount).

**Change:** One `volumes` block entry in `docker-compose.yml` under the `admin` service.

---

### Phase 2: Backup Download Endpoint

**Rationale:** The route is the core deliverable. All other pieces (button, volume) support it or follow from it. Implement and verify the endpoint in isolation via `curl` before wiring the UI button.

**Delivers:** `GET /admin/ui/backup/download` — authenticated, returns a valid `.gz` file with correct `Content-Disposition` header and `Content-Type: application/gzip`.

**Addresses:** All P1 features (route, auth gate, error handling).

**Avoids:** Pitfall 3 (wrong auth dependency), Pitfall 4 (blocking event loop), Pitfall 5 (`utcnow` deprecation), Pitfall 6 (Content-Disposition format errors).

**Changes:**
- `app/admin/ui_router.py` — new endpoint with `Depends(require_admin_cookie)`, `asyncio.to_thread` wrapping `run_backup`, `FileResponse` return with `filename=f"ollog-backup-{backup_path.stem}.gz"`
- `app/backup/dump.py` — replace `datetime.utcnow()` with `datetime.now(timezone.utc)` (one line)

**Verification:** `curl -I` with valid admin cookie shows `content-disposition: attachment; filename="ollog-backup-*.gz"`; `curl -v` without cookie shows 302 redirect; `gunzip -t` on the downloaded file exits 0; loading another admin page while backup runs responds in under 1 second.

---

### Phase 3: Admin UI Button

**Rationale:** Once the endpoint is verified via `curl`, adding the browser button is a single template edit. It is decoupled from the backend and can be done last.

**Delivers:** "Download Backup" anchor visible in the admin console, triggering a browser-native file download Save dialog.

**Addresses:** P1 UI feature; Pitfall 1 (HTMX binary response interception).

**Change:** `<a href="/admin/ui/backup/download" class="btn-primary">Download Backup</a>` in `templates/admin/users.html`. No HTMX attributes whatsoever.

**Verification:** Click the button in a logged-in browser session — Save dialog appears; file downloads; `gunzip -t` on the file exits 0; clicking the button in a logged-out session redirects to `/admin/ui/login`.

---

### Phase Ordering Rationale

- Volume mount before endpoint: Docker tests require the mount or results are misleading and non-reproducible.
- Endpoint before button: `curl` can verify the endpoint independently; the button depends on the endpoint being correct first.
- Auth and event-loop fixes are tasks within the endpoint phase, not separate phases — they are part of writing the endpoint correctly, not cleanup.
- The three sub-tasks together constitute a single milestone. A roadmapper presenting this to stakeholders should describe it as one phase ("Wire the backup download button") with three ordered implementation tasks.

### Research Flags

No phases need additional research. All patterns are directly verified from the codebase and official documentation:

- `FileResponse` with `filename=` for `Content-Disposition`: HIGH confidence from FastAPI official docs.
- `require_admin_cookie` auth dependency pattern: HIGH confidence from direct code inspection of every existing admin UI route.
- HTMX binary response limitation and plain-anchor workaround: MEDIUM/HIGH confidence from HTMX maintainer confirmation in official GitHub issues; the workaround itself is unambiguous.
- Docker volume mount: HIGH confidence from direct `docker-compose.yml` inspection.
- `asyncio.to_thread` for wrapping synchronous I/O: HIGH confidence from FastAPI official concurrency docs.

Standard patterns apply throughout. No `/gsd:research-phase` calls are needed during planning.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All findings from direct codebase inspection; no unverified training-data claims; zero new dependencies |
| Features | HIGH | Codebase audited directly; HTMX file download limitation confirmed via official HTMX GitHub issues and maintainer responses |
| Architecture | HIGH | All component boundaries verified from source code; HTMX download workaround is MEDIUM confidence but the recommended approach (plain anchor) is unambiguous and verified |
| Pitfalls | HIGH | Critical pitfalls verified against official FastAPI docs, HTMX GitHub, Python 3.12 changelog, and direct project code inspection |

**Overall confidence:** HIGH

### Gaps to Address

- **Asyncio event loop blocking severity at current scale:** `run_backup` uses synchronous `gzip.open` writes. The research flags this as a pitfall requiring `asyncio.to_thread()`. At hobby scale (sub-5-second dumps), the practical impact on users is low but the architectural issue is real. The roadmapper should ensure the endpoint implementation task explicitly requires the `to_thread` wrapper rather than treating it as optional polish.

- **`to_list(length=None)` memory usage:** For the current logbook scale this is acceptable. If the station has imported a large contest ADIF file, peak RAM during backup could be significant (3-5x the raw collection size in bytes). The research recommends cursor streaming (`async for`) as the correct long-term fix but notes it requires modifying `run_backup` itself. Recommend deferring this refactor given hobby-scale datasets; revisit if a station accumulates 100k+ QSOs.

- **UX: no spinner on plain anchor:** Because the download button must be a plain `<a href>`, there is no HTMX loading indicator during backup generation. The browser's native tab spinner is the only visible feedback during the 1-5 second backup window. This is acceptable for v1 and is architecturally unavoidable given the HTMX binary response limitation. Do not plan for an HTMX spinner.

---

## Sources

### Primary (HIGH confidence)

- `/Users/royco/ollog/app/backup/dump.py` — `run_backup` signature, EJSON strategy, filename format, `utcnow` usage confirmed
- `/Users/royco/ollog/app/admin/ui_router.py` — existing endpoint patterns and `require_admin_cookie` usage confirmed
- `/Users/royco/ollog/app/auth/dependencies.py` — `require_admin_cookie` vs `require_admin` distinction; `admin_token` cookie name confirmed
- `/Users/royco/ollog/docker-compose.yml` — volume mount gap for admin service confirmed; `env_file` presence confirmed
- `/Users/royco/ollog/app/config.py` — `backup_dir`, `mongodb_uri`, `mongodb_db` settings confirmed
- `/Users/royco/ollog/Dockerfile` — `python:3.12-slim` base image; mongodump absence confirmed
- `/Users/royco/ollog/pyproject.toml` — all deps confirmed as already present; `apscheduler<4` upper bound confirmed
- `/Users/royco/ollog/docs/admin-guide/backup.md` — "no mongodump required" documented as intentional design decision
- [FastAPI custom responses — FileResponse](https://fastapi.tiangolo.com/advanced/custom-response/) — `filename=` parameter and `Content-Disposition` header behavior
- [FastAPI concurrency and async/await](https://fastapi.tiangolo.com/async/) — blocking I/O guidance; `asyncio.to_thread` recommendation
- [Python 3.12 datetime.utcnow() DeprecationWarning](https://docs.python.org/3.12/library/datetime.html) — confirmed; `datetime.now(timezone.utc)` as replacement

### Secondary (MEDIUM confidence)

- [HTMX issue #474](https://github.com/bigskysoftware/htmx/issues/474) — HTMX maintainer confirms no `Content-Disposition: attachment` support in XHR responses; closed without native support
- [HTMX discussion #2741](https://github.com/bigskysoftware/htmx/discussions/2741) — community pattern: plain anchor or two-step HTMX/redirect approach confirmed as established workaround

### Tertiary (not applicable)

All relevant decisions for this milestone are resolvable from codebase inspection and official documentation. No findings rely on inference or low-confidence sources.

---

*Research completed: 2026-04-13*
*Ready for roadmap: yes*
