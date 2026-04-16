---
phase: 43
slug: stats-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
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
| 43-01-01 | 01 | 1 | STATS-01 | — | N/A | smoke | `uv run pytest tests/test_stats.py -x` | ✅ | ⬜ pending |
| 43-01-02 | 01 | 1 | STATS-02 | — | N/A | smoke | `uv run pytest tests/test_stats.py -x` | ✅ | ⬜ pending |
| 43-01-03 | 01 | 1 | STATS-03 | — | N/A | smoke | `uv run pytest tests/test_stats.py -x` | ✅ | ⬜ pending |
| 43-01-04 | 01 | 1 | STATS-04 | — | N/A | smoke | `uv run pytest tests/test_stats.py -x` | ✅ | ⬜ pending |
| 43-01-05 | 01 | 1 | STATS-05 | — | N/A | manual | Load `/log/stats` in browser, verify subtitle text | N/A | ⬜ pending |
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
| Stats nav link highlighted on `/log/stats` | STATS-01 | Jinja2 template rendering, no server-side assertion | Load `/log/stats` in browser; confirm "Stats" link has `nav-item-active` class |
| DXCC entity scalar visible in chart subtitle | STATS-05 | Template rendering, no test assertion | Load `/log/stats`; verify subtitle shows "By DXCC Entity · N entities" |
| Charts re-initialize on theme toggle | STATS-08 | Browser JS event, not testable in pytest | Toggle theme; verify all 3 charts re-render with mode-correct colors and no stale canvas error |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
