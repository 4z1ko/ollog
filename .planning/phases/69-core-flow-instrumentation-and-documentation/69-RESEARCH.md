# Phase 69: Core Flow Instrumentation and Documentation - Research

**Researched:** 2026-06-19
**Status:** Complete

## Objective

Determine what is already instrumented from Phase 67/68, identify remaining gaps against OBS-01 through OBS-05, and define the safest implementation approach for Phase 69 without changing QSO behavior.

## Current Coverage

Phase 67 already shipped broad internal logging:

- `app/main.py` logs main service startup/shutdown, UDP listener start/stop, ACLog bridge manager start/stop, and backup scheduler start/stop.
- `app/admin_main.py` logs admin service startup/shutdown.
- `app/database.py` logs MongoDB connection and close events.
- `app/qso/router.py` logs HTTP API QSO receive, insert, duplicate, update, update failure, update duplicate, and delete outcomes.
- `app/qso/service.py` logs shared QSO validation rejects, duplicates, insert failures, and inserts for background ingestion sources.
- `app/udp/server.py` logs UDP parse/routing rejects, datagram receive, transport errors, transport close, and listener bind.
- `app/aclog/client.py` logs live ACLog connect/disconnect/reconnect, skipped QSOs, and processed QSOs.
- `app/aclog/manager.py` logs bridge task start/stop and reconcile failure.
- `app/admin/ui_router.py`, `app/admin/router.py`, and `app/internal_logs/router.py` log many admin UI/API actions, including log settings changes.
- `docs/admin-guide/application-logs.md` documents log levels, stored fields, masking, retention, ADIF field meaning, filters, live updates, and Phase 68 pagination/details behavior.

## Gaps And Risks Found

### G-69-01: UDP async logging dispatch needs contract coverage

`app/udp/server.py` dispatches several synchronous protocol callbacks via `asyncio.create_task(app_logger...)`. That can be valid, but it is easy to regress because these calls are not awaited directly. Phase 69 tests should prove the expected event names are emitted for:

- `udp_datagram_received`
- `udp_transport_error`
- `udp_transport_closed`
- parse/routing rejects from `_handle_datagram()`

The executor should verify that every async logger call is either awaited in async code or explicitly scheduled from synchronous callbacks.

### G-69-02: Manual ACLog sync is not using the internal logger

`app/aclog/sync.py` currently reports sync outcomes through the Python module logger and returned `ACLogSyncReport`, but the visible code does not call `app_logger`. OBS-04 explicitly includes manual sync, record import, skip, duplicate, and error outcomes. Phase 69 should instrument:

- sync start/connect failure
- records received
- skipped missing identity
- skipped unmatched identity
- imported accepted record
- duplicate/already-present record
- import error/rejected record
- sync completed summary

Metadata should include safe bridge/source context and should not include secrets.

### G-69-03: ADIF import outcomes need internal log visibility

`app/qso/service.py::import_qsos_from_bytes()` returns accepted/duplicate/error counts but does not emit internal application logs for the import flow. OBS-02 includes import outcomes. Phase 69 should log:

- import started or parsed
- validation/import errors at summary level or per representative error where useful
- duplicate outcomes
- insert success outcomes
- import completed summary
- file-size rejection in the UI/API wrapper if applicable

Do not log raw file contents or full ADIF payloads.

### G-69-04: Operator auth and token actions are partially uncovered

Admin auth actions are already logged in `app/admin/ui_router.py`, but operator login/logout in `app/qso/ui_router.py`, OAuth token login in `app/auth/router.py`, and API-token create/revoke in `app/tokens/router.py` / operator UI token routes are not visibly using `app_logger`. OBS-05 includes authentication and admin actions without credentials. Phase 69 should add safe logs for:

- operator login succeeded/failed
- OAuth token login succeeded/failed
- operator logout if useful
- API token created/revoked through REST and UI

Do not log passwords, bearer tokens, plaintext API tokens, hashes, authorization headers, or full cookies. Safe token metadata is limited to token id/name/prefix and owner username/callsign.

### G-69-05: Documentation needs a coverage matrix

`docs/admin-guide/application-logs.md` explains the logging system, but it does not yet list the major operational flows and representative event names now available. Phase 69 should add coverage-focused documentation, not a troubleshooting runbook.

## Recommended Implementation Strategy

Use one gap-reconciliation plan:

1. Add strict event-contract tests first with monkeypatched/fake `app_logger` objects where possible.
2. Fill only missing instrumentation and async-dispatch defects found by those tests.
3. Update documentation with a compact flow/event coverage matrix.
4. Run focused tests and lightweight compile/docs checks.

Avoid broad event renaming. Preserve existing event names unless a concrete defect is found.

## Validation Architecture

Use layered validation:

- Unit-style tests with fake loggers for event name, source, transport, qso/bridge metadata, and sensitive-value exclusion.
- Existing `tests/test_internal_logs.py` for logger storage, masking, query, and live broadcast behavior.
- Existing ingestion/bridge tests where available to confirm QSO behavior remains unchanged.
- Static checks for no raw secret fields in new log metadata.
- Documentation verification with MkDocs strict build when docs change.

## Security Notes

- Treat log records as admin-visible operational data, not a place for raw payloads.
- Do not log ADIF file contents, full UDP datagrams, passwords, tokens, API keys, bearer tokens, cookies, or connection strings.
- Prefer identifiers that are already visible to the operator/admin: username, callsign, bridge id/name, host/port when already configured, QSO id, event status, counts.
- Logging must remain failure-isolated and must not alter QSO insert, duplicate, update, delete, or import behavior.

## RESEARCH COMPLETE

