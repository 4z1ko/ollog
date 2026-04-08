# Requirements: ollog v1.6 Live Log Table

**Defined:** 2026-04-08
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss

## v1 Requirements

### LIVE — Live Table Updates

- [ ] **LIVE-01**: Operator's log view table auto-refreshes when a new QSO is inserted while viewing page 1 with no active filters
- [ ] **LIVE-02**: Auto-refresh fires a re-fetch of `/log/view` (SSE-triggered via existing `/feed/station`) — operator QSO isolation preserved via JWT on every re-fetch
- [ ] **LIVE-03**: Auto-refresh is suppressed when operator is on page 2+, has active filters, or non-default sort — no disruptive mid-browse refresh
- [ ] **LIVE-04**: Auto-refresh is suppressed while an inline QSO edit row is open — unsaved edits are not lost
- [ ] **LIVE-05**: A "Live" indicator is visible in the log view when auto-refresh is active

### SESSION — Session Robustness

- [ ] **SESSION-01**: JWT session lifetime configurable via `JWT_EXPIRE_MINUTES` env var (default raised to 480 min) so overnight FT8 sessions don't hit auth expiry mid-session

## Future Requirements

### LIVE — Extended Live Features

- **LIVE-F01**: Per-operator SSE endpoint (`/feed/log`) so only that operator's inserts trigger re-fetch (avoids unnecessary cross-operator refreshes)
- **LIVE-F02**: Animated row highlight when new QSO appears (fade-in or brief highlight)

## Out of Scope

| Feature | Reason |
|---------|--------|
| SSE row injection into log table (sse-swap on tbody) | Bypasses filters, breaks pagination counts, incompatible with paginated view |
| Auto-refresh on page 2+ | Disruptive to browsing; user is reading history, not monitoring live |
| Auto-refresh with active filters | Client cannot evaluate server-side filter predicates — injected rows may violate active filter |
| Real-time QSO count update without re-fetch | Requires separate counter endpoint; re-fetch updates total naturally |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LIVE-01 | Phase 23 | Pending |
| LIVE-02 | Phase 23 | Pending |
| LIVE-03 | Phase 23 | Pending |
| LIVE-04 | Phase 23 | Pending |
| LIVE-05 | Phase 23 | Pending |
| SESSION-01 | Phase 24 | Pending |

**Coverage:**
- v1 requirements: 6 total
- Mapped to phases: 6
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-08*
*Last updated: 2026-04-08 — traceability filled after roadmap creation*
