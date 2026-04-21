---
phase: 48
slug: model-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-20
---

# Phase 48 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` / `pytest.ini` |
| **Quick run command** | `uv run pytest tests/test_qso.py tests/test_qso_schema.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_qso.py tests/test_qso_schema.py -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 48-01-01 | 01 | 1 | TS-01 | — | `_created_at` set at insert, not user-controlled | unit | `uv run pytest tests/test_qso.py -k "created_at" -q` | ❌ W0 | ⬜ pending |
| 48-01-02 | 01 | 1 | TS-02 | — | PATCH does not overwrite `_created_at` | unit | `uv run pytest tests/test_qso.py -k "created_at" -q` | ❌ W0 | ⬜ pending |
| 48-01-03 | 01 | 1 | TS-03 | — | compound index exists after startup | unit | `uv run pytest tests/test_qso_schema.py -q` | ✅ | ⬜ pending |
| 48-01-04 | 01 | 1 | TS-01 | — | startup backfill migration is idempotent | unit | `uv run pytest tests/test_qso.py -k "backfill" -q` | ❌ W0 | ⬜ pending |
| 48-01-05 | 01 | 1 | TS-01 | — | `_created_at` absent from GET API response | unit | `uv run pytest tests/test_qso.py -k "created_at" -q` | ❌ W0 | ⬜ pending |
| 48-01-06 | 01 | 1 | TS-01 | — | `_created_at` absent from ADIF export | unit | `uv run pytest tests/test_adif.py -k "created_at" -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_qso.py` — add test stubs for `_created_at` insert stamping, PATCH protection, API response exclusion
- [ ] `tests/test_adif.py` — add test stub for `_created_at` exclusion from ADIF export
- [ ] Update `tests/test_qso_schema.py` — update `test_qso_has_three_indexes` to expect 4 indexes after adding `operator_created_at_idx`

*Note: pytest and MongoDB test infrastructure already in place — only new test functions needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Startup migration log banner | TS-01 | Log output inspection | Start app, verify `INFO: _created_at backfill: N documents updated` appears in logs |
| ObjectId timestamp accuracy | TS-01 | Requires real MongoDB with known-age documents | Insert QSO, inspect `_created_at` vs `_id.generation_time` match |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
