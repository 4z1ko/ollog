# Requirements: ollog v2.2

**Defined:** 2026-04-15
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss

## v2.2 Requirements

Requirements for the Multi-Operator UDP milestone.

### UDP Routing

- [ ] **UDP-01**: When a UDP ADIF datagram contains an `OPERATOR` field whose value matches a registered, enabled operator callsign, the QSO is logged to that operator's personal log — overriding `UDP_OPERATOR` env var
- [ ] **UDP-02**: Operator identity resolution uses an in-memory callsign→User cache loaded at startup — no per-datagram MongoDB round-trip occurs during normal operation
- [ ] **UDP-03**: The operator cache is invalidated (dirty-flagged) whenever an operator is created, enabled, disabled, or has their callsign/profile updated — the cache reloads lazily on the next datagram that requires lookup
- [ ] **UDP-04**: If the datagram contains an `OPERATOR` field whose callsign does not match any registered enabled operator, the QSO is dropped and a WARNING is logged including the unrecognized callsign and source address
- [ ] **UDP-05**: If the datagram has no `OPERATOR` field and `UDP_OPERATOR` env var is set, the system falls back to `UDP_OPERATOR`-based routing (existing behavior preserved)
- [ ] **UDP-06**: `UDP_OPERATOR` env var is optional — if absent and the datagram contains no `OPERATOR` field, the QSO is dropped and a WARNING is logged

### Documentation

- [ ] **DOC-01**: `docs/deployment.md` updated — `UDP_OPERATOR` documented as optional fallback, multi-operator UDP routing behavior explained with example
- [ ] **DOC-02**: MkDocs static site rebuilt (`uv run mkdocs build --strict`) and committed to repo

## Future Requirements

### v3+ Enhancements

- **UDP-F01**: Per-sender IP allowlist (security boundary for multi-operator deployments)
- **UDP-F02**: UDP acknowledgment / replay protection (sequence numbers)
- **UDP-F03**: Real-time UDP ingestion metrics in admin UI (datagrams/sec, rejection rate)

## Out of Scope

| Feature | Reason |
|---------|--------|
| UDP authentication per-datagram | Loopback default is the security boundary; APP_OLLOG_TOKEN already handles auth for trusted networks |
| Per-operator UDP ports | Single port + OPERATOR field routing is simpler; multi-port adds ops burden |
| UDP multicast/broadcast | Niche use case; unicast covers all known ham radio logging tools |
| Admin UI for UDP routing status | Read logs; out of scope for this milestone |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| UDP-01 | Phase 41 | Pending |
| UDP-02 | Phase 41 | Pending |
| UDP-03 | Phase 41 | Pending |
| UDP-04 | Phase 41 | Pending |
| UDP-05 | Phase 41 | Pending |
| UDP-06 | Phase 41 | Pending |
| DOC-01 | Phase 41 | Pending |
| DOC-02 | Phase 41 | Pending |

**Coverage:**
- v2.2 requirements: 8 total
- Mapped to phases: 8 (100%)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-15*
*Last updated: 2026-04-15 — initial definition*
