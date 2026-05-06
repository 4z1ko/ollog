# Requirements: ollog v2.8 Clear Log

**Defined:** 2026-05-06
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss

## v1 Requirements

### Operator Clear Log (Self-Service)

- [ ] **CLR-01**: Operator can see a "Clear my log" action in a Danger Zone section at the bottom of the profile/settings page
- [ ] **CLR-02**: Clicking it opens a confirmation modal showing the number of QSOs that will be deleted and requiring the operator to enter their password
- [ ] **CLR-03**: On successful password verification, all of the operator's QSOs are permanently deleted from MongoDB
- [ ] **CLR-04**: Operator sees an inline success message with the count of QSOs deleted; the modal closes
- [ ] **CLR-05**: Incorrect password shows an inline error inside the modal — deletion does not proceed

### Admin Clear Operator Log

- [ ] **ACLR-01**: Admin can trigger "Clear log" for any operator from the admin operators management page (alongside existing enable/disable/reset-password actions)
- [ ] **ACLR-02**: A confirmation modal opens showing the target operator's callsign and QSO count, requiring the admin to re-enter their own password
- [ ] **ACLR-03**: On successful admin password verification, all QSOs for the target operator are permanently deleted
- [ ] **ACLR-04**: Admin sees an inline success confirmation with the operator callsign and QSO count deleted
- [ ] **ACLR-05**: Incorrect admin password shows an inline error — deletion does not proceed

### Documentation

- [ ] **DOC-01**: Operator getting-started guide updated with a "Clear my log" section explaining the Danger Zone flow and password confirmation
- [ ] **DOC-02**: Admin guide updated with "Clear operator log" instructions including the admin-password confirmation step
- [ ] **DOC-03**: MkDocs site rebuilt and `site/` committed to repo

## Future Requirements

None identified for this feature area.

## Out of Scope

| Feature | Reason |
|---------|--------|
| REST API endpoint for bulk QSO delete | No external tooling needs this; UI-only is sufficient for v2.8 |
| Selective clear (by date range, band, mode) | Adds significant UI complexity; full clear covers the use case |
| Soft-delete / archive (recoverable) | User explicitly chose permanent delete; soft-delete is misleading for a "clear" action |
| Per-operator clear from the operator's own admin panel | Operators have no admin panel; admin console handles this |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLR-01 | TBD | Pending |
| CLR-02 | TBD | Pending |
| CLR-03 | TBD | Pending |
| CLR-04 | TBD | Pending |
| CLR-05 | TBD | Pending |
| ACLR-01 | TBD | Pending |
| ACLR-02 | TBD | Pending |
| ACLR-03 | TBD | Pending |
| ACLR-04 | TBD | Pending |
| ACLR-05 | TBD | Pending |
| DOC-01 | TBD | Pending |
| DOC-02 | TBD | Pending |
| DOC-03 | TBD | Pending |

**Coverage:**
- v1 requirements: 13 total
- Mapped to phases: 0 (roadmap pending)
- Unmapped: 13 ⚠️

---
*Requirements defined: 2026-05-06*
*Last updated: 2026-05-06 after initial definition*
