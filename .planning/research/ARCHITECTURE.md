# Architecture Patterns: v2.4 Live Log & Sound Alerts

**Milestone:** v2.4 Live Log & Sound Alerts
**Researched:** 2026-04-16
**Based on:** Direct codebase reading (no inference)

---

## Current SSE/HTMX Architecture (as-built)

### Complete Data Flow for a Successful Auto-Refresh (Page 1, No Filters)

```
QSO.insert()                         [any source: REST API, UI form, UDP]
  -> MongoDB oplog write
    -> change stream fires             [app/feed/manager.py: watch_qsos()]
      -> feed_row.html rendered        [Jinja2, operator-agnostic HTML]
        -> mgr.broadcast(html)         [puts html string into all connected queues]
          -> station_feed() yields     [app/feed/router.py: ServerSentEvent(data=html, event="new_qso")]
            -> browser receives SSE    [htmx-ext-sse 2.2.4 on #log-table]
              -> htmx:sseMessage fires [log.html inline script]
                -> checks event.type == 'new_qso'
                -> checks document.getElementById('auto-refresh-ok')
                -> checks !document.querySelector('#log-table input')
                -> htmx.ajax('GET', '/log/view', {target:'#log-table', swap:'innerHTML'})
                  -> log_view() re-renders log_table.html with fresh page 1 data
```

### The #auto-refresh-ok Sentinel

Rendered in `log_table.html` only when ALL of:
- `page == 1`
- `sort == '-qso_date_utc'`
- No `call`, `band`, `mode`, `date_from`, `date_to` filters active

The sentinel is a `<span id="auto-refresh-ok" hidden></span>`. Its presence or absence is the server's single source of truth about whether auto-refresh is permitted. It lives inside `#log-table` (the HTMX swap target), so every pagination or filter navigation atomically updates its presence.

### The SSE Connection Lifecycle

The `hx-ext="sse"` and `sse-connect="/feed/station"` attributes are on `#log-table` (the outer container div in `log.html`), NOT inside `log_table.html` (the partial). This is load-bearing: the partial is the HTMX swap target — its innerHTML is replaced on every navigation, but `#log-table` itself persists, keeping the SSE connection alive across all pagination and filter interactions.

### The Operator Isolation Gap in the Change Stream

`watch_qsos()` fires for every insert into the `qsos` collection from every operator. It broadcasts the rendered `feed_row.html` to all connected SSE clients regardless of which operator owns the new QSO. The client-side `htmx:sseMessage` handler never inspects the operator field in the SSE payload — it only checks `#auto-refresh-ok` and the edit-row guard.

This is already operator-safe: the `/log/view` re-fetch enforces operator isolation via JWT. The broadcast being unscoped is intentional and correct.

### The Likely SSE Bug

For UDP QSOs: `QSO.insert()` is called identically in `_handle_datagram()` as in the REST API path. The change stream pipeline `[{"$match": {"operationType": "insert"}}]` matches all inserts regardless of source. The UDP insert MUST trigger the change stream.

The most probable failure mode: a Jinja2 render error inside `watch_qsos()` that is not caught. The current exception handler only catches `PyMongoError`. A `TypeError` or `AttributeError` from `feed_row.html` attempting `qso_date_utc.strftime(...)` when `qso_date_utc` is `None` would propagate out of the `async for` body and kill the watcher task entirely. Once dead, the watcher does not restart. All subsequent inserts (UDP or REST) produce no SSE events. The LIVE indicator stays green (the SSE connection is still open — the watcher dying does not close client connections), so operators see no signal that live updates have stopped.

Secondary suspect: `change.get("fullDocument", {})` returns `{}` for some change events, causing broadcast of empty HTML. The client still receives the event, fires `htmx.ajax()`, and the table reloads correctly — but this would appear as "works fine" not "not working."

---

## v2.4 Component Map

### Modified Components

| Component | File | What Changes |
|-----------|------|--------------|
| Change stream watcher | `app/feed/manager.py` | Wrap Jinja2 render in `try/except Exception` with `logger.error` + `continue`; add debug logging around broadcast |
| SSE message handler | `templates/log/log.html` | Add badge counter logic; add Web Audio tone trigger; add `htmx:afterSettle` handler for badge re-sync |
| Log table partial | `templates/log/log_table.html` | Add badge HTML element (hidden by default) |
| User model | `app/auth/models.py` | Add `notify_sound: bool = False` |
| Profile schema | `app/profile/schemas.py` | Add `notify_sound: Optional[bool]` to `ProfileUpdateRequest` and `ProfileResponse` |
| Profile service | `app/profile/service.py` | No logic change — `update_profile()` already passes arbitrary dict keys to `$set` |
| Profile UI handler | `app/qso/ui_router.py` | Add `notify_sound` Form param to `profile_update()`; change `log_view()` dependency from `get_current_operator_callsign_cookie` to `get_current_user_cookie`; add `notify_sound` to log_view context |
| Profile template | `templates/log/profile.html` | Add "Notifications" section with sound toggle checkbox |

### New Components

None. All v2.4 features fit within existing files. No new Python modules, routers, or MongoDB collections.

---

## Feature Integration Points

### 1. SSE Bug Fix

**Integration point:** `app/feed/manager.py` `watch_qsos()` inner loop body.

Two changes:

1. Wrap the render call: `try: html = templates.get_template(...).render(ctx) except Exception as e: logger.error("feed_row render failed: %s", e); continue`
2. Add: `logger.debug("SSE broadcast call=%s operator=%s", ctx["call"], ctx["operator"])` before `mgr.broadcast(html)`.

The `while True` / `PyMongoError` reconnect logic is already correct for MongoDB connectivity failures. The fix extends it to cover template render failures without crashing the watcher.

### 2. "N New QSOs" Badge

**Integration points:**

`templates/log/log_table.html` — add badge HTML at top of file (before the empty-state check):

```html
<div id="new-qso-badge" class="hidden ...">
  <span id="new-qso-count">0</span> new QSO<span id="new-qso-plural">s</span>
  <button onclick="dismissBadge()">Dismiss</button>
</div>
```

`templates/log/log.html` script block — add:

```javascript
var qsoCounter = 0;

function updateBadge() {
  var badge = document.getElementById('new-qso-badge');
  if (!badge) return;
  if (qsoCounter > 0) {
    document.getElementById('new-qso-count').textContent = qsoCounter;
    document.getElementById('new-qso-plural').textContent = qsoCounter === 1 ? '' : 's';
    badge.classList.remove('hidden');
  } else {
    badge.classList.add('hidden');
  }
}

function dismissBadge() {
  qsoCounter = 0;
  updateBadge();
}
```

Modify the existing `htmx:sseMessage` handler:
- When `#auto-refresh-ok` present: call `htmx.ajax()` then `qsoCounter = 0; updateBadge()` (reset on reload).
- When `#auto-refresh-ok` absent: `qsoCounter++; updateBadge()`.

Add `htmx:afterSettle` handler: after every HTMX DOM swap (pagination, filter navigation, SSE-triggered reload), call `updateBadge()` to re-sync the freshly-rendered badge element with the current `qsoCounter`.

**Why counter lives in JS, not DOM:** The badge element is inside `log_table.html` (the HTMX swap target). Every HTMX swap replaces the element, resetting its text content. The JS variable `qsoCounter` is in the outer `log.html` scope and survives all swaps. The `htmx:afterSettle` handler bridges the gap by re-applying `qsoCounter` to the newly-rendered badge after each swap.

### 3. Web Audio Tone

**Integration point:** `templates/log/log.html` only. Zero server changes.

Pattern for AudioContext init (browser autoplay policy compliance):

```javascript
var audioCtx = null;

function initAudio() {
  if (!audioCtx) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  }
}

function playTone() {
  if (!audioCtx) return;
  var osc = audioCtx.createOscillator();
  var gain = audioCtx.createGain();
  osc.connect(gain);
  gain.connect(audioCtx.destination);
  osc.frequency.value = 880;
  gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.3);
  osc.start(audioCtx.currentTime);
  osc.stop(audioCtx.currentTime + 0.3);
}

document.addEventListener('click', initAudio, { once: true });
document.addEventListener('keydown', initAudio, { once: true });
```

In `htmx:sseMessage` handler, add: `if (NOTIFY_SOUND) playTone();`

`NOTIFY_SOUND` is a template variable baked in by the server (see below).

### 4. notify_sound Gating in log.html

**Problem:** `log_view()` currently depends on `get_current_operator_callsign_cookie` which returns a string. The `notify_sound` preference lives on the User document. To pass it to the template, the handler must load the full User.

**Solution:** Change the dependency from `get_current_operator_callsign_cookie` to `get_current_user_cookie` in `log_view()`. Extract `callsign = user.callsign` for existing usage. Add `"notify_sound": user.notify_sound` to `ctx`.

This is a 3-line change in `ui_router.py`. `get_current_user_cookie` is already imported in the same file (used by `profile_update()` and `submit_qso()`). The extra DB read per page load is one indexed lookup by `_id` — negligible.

In `log.html`, emit before the existing script:

```html
<script>
  var NOTIFY_SOUND = {{ 'true' if notify_sound else 'false' }};
</script>
```

### 5. notify_sound Profile Toggle

**Checkbox encoding issue:** HTML checkboxes send the named field only when checked. If unchecked, the field is absent from the form POST body. FastAPI Form() parameter with `Optional[bool] = None` receives `None` when the checkbox is unchecked. The `model_dump(exclude_unset=True)` call in `profile_update()` will then omit `notify_sound` from the update dict, leaving the stored value unchanged instead of setting it to False.

**Fix:** Use the hidden-input override pattern in the template:

```html
<input type="hidden" name="notify_sound" value="false">
<input type="checkbox" name="notify_sound" value="true" {{ 'checked' if profile.notify_sound else '' }}>
```

FastAPI receives both values; `Form()` with a list-capable type gets both. Simpler: just read the raw form data in `profile_update()` for this field: `notify_sound_raw = (await request.form()).get("notify_sound")` and convert `"true"` -> `True`, anything else -> `False`. But this bypasses Pydantic validation.

Cleanest approach: keep the `Annotated[Optional[str], Form()]` type for `notify_sound`, coerce `"true"` -> `True` / anything else -> `False` explicitly in the handler body before passing to `ProfileUpdateRequest`. Always include `notify_sound` in `raw` dict (never skip it), so `exclude_unset=True` always includes it and the DB value is always updated on every profile save.

---

## Build Order (Recommended Phases)

The features have a strict dependency chain. Phases must be executed in order.

### Phase 1 — Diagnose and Fix SSE Watcher (prerequisite)

**Files:** `app/feed/manager.py`

Add defensive error handling around the Jinja2 render call. Add debug logging for each broadcast. Optionally add a test that inserts via the UDP path and asserts the change stream watcher does not die.

Do not build any new UI until this is confirmed working. Rationale: badge and tone are meaningless if the SSE event never arrives.

### Phase 2 — Add notify_sound to User Model and Schemas

**Files:** `app/auth/models.py`, `app/profile/schemas.py`

Add the field. Run existing profile API tests (`test_profile_api.py`) to confirm no regressions. No migration needed — Beanie defaults handle existing documents.

### Phase 3 — Wire notify_sound into log_view Context

**Files:** `app/qso/ui_router.py`, `templates/log/log.html`

Change `log_view()` dependency. Pass `notify_sound` to template. Emit `NOTIFY_SOUND` JS constant. At this point the constant is always `false` for all users (field defaults to False), which is correct.

### Phase 4 — Badge Counter

**Files:** `templates/log/log_table.html`, `templates/log/log.html`

Add badge HTML. Add `qsoCounter` JS, `updateBadge()`, `dismissBadge()`. Modify `htmx:sseMessage` handler. Add `htmx:afterSettle` handler.

### Phase 5 — Web Audio Tone

**Files:** `templates/log/log.html`

Add `initAudio()`, `playTone()`. Add gesture listeners. Wire into `htmx:sseMessage` handler behind `NOTIFY_SOUND` guard. No server changes.

### Phase 6 — Profile Toggle UI

**Files:** `app/qso/ui_router.py`, `app/profile/schemas.py`, `templates/log/profile.html`

Add `notify_sound` form parameter to `profile_update()`. Add checkbox to profile form. Handle the checkbox encoding correctly (hidden input + explicit coercion). Test that toggling on/off persists correctly and is reflected in `NOTIFY_SOUND` on the next page load.

---

## What Does NOT Change

- SSE event name (`new_qso`) — no changes to event shape or name.
- `sse-connect="/feed/station"` endpoint — unchanged.
- `#auto-refresh-ok` sentinel conditions — no new server-side conditions.
- `ConnectionManager` broadcast model — no per-operator filtering. Operator isolation is enforced by the JWT on the `/log/view` re-fetch, not at the broadcast level.
- `feed_row.html` template — not used by badge or tone features.
- MongoDB QSO schema — unchanged.
- No new collections, no new API endpoints, no new Python modules.

---

## Risk Flags

**AudioContext autoplay policy:** Chrome and Firefox require a user gesture before `AudioContext` creation succeeds. The `{ once: true }` listener approach is correct. If the SSE event arrives before any gesture (operator leaves the page open after login without clicking), `playTone()` silently no-ops because `audioCtx` is null. This is acceptable behavior — tone starts working after the first interaction.

**Badge re-application after HTMX swap:** `htmx:afterSettle` fires synchronously after DOM insertion, before the next paint. The `updateBadge()` call in the afterSettle handler will find the fresh badge element and apply `qsoCounter`. No race condition. Verify this handles the case where `qsoCounter === 0` correctly (badge stays hidden on page 1 auto-refresh reloads).

**notify_sound checkbox form encoding:** The hidden-input override pattern is standard HTML and works correctly with FastAPI Form(). The key invariant: `notify_sound` must always be present in the `raw` dict passed to `ProfileUpdateRequest`, even when the checkbox is unchecked, so that `$set` always writes the current value to MongoDB. If it is ever absent from `exclude_unset=True` output, a user who unchecks the box will see no change on next page load — a silent bug.

**SSE watcher task death on unhandled exception:** After the Phase 1 fix, any exception in the render path logs and continues. Any exception outside the inner loop (e.g., from the `collection.watch()` call) already reconnects via `PyMongoError` catch. After the fix, the only remaining risk is `asyncio.CancelledError` being re-raised by `continue` inside the cancel handler — ensure `except asyncio.CancelledError: break` comes before `except Exception`.

**HTMX ajax() after SSE-triggered reload resets scroll position:** The `htmx.ajax()` call swaps `#log-table` innerHTML, which may cause a scroll jump. This is existing behavior from v1.6, not a v2.4 regression. The badge feature on page 2+ explicitly avoids triggering `htmx.ajax()`, which is the correct mitigation.
