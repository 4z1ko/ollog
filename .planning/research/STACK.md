# Technology Stack

**Project:** ollog v2.7 UTC Date/Time Entry
**Researched:** 2026-04-24
**Scope:** Additions and changes for v2.7 features ONLY. Validated v2.6 stack is not re-listed.
**Confidence:** HIGH (all claims verified against codebase audit, official browser specs, or
existing patterns in this project)

---

## Verdict Up Front

No new dependencies for any of the five feature areas. Browser-native JS, the existing
Beanie/PyMongo migration pattern, and the existing `htmx:beforeRequest` hook cover everything.
A date/time library (Luxon, Day.js, Moment.js) would add weight without adding value.

---

## Feature 1: Live Auto-Updating UTC Clock in a Form Input

**Technology:** Vanilla JS `setInterval` + `Date` prototype UTC accessors.

```javascript
function utcTimeNow() {
  var d = new Date();
  return (
    String(d.getUTCHours()).padStart(2, '0') +
    String(d.getUTCMinutes()).padStart(2, '0') +
    String(d.getUTCSeconds()).padStart(2, '0')
  ); // HHMMSS
}

function utcDateNow() {
  var d = new Date();
  return (
    d.getUTCFullYear() +
    String(d.getUTCMonth() + 1).padStart(2, '0') +
    String(d.getUTCDate()).padStart(2, '0')
  ); // YYYYMMDD
}

// While locked:
var clockTimerId = setInterval(function () {
  timeInput.value = utcTimeNow();
  dateInput.value = utcDateNow();
}, 1000);

// On unlock:
clearInterval(clockTimerId);
clockTimerId = null;
```

`setInterval` at 1-second intervals is the correct pattern — it matches the existing live clock
concept already present elsewhere in the app (SSE event timing, etc.) and imposes no meaningful
CPU load. The existing `form.html` IIFE already has a pattern of managing `setInterval` via a
scoped closure; the clock timer follows the same model.

**Why not a date/time library?**

All required operations are: get UTC year/month/day/hour/minute/second, zero-pad each component,
concatenate. This is 6 accessor calls. Luxon weighs ~60 kB minified; Day.js ~8 kB but requires
UTC plugin import. Neither justifies the dependency for 6 lines of native JS.

`Intl.DateTimeFormat` with `timeZone: 'UTC'` and `formatToParts()` works but is more verbose
and involves string parsing of parts — less clear than direct UTC accessors for ADIF's
non-ISO formats.

**Confidence:** HIGH — browser built-ins, no version concerns.

---

## Feature 2: Lock/Unlock Toggle

**Technology:** HTML `readonly` attribute toggled via JS. Zero new dependencies.

The `readonly` vs `disabled` distinction is load-bearing:

| Attribute | Included in form submit? | HTMX serialises it? |
|-----------|--------------------------|---------------------|
| `readonly` | Yes | Yes |
| `disabled` | No | No |

Using `disabled` would silently drop QSO_DATE and TIME_ON from the HTMX POST body, causing
server-side validation failure (both fields are `required` in the form and the service layer).
Use `readonly` exclusively.

```javascript
function lockField(input) {
  input.readOnly = true;
  // add visual indicator class
}
function unlockField(input) {
  input.readOnly = false;
  clearInterval(clockTimerId);
  clockTimerId = null;
  // remove visual indicator class
}
```

**Lock icon:** Inline Heroicons SVG, `w-4 h-4` (16x16 px). Two SVG paths needed:
locked state (filled padlock) and unlocked state (open padlock). These are available in
the Heroicons set already used throughout the codebase. Toggling is done via `classList`
swap on two sibling `<svg>` elements — identical to the existing theme icon toggle pattern
in `base_app.html` (`icon-moon` / `icon-sun` swap).

**Confidence:** HIGH — HTML spec behaviour, matches existing codebase icon toggle pattern.

---

## Feature 3: HHMM to HHMMSS Normalisation

Two integration points are needed. Both are one-line changes to existing code.

### 3a. JS Pre-Submit (UI path)

The existing `htmx:beforeRequest` listener in `form.html` is already the correct hook:

```javascript
form.addEventListener('htmx:beforeRequest', function (e) {
  submitAttempted = true;
  if (!validate()) { e.preventDefault(); return; }

  // Normalise TIME_ON: HHMM → HHMM00 before HTMX serialises the form
  var t = field('TIME_ON');
  if (t && /^\d{4}$/.test(t.value.trim())) {
    t.value = t.value.trim() + '00';
  }
});
```

HTMX serialises the form body after this event fires, so the normalised value is what
the server receives. The input retains the HHMMSS value visually after the mutation.

### 3b. Server-Side (`build_qso_dict` — covers REST API + UDP)

```python
# In build_qso_dict(), after the BAND/MODE uppercase normalisation block:
if len(result.get("TIME_ON", "")) == 4:
    result["TIME_ON"] = result["TIME_ON"] + "00"
```

This makes all three ingestion paths (UI form, REST API, UDP datagram) store HHMMSS.
It runs before `parse_adif_datetime()` which already handles both lengths correctly, so
no change to the parser is needed.

**Why both?**
- JS-only: REST API callers and UDP datagrams would still store HHMM.
- Server-only: the UI input would briefly show HHMM before server normalises it (minor).
- Both: the UI always shows HHMMSS after submit, and all paths are consistent.

**Confidence:** HIGH — single-line additions to existing code paths.

---

## Feature 4: Validation Rule Update

The existing TIME_ON validator in `form.html`:

```javascript
TIME_ON: function (v) { return /^\d{4}$/.test(v.trim()); },
```

Must become:

```javascript
TIME_ON: function (v) { return /^\d{4}(\d{2})?$/.test(v.trim()); },
```

This accepts both HHMM (locked auto-clock always outputs HHMMSS; manual entry may be HHMM)
and HHMMSS. The JS pre-submit normaliser in Feature 3a appends `00` for HHMM before the
server sees it.

**Confidence:** HIGH — regex change, no dependencies.

---

## Feature 5: Idempotent DB Migration (TIME_ON HHMM → HHMM00)

**Technology:** Raw PyMongo `UpdateOne` bulk_write via `QSO.get_pymongo_collection()`.

This is the exact same pattern as the existing `backfill_created_at()` in `app/main.py`.

```python
async def backfill_time_on_hhmmss():
    """Idempotent migration: normalise TIME_ON from HHMM to HHMM00.

    Finds QSO documents where TIME_ON is exactly 4 characters (legacy HHMM format)
    and appends '00' to produce HHMMSS. Safe to re-run — 4-digit strings cannot exist
    after the first successful run.
    """
    from app.qso.models import QSO
    from pymongo import UpdateOne

    collection = QSO.get_pymongo_collection()
    cursor = collection.find(
        {"TIME_ON": {"$exists": True, "$regex": r"^\d{4}$"}},
        {"_id": 1, "TIME_ON": 1},
    )
    ops = []
    async for doc in cursor:
        ops.append(UpdateOne(
            {"_id": doc["_id"]},
            {"$set": {"TIME_ON": doc["TIME_ON"] + "00"}},
        ))
    if ops:
        result = await collection.bulk_write(ops, ordered=False)
        logger.info("TIME_ON backfill: %d documents updated", result.modified_count)
    else:
        logger.info("TIME_ON backfill: 0 documents — already up to date")
```

**Integration in `app/main.py` lifespan:**

```python
await backfill_created_at()        # existing
await backfill_time_on_hhmmss()    # new — add after
```

**Why raw PyMongo (not Beanie Document update)?**

`TIME_ON` is stored in `model_extra` — it is not a declared field on the `QSO` Beanie
Document. Beanie's high-level update API goes through Pydantic validation, which does not
know about `TIME_ON`. Raw `UpdateOne` via `get_pymongo_collection()` is the correct
and tested path (same as `backfill_created_at` which operates on `_created_at`, also
accessed via raw collection). `get_pymongo_collection()` is the official Beanie accessor
for raw MongoDB operations — Motor was EOL'd May 2025 and is not in this codebase.

**Why `ordered=False`?**

Each document is independent. Unordered bulk write allows MongoDB to parallelise
operations. If one fails, the rest continue. This is the same choice made in
`backfill_created_at`.

**Idempotency guarantee:** The `$regex: r"^\d{4}$"` filter matches only exactly 4-digit
strings. After normalisation, all TIME_ON values are 6 digits. Re-running the migration
finds zero matching documents and performs zero writes.

**Confidence:** HIGH — exact pattern of `backfill_created_at` in this codebase.

---

## Feature 6: Post-Submit Behavior Toggle

**Technology:** JS boolean state in the existing `form.html` IIFE. No new dependencies.

The existing `htmx:afterSwap` handler already handles the reset case. The toggle adds a
persistent mode variable and a UI control (checkbox or toggle button):

```javascript
var postSubmitMode = 'reset'; // 'reset' | 'keep'

// UI control (checkbox) sets this:
// postSubmitMode = checkbox.checked ? 'keep' : 'reset';

document.body.addEventListener('htmx:afterSwap', function (e) {
  if (!e.detail.target || e.detail.target.id !== 'qso-result') return;
  var result = document.getElementById('qso-result');
  if (!result || !result.querySelector('.success-msg')) return;

  clearErrors();
  submitAttempted = false;

  if (postSubmitMode === 'reset') {
    // Clear all fields, restore live UTC clock
    form.reset();
    if (!timeLocked) lockTime();   // re-enable clock
  } else {
    // Keep date/time values and lock state; only clear contact fields
    field('CALL').value = '';
    field('RST_SENT').value = '';
    field('RST_RCVD').value = '';
    field('FREQ').value = '';
  }

  var callField = field('CALL');
  if (callField) callField.focus();
});
```

The toggle control is a Tailwind-styled checkbox/label pair. No HTMX attributes needed —
it sets a JS variable only.

**Confidence:** HIGH — JS-only, existing HTMX event hook is the integration point.

---

## Stack Summary: What Changes vs What Stays

| Component | Change Required | Notes |
|-----------|----------------|-------|
| `app/qso/service.py` | Add 2-line HHMM normalisation in `build_qso_dict()` | Before `parse_adif_datetime` call |
| `app/main.py` | Add `backfill_time_on_hhmmss()` function + lifespan call | After existing `backfill_created_at()` |
| `templates/log/form.html` | JS clock, lock/unlock, validation regex, post-submit toggle | All within existing IIFE |
| `static/css/output.css` | Rebuild if new `dark:` or responsive classes added for lock icons | `npm run build` |
| `app/qso/models.py` | No change | `TIME_ON` is in `model_extra`; no declaration needed |
| `app/qso/router.py` | No change | `parse_adif_datetime` already handles HHMMSS |
| `pyproject.toml` | No change | Zero new Python dependencies |
| `package.json` | No change | Zero new JS dependencies |

---

## What NOT to Add

| Item | Reason |
|------|--------|
| Luxon / Day.js / Moment.js | 6 lines of native `Date` UTC accessors replace them entirely |
| `<input type="datetime-local">` | Operates in local time; requires UTC conversion; produces ISO 8601 combined string — incompatible with ADIF's separate YYYYMMDD / HHMMSS fields |
| `disabled` attribute on locked fields | Excluded from form serialisation — HTMX POST would omit QSO_DATE and TIME_ON, causing 422 on server |
| Beanie Document update API for migration | `TIME_ON` is `model_extra`, not a declared field; Pydantic validation blocks it; raw PyMongo is correct |
| `type="time"` browser input | Browser time inputs enforce local timezone display and HH:MM format — incompatible with ADIF HHMMSS and the font-mono ADIF-string convention |
| A separate migration endpoint or CLI command | Startup migration is the project's established pattern (precedent: `backfill_created_at`); simpler ops model |

---

## Version Compatibility

All features use packages already pinned in the project:

| Package | Version | Relevant Capability Used |
|---------|---------|--------------------------|
| Beanie | 2.1+ | `get_pymongo_collection()` for raw collection access |
| pymongo | 4.16+ | `UpdateOne`, `bulk_write(ordered=False)`, async cursor |
| HTMX | 2.0.4 | `htmx:beforeRequest`, `htmx:afterSwap` event hooks |
| Tailwind CSS | v3 | Lock icon styling, `readonly` visual state classes |
| Python | 3.12+ | `asyncio`, `datetime.now(tz=timezone.utc)` |
| Browser | Modern (2020+) | `Date.getUTCFullYear()` etc., `setInterval`, `readOnly` property |

---

## Sources

- HTML `readonly` attribute spec: [MDN — readonly](https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/readonly) — HIGH confidence
- `Date` UTC methods: [MDN — Date](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date) — HIGH confidence
- `setInterval`: [MDN — setInterval](https://developer.mozilla.org/en-US/docs/Web/API/Window/setInterval) — HIGH confidence
- `form.html` codebase audit: `htmx:beforeRequest` hook verified at lines 237–241, `htmx:afterSwap` hook at lines 245–255 — HIGH confidence
- `build_qso_dict()` codebase audit: `parse_adif_datetime()` HHMM/HHMMSS dual-length handling verified at service.py lines 30–44 — HIGH confidence
- `backfill_created_at()` migration pattern: `app/main.py` lines 22–47 — HIGH confidence (direct code audit)
- Beanie `get_pymongo_collection()`: verified in `backfill_created_at()` at main.py line 29; Motor EOL confirmed in PROJECT.md Key Decisions — HIGH confidence
- `model_extra` for TIME_ON: confirmed by absence from declared fields in `app/qso/models.py` (only `operator_callsign`, `CALL`, `BAND`, `MODE`, `qso_date_utc`, `is_deleted`, `created_at` are declared) — HIGH confidence

---

*Stack research for: ollog v2.7 UTC Date/Time Entry*
*Researched: 2026-04-24*
