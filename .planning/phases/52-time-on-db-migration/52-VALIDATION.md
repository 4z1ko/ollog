---
phase: 52
slug: time-on-db-migration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-27
---

# Phase 52 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio 1.3.0 (STRICT mode) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_migration.py -v` |
| **Full suite command** | `uv run pytest tests/` |
| **Estimated runtime** | ~5 seconds (real MongoDB required on localhost:27017) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_migration.py -v`
- **After every plan wave:** Run `uv run pytest tests/`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 52-01-01 | 01 | 1 | DB-01 | — | N/A | integration | `uv run pytest tests/test_migration.py::test_normalize_time_on_pads_4digit -v` | ❌ W0 | ⬜ pending |
| 52-01-02 | 01 | 1 | DB-01 | — | N/A | integration | `uv run pytest tests/test_migration.py::test_normalize_time_on_idempotent -v` | ❌ W0 | ⬜ pending |
| 52-01-03 | 01 | 1 | DB-02 | — | N/A | integration | `uv run pytest tests/test_migration.py::test_parse_adif_datetime_accepts_hhmm -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_migration.py` — new file with stubs for DB-01 and DB-02 tests

*Note: `tests/conftest.py` already exists; `pytest-asyncio` and `motor` already installed.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
