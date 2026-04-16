# Requirements: ollog

**Defined:** 2026-04-16
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss

## v2.4 Requirements

### Live Refresh (Fix)

- [ ] **LIVE-01**: UDP-inserted QSOs trigger the SSE live table refresh — the `watch_qsos` watcher task is hardened against unhandled exceptions and Python 3.12+ GC (strong reference stored in `app.state`)
- [ ] **LIVE-02**: The LIVE/OFFLINE indicator stays accurate — green only when events are actually flowing, not just when the SSE HTTP connection is open

### Page 2+ Badge

- [ ] **LIVE-03**: When new QSOs arrive while the operator is on page 2+ or has active filters, a "N new QSO(s)" badge appears in the log view header
- [ ] **LIVE-04**: Clicking the badge dismisses it (resets counter to zero) — no page jump, no auto-scroll

### Sound Notification

- [ ] **SND-01**: A brief audio tone plays in the browser when a new QSO arrives via SSE (Web Audio API synthesized tone — no external audio file)
- [ ] **SND-02**: The tone only plays after the operator has interacted with the page at least once (browser autoplay policy compliant)
- [ ] **SND-03**: Sound notifications are off by default

### Profile Toggle

- [ ] **SND-04**: The operator's Profile Settings page has a "Sound notifications" on/off toggle
- [ ] **SND-05**: The sound preference is persisted per-operator in MongoDB (survives page reload and session restart)

## Future Requirements

### Enhanced Live Log

- **LIVE-F01**: Real-time row insertion — new QSOs animate in at the top of the table without a full reload
- **LIVE-F02**: Auto-scroll to latest — lock mode that keeps the table pinned to newest entries
- **LIVE-F03**: Live refresh on page 2+ (not just badge) — configurable opt-in

### Enhanced Sound

- **SND-F01**: Volume control for tone notification
- **SND-F02**: Selectable tone pitch or pattern
- **SND-F03**: Per-band or per-mode filtering for tone trigger

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-jump to page 1 on new QSO | Interrupts browsing history — dismissed by user |
| Toast/overlay notification | Visual interrupt — badge is sufficient |
| Volume slider | Scope creep for v2.4 |
| localStorage sound preference | Server-side is correct for shared station computer |
| CDN audio files or howler.js | Web Audio API synthesized tone is zero-dep and sufficient |
| Real-time row insertion (no reload) | HTMX SSE swap is simpler and correct; animation deferred |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LIVE-01 | TBD | Pending |
| LIVE-02 | TBD | Pending |
| LIVE-03 | TBD | Pending |
| LIVE-04 | TBD | Pending |
| SND-01 | TBD | Pending |
| SND-02 | TBD | Pending |
| SND-03 | TBD | Pending |
| SND-04 | TBD | Pending |
| SND-05 | TBD | Pending |

**Coverage:**
- v2.4 requirements: 9 total
- Mapped to phases: TBD (roadmapper assigns)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-16*
*Last updated: 2026-04-16 after requirements confirmed*
