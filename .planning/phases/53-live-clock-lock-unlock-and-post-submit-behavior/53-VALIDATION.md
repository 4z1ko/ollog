---
phase: 53
slug: live-clock-lock-unlock-and-post-submit-behavior
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-28
---

# Phase 53 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (regression guard); manual browser verification (frontend) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `npm run build && npm run verify` |
| **Full suite command** | `uv run pytest tests/` |
| **Estimated runtime** | ~30 seconds (pytest) + ~5 seconds (npm verify) |

---

## Sampling Rate

- **After every task commit:** Run `npm run build && npm run verify` (confirms dark: classes emitted)
- **After every plan wave:** Run `uv run pytest tests/ -x -q` (backend regression guard)
- **Before `/gsd-verify-work`:** Full suite must be green + manual browser walkthrough of all 7 success criteria
- **Max feedback latency:** 35 seconds

---

## Per-Task Verification Map

All phase requirements are pure frontend JavaScript/DOM behaviors. They are not testable with pytest. The backend test suite is used as a regression guard only.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 53-01-01 | 01 | 1 | DATE-01, DATE-02 | — | N/A | manual | — | ✅ | ⬜ pending |
| 53-01-02 | 01 | 1 | DATE-03 | — | N/A | manual | — | ✅ | ⬜ pending |
| 53-01-03 | 01 | 1 | DATE-04 | — | N/A | manual | — | ✅ | ⬜ pending |
| 53-01-04 | 01 | 1 | TIME-01, TIME-02 | — | N/A | manual | — | ✅ | ⬜ pending |
| 53-01-05 | 01 | 1 | TIME-03 | — | N/A | manual | — | ✅ | ⬜ pending |
| 53-01-06 | 01 | 1 | TIME-04 | — | N/A | manual | — | ✅ | ⬜ pending |
| 53-01-07 | 01 | 1 | TIME-05 | — | N/A | manual | — | ✅ | ⬜ pending |
| 53-01-08 | 01 | 1 | RESET-01 | — | N/A | manual | — | ✅ | ⬜ pending |
| 53-01-09 | 01 | 1 | RESET-02 | — | N/A | manual | — | ✅ | ⬜ pending |
| 53-01-10 | 01 | 1 | RESET-03 | — | N/A | manual | — | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test files required — all behaviors are frontend-only and verified manually.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Date pre-filled with UTC YYYYMMDD, readonly, padlock icon | DATE-01, DATE-02 | JavaScript/DOM; no pytest hook | Open form; check date input value matches `new Date().toISOString().slice(0,10).replace(/-/g,'')` and has `readonly` attribute |
| Date padlock toggles readonly | DATE-03 | UI interaction | Click padlock icon; verify `readonly` removed and icon changes; click again to re-lock |
| Invalid date rejected inline | DATE-04 | Client-side validation | Enter `20260132`; submit; verify inline error visible and form not submitted |
| Time pre-filled with UTC HHMMSS, auto-updates every second | TIME-01, TIME-02 | Real-time JavaScript behavior | Open form; verify time field value increments each second and matches UTC |
| Time padlock stops auto-update | TIME-03 | UI interaction | Click padlock; verify clock stops; enter manual value; click again to restart |
| HHMM normalized to HHMM00 | TIME-04 | POST body inspection | Enter `1430` in unlocked time; open DevTools Network tab; submit form; verify POST body contains `TIME_ON=143000` |
| Invalid time rejected inline | TIME-05 | Client-side validation | Enter `9999`; verify inline error and form blocked |
| Reset toggle present in submit row | RESET-01 | DOM check | Verify toggle widget in submit row with two states: "Reset to live UTC" / "Keep current date/time" |
| "Keep current" preserves fields | RESET-02 | Post-submit state | Select "Keep current"; submit QSO; verify date, time, and lock state unchanged after swap |
| "Reset to live UTC" re-locks fields | RESET-03 | Post-submit state | Select "Reset to live UTC"; submit QSO; verify both fields locked, clock restarted, live UTC values restored |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 35s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
