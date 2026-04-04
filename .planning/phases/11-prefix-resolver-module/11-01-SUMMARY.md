---
phase: 11-prefix-resolver-module
plan: "01"
subsystem: api
tags: [callsign, itu, bisect, prefix-lookup, amateur-radio, pycountry]

# Dependency graph
requires: []
provides:
  - "app.callsign.prefixes.lookup_prefix() — resolves any amateur radio callsign to ISO 3166-1 alpha-2 country code"
  - "313 ITU Series Range entries in sorted bisect-compatible table"
  - "Suffix stripping for /P /7 /QRP /M /MM /AM and prefix/callsign EA3/G3YWX format"
affects:
  - 12-flag-display

# Tech tracking
tech-stack:
  added: [pycountry>=26.2.16]
  patterns:
    - "Static in-memory ITU prefix table — loaded once at import, zero I/O per call"
    - "Bisect-based range lookup with truncated-comparison for digit/letter ASCII ordering"
    - "Sentinel object (_NOTFOUND) to distinguish not-found from found-with-None-ISO"

key-files:
  created:
    - app/callsign/__init__.py
    - app/callsign/prefixes.py
    - tests/test_prefix_resolver.py
  modified:
    - pyproject.toml

key-decisions:
  - "Truncated comparison in bisect lookup: compare start[:n] <= prefix <= end[:n] to handle digit-before-letter ASCII ordering (W1AW would fail raw string compare against WAA-WZZ)"
  - "Structural prefix extraction: require digit in callsign; extract letters-before-digit (DL from DL1ABC) AND letter+digit variant (C7 from C7A) as candidates — no digit means not a valid callsign"
  - "_NOTFOUND sentinel distinguishes range-miss from non-country-entity (iso=None), enabling correct None propagation for 4U/C7/4Y entities"
  - "Prefix/callsign format EA3/G3YWX: left side is shorter than right, so return left (operating prefix) not right (home callsign)"

patterns-established:
  - "Sentinel pattern: use object() sentinel for _NOTFOUND vs None to distinguish miss from found-null"
  - "Callsign structural parsing: find first digit position to split letter-prefix from serial"

# Metrics
duration: 13min
completed: 2026-04-04
---

# Phase 11 Plan 01: Prefix Resolver Module Summary

**Pure-Python in-memory ITU callsign prefix resolver using bisect range table with truncated-comparison to handle digit/letter ASCII ordering, suffix stripping, and 313 ITU ranges mapped to ISO country codes**

## Performance

- **Duration:** 13 min
- **Started:** 2026-04-04T20:04:16Z
- **Completed:** 2026-04-04T20:17:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `app/callsign/prefixes.py` with `lookup_prefix()` resolving callsigns to ISO alpha-2 codes
- Solved the ASCII digit/letter ordering problem (digits 49-57 sort before letters 65-90) with truncated comparison in bisect lookup
- Created 28-test suite covering PRFX-01 through PRFX-04 — all pass

## Task Commits

1. **Task 1: Create prefix resolver module with full ITU data** - `df0a70b` (feat)
2. **Task 2: Create comprehensive test suite and verify all requirements** - `c09fe75` (test)

**Plan metadata:** (final commit below)

## Files Created/Modified

- `app/callsign/__init__.py` — Package marker (empty)
- `app/callsign/prefixes.py` — Full module: _ITU_NAME_TO_ISO (190+ entries), _ITU_RAW_DATA (313 ranges), _build_ranges(), _range_lookup(), _strip_suffix(), lookup_prefix()
- `tests/test_prefix_resolver.py` — 28 parametrized tests covering all PRFX requirements
- `pyproject.toml` — Added pycountry>=26.2.16 dependency

## Decisions Made

- **Truncated comparison** — `bisect_right(_STARTS, prefix + "~")` with `start[:n] <= prefix <= end[:n]` handles the fact that `"W" < "WAA"` in Python string ordering (digits 49 sort before letters 65). Without this, `W1AW` would not match the `WAA-WZZ` US range.
- **Structural callsign parsing** — Require at least one digit in callsign to confirm it's structurally valid. Extract letter-prefix (letters before first digit) and letter+digit variant as candidates. `UNKNOWN` has no digit, returns None correctly.
- **_NOTFOUND sentinel** — Distinguish "no range matched" from "range matched but entity has no ISO code (non-country)". Without sentinel, `4U1ITU` would fall through to shorter prefix match giving Israel's `IL`.
- **pycountry declared as runtime dep** — Added to main `dependencies` not `dev`, per plan instruction (used at data-build time; harmless to include at runtime).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed bisect range lookup for digit-before-letter ASCII ordering**
- **Found during:** Task 1 verification
- **Issue:** `lookup_prefix('W1AW')` returned None. ITU ranges use letter-only keys (WAA-WZZ). Digit `1` (ASCII 49) sorts before letters (ASCII 65+), so `"W" < "WAA"` and `"W1A" < "WAA"` in Python — raw string compare would never match.
- **Fix:** Changed `_range_lookup` to use `bisect_right(_STARTS, prefix + "~")` and compare truncated endpoints `start[:n] <= prefix <= end[:n]` instead of `start <= prefix <= end`. Added `_NOTFOUND` sentinel to distinguish not-found from found-with-None.
- **Files modified:** app/callsign/prefixes.py
- **Verification:** All 28 tests pass including W1AW->US, JA1YWX->JP, 3DA0ABC->SZ
- **Committed in:** df0a70b (Task 1 commit)

**2. [Rule 1 - Bug] Fixed structural prefix extraction for C7A and UNKNOWN edge cases**
- **Found during:** Task 1 verification
- **Issue:** `C7A` returned `CA` (Canada) instead of `None` (WMO). `UNKNOWN` returned `KZ` (Kazakhstan) instead of `None`. The plan's `for length in (3, 2, 1)` loop tried `UNK` which matches Kazakhstan's `UNA-UQZ`. `C7A` extracted prefix `C` which matched Canada's `CYA-CZZ` instead of the correct `C7A-C7Z` (WMO).
- **Fix:** Added `_extract_prefixes()` logic in `lookup_prefix`: (1) require digit in callsign else return None, (2) try letter+digit candidate (C7) before letters-only candidate (C), (3) for digit-starting callsigns extract digit+letters (4U, 3DA).
- **Files modified:** app/callsign/prefixes.py
- **Verification:** C7A->None, 4U1ITU->None, UNKNOWN->None, 4Y1A->None all correct
- **Committed in:** df0a70b (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 - Bug)
**Impact on plan:** Both fixes were necessary for correctness. The plan's described algorithm was incomplete for the ITU range format. The fixes maintain the bisect-based approach while handling ASCII ordering realities.

## Issues Encountered

- The plan's original `_range_lookup` algorithm (`bisect_right(_STARTS, prefix) - 1` with `start <= prefix <= end`) is fundamentally incompatible with the ITU range format. ITU ranges use letter-padded keys (WAA-WZZ) while real callsigns contain digits (W1AW). Python sorts digits before letters, so no simple string comparison works. Required two fixes: truncated bisect and structural prefix extraction.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `lookup_prefix()` ready for Phase 12 flag display integration
- Returns ISO alpha-2 codes compatible with flag SVG filenames
- Non-country entities (4U, C7, 4Y) return None — Phase 12 must handle None gracefully (no flag shown)
- Static file path mismatch for flag SVGs still pending (noted in STATE.md tech debt): `app/static/flags/` vs project-root `static/` — fix at Phase 12 start

---
*Phase: 11-prefix-resolver-module*
*Completed: 2026-04-04*
