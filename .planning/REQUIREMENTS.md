# Requirements: ollog v2.1

**Defined:** 2026-04-14
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss

## v2.1 Requirements

Requirements for the Database Restore milestone. Each maps to a roadmap phase.

### Admin UI

- [ ] **UI-01**: Admin sidebar includes a "Restore" navigation item linking to the restore page — visible on all admin pages (Operators, Backup, and Restore)
- [ ] **UI-02**: Restore page exists at `/admin/ui/restore` with a file upload form that accepts `.gz` files
- [ ] **UI-03**: Restore page is protected by admin cookie authentication (`require_admin_cookie`) — unauthenticated access redirects to login

### File Validation

- [ ] **VAL-01**: Uploaded file is validated as a valid gzip archive (decompressible, not corrupt)
- [ ] **VAL-02**: Uploaded file contents are validated as NDJSON backup format — at least one line parses as a valid `{"collection": "...", "doc": {...}}` record
- [ ] **VAL-03**: Validation failure displays an inline error message on the restore page without losing the form state; no database changes are made

### Password Confirmation

- [ ] **AUTH-01**: After successful file validation, a password confirmation modal appears with the page background blurred
- [ ] **AUTH-02**: The modal requires the admin to enter their own login password (the password used to log in to the admin console)
- [ ] **AUTH-03**: Entering a wrong password displays an inline error inside the modal without closing it or starting the restore
- [ ] **AUTH-04**: A "Cancel" button in the modal dismisses it without starting the restore or deleting the uploaded file

### Restore Operation

- [ ] **OPS-01**: Before wiping any data, the system automatically creates a backup of the current database and records the backup file path in the success/error response
- [ ] **OPS-02**: After password verification, all MongoDB collections are dropped and repopulated from the uploaded backup file, collection by collection
- [ ] **OPS-03**: On successful restore, the restore page shows a success banner indicating the restore is complete and referencing the auto-backup filename
- [ ] **OPS-04**: On restore failure (after wipe has started), the page shows an error message that includes the auto-backup filename so the admin can recover using the backup feature

## Future Requirements

### v3+ Enhancements

- **REST-F01**: Restore progress indicator (SSE-based — operation can take several seconds for large databases)
- **REST-F02**: Restore history log listing previous restore operations with timestamps and file sizes
- **REST-F03**: Partial restore — restore only selected collections from the backup file
- **REST-F04**: Drag-and-drop file upload interface

## Out of Scope

| Feature | Reason |
|---------|--------|
| Restore from S3 | S3 uploads are a separate infrastructure concern; local file upload covers the primary use case |
| Scheduled/automated restore | Restore is intentionally manual and destructive; automation creates risk |
| Restore encryption/decryption | Not needed for self-hosted single-admin deployment |
| Incremental restore (merge, not overwrite) | Merge semantics are complex and error-prone; full overwrite is the safe default |
| Multiple simultaneous restore operations | Single-admin deployment; concurrent restores would corrupt the database |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| UI-01 | — | Pending |
| UI-02 | — | Pending |
| UI-03 | — | Pending |
| VAL-01 | — | Pending |
| VAL-02 | — | Pending |
| VAL-03 | — | Pending |
| AUTH-01 | — | Pending |
| AUTH-02 | — | Pending |
| AUTH-03 | — | Pending |
| AUTH-04 | — | Pending |
| OPS-01 | — | Pending |
| OPS-02 | — | Pending |
| OPS-03 | — | Pending |
| OPS-04 | — | Pending |

**Coverage:**
- v2.1 requirements: 14 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 14 ⚠

---
*Requirements defined: 2026-04-14*
*Last updated: 2026-04-14 — initial definition*
