---
phase: 54
slug: operator-clear-log
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-06
---

# Phase 54 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` / `tests/` |
| **Quick run command** | `uv run pytest tests/test_qso.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_qso.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 54-01-01 | 01 | 1 | CLR-03 | — | delete_many filtered by _operator | unit | `uv run pytest tests/test_qso.py::test_clear_operator_log -x -q` | ❌ W0 | ⬜ pending |
| 54-01-02 | 01 | 1 | CLR-02 | — | password verify before delete | unit | `uv run pytest tests/test_qso.py::test_clear_operator_log_wrong_password -x -q` | ❌ W0 | ⬜ pending |
| 54-02-01 | 02 | 2 | CLR-01 | — | Danger Zone renders in profile | manual | See manual verifications | N/A | ⬜ pending |
| 54-02-02 | 02 | 2 | CLR-02 | — | Modal shows correct QSO count | manual | See manual verifications | N/A | ⬜ pending |
| 54-02-03 | 02 | 2 | CLR-04 | — | Success message shows deleted count | manual | See manual verifications | N/A | ⬜ pending |
| 54-02-04 | 02 | 2 | CLR-05 | — | Wrong password shows inline error | manual | See manual verifications | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_qso.py::test_clear_operator_log` — stub for CLR-03
- [ ] `tests/test_qso.py::test_clear_operator_log_wrong_password` — stub for CLR-05

*Existing infrastructure covers shared fixtures and conftest.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Danger Zone section visible on profile page | CLR-01 | UI rendering requires browser | Navigate to `/log/profile`, scroll to bottom, verify "Danger Zone" section with "Clear my log" button |
| Modal shows correct QSO count | CLR-02 | HTMX modal requires browser | Click "Clear my log", verify modal shows exact count matching `db.qsos.count_documents({_operator: callsign, _deleted: False})` |
| Success message shows deleted count | CLR-04 | HTMX response requires browser | Submit correct password, verify inline message shows count of deleted QSOs |
| Wrong password shows inline error in modal | CLR-05 | HTMX error response requires browser | Submit wrong password, verify error shown inside modal, modal stays open |
| Zero QSO operator sees count of 0 | CLR-02 | Requires test operator account | Login as operator with no QSOs, open modal, verify count is 0 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
