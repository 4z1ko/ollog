# Feature Research

**Domain:** UTC date/time entry enhancements for an HTMX ham radio logbook form
**Milestone:** v2.7 UTC Date/Time Entry
**Researched:** 2026-04-24
**Confidence:** HIGH — grounded in direct codebase inspection, ADIF spec verification, LoTW domain research, and UX pattern research

---

## Current State Snapshot

The existing `templates/log/form.html` QSO entry form has:

| Field | Current Behavior | v2.7 Target |
|-------|-----------------|-------------|
| `QSO_DATE` (text input) | Blank on page load; placeholder `YYYYMMDD`; required; 8-digit validation on submit | Locked to today's UTC by default; lock icon toggles manual edit; `readonly` not `disabled` |
| `TIME_ON` (text input) | Blank on page load; placeholder `HHMM`; required; 4-digit validation on submit | Live UTC HHMMSS while locked; lock icon freezes for manual entry; HHMM normalized to HHMM00 |
| Post-submit reset | Always: `form.reset()` + focus CALL + clear errors (line 249 in form.html) | Toggle: "Keep current" vs "Reset to live UTC" |
| TIME_ON format in DB | Stored as HHMM string | Stored as HHMMSS string; migration backfills existing HHMM→HHMM00 |

The existing JavaScript validation rule for `TIME_ON` is `/^\d{4}$/.test(v.trim())` — this must be updated to accept both 4-digit (HHMM) and 6-digit (HHMMSS) forms.

---

## ADIF Spec: TIME_ON Precision

**Specification:** ADIF 3.1.7 (project's pinned version, `https://adif.org/317/ADIF_317.htm`)

The ADIF `Time` data type is defined as: HHMMSS or HHMM. HH (hours, 00–23) and MM (minutes, 00–59) are **required**. SS (seconds, 00–59) is **optional**.

**What this means for ollog:**

- Both HHMM and HHMMSS are spec-valid. Existing HHMM records do not violate the spec.
- The migration plan (normalize HHMM→HHMM00) produces valid HHMMSS. No spec breakage.
- When a user enters HHMM manually via the locked-off form, submitting as HHMM00 is transparent and correct.
- HHMMSS is the preferred form for modern interoperability: FT8/WSJT-X logs 6-digit times; ADIF export consumers (LoTW, eQSL, QRZ) all accept it.

**FT8 / seconds precision:** FT8 QSOs start and end at 15-second boundaries (0, 15, 30, 45 seconds). WSJT-X logs TIME_ON with seconds. When operators import WSJT-X ADIF into ollog, the seconds are preserved. Having ollog's manual entry UI also capture/store seconds makes the logbook internally consistent regardless of entry path (manual UI vs UDP vs ADIF import).

**LoTW matching:** LoTW uses a ±30-minute tolerance window for QSL confirmation matching — seconds precision is not a factor in matching accuracy. Capturing seconds in TIME_ON is about internal consistency and FT8 ecosystem compatibility, not LoTW compliance.

**Confidence:** HIGH — ADIF spec confirmed via multiple searches; LoTW tolerance confirmed via DXLab mailing list discussion and LoTW help docs.

---

## Table Stakes

Features users expect. Missing = product feels incomplete or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Date field pre-filled with today's UTC | Every ham logging tool (N1MM+, Log4OM, Ham Radio Deluxe) pre-fills the current UTC date. A blank date field on a live-logging tool reads as broken. | LOW | `new Date().toISOString().slice(0,10).replace(/-/g,'')` on page load. |
| Time field showing current UTC | Live logging means real-time. Operators logging a QSO now expect the time field to already show "now." | MEDIUM | `setInterval` updating the input value every second while locked. |
| "Locked" means readonly, not disabled | `readonly` inputs submit their value in the form; `disabled` inputs do not. Ham operators expect the date/time to be included in the QSO even when they didn't type it themselves. | LOW | Existing form uses `name="QSO_DATE"` and `name="TIME_ON"` — value submission depends on `readonly` not `disabled`. |
| Lock icon is recognizable | Padlock convention is near-universal for "this field is protected" — closed padlock = locked/readonly, open padlock = editable. | LOW | Heroicons has `lock-closed` and `lock-open` (both 16x16 `solid` variant). Existing codebase already uses Heroicons for all icons. |
| Clicking the lock icon toggles editability | Operators who worked a QSO a few minutes ago expect to be able to back-date without navigating away or reloading. | LOW | Toggle `readonly` attribute + swap icon on click. |
| Post-submit field behavior is predictable | The current behavior (full form reset after successful submit) is the right default for one-off QSO logging. Users expect a clear form to mean "ready for next QSO." | LOW | Preserve existing reset-on-success as the **default** post-submit behavior. |

---

## Differentiators

Features that set this tool apart for its use case (multi-operator club station, high-frequency FT8/contest logging).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Live auto-updating time while locked | Eliminates the most common logging error: submitting a QSO with a stale or blank time. Operator just logs — the time is always right. | MEDIUM | `setInterval` at 1 Hz; pause updates while field is focused OR while a lock-off override is in effect. Resume on blur if locked. |
| HHMMSS precision (6 digits) | Consistent with WSJT-X ADIF output, FT8 15-second boundary logging, and modern logbook standards. Makes UDP-submitted FT8 QSOs and manually-entered QSOs time-consistent. | LOW | Validation rule update: `/^\d{4}(\d{2})?$/` (4 or 6 digits). Store whatever precision was captured — no normalization that loses information. |
| Post-submit toggle: "Keep current date/time" | For operators running a contest sprint or logging a pile-up, every QSO is on the same band/mode for 2 hours. Resetting the form after each QSO and re-entering the same time is friction. "Keep current" means the locked-off time value and the lock state both persist, so the next QSO is pre-stamped without re-entry. | MEDIUM | A small checkbox or toggle below the date/time fields, off by default. When checked: after a successful submit, skip the `form.reset()` entirely for date and time fields; when using locked live-UTC mode, the auto-updating continues uninterrupted. |
| Date auto-updates at UTC midnight | Edge case: operator logs across midnight UTC. Locked date auto-updates to the new date at midnight. No manual date correction needed. | LOW | Handled by the same `setInterval` that updates time: recompute both date and time strings on each tick. |
| Visual distinction between "locked auto-UTC" and "manually overridden" | Operators need to glance and know: is this field currently showing live UTC or did someone set it manually? Lock icon state provides this, but a subtle background or border difference makes it unambiguous. | LOW | `readonly` + locked class: neutral input background (current `form-input` style). Unlocked: no change (already editable appearance). The open-padlock icon is sufficient visual differentiation. |

---

## Lock Icon UX Convention

**Established convention (HIGH confidence):**

- **Closed padlock (lock-closed)** = field is locked / protected / readonly. Value is system-controlled. User cannot type.
- **Open padlock (lock-open)** = field is editable. User can type freely.

This convention is used by: macOS System Preferences (locked settings sections), iOS (screen lock), iOS Keychain, most password managers, Salesforce field lock, Microsoft Dynamics field lock, Adobe Acrobat PDF lock.

**Action on click:** The lock icon is itself the toggle. Clicking the closed padlock opens it (makes field editable). Clicking the open padlock closes it (locks field back to live UTC). This is the same interaction model as macOS System Preferences lock buttons.

**Tooltip requirement (MEDIUM priority):** Research found that lock/unlock icon semantics in form fields can be unclear to unfamiliar users (KeeWeb GitHub issue #805: "Unclear UX Lock/Unlock in field. No ToolTip"). Add `title="Click to edit"` on the closed lock and `title="Click to lock (restore live UTC)"` on the open lock. These are visible on hover and exposed to screen readers via `aria-label`.

**Icon sizing:** Heroicons `lock-closed` and `lock-open` at `w-4 h-4` (16×16, matching existing secondary button icons in this codebase).

**Placement:** Icon as an inline button inside or immediately adjacent to the right side of the input. CSS: `relative` on the input wrapper, `absolute right-2 top-1/2 -translate-y-1/2` on the icon button. This is the "input with trailing icon" pattern used in most design systems (Carbon, Cloudscape, Tailwind UI).

---

## Anti-Features

| Anti-Feature | Why to Avoid | What to Do Instead |
|--------------|-------------|-------------------|
| `disabled` attribute on locked fields | Disabled inputs do not submit their value — the form POST would be missing `QSO_DATE` and `TIME_ON`, causing server-side validation failures. A disabled field also looks visually different (grayed out) in ways that suggest the data is unavailable rather than system-controlled. | Use `readonly` attribute. Value submits normally. Appearance is identical to an editable field. |
| Three-state post-submit toggle (reset / keep-with-freeze / keep-with-live) | Tristate toggles are unusual in form UX and generate user confusion. "Keep current" means different things in the locked vs unlocked state, but the user's intent is always "don't wipe what I just had." | Two states only: (1) Reset to live UTC (default, existing behavior), (2) Keep current date/time + lock state. |
| Showing seconds in the time input placeholder | If the placeholder says `HHMMSS`, operators running SSB pile-ups (who log at minute-level precision) feel like they're doing it wrong by only entering 4 digits. HHMM is valid. | Placeholder: `HHMM or HHMMSS`. Validation: accept both. DB: store exactly what was submitted (HHMM or HHMMSS). |
| Auto-pausing the live clock when the user starts typing | This is a subtle UX trap. If the clock pauses on first keypress in the time field, and the user types `14` then pauses to think, the displayed time is now wrong (stopped mid-edit). | Pause when locked is toggled off (explicit user action). Do not pause on keypress. When lock is off, the interval is simply not running — there is no "pause during typing" logic needed. |
| Separate "Restore to UTC" button | Adding a second button to the form adds visual noise. The lock icon already serves as "restore to UTC" — clicking the open padlock re-locks and immediately resumes auto-update. | Lock icon is the restore mechanism. No additional button. |
| Using `<input type="time">` | Browser time pickers add a native clock UI that conflicts with ADIF HHMM/HHMMSS text format. They output `HH:MM` (with colon), requiring strip/normalize before submission. | Keep `<input type="text">` with client-side formatting. Consistent with existing form pattern. |

---

## Feature Dependencies

```
JS setInterval (1 Hz clock) — needed by:
  ├── Live auto-updating time in TIME_ON input (while locked)
  └── Auto-date rollover at UTC midnight (while date is locked)

readonly attribute toggle — needed by:
  ├── Lock icon click handler
  └── "Keep current" post-submit behavior (must restore readonly state after submit)

Post-submit toggle checkbox (new UI element) — reads:
  └── Current lock state of date/time fields (to decide whether to re-lock after submit)

HHMMSS storage in MongoDB — needed by:
  ├── Updated validation regex (4 or 6 digits)
  └── Startup migration: backfill HHMM → HHMM00 on pre-existing records

TIME_ON regex in form.js:
  └── Currently: /^\d{4}$/ — must change to /^\d{4}(\d{2})?$/
```

### Critical Implementation Note: Locked ≠ Live-Updating After Submit

When "Keep current" mode is active AND the time was locked (live-UTC), post-submit behavior must be: do NOT reset the time field, and DO resume the live-clock interval. The time value will have been frozen during the POST (form submission blocks JS briefly), but the interval resumes immediately after. Since the submit takes <200ms on a local server, the displayed time will be at most 1 second stale — acceptable for ham logging purposes.

---

## MVP Definition (for v2.7)

### Launch With (required to ship v2.7)

1. **Date locked to today UTC on page load** — `QSO_DATE` pre-filled, `readonly`, closed lock icon.
2. **Time live-updating while locked** — `TIME_ON` pre-filled with HHMMSS, `readonly`, updating every second, closed lock icon.
3. **Lock icon toggles editability** — click closed → open lock, remove `readonly`, stop interval; click open → closed lock, restore `readonly`, restart interval with current UTC.
4. **HHMM-entered time accepted** — when unlocked and user enters HHMM, server/DB accepts it as-is; no forced normalization client-side (server normalizes to HHMM00 before storage, or store verbatim if 4 or 6 digits are both valid DB representations).
5. **Post-submit toggle: "Keep current date/time"** — checkbox (unchecked = default reset behavior, checked = preserve fields + lock state after submit).
6. **Updated validation regex** — `/^\d{4}(\d{2})?$/` on TIME_ON; `/^\d{8}$/` on QSO_DATE stays unchanged.
7. **DB stores HHMMSS** — Beanie model field accepts both; startup migration backfills HHMM→HHMM00.

### Stretch Goals (v2.7 if time permits)

- Tooltip on lock icon buttons (`title` attribute for hover hint).
- Subtle visual cue: locked fields use a slightly different cursor (`cursor-default` when `readonly`).

### Explicitly Out of Scope for v2.7

- `<input type="datetime-local">` — would break ADIF field name structure and add colon-stripping complexity.
- Date picker calendar widget — text entry with YYYYMMDD is the correct pattern for ham operators who know their dates.
- Keyboard shortcut to toggle lock — nice to have, but adds complexity. Operator can click the icon.

---

## Ham Radio Operator Workflow Context

**Why lock/unlock matters for ham operators:**

Contest operation (running a frequency, logging a pile-up): Operators log 50–200 QSOs per hour. Every QSO gets the current time. The time field must never be blank, never stale, and must not require manual re-entry between QSOs. "Keep current" + locked live-UTC is the contest workflow: the form auto-stamps time; the operator only touches CALL, RST, possibly band/mode.

**Why keeping the date/time across submits matters:**

For casual DX logging: QSOs happen 5–30 minutes apart. The date doesn't change. The time should auto-update. "Keep current" lets the operator log 3 QSOs in an afternoon without re-filling the form from scratch each time.

**For backdated entry (logging paper slips):** Operator unlocks both fields, enters historical YYYYMMDD and HHMM, logs. Post-submit reset to live UTC is the correct behavior here, because the next QSO is current-time again.

**General ham logbook software behavior (N1MM+, Ham Radio Deluxe, Log4OM):** All major logging tools pre-fill current UTC time and do not require manual entry. Some (HRD, Log4OM) auto-populate time from rig control. N1MM+ operates in contest mode where time auto-stamps on every QSO log. This is the established expectation: time entry should be invisible for the normal-path operator.

---

## Sources

- Direct codebase inspection: `templates/log/form.html` (lines 39–50, 170–257) — HIGH confidence
- ADIF 3.1.7 Time data type: HHMM and HHMMSS both valid, seconds optional — confirmed via multiple ADIF spec search results — HIGH confidence
- LoTW ±30 minute QSL matching tolerance: confirmed via DXLab@groups.io discussion and general LoTW help docs — MEDIUM confidence (mailing list source, widely corroborated)
- FT8 15-second timing boundaries: from WSJT-X user guide and FT8 protocol paper — HIGH confidence
- Lock icon convention (closed = locked, open = editable): confirmed via Apple/macOS UX, Salesforce, Microsoft Dynamics, Material UI, Heroicons naming — HIGH confidence
- Tooltip necessity for lock/unlock in form fields: KeeWeb GitHub issue #805 — MEDIUM confidence (single source, confirms known UX concern)
- `readonly` vs `disabled` for submittable read-only inputs: MDN HTML spec, W3Schools — HIGH confidence
- Ham logging tool time-stamping behavior (HRD, N1MM+, Log4OM): confirmed via logging software documentation and reviews — MEDIUM confidence (indirect references)
- Focus/blur pattern for live-updating inputs: JavaScript.info focus/blur docs, Phoenix LiveView issue #938 — HIGH confidence

---
*Feature research for: v2.7 UTC Date/Time Entry (ollog)*
*Researched: 2026-04-24*
