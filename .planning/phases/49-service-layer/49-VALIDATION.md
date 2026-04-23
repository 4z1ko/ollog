---
phase: 49
slug: service-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-23
---

# Phase 49 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio 9.0.2 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_service_sort.py tests/test_sse_sentinel.py tests/test_view_dict.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_service_sort.py tests/test_sse_sentinel.py tests/test_view_dict.py -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 49-01-01 | 01 | 0 | SORT-04 | T-49-01 | `_ALLOWED_SORT_FIELDS` frozenset declared; logger set up | unit | `uv run pytest tests/test_service_sort.py -x` | ❌ W0 | ⬜ pending |
| 49-01-02 | 01 | 1 | SORT-04 | T-49-01 | Invalid sort field rejected, fallback to default, WARNING logged | unit | `uv run pytest tests/test_service_sort.py -x` | ❌ W0 | ⬜ pending |
| 49-01-03 | 01 | 1 | — | — | `created_at` key present in `_qso_to_view_dict()` output | unit | `uv run pytest tests/test_view_dict.py -x` | ❌ W0 | ⬜ pending |
| 49-01-04 | 01 | 1 | SORT-03 | — | `#auto-refresh-ok` sentinel rendered for `-_created_at` and `-qso_date_utc`; absent for other sorts | integration | `uv run pytest tests/test_sse_sentinel.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_service_sort.py` — stubs for SORT-04 (allowlist guard, WARNING log, fallback, all 10 valid values accepted); direct `get_qso_page()` call pattern — follow `test_operator_isolation.py`
- [ ] `tests/test_sse_sentinel.py` — stubs for SORT-03 (sentinel rendered for `-qso_date_utc` and `-_created_at`; absent for `CALL` sort); use `httpx.AsyncClient` + `ASGITransport` + JWT cookie pattern from `test_log_view_notify_sound.py`
- [ ] `tests/test_view_dict.py` — stubs for `_qso_to_view_dict()` `created_at` key presence; unit test, no MongoDB required, construct `QSO(...)` (not `model_construct()`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Browser live feed fires on `-_created_at` sort | SORT-03 | Requires running SSE connection in a browser | Log in, sort by "Entry time ↓", verify table auto-updates when new QSO arrives via SSE |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
