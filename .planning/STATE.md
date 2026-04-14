# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-13)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v2.0 Database Backup — admin one-click MongoDB backup download

## Current Position

Phase: 37 — Infrastructure and Backup Endpoint
Plan: Not started
Status: Roadmap created; ready for plan-phase
Last activity: 2026-04-13 — Roadmap created for v2.0 (Phases 37–38)

Progress: [ ] Phase 37 [ ] Phase 38

## Performance Metrics

**Velocity (historical):**
- Total plans completed: 47 plans across v1.0–v1.9
- Average duration: ~5–20 min/plan

**By Milestone:**

| Milestone | Phases | Plans |
|-----------|--------|-------|
| v1.0 | 1–6 | 19 |
| v1.1 | 7–10 | 7 |
| v1.2 | 11–12 | 2 |
| v1.3 | 13–15 | 8 |
| v1.4 | 16–18 | 4 |
| v1.5 | 19–22 | 4 |
| v1.6 | 23–24 | 2 |
| v1.7 | 25–28 | 4 |
| v1.8 | 29–31 | 3 |
| v1.9 | 32–36 | TBD (shipped) |
| v2.0 | 37–38 | TBD (in progress) |

## Accumulated Context

### v2.0 Critical Implementation Rules (Pitfall Prevention)

- **No HTMX on the download button:** The download anchor in `backup.html` must be a plain `<a href="/admin/ui/backup/download">` with zero `hx-*` attributes. HTMX intercepts XHR responses — `Content-Disposition: attachment` is silently ignored and the binary payload is discarded. There is no error, no console output, no server-side failure. The button appears to do nothing. Prevention: plain anchor only.
- **Volume mount before endpoint test:** Without `- ./backups:/app/backups` in the `admin` service `volumes` block, `run_backup` writes to the container's ephemeral overlay filesystem. The download works within the same request but the file vanishes on container restart. Add the mount in Phase 37 before any curl verification.
- **asyncio.to_thread is required:** `run_backup` uses synchronous `gzip.open` I/O. Called directly from an `async def` route handler it blocks all concurrent uvicorn requests for the duration of the write. Wrap with `await asyncio.to_thread(run_backup, settings)`.
- **require_admin_cookie, not require_admin:** The browser sends a cookie, not an Authorization header. Using the Bearer-JWT dependency (`require_admin`) causes 401 → silent 302 redirect to login, masking the real failure. Use `Depends(require_admin_cookie)` exclusively on the backup endpoint.
- **datetime.now(timezone.utc) in dump.py:** `datetime.utcnow()` emits DeprecationWarning on Python 3.12 and is scheduled for removal. Fix is one line in `app/backup/dump.py`. Address in Phase 37 alongside the endpoint.
- **FileResponse filename derivation:** Use `f"ollog-backup-{backup_path.stem}.gz"` in the `filename=` argument of `FileResponse`. This avoids a second `datetime.now()` call and ensures the filename matches the actual file on disk.

### v2.0 Key Architecture

- **Existing:** `app/backup/dump.py::run_backup(settings)` is fully implemented, tested, and used by the CLI and scheduler. Phase 37 is pure wiring.
- **Phase 37 touches:** `docker-compose.yml` (volume mount), `app/backup/dump.py` (utcnow fix), `app/admin/ui_router.py` (new endpoint)
- **Phase 38 touches:** `app/admin/ui_router.py` (GET /admin/ui/backup page route), `templates/admin/backup.html` (new template), admin sidebar nav in `templates/admin/base_app.html` or equivalent
- **No new dependencies:** All required libraries (`fastapi.responses.FileResponse`, `require_admin_cookie`, `run_backup`) are already present
- **apscheduler<4 upper bound is load-bearing:** Do not touch `pyproject.toml` APScheduler constraints

### v1.9 Critical Build Rules (carried forward — CSS pipeline still active)

- **FOUC prevention:** The inline IIFE in `base.html` `<head>` is load-bearing. Never move it, add `defer`/`async`, or extract it to an external file.
- **Tailwind purge:** New `dark:` classes must appear as complete literal strings in scanned template files. Always run `npm run build` + grep verification for new classes before committing templates or `input.css`.
- **Safari backdrop-filter:** Declare `-webkit-backdrop-filter` explicitly in `@layer components` for glass card classes. Use fixed pixel values, not CSS variable references.
- **PostCSS autoprefixer:** Always configure `postcss.config.js` with `autoprefixer({ remove: false })` when writing explicit webkit prefixes in source CSS.
- **FastAPI sub-app StaticFiles:** Every FastAPI sub-app that serves HTML must have its own `StaticFiles` mount for `/static`. The main app mount does not propagate.

### Known Tech Debt (carried forward)

- `QSO.find_active()` in models.py — dead production code
- `from_mongo_dt()` in utils.py — tested, not called in production
- Docker end-to-end verification pending (requires live Docker environment)

### Decisions (v2.0 Roadmap)

- **Phase structure:** 2 phases (37 + 38) derived from the natural infrastructure/backend vs UI delivery boundary; consistent with research recommendation
- **Phase 37 bundles INFRA-01 + BACK-01–05:** Volume mount is an infrastructure prerequisite for reliable endpoint testing; both touch the same Docker + Python files in one coherent wiring session
- **Phase 38 is UI-only:** All four UI requirements (sidebar nav, page route, plain anchor, component tokens) are delivered together as one template session with no backend risk

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-13
Stopped at: Roadmap created for v2.0 (Phases 37–38); ROADMAP.md, STATE.md, REQUIREMENTS.md written; ready for /gsd:plan-phase 37
Resume file: None
