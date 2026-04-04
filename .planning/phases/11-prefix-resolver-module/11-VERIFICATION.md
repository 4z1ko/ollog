---
phase: 11-prefix-resolver-module
verified: 2026-04-04T20:22:50Z
status: passed
score: 13/13 must-haves verified
re_verification: false
---

# Phase 11: Prefix Resolver Module Verification Report

**Phase Goal:** A self-contained, fully-tested callsign-to-ISO-code resolver exists and is verifiable in isolation before any UI work begins
**Verified:** 2026-04-04T20:22:50Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | lookup_prefix('W1AW') returns 'US' | VERIFIED | test_lookup_prefix[W1AW-US] PASSED |
| 2 | lookup_prefix('DL1ABC') returns 'DE' | VERIFIED | test_lookup_prefix[DL1ABC-DE] PASSED |
| 3 | lookup_prefix('JA1YWX') returns 'JP' | VERIFIED | test_lookup_prefix[JA1YWX-JP] PASSED |
| 4 | lookup_prefix('3DA0ABC') returns 'SZ' (Eswatini sub-range) | VERIFIED | test_lookup_prefix[3DA0ABC-SZ] PASSED |
| 5 | lookup_prefix('3DN1ABC') returns 'FJ' (Fiji sub-range) | VERIFIED | test_lookup_prefix[3DN1ABC-FJ] PASSED |
| 6 | lookup_prefix('G3YWX/MM') returns None | VERIFIED | test_lookup_prefix[G3YWX/MM-None] PASSED |
| 7 | lookup_prefix('G3YWX/AM') returns None | VERIFIED | test_lookup_prefix[G3YWX/AM-None] PASSED |
| 8 | lookup_prefix('W1AW/P') returns 'US' | VERIFIED | test_lookup_prefix[W1AW/P-US] PASSED |
| 9 | lookup_prefix('W1AW/7') returns 'US' | VERIFIED | test_lookup_prefix[W1AW/7-US] PASSED |
| 10 | lookup_prefix('W1AW/QRP') returns 'US' | VERIFIED | test_lookup_prefix[W1AW/QRP-US] PASSED |
| 11 | lookup_prefix('EA3/G3YWX') returns 'ES' | VERIFIED | test_lookup_prefix[EA3/G3YWX-ES] PASSED |
| 12 | lookup_prefix('4U1ITU') returns None | VERIFIED | test_lookup_prefix[4U1ITU-None] PASSED |
| 13 | lookup_prefix('UNKNOWN') returns None | VERIFIED | test_lookup_prefix[UNKNOWN-None] PASSED |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/callsign/__init__.py` | Package marker | VERIFIED | Exists, 1 line (correct for Python package marker) |
| `app/callsign/prefixes.py` | Exports lookup_prefix | VERIFIED | 716 lines, full implementation with _ITU_NAME_TO_ISO, _ITU_RAW_DATA (313 entries), _build_ranges(), _range_lookup(), _strip_suffix(), lookup_prefix() |
| `tests/test_prefix_resolver.py` | 28 tests, all pass | VERIFIED | 28 collected, 28 passed in 0.02s |
| `pycountry` in pyproject.toml | Runtime dependency | VERIFIED | `pycountry>=26.2.16` in main [project.dependencies] block |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_prefix_resolver.py` | `app/callsign/prefixes.py` | `from app.callsign.prefixes import lookup_prefix` | WIRED | Import verified, all 28 parametrized calls exercise lookup_prefix() |
| `lookup_prefix()` | `_strip_suffix()` | direct call at line 679 | WIRED | Suffix stripping integrated into lookup path |
| `lookup_prefix()` | `_range_lookup()` | candidate loop at line 711 | WIRED | Range lookup called with each candidate prefix |
| `_build_ranges()` | `_ITU_RAW_DATA` | module-level at line 583 | WIRED | Ranges built at import time from raw data, stored in _RANGES |

### Anti-Patterns Found

None. No TODO, FIXME, placeholder comments, empty implementations, or stub returns found in any phase artifact.

### Human Verification Required

None. The module is pure-Python with deterministic logic. All behavioral truths are fully covered by the automated test suite and confirmed by `uv run pytest` output.

## Gaps Summary

No gaps. All 13 observable truths pass, all 4 artifacts are substantive and wired, 28 tests pass in 0.02s. The module is self-contained and verifiable in isolation as intended.

Key implementation details confirmed by direct code inspection:

- Bisect-based range lookup with `prefix + "~"` upper-bound handles ASCII digit/letter ordering (digits 49-57 sort before letters 65-90, so W1AW would not match WAA-WZZ without truncated comparison)
- Structural prefix extraction requires at least one digit in callsign, preventing spurious matches on strings like UNKNOWN
- _NOTFOUND sentinel correctly distinguishes "no range matched" from "range matched with iso=None" (non-country entities)
- _strip_suffix correctly identifies prefix/callsign format (EA3/G3YWX: left side shorter than right = operating prefix)

---
*Verified: 2026-04-04T20:22:50Z*
*Verifier: Claude (gsd-verifier)*
