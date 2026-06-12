---
phase: 64
slug: aclog-bridge-manual-sync
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-12
---

# Phase 64 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_aclog_parser.py tests/test_aclog_client.py` |
| **Full suite command** | `.venv/bin/python -m pytest tests/test_aclog_parser.py tests/test_aclog_client.py tests/test_profile_ui.py tests/test_qso_service_collections.py` |
| **Estimated runtime** | ~20 seconds when dependencies are installed |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/test_aclog_parser.py tests/test_aclog_client.py`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/test_aclog_parser.py tests/test_aclog_client.py tests/test_profile_ui.py tests/test_qso_service_collections.py`
- **Before `/gsd-verify-work`:** Full focused suite must be green or skipped only for documented missing MongoDB/dependency reasons
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 64-01-01 | 01 | 0 | ACSYNC-02, ACSYNC-03 | T-64-01 | TCP parser/client handles all-log response without live ACLog | unit | `.venv/bin/python -m pytest tests/test_aclog_parser.py tests/test_aclog_client.py` | ✅ | ⬜ pending |
| 64-01-02 | 01 | 1 | ACSYNC-03, ACSYNC-04, ACSYNC-05, ACSYNC-06, ACSYNC-07 | T-64-02 | Sync report counts accepted, duplicate, rejected records without overwriting | unit | `.venv/bin/python -m pytest tests/test_aclog_client.py tests/test_qso_service_collections.py` | ✅ | ⬜ pending |
| 64-01-03 | 01 | 1 | ACSYNC-01, ACSYNC-08, ACSYNC-09 | T-64-03 | Route only syncs authenticated user's saved bridge | route/template | `.venv/bin/python -m pytest tests/test_profile_ui.py tests/test_aclog_client.py` | ✅ | ⬜ pending |
| 64-01-04 | 01 | 2 | ACSYNC-01, ACSYNC-07 | — | Profile UI renders saved-row Sync and report target correctly | template | `.venv/bin/python -m pytest tests/test_profile_ui.py` | ✅ | ⬜ pending |
| 64-01-05 | 01 | 2 | ACSYNC-09 | — | Existing live bridge behavior and docs remain compatible | regression/docs | `.venv/bin/python -m pytest tests/test_aclog_client.py tests/test_aclog_parser.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_aclog_client.py` — add fake TCP/manual sync coverage for all-record command, timeout, report counts.
- [ ] `tests/test_profile_ui.py` — add route/template checks for saved-row-only Sync button and `#profile-result` targeting.
- [ ] Existing parser tests cover multi-record `LIST`; add a targeted case only if the manual sync reader needs a new message shape.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live ACLog all-log sync against real ACLog | ACSYNC-02, ACSYNC-05, ACSYNC-07 | Requires N3FJP ACLog running with TCP API and real log data | Save a bridge, press Sync, confirm "Missing QSOs imported" count, press Sync again, confirm no duplicate inserts. |

---

## Threat Model Seeds

| Threat | Requirement | Mitigation Expected In Plan |
|--------|-------------|-----------------------------|
| T-64-01: hung or malicious TCP peer keeps request open | ACSYNC-02, ACSYNC-07 | Fixed timeout; report failure through HTMX fragment. |
| T-64-02: sync imports duplicates or overwrites local QSOs | ACSYNC-05, ACSYNC-06 | Additive-only ingest; rowHash/duplicate paths count skipped records; no update/delete path. |
| T-64-03: operator guesses another bridge ID | ACSYNC-08 | Route looks up bridge only on authenticated `user.aclog_bridges` and uses `get_user_qso_collection(user)`. |

---

## Validation Sign-Off

- [x] All tasks have automated verification targets or manual-only rationale
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all missing references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-12
