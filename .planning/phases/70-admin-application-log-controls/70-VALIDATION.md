---
phase: 70
slug: admin-application-log-controls
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-20
---

# Phase 70 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest via `uv run pytest`; source/template assertions in pytest; Tailwind/npm and MkDocs build checks |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_internal_logs.py` |
| **Full suite command** | `uv run pytest tests/` |
| **Estimated runtime** | ~5–30 seconds for focused tests, environment-dependent for full suite |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_internal_logs.py`
- **After every plan wave:** Run focused pytest plus affected build checks
- **Before `$gsd-verify-work`:** Focused pytest, compileall, CSS build/verify, MkDocs strict build, and `git diff --check` must be green
- **Max feedback latency:** 30 seconds for focused checks in a warm environment

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 70-01-01 | 70-01 | 0 | LOGCTRL-01 | T-70-04 / T-70-05 | Pause is current-browser only and gates automatic live updates without blocking explicit refreshes. | pytest source checks | `uv run pytest tests/test_internal_logs.py` | yes | green |
| 70-01-01 | 70-01 | 0 | LOGCTRL-02 | T-70-05 | Start resumes automatic updates and calls the table refresh path immediately. | pytest source checks | `uv run pytest tests/test_internal_logs.py` | yes | green |
| 70-01-01 | 70-01 | 0 | LOGCTRL-03 | T-70-04 | LIVE/PAUSED state and Pause/Start label/ARIA state are visible in the Recent Logs header. | pytest source checks | `uv run pytest tests/test_internal_logs.py` | yes | green |
| 70-01-02 | 70-01 | 1 | LOGCTRL-05 | T-70-01 / T-70-02 / T-70-03 | Clear deletes `ApplicationLog` records, refreshes the view, preserves future logging, and handles audit failure safely. | pytest async route/service tests | `uv run pytest tests/test_internal_logs.py` | yes | green |
| 70-01-02 | 70-01 | 1 | LOGCTRL-06 | T-70-01 | Admin routes use `require_admin_cookie`; clear helper touches `ApplicationLog` only and preserves `ApplicationLogSettings`. | pytest async route/service tests | `uv run pytest tests/test_internal_logs.py` | yes | green |
| 70-01-02 | 70-01 | 1 | LOGCTRL-07 | T-70-02 / T-70-03 | Clear writes best-effort forced `application_logs_cleared` audit metadata with admin username and deleted count only. | pytest async route tests | `uv run pytest tests/test_internal_logs.py` | yes | green |
| 70-01-03 | 70-01 | 1 | LOGCTRL-04 | T-70-06 / T-70-07 | Header clear button opens confirmation modal; modal explains scope and supports cancel before deletion. | pytest template/source checks | `uv run pytest tests/test_internal_logs.py` | yes | green |
| 70-01-03 | 70-01 | 1 | LOGCTRL-01–03 | T-70-04 / T-70-05 / T-70-07 | UI controls wrap in Recent Logs header and keep existing filter/pagination refresh behavior intact. | pytest template/source checks, UAT | `uv run pytest tests/test_internal_logs.py` | yes | green |
| 70-01-04 | 70-01 | 2 | LOGCTRL-08 | T-70-04 / T-70-06 | Admin docs explain current-browser Pause/Start scope, Clear Log Messages scope, and preservation guarantees. | docs/source checks and MkDocs build | `uv run mkdocs build --strict` | yes | green |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Audit 2026-06-20

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Evidence:

- `tests/test_internal_logs.py::test_admin_logs_page_has_pause_start_and_clear_controls`
- `tests/test_internal_logs.py::test_clear_application_logs_modal_uses_safety_copy`
- `tests/test_internal_logs.py::test_clear_application_logs_deletes_only_application_logs`
- `tests/test_internal_logs.py::test_admin_logs_clear_modal_renders_confirmation`
- `tests/test_internal_logs.py::test_admin_logs_clear_confirm_deletes_then_force_logs`
- `tests/test_internal_logs.py::test_admin_logs_clear_confirm_succeeds_when_audit_log_fails`
- `70-UAT.md` records 5/5 user-facing checks passed.
- `70-SECURITY.md` records 7/7 plan-time threats closed.

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s for focused checks
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-06-20
