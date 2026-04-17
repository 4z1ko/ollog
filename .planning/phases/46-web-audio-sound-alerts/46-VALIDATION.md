---
phase: 46
slug: web-audio-sound-alerts
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-17
---

# Phase 46 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pyproject.toml` (existing, no `[tool.pytest.ini_options]` section — uses defaults) |
| **Quick run command** | `uv run pytest tests/test_profile_api.py -x` |
| **Full suite command** | `uv run pytest tests/` |
| **Estimated runtime** | ~5 seconds (existing suite) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_profile_api.py -x`
- **After every plan wave:** Run `uv run pytest tests/`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 46-01-01 | 01 | 1 | SND-01 | — | `notify_sound` bool from JWT-validated User only; no user input reaches JS injection | integration | `uv run pytest tests/test_log_view_notify_sound.py -x` | ❌ Wave 0 | ⬜ pending |
| 46-01-02 | 01 | 1 | SND-01 | — | NOTIFY_SOUND renders as `"true"`/`"false"` (not Python `True`/`False`) | integration | `uv run pytest tests/test_log_view_notify_sound.py::test_notify_sound_true_injected -x` | ❌ Wave 0 | ⬜ pending |
| 46-01-03 | 01 | 1 | SND-01 + SND-02 | — | NOTIFY_SOUND renders as `"false"` when sound disabled | integration | `uv run pytest tests/test_log_view_notify_sound.py::test_notify_sound_false_injected -x` | ❌ Wave 0 | ⬜ pending |
| 46-02-01 | 02 | 1 | SND-01 | — | Tone plays on new QSO; no audio file fetch | manual | Browser DevTools: Network tab shows no audio file requests on QSO arrival | — | ⬜ pending |
| 46-02-02 | 02 | 1 | SND-02 | — | Autoplay gate: tone silent before user interaction | manual | Open fresh tab, wait for UDP QSO — confirm no tone; click anywhere, next QSO produces tone | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_log_view_notify_sound.py` — new file; tests `test_notify_sound_true_injected` and `test_notify_sound_false_injected`; uses async test client (httpx + FastAPI) authenticating via cookie, GETs `/log/view`, asserts rendered HTML contains `const NOTIFY_SOUND = "true"` or `"false"`.

*Infrastructure note: Existing `conftest.py` initializes only the `QSO` model. A `log_view()` test requires `User` model initialization and an HTTP test client. If setup cost is too high, the planner may treat backend rendering as manual-only and rely on quick-run regression coverage via the existing profile test suite — this is consistent with the project's existing pattern for rendering concerns.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Audible tone plays on new QSO | SND-01 | Browser audio synthesis is not testable with pytest | With sound enabled: log a QSO via UDP while on the log view page; confirm tone is heard |
| Tone silent before first page interaction | SND-02 | Browser autoplay policy is a browser-runtime enforcement | Open fresh tab; wait for UDP QSO; confirm no tone; click somewhere; wait for next QSO; confirm tone |
| No audio file fetches | SND-01 | Network tab inspection required | Chrome DevTools → Network → filter by Media; confirm no audio file requests on QSO arrival |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
