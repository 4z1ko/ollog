# Requirements: ollog v2.0

**Defined:** 2026-04-13
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss

## v2.0 Requirements

Requirements for the Database Backup milestone. Each maps to a roadmap phase.

### Infrastructure

- [ ] **INFRA-01**: `admin` service in `docker-compose.yml` mounts `./backups:/app/backups` volume (matches existing `api` service mount — without this, generated backups are lost on container restart)

### Backup Endpoint

- [ ] **BACK-01**: Admin can trigger a full MongoDB database backup via `GET /admin/ui/backup/download`
- [ ] **BACK-02**: Backup endpoint is protected by admin JWT cookie authentication (`require_admin_cookie`)
- [ ] **BACK-03**: Backup generation runs inside `asyncio.to_thread()` to avoid blocking the uvicorn event loop during potentially long-running gzip write
- [ ] **BACK-04**: Download response sets `Content-Disposition: attachment; filename="ollog-backup-YYYY-MM-DD-HH-MM-SS.gz"` with current UTC timestamp in human-readable format (e.g. `ollog-backup-2026-04-14-15-30-42.gz`)
- [ ] **BACK-05**: `datetime.utcnow()` replaced with `datetime.now(timezone.utc)` in `app/backup/dump.py` (Python 3.12 deprecation fix)

### Admin UI

- [ ] **UI-01**: Admin sidebar includes a "Backup" navigation item linking to the backup page
- [ ] **UI-02**: Backup page exists at `/admin/ui/backup` with a "Download Backup" button
- [ ] **UI-03**: Download button is a plain `<a href="/admin/ui/backup/download">` anchor — no HTMX attributes — so the browser handles the file save dialog natively
- [ ] **UI-04**: Backup page uses existing Apple component tokens (`.card`, `.btn-primary`, `.card-title`) consistent with admin UI v1.9 design

## Future Requirements

### v3+ Enhancements

- **BACK-F01**: Streaming backup (cursor-based, not `to_list(length=None)`) for large datasets
- **BACK-F02**: Backup history page listing previously generated files with download links
- **BACK-F03**: Auto-prune old backup files on new download (disk hygiene)
- **BACK-F04**: Progress indicator during backup generation (requires SSE or polling endpoint)

## Out of Scope

| Feature | Reason |
|---------|--------|
| S3 upload configuration in UI | Already handled by env vars (`BACKUP_S3_BUCKET`); `run_backup()` fires upload automatically when configured — no UI needed |
| Scheduled backup UI | Already implemented in `app/backup/scheduler.py` via env vars — no UI needed |
| Incremental / differential backups | Not applicable to hobby-scale MongoDB; full dump is correct at this size |
| Restore-from-backup UI | Restore requires CLI access to prevent accidental data loss; out of scope by design |
| Backup encryption | Not needed for self-hosted single-admin deployment |
| Progress bar / real-time feedback | HTMX cannot monitor a streaming download; spinner on `<a href>` is not addressable; deferred to v3 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 37 | Pending |
| BACK-01 | Phase 37 | Pending |
| BACK-02 | Phase 37 | Pending |
| BACK-03 | Phase 37 | Pending |
| BACK-04 | Phase 37 | Pending |
| BACK-05 | Phase 37 | Pending |
| UI-01 | Phase 38 | Pending |
| UI-02 | Phase 38 | Pending |
| UI-03 | Phase 38 | Pending |
| UI-04 | Phase 38 | Pending |

**Coverage:**
- v2.0 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-13*
*Last updated: 2026-04-13 — traceability confirmed during roadmap creation (Phases 37–38)*
