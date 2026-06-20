---
phase: 70
slug: admin-application-log-controls
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-20
---

# Phase 70 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Admin browser -> Admin UI routes | Authenticated admin HTMX requests, log table refreshes, and current-browser live feed controls | Admin session cookie, filter parameters, clear confirmation request |
| Admin UI routes -> MongoDB application_logs | Admin route deletes stored application log records and creates a forced audit record | Application log records, deleted count, sanitized audit metadata |
| Application logger -> Admin browser | Recent log rows are rendered through templates and near-live updates | Sanitized log message, source, event type, metadata, error detail |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-70-01 | Tampering / Data loss | Clear Log Messages action | mitigate | `clear_application_logs()` deletes only `ApplicationLog` records; tests verify settings and unrelated data are not targeted. | closed |
| T-70-02 | Repudiation | Clear audit trail | mitigate | Clear route deletes old records first, then force-saves a fresh `application_logs_cleared` audit record with deleted count and admin username. | closed |
| T-70-03 | Availability | Audit failure after clear | mitigate | Clear route treats failed audit persistence as non-fatal after deletion, returns clear success, and shows an audit-warning note. | closed |
| T-70-04 | Information integrity | Pause/Start live-feed control | mitigate | UI and docs scope Pause to the current browser live feed only; server-side logging, storage, and future log capture remain unchanged. | closed |
| T-70-05 | Availability / UX safety | Paused Recent Logs refresh behavior | mitigate | Pause gates only automatic SSE and polling updates; explicit filter, pagination, and Start-triggered refresh paths remain available. | closed |
| T-70-06 | Information integrity | Clear confirmation modal | mitigate | Confirmation copy states that all application log messages are cleared from the database and that QSO records, users, and log settings are not affected. | closed |
| T-70-07 | Usability / operational safety | Admin Recent Logs controls | mitigate | Controls reuse existing admin design tokens, compact responsive wrapping, and confirmation modal patterns; UAT verified visibility and behavior. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

No accepted risks.

---

## Evidence

| Threat ID | Evidence |
|-----------|----------|
| T-70-01 | `app/internal_logs/service.py` scopes deletion to `ApplicationLog.find({}).delete_many()`; `tests/test_internal_logs.py::test_clear_application_logs_deletes_only_application_logs` verifies settings preservation. |
| T-70-02 | `app/admin/ui_router.py` performs clear before `app_logger.info(..., event_type="application_logs_cleared", force=True)`; `tests/test_internal_logs.py::test_admin_logs_clear_confirm_deletes_then_force_logs` verifies order and metadata. |
| T-70-03 | `templates/admin/clear_application_logs_result.html` can report clear success with audit warning; `tests/test_internal_logs.py::test_admin_logs_clear_confirm_succeeds_when_audit_log_fails` covers the path. |
| T-70-04 | `templates/admin/logs.html` uses a client-side `logsLivePaused` flag and PAUSED/LIVE status; no backend logging threshold, storage, or broadcast code is changed by Pause. |
| T-70-05 | `templates/admin/logs.html` guards only SSE and interval polling; `window.refreshApplicationLogsTable` remains callable, and Start triggers immediate reconciliation. |
| T-70-06 | `templates/admin/clear_application_logs_modal.html` contains the locked clear-scope wording; modal copy is covered by focused tests. |
| T-70-07 | `70-UAT.md` records 5/5 passed checks for controls, pause suppression, start reconciliation, clear confirmation, and clear preservation behavior. |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-20 | 7 | 7 | 0 | Codex |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-20
