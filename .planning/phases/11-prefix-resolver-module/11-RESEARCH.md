# Phase 11: Prefix Resolver Module - Research

**Researched:** 2026-04-04
**Domain:** Python callsign-to-ISO-code resolver, ITU prefix range matching, pycountry integration
**Confidence:** HIGH

## Summary

Phase 11 builds a pure-Python, in-memory, zero-DB module (`app/callsign/prefixes.py`) that resolves an amateur radio callsign to an ISO 3166-1 alpha-2 country code. The core algorithm is a longest-prefix-match over the ITU Series Ranges data using Python's `bisect` module against a sorted list of `(start, end, iso_code)` tuples. No framework dependencies are needed; the module is a single file of pure functions with a static data table built at import time.

The hardest problem is name-to-ISO mapping: ITU uses names like "Germany (Federal Republic of)" which `pycountry.search_fuzzy()` handles inconsistently. The verified solution is a hand-maintained static override dict keyed on ITU name fragments, with `pycountry.countries.get(alpha_2=...)` used for exact lookups where the ISO code is already known. Non-country entities (4U, C7, 4Y) and /MM and /AM operating suffixes must be handled explicitly before lookup.

The existing codebase provides the exact pattern to follow: `app/adif/parser.py` is a pure-Python, no-dependency utility module, and `tests/test_adif_parser.py` demonstrates synchronous `pytest` tests with no DB fixtures. Phase 11 follows the same structure: module in `app/callsign/`, tests in `tests/test_prefix_resolver.py`, no async, no MongoDB.

**Primary recommendation:** Implement `app/callsign/prefixes.py` as a pure-Python module with a static sorted-range table and a static ITU-name-to-ISO override dict. Use `bisect_right` for O(log n) range lookup. Never use `search_fuzzy` to map ITU names.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `bisect` | stdlib | O(log n) range lookup over sorted list | Zero-dependency, correct, fast for ~600-row static table |
| `pycountry` | >=26.2.16 | Validate and normalize ISO codes | Already in project requirements; `countries.get(alpha_2=...)` for exact lookups only |
| Python stdlib `re` | stdlib | Callsign suffix stripping | Zero-dependency regex for /MM, /AM, /P, /7, /QRP patterns |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | >=8.0 | Unit tests | Already in dev deps; synchronous tests only, no async needed |
| `pytest.mark.parametrize` | stdlib pytest | Data-driven test cases | Ideal for the ~10+ required lookup assertions |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `bisect` sorted-range table | `dict` with all explicit prefixes | Dict requires enumerating all valid 1-3 char prefixes from ranges manually; bisect handles ranges natively |
| Static ITU-name override dict | `pycountry.search_fuzzy()` | `search_fuzzy` is non-deterministic for parenthetical names like "Germany (Federal Republic of)"; confirmed unreliable in issue #242 |
| Static Python module | MongoDB collection | ITU data is static; DB adds latency, failure modes, and test complexity with no benefit |

**Installation:**
```bash
uv add "pycountry>=26.2.16"
```

## Architecture Patterns

### Recommended Project Structure
```
app/
├── callsign/
│   ├── __init__.py          # empty
│   └── prefixes.py          # lookup_prefix() + static data, no DB deps
tests/
└── test_prefix_resolver.py  # synchronous pytest, no fixtures needed
```

No `router.py`, no `service.py`, no `models.py` needed for this phase. The module is a pure utility, not a FastAPI endpoint.

### Pattern 1: Sorted-Range Table with bisect_right

**What:** Build a sorted list of `(start_prefix, end_prefix, iso_code)` tuples at module import time. To look up a callsign, extract its base prefix, then use `bisect_right` to find the insertion point for the prefix in the `start` list, step back one, and verify the prefix falls at or before the corresponding `end`.

**When to use:** Any time you have a set of alphabetic ranges that partition a keyspace — which is exactly what the ITU Series Ranges table is.

**Example:**
```python
# Source: Python docs https://docs.python.org/3/library/bisect.html
import bisect

# _RANGES is sorted by start_prefix, built at module load from ITU data
# Each entry: (start, end, iso_code)
# e.g. ("3DA", "3DM", "SZ"), ("3DN", "3DZ", "FJ"), ("W", "W", "US")
_STARTS = [r[0] for r in _RANGES]  # parallel list for bisect

def _range_lookup(prefix: str) -> str | None:
    idx = bisect.bisect_right(_STARTS, prefix) - 1
    if idx < 0:
        return None
    start, end, iso = _RANGES[idx]
    if start <= prefix <= end:
        return iso
    return None
```

For the Eswatini/Fiji overlap: "3DA0ABC" → base prefix candidates "3DA", then "3D", then "3". bisect_right on "3DA" lands in the Eswatini range (3DA–3DM). "3DN1ABC" → "3DN" lands in the Fiji range (3DN–3DZ). The 3-character prefix is tried first (longest-match), so the overlap is resolved correctly.

### Pattern 2: Suffix Stripping Before Lookup

**What:** Split on "/" before any prefix work. Check the suffix part first for /MM and /AM (return None immediately). For all other suffixes (/P, /M, digit-only like /7, arbitrary like /QRP), discard the suffix and use the base callsign.

**When to use:** Always — apply before extracting the prefix.

**Example:**
```python
import re

_UNRESOLVABLE_SUFFIXES = frozenset({"MM", "AM"})
_DIGIT_SUFFIX = re.compile(r"^\d+$")

def _strip_suffix(callsign: str) -> str | None:
    """Return base callsign, or None if suffix makes it unresolvable."""
    if "/" not in callsign:
        return callsign
    base, suffix = callsign.rsplit("/", 1)
    suffix = suffix.upper()
    if suffix in _UNRESOLVABLE_SUFFIXES:
        return None          # /MM, /AM → unresolvable
    return base              # /P, /7, /QRP, etc. → use base
```

### Pattern 3: Longest-Prefix Extraction

**What:** For a cleaned base callsign, try decreasing-length prefix substrings (3 chars, 2 chars, 1 char) against the range table. Return the first match. This handles both single-letter allocations (W, K, F, G) and multi-char allocations (DL, JA, 3DA).

**When to use:** After suffix stripping, as the core lookup loop.

**Example:**
```python
def lookup_prefix(callsign: str) -> str | None:
    """Resolve callsign to ISO 3166-1 alpha-2, or None if unresolvable."""
    base = _strip_suffix(callsign.upper())
    if base is None:
        return None
    for length in (3, 2, 1):
        if len(base) >= length:
            result = _range_lookup(base[:length])
            if result is not None:
                return result
    return None
```

### Pattern 4: ITU Name to ISO Override Table

**What:** The ITU data uses country names that do not map cleanly to ISO 3166-1 names. Never use `pycountry.search_fuzzy()` for this. Instead, maintain a static dict mapping ITU name strings (as they appear in the raw data) to ISO alpha-2 codes.

**When to use:** During the one-time table build at module import, to convert each ITU row's country name to an ISO code.

**Example (partial):**
```python
# Source: ITU Table of International Call Sign Series + ISO 3166-1
_ITU_NAME_TO_ISO: dict[str, str] = {
    "United States of America":      "US",
    "Germany (Federal Republic of)": "DE",
    "Japan":                         "JP",
    "Eswatini":                      "SZ",   # formerly Swaziland in older ITU data
    "Fiji":                          "FJ",
    "United Kingdom of Great Britain and Northern Ireland": "GB",
    # ... all ~190 country rows from the ITU dataset
    # Non-country entities map to None sentinel or are absent:
    # "United Nations Organization" → None (4U prefix)
    # "World Meteorological Organization" → None (C7 prefix)
}
```

Non-country entities: do NOT emit an ISO code for rows where the ITU name maps to an international organization. Return `None` for those.

### Pattern 5: Module-Level Build — Static Table at Import

**What:** Parse the ITU data and build `_RANGES` and `_STARTS` once at module import time as module-level constants. No lazy initialization, no function-level caching needed.

**When to use:** For static data that never changes at runtime.

```python
# prefixes.py — top-level, runs once at import

def _build_ranges() -> list[tuple[str, str, str | None]]:
    """Build sorted (start, end, iso_or_none) list from ITU raw data."""
    rows = []
    for itu_range_str, itu_name in _ITU_RAW_DATA:
        iso = _ITU_NAME_TO_ISO.get(itu_name)   # None for non-country entities
        # Parse "WAA - WAZ" or "W" into start/end
        if " - " in itu_range_str:
            start, end = itu_range_str.split(" - ")
        else:
            start = end = itu_range_str.strip()
        rows.append((start.strip(), end.strip(), iso))
    rows.sort(key=lambda r: r[0])
    return rows

_RANGES: list[tuple[str, str, str | None]] = _build_ranges()
_STARTS: list[str] = [r[0] for r in _RANGES]
```

### Anti-Patterns to Avoid

- **Using `search_fuzzy` for ITU names:** Non-deterministic for parenthetical names. Issue #242 documents wrong result for certain country names. Use exact dict lookup instead.
- **Storing ITU data in MongoDB:** This is static reference data. DB adds latency, test complexity (requires Beanie/motor setup), and failure modes with zero benefit.
- **Trying only the 2-char prefix:** Single-letter allocations (W, K, F) require 1-char lookup. Sub-range overlaps like 3DA/3DN require 3-char lookup. Must try 3, 2, 1 in order.
- **Splitting on "/" and always using the left side:** /MM and /AM must be caught first; they make the callsign unresolvable. Check suffix before discarding it.
- **Case-sensitive comparisons:** Normalize to uppercase at the entry point of `lookup_prefix`. The ITU data is uppercase; user input may not be.
- **Async tests for pure functions:** This module has no async code. Using `pytest-asyncio` for these tests adds unnecessary complexity. Use plain `def test_*` functions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ISO country code validation | Custom country dict | `pycountry.countries.get(alpha_2=...)` | pycountry embeds iso-codes 4.20.1; covers all 249 ISO 3166-1 entries including recent renames (Eswatini, North Macedonia) |
| Binary search over sorted data | Linear scan of 600 rows | `bisect.bisect_right` | O(log n) vs O(n); stdlib, zero deps |
| Regex for suffix detection | Manual string parsing | `re` module patterns | Handles digit-only (/7, /07) and alpha (/QRP, /P, /MM) in one pass cleanly |

**Key insight:** The only genuinely custom piece in this module is the ITU-name-to-ISO override table — everything else (binary search, country validation, regex) has a stdlib or standard library solution.

## Common Pitfalls

### Pitfall 1: Overlapping Range Sub-Division (3DA–3DM vs 3DN–3DZ)

**What goes wrong:** If you only try 2-character prefixes, "3D" doesn't uniquely identify the country. Both Eswatini and Fiji start with "3D".

**Why it happens:** The ITU splits the 3D series between two countries at the third character. This is the only such split in the ~600-row table (it is an unusual case per Wikipedia ITU prefix article).

**How to avoid:** Always try 3-char prefix first. "3DA" falls in 3DA–3DM (Eswatini). "3DN" falls in 3DN–3DZ (Fiji). The bisect range-check correctly distinguishes them when 3 chars are used.

**Warning signs:** Test `lookup_prefix("3DA0ABC")` returns "SZ" AND `lookup_prefix("3DN1ABC")` returns "FJ". If both return the same value, the 3-char path is broken.

### Pitfall 2: /MM and /AM Treated as Portable Suffixes

**What goes wrong:** If you strip all suffixes and use the base callsign, "G3YWX/MM" becomes "G3YWX" and resolves to "GB" instead of returning None.

**Why it happens:** /MM (maritime mobile) and /AM (aeronautical mobile) are documented as "unresolvable" in the requirements because the callsign is not associated with a land-based ITU allocation during that operation. Additionally, "MM" is also a valid prefix for Scotland and "AM" for Spain, which would cause false positives.

**How to avoid:** Check the suffix before discarding it. `_UNRESOLVABLE_SUFFIXES = frozenset({"MM", "AM"})`. Return None immediately.

**Warning signs:** `lookup_prefix("G3YWX/MM")` should return None. If it returns "GB" or "ES", the suffix check is missing or wrong.

### Pitfall 3: pycountry search_fuzzy Returning Wrong Country

**What goes wrong:** `pycountry.countries.search_fuzzy("Germany (Federal Republic of)")` may return Germany correctly in some versions but is documented as unreliable for names with parenthetical qualifiers. Issue #242 shows wrong results for similar historic-name searches.

**Why it happens:** `search_fuzzy` uses tokenized matching, not exact string comparison. Parenthetical words can confuse the ranking.

**How to avoid:** Never call `search_fuzzy` with ITU name strings. Use the static `_ITU_NAME_TO_ISO` override table built once from the ITU dataset. All ~190 country mappings must be in this table explicitly.

**Warning signs:** If you call `search_fuzzy` anywhere in the prefix module, the test suite may pass locally but fail when pycountry updates its data or scoring algorithm.

### Pitfall 4: Missing Single-Letter Prefix Coverage

**What goes wrong:** Some of the most common callsigns (W1AW, K5X, F5ZZZ) use single-letter prefixes (W, K, F). If the lookup only tries 2+ char prefixes, these all return None.

**Why it happens:** The ITU allocates entire letter series to major countries. "W" alone covers all W-prefix callsigns for the USA. The range is "WAA–WZZ" or similar; extracting 2 chars gives "W1" which may not be in the table.

**How to avoid:** The longest-prefix-match loop must include length 1: `for length in (3, 2, 1)`. Also verify that the range table correctly captures single-letter entries.

**Warning signs:** `lookup_prefix("W1AW")` returns None instead of "US".

### Pitfall 5: Non-Country Entity Returns Wrong ISO Code

**What goes wrong:** "4U" is allocated to the United Nations. If you map it to an ISO code (e.g. "CH" for Switzerland because 4U1ITU operates from Geneva), that is incorrect per PRFX-04.

**Why it happens:** The ITU data lists the UN organization name, not a country name. A naive name-to-ISO lookup might fall back to Switzerland or return a garbage match.

**How to avoid:** In `_ITU_NAME_TO_ISO`, explicitly map organization names to `None`. The range-lookup function returns `None` when iso is `None`. Document which entries are intentionally None.

**Warning signs:** `lookup_prefix("4U1ITU")` should return None. If it returns "CH" or any other ISO code, non-country filtering is broken.

### Pitfall 6: Case-Sensitivity in Lookup

**What goes wrong:** `lookup_prefix("w1aw")` or `lookup_prefix("dl1abc")` returns None because the comparison is case-sensitive.

**Why it happens:** User callsign input or ADIF data may be mixed case. The ITU range table is uppercase.

**How to avoid:** Normalize to uppercase at the entry point: `callsign = callsign.upper()` as the first line of `lookup_prefix`.

**Warning signs:** Tests pass with uppercase inputs but fail with lowercase.

## Code Examples

Verified patterns from official sources:

### bisect_right for range lookup
```python
# Source: https://docs.python.org/3/library/bisect.html
import bisect

breakpoints = [60, 70, 80, 90]
grades = "FDCBA"

def grade(score):
    i = bisect.bisect_right(breakpoints, score)
    return grades[i]
# score=85 → bisect_right finds i=3 → grade "B"

# Applied to ITU ranges:
# _STARTS = ["3DA", "3DN", "DL", "F", "G", "JA", "K", "W", ...]
# bisect_right(_STARTS, "3DA") - 1 → index 0 → check 3DA <= "3DA" <= 3DM ✓
# bisect_right(_STARTS, "3DN") - 1 → index 1 → check 3DA <= "3DN" <= ... no, check _RANGES[1]
```

### pycountry exact lookup (safe)
```python
# Source: pycountry README https://github.com/pycountry/pycountry/blob/main/README.rst
import pycountry

# SAFE: exact alpha_2 lookup
country = pycountry.countries.get(alpha_2="US")
# Returns Country(alpha_2='US', alpha_3='USA', name='United States', ...)

# SAFE: exact name lookup
country = pycountry.countries.get(name="Germany")
# Returns Country(...)

# UNSAFE for ITU names:
# pycountry.countries.search_fuzzy("Germany (Federal Republic of)")
# — do NOT use this for ITU name mapping
```

### pytest.mark.parametrize for data-driven prefix tests
```python
# Source: pytest docs https://docs.pytest.org/en/stable/
import pytest
from app.callsign.prefixes import lookup_prefix

@pytest.mark.parametrize("callsign,expected", [
    ("W1AW",      "US"),
    ("DL1ABC",    "DE"),
    ("JA1YWX",   "JP"),
    ("3DA0ABC",   "SZ"),   # Eswatini
    ("3DN1ABC",   "FJ"),   # Fiji
    ("G3YWX/MM",  None),   # maritime mobile
    ("G3YWX/AM",  None),   # aeronautical mobile
    ("W1AW/P",    "US"),   # portable — base callsign used
    ("W1AW/7",    "US"),   # area suffix — base callsign used
    ("W1AW/QRP",  "US"),   # self-assigned suffix — base callsign used
    ("4U1ITU",    None),   # non-country UN entity
    ("UNKNOWN",   None),   # unrecognized prefix
])
def test_lookup_prefix(callsign, expected):
    assert lookup_prefix(callsign) == expected
```

### Suffix-stripping pattern
```python
# Pure Python, no deps
import re

_UNRESOLVABLE = frozenset({"MM", "AM"})
_DIGIT_RE = re.compile(r"^\d+$")

def _strip_suffix(callsign: str) -> str | None:
    """Return base callsign or None for unresolvable suffixes."""
    if "/" not in callsign:
        return callsign
    base, _, suffix = callsign.rpartition("/")
    if suffix.upper() in _UNRESOLVABLE:
        return None
    return base   # /P, /M, /7, /QRP → ignore suffix
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `search_fuzzy` for all name lookups | Static override dict for ITU names | pycountry issue #242 (2024) | Reliability: `search_fuzzy` returns wrong results for parenthetical names |
| `pyhamtools` full library (Clublog/ARRL data) | Custom static ITU ranges module | Phase 11 decision | This project uses the raw ITU Series Ranges table; pyhamtools adds non-ITU complexity |
| pycountry 24.6.1 | pycountry 26.2.16 | Feb 2026 | Dropped Python 3.8/3.9; added initials matching in search_fuzzy; upgraded to iso-codes 4.20.1 |

**Deprecated/outdated:**
- `pycountry.search_fuzzy()` for ITU name resolution: Unreliable for names with parenthetical qualifiers; do not use.
- `pyhamtools`: Supports Clublog and QRZ data sources, not the raw ITU Series Ranges table used in this project.

## Open Questions

1. **Exact format of the user-provided ITU dataset**
   - What we know: Phase context says "WAA - WAZ,United States of America" (~600 rows), user already provided the full dataset
   - What's unclear: Whether rows are stored as a `.csv`, inline Python list, or separate data file; exact column separator; whether all ~600 rows are countries or include maritime/aeronautical allocations that also need None treatment
   - Recommendation: Planner should specify that the first task is to audit the raw dataset format and build the `_ITU_RAW_DATA` list structure accordingly. The static override dict (`_ITU_NAME_TO_ISO`) will need to cover every unique country name in the dataset.

2. **Whether to embed ITU data inline or as a data file**
   - What we know: The phase says "in-memory static Python module"; existing project has no data file precedent
   - What's unclear: 600 rows inline in a Python list vs. a bundled `.csv` read at import time
   - Recommendation: Inline Python list of tuples is simpler (no file I/O, no path resolution), consistent with a pure-Python module. Use a `_ITU_RAW_DATA: list[tuple[str, str]]` constant at the top of `prefixes.py`.

3. **Whether Eswatini appears as "Eswatini" or "Swaziland" in the user's dataset**
   - What we know: Swaziland renamed to Eswatini in 2018; ITU updated its records but older datasets may still say "Swaziland"
   - What's unclear: Which name appears in the user-provided data
   - Recommendation: Map both "Swaziland" and "Eswatini" to "SZ" in the override dict as a safety measure.

## Sources

### Primary (HIGH confidence)
- Python stdlib docs https://docs.python.org/3/library/bisect.html — bisect_right range-lookup pattern, grade example
- pycountry README https://github.com/pycountry/pycountry/blob/main/README.rst — search_fuzzy description, `countries.get` usage
- pycountry HISTORY.txt https://github.com/pycountry/pycountry/blob/main/HISTORY.txt — version 26.2.16 changelog, confirmed search_fuzzy limitations in #242
- Wikipedia ITU prefix https://en.wikipedia.org/wiki/ITU_prefix — 3DA-3DM (Eswatini) / 3DN-3DZ (Fiji) split documented; 4U, C7, 4Y as international organization entries
- Existing codebase `app/adif/parser.py` — pure-Python module pattern to follow directly
- Existing codebase `tests/test_adif_parser.py` — synchronous pytest pattern without DB fixtures

### Secondary (MEDIUM confidence)
- Wikipedia Amateur radio call signs https://en.wikipedia.org/wiki/Amateur_radio_call_signs — /MM, /AM conflict with M (England), MM (Scotland), AM (Spain) prefixes; /P, /7 suffix meanings
- m7spi.co.uk callsign suffixes https://www.m7spi.co.uk/use-of-callsigns-and-suffixes/ — /A, /M, /MM, /AM, /P suffix table with purposes; confirms /MM = maritime mobile
- pycountry issues https://github.com/pycountry/pycountry/issues/242 — wrong result from search_fuzzy for country name edge cases

### Tertiary (LOW confidence)
- eham.net 4U1 article https://www.eham.net/article/23104 — 4U1ITU/4U1UN/4U1WB/4U1VIC are United Nations/ITU entities; confirms non-country nature of 4U prefix (not independently verified against ITU official table)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — bisect and pycountry are stdlib/well-documented; project pyproject.toml confirms existing deps; adif module confirms pure-Python pattern is established in this codebase
- Architecture: HIGH — directly mirrors `app/adif/parser.py` structure; no novel patterns required
- Pitfalls: HIGH for /MM and bisect range logic (verified by requirements + Wikipedia); MEDIUM for pycountry search_fuzzy unreliability (documented in issue tracker, confirmed by HISTORY.txt entry)
- ITU data format: MEDIUM — phase context describes format as "WAA - WAZ,United States of America" but exact file/structure is not yet seen; one open question remains

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (pycountry is stable; ITU data is static reference data)
