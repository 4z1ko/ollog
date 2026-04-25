# Domain Pitfalls

**Domain:** UTC Date/Time Entry Enhancements — live lock/unlock toggles, HHMMSS precision, post-submit reset — adding to existing HTMX + FastAPI + Beanie/MongoDB logbook
**Researched:** 2026-04-24
**Milestone:** v2.7 UTC Date/Time Entry
**Overall confidence:** HIGH — all pitfalls grounded in live codebase inspection (`form.html`, `service.py`) + browser/HTML/HTMX specs

---

## Critical Pitfalls

Mistakes that cause data loss, silent wrong values, or complete feature failure.

---

### Pitfall 1: HTMX Swap Scope — The Form Is NOT the Swap Target (Must Stay That Way)

**What goes wrong:** Developer moves `hx-target` or `hx-swap` so the form itself gets replaced after submit. All JS event listeners, `setInterval` clock timers, lock state, and the `submitAttempted` flag on the old DOM node are silently destroyed. New form node has no wiring. Live clock stops. Lock toggle stops. Validation breaks.

**Why it happens:** The reflex to "show success state in the form" leads to swapping the form container rather than a separate result area.

**This project's actual wiring (form.html lines 24-28):**
```html
<form id="qso-form"
      hx-post="/log/qsos"
      hx-target="#qso-result"   <!-- only this div is replaced -->
      hx-swap="innerHTML">
```
```html
<div id="qso-result"></div>     <!-- sibling of form, not parent/child -->
```

The form is never replaced. The IIFE event listeners survive every submit. This is the correct architecture — preserve it.

**Consequences if broken:**
- Live clock stops after first submit (interval running on detached node, updating nothing)
- Lock toggle stops responding (listener on detached node)
- `submitAttempted = false` never resets correctly
- Validation error highlights persist forever or never appear

**Prevention:**
- Keep `hx-target="#qso-result"` and `hx-swap="innerHTML"` — do not change the swap target to the form, the `.card-body`, or any ancestor of `#qso-form`.
- Post-submit behavior (reset, keep state) belongs in the `htmx:afterSwap` handler already present in the IIFE (form.html line 245), not in a swap that replaces the form.
- If a future requirement forces form-level swapping, the re-initialization pattern is: `document.body.addEventListener('htmx:afterSettle', function(e) { if (e.detail.target.id === 'qso-form') initForm(); })` — bind to `document.body`, check the target ID, re-run the IIFE body as a named function.

**Detection:** After a successful submit, click the lock toggle. If nothing happens, the form was swapped.

---

### Pitfall 2: `disabled` vs `readonly` — Silent Value Drops on Locked Fields

**What goes wrong:** The date/time input is given `disabled` to prevent editing while locked. It renders grayed-out and non-interactive — looks correct to the eye. But HTML spec: `disabled` form controls are excluded from `FormData` serialization. HTMX uses `FormData` — it obeys the same rule. The `QSO_DATE` and `TIME_ON` values are silently absent from the POST body. The server receives missing required fields and returns a validation error (or worse, accepts a QSO with empty date/time if validation is insufficiently strict).

**The rule:**
- `readonly` — field is non-editable by the user; value IS submitted with the form. Use this for locked fields.
- `disabled` — field is excluded from submission entirely. Use only for controls that should contribute no value (decorative buttons, intentionally cleared optional fields).

**Prevention:**
```html
<!-- WRONG: value not submitted -->
<input type="text" name="QSO_DATE" disabled class="form-input ...">

<!-- CORRECT: non-editable but value submits -->
<input type="text" name="QSO_DATE" readonly class="form-input ...">
```

Toggle lock state via the `readonly` property in JS, never `disabled`:
```javascript
// Lock — user cannot edit, clock can still write, value still submits
dateInput.readOnly = true;

// Unlock — user can edit freely
dateInput.readOnly = false;
```

The clock update code must use `.value =` to write into the `readonly` input — JS can write to a `readonly` input's `.value` property programmatically even when the user cannot type into it. This is correct behavior.

**Detection:** In DevTools Network tab, submit the form with a locked date. Inspect the request payload (Form Data section). If `QSO_DATE` is absent, the field is `disabled` not `readonly`.

---

### Pitfall 3: `setInterval` Clock Drift — Accumulating Error

**What goes wrong:** `setInterval(updateClock, 1000)` fires approximately every 1000ms, but each callback takes non-zero time. The interval does not self-correct. Over a 4-hour FT8 session (typical overnight contest), the display can drift 2-5 seconds behind actual UTC. For FT8 QSOs (15-second transmission cycles), even a 2-second displayed lag causes operators to log at the wrong second and creates confusion about whether the displayed time matches the stored time.

**Why it happens:** `setInterval` schedules the next tick relative to the previous tick's schedule time — it does not account for callback execution time or browser scheduling jitter.

**The correct pattern — derive from wall clock on every tick, never accumulate:**
```javascript
function updateClock(timeInput) {
  var now = new Date();
  var hh = String(now.getUTCHours()).padStart(2, '0');
  var mm = String(now.getUTCMinutes()).padStart(2, '0');
  var ss = String(now.getUTCSeconds()).padStart(2, '0');
  timeInput.value = hh + mm + ss;  // HHMMSS
}

// Align first tick to next second boundary to reduce initial display lag
var clockTimer = null;
function startClock(timeInput) {
  if (clockTimer) clearInterval(clockTimer);
  var msUntilNextSecond = 1000 - (Date.now() % 1000);
  setTimeout(function() {
    updateClock(timeInput);
    clockTimer = setInterval(function() { updateClock(timeInput); }, 1000);
  }, msUntilNextSecond);
}

function stopClock() {
  clearInterval(clockTimer);
  clockTimer = null;
}
```

This pattern:
1. Always calls `new Date()` inside the tick — drift cannot accumulate because each tick reads the current wall clock, not a counter
2. Aligns the first tick to the next whole-second boundary — displayed seconds track the system clock within ~1 tick's worth of jitter (~16ms)

**Prevention:**
- Never use a counter or accumulate time deltas. Always call `new Date()` inside the tick.
- Store the `setInterval` handle in the IIFE scope as `clockTimer = null`. Clear it in `stopClock()`, on form reset, and on lock-off.

---

### Pitfall 4: Browser Timezone Leakage — `new Date()` Returns Local Time

**What goes wrong:** `new Date().getHours()` returns local hours. An operator in UTC+5 logging at 14:30 local time has the clock display "1430" as the UTC time, but actual UTC is "0930". The QSO is stored with a 5-hour error in `TIME_ON`. The derived `qso_date_utc` field is then also wrong. Duplicate detection, which uses `qso_date_utc` for the ±2-minute window, may fail to catch real duplicates or falsely flag non-duplicates.

**Why it happens:** JS `Date` methods without `UTC` in their name (`.getHours()`, `.getMinutes()`, `.getDate()`, `.getMonth()`, `.getFullYear()`) all return values in the browser's local timezone. This is the JS default; UTC variants are opt-in.

**Every UTC access must use the `UTC` variants:**
```javascript
// WRONG — returns local time
var h = now.getHours();
var m = now.getMinutes();
var d = now.getDate();
var y = now.getFullYear();

// CORRECT — always UTC regardless of browser timezone
var h = now.getUTCHours();
var m = now.getUTCMinutes();
var d = now.getUTCDate();
var y = now.getUTCFullYear();
```

**For QSO_DATE (YYYYMMDD):**
```javascript
function utcDateString(now) {
  var y  = now.getUTCFullYear();
  var mo = String(now.getUTCMonth() + 1).padStart(2, '0');  // +1: months are 0-indexed
  var d  = String(now.getUTCDate()).padStart(2, '0');
  return '' + y + mo + d;
}
```

**For TIME_ON (HHMMSS):**
```javascript
function utcTimeString(now) {
  var h = String(now.getUTCHours()).padStart(2, '0');
  var m = String(now.getUTCMinutes()).padStart(2, '0');
  var s = String(now.getUTCSeconds()).padStart(2, '0');
  return h + m + s;
}
```

**Prevention:**
- Code review rule: grep the template for `\.getHours\b\|\.getMinutes\b\|\.getDate\b\|\.getFullYear\b\|\.getMonth\b` (without `UTC`) — any hit is a bug.
- Never use `.toLocaleDateString()`, `.toLocaleTimeString()`, or `.toLocalString()` — all are locale-formatted and timezone-adjusted.

**Detection:** Test from a browser with the OS timezone set to UTC+8 or UTC-5. If the displayed clock matches local wall-clock time instead of UTC, the bug is present.

---

### Pitfall 5: MongoDB HHMM → HHMMSS Migration — Double-Padding and Field Scope

**What goes wrong:**

1. **Double-padding on re-run.** The migration is called from the FastAPI lifespan (alongside `backfill_created_at()`), so it runs on every restart. If the filter regex matches 6-digit strings (e.g., `\d{4,}` or `\d+`), already-migrated `"143000"` records get padded to `"14300000"`. The ADIF spec does not define 8-character TIME_ON — the value becomes invalid.

2. **Scope too broad.** A bulk update that filters on any 4-digit string could theoretically match numeric ADIF `model_extra` fields other than `TIME_ON` if the `$match` filter is applied without specifying the `TIME_ON` field name. This would corrupt unrelated 4-digit ADIF fields.

3. **pymongo aggregation pipeline syntax required.** The `$concat` operator needs to reference the existing field value (`"$TIME_ON"`). This requires MongoDB 4.2+ aggregation pipeline update syntax — the `update_many(filter, [pipeline])` list form. The standard `update_many(filter, {"$set": {"TIME_ON": "0000"}})` dict form cannot reference the existing value.

**The correct idempotent migration pattern:**
```python
async def migrate_time_on_to_hhmmss() -> int:
    """Idempotent: matches only exact 4-digit TIME_ON values (HHMM).
    6-digit HHMMSS values do not match — safe to run on every restart.
    Uses aggregation pipeline update to append "00" to the existing value.
    """
    collection = QSO.get_pymongo_collection()  # not get_motor_collection() — Motor is EOL
    result = await collection.update_many(
        {"TIME_ON": {"$regex": r"^\d{4}$"}},               # exactly 4 digits, anchored
        [{"$set": {"TIME_ON": {"$concat": ["$TIME_ON", "00"]}}}],  # pipeline update
    )
    return result.modified_count
```

Key points:
- `r"^\d{4}$"` — anchored start and end. A 6-digit `HHMMSS` does not match `^\d{4}$`. Idempotent by design.
- Filter explicitly specifies `TIME_ON` field name — no other field is touched.
- `[{...}]` list syntax triggers aggregation pipeline mode; `$concat` can reference `"$TIME_ON"`.
- Uses `get_pymongo_collection()` — the correct raw-collection accessor per this codebase (CLAUDE.md Key Decisions: `get_pymongo_collection()` not `get_motor_collection()`; Motor EOL'd May 2025).

**Prevention:**
- Always anchor time-format regexes: `^\d{4}$` not `\d{4}`.
- Run the migration from lifespan startup and log `modified_count` — zero on restart means it's idempotent.
- Add a test: insert a pre-migrated `HHMMSS` record, run migration, assert it is unchanged. Insert an `HHMM` record, run migration, assert it becomes `HHMMSS`.

---

### Pitfall 6: Validation Timing — Accepting 4-Digit Input While Storing 6-Digit Values

**What goes wrong:** The current form validator (form.html line 181) accepts `TIME_ON` matching `^\d{4}$`. The v2.7 requirement stores HHMMSS (6 digits). Two bad paths:

A. Validator updated to require `^\d{6}$` only. Operators who naturally type "1430" get an immediate error. Bad UX — the server already accepts HHMM and normalizes it.

B. Validator left at `^\d{4}$`. Operators type "143000" (6 digits) and get a red error because the validator rejects 6-digit input. Can't log QSOs that already have seconds.

**The correct approach — validate both, normalize in `htmx:beforeRequest`:**

The server's `parse_adif_datetime()` already accepts both HHMM and HHMMSS (service.py lines 36-43). Client-side normalization in `htmx:beforeRequest` pads HHMM to HHMMSS before the request fires, so the stored value is always 6 digits without requiring a server change.

```javascript
// Update the validator to accept both formats:
TIME_ON: function (v) {
  return /^\d{4}$/.test(v.trim()) || /^\d{6}$/.test(v.trim());
},

// Normalize in htmx:beforeRequest (already exists in IIFE):
form.addEventListener('htmx:beforeRequest', function (e) {
  submitAttempted = true;

  // Pad HHMM to HHMMSS before validation and submission
  var timeInput = field('TIME_ON');
  if (timeInput && /^\d{4}$/.test(timeInput.value.trim())) {
    timeInput.value = timeInput.value.trim() + '00';
  }

  if (!validate()) {
    e.preventDefault();
  }
});
```

**The wrong validation timing choices:**
- Normalizing on `blur`: operators tab quickly past the time field while the clock is updating — blur fires on a stale value, races with the clock update.
- Validating on `input` before `submitAttempted`: shows error after typing "14" of "1430" (mid-keystroke). Already handled correctly in the IIFE by the `submitAttempted` guard — preserve this pattern.
- Normalizing in a `submit` event listener: fires before `htmx:beforeRequest`, which is acceptable but inconsistent with existing interception pattern. Use `htmx:beforeRequest` for consistency.

---

### Pitfall 7: Passing JS-Computed Values to HTMX — Hidden Input vs Single Visible `readonly` Input

**What goes wrong:** Two approaches exist for submitting a clock-driven time value: a hidden input that the visible display reads from, or a visible `readonly` input that the clock updates directly. Each has failure modes.

**Hidden input failure modes:**
- If both a visible `<input name="TIME_ON">` and a hidden `<input name="TIME_ON">` exist in the DOM simultaneously, `FormData` serializes both. Servers typically use the last value. If the order is wrong, the wrong value is submitted.
- Keeping display and hidden input in sync requires updating two elements on every clock tick — easy to miss one.

**`hx-vals` failure modes:**
- `hx-vals='js:{"TIME_ON": document.getElementById("time-on").value}'` overrides the form's TIME_ON value at request time. Works, but evaluated in global scope — breaks under strict CSP `script-src` policies that block eval.
- Bypasses normal form serialization, making the data flow harder to reason about and test.

**The correct approach — single visible `readonly` input:**
```html
<input type="text" name="TIME_ON" id="time-on"
       readonly
       class="form-input font-mono"
       placeholder="HHMMSS">
```

```javascript
// Clock writes directly to the input value
function updateClock() {
  var now = new Date();
  timeInput.value = utcTimeString(now);  // JS can set .value on readonly inputs
}

// Lock toggle
function setLocked(isLocked) {
  timeInput.readOnly = isLocked;
  if (isLocked) {
    startClock(timeInput);
  } else {
    stopClock();
  }
}
```

This is the cleanest approach: one element, no sync problem, no duplicate name problem, no CSP concern, no `hx-vals` complexity. `readonly` inputs are submitted by HTMX/FormData. JS can write to `.value` programmatically even when `readOnly = true`.

---

## Moderate Pitfalls

---

### Pitfall 8: Month Off-by-One — `getUTCMonth()` Is 0-Indexed

**What goes wrong:** `new Date().getUTCMonth()` returns 0 for January, 11 for December. Forgetting the `+1` produces dates like `"20260324"` where month field `03` represents April (month 4). A QSO logged in April is stored as March. The compound duplicate-detection index uses `qso_date_utc` — a wrong date may miss real duplicates or create phantom duplicates.

**Prevention:**
```javascript
var month = String(now.getUTCMonth() + 1).padStart(2, '0');  // +1 always
```

Code review rule: grep for `getUTCMonth()` without `+ 1` — any hit is a bug.

---

### Pitfall 9: Post-Submit `form.reset()` Clears Auto-Populated Date/Time Fields

**What goes wrong:** The current IIFE calls `form.reset()` on successful submit (form.html line 249). Browser `form.reset()` restores each field to its `defaultValue` (the `value=""` attribute from HTML at parse time). Date/time inputs that were set by the clock JS have no `value=""` in HTML — they reset to empty string. The live clock would need to immediately re-populate them.

The v2.7 requirement adds a post-submit toggle: "Keep current date/time" vs "Reset to live UTC." The `form.reset()` call must become conditional.

**The correct conditional reset pattern:**
```javascript
// In the htmx:afterSwap success handler (form.html line 245 area):
var result = document.getElementById('qso-result');
if (result && result.querySelector('.success-msg')) {
  if (keepDateTimeCheckbox && keepDateTimeCheckbox.checked) {
    // Selective reset — clear contact fields, preserve date/time and lock state
    field('CALL').value = '';
    field('RST_SENT').value = '';
    field('RST_RCVD').value = '';
    field('FREQ').value = '';
    // Date, time, band, mode preserved
  } else {
    // Full reset — re-populate date/time immediately after
    form.reset();
    clearErrors();
    submitAttempted = false;
    // Re-populate date/time with current UTC
    field('QSO_DATE').value = utcDateString(new Date());
    if (timeLocked) {
      field('TIME_ON').value = utcTimeString(new Date());
      // Clock is still running; it will keep updating
    }
  }
  var callField = field('CALL');
  if (callField) callField.focus();
}
```

**Prevention:** Never call `form.reset()` unconditionally in a form with auto-populated fields. After any reset, synchronously re-populate the live fields from the clock before returning control to the user.

---

### Pitfall 10: Clock Timer Leak — `setInterval` Not Cleared on Page Navigation

**What goes wrong:** The IIFE starts `setInterval` when the page loads. If the operator navigates away, the interval continues firing against a detached DOM node. On multi-page HTMX apps with partial swaps, multiple intervals accumulate — several timers all trying to update the same element, causing visible flickering or silent no-ops on detached nodes.

**This project's risk level:** LOW-MEDIUM. `form.html` is a full-page template; HTMX nav between pages is full-page navigation. The form's `<script>` block loads only on `form.html`. Risk increases if the form is ever embedded as a partial within another page.

**Prevention:**
```javascript
var clockTimer = null;

window.addEventListener('beforeunload', function() {
  if (clockTimer) { clearInterval(clockTimer); clockTimer = null; }
});
// Also clear when lock is toggled off
```

---

### Pitfall 11: Tailwind Dark Mode Classes on Lock Icon — Purge Strips Dynamically Constructed Classes

**What goes wrong:** The lock icon has two SVG states (locked/unlocked). If Tailwind class names are constructed dynamically in JS (e.g., `el.className = 'w-4 h-4 ' + (locked ? 'text-indigo-500' : 'text-gray-400')`), Tailwind's purge scanner never sees `text-indigo-500` or `text-gray-400` as literal strings in the template — they are stripped from `output.css`. The icon renders without color.

**Prevention:** Per `CLAUDE.md` — all Tailwind classes must appear as literal strings in template files. Use two pre-declared SVG icon elements with a `hidden` class toggled between them, rather than dynamic class construction:

```html
<!-- In form.html — both elements always exist with literal Tailwind classes -->
<span id="lock-icon-locked"  class="text-indigo-500 dark:text-indigo-400"><!-- locked SVG --></span>
<span id="lock-icon-unlocked" class="hidden text-gray-400 dark:text-gray-500"><!-- unlocked SVG --></span>
```

```javascript
// Toggle with classList.add/remove — no dynamic class construction
function updateLockIcon(isLocked) {
  lockIconLocked.classList.toggle('hidden', !isLocked);
  lockIconUnlocked.classList.toggle('hidden', isLocked);
}
```

After adding new dark-mode classes, run `npm run verify` to confirm they appear in `static/css/output.css`.

---

### Pitfall 12: `htmx:afterSwap` vs `htmx:afterSettle` — When Each Is Correct

**What goes wrong:** Using `htmx:afterSwap` to trigger a CSS transition (e.g., animating the success message into view) fails because the browser has not yet rendered the new DOM when `afterSwap` fires. Using `htmx:afterSettle` for a simple DOM read (checking for `.success-msg`) is harmless but adds unnecessary latency.

**This project's existing code** (form.html line 245) uses `htmx:afterSwap` to check for `.success-msg` — this is correct since it's a DOM read, not a layout operation.

**The rule:**
- `htmx:afterSwap` — correct for: DOM reads, classList changes, focus calls, value assignments
- `htmx:afterSettle` — required for: triggering CSS transitions, reading `offsetHeight`/computed styles, anything that needs the browser to have painted

The v2.7 success handler only needs DOM reads and form resets — `htmx:afterSwap` remains correct.

---

## Minor Pitfalls

---

### Pitfall 13: Duplicate `name="TIME_ON"` Elements If Visible + Hidden Inputs Coexist

**What goes wrong:** During implementation, a developer adds a hidden `<input name="TIME_ON">` for the locked-clock value while the original visible `<input name="TIME_ON">` is still in the DOM. Both serialize into FormData. The server sees two `TIME_ON` values. FastAPI/Pydantic typically uses the last one; depending on form field ordering, this could be the stale visible value or the correct hidden value.

**Prevention:** Ensure exactly one `<input name="TIME_ON">` exists in the form DOM at any time. The recommended approach (Pitfall 7) uses a single visible `readonly` input — no hidden input is ever needed.

**Detection:** `document.querySelectorAll('[name="TIME_ON"]').length > 1` in the console after loading the form. Any result greater than 1 is a bug.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Date/time lock toggle JS | Pitfall 2 (disabled vs readonly) | Use `.readOnly` property, never `.disabled`. Verify via Network tab FormData inspection. |
| Live UTC clock | Pitfall 3 (setInterval drift) + Pitfall 4 (local timezone) | Derive from `new Date().getUTC*()` on every tick. Align to second boundary. |
| UTC date formatting | Pitfall 8 (month off-by-one) | `getUTCMonth() + 1` always. Grep check in review. |
| HHMM → HHMMSS migration | Pitfall 5 (double-pad, field scope) | `r"^\d{4}$"` anchored regex; aggregation pipeline `$concat`; `get_pymongo_collection()`; run from lifespan startup. |
| Time validation update | Pitfall 6 (4-vs-6 digit) | Validator accepts both; normalize to HHMMSS in `htmx:beforeRequest`. |
| Post-submit reset | Pitfall 9 (reset kills live fields) | Conditional reset; re-populate date/time immediately after `form.reset()`. |
| Value submission | Pitfall 7 + 13 (hx-vals, hidden input, duplicates) | Single visible `readonly` input only. No hidden `name="TIME_ON"`. No `hx-vals`. |
| HTMX swap scope | Pitfall 1 (form replaced) | Keep `hx-target="#qso-result"`, never point at form or any ancestor of `#qso-form`. |
| Tailwind lock icon | Pitfall 11 (purge) | Literal class strings only. Run `npm run verify` after adding new `dark:` classes. |
| Clock timer lifecycle | Pitfall 10 (timer leak) | Store `setInterval` handle; clear on `beforeunload` and on lock-off. |

---

## "Looks Done But Isn't" Checklist

- [ ] **readonly not disabled:** Lock toggle uses `input.readOnly = true/false`. Network tab confirms `QSO_DATE` and `TIME_ON` present in FormData when locked.
- [ ] **UTC time source:** All date/time construction uses `getUTCHours()`, `getUTCMinutes()`, `getUTCSeconds()`, `getUTCDate()`, `getUTCMonth() + 1`, `getUTCFullYear()`. Grep for bare `getHours|getMinutes|getDate|getMonth|getFullYear` — zero hits.
- [ ] **Clock drift prevention:** `updateClock()` calls `new Date()` on every tick. No counter or accumulated delta. First tick aligned to next second boundary.
- [ ] **Swap scope preserved:** `hx-target` still points at `#qso-result`. `hx-swap` still `innerHTML`. Form is never replaced.
- [ ] **Migration idempotent:** Run migration twice. `modified_count` is zero on second run. Pre-existing HHMMSS values unchanged.
- [ ] **Migration scoped:** Only `TIME_ON` field updated. No other 4-digit ADIF fields touched.
- [ ] **Validator accepts both:** Submitting with TIME_ON = "1430" succeeds. Submitting with "143000" succeeds. Submitting with "143" or "14300" fails.
- [ ] **Normalization fires:** Submit form with TIME_ON = "1430". Stored value in MongoDB is "143000" (6 digits).
- [ ] **Post-submit reset conditional:** With "Keep date/time" toggle checked: date/time fields retain values after submit. CALL field clears. With toggle unchecked: all fields clear, date/time repopulate from UTC immediately.
- [ ] **Single name="TIME_ON":** `document.querySelectorAll('[name="TIME_ON"]').length === 1` in console. Always.
- [ ] **Dark mode icon classes:** `npm run verify` passes after adding lock icon. New `dark:` classes appear in `output.css`.
- [ ] **No timezone leakage:** Test with browser timezone = UTC+8. Displayed UTC clock matches UTC, not local time.

---

## Sources

- `templates/log/form.html` — live codebase: HTMX wiring (`hx-target="#qso-result"`, `hx-swap="innerHTML"`), JS IIFE, validation rules (`^\d{4}$`), `htmx:afterSwap` success handler, `submitAttempted` guard pattern
- `app/qso/service.py` — live codebase: `parse_adif_datetime()` accepting both HHMM (4-char) and HHMMSS (6-char), `build_qso_dict()` normalization, `get_pymongo_collection()` precedent from stats page
- `.planning/PROJECT.md` — v2.7 requirements; Key Decisions (Motor EOL, `get_pymongo_collection()`, HTMX cookie auth, `NOTIFY_SOUND` string rendering pattern, `#log-table` SSE swap target pattern, `classList.add/remove` for hidden badge)
- HTML spec — disabled vs readonly form control submission behavior (HIGH confidence — browser spec, MDN)
- HTMX docs — `htmx:beforeRequest`, `htmx:afterSwap`, `htmx:afterSettle` event lifecycle; FormData serialization (HIGH confidence — used throughout this codebase; `htmx:afterSwap` for theme icon sync confirmed in CLAUDE.md Key Decisions v1.9)
- MongoDB docs — aggregation pipeline update syntax (`[{$set: ...}]` list form), `$regex` anchoring, `$concat` in aggregation (HIGH confidence — same pattern used in existing `backfill_created_at()` migration in this project)

---
*Pitfalls research for: v2.7 UTC Date/Time Entry*
*Researched: 2026-04-24*
