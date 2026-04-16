# Research Summary — v2.4 Live Log & Sound Alerts

**Synthesized from:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md
**Date:** 2026-04-16
**Confidence:** HIGH

---

## Executive Summary

v2.4 fixes one confirmed bug and adds two new client-side capabilities. **Zero new Python packages. Zero new JavaScript dependencies.** The SSE live-refresh bug is not in the UDP insert path — UDP inserts correctly reach MongoDB and trigger the change stream — but in the **watcher task lifecycle** in `app/feed/manager.py`. Either an unhandled Jinja2 render exception kills the `watch_qsos` task permanently with no restart, or the task object loses its strong reference and is silently GC'd by Python 3.12+. Fixing the watcher defensively resolves the bug for UDP and all insert paths simultaneously.

The badge (page 2+) and Web Audio tone are pure browser-side additions requiring no new files or routes.

---

## Stack — No Changes

- **Web Audio API**: `AudioContext` + `OscillatorNode` + `GainNode`, 880 Hz / 150 ms sine — browser built-in, Baseline Widely Available since April 2021 (Chrome 35+, Firefox 25+, Safari 14.1+, Edge 79+)
- **`webkitAudioContext` fallback** covers Safari pre-14.1 at zero cost
- **No new Python packages** — bug fix is in existing `app/feed/manager.py`
- Howler.js, tone.js, browser-beep explicitly rejected as overkill for a single tone

---

## Features — All 4 Table Stakes

1. **Fix: UDP QSOs trigger SSE refresh** — multi-operator UDP is broken without it; root cause is watcher task dying, not the insert path
2. **Dismissable badge on page 2+** — operators reviewing history get notified without forced scroll interruption; click = dismiss counter
3. **`notify_sound: bool = False` in User doc** — per-operator, server-side, opt-in, no migration required
4. **Web Audio tone on SSE `new_qso` event** — synthesized 880 Hz / 150 ms sine, zero audio files, correct autoplay policy compliance

Anti-features out of scope: auto-jump to page 1 on new QSO, toast overlay, volume slider, localStorage preference (shared station), CDN audio files.

---

## Architecture — No New Files, No New Routes

**Modified files only:**
- `app/feed/manager.py` — defensive watcher fix (strong reference + exception isolation)
- `app/auth/models.py` — add `notify_sound: bool = False` field
- `app/auth/schemas.py` — add to `ProfileUpdateRequest` / `ProfileResponse`
- `app/qso/ui_router.py` — swap dependency to get `notify_sound` into log template context; add `notify_sound` Form param to `profile_update()`
- `templates/log/log.html` — badge HTML (sibling of `#log-table`) + JS counter + Web Audio init
- `templates/log/profile.html` — sound toggle checkbox with hidden-input guard

**Critical placement rule:** Badge HTML must be a **sibling of `#log-table`**, not inside it — every pagination/filter navigation replaces `#log-table` innerHTML. The JS counter lives in the outer `log.html` scope and is re-applied via `htmx:afterSettle`.

`NOTIFY_SOUND` is a server-rendered JS constant in the outer page; survives all HTMX swaps; updated only on full page reload (acceptable — no mid-session change needed).

---

## Top 5 Pitfalls

1. **`watch_qsos` task has no strong reference** — silent GC kill on Python 3.12+ → store in `app.state.watcher_task` (mirrors `_background_tasks` pattern from UDP server)
2. **HTML checkbox sends nothing when unchecked** → `<input type="hidden" name="notify_sound" value="false">` must precede the checkbox; always include field in profile update dict
3. **`AudioContext` created at page load is permanently suspended** → lazy init on first `click`/`touchstart`; check `ctx.state === 'running'` before `osc.start()`
4. **Badge element inside `#log-table` destroyed on every swap** → badge is sibling of `#log-table` in `log.html`, not in `log_table.html`
5. **`outerHTML` swap on SSE host element closes SSE connection** → always use `swap: 'innerHTML'` on the SSE host element

---

## Build Order

1. **Fix SSE watcher** — defensive try/except + strong reference in `app/feed/manager.py`. Hard prerequisite for everything else.
2. **Profile model + schema** — `notify_sound` field on `User`, `ProfileUpdateRequest`, `ProfileResponse`
3. **Wire into log view** — dependency swap in `log_view()`; emit `NOTIFY_SOUND` JS constant; `notify_sound` Form param in `profile_update()`
4. **Badge** — HTML sibling + JS counter + `htmx:afterSettle` re-sync (independent of audio)
5. **Web Audio tone** — `initAudio()`/`playTone()` in `log.html`; lazy init on gesture; gate behind `NOTIFY_SOUND`
6. **Profile toggle UI** — checkbox + hidden-input guard in `profile.html`; end-to-end toggle round-trip

---

## Two Implementation Validations Needed

- **Phase 1:** Confirm pymongo 4.16+ `AsyncCollection.watch()` call signature — current code uses double-await (`async with await collection.watch(...)`); may be correct or may need outer `await` removed
- **Phase 6:** Confirm FastAPI `Form()` behavior when same field name appears twice (hidden + checkbox) — determines whether hidden input precedes or follows the checkbox

---

*Research complete — ready for requirements definition*
