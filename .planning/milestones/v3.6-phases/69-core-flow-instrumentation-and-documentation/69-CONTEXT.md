# Phase 69: Core Flow Instrumentation and Documentation - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 69 reconciles and completes internal application logging coverage for core operational flows: service startup/shutdown, MongoDB lifecycle, HTTP/UI QSO paths, UDP ingestion, ACLog bridge/manual sync, auth/admin actions, and documentation/tests. Phase 67 already implemented broad instrumentation, so this phase should audit existing coverage against OBS-01 through OBS-05 and fill gaps without changing QSO behavior.

</domain>

<decisions>
## Implementation Decisions

### Reconciliation Depth
- **D-01:** Use gap-fill only. Audit existing Phase 67 instrumentation against OBS-01 through OBS-05, then add missing or weak events/tests/docs.
- **D-02:** Do not rename, reshape, or standardize existing event names, source names, metadata keys, or transport labels unless there is a clear defect. Avoid churn.

### Test Strictness
- **D-03:** Use exact event contracts for Phase 69 tests. Tests should assert precise event names and metadata shape for instrumented flows where feasible.
- **D-04:** Favor targeted tests around representative core flows and known gaps, but assertions should be strict enough to catch event-name and metadata regressions.

### Documentation Boundary
- **D-05:** Use coverage-focused documentation. Update docs to explain what flows are logged, how admins can filter/search them, and what fields/events they can expect.
- **D-06:** Do not expand into a full troubleshooting runbook in this phase. Scenario-based runbooks can be a future documentation enhancement.

### the agent's Discretion
- The planner may choose the specific gap-audit method and test fixture strategy.
- The planner may choose whether one plan or multiple plans best fits the scope, but should keep implementation tightly scoped to OBS-01 through OBS-05.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap And Requirements
- `.planning/ROADMAP.md` — Phase 69 goal and success criteria.
- `.planning/REQUIREMENTS.md` — OBS-01 through OBS-05 requirements.
- `.planning/STATE.md` — Current milestone context and known verification constraints.

### Prior Phase Artifacts
- `.planning/phases/67-logging-foundation/67-01-SUMMARY.md` — Existing logging implementation and instrumentation already shipped.
- `.planning/phases/67-logging-foundation/67-SECURITY.md` — Security expectations for masking, admin-only access, and failure isolation.
- `.planning/phases/67-logging-foundation/67-VALIDATION.md` — Existing validation coverage for the logging foundation.
- `.planning/phases/68-admin-log-configuration-and-viewer/68-01-SUMMARY.md` — Admin log viewer reconciliation and live-update fixes.
- `.planning/phases/68-admin-log-configuration-and-viewer/68-UAT.md` — UAT evidence for live log rendering behavior.
- `.planning/phases/68-admin-log-configuration-and-viewer/68-SECURITY.md` — Admin log viewer security constraints.
- `.planning/phases/68-admin-log-configuration-and-viewer/68-VALIDATION.md` — Admin log viewer validation coverage.

### Implementation Files
- `app/internal_logs/service.py` — Logger API, sanitization, settings, query helpers.
- `app/internal_logs/manager.py` — Live log broadcast manager.
- `app/internal_logs/models.py` — Log/settings schemas and indexes.
- `app/main.py` — Main app startup/shutdown, UDP, bridge, and scheduler lifecycle integration.
- `app/database.py` — MongoDB lifecycle logging.
- `app/qso/router.py` — HTTP/API QSO instrumentation.
- `app/qso/service.py` — Validation, duplicate, insert, and source-to-transport instrumentation.
- `app/udp/server.py` — UDP receive/parse/routing instrumentation.
- `app/aclog/client.py` — ACLog connect/reconnect/QSO processing instrumentation.
- `app/aclog/manager.py` — ACLog bridge manager task instrumentation.
- `app/admin/ui_router.py` and `app/admin/router.py` — Admin/auth/user/backup/restore/log-settings instrumentation.
- `docs/admin-guide/application-logs.md` — User-facing logging documentation.
- `tests/test_internal_logs.py` — Existing focused logging tests.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app_logger` from `app.internal_logs.service` should remain the only application logging entry point.
- `sanitize_metadata()` and `error_details()` should remain responsible for masking sensitive structured details before storage/broadcast.
- Existing tests in `tests/test_internal_logs.py` can be extended with fake loggers/monkeypatching for strict event contract checks without requiring live MongoDB.

### Established Patterns
- Logging is failure-isolated: instrumentation must not raise into QSO/admin/bridge flows.
- Structured log records use `source`, `event_type`, `transport`, optional `qso_id`, `bridge_name`, `remote_software`, and `metadata`.
- Admin settings updates and important audit events may use `force=True` when threshold suppression would hide critical admin evidence.
- Existing docs distinguish contacted station `CALL`, local station `MYCALL`/station call, and `OPERATOR`; preserve that language.

### Integration Points
- Main lifecycle: `app/main.py`, `app/admin_main.py`, `app/database.py`.
- QSO HTTP/UI/API and service layer: `app/qso/router.py`, `app/qso/ui_router.py`, `app/qso/service.py`.
- UDP ingestion: `app/udp/server.py`.
- ACLog bridge/manual sync: `app/aclog/client.py`, `app/aclog/manager.py`, `app/aclog/sync.py`, profile/admin routes if sync is triggered there.
- Admin/auth actions: `app/admin/ui_router.py`, `app/admin/router.py`, `app/auth/router.py`, token routes if relevant.

</code_context>

<specifics>
## Specific Ideas

- Phase 69 should be treated as reconciliation, not a broad refactor.
- Gap-fill only means existing event naming should be preserved unless an event is wrong or unsafe.
- Exact event-contract tests are preferred for core instrumentation behavior.
- Documentation should explain final coverage and filter/search usage, not become a full troubleshooting runbook.

</specifics>

<deferred>
## Deferred Ideas

- A scenario-based troubleshooting runbook for admins, such as “UDP QSO missing” or “ACLog disconnected,” is useful but out of scope for Phase 69 unless it is small enough to fit naturally into coverage-focused docs.
- Event naming/metadata normalization across the whole logging system is deferred unless a specific defect is found during Phase 69.

</deferred>

---

*Phase: 69-Core Flow Instrumentation and Documentation*
*Context gathered: 2026-06-19*
