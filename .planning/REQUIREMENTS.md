# Requirements: v2.7 UTC Date/Time Entry

## Overview

Upgrade the Log QSO form with live UTC date/time defaults, lock/unlock toggles,
HHMMSS precision, and post-submission reset behavior control.

## v1 Requirements

### Date Field (DATE)

- [ ] **DATE-01**: Date field defaults to today's UTC date in `YYYYMMDD` format on form load
- [ ] **DATE-02**: Date field is locked (`readonly`) by default — value is included in form submission
- [ ] **DATE-03**: A lock icon button (16×16, closed padlock when locked / open when unlocked)
      next to the date field toggles between readonly and editable
- [ ] **DATE-04**: Manual date input is validated against `YYYYMMDD` format; invalid input is
      rejected with visible feedback before submission

### Time Field (TIME)

- [ ] **TIME-01**: Time field defaults to current UTC time in `HHMMSS` format on form load
- [ ] **TIME-02**: While locked, the time field auto-updates every second via `setInterval`
      using `Date.getUTC*()` methods (no local-timezone leakage)
- [ ] **TIME-03**: A lock icon button (16×16) next to the time field toggles auto-update off
      and makes the field editable
- [ ] **TIME-04**: Manual time input accepts either `HHMM` (4 digits) or `HHMMSS` (6 digits);
      `HHMM` is normalized to `HHMM00` before submission
- [ ] **TIME-05**: Manual time input is validated; invalid formats are rejected with visible
      feedback before submission

### Database (DB)

- [ ] **DB-01**: Existing `TIME_ON` values stored as `HHMM` (4 digits) are migrated to
      `HHMM00` (6 digits) at app startup; migration is idempotent (safe to re-run)
- [ ] **DB-02**: Server-side `TIME_ON` validation accepts both `HHMM` (4 digits) and
      `HHMMSS` (6 digits)

### Post-Submit Behavior (RESET)

- [ ] **RESET-01**: A toggle on the Log QSO form controls post-submission behavior:
      "Keep current date/time" vs "Reset to live UTC"
- [ ] **RESET-02**: "Keep current date/time" — after QSO submission, field values and
      lock/unlock state are preserved exactly as they were before submission
- [ ] **RESET-03**: "Reset to live UTC" — after QSO submission, both fields return to
      locked state with date set to today's UTC and time auto-updating

## Future Requirements

- Keyboard shortcut to toggle date/time lock
- Date picker calendar widget for manual date selection
- Per-operator reset preference persisted server-side (currently localStorage)

## Out of Scope

- `<input type="datetime-local">` — incompatible with ADIF's separate QSO_DATE/TIME_ON field structure
- Changing the ADIF TIME_ON field to a typed datetime model — ADIF stores strings verbatim
- Band/mode/freq preservation in "Keep current" mode — only date/time fields specified

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| DATE-01 | — | Pending |
| DATE-02 | — | Pending |
| DATE-03 | — | Pending |
| DATE-04 | — | Pending |
| TIME-01 | — | Pending |
| TIME-02 | — | Pending |
| TIME-03 | — | Pending |
| TIME-04 | — | Pending |
| TIME-05 | — | Pending |
| DB-01   | — | Pending |
| DB-02   | — | Pending |
| RESET-01 | — | Pending |
| RESET-02 | — | Pending |
| RESET-03 | — | Pending |
