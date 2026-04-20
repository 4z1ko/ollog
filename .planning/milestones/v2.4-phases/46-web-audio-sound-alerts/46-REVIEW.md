---
phase: 46-web-audio-sound-alerts
reviewed: 2026-04-17T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - tests/test_log_view_notify_sound.py
  - app/qso/ui_router.py
  - templates/log/log.html
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 46: Code Review Report

**Reviewed:** 2026-04-17T00:00:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed the three files that implement the phase-46 web-audio sound-alert feature: the new integration tests, the updated `log_view()` route in `ui_router.py`, and the updated `log.html` template.

The backend injection of `notify_sound` into the template context is correct and the `User.notify_sound` model default (`False`) is appropriate. The JavaScript sound engine is functionally sound for the happy path. Three warnings and three info items were found, none of which are critical, but two of the warnings risk the feature silently not working for users.

---

## Warnings

### WR-01: `playTone` promise rejection is silently swallowed

**File:** `templates/log/log.html:177-179`

**Issue:** `playTone()` is an `async` function that calls `ctx.resume()` (which returns a `Promise`). The call site at line 177 does not `await` the result and there is no `.catch()` attached. If the browser refuses to resume the `AudioContext` (e.g. autoplay policy enforcement on Safari/Chrome), the rejection is unhandled. In environments where unhandled promise rejections surface as uncaught errors this will produce console noise; on some browsers it can also abort the current microtask queue.

**Fix:**
```js
// Replace the bare call:
if (NOTIFY_SOUND === 'true' && userInteracted && audioCtx) {
  playTone(audioCtx).catch(function (err) {
    console.warn('ollog: playTone failed', err);
  });
}
```

---

### WR-02: `htmx:sseMessage` handler fires for every SSE message type, not just `new_qso`

**File:** `templates/log/log.html:165`

**Issue:** The guard `e.detail.type !== 'new_qso'` relies on the `type` property being set on the raw `MessageEvent` object (`e.detail`). The HTMX SSE extension sets `e.detail` to the raw `MessageEvent`; the `type` property on a `MessageEvent` is the *event name* string (e.g. `"new_qso"`). This is correct per the HTMX SSE extension docs, but the guard assumes that `e.detail` is always truthy and has a `.type` property. If the SSE extension ever passes `undefined` as `e.detail` (e.g. on a connection-level event with no data), line 165 will throw `TypeError: Cannot read properties of undefined (reading 'type')`, which will silently prevent the live-indicator logic from running for subsequent events.

**Fix:**
```js
// Add a more defensive guard:
if (!e.detail || typeof e.detail.type === 'undefined') return;
if (e.detail.type !== 'new_qso') return;
```

---

### WR-03: `osc.stop()` resource leak when `AudioContext` is suspended at tone-play time

**File:** `templates/log/log.html:135-156`

**Issue:** `playTone` creates an `OscillatorNode` and a `GainNode` unconditionally before calling `ctx.resume()`. If `resume()` is rejected (e.g. a second sound fires before the first resume resolves), the oscillator has already been started via `osc.start(now)` with `now` from the *old* `ctx.currentTime` (before resume). After a late resume the oscillator's scheduled stop time (`now + 0.12`) may already have passed, leaving the oscillator in a started-but-never-stopped state until the GC collects it. On browsers with strict AudioNode limits this can exhaust the node pool over many QSOs.

**Fix:** Move node creation after the `await ctx.resume()` call so `ctx.currentTime` is accurate at scheduling time:
```js
async function playTone(ctx) {
  if (ctx.state === 'suspended') {
    await ctx.resume();
  }
  var now = ctx.currentTime;  // read AFTER resume
  var osc = ctx.createOscillator();
  var gain = ctx.createGain();
  // ... rest of scheduling unchanged
}
```
Note: the current code already does read `now` after the `resume()` check, so this is a latent issue only if `resume()` is very slow. The bigger practical fix is wrapping the call site in `.catch()` (WR-01) which prevents the broken-state path entirely.

---

## Info

### IN-01: Test fixture `client` does not use the per-test database

**File:** `tests/test_log_view_notify_sound.py:38-43`

**Issue:** The `client` fixture creates an `AsyncClient` backed by `app.main:app`, but its scope is `function` and it does not receive `log_view_db` as a parameter. Beanie is initialized against `ollog_log_view_test` by `log_view_db`, but only if `log_view_db` runs first. Pytest-asyncio fixture ordering is determined by dependency injection, not declaration order. Because `client` does not depend on `log_view_db`, there is no guarantee Beanie is initialized before the client is used. The tests happen to pass because both fixtures are `function`-scoped and pytest-asyncio resolves them in the order they appear in the test signature (`client, operator, log_view_db`), but the `operator` fixture depends on `log_view_db`, which is what actually forces correct ordering. If a future test uses `(client, log_view_db)` directly without `operator`, the ordering guarantee disappears.

**Fix:** Add `log_view_db` as an explicit parameter to the `client` fixture, or document the ordering assumption with a comment:
```python
@pytest_asyncio.fixture(scope="function")
async def client(log_view_db):  # explicit dep ensures Beanie is initialized first
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

---

### IN-02: `NOTIFY_SOUND` constant is a string comparison, not a boolean

**File:** `templates/log/log.html:116`

**Issue:** The template emits `const NOTIFY_SOUND = "true"` or `const NOTIFY_SOUND = "false"` (string literals). The guard at line 177 correctly compares `NOTIFY_SOUND === 'true'`. This is intentional but fragile — any future developer reading `if (NOTIFY_SOUND === 'true')` may be surprised and "fix" it to `if (NOTIFY_SOUND)`, which would always evaluate to truthy because any non-empty string is truthy in JS. Recommend using a proper JS boolean:

```html
<!-- In log.html line 116: -->
const NOTIFY_SOUND = {{ 'true' if notify_sound else 'false' }};
```
This emits a bare JS boolean (`true`/`false`) rather than a string, making the intent unambiguous and the guard simpler (`if (NOTIFY_SOUND && userInteracted && audioCtx)`).

---

### IN-03: `indicator.querySelector('span:last-child')` is brittle

**File:** `templates/log/log.html:170`

**Issue:** The live indicator's text content is updated by selecting `span:last-child` inside `#live-indicator`. The live indicator markup (lines 18-23) has two `<span>` children: the pulsing dot and the text "LIVE". Selecting by structural position means any future addition of a child element (e.g. a tooltip, an icon) before or after the text span silently updates the wrong element. This same pattern repeats in the `htmx:sseError` handler at line 189.

**Fix:** Add a stable `id` or `data-` attribute to the text span:
```html
<span id="live-indicator-label">LIVE</span>
```
Then reference it by id:
```js
document.getElementById('live-indicator-label').textContent = 'LIVE';
```

---

_Reviewed: 2026-04-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
