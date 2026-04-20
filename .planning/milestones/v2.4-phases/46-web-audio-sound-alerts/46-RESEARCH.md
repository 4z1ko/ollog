# Phase 46: Sound Playback Wiring — Research

**Researched:** 2026-04-17
**Domain:** Web Audio API browser synthesis + FastAPI route dependency swap
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 Tone character:** 440 Hz sine wave, ~120 ms duration, smooth attack/decay envelope. OscillatorNode (type `"sine"`, frequency 440) through GainNode. `linearRampToValueAtTime` ramps gain up over ~10 ms and down over ~30 ms before oscillator stop.
- **D-02 Autoplay gate:** Module-scoped `userInteracted` boolean. Set `true` on first `click` or `keydown` event on `document`. New QSO arriving before any interaction: fail silently, no visual indicator.
- **D-03 JS structure:** All audio code inside the existing IIFE `<script>` in `log.html`, alongside the existing SSE listeners. The `AudioContext` instance and `userInteracted` flag are scoped within the IIFE. No separate `<script>` block, no external JS file.
- **D-04 Backend dependency change:** `log_view()` in `ui_router.py` switches from `callsign: str = Depends(get_current_operator_callsign_cookie)` to `user: User = Depends(get_current_user_cookie)`. Extract `callsign = user.callsign` inside the handler. Inject `notify_sound=user.notify_sound` into Jinja2 context as a boolean; template renders it as `const NOTIFY_SOUND = "{{ 'true' if notify_sound else 'false' }}";`.
- **D-05 HTMX partial path unchanged:** When `request.headers.get("HX-Request")` is truthy, `log_view()` still returns `log_table.html`. The `NOTIFY_SOUND` constant is only needed in the full `log.html` page.

### Claude's Discretion

- Exact oscillator start/stop timing (play immediately on SSE fire, no delay)
- `context.resume()` is called and awaited before oscillator start (handles suspended state)
- `webkitAudioContext` fallback: `const AudioContext = window.AudioContext || window.webkitAudioContext;`
- AudioContext is created lazily on first interaction, stored as an IIFE-scoped variable (initially `null`)
- If `AudioContext` is not available (very old browser), fail silently — no try/catch required at init time

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SND-01 | A brief audio tone plays in the browser when a new QSO arrives via SSE (Web Audio API synthesized tone — no external audio file) | Web Audio API OscillatorNode synthesis verified; integration point is the `htmx:sseMessage` listener already in `log.html` |
| SND-02 | The tone only plays after the operator has interacted with the page at least once (browser autoplay policy compliant) | `AudioContext.state === 'suspended'` pattern + `resume()` verified via MDN; lazy `AudioContext` creation on first user gesture is the canonical approach |
</phase_requirements>

---

## Summary

Phase 46 is a minimal JS + Python wiring task. The heavy lifting (data model, profile toggle, profile save/load) was completed in Phase 45. This phase adds:
1. Audio playback logic inside the existing IIFE `<script>` in `templates/log/log.html`
2. A dependency swap in `app/qso/ui_router.py:log_view()` to supply `notify_sound` to the template

The Web Audio API is a native browser API — no npm installs, no CDN references, no new Python packages. The oscillator synthesis pattern (OscillatorNode + GainNode + linearRampToValueAtTime) is well-established and supported in all modern browsers since 2013. Safari requires the `webkitAudioContext` fallback for older versions but the standardized `AudioContext` works in Safari 14.1+ (released 2021).

The two files being touched are small and well-understood: `log.html` is 160 lines and the IIFE contains the SSE listener; `ui_router.py` already imports both `get_current_user_cookie` and `get_current_operator_callsign_cookie` — only the dependency injected into `log_view()` changes.

**Primary recommendation:** Follow D-01 through D-05 exactly as specified in CONTEXT.md. Verified patterns from MDN confirm all technical choices are sound.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sound synthesis (tone generation) | Browser / Client | — | Web Audio API runs entirely in the browser; no server involvement after page load |
| Autoplay policy gate (userInteracted flag) | Browser / Client | — | Browser-side state that reflects user gesture history; cannot be determined server-side |
| SSE event trigger (new_qso detection) | Browser / Client | — | `htmx:sseMessage` listener is client-side; HTMX fires the event after SSE message receipt |
| Sound preference read (NOTIFY_SOUND constant) | Frontend Server (SSR) | Browser / Client | Server injects the boolean as a JS constant at page render time; client reads the constant |
| log_view() dependency swap | API / Backend | — | FastAPI route dependency change; swaps `get_current_operator_callsign_cookie` for `get_current_user_cookie` |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Web Audio API | Native (W3C Living Standard) | Oscillator synthesis, gain envelope | Zero-dependency; built into all browsers; synthesized tone with no file fetch |
| FastAPI | >=0.135.0 (project constraint) | Route handler, Depends injection | Already in stack |
| Beanie / User model | 2.1.0+ (project constraint) | `user.notify_sound` field access | Already in stack; Phase 45 added the field |

### No New Dependencies

This phase introduces zero new packages. All capabilities are:
- `window.AudioContext` / `window.webkitAudioContext` — native browser
- `get_current_user_cookie` — already imported in `ui_router.py` line 26
- `User` model — already imported in `ui_router.py` line 27

**Installation:** None required.

**Version verification:** N/A — no new packages added. [VERIFIED: codebase read of `pyproject.toml` and `ui_router.py`]

---

## Architecture Patterns

### System Architecture Diagram

```
UDP Datagram
    │
    ▼
app/udp/ ──► MongoDB change stream
                    │
                    ▼
            app/feed/manager.py (watch_qsos)
                    │
                    ▼
            SSE event "new_qso" ──► browser EventSource (HTMX ext:sse)
                    │
                    ▼
            htmx:sseMessage fires on document.body
                    │
                    ├── [guard: e.target.id !== 'log-table'] → return
                    ├── [guard: e.detail.type !== 'new_qso'] → return
                    │
                    ├── [existing] LIVE indicator update
                    ├── [existing] HTMX table reload (if on page 1, no filters)
                    │
                    └── [NEW Phase 46] playTone()
                                │
                                ├── [guard: NOTIFY_SOUND !== "true"] → return
                                ├── [guard: !userInteracted] → return (silent)
                                └── AudioContext.resume() → OscillatorNode start
                                        │
                                        ▼
                                    440 Hz sine wave, 120 ms
                                    attack 10 ms / decay 30 ms
                                    via GainNode linearRamp

Page load (full page only, not HX-Request):
    log_view() (ui_router.py)
        │
        ├── user: User = Depends(get_current_user_cookie)  [CHANGED D-04]
        ├── callsign = user.callsign
        ├── notify_sound = user.notify_sound
        │
        └── Jinja2 render log.html with {notify_sound: bool}
                │
                ▼
        <script>
          const NOTIFY_SOUND = "{{ 'true' if notify_sound else 'false' }}";
          // AudioContext lazy init on first click/keydown
          // userInteracted flag tracks page interaction
        </script>
```

### Recommended Project Structure

No new files. All changes are in:

```
app/qso/
└── ui_router.py       # log_view() dependency swap + notify_sound inject

templates/log/
└── log.html           # IIFE: AudioContext + userInteracted + playTone()
```

### Pattern 1: Lazy AudioContext with webkitAudioContext Fallback

**What:** Create AudioContext only on the first user gesture, not at page load. Store it in an IIFE-scoped variable. Use the `webkitAudioContext` fallback for Safari < 14.1.
**When to use:** Any page where audio must comply with browser autoplay policy.

```javascript
// Source: MDN Web Docs - Web Audio API Best Practices
// https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices
(function () {
  var AudioCtxClass = window.AudioContext || window.webkitAudioContext;
  var audioCtx = null;
  var userInteracted = false;

  function ensureAudioContext() {
    if (!AudioCtxClass) return null;  // very old browser — fail silently
    if (!audioCtx) {
      audioCtx = new AudioCtxClass();
    }
    return audioCtx;
  }

  document.addEventListener('click', function () { userInteracted = true; });
  document.addEventListener('keydown', function () { userInteracted = true; });
})();
```

### Pattern 2: Synthesized Beep Tone — OscillatorNode + GainNode Envelope

**What:** Create a short sine-wave beep with smooth attack/decay using scheduled AudioParam ramps.
**When to use:** Any in-browser notification tone that must not load external audio files.

```javascript
// Source: MDN Web Docs — OscillatorNode
// https://developer.mozilla.org/en-US/docs/Web/API/OscillatorNode
async function playTone(ctx) {
  // Handle suspended state (autoplay policy)
  if (ctx.state === 'suspended') {
    await ctx.resume();
  }

  var now = ctx.currentTime;
  var oscillator = ctx.createOscillator();
  var gainNode = ctx.createGain();

  oscillator.type = 'sine';
  oscillator.frequency.setValueAtTime(440, now);  // 440 Hz = concert A

  // Start at 0, ramp up over 10 ms (attack)
  gainNode.gain.setValueAtTime(0, now);
  gainNode.gain.linearRampToValueAtTime(0.3, now + 0.01);

  // Ramp down to 0 over 30 ms (decay), starting at 80 ms
  gainNode.gain.linearRampToValueAtTime(0.3, now + 0.08);
  gainNode.gain.linearRampToValueAtTime(0, now + 0.11);

  oscillator.connect(gainNode);
  gainNode.connect(ctx.destination);

  oscillator.start(now);
  oscillator.stop(now + 0.12);  // 120 ms total duration
}
```

**Key timing breakdown:**
- 0–10 ms: attack (gain 0 → 0.3)
- 10–80 ms: sustain (gain held at 0.3)
- 80–110 ms: decay (gain 0.3 → 0)
- 110–120 ms: buffer before oscillator.stop()

### Pattern 3: Integration into Existing htmx:sseMessage Handler

**What:** Hook playTone() into the existing `htmx:sseMessage` listener after the `new_qso` guard, guarded by `NOTIFY_SOUND` and `userInteracted`.
**When to use:** Adding behavior to an event already being handled.

```javascript
// In the existing IIFE — append after current new_qso guards
document.body.addEventListener('htmx:sseMessage', function (e) {
  if (!e.target || e.target.id !== 'log-table') return;
  if (!e.detail || e.detail.type !== 'new_qso') return;

  // [existing code: LIVE indicator update, HTMX reload]

  // [NEW] Sound notification
  if (NOTIFY_SOUND === 'true' && userInteracted && audioCtx) {
    playTone(audioCtx);  // fire-and-forget; no await needed
  }
});
```

**Note on `audioCtx` initialization timing:** `audioCtx` is created in the interaction handler (`click`/`keydown`). By the time `userInteracted` is `true`, `audioCtx` will also be non-null because both are set in the same listener. The `userInteracted && audioCtx` guard is belt-and-suspenders.

### Pattern 4: Backend Dependency Swap — log_view()

**What:** Replace the callsign-only dependency with the full User dependency to access `notify_sound`.
**When to use:** Route needs any User field beyond callsign.

```python
# Before (current code, line 259):
# callsign: str = Depends(get_current_operator_callsign_cookie),

# After (D-04):
async def log_view(
    request: Request,
    page: int = Query(1, ge=1),
    # ... other query params ...
    user: User = Depends(get_current_user_cookie),
):
    callsign = user.callsign
    # ... existing query logic unchanged ...
    ctx = {
        # ... existing keys ...
        "callsign": callsign,
        "notify_sound": user.notify_sound,  # NEW
    }
```

**HTMX partial path (D-05):** When `request.headers.get("HX-Request")` is truthy, `log_view()` returns `log_table.html`. The `NOTIFY_SOUND` constant is defined in the full `log.html` outer shell, not in `log_table.html` — so the partial swap path does not need `notify_sound` injected into its context. The existing `ctx` dict already passes to both paths; the partial just ignores the `notify_sound` key.

### Anti-Patterns to Avoid

- **Creating AudioContext at page load:** Browsers immediately suspend it under autoplay policy. Create lazily inside the first user gesture handler.
- **Playing tone without checking `context.state`:** If `AudioContext` is suspended, `oscillator.start()` will fire but produce no sound. Always `await ctx.resume()` before starting.
- **Setting `gain.value` directly instead of scheduling:** Direct assignment causes clicks/pops at audio transition boundaries. Use `setValueAtTime` + `linearRampToValueAtTime` for smooth envelopes.
- **Not calling `oscillator.stop()`:** One-shot oscillators that are never stopped hold references in the audio graph indefinitely. Always schedule a `stop()` call.
- **Using `async function` for the htmx:sseMessage listener callback itself:** HTMX event listeners must be synchronous callbacks. Call `playTone()` without `await` from the listener; let `playTone` be an async internal function.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tone synthesis | Custom audio file player, `<audio>` element | Web Audio API OscillatorNode | Zero external files; synthesized in browser; zero latency |
| Gain envelope / attack-decay | Manual setTimeout-based gain steps | `linearRampToValueAtTime` | AudioParam scheduling is sample-accurate; setTimeout is not |
| Autoplay policy compliance | User-interaction modal or permission prompt | Lazy AudioContext creation + `resume()` | Standard browser pattern; no UI overhead |
| Cross-browser Audio | Custom vendor-prefix sniffing | `window.AudioContext || window.webkitAudioContext` | Two-line fallback covers all live browser versions |

**Key insight:** Web Audio API's AudioParam scheduling system handles time-accurate audio with no JavaScript timer overhead. Hand-rolling with setTimeout introduces drift that causes audio artifacts.

---

## Common Pitfalls

### Pitfall 1: AudioContext Created Before User Gesture
**What goes wrong:** `const audioCtx = new AudioContext()` at script evaluation time → browser sets `audioCtx.state = 'suspended'` → `oscillator.start()` silently does nothing.
**Why it happens:** Browsers enforce autoplay policy at `AudioContext` creation time if no user gesture has occurred.
**How to avoid:** Create `audioCtx` inside the first `click` or `keydown` handler, not at IIFE initialization time. The `let audioCtx = null;` variable is initialized at IIFE scope; the object is assigned only inside the interaction handler.
**Warning signs:** Tone never plays even when `NOTIFY_SOUND === "true"` and `userInteracted === true`.

### Pitfall 2: `async` sseMessage Listener Blocks Synchronous HTMX Processing
**What goes wrong:** Making the `htmx:sseMessage` listener `async` causes the function to return a Promise, which HTMX ignores — but the internal `await` may cause `playTone` to run after HTMX has already swapped the table.
**Why it happens:** Async event handlers return Promises, not values — HTMX does not await them.
**How to avoid:** The outer listener must remain a synchronous `function`. Call `playTone(audioCtx)` without `await`; `playTone` may be async internally (for the `ctx.resume()` await), but invoking it fire-and-forget is correct because audio scheduling via AudioParam is done immediately inside `playTone` before any internal await.
**Warning signs:** Table swap stutters or tone plays out of sequence with the HTMX reload.

### Pitfall 3: NOTIFY_SOUND Evaluated Before `<script>` Block Renders
**What goes wrong:** Jinja2 escapes the boolean or the constant renders as `"True"/"False"` (Python booleans) instead of `"true"/"false"` (JS strings).
**Why it happens:** Python booleans serialize as `True`/`False`, not `true`/`false`. A naive `{{ notify_sound }}` would produce `True`, causing `NOTIFY_SOUND === "true"` to always be `false`.
**How to avoid:** Use the explicit Jinja2 conditional: `"{{ 'true' if notify_sound else 'false' }}"`. This is locked in D-04 and confirmed by the existing `base.html` theme constant pattern.
**Warning signs:** `NOTIFY_SOUND` evaluates as `"True"` in DevTools console — tone never plays despite preference being enabled.

### Pitfall 4: `callsign` Not Extracted from `user` After Dependency Swap
**What goes wrong:** After swapping to `user: User = Depends(get_current_user_cookie)`, references to `callsign` in the handler body still expect a `str` parameter that no longer exists.
**Why it happens:** The old `callsign: str` parameter is being removed; everywhere the handler uses `callsign`, it must now use `user.callsign`.
**How to avoid:** Add `callsign = user.callsign` as the first line of the handler body. All downstream calls to `get_qso_page(operator=callsign, ...)` and the context dict `"callsign": callsign` remain unchanged.
**Warning signs:** `NameError: name 'callsign' is not defined` at runtime; or worse, a missing variable that causes a 500 on the log view page.

### Pitfall 5: oscillator.stop() Called Before Decay Completes
**What goes wrong:** The gain decay ramp is still running when `oscillator.stop()` fires — this can cause a click artifact as the oscillator cuts off a non-zero gain value.
**Why it happens:** `stop()` immediately terminates oscillator output regardless of scheduled GainNode ramps.
**How to avoid:** Schedule `oscillator.stop()` at a time >= the end of the gain decay ramp. For the D-01 spec: decay ends at `now + 0.11`; schedule `oscillator.stop(now + 0.12)` to give a 10 ms buffer.
**Warning signs:** Audible "click" or "pop" at the end of the tone.

---

## Code Examples

### Complete Audio Integration Block (for log.html IIFE)

```javascript
// Source: MDN OscillatorNode + MDN Best Practices
// https://developer.mozilla.org/en-US/docs/Web/API/OscillatorNode
// https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices

(function () {
  // --- Existing IIFE state ---
  var indicator = document.getElementById('live-indicator');
  var eventsFlowing = false;

  // --- NEW Phase 46 state ---
  var AudioCtxClass = window.AudioContext || window.webkitAudioContext;
  var audioCtx = null;
  var userInteracted = false;

  // Create AudioContext lazily on first user gesture (autoplay policy)
  function onFirstInteraction() {
    if (userInteracted) return;
    userInteracted = true;
    if (AudioCtxClass) {
      audioCtx = new AudioCtxClass();
    }
  }

  document.addEventListener('click', onFirstInteraction);
  document.addEventListener('keydown', onFirstInteraction);

  async function playTone(ctx) {
    if (ctx.state === 'suspended') {
      await ctx.resume();
    }
    var now = ctx.currentTime;
    var osc = ctx.createOscillator();
    var gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(440, now);

    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(0.3, now + 0.01);   // 10 ms attack
    gain.gain.linearRampToValueAtTime(0.3, now + 0.08);   // hold to 80 ms
    gain.gain.linearRampToValueAtTime(0, now + 0.11);     // 30 ms decay

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.12);  // stop after 120 ms (10 ms after decay ends)
  }

  // --- Existing + NEW SSE listener ---
  document.body.addEventListener('htmx:sseMessage', function (e) {
    if (!e.target || e.target.id !== 'log-table') return;
    if (!e.detail || e.detail.type !== 'new_qso') return;

    // [existing] LIVE indicator
    if (!eventsFlowing) {
      eventsFlowing = true;
      indicator.classList.remove('hidden');
      indicator.classList.add('flex');
      indicator.querySelector('span:last-child').textContent = 'LIVE';
      indicator.classList.remove('bg-rose-100', 'text-rose-700');
      indicator.classList.add('bg-emerald-100', 'dark:bg-emerald-900/40',
                              'text-emerald-700', 'dark:text-emerald-400');
    }

    // [existing] HTMX reload
    if (!document.getElementById('auto-refresh-ok')) return;
    if (document.querySelector('#log-table input')) return;
    htmx.ajax('GET', '/log/view', { target: '#log-table', swap: 'innerHTML' });

    // [NEW] Sound notification — after all existing logic
    if (NOTIFY_SOUND === 'true' && userInteracted && audioCtx) {
      playTone(audioCtx);  // fire-and-forget
    }
  });

  // [existing] sseError and sseClose listeners unchanged
})();
```

**Note:** `NOTIFY_SOUND` is declared in a separate `<script>` block above the IIFE that injects it. Ensure the constant declaration appears before the IIFE, or declare it inside the IIFE by reading from a `<meta>` tag. The simplest approach (matching `base.html` pattern): inject `const NOTIFY_SOUND = "{{ 'true' if notify_sound else 'false' }}";` inside the same `<script>` block, before the IIFE opening.

### log_view() Route Handler — Diff

```python
# app/qso/ui_router.py — log_view() signature change (D-04)

# REMOVE:
#   callsign: str = Depends(get_current_operator_callsign_cookie),

# ADD:
#   user: User = Depends(get_current_user_cookie),

# ADD at top of handler body:
#   callsign = user.callsign

# ADD to ctx dict:
#   "notify_sound": user.notify_sound,

# No change to HX-Request partial path — ctx already contains notify_sound;
# log_table.html does not reference it, so the extra key is harmlessly ignored.
```

### Jinja2 Template Constant Injection

```html
<!-- In log.html <script> block, before IIFE -->
<script>
  const NOTIFY_SOUND = "{{ 'true' if notify_sound else 'false' }}";
  (function () {
    // ... IIFE code ...
  })();
</script>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `new Audio()` with audio files | Web Audio API OscillatorNode | ~2013 | Zero file fetches; synthesized in-browser |
| Global `AudioContext` at page load | Lazy creation on first gesture | Chrome 71 (2018) autoplay policy | No silent-suspension bug |
| `createOscillator()` factory method | `new OscillatorNode(ctx, options)` constructor | Web Audio API Level 1 | Both work; factory method used here for clarity |

**Deprecated/outdated:**
- `webkitAudioContext` without `AudioContext` check: `window.webkitAudioContext` alone fails in Chrome/Firefox. Always prefer `window.AudioContext || window.webkitAudioContext`.
- `ScriptProcessorNode`: deprecated; `AudioWorkletNode` is the modern replacement for custom DSP. Not relevant here — `OscillatorNode` is sufficient.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `linearRampToValueAtTime` produces smooth clicks in all modern browsers with no audible artifacts at the specified timing values | Code Examples (gain ramp timing) | Audible click/pop at attack or decay boundary — adjust timing values |
| A2 | The `htmx:sseMessage` listener return path after the HTMX reload (`htmx.ajax(...)`) is not reached when the guard conditions fail — so the tone code appended after `htmx.ajax()` never runs when auto-refresh is disabled | Architecture Patterns — Integration Pattern | Tone would only play when auto-refresh is active; silent when on page 2+ |

**Assumption A2 correction:** Looking at the actual `log.html` code: the `htmx.ajax()` call is guarded by two `if (!...) return;` checks at lines 137–139. If either guard returns early, the tone code after `htmx.ajax()` is also skipped. This means **the tone will not play** if `auto-refresh-ok` is absent (page 2+) or if the log table has an active input field. The planner must decide: should the tone guard checks mirror the HTMX reload checks, or should tone play independently of auto-refresh state?

**Recommendation:** Tone playback should be independent of the HTMX reload guards — a new QSO arriving on page 2 should still ring a tone even if the table doesn't auto-refresh. The tone code must be placed **before** the `auto-refresh-ok` guard returns, not after `htmx.ajax()`.

---

## Open Questions

1. **Tone placement relative to auto-refresh guards (Assumption A2)**
   - What we know: Current `log.html` has an early `return` if `auto-refresh-ok` is absent (page 2+) or active filter input is present. Tone code placed after `htmx.ajax()` would be unreachable in those cases.
   - What's unclear: Should SND-01 ("tone plays on new QSO via SSE") fire even when the operator is browsing page 2 with filters?
   - Recommendation: Yes — SND-01 does not scope tone playback to page 1 only. Place the tone block immediately after the `new_qso` type guard (before the `auto-refresh-ok` guard), so tone fires independently of the HTMX reload decision.

---

## Environment Availability

Step 2.6: This phase is purely browser-side JS + Python code changes. No external CLI tools, databases, or services are introduced beyond the existing FastAPI + MongoDB stack. Environment availability audit skipped — all dependencies are already in use by the running project.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (no `[tool.pytest.ini_options]` section — uses defaults) |
| Quick run command | `uv run pytest tests/test_profile_api.py -x` |
| Full suite command | `uv run pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SND-01 | A brief audio tone plays when new QSO arrives (no audio file fetch) | manual | Browser DevTools: Network tab shows no audio file requests on QSO arrival while sound enabled | — |
| SND-01 | `log_view()` injects `notify_sound` into template context | integration | `uv run pytest tests/test_log_view_notify_sound.py -x` | ❌ Wave 0 |
| SND-02 | Tone does not play until page interaction has occurred | manual | Open fresh tab, wait for UDP QSO — confirm no tone; then click anywhere, wait for next QSO — confirm tone | — |
| SND-01 + SND-02 | `NOTIFY_SOUND = "false"` when user.notify_sound is False | integration | `uv run pytest tests/test_log_view_notify_sound.py::test_notify_sound_false_injected -x` | ❌ Wave 0 |
| SND-01 + SND-02 | `NOTIFY_SOUND = "true"` when user.notify_sound is True | integration | `uv run pytest tests/test_log_view_notify_sound.py::test_notify_sound_true_injected -x` | ❌ Wave 0 |

**Note:** The audio synthesis itself (OscillatorNode, GainNode, autoplay gate) is pure browser JavaScript. It cannot be tested with pytest. Manual browser verification is the only mechanism for SND-01 (tone audibility) and SND-02 (autoplay gate). The integration tests cover the backend plumbing (that the constant reaches the template).

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_profile_api.py -x` (fast, catches regression in nearby profile code)
- **Per wave merge:** `uv run pytest tests/`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_log_view_notify_sound.py` — new file; covers `test_notify_sound_false_injected`, `test_notify_sound_true_injected`; requires an async test client that authenticates via cookie and GETs `/log/view`, asserting the rendered HTML contains `const NOTIFY_SOUND = "true"` or `"false"`.

**Infrastructure note:** Existing `conftest.py` initializes only the `QSO` model for `test_db`. A test for `log_view()` requires `User` model initialization and an HTTP test client (httpx + FastAPI test app). This is a non-trivial setup — the planner should either (a) treat SND-01 backend verification as manual-only, or (b) create a lightweight fixture that can render the log view with a mocked user. Option (a) is simpler and consistent with the project's existing pattern of manual browser verification for rendering concerns.

---

## Security Domain

This phase involves no new authentication paths, no new data ingestion, and no new API endpoints. The dependency swap in `log_view()` uses the existing `get_current_user_cookie` pattern (already used by `profile_page()`, `profile_update()`, `tokens_list()`, `tokens_create()`, `tokens_revoke()`). The operator isolation guarantee is unchanged — `callsign = user.callsign` is extracted from the JWT-validated User document, not from query params.

No new ASVS categories apply beyond those already covered by the existing auth infrastructure.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No change | Existing `get_current_user_cookie` (JWT HttpOnly cookie) |
| V5 Input Validation | No change | `notify_sound: bool` is a Python bool from Beanie; no user input reaches the JS injection point |

---

## Sources

### Primary (HIGH confidence)

- MDN Web Docs — OscillatorNode: https://developer.mozilla.org/en-US/docs/Web/API/OscillatorNode — constructor, frequency/type, start/stop, linearRampToValueAtTime usage
- MDN Web Docs — Web Audio API Best Practices: https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices — autoplay policy, lazy context creation, `context.state` check
- Context7 `/webaudio/web-audio-api` — W3C spec source; linearRampToValueAtTime scheduling semantics
- Project codebase — `templates/log/log.html` (read directly): existing IIFE, SSE listeners, integration points
- Project codebase — `app/qso/ui_router.py` (read directly): `log_view()` signature, existing imports, HX-Request branch
- Project codebase — `app/auth/dependencies.py` (read directly): `get_current_user_cookie` return type
- Project codebase — `app/auth/models.py` (read directly): `User.notify_sound: bool = False`

### Secondary (MEDIUM confidence)

- MDN Web Docs — Web Audio API Using Guide: https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Using_Web_Audio_API — GainNode usage, AudioContext.resume() pattern

### Tertiary (LOW confidence)

None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; verified from project codebase
- Architecture: HIGH — all integration points confirmed by direct file reads
- Web Audio patterns: HIGH — verified via MDN official documentation
- Pitfalls: HIGH — derived from code inspection and known browser behavior; Pitfall 5 (oscillator stop timing) is ASSUMED to be relevant based on audio engineering fundamentals but not specifically tested in this codebase
- Tone placement (Open Question): MEDIUM — interpretation of success criteria vs. code structure; flagged for planner decision

**Research date:** 2026-04-17
**Valid until:** 2026-05-17 (stable browser API; 30-day window)
