---
phase: 69-core-flow-instrumentation-and-documentation
plan: 69-01
subsystem: observability
tags: [internal-logs, qso-import, aclog, udp, auth, api-tokens, docs, tests]
requires:
  - phase: 67
    provides: MongoDB-backed internal logger, settings, masking, retention, and baseline instrumentation
  - phase: 68
    provides: Admin Logs page, live updates, filters, pagination, and formatted JSON details
provides:
  - Safe internal application logs for ADIF import completion outcomes
  - Manual ACLog sync lifecycle, processed, skipped, failed, and completion logs
  - Safe operator/OAuth login and API-token action logs
  - Focused event-contract tests for import, sync, auth/token, and UDP callback events
  - Admin documentation coverage matrix for representative application log events
affects: [internal-logs, qso, aclog, udp, auth, tokens, docs, tests]
tech-stack:
  added: []
  patterns:
    - Additive event instrumentation through failure-isolated `app_logger`
    - Fake app logger tests for exact event contracts without MongoDB
    - Source documentation updated without committing generated MkDocs `site/` churn
key-files:
  modified:
    - app/aclog/sync.py
    - app/auth/router.py
    - app/qso/service.py
    - app/qso/ui_router.py
    - app/tokens/router.py
    - docs/admin-guide/application-logs.md
    - tests/test_aclog_client.py
    - tests/test_internal_logs.py
    - tests/test_udp_pipeline.py
requirements-completed:
  - OBS-01
  - OBS-02
  - OBS-03
  - OBS-04
  - OBS-05
duration: 45 min
completed: 2026-06-19
---

# Phase 69 Plan 69-01: Core Flow Instrumentation Reconciliation Summary

**Core flow logging reconciliation for import, manual ACLog sync, auth/token actions, and event documentation**

## Accomplishments

- Added `qso_import_completed` internal logs to ADIF import with operator and accepted/duplicate/error counts, without raw file contents or full record payloads.
- Added route-level ADIF import logs for browser and API imports: `qso_import_started`, `qso_import_request_completed`, and `qso_import_failed`, so admins can see the import operation boundary directly.
- Added manual ACLog sync internal logs for `bridge_sync_started`, `bridge_sync_records_received`, `bridge_sync_qso_processed`, `bridge_sync_qso_skipped`, `bridge_sync_failed`, and `bridge_sync_completed`.
- Added safe logs for OAuth login success/failure, operator UI login success/failure/logout, REST API-token create/revoke, and operator UI API-token create/revoke.
- Added strict fake-logger tests for import summary logs, manual sync processed/skipped/failed events, auth/token metadata safety, and UDP protocol callback events.
- Updated the admin application logs guide with a compact coverage matrix of representative event names and reinforced `CALL`/`MYCALL`/`OPERATOR` meanings.

## Decisions Made

- Kept all event changes additive; no existing event names were renamed or normalized.
- Used safe identifiers and counts only for auth/token/import logs. Plaintext tokens and hashes remain out of metadata.
- Kept manual sync QSO report behavior unchanged; internal logs now mirror outcomes without changing counts or import decisions.
- Restored generated MkDocs `site/` output after docs verification and committed only source documentation changes.

## Deviations From Plan

None.

## Verification

Passed:

- `uv run pytest tests/test_internal_logs.py tests/test_aclog_client.py tests/test_udp_pipeline.py tests/test_tokens.py` - 52 passed.
- `uv run python -m compileall app tests/test_internal_logs.py tests/test_aclog_client.py tests/test_udp_pipeline.py` - passed after approved escalation because sandboxed `uv` could not open `/Users/roy/.cache/uv`.
- `uv run mkdocs build --strict` - passed.
- `git diff --check` - passed.

Notes:

- `rg --pcre2` found only the existing `asyncio.create_task(app_logger...)` protocol callback sites in `app/udp/server.py` and `app/aclog/client.py`; no unscheduled async logger coroutine was introduced.

## Self-Check: PASSED

- OBS-01 through OBS-05 are covered by implemented logs, existing Phase 67 logs, and focused tests/source checks.
- Sensitive credentials, tokens, hashes, cookies, authorization headers, raw ADIF payloads, UDP datagrams, and ACLog TCP payloads are not logged by the new instrumentation.
- Existing QSO import, duplicate, UDP, token, and ACLog sync behavior remains unchanged aside from failure-isolated logging side effects.

## User Setup Required

None.

## Next Phase Readiness

Phase 69 is executed and ready for `/gsd-verify-work 69`.

---
*Phase: 69-core-flow-instrumentation-and-documentation*
*Completed: 2026-06-19*
