# Feature Landscape

**Domain:** Real-time web logging (ham radio QSO log, v2.4 Live Log & Sound Alerts)
**Milestone:** v2.4
**Researched:** 2026-04-16
**Confidence:** HIGH — all findings grounded in direct code inspection of the existing codebase

---

## Feature 1: UDP QSOs Triggering SSE Refresh (Bug Fix)

### What "Done" Looks Like

A QSO inserted via UDP datagram causes the same SSE `new_qso` event as a QSO inserted via REST API or web form. No special handling needed in the UDP path — the fix lives in the SSE/change-stream layer.

### Current Behavior (Diagnosis from Code)

The change-stream watcher (`app/feed/manager.py: watch_qsos`) uses this call pattern:

```python
async with await collection.watch(pipeline, full_document="updateLookup") as stream:
```

The `await collection.watch(...)` double-await mirrors the `(await collection.aggregate(pipeline)).to_list()` pattern discovered in v2.3 (see Key Decisions). Whether this is correct for `pymongo 4.16+` AsyncCollection's `.watch()` method is the primary investigation target. If `.watch()` is a coroutine, this is correct; if it returns a cursor directly, the extra `await` creates a coroutine object that the `async with` never actually opens as a real stream — silently producing an empty iterator.

Additionally: `watch_qsos` is started in lifespan using `get_client()`, which returns the shared `AsyncMongoClient`. Beanie also uses this same client for all QSO inserts. There is no connection isolation — UDP-inserted QSOs go through the same `_client` instance and thus the same MongoDB session, so the change stream should see them. If the stream is working for REST inserts but not UDP inserts, the bug is in the `watch_qsos` loop or a timing/reconnect issue, not in the UDP path itself.

The watcher pipeline is:
```python
[{"$match": {"operationType": "insert"}}]
```
This is correct — inserts from all paths (REST, UI form, UDP) trigger `operationType: "insert"` on the change stream.

### Table Stakes

- Every insert path (REST, UI form, UDP) must trigger the SSE event. This is the core contract.
- The fix must not break the existing REST/UI form path.
- No new environment variable or configuration.

### Complexity

**Low** — isolated to `watch_qsos` call pattern. The fix is verifying the correct pymongo async API for `.watch()` and correcting if needed. One-line change or two at most.

### Dependencies on Existing Architecture

- `app/feed/manager.py` — `watch_qsos()` is the only change
- `app/database.py` — no change; `get_client()` already returns the correct client
- `app/udp/server.py` — no change; `await qso.insert()` is already correct
- Must verify: does `AsyncCollection.watch()` in pymongo 4.16+ return a coroutine (requiring `await`) or an async context manager directly?

---

## Feature 2: "N New QSOs" Dismissable Badge on Page 2+

### What "Done" Looks Like

When the operator is on page 2 or higher (or has active filters), and a new QSO arrives via SSE:

1. A badge appears in or near the log table header: "3 new QSOs" (incrementing counter)
2. The badge is visually distinct but non-intrusive — it does not interrupt the current view, does not scroll, does not auto-jump to page 1
3. Clicking the badge dismisses it (counter resets to zero, badge hides)
4. No click action required beyond dismissal — it is informational only (no auto-navigation)
5. Badge resets to zero if the operator manually navigates to page 1 (because the table will auto-refresh)

### Table Stakes

- Counter must only appear when `#auto-refresh-ok` is absent (i.e., page 2+, active filters, or non-default sort) — because on page 1 with defaults, the table auto-refreshes and the badge is redundant
- Counter must increment for each SSE `new_qso` event received while the badge is visible
- Single click dismisses the badge
- Must survive HTMX partial swaps (because `#log-table` innerHTML is replaced by pagination navigation) — the badge must be outside the HTMX swap target or re-registered after swap
- Must not appear simultaneously with the auto-refresh (mutually exclusive with `#auto-refresh-ok`)

### Differentiators (Nice-to-Have, Not Required)

- Badge color change at thresholds (e.g., turns amber at 10+ new QSOs) — skip
- Click-to-navigate to page 1 — not required, adds complexity and can interrupt browsing

### Anti-Features

- Auto-jump to page 1 on new QSO — explicitly out of scope per milestone spec, would interrupt browsing
- Toast/popup notification — too intrusive for a logging environment where QSOs arrive continuously during FT8 sessions; badge is the correct pattern

### UX Behavior

The badge lives in the log table card header area, rendered in a fixed position relative to the table (not absolutely positioned on the viewport). This keeps it contextually anchored without interfering with scroll position.

```
[ 3 new QSOs  x ]   <- appears in table header row, right-aligned; x = dismiss
```

State is entirely client-side: a JS counter variable incremented in the `htmx:sseMessage` handler when `#auto-refresh-ok` is absent.

### Complexity

**Low-Medium** — pure JavaScript + Jinja2/HTML changes.

Key implementation decisions:
- Badge element must live in `log.html` (outside `#log-table`), not in `log_table.html` (inside the swap target)
- The `htmx:sseMessage` handler in `log.html` already distinguishes page-1/auto-refresh vs page-2+ via `#auto-refresh-ok`; the badge logic hangs off the `else` branch of that same check
- Badge must be hidden by default (`hidden` class), shown when counter > 0
- On dismiss: counter = 0, badge hidden
- On HTMX swap of `#log-table` (pagination, filter, sort): if page 1 is now active, `#auto-refresh-ok` will appear in the new content; the badge should be dismissed in the `htmx:afterSettle` handler if `#auto-refresh-ok` is now present

### Dependencies on Existing Architecture

- `templates/log/log.html` — badge HTML and JS changes (same file as SSE handler)
- `templates/log/log_table.html` — no change
- `app/feed/router.py` — no change; `new_qso` event already fired
- No backend changes required

---

## Feature 3: Web Audio API Tone on New QSO Arrival

### What "Done" Looks Like

When a new QSO SSE event arrives in the browser:

1. A brief, clean audio tone plays (duration: ~200ms; frequency: ~880 Hz; envelope: short attack, short decay — sounds like a soft "beep")
2. Sound only plays if the operator has opted in (per-operator preference)
3. Sound respects browser autoplay policy: audio context is created/resumed on the first user gesture, not on page load
4. Sound works without any external files — synthesized via Web Audio API oscillator

### Table Stakes

- Zero external audio file dependencies — must use `AudioContext` + `OscillatorNode`
- Must not play on page load (browser autoplay policy will block it and log a console error)
- Must not play on every SSE message from `new_qso` if sound is disabled
- Must play once per `new_qso` event (not once per table row, not batched)
- Must degrade gracefully if `AudioContext` is not supported (unlikely in 2026, but: `if (window.AudioContext)` guard)

### Web Audio API Behavior (How It Works)

```javascript
// Pattern for zero-file audio notification:
let audioCtx = null;

function ensureAudioContext() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    // Resume if suspended (browser may suspend on page load)
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}

function playTone(freq, duration) {
    ensureAudioContext();
    var osc = audioCtx.createOscillator();
    var gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.type = 'sine';
    osc.frequency.value = freq || 880;
    gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + (duration || 0.18));
    osc.start(audioCtx.currentTime);
    osc.stop(audioCtx.currentTime + (duration || 0.18));
}
```

The `AudioContext` must be created (or resumed) inside a user gesture handler. The approach: initialize `audioCtx` on the first `click` or `keydown` event on `document.body`, then it is available for programmatic calls from SSE events thereafter.

### Autoplay Policy Details

Modern browsers (Chrome, Firefox, Safari) block `AudioContext` creation before user interaction. The fix is straightforward:

```javascript
// Initialize audio context on first user gesture
document.body.addEventListener('click', function initAudio() {
    ensureAudioContext();
}, { once: true });
```

This fires once, primes the context, and `{ once: true }` self-removes. Subsequent programmatic calls to `playTone()` work because the context is now in `running` state.

Safari requires `webkitAudioContext` fallback (already in the pattern above).

### Differentiators (Nice-to-Have, Not Required)

- Volume control slider in profile — skip for v2.4
- Different tones for different modes (FT8 vs SSB) — skip
- Tone customization (frequency picker) — skip

### Anti-Features

- External audio file (`.wav`, `.mp3`) — adds file to serve, MIME type handling, caching; no benefit over synthesized tone
- `<audio>` element — worse fit for programmatic triggering; Web Audio API is the correct approach

### Complexity

**Low** — pure browser JavaScript, no backend changes. Approximately 30 lines of JavaScript added to `log.html`.

### Dependencies on Existing Architecture

- `templates/log/log.html` — JS added to existing `htmx:sseMessage` handler
- No Tailwind changes (no new UI elements beyond the profile toggle)
- No backend changes, no new routes
- Feature 4 (profile toggle) controls whether `playTone()` is called

---

## Feature 4: Profile Toggle — Sound On/Off Persisted Per Operator

### What "Done" Looks Like

1. Profile Settings page (`/log/profile`) has a new "Sound Notifications" toggle switch (checkbox)
2. Saving profile with the toggle on/off persists `sound_enabled: bool` to the operator's `User` document in MongoDB
3. When the log view page loads, the server renders the page with the operator's sound preference included as a JS variable in the template
4. The `playTone()` call in `htmx:sseMessage` checks this preference before playing

### Table Stakes

- Default: sound off (`sound_enabled = False`) — opt-in, not opt-out
- Toggle must be saved with the existing Profile form submit (not a separate endpoint)
- Server must pass the preference to `log.html` so the JS can read it on page load without a separate API call
- The preference is per-operator (stored in `User` document), not per-browser (not `localStorage`) — correct scope for a shared station deployment where operators rotate

### How Preference Reaches the Browser

The log view GET route in `app/qso/ui_router.py` already has the `User` object (via `get_current_user_cookie`). Pass `sound_enabled` to the template context as a boolean. Render it into an inline JS variable:

```html
<!-- In log.html, inside the <script> block that already handles SSE -->
var SOUND_ENABLED = {{ 'true' if sound_enabled else 'false' }};
```

The `htmx:sseMessage` handler then adds: `if (SOUND_ENABLED) { playTone(); }`

### Model Changes Required

`app/auth/models.py: User` — add one field:
```python
sound_enabled: bool = False  # sound notifications on new QSO arrival
```
Default `False` means existing operators are unaffected on upgrade.

`app/profile/schemas.py: ProfileUpdateRequest` — add:
```python
sound_enabled: Optional[bool] = None
```

`app/profile/service.py: update_profile` — no code change needed; `"sound_enabled"` will be in `updates` dict and passed to `$set`.

### UI Changes Required

`templates/log/profile.html` — add a "Notifications" section (new card or appended to existing Operator Details card) with a toggle checkbox.

### Checkbox Submission Behavior (Critical Detail)

HTML checkbox submission: unchecked boxes are not submitted in the form POST body. The profile POST handler in `app/qso/ui_router.py` must handle this:

- If `sound_enabled` key is absent from the POST body, treat as `False` (sound disabled)
- This is different from other optional profile fields (`my_rig`, `name`, etc.) that use `None` to mean "field not changed"
- The UI router POST for `/log/profile` must explicitly set `sound_enabled = "sound_enabled" in form_data`

This is the one non-obvious implementation detail for this feature.

### Complexity

**Low-Medium** — primarily backend model and form changes. The checkbox normalization logic is the only subtle point.

### Dependencies on Existing Architecture

- `app/auth/models.py` — add `sound_enabled: bool = False` to `User`
- `app/profile/schemas.py` — add `sound_enabled: Optional[bool] = None` to `ProfileUpdateRequest`
- `app/qso/ui_router.py` — profile POST handler: normalize checkbox absence to `False`; log view GET handler: add `sound_enabled` to template context
- `templates/log/profile.html` — add toggle UI
- `templates/log/log.html` — read `sound_enabled` from template context; pass to `playTone()` guard

---

## Feature Summary Table

| Feature | Category | Backend | Frontend | Complexity | Risk |
|---------|----------|---------|----------|------------|------|
| UDP -> SSE fix | Bug fix | `manager.py` 1-2 lines | None | Low | Low |
| "N new QSOs" badge | New feature | None | `log.html` JS + HTML | Low-Med | Low |
| Web Audio tone | New feature | None | `log.html` JS | Low | Low |
| Sound profile toggle | New feature | `User`, schemas, UI router | `profile.html`, `log.html` | Low-Med | Low |

---

## Table Stakes vs Differentiators

### Table Stakes (must ship in v2.4)

- UDP-sourced QSOs trigger the live refresh — multi-op UDP (v2.2) is effectively broken without this
- Badge on page 2+ — operators actively browsing history must know new QSOs arrived without a forced page jump
- Sound toggle persisted to operator profile — per-operator, per-server, survives browser restarts
- Default: sound off — shared station deployments must not start beeping unexpectedly on first deploy

### Differentiators

- Synthesized tone (no file) — cleaner than serving an audio file; immediate, no HTTP round-trip before first QSO
- Badge auto-clears on navigate-to-page-1 — prevents stale counter confusing operators after manual navigation
- User-gesture audio init pattern — correct browser API usage, no console errors, follows browser autoplay spec

### Anti-Features (Explicitly Out of Scope for v2.4)

| Anti-Feature | Why | What Instead |
|--------------|-----|-------------|
| Auto-jump to page 1 on new QSO | Interrupts browsing, especially during FT8 QSO review | Dismissable badge only |
| Toast/popup overlay | Intrusive during continuous FT8 sessions | Badge in table header |
| Volume slider | Adds form complexity; binary toggle is sufficient | `sound_enabled` bool |
| Per-browser sound preference (localStorage) | Wrong scope for shared station | MongoDB User field |
| Audio file (.wav/.mp3) | Dependency, MIME type config, serving complexity | Web Audio API oscillator |

---

## Feature Dependencies

```
Feature 1 (UDP fix) -> independent; badge and audio work regardless of source
Feature 4 (profile toggle) -> independent; stores bool in User document
Feature 3 (audio tone) -> reads sound_enabled from Feature 4's model + template context
Feature 2 (badge) -> relies on SSE events firing; Feature 1 fix ensures UDP triggers them
```

Suggested build order within milestone:
1. Feature 1 (UDP fix) — unblocks Feature 2 for UDP QSOs; confirms SSE chain is intact
2. Feature 4 (profile toggle, model + form) — add field, update form, pass to template context
3. Feature 3 (Web Audio tone) — reads preference from template context
4. Feature 2 (badge) — purely additive JS/HTML change, no backend

---

## Sources

- Direct inspection: `app/feed/manager.py`, `app/feed/router.py`, `app/udp/server.py`, `app/main.py`, `app/database.py`, `app/auth/models.py`, `app/profile/schemas.py`, `app/profile/service.py`
- Direct inspection: `templates/log/log.html`, `templates/log/log_table.html`, `templates/log/profile.html`, `templates/log/form.html`, `templates/log/feed_row.html`
- Key Decisions table in `.planning/PROJECT.md` — v1.6 SSE design decisions, v2.2 UDP routing decisions, v2.3 double-await pattern discovery
- Web Audio API: HIGH confidence from knowledge base (AudioContext, OscillatorNode, GainNode, autoplay policy behavior in Chrome/Firefox/Safari 2026)
- HTML checkbox submission behavior: HIGH confidence (well-established browser standard)
