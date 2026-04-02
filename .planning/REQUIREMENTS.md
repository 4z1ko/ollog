# Requirements: ollog — Ham Radio Online Logbook

**Defined:** 2026-04-03
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss

## v1 Requirements

### Authentication & Accounts

- [ ] **AUTH-01**: Admin can create operator accounts (callsign, username, password)
- [ ] **AUTH-02**: Admin can enable and disable operator accounts
- [ ] **AUTH-03**: Admin can reset operator passwords
- [ ] **AUTH-04**: Operator can log in with username and password
- [ ] **AUTH-05**: Operator session persists via JWT across browser refresh
- [ ] **AUTH-06**: All API endpoints require authentication (no unauthenticated access)

### QSO Entry

- [ ] **QSO-01**: Operator can log a QSO via web form with fields: CALL, QSO_DATE, TIME_ON, BAND, FREQ, MODE, RST_SENT, RST_RCVD
- [ ] **QSO-02**: Operator can log a QSO via REST API in ADIF field format in real-time
- [ ] **QSO-03**: Operator can edit any field of their own QSOs after logging
- [ ] **QSO-04**: Operator can soft-delete their own QSOs (with confirmation; recoverable)
- [ ] **QSO-05**: System warns operator when a potential duplicate QSO is detected (same CALL, BAND, MODE within ±2 min window)
- [ ] **QSO-06**: QSO timestamps are stored and displayed in UTC

### Log View

- [ ] **LOG-01**: Operator can view their QSO log as a paginated list
- [ ] **LOG-02**: Operator can filter their log by callsign, date range, band, and mode
- [ ] **LOG-03**: Operator can sort their log by date/time, callsign, or band

### ADIF Import & Export

- [ ] **ADIF-01**: Operator can upload a .adi or .adif file to bulk-import QSOs into their logbook
- [ ] **ADIF-02**: Import detects and reports duplicate QSOs using fuzzy ±2 min window (never auto-deletes; shows import report)
- [ ] **ADIF-03**: Import preserves all ADIF fields including APP_ and USERDEF fields (lossless N+1 passthrough)
- [ ] **ADIF-04**: Operator can download their logbook as a valid .adi file
- [ ] **ADIF-05**: Export round-trips losslessly — no field is dropped or renamed between import and export
- [ ] **ADIF-06**: ADIF parser handles real-world file variants: missing EOH, case-insensitive field names, varying EOR whitespace

### Multi-Operator

- [ ] **MULTI-01**: Multiple operators can log QSOs simultaneously without data conflicts or loss
- [ ] **MULTI-02**: Operator data is strictly isolated — no operator can read or write another operator's QSOs
- [ ] **MULTI-03**: Operator can see other operators' QSOs appear live in a shared station feed without page refresh (WebSocket or SSE)

## v2 Requirements

### Statistics & Awards

- **STAT-01**: Per-operator QSO count and band/mode breakdown dashboard
- **STAT-02**: DXCC entity derivation per QSO (from cty.dat, no external API)
- **STAT-03**: DXCC worked/confirmed entity tracking
- **STAT-04**: WAS, WAZ, and other award progress tracking

### Integrations

- **INTG-01**: Direct LoTW upload integration per operator (requires TQSL certificate management)
- **INTG-02**: Callsign lookup via QRZ XML or HamQTH (auto-fill operator details on QSO entry)
- **INTG-03**: eQSL direct upload integration

### Operations

- **OPS-01**: Per-operator activity audit log (who logged what and when)
- **OPS-02**: Import rollback by import_batch_id
- **OPS-03**: CSV export of QSO log

## Out of Scope

| Feature | Reason |
|---------|--------|
| Self-registration | Admin controls all accounts — no public signup endpoint |
| Award tracking (DXCC, WAS, etc.) | Complex rule sets, separate product concern — deferred to v2 |
| Mobile native app | Web UI is responsive; no native app in v1 |
| Real-time chat or club coordination | Not core to logging |
| LoTW direct upload | Per-operator TQSL certificate management adds significant operational complexity |
| Callsign lookup (QRZ/HamQTH) | External API dependency with subscription/rate-limit friction |
| ADIF validation against full spec enumerations | Warn on unknown values, don't reject — operators have non-standard entries |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 2 | Pending |
| AUTH-02 | Phase 2 | Pending |
| AUTH-03 | Phase 2 | Pending |
| AUTH-04 | Phase 1 | Pending |
| AUTH-05 | Phase 1 | Pending |
| AUTH-06 | Phase 1 | Pending |
| QSO-01 | Phase 3 | Pending |
| QSO-02 | Phase 3 | Pending |
| QSO-03 | Phase 3 | Pending |
| QSO-04 | Phase 3 | Pending |
| QSO-05 | Phase 3 | Pending |
| QSO-06 | Phase 3 | Pending |
| LOG-01 | Phase 3 | Pending |
| LOG-02 | Phase 3 | Pending |
| LOG-03 | Phase 3 | Pending |
| ADIF-01 | Phase 4 | Pending |
| ADIF-02 | Phase 4 | Pending |
| ADIF-03 | Phase 4 | Pending |
| ADIF-04 | Phase 4 | Pending |
| ADIF-05 | Phase 4 | Pending |
| ADIF-06 | Phase 4 | Pending |
| MULTI-01 | Phase 5 | Pending |
| MULTI-02 | Phase 5 | Pending |
| MULTI-03 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-03*
*Last updated: 2026-04-03 after roadmap creation*
