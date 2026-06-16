---
phase: 66
slug: aclog-operator-identity-routing
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-16
updated: 2026-06-16
---

# Phase 66 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| ACLog TCP API to ollog bridge | ACLog is an external TCP source controlled outside ollog. ollog consumes XML-like full-record data from it. | QSO records, operator identity, bridge host/port data |
| Authenticated profile UI to manual sync | A signed-in ollog operator triggers sync for their own saved bridge row. | Bridge ID, sync report, skipped-record examples |
| ACLog record to per-user QSO collection | Parsed ACLog records are transformed into ADIF-style dicts before insertion. | Operator-owned QSO data in `<username>_qsos` |
| Sync report to browser | Skipped records are summarized back to the authenticated operator. | Counts and bounded examples for missing/unmatched records |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-66-01 | Spoofing / Authorization | Manual sync and live bridge import | mitigate | `match_aclog_operator_identity()` gates every ACLog record on matched `OPERATOR` before QSO insertion; tests cover shared remote matched/missing/unmatched records. | closed |
| T-66-02 | Elevation of privilege / Tampering | Live bridge fallback behavior | mitigate | Identity-less `ENTEREVENT` fallback imports are blocked; unmatched or missing full-record identity is skipped and logged. | closed |
| T-66-03 | Spoofing | Identity candidate selection | mitigate | Only `OPERATOR` is authoritative in v3.5; station-like fields such as `STATION_CALLSIGN` do not authorize imports. | closed |
| T-66-04 | Information disclosure | Profile Settings sync report | mitigate | Skipped examples are bounded and contain only index, call, and concise reason/identity field; full QSO records are not rendered. | closed |
| T-66-05 | Regression / Integrity | Existing accepted ACLog imports | mitigate | Matching records continue through full-record preservation, Other/custom-field mapping, duplicate handling, rowHash, and per-user collection routing; focused regression tests passed. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Evidence

### T-66-01 — Shared Remote Cross-Import Prevention

- `app/aclog/sync.py` checks `match_aclog_operator_identity(record, user)` before `_map_other_slots_to_custom_fields()` and before `ingest_qso_record()`.
- `app/aclog/client.py` checks `match_aclog_operator_identity(record, user)` before live bridge `_map_other_slots_to_custom_fields()` and `ingest_qso_record()`.
- `tests/test_aclog_client.py::test_manual_sync_filters_missing_and_unmatched_operator_records` proves only matching records reach ingest.
- `tests/test_aclog_client.py::test_live_bridge_ingests_only_matching_full_record_identity` and `test_live_bridge_skips_unmatched_full_record_identity` cover live bridge matched/unmatched behavior.

### T-66-02 — Missing Identity Fallback Prevention

- `app/aclog/client.py` logs and skips pending `ENTEREVENT` records when the bridge disconnects, a new event supersedes a pending one, or no matching full record is returned.
- `tests/test_aclog_client.py::test_handle_full_record_mismatch_skips_enterevent_fallback` proves a mismatched full-record response does not insert the base `ENTEREVENT`.

### T-66-03 — Shared Station Callsign Safety

- `app/aclog/identity.py` uses `ACLOG_OPERATOR_IDENTITY_FIELDS = ("OPERATOR",)` and intentionally excludes station-like fields.
- `tests/test_aclog_identity.py::test_station_callsign_does_not_authorize_shared_station_record` proves a station-only field remains missing.
- `tests/test_aclog_identity.py::test_operator_identity_takes_precedence_over_station_callsign` proves a conflicting `OPERATOR` remains unmatched even when station callsign matches.

### T-66-04 — Report Data Minimization

- `app/aclog/sync.py` uses `_append_example()` with a fixed `ACLOG_SYNC_EXAMPLE_LIMIT = 5`.
- Examples contain only `index`, `call`, and `reason`.
- `templates/log/aclog_sync_result.html` renders aggregate counts and bounded examples, not full records.

### T-66-05 — Existing Behavior Preservation

- `tests/test_aclog_client.py::test_manual_sync_counts_imported_duplicates_and_errors` preserves imported, duplicate, and error reporting for matching records.
- `tests/test_aclog_client.py::test_handle_full_record_response_ingests_enriched_record` verifies full-record field preservation for accepted matching records.
- Focused verification command passed: `.venv/bin/python -m pytest tests/test_aclog_identity.py tests/test_aclog_client.py tests/test_profile_ui.py` — 18 passed, 5 skipped.

---

## Accepted Risks Log

No accepted risks.

---

## Residual Notes

- Real shared-ACLog hardware smoke testing was skipped in UAT because this environment has no live shared ACLog host. Deterministic simulated ACLog API tests cover the security-critical import and skip decisions.
- `ruff` is not installed in `.venv`, so lint verification remains a tooling limitation rather than an open security threat.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-16 | 5 | 5 | 0 | Codex |

---

## Verification Commands

Passed:

- `.venv/bin/python -m pytest tests/test_aclog_identity.py tests/test_aclog_client.py tests/test_profile_ui.py` — 18 passed, 5 skipped
- `.venv/bin/python -m compileall app/aclog tests/test_aclog_identity.py tests/test_aclog_client.py tests/test_profile_ui.py`

Blocked:

- `.venv/bin/python -m ruff check app/aclog tests/test_aclog_identity.py tests/test_aclog_client.py tests/test_profile_ui.py` — `No module named ruff`

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-16
