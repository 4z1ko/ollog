# Requirements: ollog - v3.5 ACLog Registered Operator Routing

**Defined:** 2026-06-16
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss.

## v3.5 Requirements

### ACLog Operator Identity Routing

- [ ] **ACOP-01**: ollog can identify an ACLog record's operator identity from full-record API data, using the safest available ACLog field names discovered from real `LIST INCLUDEALL` responses.
- [ ] **ACOP-02**: Manual ACLog sync imports only remote QSOs whose ACLog operator identity matches the authenticated ollog operator's callsign/profile identity.
- [ ] **ACOP-03**: Live ACLog bridge ingestion imports only saved ACLog QSOs whose ACLog operator identity matches the ollog operator who owns the bridge.
- [ ] **ACOP-04**: ACLog records with missing, blank, or unmatched operator identity are skipped and counted/reported instead of being imported into the bridge owner's collection.
- [ ] **ACOP-05**: Two ollog operators can point saved ACLog bridges at the same remote ACLog computer without importing each other's QSOs.
- [ ] **ACOP-06**: Existing full-record import behavior remains intact for all matching records, including non-empty returned fields, Other/custom-field mapping, duplicate handling, rowHash behavior, and per-user `<username>_qsos` collection routing.
- [ ] **ACOP-07**: Profile Settings sync reports include operator-filter results, including matched/imported records, skipped missing-operator records, skipped unmatched-operator records, duplicates/already-present records, and errors.
- [ ] **ACOP-08**: Tests cover parser/operator-field detection, manual sync filtering, live bridge filtering, skip/report behavior, and the shared-remote two-operator scenario.
- [ ] **ACOP-09**: Operator documentation explains how shared ACLog remote computers are handled, which ACLog operator identity fields ollog recognizes, and why records without a matching identity are skipped.

## Research Findings

- N3FJP's official TCP API documents `GETUSERSETTINGS`, which returns an `OPERATOR` value for the currently configured software user.
- The same API documents `LIST INCLUDEALL`, which returns every QSO field with a non-empty value.
- The API docs do not guarantee, by field name, which operator identity field appears on saved QSO records. Phase 66 must therefore include a real-response discovery step before locking the parser/matcher behavior.
- Current ollog ACLog ingestion routes records by the ollog user who owns the bridge, not by ACLog record identity. Without filtering, two operators pointed at the same ACLog computer can import the same remote records into separate local collections.

## Future Requirements

### ACLog Identity Enhancements

- **ACOP-FUT-01**: Admin can configure explicit ACLog-operator-to-ollog-operator mappings when ACLog stores a label that differs from the operator callsign.
- **ACOP-FUT-02**: Operator can preview skipped unmatched ACLog records before deciding whether to import them.
- **ACOP-FUT-03**: ACLog bridge diagnostics can show recent raw identity field names for troubleshooting.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Importing records with missing operator identity | User confirmed missing ACLog operator identity must be skipped. |
| Importing records with unmatched operator identity | User confirmed unmatched ACLog operator identity must be skipped. |
| Reassigning QSOs between ollog users during sync | Current milestone prevents cross-operator import; reassignment workflows need separate review. |
| Updating existing imported QSOs from ACLog | Existing manual sync is additive only and should stay that way. |
| Scheduled/background sync | Current scope is identity-safe behavior for existing live bridge and manual sync paths. |
| Changes to ACLog itself | ollog can only consume fields returned by the ACLog API. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ACOP-01 | Phase 66 | Planned |
| ACOP-02 | Phase 66 | Planned |
| ACOP-03 | Phase 66 | Planned |
| ACOP-04 | Phase 66 | Planned |
| ACOP-05 | Phase 66 | Planned |
| ACOP-06 | Phase 66 | Planned |
| ACOP-07 | Phase 66 | Planned |
| ACOP-08 | Phase 66 | Planned |
| ACOP-09 | Phase 66 | Planned |

**Coverage:**
- v3.5 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0

---
*Requirements defined: 2026-06-16*
*Last updated: 2026-06-16 at v3.5 milestone start*
