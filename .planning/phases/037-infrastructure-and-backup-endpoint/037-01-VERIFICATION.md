---
phase: 037-infrastructure-and-backup-endpoint
verified: 2026-04-14T14:06:39Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 37: Infrastructure and Backup Endpoint Verification Report

**Phase Goal:** The admin can successfully download a valid MongoDB backup `.gz` file via `GET /admin/ui/backup/download`, with the file persisting to the shared `./backups` volume and arriving in the browser with a correctly formatted timestamped filename.
**Verified:** 2026-04-14T14:06:39Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Admin with valid cookie can GET /admin/ui/backup/download and receive a .gz file download | VERIFIED | `@ui_router.get("/backup/download")` at `ui_router.py:229`; returns `FileResponse(... media_type="application/gzip")` |
| 2  | The downloaded file has Content-Disposition header with filename matching ollog-backup-YYYY-MM-DD-HH-MM-SS.gz | VERIFIED | `filename=f"ollog-backup-{backup_path.stem}.gz"` at `ui_router.py:241`; stem comes from `strftime('%Y-%m-%d-%H-%M-%S')` in `dump.py:24` |
| 3  | Unauthenticated request to /admin/ui/backup/download returns 302 redirect to login | VERIFIED | `require_admin_cookie` raises 401/403; `admin_main.py:33-34` catches those and returns `RedirectResponse(url="/admin/ui/login", status_code=302)` for all `/admin/ui/` paths |
| 4  | Backup file persists at ./backups/ on the host via Docker volume mount | VERIFIED | `docker-compose.yml:49` — admin service has `./backups:/app/backups`; `config.py` has `backup_dir = "/app/backups"` |
| 5  | Event loop is not blocked during backup — asyncio.to_thread wraps sync _write_backup | VERIFIED | `dump.py:56`: `backup_path = await asyncio.to_thread(_write_backup, settings)` |
| 6  | datetime.utcnow() no longer appears in app/backup/dump.py | VERIFIED | No matches for `utcnow` in `dump.py`; file uses `datetime.now(timezone.utc)` at line 24 |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docker-compose.yml` | Volume mount `./backups:/app/backups` on admin service | VERIFIED | Present at line 49 under `admin:` service |
| `app/backup/dump.py` | Sync `_write_backup` helper + async `run_backup` orchestrator | VERIFIED | Both functions defined; 65 lines, substantive implementation |
| `app/admin/ui_router.py` | GET `/admin/ui/backup/download` endpoint | VERIFIED | `backup_download` function at line 229; returns `FileResponse` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/admin/ui_router.py` | `app/backup/dump.py` | `await run_backup(settings)` | WIRED | Lazy import at line 234; called at line 237 |
| `app/backup/dump.py` | `asyncio.to_thread` | `_write_backup` called inside `to_thread` | WIRED | `dump.py:56` exact match |
| `app/admin/ui_router.py` | `FileResponse` | `filename=` parameter | WIRED | `FileResponse(` at line 238, `filename=` at line 241 — multiline call, pattern match confirmed manually |
| `app/admin/ui_router.py` | `app/auth/dependencies.py` | `Depends(require_admin_cookie)` | WIRED | Found at `ui_router.py:231` on the backup endpoint specifically; also lines 99, 124, 158, 202 |

Note: The plan's key link pattern `FileResponse.*filename=` is a single-line regex that does not match a multiline call. The wiring is real — `FileResponse` and `filename=` both exist in the same return block (lines 238-242). Verified by targeted grep.

### Requirements Coverage

No REQUIREMENTS.md entries mapped specifically to phase 37 were present. All must-haves from the plan frontmatter are satisfied.

### Anti-Patterns Found

None. No TODO/FIXME/placeholder comments, stub returns, or empty handlers found in any of the three modified files.

### Human Verification Required

#### 1. End-to-end download flow in running stack

**Test:** With Docker stack running (`--profile admin`), log in at `/admin/ui/login`, then navigate to `/admin/ui/backup/download`.
**Expected:** Browser prompts a file download named `ollog-backup-YYYY-MM-DD-HH-MM-SS.gz`; file appears in `./backups/` on the host after download.
**Why human:** Cannot exercise the live MongoDB connection, Docker volume bind mount, or browser file-save behavior programmatically from static analysis.

#### 2. Unauthenticated 302 redirect

**Test:** In an incognito window (no `admin_token` cookie), navigate directly to `http://localhost:8001/admin/ui/backup/download`.
**Expected:** Browser lands on `/admin/ui/login` (302 redirect); no file download occurs.
**Why human:** Confirms the exception handler fires correctly in the running FastAPI process, not just that the code path exists.

### Gaps Summary

No gaps. All six observable truths are verified against the actual codebase. The implementation is complete and fully wired:

- Docker volume is mounted on both `api` and `admin` services.
- `_write_backup` is synchronous, wrapped correctly in `asyncio.to_thread`, avoiding event loop blocking.
- Filename format `ollog-backup-YYYY-MM-DD-HH-MM-SS.gz` is produced by combining the `strftime` stem with the `ollog-backup-` prefix in `FileResponse`.
- `datetime.utcnow()` is absent; the file uses the timezone-aware `datetime.now(timezone.utc)`.
- Auth guard `require_admin_cookie` is applied to the download endpoint, and the app-level exception handler converts 401/403 into a 302 redirect for all `/admin/ui/` paths.

---

_Verified: 2026-04-14T14:06:39Z_
_Verifier: Claude (gsd-verifier)_
