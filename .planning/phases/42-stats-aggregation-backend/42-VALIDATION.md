---
phase: 42
slug: stats-aggregation-backend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 42 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pyproject.toml` (project root) |
| **Quick run command** | `uv run pytest tests/test_stats.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_stats.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 42-01-01 | 01 | 0 | STATS-06, STATS-07 | T-42-01 | Test stubs isolate by `_operator` and cover empty-state | unit | `uv run pytest tests/test_stats.py -x` | ❌ W0 | ⬜ pending |
| 42-01-02 | 01 | 1 | STATS-06 | T-42-01 | `get_stats()` returns only queried operator's data | integration | `uv run pytest tests/test_stats.py::test_stats_operator_isolation -x` | ❌ W0 | ⬜ pending |
| 42-01-03 | 01 | 1 | STATS-07 | — | `get_stats()` returns `total_qsos=0` and empty shape for empty log | integration | `uv run pytest tests/test_stats.py::test_stats_empty_log -x` | ❌ W0 | ⬜ pending |
| 42-01-04 | 01 | 1 | STATS-06 | T-42-02 | Route `/log/stats` returns 401 without auth cookie | integration | `uv run pytest tests/test_stats.py::test_stats_route_requires_auth -x` | ❌ W0 | ⬜ pending |
| 42-01-05 | 01 | 1 | STATS-07 | — | Route `/log/stats` returns 200 for operator with zero QSOs | integration | `uv run pytest tests/test_stats.py::test_stats_route_empty_log -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_stats.py` — stubs for STATS-06 (operator isolation) and STATS-07 (empty-state)
- [ ] Shared fixtures: `tests/conftest.py` already provides `test_db` fixture; stats tests may need the `isolation_test_db` pattern from `test_operator_isolation.py` which includes the `User` model alongside `QSO`

*Existing test infrastructure covers the framework setup — only the stats-specific test file needs to be created.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/log/stats` page renders in browser without visual errors | STATS-07 | Template rendering correctness requires visual inspection | Log in, navigate to `/log/stats`, confirm no Jinja2 errors and `total_qsos` renders in the stub |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
