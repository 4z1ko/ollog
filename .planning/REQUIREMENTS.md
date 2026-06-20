# Requirements: ollog v3.6 Internal Application Logging

**Defined:** 2026-06-18
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss.

## v3.6 Requirements

### Logging Foundation

- [x] **LOG-01**: Admin-visible internal logging supports the levels `Trace`, `Debug`, `Info`, `Warn`, `Error`, and `Fatal` in that severity order.
- [x] **LOG-02**: The app saves only log events at or above the configured minimum level, defaulting to `Info`.
- [x] **LOG-03**: Each saved log record includes timestamp, level, source/module, message, optional event type, optional correlation/request ID, optional QSO ID, optional bridge/source name, optional remote logging software name, transport type, structured metadata, and sanitized error details when relevant.
- [x] **LOG-04**: Sensitive values such as passwords, tokens, API keys, secrets, and full connection strings are masked before logs are stored.
- [x] **LOG-05**: Logs are stored in MongoDB with efficient indexes for timestamp, level, source/module, and correlation/request ID.
- [x] **LOG-06**: Log retention prevents unbounded growth, defaulting to 30 days and using an expiry mechanism compatible with configurable retention.

### Admin Operations

- [x] **ADMINLOG-01**: Admin can configure the active minimum log level from the admin area.
- [x] **ADMINLOG-02**: Admin can configure log retention days from the admin area.
- [x] **ADMINLOG-03**: Admin can open a Logs page and see recent MongoDB-backed application logs.
- [x] **ADMINLOG-04**: Admin can filter logs by level, source/module, text search, and date/time range.
- [x] **ADMINLOG-05**: The Logs page updates live or near-live using the app's existing SSE pattern.
- [x] **ADMINLOG-06**: Admin help text explains every log level and the default behavior.

### Instrumentation

- [x] **OBS-01**: Startup, shutdown, MongoDB connection success/failure, UDP listener state, ACLog bridge manager state, and backup scheduler state are logged.
- [x] **OBS-02**: HTTP API/UI QSO receive, validation failures, insert success, duplicate detection, update, delete, and import outcomes are logged.
- [x] **OBS-03**: UDP receive/parse/reject/accept/duplicate outcomes are logged.
- [x] **OBS-04**: ACLog bridge connect/disconnect/reconnect, manual sync, record import, skip, duplicate, and error outcomes are logged.
- [x] **OBS-05**: Authentication and admin actions, including log-level configuration changes, are logged without storing credentials.

## Future Requirements

- Cross-node aggregation controls for multi-instance deployments.
- Export/download of filtered application logs.
- Per-source dynamic logging thresholds.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Replacing Python/process logs | This milestone adds MongoDB-backed internal app logs for admin visibility; process logs still serve container/runtime diagnostics. |
| External log shipping | Useful later, but not required for local admin debugging. |
| Full distributed tracing | Correlation IDs are supported opportunistically; complete trace propagation is a later observability layer. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LOG-01 | Phase 67 | Complete |
| LOG-02 | Phase 67 | Complete |
| LOG-03 | Phase 67 | Complete |
| LOG-04 | Phase 67 | Complete |
| LOG-05 | Phase 67 | Complete |
| LOG-06 | Phase 67 | Complete |
| ADMINLOG-01 | Phase 68 | Complete |
| ADMINLOG-02 | Phase 68 | Complete |
| ADMINLOG-03 | Phase 68 | Complete |
| ADMINLOG-04 | Phase 68 | Complete |
| ADMINLOG-05 | Phase 68 | Complete |
| ADMINLOG-06 | Phase 68 | Complete |
| OBS-01 | Phase 69 | Complete |
| OBS-02 | Phase 69 | Complete |
| OBS-03 | Phase 69 | Complete |
| OBS-04 | Phase 69 | Complete |
| OBS-05 | Phase 69 | Complete |

**Coverage:**
- v3.6 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0

---
*Requirements defined: 2026-06-18*
*Last updated: 2026-06-19 after v3.6 milestone audit*
