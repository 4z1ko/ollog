---
phase: 55
slug: admin-clear-operator-log
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-07
---

# Phase 55 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pyproject.toml` (pytest config section) |
| **Quick run command** | `uv run pytest tests/test_admin_clear_log.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_admin_clear_log.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 55-01-01 | 01 | 0 | ACLR-01..05 | — | Test stubs only — no assertions yet | unit | `uv run pytest tests/test_admin_clear_log.py -x` | ❌ W0 | ⬜ pending |
| 55-02-01 | 02 | 1 | ACLR-01 | — | "Clear log" button visible in row actions | integration | `uv run pytest tests/test_admin_clear_log.py::test_clear_log_button_visible -x` | ❌ W0 | ⬜ pending |
| 55-02-02 | 02 | 1 | ACLR-02 | — | Modal shows callsign, QSO count, password field | integration | `uv run pytest tests/test_admin_clear_log.py::test_modal_shows_callsign_and_count -x` | ❌ W0 | ⬜ pending |
| 55-02-03 | 02 | 1 | ACLR-03 | T-auth | Admin password verifies against admin hash (not target) | integration | `uv run pytest tests/test_admin_clear_log.py::test_clear_correct_password -x` | ❌ W0 | ⬜ pending |
| 55-02-04 | 02 | 1 | ACLR-04 | — | Success fragment shows callsign + deleted count | integration | `uv run pytest tests/test_admin_clear_log.py::test_success_fragment_content -x` | ❌ W0 | ⬜ pending |
| 55-02-05 | 02 | 1 | ACLR-05 | T-auth | Wrong password → error, no deletion, modal stays | integration | `uv run pytest tests/test_admin_clear_log.py::test_wrong_password_no_delete -x` | ❌ W0 | ⬜ pending |
| 55-02-06 | 02 | 1 | ACLR-05 | — | Zero-QSO operator clears without error | integration | `uv run pytest tests/test_admin_clear_log.py::test_clear_zero_qsos -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_admin_clear_log.py` — stubs for ACLR-01 through ACLR-05 plus zero-QSO path

**Test fixture note:** Admin UI routes use `admin_token` cookie (not `access_token`).
Cookie fixture must use `{"Cookie": f"admin_token={token}"}`.
Test DB name: `ollog_admin_clearlog_test` (distinct from Phase 54's `ollog_clearlog_test`).

*Existing infrastructure covers framework — only the new test file is needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Modal renders correctly in dark mode | ACLR-02 | Visual inspection required | Load `/admin/ui/users`, click "Clear log", verify modal backdrop, button colors, and text are legible in dark mode |
| Cancel button dismisses modal without page reload | ACLR-02 | HTMX DOM swap not exercised by pytest | Click "Clear log", then click "Keep log" (cancel), verify modal disappears and table remains intact |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
