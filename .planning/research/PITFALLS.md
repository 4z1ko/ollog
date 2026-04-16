# Domain Pitfalls — v2.4 Live Log & Sound Alerts

**Domain:** Adding SSE live-refresh fix + Web Audio notifications to existing FastAPI/HTMX/SSE/MongoDB app
**Researched:** 2026-04-16
**Scope:** v2.4 only — pitfalls specific to these four problem areas:
1. Debugging the UDP → change-stream → SSE → HTMX table-refresh chain
2. Building a client-side new-QSO counter badge for page 2+
3. Web Audio API oscillator tone with autoplay constraints
4. Adding `notify_sound: Optional[bool]` to the Beanie `User` document

---

## Critical Pitfalls

### Pitfall 1: SSE sse-connect Element Destroyed When Its Own outerHTML Is Replaced

**What goes wrong:** The `#log-table` div carries `hx-ext="sse" sse-connect="/feed/station"`. When an HTMX swap replaces the *contents* of `#log-table` (i.e., `hx-swap="innerHTML"`), the div element itself persists and the SSE connection survives. But if anything performs an `outerHTML` swap or `htmx.ajax()` call that targets `#log-table` with `outerHTML`, the element is removed from the DOM, the htmx-ext-sse extension fires `htmx:sseClose` with reason `nodeReplaced`, and the EventSource is permanently closed — silently, with no reconnect.

**Root cause:** The current `htmx:sseMessage` handler correctly calls `htmx.ajax('GET', '/log/view', { target: '#log-table', swap: 'innerHTML' })`. This is safe. The risk is any future code that adds a badge counter or other SSE-triggered swap using `swap: 'outerHTML'` against the `#log-table` container itself.

**Consequences:** After one misfired `outerHTML` swap on `#log-table`, live updates stop until page reload. The LIVE indicator may not reflect this because `htmx:sseClose` fires asynchronously and the indicator logic could miss it if the element was already removed before the event propagated.

**Prevention:**
- The badge counter element must be a sibling of `#log-table`, never a child of it.
- Never retarget `#log-table` with `swap: 'outerHTML'` from the `htmx:sseMessage` handler.
- Verify SSE survival after pagination: DevTools → Network → EventStream tab should show continuous event flow after clicking Previous/Next.

**Detection:** After any pagination click, confirm the SSE connection is still open in DevTools Network → EventStream. A closed stream appears as a grayed-out entry with no new events.

**Phase:** First implementation phase (live refresh + badge). Must verify SSE connection survives every HTMX swap before considering the feature complete.

---

### Pitfall 2: Web Audio AudioContext Created on Page Load Is Permanently Suspended

**What goes wrong:** Chrome, Firefox, and Safari all enforce the autoplay policy: an `AudioContext` created before any user gesture starts in `suspended` state. Calling `oscillator.start()` on a node connected to a suspended context plays nothing — no error is thrown. The SSE event handler that fires on QSO arrival is not a user gesture, so even calling `audioCtx.resume()` from inside it may have no effect if the context was never unlocked.

**Root cause:** Browsers require audio to originate from — or be explicitly unlocked during — a user gesture (click, keydown, touchstart). An `AudioContext` created in a `<script>` tag or module-level code on page load will be `suspended`, regardless of subsequent non-gesture-triggered `resume()` calls.

**Consequences:** Sound toggle appears to save correctly (profile field updated), LIVE indicator shows QSOs arriving, but zero audio plays. The browser console shows no errors. `audioCtx.state` is the only diagnostic signal.

**Prevention:**
- Create `AudioContext` lazily on the first user interaction that enables the sound feature — the profile checkbox click is itself a valid user gesture.
- Before every oscillator play, check `if (audioCtx.state === 'suspended') { await audioCtx.resume(); }`.
- One `AudioContext` per page session: store it in a module-level variable, create only once, reuse for all subsequent oscillator nodes.
- Add a visible "Test sound" button on the profile page. Clicking it creates/resumes the context and fires one test tone — this is the most reliable cross-platform unlock mechanism.

**Detection:** `console.log(audioCtx.state)` in the SSE handler. Expected value: `'running'`. Any other value means sound will not play.

**Phase:** Audio tone implementation phase.

---

### Pitfall 3: iOS Safari Requires touchstart (Not Just click) to Unlock AudioContext

**What goes wrong:** Chrome and Firefox honour `click` as a sufficient gesture to unlock an `AudioContext`. On iOS Safari, the `click` event alone may not satisfy WebKit's audio unlock requirement — the context stays `suspended` after `audioCtx.resume()` is called from a click handler. Additionally, iOS's hardware silent switch blocks all Web Audio output regardless of `AudioContext` state; this is not a software issue and has no workaround.

**Root cause:** Apple's WebKit WebAudio implementation has historically required `touchstart` (or a combined touch+click flow) for the initial unlock. The behaviour has been partially relaxed in newer iOS versions but remains inconsistent across iOS 16–18.

**Consequences:** Audio works on desktop Chrome/Firefox/Safari but fails silently on all iOS devices. The operator toggled sound on, the profile shows it enabled, but no tone plays.

**Prevention:**
- Listen on both `click` and `touchstart` when initializing the `AudioContext` unlock: `['click', 'touchstart'].forEach(ev => document.addEventListener(ev, initAudio, {once: true}))`.
- The "Test sound" button (see Pitfall 2) provides the explicit interaction needed for iOS.
- Document the iOS silent switch as a known hardware limitation in the profile toggle's help text.

**Detection:** Test on a physical iOS device. If `audioCtx.state` remains `'suspended'` after toggle click, the `touchstart` listener is needed.

**Phase:** Audio tone implementation phase. Low extra effort if the unlock pattern is designed correctly from the start.

---

### Pitfall 4: Change Stream Watcher Task Has No Strong Reference — Silent GC Kill on Python 3.12+

**What goes wrong:** If the `watch_qsos` coroutine is started with `asyncio.create_task()` but the returned task object is not held by a strong reference (e.g., stored in a module-level set or the lifespan state), Python 3.12+'s garbage collector may collect the task mid-run. The task silently disappears with no exception, no log entry, and the SSE feed stops receiving change stream events.

**Root cause:** Python 3.12+ explicitly warns (and in some builds, enforces) that tasks without strong references are eligible for GC. The UDP server already handles this correctly with `self._background_tasks: set[asyncio.Task]`. The same pattern must be applied to the `watch_qsos` task in the lifespan.

**Consequences:** The SSE change stream watcher stops silently. All operators see the LIVE indicator turn green (the SSE *connection* is alive) but no new QSOs trigger table refreshes. The symptom is identical to "no QSOs are being inserted," making diagnosis confusing.

**Prevention:**
- Store the `watch_qsos` task in the FastAPI lifespan `state` dict or a module-level strong reference: `app.state.watcher_task = asyncio.create_task(watch_qsos(...))`.
- Add a startup log line from inside `watch_qsos` confirming the watcher entered its event loop (distinct from the startup banner that confirms the task was created).

**Detection:** `logger.debug("watch_qsos: waiting for next change stream event")` inside the `async for change in stream:` loop confirms the watcher is alive.

**Phase:** This is the first thing to check in the live refresh fix phase.

---

### Pitfall 5: UDP QSO Insert Does Not Reach the SSE Client — Diagnosis Order

**What goes wrong:** The symptom "UDP QSOs appear in `/log/view` after reload but do not trigger live refresh" means the insert reached MongoDB but the broadcast did not reach the SSE client. The failure can occur at any of four points in the chain.

**Diagnosis order (fastest to slowest):**

1. **Is `watch_qsos` alive?** Run `mongosh` and execute `db.qsos.watch([{$match: {operationType: "insert"}}])`, then send a test UDP datagram. If the mongosh watch fires, the replica set oplog is working and the issue is in the Python watcher. If mongosh watch does not fire, the issue is in MongoDB (replica set not running, wrong database, or insert is on a different connection's transaction that has not committed).

2. **Is the watcher watching the correct collection?** The `watch_qsos` function receives a `collection` argument from the lifespan. Verify this is `await QSO.get_motor_collection()` — wait, this codebase uses `get_pymongo_collection()` (Motor EOL'd). Confirm the async collection object is correct: `collection = QSO.get_pymongo_collection()`.

3. **Is the broadcast reaching any queue?** Add `logger.debug("broadcasting to %d clients", len(mgr._queues))` in `ConnectionManager.broadcast()`. Zero clients means no SSE connections are open. Non-zero means the broadcast is sent but the client is not processing it.

4. **Is the `htmx:sseMessage` handler filtering the event out?** The handler checks `e.detail.elt.id !== 'log-table'` and `e.detail.type !== 'new_qso'`. Log these values in the browser console during a test insert.

**Consequences:** Without this diagnosis sequence, hours can be lost chasing the wrong layer.

**Prevention:** Log the change stream event at DEBUG level on receipt. Log the number of broadcast targets. Log the SSE event type on the client side during development.

**Phase:** First phase of v2.4. This is the core bug to fix.

---

## Moderate Pitfalls

### Pitfall 6: Counter Badge State Must Live Outside the HTMX Swap Target

**What goes wrong:** The "N new QSOs" badge counter for page 2+ must be maintained in a JavaScript variable and rendered in a DOM element that is never touched by HTMX swaps. If the badge element is placed inside `#log-table`, it is destroyed and re-created on every pagination or filter swap, resetting the count to zero.

**Root cause:** Every HTMX swap that targets `#log-table` with `innerHTML` replaces the entire inner content of the div, including any badge placed inside it.

**The wrong approach:** A badge rendered inside `log_table.html` (the HTMX partial). The partial is replaced on every navigation event.

**Prevention:**
- Place the badge element as a direct sibling of `#log-table` in `log.html`, outside the partial template.
- Manage badge visibility entirely in JavaScript: increment on `htmx:sseMessage` when `#auto-refresh-ok` is absent, reset on any `htmx:afterSwap` targeting `#log-table`, and on the dismiss click.
- The badge state does not need to survive page reload — a reload shows the current table.

**Detection:** Navigate to page 2, watch for a UDP QSO insert, confirm the badge appears. Then click Previous/Next and confirm the badge resets to zero.

**Phase:** Badge counter implementation, same phase as live refresh fix.

---

### Pitfall 7: HTML Checkbox Does Not Send Value When Unchecked — Toggle Cannot Be Turned Off

**What goes wrong:** HTML checkbox inputs send their value in the form body only when checked. When unchecked, the browser sends nothing — the key is absent from the POST body. If the `profile_update` endpoint treats an absent `notify_sound` key as "no change," the user can enable sound notifications but can never disable them via the form.

**Root cause:** This is standard HTML form behavior, not a bug. Every framework that handles checkboxes must account for it.

**Consequences:** Profile toggle is one-directional: on → permanently on, with no way to turn off without direct database manipulation.

**Prevention:**
- Add a hidden input immediately before the checkbox:
  ```html
  <input type="hidden" name="notify_sound" value="false">
  <input type="checkbox" name="notify_sound" value="true" ...>
  ```
  When unchecked, the hidden field sends `false`. When checked, the checkbox value `true` overrides it (last value wins in standard form encoding — verify FastAPI form parsing behaviour; if it takes the first value, reverse the order).
- In the handler, coerce `notify_sound` explicitly: `"true"` → `True`, `"false"` → `False`, `None`/absent → `None` (no change).
- Add `notify_sound: Optional[bool] = None` to `ProfileUpdateRequest` with a validator that accepts string `"true"`/`"false"` as well as booleans.

**Phase:** Profile toggle implementation phase. This must be tested explicitly.

---

### Pitfall 8: `Optional[bool]` Field in Beanie User Document — `None` is Not `False` in MongoDB Queries

**What goes wrong:** Adding `notify_sound: Optional[bool] = None` to the `User` document means every existing user document in MongoDB has no `notify_sound` field at all. Beanie reads missing fields as the Python default (`None`). The template check `if user.notify_sound:` correctly returns `False` for both `None` and `False` — no migration is needed for the display path.

**The risk:** If any service code queries users with `User.find({User.notify_sound == False})` (Beanie query syntax) or the raw MongoDB filter `{notify_sound: False}`, it will match documents where the field is explicitly `false` but *not* documents where the field is missing or `null`. For a query that means "find operators who have NOT enabled sound," this query misses every pre-existing user.

**Root cause:** MongoDB distinguishes between a field being absent, `null`, and `false`. `{notify_sound: False}` matches only explicit `false`.

**Consequences for v2.4:** Low risk. No service-layer code needs to query by `notify_sound`. The risk is in future milestones that might send a "QSO alert" to all operators with sound enabled.

**Prevention:**
- `Optional[bool] = None` in `User` — correct, matches existing optional field pattern.
- If ever querying "sound NOT enabled," use `{notify_sound: {"$ne": True}}` — this matches `False`, `None`, and missing field.
- No migration script needed for v2.4 since `None` correctly defaults to sound off.
- Document the `None` vs `False` semantics as a comment next to the field in the model.

**Phase:** Profile toggle model addition. One-line addition to `User` and `ProfileUpdateRequest`.

---

### Pitfall 9: AudioContext Instance Limit — Do Not Create Per-Event

**What goes wrong:** Browsers limit concurrent `AudioContext` instances (Chrome: ~6 per tab, lower on mobile). If the `htmx:sseMessage` handler creates a new `AudioContext` for each QSO arrival, the limit is hit after a few QSOs and subsequent `new AudioContext()` calls throw `DOMException` or silently return a broken context.

**Root cause:** `AudioContext` objects are not automatically garbage-collected until `audioCtx.close()` is called. Unclosed contexts accumulate.

**Consequences:** After 6 QSOs with sound enabled, sound stops working. The error in the console is obscure (`DOMException: Failed to construct 'AudioContext'`).

**Prevention:**
- One `AudioContext` per page session. Store in a module-level variable. Create only once (lazily on first user gesture). Reuse for all subsequent oscillator nodes.
- `OscillatorNode` and `GainNode` are single-use by design (`start()` can be called only once on each). Create new nodes per tone, but always connect them to the *same* `AudioContext`.
- Use `oscillator.stop(audioCtx.currentTime + duration)` — the browser garbage-collects stopped nodes automatically.

**Phase:** Audio tone implementation phase. Design the single-context pattern from the start.

---

### Pitfall 10: FT8 Burst Creates SSE Event Flood — Table Refresh Stampede

**What goes wrong:** FT8 produces QSOs in roughly 15-second cycles. A busy station may log 5–20 QSOs per cycle. Each insert triggers a change stream event → SSE broadcast → `htmx:sseMessage` → `htmx.ajax('GET', '/log/view')`. With 5 operators connected and a burst of 10 QSOs, the server receives up to 50 concurrent `GET /log/view` requests.

**Root cause:** The current `htmx:sseMessage` handler fires one `htmx.ajax()` per SSE event with no debounce.

**Consequences:** At home-station scale (1–2 operators), harmless. At contest scale (6+ operators, heavy FT8), unnecessary server load and potential visual flicker from repeated DOM swaps.

**Prevention:**
- Debounce the `htmx.ajax()` call: `clearTimeout(refreshTimer); refreshTimer = setTimeout(() => htmx.ajax(...), 400);`
- The badge counter increment should *not* be debounced — it should fire on every event. Only the full table re-fetch is debounced.
- 400ms is sufficient to collapse an entire FT8 burst into one refresh.

**Note:** This is not blocking for v2.4 at ollog's typical scale, but the debounce should be added in the same commit as the refresh fix — it is a one-liner addition.

**Phase:** Live refresh fix phase.

---

## Minor Pitfalls

### Pitfall 11: `ProfileUpdateRequest` Schema Must Include `notify_sound`

**What goes wrong:** `ProfileUpdateRequest` in `app/profile/schemas.py` is the gatekeeper for what fields reach `update_profile()`. If `notify_sound` is not added to this schema, the router discards it before validation and it is never written to MongoDB.

**Prevention:** Add `notify_sound: Optional[bool] = None` to `ProfileUpdateRequest`. Add a corresponding parameter in the `profile_update` endpoint's function signature in `app/qso/ui_router.py`. Two-line change.

**Phase:** Profile toggle implementation phase.

---

### Pitfall 12: Jinja2 Checkbox `checked` Attribute for `Optional[bool]`

**What goes wrong:** `{{ 'checked' if profile.notify_sound == True else '' }}` handles `True` but renders no `checked` for both `None` and `False` — correct behavior. However, using `{{ 'checked' if profile.notify_sound else '' }}` is equally correct and simpler: both `None` and `False` are falsy in Python/Jinja2.

**The wrong approach:** `{{ 'checked' if profile.notify_sound is not None and profile.notify_sound else '' }}` — overly complex and still equivalent.

**Prevention:** Use `{{ 'checked' if profile.notify_sound else '' }}`. Test with a fresh user (field is `None`) and a user who explicitly disabled sound (field is `False`) — both should render an unchecked checkbox.

**Phase:** Profile toggle template.

---

### Pitfall 13: `htmx:sseMessage` detail.type Is the Correct Property Name

**What goes wrong:** The SSE extension's `htmx:sseMessage` event detail object is the native `MessageEvent` from the browser's `EventSource`. The event type name is accessed as `e.detail.type`. Attempting `e.detail.event` (as some informal docs suggest) returns `undefined` in htmx-ext-sse 2.2.4.

**Prevention:** The existing code correctly uses `e.detail.type !== 'new_qso'`. For the badge counter, reuse the same `htmx:sseMessage` listener — no new event type is needed.

**Phase:** Awareness only. No action needed if the existing pattern is reused.

---

### Pitfall 14: `update_profile` Already Uses `$set` — `notify_sound=False` Is Stored Correctly

**What goes wrong:** Concern that `model_dump(exclude_unset=True)` might drop `False` values because they look "falsy." This is not how Pydantic works: `exclude_unset=True` excludes fields that were not explicitly provided to the constructor, not fields with falsy values. If `notify_sound=False` is passed to `ProfileUpdateRequest`, it will appear in `model_dump(exclude_unset=True)`.

**Prevention:** As long as the hidden-field checkbox trick (Pitfall 7) sends `"false"` to the endpoint, and the endpoint coerces it to `bool(False)` before passing to `ProfileUpdateRequest`, the `$set` will write `false` to MongoDB. No special handling in `update_profile()` is needed.

**Phase:** Verify in the first integration test for the toggle.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Live refresh fix | `watch_qsos` task has no strong reference, silently GC'd | Store task in `app.state.watcher_task` or module-level set; add startup debug log |
| Live refresh fix | Wrong collection object passed to watcher | Log collection name and DB name on watcher startup |
| Live refresh fix | Change stream not firing (replica set not running) | Test with `mongosh` change stream watch before debugging Python layer |
| Live refresh fix | Debounce missing during FT8 burst | Add 400ms debounce on `htmx.ajax` call in same commit |
| Badge counter | Badge element inside `#log-table` (destroyed on swap) | Badge must be a sibling of `#log-table`, outside the partial template |
| Badge counter | Counter not reset on pagination | Listen on `htmx:afterSwap` targeting `#log-table` to reset counter |
| Badge counter | SSE connection killed by outerHTML swap | Verify SSE connection survives in DevTools after pagination |
| Web Audio init | AudioContext created at page load, permanently suspended | Lazy-init on first user gesture; check `audioCtx.state` before playing |
| Web Audio init | iOS Safari not unlocked by click alone | Listen on both `touchstart` and `click`; provide visible "Test sound" button |
| Web Audio init | Multiple contexts from per-event creation | One context per page session; new OscillatorNode per tone |
| Profile toggle form | Unchecked checkbox sends no value | Hidden input `value="false"` before checkbox (last-field-wins in form encoding) |
| Profile toggle model | `notify_sound` missing from `ProfileUpdateRequest` | Add `Optional[bool]` to schema and handler signature |
| Profile toggle model | Future DB query `{notify_sound: false}` misses old users | Use `{notify_sound: {$ne: True}}` if ever querying by this field |
| Profile toggle template | `checked` attribute rendering for `None` | Use `{{ 'checked' if profile.notify_sound else '' }}` |

---

## Sources

- [Web Audio API best practices — MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API/Best_practices)
- [Autoplay policy in Chrome — Chrome for Developers](https://developer.chrome.com/blog/autoplay)
- [Web Audio, Autoplay Policy and Games — Chrome for Developers](https://developer.chrome.com/blog/web-audio-autoplay)
- [Unlock JavaScript Web Audio in Safari for iOS — Matt Montag](https://www.mattmontag.com/web/unlock-web-audio-in-safari-for-ios-and-macos)
- [htmx SSE Extension documentation — htmx.org](https://htmx.org/extensions/sse/)
- [htmx SSE Extension source — GitHub bigskysoftware/htmx-extensions](https://github.com/bigskysoftware/htmx-extensions/blob/main/src/sse/sse.js)
- [Removing DOM element using SSE does not close the SSE connection — htmx issue #2510](https://github.com/bigskysoftware/htmx/issues/2510)
- [Swapping via SSE not working when content has same id — htmx issue #295](https://github.com/bigskysoftware/htmx/issues/295)
- [PyMongo async change stream documentation](https://pymongo.readthedocs.io/en/stable/api/pymongo/asynchronous/change_stream.html)
- [MongoDB Change Streams — official documentation](https://www.mongodb.com/docs/manual/changestreams/)
- [Change stream fullDocument on delete — MongoDB community forum](https://www.mongodb.com/community/forums/t/change-stream-fulldocument-on-delete/15963)
- [Query for Null or Missing Fields — MongoDB documentation](https://www.mongodb.com/docs/manual/tutorial/query-for-null-fields/)
- [Beanie Migrations documentation](https://beanie-odm.dev/tutorial/migrations/)
