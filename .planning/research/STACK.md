# Technology Stack — v2.4 Live Log & Sound Alerts

**Project:** ollog v2.4
**Milestone:** Live Log & Sound Alerts
**Researched:** 2026-04-16
**Scope:** Additions and changes ONLY. Validated v2.3 stack is not re-listed.

---

## New Python Dependencies

**None required.** All four v2.4 features can be implemented with the existing Python stack.

| Candidate | Decision | Rationale |
|-----------|----------|-----------|
| Any beanie notifications/events lib | Not needed | Change stream already wired in `app/feed/manager.py` |
| Any audio Python library | Not applicable | Sound is pure browser-side Web Audio API |
| Any new FastAPI dependency | Not needed | Profile field addition is a Beanie document field + Pydantic schema change |

---

## New JavaScript Dependencies

**None required.** Web Audio API is a browser built-in.

| Candidate | Decision | Rationale |
|-----------|----------|-----------|
| `howler.js` | Rejected | Overkill for a single-tone notification; adds 100+ KB; no CDN audio files wanted |
| `tone.js` | Rejected | Even heavier; synthesis library for full compositions |
| `browser-beep` npm | Rejected | Thin wrapper around Web Audio API with no added value for this use case |
| Web Audio API (built-in) | **Use this** | Zero-dependency, baseline widely available since April 2021, pure JS |

---

## Feature 1: UDP-Inserted QSOs Trigger SSE Reload

### Root Cause Analysis (from code audit)

The `watch_qsos` coroutine in `app/feed/manager.py` watches the `qsos` collection for
`operationType: insert` events via a pymongo async change stream. Beanie's `qso.insert()`
calls `insertOne` on the underlying `AsyncMongoClient` collection — this is a standard MongoDB
write that DOES emit a change stream event. The chain is:

```
UDP datagram -> QSODatagramProtocol.datagram_received()
  -> asyncio.create_task(_handle_datagram())
    -> qso.insert()                      # Beanie -> pymongo insertOne
      -> MongoDB oplog insert event
        -> watch_qsos async for loop
          -> manager.broadcast(html)
            -> SSE event "new_qso" -> browser
```

The chain is architecturally sound. The most likely reason UDP inserts do NOT trigger SSE
in practice:

**`.env` missing replica set parameter.** `.env` has `MONGODB_URI=mongodb://mongodb:27017`
(no `?replicaSet=rs0`). The `watch_qsos` task fails on startup with
`PyMongoError: The $changeStream stage is only supported on replica sets`. The retry loop
catches this, sleeps 1 second, and crashes again in a tight loop — it never broadcasts.
Docker Compose has `?replicaSet=rs0` in the environment override, so the Docker path works.
Local dev without Docker uses the `.env` file directly and is silently broken.

**Secondary behaviour (not a bug):** `manager.broadcast(html)` sends the same SSE event to
every connected operator. Each operator's `htmx:sseMessage` handler checks `#auto-refresh-ok`
and reloads `/log/view`, which is scoped to their own callsign via cookie JWT. A UDP insert
for operator W1AW also triggers a reload for K1XY if both are on page 1. The reload is
correct (harmless, no data leak), just a minor extra HTTP request. Do not fix in v2.4.

### Fix Required

Add a `logger.error` call (not just `logger.warning`) in `watch_qsos` when the change stream
fails, with the full exception message. This makes the replica-set misconfiguration
immediately visible in logs.

The functional code path is already correct for Docker deployments. No logic changes needed
to make UDP inserts trigger the SSE chain.

**Reuse:** existing `htmx:sseMessage` handler in `templates/log/log.html`. No changes
to the handler logic for Feature 1.

---

## Feature 2: Dismissable "N new QSOs" Badge (Page 2+)

### Implementation Approach

Pure JavaScript counter in the existing `<script>` block in `templates/log/log.html`.
No new dependencies. No server changes.

**How it works:**

The `htmx:sseMessage` handler fires for every `new_qso` event regardless of page.

- When `#auto-refresh-ok` is present (page 1, default sort, no filters, no edit open):
  fire `htmx.ajax()` reload as today.
- When `#auto-refresh-ok` is absent (page 2+, filtered, edit open):
  increment a JS counter `pendingCount`, then render/update a badge element.

**Badge placement:** The badge must live OUTSIDE `#log-table` because `#log-table`'s
`innerHTML` is replaced on every pagination/filter/sort swap. The correct anchor is the
`#live-indicator` sibling in the page header flex row in `log.html` (lines 18–23). Add
`id="new-qso-badge"` as a sibling `<div>` there. It persists across all table swaps.

**Badge HTML (render once, show/hide via JS):**
```html
<div id="new-qso-badge" class="hidden items-center gap-2 px-3 py-1 rounded-md text-xs
     font-semibold bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-400">
  <span id="new-qso-count">0</span> new QSO<span id="new-qso-plural"></span>
  <button onclick="dismissNewQsoBadge()" class="ml-1 hover:text-indigo-900 dark:hover:text-white">
    &times;
  </button>
</div>
```

**Reset on navigation to page 1:** Hook `htmx:afterSwap` on the `#log-table` element.
After a swap, if `document.getElementById('auto-refresh-ok')` exists, the operator returned
to the default view — reset `pendingCount` to 0 and hide the badge.

**SSE event data:** The current `new_qso` SSE event payload is rendered `feed_row.html`
HTML. The badge only counts events; it does not parse the payload. No server changes needed.

---

## Feature 3: Web Audio API Tone Notification

### Technology Decision

**Use the Web Audio API directly.** No library. No CDN audio files.

**Confidence: HIGH** — AudioContext and OscillatorNode are Baseline Widely Available
(MDN designation since April 2021). Chrome 35+, Firefox 25+, Safari 14.1+, Edge 79+.

### Canonical Pattern

```javascript
// Created once at page load, reused for all notifications.
let _audioCtx = null;

function _getAudioCtx() {
  if (!_audioCtx) {
    _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
  return _audioCtx;
}

// Call from ANY user interaction on the log page (filter submit, sort click,
// pagination click). Unlocks the AudioContext once; it stays running for the
// page lifetime after that.
function _unlockAudio() {
  const ctx = _getAudioCtx();
  if (ctx.state === 'suspended') ctx.resume();
}

// Called from htmx:sseMessage handler when new_qso fires
// and notify_sound is true.
function playNotificationTone() {
  const ctx = _getAudioCtx();
  if (ctx.state !== 'running') return; // Silent before first user gesture.

  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.connect(gain);
  gain.connect(ctx.destination);

  osc.type = 'sine';
  osc.frequency.value = 880;                                   // A5, sharp and audible
  gain.gain.setValueAtTime(0.3, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.15);

  osc.start(ctx.currentTime);
  osc.stop(ctx.currentTime + 0.15);                            // Auto-GC after stop
}
```

**Tone parameters:**
- 880 Hz (A5): sharp enough to cut through a busy shack, not shrill
- 150 ms duration: brief notification, not an alarm
- Exponential gain ramp: clean stop, no click artifact at cutoff
- Gain 0.3: moderate; browser cannot exceed the system volume level

**Autoplay policy resolution:** All modern browsers block `AudioContext` from producing
sound until the page has received at least one user gesture. After that initial gesture,
the context stays in `running` state for the page's lifetime. SSE-triggered audio is
permitted after that point — the gesture does not need to be contemporaneous with the
sound. In practice, the operator will have clicked a filter, sort header, pagination link,
or the form before any UDP insert arrives. The `ctx.state !== 'running'` guard makes
the first few SSE events silent — this is acceptable and by design.

`unlockAudio()` should be called from the existing interactive elements already in
`log.html`: the filter form submit button, sort column anchors, and pagination links.
The simplest approach: attach a single `htmx:beforeRequest` listener on `document.body`
(fires on every HTMX request, which covers all user interactions in this page) to call
`_unlockAudio()`.

**Memory management:** `OscillatorNode.stop()` disconnects the node automatically after
the scheduled stop time. Nodes created with `ctx.createOscillator()` are garbage-collected
after they finish. No explicit cleanup required.

**`webkitAudioContext` prefix:** Required for Safari pre-14.1 (pre-2020). The
`window.AudioContext || window.webkitAudioContext` fallback is standard practice and
costs nothing.

---

## Feature 4: `notify_sound` Profile Field

### Model Change — `app/auth/models.py`

Add one field to the User Beanie document:

```python
notify_sound: bool = False   # Sound notification on new QSOs; opt-in
```

Default `False` is intentional — opt-in, never surprises an operator after upgrade.
No MongoDB migration needed: Beanie reads documents without the field as the default value.
Existing users get `False` until they enable it in Profile Settings.

### Schema Changes — `app/profile/schemas.py`

```python
# ProfileUpdateRequest — add:
notify_sound: Optional[bool] = None

# ProfileResponse — add:
notify_sound: bool = False
```

### UI Form Change — `templates/log/profile.html`

Add a checkbox toggle in the existing HTMX form. HTML checkboxes do not submit a value
when unchecked — an absent field means `False`, not "unchanged". This differs from all
other profile fields which are nullable strings. Handle in the route handler:

```python
# In profile_update() in ui_router.py — always include notify_sound:
raw["notify_sound"] = notify_sound is not None
```

Where `notify_sound: Annotated[Optional[str], Form()] = None` is the new Form parameter
(HTML checkbox submits `"on"` when checked, nothing when unchecked; treat any non-None
value as `True`).

### Passing `notify_sound` to Browser JavaScript

The log view JS needs to know whether to play the tone. The cleanest approach is an
inline JS constant injected in `log.html` from the template context:

```html
<!-- in log.html <script> block -->
const NOTIFY_SOUND = {{ 'true' if user.notify_sound else 'false' }};
```

This requires changing the `log_view` endpoint to use
`user: User = Depends(get_current_user_cookie)` instead of the current
`callsign: str = Depends(get_current_operator_callsign_cookie)`, and passing
`notify_sound: user.notify_sound` in the template context.

`NOTIFY_SOUND` is a module-level constant that survives HTMX table swaps (the `<script>`
block is in the outer page, not in `log_table.html`). The value is set at page load; if
the operator changes the setting, they need to reload the log view page to pick it up —
this is acceptable behaviour.

---

## Integration Points — What Changes vs What Stays

| Component | Change | Details |
|-----------|--------|---------|
| `app/feed/manager.py` | Logging improvement only | Add `logger.error` for replica-set failure |
| `app/feed/router.py` | No change | SSE event emission unchanged |
| `app/udp/server.py` | No change | UDP inserts already trigger change stream |
| `app/auth/models.py` | Add one field | `notify_sound: bool = False` |
| `app/profile/schemas.py` | Add field to two schemas | `notify_sound` in request + response |
| `app/profile/service.py` | No change | `update_profile()` passes any dict; handles new field automatically |
| `app/qso/ui_router.py` | Two changes | `log_view`: use `get_current_user_cookie` dep, pass `notify_sound` in ctx; `profile_update`: add `notify_sound` Form param + always include in `raw` dict |
| `templates/log/log.html` | Extend `<script>` block | Badge element; updated `htmx:sseMessage`; `playNotificationTone()`; `_unlockAudio()`; `NOTIFY_SOUND` constant |
| `templates/log/profile.html` | Add checkbox field | `notify_sound` toggle in form |
| `templates/log/log_table.html` | No change | `#auto-refresh-ok` sentinel logic unchanged |

---

## Patterns Reused From Prior Milestones

| Pattern | Source Milestone | Applied To |
|---------|-----------------|------------|
| `htmx:sseMessage` event listener | v1.6 | Badge counter and sound trigger added to existing handler body |
| Server-side `#auto-refresh-ok` sentinel span | v1.6 | Reused as-is for page 1 vs page 2+ discrimination |
| `window.dispatchEvent(new CustomEvent(...))` | v1.9 | `htmx:beforeRequest` body listener for audio unlock |
| `Optional[field] = None` in ProfileUpdateRequest | v1.1 | `notify_sound` uses `Optional[bool] = None` in schema |
| HTTP 200 always for HTMX form fragments | v1.1 / v2.0 | Profile update response unchanged |
| `model_construct()` in unit tests | v1.1 | Tests for `notify_sound` can reuse same pattern |
| Badge element outside swap target | v1.6 (live indicator) | Badge placed as sibling of `#live-indicator` not inside `#log-table` |

---

## What NOT to Add

| Item | Reason |
|------|--------|
| CDN audio files (.mp3, .wav) | Zero-dependency constraint; Web Audio synthesis covers the use case fully |
| howler.js or tone.js | Overkill; no CDN audio files; plain Web Audio API is sufficient |
| WebSocket upgrade | SSE is already working; no bidirectionality needed |
| Any new Python package | No server-side audio; profile field change requires no new library |
| `notify_sound` as a QSO field | It is a user preference, not QSO data; belongs in User document |
| Per-operator SSE channels | Multi-operator broadcast is acceptable; each reload is scoped by JWT |
| Service worker / Push API | Heavy overkill; SSE is already a persistent connection |
| Separate `/api/notify-sound` endpoint | Setting is read at page load; inline template context is sufficient |

---

## Browser Compatibility

| Feature | Chrome | Firefox | Safari | Edge | Note |
|---------|--------|---------|--------|------|------|
| `AudioContext` | 35+ | 25+ | 14.1+ | 79+ | Baseline widely available since April 2021 |
| `webkitAudioContext` prefix | 14–35 | No | 6–14 | No | Legacy fallback; keep in code for old Safari |
| `OscillatorNode` | 35+ | 25+ | 14.1+ | 79+ | Same as AudioContext |
| `GainNode` | 35+ | 25+ | 14.1+ | 79+ | Same |
| Autoplay policy (gesture required) | 66+ | 70+ | 14.1+ | 79+ | `resume()` after any user click suffices |
| `htmx:sseMessage` event | All modern | All modern | All modern | All modern | Fires from htmx-ext-sse 2.2.4 |
| SSE (`EventSource`) | All modern | All modern | All modern | All modern | Already in use since v1.6 |

No polyfill or library needed. The `window.AudioContext || window.webkitAudioContext`
one-liner covers all relevant browsers including old Safari.

---

## Sources

- MDN Web Docs — AudioContext (Baseline Widely Available): https://developer.mozilla.org/en-US/docs/Web/API/AudioContext
- MDN Web Docs — Web Audio API Best Practices: https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices
- Chrome Developers — Web Audio Autoplay Policy: https://developer.chrome.com/blog/web-audio-autoplay
- PyMongo Async Change Stream API: https://pymongo.readthedocs.io/en/stable/api/pymongo/asynchronous/change_stream.html
- MongoDB Change Events Reference: https://www.mongodb.com/docs/manual/reference/change-events/
- htmx-ext-sse extension: https://htmx.org/extensions/sse/
- Code audit: `app/feed/manager.py`, `app/udp/server.py`, `app/auth/models.py`,
  `app/qso/ui_router.py`, `templates/log/log.html`, `templates/log/log_table.html`,
  `docker-compose.yml`, `.env`
