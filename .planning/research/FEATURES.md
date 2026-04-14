# Feature Research

**Domain:** Admin database backup download — self-hosted web admin console (FastAPI + HTMX + MongoDB)
**Researched:** 2026-04-13
**Confidence:** HIGH (codebase audited directly; backup module fully read; HTMX/FastAPI patterns verified against existing admin UI patterns in codebase; MongoDB EJSON format verified against bson library docs)

---

## Codebase Audit Findings

A previous milestone (v1.8) already built the backup engine. Confirmed by direct code audit:

**What already exists — do not re-implement:**
- `app/backup/dump.py` — `run_backup(settings)` async function: connects its own `AsyncMongoClient`, iterates all collections sorted alphabetically, serializes each document as EJSON canonical JSON, writes one JSON object per line (`{"collection": "...", "doc": {...}}`), gzip-compresses the whole file, returns the file `Path`
- `app/backup/scheduler.py` — `make_scheduler(cron_expr, job_func)` using APScheduler 3.x `AsyncIOScheduler` + `CronTrigger`
- `app/backup/upload.py` — `upload_to_s3(local_path, bucket, key)` using aioboto3; exceptions are caught and logged — never re-raised
- `app/backup/__main__.py` — one-shot CLI entry: `python -m app.backup`
- Config keys in `app/config.py`: `backup_dir` (default `/app/backups`), `backup_schedule` (cron string, optional), `backup_s3_bucket` (optional), `backup_s3_prefix` (default `backups/`)
- Filename format already decided: `%Y%m%dT%H%M%SZ.gz` (e.g. `20260413T143022Z.gz`) — compact ISO 8601 basic format, UTC

**What does NOT exist — this milestone adds:**
- Admin UI endpoint to trigger a backup on demand and stream the file to the browser
- A "Download Backup" button on the admin console UI (`/admin/ui/` area)
- Any HTTP route in `admin/ui_router.py` or `admin/router.py` for backup

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that define a working "backup button." Missing these means the feature is unusable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| One-click full dump download | Admin clicks a button, browser downloads a file. This is the entire stated goal. Anything less is not a backup button. | LOW | `run_backup(settings)` already exists. Need a `GET /admin/ui/backup/download` route protected by `require_admin_cookie`, calling `run_backup`, then streaming the `.gz` file as `application/gzip` with `Content-Disposition: attachment`. |
| Correct MIME type and Content-Disposition header | Browser must offer a Save dialog, not render the file inline. Without this, Chrome may try to decompress and display the gzip as text. | LOW | `Content-Type: application/gzip`, `Content-Disposition: attachment; filename="ollog-20260413T143022Z.gz"`. FastAPI `FileResponse` or `StreamingResponse` handles both. |
| Timestamped filename | File already includes UTC timestamp. Users need to know when a backup was taken, especially if they download multiple over time. Without a timestamp, `backup.gz` gets overwritten every time in the Downloads folder. | LOW | Already baked into `dump.py` filename format (`%Y%m%dT%H%M%SZ.gz`). Expose this in `Content-Disposition` filename. Optionally prefix with app name: `ollog-20260413T143022Z.gz`. |
| Auth gate (admin-only) | A backup file contains every QSO, every user hash, every operator profile. It must never be accessible to non-admin sessions. | LOW | Use existing `require_admin_cookie` dependency — already used on every other admin UI route. |
| Visual feedback during dump | Dumps on a hobby dataset are fast (sub-second to a few seconds). But the button must not appear broken during the wait. Minimum: button disable + spinner while request is in flight. | LOW | HTMX `hx-indicator` + `htmx-request` class gives automatic spinner behavior. Alternatively, a plain HTML link or form POST that redirects to a file download is acceptable for v1. |
| Error feedback if dump fails | If MongoDB is unreachable or disk is full, the admin needs to know. A silent failure (browser gets 500, nothing happens) is worse than no button. | LOW | Return a visible error message in the admin UI if `run_backup` raises. HTMX partial swap of an error banner is the established pattern in this codebase. |

### Differentiators (Competitive Advantage)

Features beyond baseline that improve the admin's confidence in the backup.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| File size displayed after dump | The admin can sanity-check "did I get everything?" A 300-byte file when there are 5,000 QSOs is a red flag. | LOW | After streaming the file, a secondary HTMX swap could update a status line: "Last backup: 2026-04-13 14:30 UTC — 48 KB". Requires a small metadata endpoint or returning stats in headers. |
| Last backup timestamp on the page | Confirms the most recent manual download without needing to check the filesystem or S3. Builds operator confidence that backups exist. | LOW | Store last-backup time in memory (app state or a simple file) or derive it by listing `backup_dir`. Show it in the admin UI on page load. |
| Human-readable filename prefix | `ollog-20260413T143022Z.gz` vs `20260413T143022Z.gz` — the prefix tells the admin which app this is from when they open their Downloads folder a month later. | LOW | Prepend `ollog-` in the `Content-Disposition` header. No change to the file stored on disk. |
| HTMX-powered button with spinner | Consistent with the HTMX pattern already used across the admin for create/toggle/reset. Keeps the UX cohesive — no full-page navigation. | LOW | Note: file downloads via HTMX require a workaround (HTMX does not natively trigger browser download dialog from XHR responses). The correct approach is a plain `<a href="/admin/ui/backup/download">` or a form that POSTs to a redirect. See Anti-Features section. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem natural for a backup button but are wrong for this scope.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Progress bar for dump | Large databases can take time; users want progress feedback | For a hobby ham radio logbook the dump will be sub-second to a few seconds at most. A progress bar requires server-sent events or WebSocket streaming of progress, which is significant added complexity for zero practical benefit at this data scale. The existing SSE infrastructure (`app/feed/`) could theoretically be repurposed, but it would be massive scope creep for a feature that is never needed. | Button spinner via `cursor-wait` or `disabled` state is sufficient. |
| HTMX `hx-get` for file download | Consistent with other admin HTMX interactions — feels natural | HTMX performs XHR/fetch internally. Browsers block file downloads from XHR responses — the `Content-Disposition: attachment` header is ignored by fetch/XHR. The file content arrives in JS memory and is discarded. Users see no download dialog. | Use a plain `<a href="...">` link or a non-HTMX form POST that returns a `FileResponse`. The browser handles the download natively. This is not a regression — it is the correct tool. |
| Incremental / differential backup | Backing up only changed documents since last backup reduces file size | MongoDB change streams exist but incremental backup is architecturally complex (requires tracking a resume token, diffing document state). For a hobby self-hosted logbook, a full dump is the right answer — datasets are small and gzip compression handles redundancy well. | Full dump via existing `run_backup()`. |
| Backup scheduling via UI | Admin sets a cron schedule in the UI without editing env vars | The scheduler already exists (`backup_schedule` env var, wired in `main.py` lifespan). Adding a UI to configure it requires persisting the schedule somewhere (database? config file?) and restarting the scheduler dynamically — fragile and complex. | Document the existing `BACKUP_SCHEDULE` env var in the admin UI as a tooltip or info blurb. The env var approach is the correct self-hosted pattern. |
| Per-collection or per-operator export | Download only QSOs for one operator, or only the users collection | The existing ADIF export already covers per-operator QSO export. A backup button serves a different purpose: full system restore capability. Mixing these concerns adds confusion and complexity. | ADIF export for per-operator data (already exists). Full dump for system backup. |
| Encryption of the backup file | Backup contains hashed passwords; encryption at rest protects against disclosure if the file leaks | Encryption requires key management — where does the key live? If the key is in the same Docker Compose environment as the backup, encryption provides no real protection. If the admin has to manage an external key, complexity skyrockets. | Document that hashed_password fields use bcrypt (already true), so raw password exposure via a stolen backup file requires cracking. Recommend the admin encrypt the file using their local OS tools after download. |
| Email the backup to admin | Some admin consoles offer "email me a backup daily" | The project constraints explicitly state no email infrastructure. This would require SMTP configuration, which is entirely out of scope. | The existing `backup_s3_bucket` config provides cloud storage for automated backups when needed. |
| S3 upload via UI trigger | Offer "backup and upload to S3" as a UI action separate from download | `upload.py` already fires automatically after `run_backup()` if `backup_s3_bucket` is set. A UI toggle for this would be redundant (it's already env-var-controlled) and adds UI complexity with no gain. | S3 upload is automatic when configured. The download button is for local retrieval only. |
| Restore from backup via UI | Upload a `.gz` file and restore the database | Restore is significantly more complex than backup: requires parsing the NDJSON format, handling collection drops/upserts, transactional consistency, and auth to prevent accidental restores. Out of scope for v1. | CLI restore script can be documented as a separate tool. |
| Backup history / list of past backups | Show a table of all `.gz` files in `backup_dir` | This requires listing the filesystem, displaying file sizes and timestamps, and potentially offering per-file download or delete. It is a mini file manager — disproportionate to the value. The admin knows when they clicked the button. | Last backup timestamp (single entry) is sufficient for v1. |

---

## Feature Dependencies

```
Download Backup Button
    └──requires──> GET /admin/ui/backup/download route (new, in admin/ui_router.py)
                       └──requires──> require_admin_cookie (exists)
                       └──requires──> run_backup(settings) (exists in app/backup/dump.py)
                       └──requires──> FileResponse or StreamingResponse (FastAPI stdlib)

Error Feedback
    └──requires──> Download route catches exceptions and returns HTMX-compatible error partial
    └──enhances──> Visual Feedback (spinner + error state in same UI interaction)

Visual Feedback (spinner)
    └──conflicts──> HTMX hx-get/hx-post for file download
    └──requires──> Plain <a> link (no HTMX) OR form POST with redirect
    └──note──> "Spinner while downloading" is not possible with plain <a> link without JS;
               acceptable to omit in v1 since downloads are fast for hobby-scale data

Last Backup Timestamp (differentiator)
    └──requires──> Download route returns timestamp in response headers OR
                   a secondary GET /admin/ui/backup/status endpoint
    └──enhances──> Download button (gives context on page load)
    └──optional──> Can be deferred to v1.x without breaking v1

File Size Display (differentiator)
    └──requires──> Last Backup Timestamp (same data source: file stat after dump)
    └──optional──> Can be deferred to v1.x
```

### Dependency Notes

- **HTMX conflicts with file download:** The download link must be a plain `<a href>` or non-HTMX form, not an `hx-get`. This means no HTMX spinner on the download action itself. Acceptable because downloads are fast at hobby scale.
- **`run_backup()` creates its own `AsyncMongoClient`:** This is already the design in `dump.py` (documented in the docstring: "does NOT use app.database.get_client() because get_client() returns None in CLI context"). In the web context, `get_client()` would work, but using the existing `run_backup()` function as-is avoids modifying tested code.
- **File is written to disk first, then served:** `run_backup()` writes to `backup_dir` before returning the path. The HTTP handler then serves that file. This means disk space in `backup_dir` must be sufficient. For hobby-scale data, not a concern. The disk write also means `FileResponse` (which reads the file by path) works cleanly.
- **S3 upload fires automatically after dump:** If `backup_s3_bucket` is configured, `run_backup()` already calls `upload_to_s3()`. The UI download endpoint does not need to handle this — it happens as a side effect. Admin gets local download + S3 upload simultaneously.

---

## MVP Definition

### Launch With (v1)

- [ ] `GET /admin/ui/backup/download` route in `admin/ui_router.py` — calls `run_backup(settings)`, serves the resulting `.gz` file as `application/gzip` with `Content-Disposition: attachment; filename="ollog-{timestamp}.gz"` — this is the entire feature
- [ ] Auth gate via `require_admin_cookie` — no extra work; pattern already exists on every admin UI route
- [ ] Error handling — if `run_backup()` raises, return an HTMX-compatible error partial that swaps into the page (consistent with how toggle/reset errors work in `users_table.html`)
- [ ] "Download Backup" button or link on the admin UI page — plain `<a href="/admin/ui/backup/download">` styled as a button using existing `.btn-secondary` or `.btn-primary` CSS class

### Add After Validation (v1.x)

- [ ] Last backup timestamp + file size displayed on page — requires a `GET /admin/ui/backup/status` endpoint that stats the most recent `.gz` in `backup_dir`; adds confidence but not needed for core function
- [ ] Human-readable prefix in `Content-Disposition` filename (`ollog-` prefix) — trivial, add if it feels incomplete

### Future Consideration (v2+)

- [ ] Backup history table (list all `.gz` files in `backup_dir` with size/date) — mini file manager, disproportionate complexity for v1
- [ ] CLI restore script as a documented tool — out of scope for the UI button milestone
- [ ] Progress feedback via SSE for very large datasets — unnecessary at hobby scale; revisit if a station accumulates 100k+ QSOs

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Download route + file response | HIGH | LOW | P1 |
| Auth gate (require_admin_cookie) | HIGH | LOW (already exists) | P1 |
| Error feedback partial | MEDIUM | LOW | P1 |
| "Download Backup" button in admin UI | HIGH | LOW | P1 |
| Human-readable filename prefix | LOW | LOW | P2 |
| Last backup timestamp on page | MEDIUM | LOW | P2 |
| File size display | LOW | LOW | P3 |
| Backup history table | LOW | HIGH | defer |
| Progress bar | LOW | HIGH | never (wrong scale) |

**Priority key:**
- P1: Must have for launch — defines whether the feature works at all
- P2: Should have — adds confidence/polish, add when core is working
- P3: Nice to have — future consideration
- defer / never: Out of scope, explained in Anti-Features

---

## Format and Filename Convention (confirmed from codebase)

The dump format and naming are already decided in `dump.py` and do not need to be re-specified:

| Aspect | Decision | Source |
|--------|----------|--------|
| Container format | gzip | `gzip.open(backup_path, "wt")` in `dump.py` |
| Content format | NDJSON (newline-delimited JSON) | one `gz.write(line + "\n")` per document |
| JSON encoding | EJSON Canonical (bson `CANONICAL_JSON_OPTIONS`) | preserves ObjectId, Date, Binary types exactly |
| Filename | `%Y%m%dT%H%M%SZ.gz` (e.g. `20260413T143022Z.gz`) | `datetime.utcnow().strftime(...)` in `dump.py` |
| Timestamp zone | UTC (Z suffix) | `datetime.utcnow()` |
| MIME type for download | `application/gzip` | standard; `application/x-gzip` is an older synonym |

The format is opinionated and correct: EJSON canonical JSON is MongoDB's own round-trip-safe format (it encodes ObjectId as `{"$oid": "..."}` etc.), gzip compression is lossless and universally supported, NDJSON is streamable if needed in the future. No changes needed to the format.

---

## Sources

- Direct codebase audit: `/Users/royco/ollog/app/backup/dump.py`, `scheduler.py`, `upload.py`, `__main__.py`, `app/config.py`, `app/admin/ui_router.py`, `app/admin_main.py`
- FastAPI `FileResponse` docs (confirmed `Content-Disposition` header support): https://fastapi.tiangolo.com/advanced/custom-response/#fileresponse
- HTMX file download limitation (XHR cannot trigger browser Save dialog): confirmed behavior per HTMX GitHub issue #2 and MDN fetch API behavior (Content-Disposition ignored in XHR/fetch responses)
- bson `json_util` CANONICAL_JSON_OPTIONS: https://pymongo.readthedocs.io/en/stable/api/bson/json_util.html
- MIME type for gzip: https://www.iana.org/assignments/media-types/application/gzip (IANA registered 2013)

---
*Feature research for: admin database backup download button — ollog self-hosted ham radio logbook*
*Researched: 2026-04-13*
