# Phase 46: Sound Playback Wiring — Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire Web Audio API sound playback into `log.html`. When a `new_qso` SSE event arrives, play a brief synthesized tone in the browser — but only if `NOTIFY_SOUND === "true"` (from the operator's stored preference) and the operator has already interacted with the page at least once (browser autoplay policy).

Phase 45 delivered the `notify_sound` model field, the profile toggle UI, and the backend save/load. Phase 46 delivers the JS playback layer only — no new Python packages, no new HTML structure beyond the script additions.

</domain>

<decisions>
## Implementation Decisions

### Tone Character
- **D-01:** Tone is a **440 Hz sine wave, ~120 ms duration, smooth attack/decay envelope** — soft low tone that is unobtrusive during long FT8 sessions. Implemented via `OscillatorNode` (type `"sine"`, frequency 440) connected through a `GainNode`. Use `linearRampToValueAtTime` to ramp gain up over ~10 ms and down over ~30 ms before stopping the oscillator.

### Autoplay Policy Gate
- **D-02:** Track user interaction with a module-scoped boolean (`userInteracted`). Set `true` on first `click` or `keydown` event on `document`. If a `new_qso` event arrives before any interaction, **fail silently** — do not play the tone, do not show any visual indicator. The profile page hint ("Requires at least one page interaction") is the only user education needed.

### JS Structure
- **D-03:** All audio code lives inside the existing IIFE `<script>` in `log.html`, alongside the existing SSE listeners. The `AudioContext` instance and `userInteracted` flag are scoped within the IIFE (module-level within it). No separate `<script>` block, no external JS file.

### Backend Dependency Change
- **D-04:** `log_view()` in `ui_router.py` switches from `callsign: str = Depends(get_current_operator_callsign_cookie)` to `user: User = Depends(get_current_user_cookie)`. Extract `callsign = user.callsign` inside the handler. Inject `notify_sound=user.notify_sound` into the Jinja2 context as a boolean; the template renders it as `const NOTIFY_SOUND = "{{ 'true' if notify_sound else 'false' }}";`.

### HTMX Partial Path Unchanged
- **D-05:** When `request.headers.get("HX-Request")` is truthy, `log_view()` still returns `log_table.html`. The `NOTIFY_SOUND` constant is only needed in the full `log.html` page — the partial swap path does not need the sound preference injected.

### Claude's Discretion
- Exact oscillator start/stop timing (play immediately on SSE fire, no delay)
- `context.resume()` is called and awaited before oscillator start (handles suspended state)
- `webkitAudioContext` fallback: `const AudioContext = window.AudioContext || window.webkitAudioContext;`
- AudioContext is created lazily on first interaction, stored as an IIFE-scoped variable (initially `null`)
- If `AudioContext` is not available (very old browser), fail silently — no try/catch required at init time

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing SSE Listener (integration point)
- `templates/log/log.html` — Contains the IIFE `<script>` with `htmx:sseMessage`, `htmx:sseError`, `htmx:sseClose` listeners. Audio code integrates here.

### Backend Route to Modify
- `app/qso/ui_router.py` — `log_view()` handler (line ~248). Switch dependency and inject `notify_sound` into template context.

### Auth Dependencies
- `app/auth/dependencies.py` — `get_current_user_cookie` returns full `User` document; `get_current_operator_callsign_cookie` returns only callsign string.

### User Model
- `app/auth/models.py` — `User.notify_sound: bool = False`

### Profile UI (reference for toggle already built)
- `templates/log/profile.html` — Sound toggle already wired to backend; no changes needed in Phase 46.

### Project Requirements
- `.planning/REQUIREMENTS.md` — SND-01, SND-02 are the acceptance criteria for this phase.

### Architecture Decisions (PRE-DECIDED — must follow)
- `.planning/STATE.md` §v2.4 Architecture Decisions — Web Audio lazy init pattern, NOTIFY_SOUND constant format, no new packages.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `document.body.addEventListener('htmx:sseMessage', ...)` — already in `log.html` IIFE; audio playback hooks into this same listener after the `if (!e.detail || e.detail.type !== 'new_qso') return;` guard.
- `get_current_user_cookie` — already used by `profile_page()` and `profile_update()` in `ui_router.py`; same pattern for `log_view()`.

### Established Patterns
- IIFE `<script>` in templates for page-level JS state (no global leakage)
- Jinja2 template variables injected as JS constants in `<script>` blocks (pattern from base.html theme IIFE)
- `Depends(get_current_user_cookie)` returns the full `User` Beanie document

### Integration Points
- `log.html` IIFE: add `let audioCtx = null; let userInteracted = false;` alongside existing `let eventsFlowing = false;`
- `htmx:sseMessage` handler: after line `if (!e.detail || e.detail.type !== 'new_qso') return;`, add the tone playback call
- `log_view()`: add `user: User = Depends(get_current_user_cookie)` param, inject `"notify_sound": user.notify_sound` into both the full-page and partial context dicts

</code_context>

<specifics>
## Specific Ideas

No specific external references — user confirmed "you decide" on tone parameters. Chosen: 440 Hz sine wave, 120 ms, smooth attack/decay envelope (OscillatorNode + GainNode with ramp), suitable for long overnight FT8 sessions.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 46-web-audio-sound-alerts*
*Context gathered: 2026-04-17*
