---
phase: 69
slug: core-flow-instrumentation-and-documentation
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-19
validated: 2026-06-19
---

# Phase 69 — Validation Strategy

> Nyquist validation audit for core flow instrumentation and documentation.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x with pytest-asyncio; Python compileall; MkDocs strict build |
| **Config file** | `pyproject.toml`, `mkdocs.yml` |
| **Quick run command** | `uv run pytest tests/test_internal_logs.py tests/test_aclog_client.py tests/test_udp_pipeline.py tests/test_tokens.py` |
| **Full suite command** | `uv run pytest tests/test_internal_logs.py tests/test_aclog_client.py tests/test_udp_pipeline.py tests/test_tokens.py && uv run python -m compileall app tests/test_internal_logs.py tests/test_aclog_client.py tests/test_udp_pipeline.py && uv run mkdocs build --strict && git diff --check` |
| **Estimated runtime** | ~1 second for focused pytest; ~2 seconds for compile/docs/diff checks in this environment |

---

## Sampling Rate

- **After event-contract changes:** Run `uv run pytest tests/test_internal_logs.py tests/test_aclog_client.py tests/test_udp_pipeline.py tests/test_tokens.py`.
- **After async callback changes:** Run focused UDP/ACLog tests and `uv run python -m compileall app tests/test_internal_logs.py tests/test_aclog_client.py tests/test_udp_pipeline.py`.
- **After documentation changes:** Run `uv run mkdocs build --strict` and restore generated `site/` churn unless intentionally committing docs output.
- **Before `$gsd-verify-work`:** Run focused pytest, compileall, MkDocs strict build, and `git diff --check`.
- **Max feedback latency:** < 5 seconds for focused Phase 69 checks.

---

## Requirement Coverage Map

| Requirement | Behavior | Automated Evidence | UAT Evidence | Status |
|-------------|----------|--------------------|--------------|--------|
| OBS-01 | Startup/shutdown, MongoDB, UDP listener, ACLog bridge, and backup scheduler lifecycle events are logged. | Existing Phase 67 lifecycle instrumentation plus Phase 69 source review; `tests/test_udp_pipeline.py` verifies UDP callback event emission. | `69-UAT.md` Tests 4 and 6 passed. | covered |
| OBS-02 | QSO receive, validation, insert, update, delete, duplicate, and import outcomes are logged across API/UI paths. | Existing Phase 67 QSO instrumentation plus Phase 69 import tests in `tests/test_internal_logs.py` for `qso_import_completed`, `qso_import_started`, and `qso_import_request_completed`. | `69-UAT.md` Tests 1 and 6 passed. | covered |
| OBS-03 | UDP and ACLog receive/parse/import/skip/error events include source/transport context without secrets. | `tests/test_aclog_client.py` verifies `bridge_sync_started`, `bridge_sync_records_received`, `bridge_sync_qso_processed`, `bridge_sync_qso_skipped`, `bridge_sync_failed`, and `bridge_sync_completed`; `tests/test_udp_pipeline.py` verifies UDP datagram/error/closed events. | `69-UAT.md` Tests 2, 4, and 6 passed. | covered |
| OBS-04 | Auth/admin actions and log configuration changes are logged without credentials. | `tests/test_internal_logs.py` verifies OAuth login and API-token create logs omit forbidden credential/token metadata; Phase 67/68 already covered admin/log-settings actions. | `69-UAT.md` Tests 3 and 6 passed. | covered |
| OBS-05 | Documentation and focused tests verify existing QSO behavior remains unchanged. | `docs/admin-guide/application-logs.md` documents event coverage and `CALL`/`MYCALL`/`OPERATOR` semantics; focused tests passed across internal logs, ACLog, UDP, and tokens. | `69-UAT.md` Tests 5 and 6 passed. | covered |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 69-01-01 | 69-01 | 0 | OBS-01 through OBS-05 | T-69-01, T-69-03, T-69-04, T-69-06 | Event contracts pin safe metadata, source/transport context, local-station semantics, and async callback events before/following implementation. | pytest | `uv run pytest tests/test_internal_logs.py tests/test_aclog_client.py tests/test_udp_pipeline.py tests/test_tokens.py` | yes | green |
| 69-01-02 | 69-01 | 1 | OBS-02, OBS-04, OBS-05 | T-69-01, T-69-02, T-69-03 | ADIF import and auth/token logs use safe identifiers/counts and preserve existing return shapes. | pytest + compile | `uv run pytest tests/test_internal_logs.py tests/test_tokens.py`; `uv run python -m compileall app tests/test_internal_logs.py tests/test_aclog_client.py tests/test_udp_pipeline.py` | yes | green |
| 69-01-03 | 69-01 | 1 | OBS-01, OBS-03, OBS-05 | T-69-02, T-69-03, T-69-04, T-69-06 | ACLog sync and UDP callback logs preserve routing/identity behavior, avoid raw payloads, and schedule/await logger calls correctly. | pytest + source check | `uv run pytest tests/test_aclog_client.py tests/test_udp_pipeline.py` | yes | green |
| 69-01-04 | 69-01 | 2 | OBS-01 through OBS-05 | T-69-01 through T-69-06 | Docs/checks confirm coverage matrix, ADIF field semantics, no secret leakage, no async logger coroutine defects, and regression safety. | pytest + docs/build checks + UAT + security | `uv run pytest tests/test_internal_logs.py tests/test_aclog_client.py tests/test_udp_pipeline.py tests/test_tokens.py`; `uv run mkdocs build --strict`; `git diff --check` | yes | green |

---

## Wave 0 Requirements

Existing pytest infrastructure covered Phase 69. Wave 0 added/updated focused event-contract tests in:

- `tests/test_internal_logs.py` — import, auth, token, live/admin log regressions, and forbidden metadata checks.
- `tests/test_aclog_client.py` — manual ACLog sync start/records/processed/skipped/failed/completed events and local-station attribution safety.
- `tests/test_udp_pipeline.py` — UDP protocol callback event emission.
- `tests/test_tokens.py` — token service/model regression coverage included in the focused Phase 69 command.

---

## Manual-Only Verifications

All Phase 69 behaviors have automated, source, UAT, and/or security verification. No manual-only gaps remain.

---

## Validation Commands Run

| Command | Result | Notes |
|---------|--------|-------|
| `uv run pytest tests/test_internal_logs.py tests/test_aclog_client.py tests/test_udp_pipeline.py tests/test_tokens.py` | passed | 53 tests passed |
| `uv run python -m compileall app tests/test_internal_logs.py tests/test_aclog_client.py tests/test_udp_pipeline.py` | passed | Required escalation because sandboxed `uv` could not access `/Users/roy/.cache/uv`; same command passed after approval |
| `uv run mkdocs build --strict` | passed | MkDocs warning banner only; generated `site/` output was restored per repo practice |
| `git diff --check` | passed | No whitespace/errors |

---

## UAT and Security Cross-Checks

- `69-UAT.md`: complete, 6/6 tests passed, 0 open issues.
- UAT-discovered near-live log rendering/polling/detail-state defects were fixed before final UAT completion and are backed by focused tests in `tests/test_internal_logs.py`.
- `69-SECURITY.md`: verified, `threats_open: 0`, 6/6 plan-time threats closed, no accepted risks.

---

## Validation Sign-Off

- [x] All tasks have automated verify evidence or UAT/security evidence.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covered all missing references.
- [x] No watch-mode flags used.
- [x] Feedback latency < 5 seconds for focused checks.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-06-19
