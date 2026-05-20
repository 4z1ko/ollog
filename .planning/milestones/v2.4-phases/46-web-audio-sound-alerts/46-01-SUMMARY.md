---
phase: 46-web-audio-sound-alerts
plan: "01"
subsystem: audio-notifications
tags: [web-audio, sse, frontend, backend, sound-alerts]
status: complete
completed_tasks: 3
total_tasks: 3

dependency_graph:
  requires:
    - "Phase 45: notify_sound field on User model"
  provides:
    - "SND-01: 440 Hz synthesized tone on new QSO SSE event"
    - "SND-02: Autoplay policy compliant lazy AudioContext"
  affects:
    - "templates/log/log.html (IIFE script block)"
    - "app/qso/ui_router.py (log_view dependency)"

tech_stack:
  added: []
  patterns:
    - "Web Audio API (native browser, no npm deps)"
    - "Lazy AudioContext init on first user gesture"
    - "Jinja2 bool-to-string: '{{ true if x else false }}'"
    - "Fire-and-forget async tone playback"

key_files:
  created:
    - tests/test_log_view_notify_sound.py
  modified:
    - app/qso/ui_router.py
    - templates/log/log.html

decisions:
  - "D-03: NOTIFY_SOUND declared outside IIFE but in same <script> block"
  - "D-04: Jinja2 renders 'true'/'false' strings (not Python True/False) to avoid JS type mismatch"
  - "D-02: onFirstInteraction is idempotent — userInteracted guard prevents AudioContext re-creation"
  - "Tone fires BEFORE auto-refresh guards so it plays on page 2+ (resolves RESEARCH.md open question)"

metrics:
  duration_minutes: ~10
  completed_date: "2026-04-17"
  tasks_completed: 2
  files_modified: 3
---

# Phase 46 Plan 01: Web Audio Sound Alerts Summary

**One-liner:** Web Audio API 440 Hz synthesized tone wired to SSE new_qso events with lazy AudioContext init for autoplay policy compliance.

## Status

Tasks 1 and 2 complete and committed. Task 3 (browser verification) is a `checkpoint:human-verify` — awaiting operator confirmation before this plan can be marked fully complete.

## Tasks Completed

### Task 1: Backend dependency swap + integration tests

**Commit:** a0f6e4e

Changes to `app/qso/ui_router.py`:
- Replaced `callsign: str = Depends(get_current_operator_callsign_cookie)` with `user: User = Depends(get_current_user_cookie)` in `log_view()` signature
- Added `callsign = user.callsign` as first line of handler body to preserve all downstream callsign references
- Added `"notify_sound": user.notify_sound` to the `ctx` dict

New file `tests/test_log_view_notify_sound.py`:
- `test_notify_sound_false_injected`: verifies `const NOTIFY_SOUND = "false"` in rendered HTML when `user.notify_sound` is `False`
- `test_notify_sound_true_injected`: verifies `const NOTIFY_SOUND = "true"` in rendered HTML when `user.notify_sound` is `True`
- Both tests pass (2/2 green)

### Task 2: Web Audio JS wiring in log.html IIFE

**Commit:** ca3b38b

Replaced the `<script>` block (formerly lines 114-161) in `templates/log/log.html` with:

- `const NOTIFY_SOUND = "{{ 'true' if notify_sound else 'false' }}"` — declared outside IIFE so it's accessible from the IIFE scope
- `var AudioCtxClass = window.AudioContext || window.webkitAudioContext` — Safari fallback
- `var audioCtx = null; var userInteracted = false` — lazy init state
- `onFirstInteraction()` — idempotent handler, creates AudioContext on first click or keydown
- `async function playTone(ctx)` — 440 Hz sine wave with 10ms attack, 70ms sustain, 30ms decay (stops at 120ms), fire-and-forget call from SSE handler
- Sound check placed BEFORE `auto-refresh-ok` guard so tone fires on page 2+ and with active filters
- `htmx:sseError` and `htmx:sseClose` handlers updated to use `e.target` instead of `e.detail.elt` (per memory feedback on htmx SSE event detail format)

## Test Results

```
tests/test_log_view_notify_sound.py::test_notify_sound_false_injected PASSED
tests/test_log_view_notify_sound.py::test_notify_sound_true_injected PASSED
tests/test_profile_api.py (11 tests) — all PASSED (no regression)
```

## Task 3: Browser Verification (APPROVED)

**Type:** checkpoint:human-verify (blocking)
**Outcome:** Approved by operator 2026-04-17

Results:
1. ✓ Tone plays after page interaction — 440 Hz synthesized tone heard via Web Audio API
2. ✓ Autoplay gate confirmed — no tone in fresh tab before any click
3. ✓ Tone plays after clicking — autoplay gate cleared correctly
4. ✓ Sound disabled — no tone when notify_sound is off
5. ✓ No audio file requests — DevTools Network/Media tab shows zero entries
6. ✓ LIVE indicator turns green on first SSE event; no JS console errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test infrastructure: worktree requires env vars + main repo venv**
- **Found during:** Task 1 verification
- **Issue:** Running `uv run pytest` from worktree created a fresh venv missing env vars (`SECRET_KEY`, `API_TOKEN_SECRET`). The plan's `<verify>` command `cd /Users/royco/ollog && uv run pytest ...` resolves to the main repo's template directory, not the worktree's, causing `NOTIFY_SOUND` not to appear in test responses.
- **Fix:** Used `SECRET_KEY=... API_TOKEN_SECRET=... /Users/royco/ollog/.venv/bin/python -m pytest ...` from worktree directory so templates resolve to worktree's modified `log.html` while using the main repo's venv (which has all packages and env config).
- **Impact:** Tests pass correctly — no code change needed, only test invocation method.

## Known Stubs

None — `notify_sound` is a live boolean from the User document, not hardcoded.

## Threat Flags

None — no new attack surface. Dependency swap uses the same JWT HttpOnly cookie validation path already used by `profile_page()`, `submit_qso()`, and token management routes.

## Self-Check

- [x] `app/qso/ui_router.py` contains `user: User = Depends(get_current_user_cookie)` in `log_view()` signature
- [x] `app/qso/ui_router.py` contains `callsign = user.callsign`
- [x] `app/qso/ui_router.py` contains `"notify_sound": user.notify_sound`
- [x] `templates/log/log.html` contains `const NOTIFY_SOUND = "{{ 'true' if notify_sound else 'false' }}"`
- [x] `templates/log/log.html` contains `async function playTone(ctx)`
- [x] `templates/log/log.html` contains `osc.frequency.setValueAtTime(440, now)`
- [x] `tests/test_log_view_notify_sound.py` exists with both test functions
- [x] Commits a0f6e4e and ca3b38b exist in git log

## Self-Check: PASSED
