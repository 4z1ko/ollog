---
phase: 69
slug: core-flow-instrumentation-and-documentation
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-19
verified: 2026-06-19
---

# Phase 69 — Security

> Per-phase security verification for core flow instrumentation and documentation.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Operator/admin HTTP clients ↔ FastAPI routes | Browser, OAuth, API-token, and import routes emit operational logs while preserving existing auth flows. | Usernames, callsigns, role names, token identifiers/prefixes, import counts, file metadata |
| QSO ingestion services ↔ internal logger | ADIF import, QSO service, UDP, and ACLog sync paths write failure-isolated application log records. | QSO IDs, contacted-station calls, counts, duplicate/reject reasons, source/module metadata |
| Remote logging software ↔ bridge/sync code | ACLog and UDP callbacks add observability without changing QSO routing or ownership decisions. | Bridge name/id/host/port, ACLog identity fields, status/disposition counts, UDP remote address/byte counts |
| Internal logger ↔ MongoDB/admin viewer | Sanitized structured logs are stored and later rendered by the admin logs UI from Phase 68. | Log metadata, error details, event types, transport/source names |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-69-01 | Information Disclosure | New import, auth, token, UDP, and ACLog instrumentation | mitigate | Phase 69 logs only safe identifiers and counts; tests assert forbidden metadata keys and plaintext token/hash values are absent. The underlying logger masking from Phase 67 remains in the storage path. | closed |
| T-69-02 | Denial of Service / Reliability | QSO ingestion and auth/admin flows | mitigate | New log calls use the existing failure-isolated `app_logger` and preserve route/service return shapes; no business success path depends on log storage. | closed |
| T-69-03 | Tampering / Integrity | QSO ownership, duplicate handling, collections, and ACLog identity matching | mitigate | Instrumentation is additive and does not alter ownership/routing, duplicate detection, rowHash, collection selection, or ACLog identity matching; focused regression tests passed. | closed |
| T-69-04 | Information Disclosure / Integrity | Local-station attribution in logs | mitigate | Documentation and tests keep ADIF semantics explicit: `CALL` is contacted station, `MYCALL`/setup Call is local station, and `OPERATOR` is operator value; skipped ACLog logs do not use contacted-station `CALL` as local station identity. | closed |
| T-69-05 | Denial of Service / Operational Quality | Log volume and severity choices | mitigate | Routine import/sync/auth summaries use `Info`, rejected/skipped outcomes use `Warn`, operation failures use `Error`, and no raw ADIF/UDP/ACLog payload dumps are logged. | closed |
| T-69-06 | Reliability | Async logger dispatch in UDP/ACLog callbacks | mitigate | Async functions await logger calls; synchronous protocol callbacks schedule logger coroutines with `asyncio.create_task()`. UDP callback regression tests verify datagram/error/closed log events are emitted. | closed |

---

## Verification Evidence

| Threat | Evidence |
|--------|----------|
| T-69-01 | `app/qso/service.py` logs `qso_import_completed` with operator and counts only; `app/auth/router.py`, `app/qso/ui_router.py`, and `app/tokens/router.py` log auth/token events with username/callsign/role/token id/name/prefix only. `tests/test_internal_logs.py` asserts `password`, `token`, `full_token`, `hashed_token`, `authorization`, and `cookie` are absent from metadata and plaintext token/hash values do not appear in recorded events. |
| T-69-02 | Phase 69 uses `await app_logger.*` through the existing Phase 67 logger service. The execution summary records that existing import, duplicate, UDP, token, and ACLog sync behavior remains unchanged aside from failure-isolated logging side effects. |
| T-69-03 | `app/aclog/sync.py` still routes records through `ingest_qso_record()` with the authenticated user's collection and existing identity checks; `tests/test_aclog_client.py` verifies accepted, duplicate, skipped missing/unmatched, failed, and completed manual sync outcomes without changing report counts. The Phase 69 summary records 52 focused tests passing. |
| T-69-04 | `tests/test_aclog_client.py` asserts skipped manual sync records include contacted-station `call` only as QSO context and do not add `local_station` or `station_call` from `CALL`. `docs/admin-guide/application-logs.md` documents `CALL`, `MYCALL`/setup Call, and `OPERATOR` meanings and says contacted-station `CALL` is not used as the source station identifier. |
| T-69-05 | `app/aclog/sync.py` uses `bridge_sync_started`, `bridge_sync_records_received`, `bridge_sync_qso_processed`, and `bridge_sync_completed` at `Info`; skipped records use `Warn`; failures use `Error`. ADIF import logs counts and file metadata, not raw file contents or full record payloads. |
| T-69-06 | `app/udp/server.py` schedules synchronous protocol callback logs via `asyncio.create_task(app_logger.debug/warn/info(...))`; async startup and ingest paths await logger calls. `tests/test_udp_pipeline.py` verifies `udp_datagram_received`, `udp_transport_error`, and `udp_transport_closed` callback events. |

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-19 | 6 | 6 | 0 | Codex inline security audit |

## Notes

- This review verified the plan-time threat model in `69-01-PLAN.md`; no retroactive STRIDE expansion was required.
- The new logs intentionally include contacted-station callsign as QSO context where useful, but not as local station ownership/source identity.
- Phase 69 did not introduce new storage, authentication, authorization, or admin-view access paths beyond the Phase 67/68 logging system.
- The Phase 69 execution summary records the relevant focused verification: internal log, ACLog, UDP, token tests; Python compile; MkDocs strict build; and `git diff --check`.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-19
