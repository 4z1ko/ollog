---
phase: 49-service-layer
fixed_at: 2026-04-23T00:00:00Z
review_path: .planning/phases/49-service-layer/49-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 49: Code Review Fix Report

**Fixed at:** 2026-04-23T00:00:00Z
**Source review:** .planning/phases/49-service-layer/49-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (CR-01, WR-01, WR-02, WR-03)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: Unescaped user input in MongoDB `$regex` — ReDoS and data probing risk

**Files modified:** `app/qso/service.py`
**Commit:** 506fb5d
**Applied fix:** Added `import re` at the top of the module and wrapped `callsign_filter` with `re.escape()` before passing it to the MongoDB `$regex` operator. User input is now treated as a literal substring, eliminating regex injection and ReDoS risk while preserving partial-callsign search UX.

### WR-01: `parse_adif_datetime` silently misparses TIME_ON values that are neither 4 nor 6 characters

**Files modified:** `app/qso/service.py`
**Commit:** 2b7ad9b
**Applied fix:** Changed the bare `else` branch to `elif len(time_on) == 6` and added an explicit `else` that raises a descriptive `ValueError` naming the actual length and value received. Malformed TIME_ON values now produce an actionable error message instead of a cryptic `strptime` failure.

### WR-02: Silent no-op when `update_dict` is empty in `qso_update` PATCH handler

**Files modified:** `app/qso/ui_router.py`
**Commit:** ab10422
**Applied fix:** Replaced the `if update_dict: await qso.update(...)` guard with an early `if not update_dict: raise HTTPException(status_code=400, detail="No valid fields to update")` followed by an unconditional `await qso.update(...)`. Submitting a form with no valid fields now returns HTTP 400 instead of silently returning the unchanged row.

### WR-03: `_ALLOWED_SORT_FIELDS` uses `_created_at` without explaining it is the MongoDB alias

**Files modified:** `app/qso/service.py`
**Commit:** 78ec056
**Applied fix:** Added inline comment `# MongoDB alias "_created_at" (not the Python attribute "created_at")` above the `"-_created_at", "_created_at"` entries in the frozenset, documenting the deliberate use of the MongoDB field alias rather than the Python attribute name.

---

_Fixed: 2026-04-23T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
