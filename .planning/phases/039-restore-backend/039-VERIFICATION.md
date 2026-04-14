---
phase: 039-restore-backend
verified: 2026-04-14T17:47:22Z
status: passed
score: 6/6 must-haves verified
gaps: []
human_verification: []
---

# Phase 39: Restore Backend Verification Report

**Phase Goal:** The two-phase restore API exists and is fully functional — an uploaded .gz file is validated for integrity and NDJSON format, a password modal form triggers auto-backup then drop-and-restore, and all outcomes (validation failure, wrong password, restore success, restore failure) return appropriate HTMX response fragments.
**Verified:** 2026-04-14T17:47:22Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1 | POST /admin/ui/restore/upload with a valid .gz NDJSON backup returns HTTP 200 with password_modal.html containing a hidden temp_path field | VERIFIED | `restore_upload` writes raw to NamedTemporaryFile, reads first line with gzip+json.loads, checks `collection`/`doc` keys, then returns `TemplateResponse("admin/restore/password_modal.html", {"temp_path": temp_path})`. Template has `<input type="hidden" name="temp_path" value="{{ temp_path }}">`. |
| 2 | POST /admin/ui/restore/upload with invalid file (bad gzip or bad NDJSON) returns HTTP 200 with upload_error.html and no tempfile left on disk | VERIFIED | On `(OSError, EOFError, ValueError)` the handler calls `os.unlink(temp_path)` then returns `TemplateResponse("admin/restore/upload_error.html", ..., status_code=200)`. Outer `except Exception` also deletes the file before re-raising. |
| 3 | POST /admin/ui/restore/confirm with wrong password returns HTTP 200 with password_error.html (modal stays open, temp_path preserved) | VERIFIED | After path traversal guard, `verify_password(password, current_user.hashed_password)` is checked. On failure returns `TemplateResponse("admin/restore/password_error.html", {"error": "Incorrect password", "temp_path": temp_path}, status_code=200)`. Template re-renders the full modal with the hidden `temp_path` field intact. |
| 4 | POST /admin/ui/restore/confirm with correct password triggers auto-backup then drop+restore, returns restore_success.html with auto-backup filename | VERIFIED | `await run_backup(settings)` is called and assigned to `auto_backup_path` before `await run_restore(str(p), settings)`. Success returns `TemplateResponse("admin/restore/restore_success.html", {"backup_path": auto_backup_path.name})`. Failure path also passes `auto_backup_path.name`. |
| 5 | _restore_from_file uses bson.json_util.loads so ObjectId and datetime fields are restored with correct BSON types, not plain dicts | VERIFIED | `from bson.json_util import loads as bson_loads` at module level. Every NDJSON line is deserialized with `record = bson_loads(line)`. No `json.loads` appears in `restore.py` (the only occurrence in the grep output is in a docstring comment, not executable code). |
| 6 | Path traversal guard on temp_path rejects any path outside tempfile.gettempdir(); unauthenticated requests are rejected by require_admin_cookie | VERIFIED | Guard: `p = pathlib.Path(temp_path).resolve()`, `tmpdir = pathlib.Path(tempfile.gettempdir()).resolve()`, then checks `not str(p).startswith(str(tmpdir)) or p.suffix != ".gz" or not p.exists()` — returns HTTP 400 on failure. Both routes have `Depends(require_admin_cookie)` as a parameter dependency. |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/backup/restore.py` | Sync `_restore_from_file` + async `run_restore` | VERIFIED | File exists, 48 lines, non-stub. Exports `run_restore`. Uses `bson.json_util.loads` via `bson_loads` alias. `try/finally: client.close()` wraps only drop+insert loop. |
| `app/admin/ui_router.py` | POST /restore/upload and POST /restore/confirm routes | VERIFIED | Both routes present in `# Restore` section (lines 258–386). `UploadFile` imported at top of file (line 12). `verify_password` imported at line 18. |
| `templates/admin/restore/upload_error.html` | Inline error fragment for bad file upload | VERIFIED | Exists. Non-empty. Renders `{{ error }}` in `<div class="alert alert-error">`. |
| `templates/admin/restore/password_modal.html` | Modal fragment with hidden temp_path input | VERIFIED | Exists. Contains `<input type="hidden" name="temp_path" value="{{ temp_path }}">`. Points to `hx-post="/admin/ui/restore/confirm"`. |
| `templates/admin/restore/password_error.html` | Inline error inside modal for wrong password | VERIFIED | Exists. Re-renders full modal. Hidden `temp_path` preserved. `{{ error }}` in `alert-error` div. |
| `templates/admin/restore/restore_success.html` | Success banner with auto-backup filename | VERIFIED | Exists. `{{ backup_path }}` conditionally rendered in `<code>` tag inside `alert-success`. |
| `templates/admin/restore/restore_failure.html` | Error banner with auto-backup filename and error message | VERIFIED | Exists. `{{ error }}` and `{{ backup_path }}` both conditionally rendered inside `alert-error`. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ui_router.py restore_upload` | `templates/admin/restore/password_modal.html` | `TemplateResponse` with `temp_path` context var | WIRED | Line 307–311: `TemplateResponse(request, "admin/restore/password_modal.html", {"temp_path": temp_path})` |
| `ui_router.py restore_confirm` | `app/backup/restore.run_restore` | `await run_restore(str(p), settings)` | WIRED | Line 370: `await run_restore(str(p), settings)` — imported lazily at line 336 |
| `app/backup/restore._restore_from_file` | `bson.json_util.loads` | `bson_loads(line)` for each NDJSON line | WIRED | Line 5: `from bson.json_util import loads as bson_loads`; line 27: `record = bson_loads(line)` |
| `ui_router.py restore_confirm` | `app/backup/dump.run_backup` | `auto_backup_path = await run_backup(settings)` before any drop | WIRED | Line 335: `from app.backup.dump import run_backup`; line 359: `auto_backup_path = await run_backup(settings)` — precedes `run_restore` at line 370 |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/admin/ui_router.py` | 291 | `json.loads` in `restore_upload` | Info | Not a bug. Used only for structural NDJSON validation (checking `collection`/`doc` keys exist in the first line), not for database deserialization. The actual deserialization into MongoDB uses `bson.json_util.loads` inside `_restore_from_file`. Intentional per plan spec. |

No blocker or warning anti-patterns found.

---

### Human Verification Required

None. All must-haves are verifiable from source code. The behavioral outcomes (HTTP responses, tempfile cleanup) are directly readable from the handler logic.

---

### Gaps Summary

No gaps. All six observable truths are verified by direct source inspection. All seven artifacts exist and are substantive (non-stub). All four key links are confirmed wired. The `json.loads` usage in the upload handler is scoped to structural validation only and does not affect BSON type fidelity.

---

_Verified: 2026-04-14T17:47:22Z_
_Verifier: Claude (gsd-verifier)_
