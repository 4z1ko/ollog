---
phase: 67
slug: logging-foundation
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-19
---

# Phase 67 Security Review: Logging Foundation

## Scope

Phase 67 adds MongoDB-backed application logging, log settings, log retention, sensitive-value masking, live log broadcast plumbing, admin log APIs/UI, and instrumentation across core app flows.

This is a retroactive STRIDE review because the phase plan predates a formal threat register. Review evidence came from:

- `app/internal_logs/models.py`
- `app/internal_logs/service.py`
- `app/internal_logs/router.py`
- `app/admin/ui_router.py`
- `app/database.py`
- `tests/test_internal_logs.py`
- `.planning/phases/67-logging-foundation/67-01-SUMMARY.md`
- `.planning/phases/67-logging-foundation/67-UAT.md`

## Trust Boundaries

| Boundary | Assets crossing boundary | Security expectation |
|----------|--------------------------|----------------------|
| App runtime -> MongoDB `application_logs` / `application_log_settings` | Operational messages, metadata, errors, retention/settings | Store only sanitized structured records; preserve availability if logging fails. |
| Admin browser -> Admin log UI/API/SSE | Log search filters, live log records, settings updates | Admin-only access; validate settings and filters. |
| QSO, UDP, ACLog, auth, backup, and admin flows -> Internal logger | QSO/bridge/admin context and error details | Do not expose secrets; include enough context for operations without changing primary behavior. |

## Threat Register

| ID | STRIDE | Area | Threat | Mitigation / Evidence | Status |
|----|--------|------|--------|-----------------------|--------|
| T-67-01 | Information Disclosure | `app/internal_logs/service.py` | Sensitive fields such as passwords, tokens, API keys, or MongoDB credentials could be persisted in log metadata or errors. | `sanitize_metadata()`, `_SENSITIVE_KEY_RE`, `_MONGO_CREDENTIAL_RE`, and `error_details()` mask sensitive keys and MongoDB URI credentials before storage. Tests cover sensitive key and URI masking. | Closed |
| T-67-02 | Information Disclosure / Elevation of Privilege | Admin log routes/UI/SSE | Non-admin users could read operational logs or live log streams. | JSON routes use `require_admin`; admin UI and live log stream routes use admin cookie dependencies. Existing auth patterns are reused instead of adding unauthenticated endpoints. | Closed |
| T-67-03 | Denial of Service | Logger service | A logging collection/init/write failure could break QSO ingestion or admin flows. | `InternalLogger.log()` catches `CollectionWasNotInitialized` and generic exceptions and returns `None`, keeping primary workflows isolated from logging failures. Focused tests cover failure-safe behavior. | Closed |
| T-67-04 | Denial of Service | MongoDB log collection | Logs could grow without bound and consume database storage. | `ApplicationLog.expires_at` has a TTL index; settings default to 30 days and retention is range-limited. Model tests verify indexes and retention expiry. | Closed |
| T-67-05 | Tampering | Log settings | Invalid or unauthorized log level/retention changes could suppress useful logs or create unsafe retention. | Settings update APIs are admin-only; log levels are normalized/validated; retention is constrained to 1-3650 days; invalid settings return controlled 400 responses. | Closed |
| T-67-06 | Repudiation | Admin/settings audit | Raising the minimum log level could hide the audit event for the settings change itself. | Log settings changes use forced logging so the audit record is persisted even when it is below the configured threshold. Regression coverage verifies forced logging. | Closed |
| T-67-07 | Information Disclosure | Instrumented call sites | New instrumentation could accidentally log plaintext auth credentials or API tokens. | Source review found instrumentation records operational context, not plaintext credentials. Token/password inputs remain consumed by auth logic and are not included in log metadata; sanitizer remains a second layer for future mistakes. | Closed |

## Accepted Risks

None.

## Audit Trail

| Date | Reviewer | Result |
|------|----------|--------|
| 2026-06-19 | Codex | 7 retroactive STRIDE threats reviewed; 7 closed; 0 open; 0 accepted risks. |

## Sign-Off

- [x] Sensitive log metadata and error details are masked before storage.
- [x] Admin log viewing, streaming, and settings endpoints require admin authentication.
- [x] Logging write failures do not fail primary QSO/admin workflows.
- [x] Log retention prevents unbounded database growth.
- [x] Log settings validation prevents invalid levels and unsafe retention values.
- [x] Settings-change audit records are force-saved.
- [x] No accepted security risks remain for Phase 67.

Security review status: **Verified**.
