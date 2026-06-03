---
phase: 58
slug: configurable-qso-field-catalog-and-log-view-columns
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-03
---

# Phase 58 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_view_dict.py tests/test_service_sort.py tests/test_sse_sentinel.py` |
| **Full suite command** | `uv run pytest tests/test_view_dict.py tests/test_service_sort.py tests/test_sse_sentinel.py` plus `npm run build` when templates/classes change |
| **Estimated runtime** | ~30-90 seconds, excluding MongoDB skip/setup time |

---

## Sampling Rate

- **After every task commit:** Run the focused pytest command for touched behavior when feasible.
- **After every plan wave:** Run `uv run pytest tests/test_view_dict.py tests/test_service_sort.py tests/test_sse_sentinel.py`.
- **Before `/gsd verify-work`:** Focused tests and CSS build must pass, or failures must be explicitly documented as unrelated environment issues.
- **Max feedback latency:** 90 seconds for focused Python tests in a healthy local environment.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 58-01-01 | 01 | 1 | FIELDS-01..04, VERIFY-01..02 | T-58-01 | Unsafe internal/security fields cannot appear in selectable catalog | unit | `uv run pytest tests/test_view_dict.py` | yes | pending |
| 58-01-02 | 01 | 1 | TABLE-01..04, COLUMNS-02 | T-58-02 | Actions remain outside configurable fields; missing values render blank | unit/template | `uv run pytest tests/test_view_dict.py` | yes | pending |
| 58-01-03 | 01 | 1 | COLUMNS-01..05, TABLE-05 | T-58-03 | Stale localStorage keys are ignored; HTMX swaps reapply selected columns | source + integration | `uv run pytest tests/test_sse_sentinel.py` | yes | pending |
| 58-01-04 | 01 | 1 | TABLE-04..05 | T-58-04 | Sort allowlist remains restricted to current sortable fields | unit/integration | `uv run pytest tests/test_service_sort.py tests/test_sse_sentinel.py` | yes | pending |
| 58-01-05 | 01 | 1 | COLUMNS-05, VERIFY-03 | — | UI classes compile and bounded menu classes exist in generated CSS | build/source | `npm run build` | yes | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements:

- `tests/test_view_dict.py` exists and can be extended for catalog/value extraction.
- `tests/test_service_sort.py` exists and guards the sort allowlist.
- `tests/test_sse_sentinel.py` exists and guards HTMX/SSE table behavior.
- Tailwind build infrastructure exists via `npm run build`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Menu viewport fit and no visual overlap on narrow screens | COLUMNS-05 | Visual fit across screen widths is best checked in browser or screenshot after implementation | Open `/log/view`, open the gear menu on desktop and mobile/narrow viewport, confirm menu is bounded, scrollable, readable, and does not overflow the viewport. |

---

## Validation Sign-Off

- [x] All tasks have automated verify commands or existing Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verify.
- [x] Wave 0 covers all missing references.
- [x] No watch-mode flags.
- [x] Feedback latency target < 90s.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-06-03
