---
gsd_state_version: 1.0
milestone: v1.7
milestone_name: API Token Auth
status: executing
stopped_at: Phase 46 UI-SPEC approved
last_updated: "2026-04-17T18:18:50.380Z"
last_activity: 2026-04-17
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 4
  completed_plans: 2
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** Phase 46 — web-audio-sound-alerts

## Current Position

Phase: 46
Plan: Not started
Next: Phase 45 (notify-sound-model)
Milestone: v2.4 Live Log & Sound Alerts
Status: Executing Phase 46
Last activity: 2026-04-17

```
v2.4 Progress: [█████░░░░░░░░░░░░░░░] 25% (1/4 phases)
```

## Performance Metrics

**Velocity (historical):**

- Total plans completed: 58 plans across v1.0–v2.3
- Average duration: ~5–20 min/plan

**By Milestone:**

| Milestone | Phases | Plans |
|-----------|--------|-------|
| v1.0 | 1–6 | 19 |
| v1.1 | 7–10 | 7 |
| v1.2 | 11–12 | 2 |
| v1.3 | 13–15 | 8 |
| v1.4 | 16–18 | 4 |
| v1.5 | 19–22 | 4 |
| v1.6 | 23–24 | 2 |
| v1.7 | 25–28 | 4 |
| v1.8 | 29–31 | 3 |
| v1.9 | 32–36 | 5 |
| v2.0 | 37–38 | 2 |
| v2.1 | 39–40 | 2 |
| v2.2 | 41 | 2 |
| v2.3 | 42–43 | 2 |
| v2.4 | 44–47 | TBD |

## Accumulated Context

### Roadmap Evolution

- Phase 46 added: Web Audio sound alerts

### Critical Build Rules (carried forward)

- **FOUC prevention:** The inline IIFE in `base.html` `<head>` is load-bearing. Never move it, add `defer`/`async`, or extract it to an external file.
- **Tailwind purge:** New `dark:` classes must appear as complete literal strings in scanned template files. Always run `npm run build` + grep verification for new classes before committing templates or `input.css`.
- **Safari backdrop-filter:** Declare `-webkit-backdrop-filter` explicitly in `@layer components` for glass card classes. Use fixed pixel values, not CSS variable references.
- **PostCSS autoprefixer:** Always configure `postcss.config.js` with `autoprefixer({ remove: false })` when writing explicit webkit prefixes in source CSS.
- **FastAPI sub-app StaticFiles:** Every FastAPI sub-app that serves HTML must have its own `StaticFiles` mount for `/static`. The main app mount does not propagate.
- **apscheduler<4 upper bound is load-bearing:** Do not touch `pyproject.toml` APScheduler constraints.

### v2.4 Architecture Decisions (pre-decided from research)

- **SSE watcher strong reference:** Store watcher task in `app.state.watcher_task` to prevent Python 3.12+ GC. Without this, the task can be collected silently and events stop flowing.
- **SSE exception recovery:** Wrap the watcher's inner loop in a `try/except Exception` with a short sleep before retry — not a bare `except BaseException` which would suppress `CancelledError`.
- **LIVE indicator accuracy:** Do not set the indicator green on SSE connection open (`EventSource` readyState == OPEN). Set it green only on first `message` event received; set it grey on `error` event.
- **notify_sound field default:** `notify_sound: bool = False` on the `User` Beanie model. Existing users without the field read as `False` via Pydantic default — no migration needed.
- **Hidden input before checkbox (load-bearing):** `<input type="hidden" name="notify_sound" value="false">` must precede `<input type="checkbox" name="notify_sound" value="true">`. Unchecked checkbox sends nothing; hidden input provides the `false` fallback.
- **Web Audio lazy init:** Create `AudioContext` on first user gesture (click/keydown), not at page load. Store as module-level variable. Check `context.state === 'suspended'` and call `context.resume()` before playing.
- **webkitAudioContext fallback:** `const AudioContext = window.AudioContext || window.webkitAudioContext;` — required for Safari.
- **NOTIFY_SOUND JS constant:** Injected by `log_view()` as a Jinja2 template variable. Value is the string `"true"` or `"false"` derived from `current_user.notify_sound`. Compare as `NOTIFY_SOUND === "true"` in JS.
- **Badge placement:** Badge `<div id="new-qso-badge">` must be a sibling of `#log-table` in the DOM — not a child. HTMX SSE swaps target `#log-table` and destroy its innerHTML, which would delete the badge if nested inside.
- **Badge htmx:afterSettle re-sync:** On `htmx:afterSettle`, if the swap target is `#log-table` and the user is on page 1 with no filters, reset the badge counter to zero and hide the badge.
- **No new Python packages:** `requirements.txt` and `pyproject.toml` do not change for v2.4.
- **No new JS dependencies:** Web Audio API is native browser. No npm installs.

### Files modified in v2.4 (complete list)

- `app/feed/manager.py` — Phase 44 (strong reference + exception loop)
- `app/auth/models.py` — Phase 45 (notify_sound field)
- `app/auth/schemas.py` — Phase 45 (ProfileUpdateRequest + ProfileResponse)
- `app/qso/ui_router.py` — Phase 46 (log_view dependency swap + NOTIFY_SOUND + profile_update Form param)
- `templates/log/log.html` — Phase 46/47 (badge HTML + audio JS)
- `templates/log/profile.html` — Phase 45/46 (sound toggle UI)

### Known Tech Debt

- `QSO.find_active()` in models.py — dead production code
- `from_mongo_dt()` in utils.py — tested, not called in production
- Docker end-to-end verification pending (requires live Docker environment)

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-17T13:25:55.517Z
Stopped at: Phase 46 UI-SPEC approved
Resume file: .planning/phases/46-web-audio-sound-alerts/46-UI-SPEC.md
Next: `/gsd-plan-phase 45` to plan Phase 45 (notify-sound-model)
