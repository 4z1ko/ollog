---
phase: 67-logging-foundation
plan: 01
subsystem: observability
tags: [logging, mongodb, admin, sse, qso-ingestion, masking]
requires:
  - phase: 61
    provides: Per-user QSO collection routing for REST, browser, ADIF, API-token, UDP, and ACLog write paths
  - phase: 63
    provides: ACLog full-record bridge import flow
  - phase: 64
    provides: Manual ACLog sync route and report patterns
  - phase: 66
    provides: ACLog identity-filtered bridge and sync behavior
provides:
  - MongoDB-backed internal application log and settings models
  - Reusable async internal logger with level thresholding and sensitive metadata masking
  - TTL-based retention and query indexes for application log viewing
  - Live log broadcast manager and admin log API/UI plumbing
  - Instrumentation across service startup, QSO ingestion, UDP, ACLog, auth/admin, backup, and restore flows
affects: [admin, qso, udp, aclog, database, docs, tests]
tech-stack:
  added: []
  patterns:
    - Internal logging is failure-isolated and never raises into app flows
    - Application log settings are cached with explicit refresh on admin views
    - Sensitive structured metadata is sanitized before storage and broadcast
key-files:
  created:
    - app/internal_logs/__init__.py
    - app/internal_logs/manager.py
    - app/internal_logs/models.py
    - app/internal_logs/router.py
    - app/internal_logs/service.py
    - templates/admin/log_row.html
    - templates/admin/logs.html
    - templates/admin/logs_settings_result.html
    - templates/admin/logs_table.html
    - docs/admin-guide/application-logs.md
    - tests/test_internal_logs.py
  modified:
    - app/database.py
    - app/main.py
    - app/admin_main.py
    - app/admin/router.py
    - app/admin/ui_router.py
    - app/qso/router.py
    - app/qso/service.py
    - app/udp/server.py
    - app/aclog/client.py
    - app/aclog/manager.py
    - templates/admin/users.html
    - templates/admin/backup.html
    - templates/admin/restore.html
    - docs/admin-guide/index.md
    - mkdocs.yml
    - static/css/output.css
key-decisions:
  - "Use MongoDB TTL expiry via expires_at so application logs cannot grow forever."
  - "Use severity ordering for threshold checks while preserving the requested display levels."
  - "Force-save settings-change and restore-completion audit records so threshold changes cannot hide those events."
  - "Keep logging failure-isolated so observability cannot break QSO ingestion or admin workflows."
patterns-established:
  - "Call app_logger from important flows with source, event_type, transport, and safe metadata."
  - "Use structured metadata for operational context and rely on logger sanitization for sensitive keys."
  - "Use the same SSE pattern as the QSO feed for live admin log updates."
requirements-completed:
  - LOG-01
  - LOG-02
  - LOG-03
  - LOG-04
  - LOG-05
  - LOG-06
duration: 70 min
completed: 2026-06-18
---

# Phase 67 Plan 01: Logging Foundation Summary

**MongoDB-backed internal application logging with threshold settings, retention, masking, live admin streaming, and core ingestion instrumentation**

## Performance

- **Duration:** 70 min
- **Started:** 2026-06-18T00:00:00Z
- **Completed:** 2026-06-18T00:00:00Z
- **Tasks:** 5 planned foundation tasks plus integrated admin/instrumentation work
- **Files modified:** 27

## Accomplishments

- Added `app/internal_logs/` with Beanie log/settings documents, severity ordering, default `Info` threshold, default 30-day retention, TTL index, query indexes, metadata sanitization, and failure-isolated async logging.
- Registered the new documents in database initialization and added startup/shutdown/MongoDB lifecycle logging.
- Added admin log JSON endpoints and a Jinja/HTMX Logs page with configurable level/retention, filters, and live SSE updates.
- Added structured logging to HTTP QSO creation/update/delete, service-level ingestion/validation/duplicate/insert outcomes, UDP parse/routing errors, ACLog connect/reconnect/skip/process events, admin auth/user actions, backup, restore, and log settings changes.
- Added admin guide documentation explaining log levels, storage fields, retention, masking, and the distinction between contacted-station `CALL`, local-station `MYCALL`/station fields, and `OPERATOR`.
- Added focused unit tests for level thresholding, forced audit logging, masking, retention expiry, live broadcast, and paginated log API output.

## Task Commits

1. **Tasks 67-01-01 through 67-01-05: internal log models/service, admin viewer/API, instrumentation, docs, and tests** - `a821a65` (feat)

## Files Created/Modified

- `app/internal_logs/models.py` - Application log/settings Beanie documents, level constants, TTL/index definitions.
- `app/internal_logs/service.py` - Reusable logger, threshold checks, sanitization, settings cache, query helpers, and dict serialization.
- `app/internal_logs/manager.py` - Async queue broadcaster for live log SSE.
- `app/internal_logs/router.py` - Admin JSON API for querying logs and updating logging settings.
- `app/database.py` - Registers internal log documents and records MongoDB lifecycle events.
- `app/main.py` and `app/admin_main.py` - Logs app startup/shutdown and service lifecycle events.
- `app/qso/service.py` and `app/qso/router.py` - Logs QSO receive, validation, duplicate, insert, update, delete, and failure outcomes.
- `app/udp/server.py` - Logs UDP receive, parse, routing, transport, and handler errors.
- `app/aclog/client.py` and `app/aclog/manager.py` - Logs bridge task, connect, disconnect, reconnect, skip, and processed-QSO events.
- `app/admin/router.py` and `app/admin/ui_router.py` - Logs admin auth, user actions, backup/restore, log settings, and renders the Logs page.
- `templates/admin/logs.html`, `templates/admin/logs_table.html`, `templates/admin/log_row.html`, `templates/admin/logs_settings_result.html` - Admin log viewer UI.
- `docs/admin-guide/application-logs.md` and `docs/admin-guide/index.md` - Admin documentation for the feature.
- `tests/test_internal_logs.py` - Unit coverage for logger behavior and log API shape.

## Decisions Made

- `severity` is stored alongside the display `level` so filters can efficiently implement "Warn and above" behavior.
- Retention is implemented with `expires_at` and a TTL index instead of a cleanup job, keeping operational overhead low.
- Application logging is explicitly failure-isolated; if the log collection is unavailable or uninitialized, the app flow continues.
- Settings updates and restore completion logs use `force=True` so important audit events are preserved even when the new threshold would normally suppress them.
- Generated MkDocs `site/` output was not committed for this phase to avoid noisy generated churn; source docs and strict build verification were kept.

## Deviations from Plan

### Scope Expansion

**1. Added Phase 68/69-facing admin UI and instrumentation while executing Phase 67**
- **Found during:** Implementation execution
- **Issue:** The requested user story asked for the full internal logging system in one pass, while the GSD roadmap split it across Phases 67-69.
- **Fix:** Implemented the foundation plus admin viewer/configuration and core flow instrumentation together in `a821a65`, while keeping this summary scoped to Phase 67's foundation requirements.
- **Files modified:** Admin templates/routes, QSO/UDP/ACLog/admin instrumentation files, docs, and tests.
- **Verification:** Focused tests, compile checks, Tailwind verification, and strict MkDocs build passed.
- **Committed in:** `a821a65`

---

**Total deviations:** 1 scope expansion.
**Impact on plan:** The implementation exceeds the Phase 67 foundation scope and covers substantial Phase 68/69 behavior. No production behavior change was intended for existing QSO ingestion beyond adding failure-isolated logs.

## Issues Encountered

- `gsd-sdk` is not available on PATH in this shell, so this execution was reconciled manually from planning files, git evidence, and verification output.
- `tests/test_qso_api.py` could not run in this local environment because MongoDB advertises the replica-set host as `mongodb:27017`, which is not resolvable from the host shell.

## Verification

Passed:

- `uv run pytest tests/test_internal_logs.py tests/test_aclog_client.py tests/test_aclog_identity.py tests/test_udp_pipeline.py tests/test_qso_service_collections.py` - 45 passed
- `uv run python -m compileall app tests/test_internal_logs.py`
- `npm run verify`
- `uv run mkdocs build --strict`
- `git diff --check`

Blocked:

- `uv run pytest tests/test_qso_api.py` - local MongoDB replica-set hostname resolution error for `mongodb:27017`.

## Self-Check: PASSED

- LOG-01 through LOG-06 are covered by code and focused tests.
- Sensitive fields are masked before storage and broadcast.
- Logs below the configured threshold are skipped unless explicitly force-saved for audit events.
- Retention uses MongoDB TTL index behavior.
- Existing QSO ingestion behavior remains unchanged aside from failure-isolated logging side effects.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 67 is ready for `$gsd-verify-work 67`. Because the implementation commit already includes admin viewer/configuration and core instrumentation, Phases 68 and 69 should either be verified against the existing commit or reconciled with follow-up summaries rather than reimplemented from scratch.

---
*Phase: 67-logging-foundation*
*Completed: 2026-06-18*
