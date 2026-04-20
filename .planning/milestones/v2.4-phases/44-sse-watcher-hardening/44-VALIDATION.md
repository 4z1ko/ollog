---
phase: 44
slug: sse-watcher-hardening
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 44 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | pyproject.toml (existing, `asyncio_mode` inferred from existing tests) |
| **Quick run command** | `uv run pytest tests/test_watcher.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~10 seconds (unit tests with mocks, no live MongoDB) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_watcher.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 44-01-01 | 01 | 0 | LIVE-01 | — | N/A | unit | `uv run pytest tests/test_watcher.py -x` | ❌ W0 | ⬜ pending |
| 44-01-02 | 01 | 1 | LIVE-01 | — | N/A | unit | `uv run pytest tests/test_watcher.py::test_watcher_survives_render_exception -x` | ❌ W0 | ⬜ pending |
| 44-01-03 | 01 | 1 | LIVE-01 | — | N/A | unit | `uv run pytest tests/test_watcher.py::test_watcher_task_stored_in_app_state -x` | ❌ W0 | ⬜ pending |
| 44-01-04 | 01 | 1 | LIVE-01 | — | N/A | unit | `uv run pytest tests/test_watcher.py::test_watcher_null_date_does_not_kill -x` | ❌ W0 | ⬜ pending |
| 44-02-01 | 02 | 1 | LIVE-02 | — | N/A | manual | Browser DevTools — see Manual-Only Verifications | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_watcher.py` — stubs for LIVE-01a, LIVE-01b, LIVE-01c (watcher exception isolation, app.state strong reference, null qso_date_utc handling)

*LIVE-02 (indicator accuracy) is manual-only — no Wave 0 test file needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LIVE indicator does NOT turn green on SSE connection open (before any event) | LIVE-02 | Browser JS logic; pytest cannot simulate htmx:sseOpen/sseMessage events against a real EventSource | Open `/log/view` in DevTools → check indicator is hidden before events → confirm no green on Network tab SSE connection open |
| LIVE indicator turns green only after first `htmx:sseMessage` with `type='new_qso'` | LIVE-02 | Same reason | POST a QSO → observe SSE event in EventStream tab → confirm indicator turns green after event frame arrives |
| LIVE indicator shows OFFLINE on SSE error / hidden on SSE close | LIVE-02 | Same reason | Stop server → observe `htmx:sseError` fires → confirm indicator shows OFFLINE |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
