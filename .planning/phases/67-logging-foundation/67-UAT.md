---
status: complete
phase: 67-logging-foundation
source:
  - .planning/phases/67-logging-foundation/67-01-SUMMARY.md
started: 2026-06-18T00:00:00Z
updated: 2026-06-18T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. MongoDB Log Models and Registration
expected: Application log and settings documents exist, include the required structured fields, and are registered during database initialization.
result: pass
evidence:
  - `app/internal_logs/models.py` defines `ApplicationLog` and `ApplicationLogSettings`.
  - `ApplicationLog` includes timestamp, level, severity, message, source, event type, correlation ID, QSO ID, bridge name, remote software, transport, metadata, error details, and `expires_at`.
  - `app/database.py` registers `ApplicationLog` and `ApplicationLogSettings` with Beanie.

### 2. Log Level Thresholding
expected: The logger defaults to Info behavior and stores only records at or above the active configured threshold.
result: pass
evidence:
  - `LOG_LEVELS` order is `Trace`, `Debug`, `Info`, `Warn`, `Error`, `Fatal`.
  - `DEFAULT_LOG_LEVEL` is `Info`.
  - `should_log()` compares normalized severities.
  - `InternalLogger.log()` returns without inserting when a record is below threshold unless `force=True`.
  - `tests/test_internal_logs.py::test_log_level_threshold_ordering` and `test_logger_saves_records_at_or_above_configured_level` passed.

### 3. Sensitive Metadata Masking
expected: Passwords, tokens, API keys, authorization headers, secrets, credentials, and MongoDB connection credentials are masked before storage/broadcast.
result: pass
evidence:
  - `app/internal_logs/service.py` masks sensitive dictionary keys with `***`.
  - MongoDB URI credentials are masked by `_MONGO_CREDENTIAL_RE`.
  - Metadata and error details are sanitized before `ApplicationLog` construction.
  - `tests/test_internal_logs.py::test_sensitive_metadata_is_masked` and logger metadata assertions passed.

### 4. Retention and Indexes
expected: Logs include an expiry timestamp and MongoDB indexes support timestamp, level/severity, source, correlation ID, and TTL retention.
result: pass
evidence:
  - `ApplicationLog.Settings.indexes` defines timestamp, level/timestamp, severity/timestamp, source/timestamp, correlation/timestamp, and TTL `expires_at` indexes.
  - `expires_at_for_retention()` defaults to a positive retention window and is used when saving logs.
  - `tests/test_internal_logs.py::test_log_expiry_uses_retention_days` passed.

### 5. Live Broadcast Plumbing
expected: Newly saved log records are broadcast to connected listeners for live admin viewing.
result: pass
evidence:
  - `app/internal_logs/manager.py` defines `LogConnectionManager` with `connect`, `disconnect`, and `broadcast`.
  - `InternalLogger.log()` calls `log_manager.broadcast(log_to_dict(log))` after insert.
  - `tests/test_internal_logs.py::test_log_manager_broadcast_emits_new_log_records` passed.

### 6. Failure Isolation
expected: Internal logging failures must not raise into QSO ingestion, bridge, or admin workflows.
result: pass
evidence:
  - `InternalLogger.log()` catches `CollectionWasNotInitialized` and all other exceptions, returning `None`.
  - Existing QSO/UDP/ACLog tests passed after instrumentation was added: `tests/test_aclog_client.py`, `tests/test_aclog_identity.py`, `tests/test_udp_pipeline.py`, and `tests/test_qso_service_collections.py`.

### 7. Focused Regression and Build Checks
expected: Phase 67 verification commands pass, and generated CSS/docs remain buildable.
result: pass
evidence:
  - `uv run pytest tests/test_internal_logs.py tests/test_aclog_client.py tests/test_aclog_identity.py tests/test_udp_pipeline.py tests/test_qso_service_collections.py` - 45 passed.
  - `uv run python -m compileall app tests/test_internal_logs.py` - passed.
  - `npm run verify` - passed.
  - `uv run mkdocs build --strict` - passed with existing informational MkDocs output.
  - `git diff --check` - passed.

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None.

## Notes

- `tests/test_qso_api.py` remains blocked in this local environment because MongoDB advertises the replica-set host as `mongodb:27017`, which is not resolvable from the host shell. This is an environment limitation already recorded in the Phase 67 summary, not a Phase 67 implementation gap.
- Phase 67 implementation includes work that overlaps Phases 68 and 69. Those phases should reconcile against the existing implementation before adding duplicate work.
