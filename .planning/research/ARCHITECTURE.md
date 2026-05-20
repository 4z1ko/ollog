# Architecture Patterns: v2.7 UTC Date/Time Entry

**Domain:** HTMX + FastAPI form enhancements — live UTC clock, lock/unlock toggles, HHMMSS precision, post-submit reset behavior
**Researched:** 2026-04-24
**Based on:** Direct code analysis of app/qso/models.py, service.py, router.py, ui_router.py, app/main.py, templates/log/form.html

---

## Existing Architecture Reference Points

Before describing changes, these are the load-bearing facts from the current codebase:

**Form submission path:**
`templates/log/form.html` → HTMX `hx-post="/log/qsos"` → `ui_router.submit_qso()` → `service.build_qso_dict()` → `service.parse_adif_datetime()` → `QSO(**qso_dict).insert()`

**HTMX swap target:** `hx-target="#qso-result"` with `hx-swap="innerHTML"`. The form itself (`#qso-form`) is NOT the swap target — it is a sibling of `#qso-result`. Post-submit, the form persists in the DOM unchanged; only `#qso-result` is replaced with the `qso_result.html` partial.

**Post-submit JS hook:** `document.body.addEventListener('htmx:afterSwap', ...)` checks `e.detail.target.id === 'qso-result'`, looks for `.success-msg`, then calls `form.reset()` and focuses CALL. This is the only post-submit JS behavior currently.

**TIME_ON storage:** Stored verbatim as a string in `model_extra` (via `extra="allow"`). `parse_adif_datetime()` already handles both HHMM (4-char) and HHMMSS (6-char). The ADIF string in `model_extra["TIME_ON"]` is what gets exported; `qso_date_utc` (datetime) is the indexed/queryable form.

**Validation:**
- JS-side (`form.html`): `TIME_ON` validated with `/^\d{4}$/.test()` — currently only 4-digit HHMM accepted
- Service-side (`parse_adif_datetime()`): raises `ValueError` for anything that is not 4 or 6 chars

---

## Component Boundaries

| Component | Responsibility | What Changes in v2.7 |
|-----------|---------------|----------------------|
| `templates/log/form.html` | Form markup + inline JS | All of it — lock icons, live clock, toggle, JS rewrite |
| `app/qso/service.py` — `parse_adif_datetime()` | Parses HHMM or HHMMSS into datetime | No change needed; already handles HHMMSS |
| `app/qso/ui_router.py` — `submit_qso()` | Accepts TIME_ON form field, calls build_qso_dict | No change needed; handler is agnostic to string length |
| `app/qso/ui_router.py` — `form_page()` | GET `/log/` renders form.html | No change needed |
| `app/main.py` — `lifespan()` | Runs startup migrations | Add `normalize_time_on()` alongside `backfill_created_at()` |
| `app/qso/models.py` | QSO Beanie document | No change — TIME_ON stored as string via model_extra |

---

## Question-by-Question Integration Analysis

### Q1: Where does HHMM to HHMMSS normalization live?

**Answer: JS before submit only. Service layer is already correct.**

`parse_adif_datetime()` already accepts HHMM and HHMMSS correctly. The service layer requires no change.

The JS layer currently validates TIME_ON with `/^\d{4}$/.test()`. This rule must change to accept HHMMSS too. The correct approach:

- When locked: the live clock provides HHMMSS directly — no normalization needed.
- When unlocked and user types 4 chars (HHMM): JS pads to HHMM + "00" before HTMX fires the request. This keeps the submitted value always 6 chars.
- When unlocked and user types 6 chars: submitted as-is.

Padding happens in the `htmx:beforeRequest` handler, which already intercepts submission for validation. The same handler reads the input value, pads if 4 chars, writes it back, then allows the request. This is the natural integration point.

The server-side `parse_adif_datetime()` is unchanged and handles both lengths.

### Q2: Where does TIME_ON format validation live?

**Answer: Two-layer — JS (UX gate) and service (correctness guarantee). JS must be updated; service is already correct.**

Current JS validation: `/^\d{4}$/.test(v.trim())` — accepts only 4-digit HHMM.

Required change: Accept 4-digit HHMM (normalizes to HHMM00 on submit) or 6-digit HHMMSS. Regex: `/^\d{4}(\d{2})?$/`. Additionally validate hour 00-23, minutes 00-59, seconds 00-59 — a pure digit-length check allows "9999" which is invalid ADIF.

For the live-clock locked state, the JS populates the field programmatically, so validation rules primarily apply to unlocked/manual entry.

Server-side (`parse_adif_datetime()`): already raises ValueError for invalid lengths. Hour/minute/second range is enforced by `datetime.strptime("%H%M%S")` which raises ValueError on out-of-range values. No change needed.

The UI router's `submit_qso()` currently does not catch ValueError from `build_qso_dict()`. If an invalid time reaches the server, it raises an unhandled 500. This is existing behavior and acceptable — JS validation is the user-facing gate.

### Q3: How does the HTMX form receive its post-submit state?

**Answer: Pure client. JS reads localStorage at htmx:afterSwap time. No server involvement.**

Two approaches exist:

**Option A: Data attribute on result partial**

Server renders `qso_result.html` with a `data-reset-mode` attribute reflecting the submitted hidden field value. JS reads the attribute in `htmx:afterSwap`.

**Option B (recommended): Pure client**

JS reads `localStorage.getItem('qso_reset_mode')` in the `htmx:afterSwap` handler. The toggle state has no server representation. This is simpler and requires zero server changes.

**Recommendation: Option B.** The toggle is a UI preference with no data implications. localStorage is appropriate. The `htmx:afterSwap` handler already runs after the swap; reading localStorage there is direct and requires no changes to `submit_qso()`, `form_page()`, or `qso_result.html`.

### Q4: Where does the migration live?

**Answer: `app/main.py` lifespan, as a new `normalize_time_on()` function, following the `backfill_created_at()` pattern exactly.**

The existing `backfill_created_at()` in `main.py` is the correct template:
1. Query for documents matching the old format
2. Build a `bulk_write` ops list with `UpdateOne`
3. Execute with `ordered=False`
4. Log count updated vs already-up-to-date

For TIME_ON normalization the implementation structure is:

```python
async def normalize_time_on():
    """One-time idempotent migration: normalize HHMM TIME_ON values to HHMM00."""
    collection = QSO.get_pymongo_collection()
    # Only documents where TIME_ON exists and is exactly 4 chars
    cursor = collection.find(
        {"TIME_ON": {"$exists": True, "$regex": "^\\d{4}$"}},
        {"_id": 1, "TIME_ON": 1},
    )
    ops = []
    async for doc in cursor:
        ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": {"TIME_ON": doc["TIME_ON"] + "00"}}))
    if ops:
        result = await collection.bulk_write(ops, ordered=False)
        logger.info("TIME_ON normalization: %d documents updated", result.modified_count)
    else:
        logger.info("TIME_ON normalization: 0 documents — already up to date")
```

**Idempotency:** The `$regex: "^\\d{4}$"` filter only matches 4-digit values. After migration, all records are 6-digit and the filter returns nothing. Re-running is safe and produces a 0-documents log line.

**Lifespan registration:** Add `await normalize_time_on()` immediately after `await backfill_created_at()` in the lifespan context manager.

**Imports:** `UpdateOne` is already imported in `main.py`.

### Q5: How does the JS live clock interact with the HTMX swap?

**Answer: The clock script survives the swap because the form itself is NOT the swap target. No re-initialization is needed.**

This is the critical architectural fact: `hx-target="#qso-result"` and `hx-swap="innerHTML"`. The form (`#qso-form`) and its containing card are not inside `#qso-result`. The HTMX swap replaces only the sibling `#qso-result` div.

Therefore:
- The `<script>` block at the bottom of `form.html` executes once on page load
- The form DOM persists across submissions — the clock `setInterval` is never destroyed
- The lock/unlock toggle state is never lost due to a swap

The only swap-related concern is the `htmx:afterSwap` listener on `document.body`, which is already present in `form.html` and already stable across swaps.

**One edge case:** If the form page is navigated away from and back via the sidebar (full page load), the script re-initializes naturally on load. This is correct behavior — the clock starts fresh.

**One required behavior:** When reset mode is "reset" and `form.reset()` is called, the date and time fields revert to their HTML default (empty). The `htmx:afterSwap` handler must immediately call the initialization function again to re-populate them with current UTC and re-apply `readonly`. Failing to do this leaves the user with blank date/time fields until the next clock tick (up to 1 second gap).

Solution: Extract date/time initialization into a named `initDateTime()` function called both at page load and in the "reset" branch of `htmx:afterSwap`.

### Q6: Post-submit toggle persistence: localStorage vs user profile (server)?

**Answer: localStorage only.**

Rationale:
- The toggle controls a UI behavior preference, not logbook data
- No other feature or page needs to know this preference
- Server-side storage requires a User model field, a ProfileUpdateRequest addition, a schema migration consideration, and profile API changes — significant cost for a display preference
- The existing `notify_sound` preference (v2.4 Phase 45) is a profile field because it affects SSE-side behavior (sound plays on new_qso events server-side determination). The reset toggle has no server-side behavior component at all
- localStorage is already used in this codebase for dark mode persistence

**localStorage key:** `qso_reset_mode` with values `"reset"` (default) and `"keep"`.

---

## Data Flow: New vs Changed

### Date Field (QSO_DATE)

**New behavior:** Field starts readonly, populated with today's UTC date (YYYYMMDD) via JS on load. Lock icon renders as locked. Clicking lock icon removes `readonly`, switches icon to unlocked, allows manual entry.

**Data flow unchanged:** Submit path is identical. QSO_DATE string passes through form POST to `submit_qso()` to `build_qso_dict()` to `parse_adif_datetime()`. No service changes.

**JS integration point:** Named `initDateTime()` function — populate `input[name="QSO_DATE"]` with today's UTC date via `new Date()` UTC methods. Set `readonly`.

### Time Field (TIME_ON)

**New behavior:** Field starts readonly, updated every second via `setInterval` with current UTC HHMMSS. Lock icon renders as locked. Clicking lock icon stops the interval, removes `readonly`, allows manual entry.

**Data flow change:** `htmx:beforeRequest` handler pads 4-digit values to 6-digit before submit. Service is unchanged.

**Validation change:** JS rule for TIME_ON changes to accept both HHMM and HHMMSS. Best form: `/^\d{4}(\d{2})?$/` with additional range check on hours 00-23, minutes 00-59, seconds 00-59.

### Post-Submit Reset Toggle

**New behavior:** Toggle button (two states: "Reset to live UTC" / "Keep current") stored in localStorage. Read by `htmx:afterSwap` handler.

**Data flow:** No server involvement. Pure JS state machine.

---

## Architecture Diagram

```
page load
│
├── IIFE executes
│   ├── initDateTime()
│   │   ├── populate QSO_DATE (today UTC, set readonly)
│   │   └── populate TIME_ON (now UTC HHMMSS, set readonly, start setInterval)
│   ├── read localStorage('qso_reset_mode') → render toggle state
│   └── wire lock icon click handlers
│
│         [user clicks date lock icon]
│         └── dateLocked = false, input.removeAttribute('readonly'), switch icon
│
│         [user clicks time lock icon]
│         ├── timeLocked = false, clearInterval(clockInterval)
│         ├── input.removeAttribute('readonly'), switch icon
│         └── (clock stops updating)
│
│         [user types in unlocked TIME_ON]
│         └── live re-validation (updated rules accept HHMM and HHMMSS)
│
│         [user clicks submit]
│         ├── htmx:beforeRequest fires
│         ├── validate() — updated rules + HHMMSS support
│         ├── if TIME_ON.length === 4: TIME_ON.value += "00"  [normalize]
│         └── HTMX fires POST /log/qsos with 6-char TIME_ON
│
│                   [server: submit_qso() in ui_router.py]
│                   ├── build_qso_dict() — unchanged
│                   ├── parse_adif_datetime() — unchanged, handles 6-char
│                   └── returns qso_result.html partial (HTTP 200)
│
│         [HTMX swaps #qso-result innerHTML]
│         [form DOM unchanged — clock still running if still locked]
│
│         [htmx:afterSwap fires on document.body]
│         ├── check #qso-result for .success-msg
│         ├── read localStorage('qso_reset_mode')
│         ├── if "reset":
│         │   ├── form.reset()
│         │   ├── clearErrors()
│         │   ├── submitAttempted = false
│         │   ├── initDateTime()  <-- re-lock + re-populate + restart clock
│         │   └── focus CALL
│         └── if "keep":
│             └── focus CALL only (values and lock states preserved)
```

---

## Build Order

This ordering respects dependencies between components:

**Step 1: DB migration (main.py)**

Add `normalize_time_on()` function and call from lifespan after `backfill_created_at()`. Write the test for idempotency. This must land before any HHMMSS values are stored, so existing data is clean when the new JS starts producing 6-char strings.

**Step 2: Confirm service layer — no changes needed**

`parse_adif_datetime()` already handles HHMMSS. Verify existing tests still pass. No code change.

**Step 3: JS validation rule update in form.html**

Change TIME_ON validation regex from `/^\d{4}$/` to `/^\d{4}(\d{2})?$/`. Add range validation. This is non-breaking: existing HHMM input still valid.

**Step 4: Live clock + lock/unlock mechanism in form.html**

Add `setInterval` clock for TIME_ON, lock icon markup, date field readonly with today's UTC on load. Extract `initDateTime()` named function. This is the bulk of the template work. No backend changes.

**Step 5: HHMM to HHMMSS normalization in htmx:beforeRequest**

Pad TIME_ON to 6 chars in the submit handler. One-line addition inside the existing handler. Step 3 must be complete first so the 4-digit input passes validation before it is padded.

**Step 6: Post-submit reset toggle**

Add toggle button markup. Wire to localStorage. Update `htmx:afterSwap` handler to branch on stored value. In "reset" branch, call `initDateTime()` after `form.reset()` to re-populate date/time and restart clock. Step 4 must be complete first because the "reset" branch depends on `initDateTime()` existing.

**Why this order:**
- Migration first — idempotent, no frontend dependency, ensures data consistency from day one
- Validation update before normalization — a 4-digit input must pass the relaxed rule before the normalization code runs
- Clock/lock before toggle — toggle's "reset" branch calls `initDateTime()` which is built in Step 4
- Steps 3 and 4 are internally independent and can be done in parallel if desired

---

## Modified vs New Components

### Modified

| File | Nature of Change |
|------|-----------------|
| `templates/log/form.html` | Major rewrite of inline `<script>` block; QSO_DATE and TIME_ON input markup gains adjacent lock icon buttons |
| `app/main.py` | Add `normalize_time_on()` async function (~15 lines); add one `await` call in lifespan after `backfill_created_at()` |

### New

None. All features fit in existing files.

### Unchanged

| File | Why Unchanged |
|------|--------------|
| `app/qso/service.py` | `parse_adif_datetime()` already handles HHMMSS; `build_qso_dict()` is string-agnostic |
| `app/qso/ui_router.py` — `submit_qso()` | TIME_ON is accepted as a bare string; 6-char value works identically to 4-char |
| `app/qso/ui_router.py` — `form_page()` | No new context needed; toggle preference is client-side |
| `app/qso/models.py` | TIME_ON stored in `model_extra` as string; no schema declaration needed |
| `app/qso/router.py` | REST API already documents HHMM or HHMMSS in TIME_ON field description |
| `templates/log/qso_result.html` | No server-side context changes for reset preference |

---

## Anti-Patterns to Avoid

### Using `disabled` instead of `readonly` for locked fields

The milestone spec explicitly calls for `readonly` (not `disabled`). Disabled fields are excluded from form submission — the date and time values would not be sent to the server. `readonly` fields submit normally. This is a hard requirement.

### Putting the lock icon inside a label wrapping the input

The lock icon click must toggle `readonly` on the input and switch icon state. If the icon is inside a `<label>` wrapping the input, clicking the icon also focuses/clicks the input. Use an adjacent button element, not a label wrapper.

### Calling `form.reset()` without immediately calling `initDateTime()`

`form.reset()` clears all field values to their HTML defaults (empty strings for text inputs). After reset, the date and time fields are empty until JS re-populates them. The `htmx:afterSwap` handler must call `form.reset()` first, then immediately call `initDateTime()` to re-populate QSO_DATE and TIME_ON with current UTC values and re-apply `readonly`. Failing this leaves blank date/time fields for up to one clock tick.

### Re-implementing date/time math in JS with local time

`new Date().toISOString()` returns UTC. For YYYYMMDD: `toISOString().slice(0,10).replace(/-/g,'')`. For HHMMSS: use `getUTCHours()`, `getUTCMinutes()`, `getUTCSeconds()` and zero-pad each with `.toString().padStart(2,'0')`. Do not use `toLocaleTimeString()` — it returns local time, not UTC.

### Storing clock state in a nested closure that htmx:afterSwap cannot reach

The `htmx:afterSwap` handler needs to call `initDateTime()` and reference `clockInterval` and lock state variables. These must be declared at the IIFE top level, visible to all inner functions. The existing IIFE pattern in `form.html` declares `form`, `submitAttempted` at the top; clock state must follow the same pattern.

### Server-side persistence for the reset toggle

Adding a User model field for the reset mode preference would require: model field addition, ProfileUpdateRequest update, profile API change, and an index or migration consideration. The feature has no server-side behavior component — only the `htmx:afterSwap` JS handler reads the preference. localStorage is correct. Follow the dark mode persistence precedent already in the codebase.

---

## Patterns Established by Existing Code

### Pattern: Startup migration via lifespan (established by `backfill_created_at`)

**What:** Async function added to `main.py` at module level. Called from lifespan before `yield`. Uses `QSO.get_pymongo_collection()` for raw MongoDB access. `bulk_write` with `ordered=False`. Logs count updated vs already-up-to-date. Idempotent by using a filter that only matches pre-migration documents.

**Apply for TIME_ON:** Exactly the same structure. Filter: `{"TIME_ON": {"$regex": "^\\d{4}$"}}`. Update: append "00" to value.

### Pattern: Form persists across HTMX swap (established by existing form)

**What:** The QSO entry form uses `hx-target="#qso-result"` pointing to a sibling div. The form is not inside the swap target. Post-submit JS on `document.body` (`htmx:afterSwap`) checks the target ID before acting. This pattern means the form, its JS, and any `setInterval` timers survive every submission.

**Apply for clock:** `setInterval` started at page load survives indefinitely. No re-initialization hook is needed for the clock itself. Re-initialization is only needed for field values after `form.reset()`.

### Pattern: `htmx:afterSwap` on `document.body` for post-submit behavior

**What:** `document.body.addEventListener('htmx:afterSwap', fn)`. `fn` checks `e.detail.target.id === 'qso-result'` to scope the handler to QSO form submissions only. Currently resets the form and focuses CALL.

**Apply for toggle:** Read localStorage in the same handler. Branch on stored value. Add `initDateTime()` call in the reset branch. The existing guard (`target.id === 'qso-result'`) ensures the clock is not disturbed by other HTMX swaps on the page.

---

## Sources

- Direct code reading: `app/qso/models.py`, `app/qso/service.py`, `app/qso/router.py`, `app/qso/ui_router.py`, `app/main.py`, `templates/log/form.html` — HIGH confidence
- Existing migration pattern (`backfill_created_at` in `main.py`) — HIGH confidence, direct code
- HTMX swap target behavior (form survives swap because `#qso-result` is the target, not `#qso-form`) — HIGH confidence, verified against template markup
- ADIF spec TIME_ON format (HHMM or HHMMSS) — confirmed in `parse_adif_datetime()` docstring and `QSOCreateRequest.TIME_ON` field description

---
*Architecture research for: v2.7 UTC Date/Time Entry integration*
*Researched: 2026-04-24*
