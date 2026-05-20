---
phase: 45
slug: 45-sound-preference-model
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-17
---

# Phase 45 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_profile_api.py -x` |
| **Full suite command** | `uv run pytest tests/` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_profile_api.py -x`
- **After every plan wave:** Run `uv run pytest tests/`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 45-01-01 | 01 | 1 | SND-03 | — | notify_sound defaults to False; no cross-operator write | integration | `uv run pytest tests/test_profile_api.py::test_notify_sound_default_false -x` | ❌ W0 | ⬜ pending |
| 45-01-02 | 01 | 1 | SND-05 | — | Toggling True persists to MongoDB | integration | `uv run pytest tests/test_profile_api.py::test_notify_sound_patch_true -x` | ❌ W0 | ⬜ pending |
| 45-01-03 | 01 | 1 | SND-05 | — | Toggling False after True persists correctly | integration | `uv run pytest tests/test_profile_api.py::test_notify_sound_patch_false -x` | ❌ W0 | ⬜ pending |
| 45-01-04 | 01 | 1 | SND-04 | — | Profile page shows checkbox in correct state | manual | Browser — check checkbox reflects DB value after save | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_profile_api.py` — add `test_notify_sound_default_false`, `test_notify_sound_patch_true`, `test_notify_sound_patch_false` (file exists — add new test functions only)

*All three tests are additive; existing test infrastructure covers fixtures and client setup.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Profile page shows checkbox unchecked by default for new operator | SND-04 | Template rendering requires browser; no headless test framework available | Create new operator, navigate to `/log/profile`, confirm "Sound Notifications" checkbox is unchecked |
| Checkbox reflects saved state after round-trip | SND-04 | Requires HTML form POST + page reload, not easily testable via API | Check checkbox, click Save, reload page, confirm checkbox is still checked |
| Unchecking after checked saves correctly | SND-04 | Verifies hidden-input ordering (Pitfall 1 from RESEARCH.md) | Enable sound, save; then uncheck, save, reload — confirm checkbox is unchecked |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
