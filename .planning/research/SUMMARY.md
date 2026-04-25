# Project Research Summary

**Project:** ollog v2.7 UTC Date/Time Entry
**Domain:** HTMX form enhancement — live UTC clock, lock/unlock toggles, HHMMSS precision, post-submit reset behavior
**Researched:** 2026-04-25
**Confidence:** HIGH

## Executive Summary

v2.7 is a focused, self-contained enhancement to the QSO entry form. Zero new dependencies. Browser-native JS covers the clock and lock/unlock; the existing `htmx:beforeRequest` hook covers submission normalization; the established `backfill_created_at` lifespan migration pattern covers the DB backfill. All changes fit in two existing files: `templates/log/form.html` and `app/main.py`.

## Stack

**No new dependencies.** All capabilities covered by browser built-ins + existing HTMX hooks + existing PyMongo migration pattern.

| Capability | Implementation |
|-----------|---------------|
| Live UTC clock | Vanilla JS `setInterval` + `Date.getUTC*()` — 6 lines |
| Lock/unlock | `input.readOnly = true/false` — never `.disabled` |
| HHMM normalization | `htmx:beforeRequest` hook (already in `form.html`) |
| Post-submit reset | `htmx:afterSwap` handler + `localStorage` |
| DB migration | `get_pymongo_collection()` + `bulk_write` (exact `backfill_created_at()` pattern) |
| Lock icons | Heroicons `lock-closed` / `lock-open` SVG (same toggle pattern as moon/sun theme icons) |

## Features

**Must have:**
- `QSO_DATE` pre-filled with today's UTC on page load
- `TIME_ON` live-updating HHMMSS while locked
- Lock icon: closed = readonly/system-controlled, open = editable/user-controlled
- `readonly` (not `disabled`) on locked fields — `disabled` excludes value from form submission
- Updated validation accepting both HHMM and HHMMSS

**Should have:**
- Post-submit "Keep current date/time" toggle — contest operators log 50-200 QSOs/hour
- Auto date rollover at UTC midnight — free via the same `setInterval`
- DB migration backfilling HHMM → HHMM00 for consistency

**Defer:** Keyboard shortcut for lock toggle, date picker calendar, `<input type="datetime-local">` (incompatible with ADIF field structure)

## Architecture

**Critical insight:** `hx-target="#qso-result"` points at a sibling div — the form DOM, event listeners, and `setInterval` clock survive every submit. No re-initialization hook needed. Post-submit behavior lives in the existing `htmx:afterSwap` handler.

**Files changed:**
- `templates/log/form.html` — lock icon markup, `initDateTime()` named function, live clock, validation update, HHMM pad, post-submit toggle
- `app/main.py` — `normalize_time_on()` startup migration

**Files unchanged:** `app/qso/service.py` (already handles HHMM and HHMMSS), `app/qso/router.py`, QSO model, result partial

**Build order:**
1. `app/main.py` migration (no frontend dependency)
2. Validation rule widening in `form.html` (must precede normalizer)
3. Live clock + lock/unlock + `initDateTime()` extraction
4. HHMM-to-HHMMSS pad in `htmx:beforeRequest`
5. Post-submit toggle reading `localStorage`

## Critical Pitfalls

1. **`disabled` vs `readonly`** — `disabled` silently drops `QSO_DATE`/`TIME_ON` from POST body. Always use `.readOnly = true/false`. Verify via Network tab FormData.
2. **Local timezone leakage** — `getHours()`, `getDate()`, `getMonth()`, `getFullYear()` return local time. Every UTC access must use `getUTC*()`. Test with browser timezone set to UTC+8.
3. **`form.reset()` clears auto-populated fields** — must call `initDateTime()` immediately after reset to re-populate and re-apply `readonly`.
4. **Migration double-padding** — use anchored regex `^\d{4}$` and aggregation pipeline `[{$set: {TIME_ON: {$concat: ["$TIME_ON", "00"]}}}]` to prevent 8-digit corruption on re-run.
5. **HTMX swap scope** — never change `hx-target` to point at the form or any ancestor of `#qso-form`; destroys the form DOM and all attached timers.

## Confidence Assessment

| Area | Level |
|------|-------|
| Stack — no new deps | HIGH |
| `readonly` vs `disabled` | HIGH |
| HTMX swap survival | HIGH |
| Service layer HHMMSS compat | HIGH |
| Migration pattern | HIGH |
| `getUTC*()` requirement | HIGH |
| Post-submit localStorage | HIGH |
