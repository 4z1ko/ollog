---
phase: 07-profile-data-model-and-grid-utility
verified: 2026-04-04T13:45:41Z
status: passed
score: 5/5 must-haves verified
---

# Phase 7: Profile Data Model and Grid Utility Verification Report

**Phase Goal:** The User document holds all operator profile fields and the grid conversion utility is correct and testable.
**Verified:** 2026-04-04T13:45:41Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User document stores OPERATOR callsign (from login) and optional STATION_CALLSIGN — existing documents get None for absent fields with no migration required | VERIFIED | `station_callsign: Optional[str] = None` present in `app/auth/models.py` line 24; all 12 profile fields use `Optional[T] = None` pattern |
| 2 | User document stores personal info fields: name, email (validated format), QTH city, state/province, country | VERIFIED | Fields `name`, `email: Optional[EmailStr]`, `qth`, `state`, `country` all present with `None` defaults; EmailStr raises `ValidationError` on invalid input |
| 3 | User document stores MY_GRIDSQUARE (up to 6 characters) and the decimal lat/lon auto-derived from that grid | VERIFIED | Fields `my_gridsquare`, `latitude`, `longitude` all present as `Optional[float/str] = None`; derivation is in service layer (correct — model holds data only) |
| 4 | User document stores station equipment fields: MY_RIG, MY_ANT, and TX_PWR (watts as a number) | VERIFIED | `my_rig: Optional[str]`, `my_ant: Optional[str]`, `tx_pwr: Optional[float]` all present; `tx_pwr` is float (watts) |
| 5 | Grid conversion utility converts a valid 4- or 6-character Maidenhead locator to a (lat, lon) tuple using center=True — coordinates match center of the square, not SW corner | VERIFIED | `maidenhead.to_location(grid, center=True)` on line 38 of `app/profile/grid.py`; FN31 returns (41.5, -73.0) and FN31pr returns (41.729, -72.708); all 17 tests pass |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/auth/models.py` | User document with 12 new Optional profile fields | VERIFIED | Exactly 12 profile fields confirmed by `User.model_fields` introspection; `station_callsign: Optional[str] = None` present |
| `pyproject.toml` | Runtime dependencies including maidenhead and pydantic[email] | VERIFIED | Both `maidenhead>=1.8.0` and `pydantic[email]>=2.0` present in dependencies |
| `app/profile/__init__.py` | Profile module package marker | VERIFIED | File exists (1-line package marker) |
| `app/profile/grid.py` | grid_to_latlon() utility function | VERIFIED | 39-line substantive implementation; exports `grid_to_latlon`; uses `center=True` |
| `tests/test_profile_grid.py` | Unit tests for grid conversion | VERIFIED | 98 lines, 17 test cases across 7 test classes covering valid/invalid/edge inputs |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/auth/models.py` | `pydantic.EmailStr` | import and field type annotation | VERIFIED | `from pydantic import ConfigDict, EmailStr` on line 4; used as `Optional[EmailStr]` on line 26 |
| `app/profile/grid.py` | `maidenhead.to_location` | import and call with center=True | VERIFIED | `import maidenhead` on line 3; `maidenhead.to_location(grid, center=True)` on line 38 |
| `tests/test_profile_grid.py` | `app/profile/grid.py` | import grid_to_latlon | VERIFIED | `from app.profile.grid import grid_to_latlon` on line 2 |

### Requirements Coverage

| Requirement | Status | Notes |
|-------------|--------|-------|
| PROF-01: Operator callsign (from login) stored | SATISFIED | Existing `callsign` field; `station_callsign` adds secondary station identity |
| PROF-02: Personal info fields (name, email, QTH, state, country) | SATISFIED | All 5 fields present with correct types |
| PROF-03: Station equipment (MY_RIG, MY_ANT, TX_PWR) | SATISFIED | All 3 fields present; TX_PWR is `float` (watts) |
| PROF-04: MY_GRIDSQUARE + derived lat/lon from center | SATISFIED | Model stores grid + lat/lon; utility derives correct center coordinates |
| PROF-05: Grid utility testable and correct | SATISFIED | 17 tests all pass; center=True confirmed in implementation |

### Anti-Patterns Found

None. No TODOs, FIXMEs, placeholder returns, or empty implementations found in any phase 7 files.

### Human Verification Required

None. All success criteria are programmatically verifiable and have been verified.

### Auth Test Suite Note

Running `uv run pytest tests/test_auth.py` reports 9 passed and 1 error. The error is `pymongo.errors.ServerSelectionTimeoutError` on tests that require a live MongoDB connection — this is an infrastructure constraint of running outside Docker, not a regression introduced by phase 7. The 9 tests that run without a database connection all pass.

## Gaps Summary

No gaps. All 5 observable truths verified, all 5 artifacts substantive and wired, all key links confirmed, 17 grid utility tests pass, no anti-patterns detected.

---

_Verified: 2026-04-04T13:45:41Z_
_Verifier: Claude (gsd-verifier)_
