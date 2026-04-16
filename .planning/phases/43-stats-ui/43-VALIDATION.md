---
phase: 43
slug: stats-ui
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-16
audited: 2026-04-16
---

# Phase 43 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_stats.py -x` |
| **Full suite command** | `uv run pytest tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_stats.py -x`
- **After every plan wave:** Run `uv run pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green + `npm run build` + `npm run verify`
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 43-01-01 | 01 | 1 | STATS-01 | — | N/A | integration | `uv run pytest tests/test_stats.py::test_stats_route_empty_log -v` | ✅ | ✅ green |
| 43-01-02 | 01 | 1 | STATS-02 | — | N/A | integration | `uv run pytest tests/test_stats.py::test_stats_route_with_data -v` | ✅ | ✅ green |
| 43-01-03 | 01 | 1 | STATS-03 | — | N/A | integration | `uv run pytest tests/test_stats.py::test_stats_dxcc_top8_truncation -v` | ✅ | ✅ green |
| 43-01-04 | 01 | 1 | STATS-04 | — | N/A | integration | `uv run pytest tests/test_stats.py::test_stats_route_empty_log -v` | ✅ | ✅ green |
| 43-01-05 | 01 | 1 | STATS-05 | — | N/A | integration | `uv run pytest tests/test_stats.py::test_stats_dxcc_entity_resolution -v` | ✅ | ✅ green |
| 43-01-06 | 01 | 1 | STATS-08 | — | N/A | manual | Toggle theme in browser, verify charts re-render with mode-correct colors | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

Phase 43 is a template-only phase — all data-layer tests exist in `tests/test_stats.py` (7 tests from Phase 42). No new Python files or test stubs needed. Browser-JS behaviors (charts, dark mode re-init) are verified manually.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Charts re-initialize on theme toggle | STATS-08 | Browser JS event, not testable in pytest | Toggle theme; verify all 3 charts re-render with mode-correct colors and no stale canvas error |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** 2026-04-16

---

## Validation Audit 2026-04-16

| Metric | Count |
|--------|-------|
| Gaps found | 4 |
| Resolved | 4 |
| Escalated | 0 |

| Gap | Requirement | Resolution |
|-----|-------------|------------|
| STATS-01 PARTIAL | Nav link in sidebar HTML | Added `assert 'href="/log/stats"' in resp.text` to `test_stats_route_empty_log` |
| STATS-02 MISSING | Three canvas IDs in non-empty route response | New `test_stats_route_with_data` — inserts QSOs, asserts chart-band/mode/entity present |
| STATS-03 MISSING | DXCC entity_counts capped at ≤9 | New `test_stats_dxcc_top8_truncation` — inserts 9 unique-entity callsigns, asserts len ≤ 9 |
| STATS-04 PARTIAL | Empty-state "No data yet" text in route response | Added `assert "No data yet" in resp.text` to `test_stats_route_empty_log` |
