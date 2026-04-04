# Feature Research: Callsign Entity Lookup & Country Flag Display

**Domain:** Ham radio QSO logbook — v1.2 milestone: ITU callsign prefix→country resolution + flag icons in log view
**Researched:** 2026-04-04
**Confidence:** HIGH for core lookup behavior; MEDIUM for suffix/edge-case handling (community-consensus patterns, not a single authoritative spec)

---

## Scope Note

This document covers ONLY what is new in v1.2. The existing feature set is already built
and tested. Key constraints from the existing codebase:

- `qso_row.html`: callsign rendered as `{{ qso.CALL }}` in a plain `<td>` — flag goes here
- `feed_row.html`: callsign rendered as `<strong>{{ call }}</strong>` — separate template, flag opportunity
- `_qso_to_view_dict()` in `ui_router.py`: builds the dict passed to templates; flag data injected here
- `QSO.CALL`: stored verbatim as typed by the operator — may include suffixes like `/P`, `/MM`
- Flag SVGs: 271 ISO 3166-1 alpha-2 files already present at `app/static/flags/{code}.svg`
- ITU prefix data: ranges provided directly (e.g., `WAA–WAZ → United States`, `3DA–3DM → Eswatini`)
- No QSO data is stored; flag display is purely a render-time decoration

---

## How Callsign Prefix→Country Lookup Works in Ham Radio

### The ITU Allocation Model (HIGH confidence)

The ITU allocates blocks of prefix ranges to administrations (countries). Prefixes are
1–3 character alphanumeric strings. Ranges can be:

- **Single-letter blocks**: "K" → United States (full block)
- **Two-letter ranges**: "AAA–ALZ" → United States; "EA" → Spain (each needs ≥2 chars because the letter block is split among countries)
- **Three-character sub-ranges**: "3DA–3DM" → Eswatini; "3DN–3DZ" → Fiji (sub-ranges required because a 2-char prefix is shared)

The range boundary comparison is **lexicographic on the prefix characters**. A callsign like
`3DA0JK` has prefix `3DA`; it falls in `3DA–3DM`, so it resolves to Eswatini. A callsign
`3DM0AB` also falls in that range. A callsign `3DN5XY` falls in `3DN–3DZ`, so it resolves
to Fiji.

### Standard Matching Algorithm: Longest ITU Prefix Match (HIGH confidence)

This is the universally-adopted approach across ham radio logging software (N1MM+, Log4OM,
pyhamtools, DXCC command-line tools, cty.dat-based utilities):

1. **Strip operating suffixes** from the CALL field (see Suffix Handling below)
2. **Extract the base callsign** (the portion before any slash, or the whole call if no slash)
3. **Try progressively shorter prefixes** starting from the full base callsign down to 1 character
4. **Return the first (longest) match** found in the prefix range table

For the ITU prefix range table used in this project (not cty.dat, but the ITU Series Ranges
data with `start–end` format), the matching logic is:

```
For prefix_length in [len(base_call), len(base_call)-1, ..., 1]:
    candidate = base_call[:prefix_length]
    if any range where range.start <= candidate <= range.end:
        return that range's country
return None
```

This works because ITU ranges use lexicographic ordering and the data already encodes the
sub-range structure (e.g., `3DA–3DM` covers all strings ≥ `3DA` and ≤ `3DM`).

### Why Not Exact-Prefix Lookup (MEDIUM confidence)

A simple dict lookup (prefix → country) is insufficient because:
- ITU data is given as ranges, not enumerated individual prefixes
- Sub-ranges like `3DA–3DM` vs `3DN–3DZ` require range comparison
- A callsign `3DA0JK` would need to match `3DA` as the relevant prefix, not `3D` (which is unallocated as a standalone)
- The longest-match approach naturally resolves this without pre-expanding ranges

---

## Suffix Handling: Operating Indicators on Callsigns (MEDIUM confidence)

Operators log callsigns with suffixes appended via `/`. The suffix changes the operational
context but NOT the country of origin for the base callsign (unless the suffix is itself a
valid country prefix for a different operation).

### Standard Suffixes to Strip (no country change)

| Suffix | Meaning | Action |
|--------|---------|--------|
| `/P` | Portable operation | Strip; use base call |
| `/M` | Mobile operation | Strip; use base call |
| `/A` | Alternative licensed address | Strip; use base call |
| `/QRP` | Low-power self-identification | Strip; use base call |
| `/LH` | Lighthouse activation (non-standard) | Strip; use base call |
| `/R` | Relay/repeater (rare in QSO logging) | Strip; use base call |
| `/B` | Beacon station | Strip; use base call |

### Suffixes That ARE Country Prefixes (Complex — MEDIUM confidence)

Some suffixes are themselves valid ITU country prefixes. These indicate a **guest operation**
from another country — the prefix used over the air is the foreign prefix, not the home call.

| Suffix | Example | Meaning |
|--------|---------|---------|
| `/MM` | `G3YWX/MM` | Maritime Mobile — NOT Scotland (**M** is England, **MM** is Scotland conflict) |
| `/AM` | `EA5XY/AM` | Aeronautical Mobile — NOT Spain (**AM** is Spain conflict) |
| Numeric only, e.g., `/7` | `W6ABC/7` | US call area indicator — different US district, same country |
| Valid foreign prefix, e.g., `/VP9` | `G3YWX/VP9` | Operating from Bermuda — country changes to Bermuda |

**Practical rule for v1.2 (LOW complexity, covers 99% of cases):**

Strip any suffix that is:
- A known non-location indicator: `/P`, `/M`, `/A`, `/QRP`, `/MM`, `/AM`, `/LH`, `/R`, `/B`
- A single digit (call area indicator within same country)

Use the base callsign (part before the last `/`) for prefix lookup. If the suffix is
longer than 2 characters and not in the known-strip list, it may be a foreign prefix —
but this edge case (guest operations logged with `/VP9` style suffixes) is uncommon enough
that a "no match found → no flag" graceful fallback is the correct v1.2 behavior.

### The /MM and /AM Ambiguity (HIGH confidence — known domain gotcha)

`/MM` conflicts with the ITU prefix `MM` (Scotland). `G3YWX/MM` is a British station
operating maritime mobile, NOT a Scottish callsign. Similarly `/AM` conflicts with `AM`
(Spain). The standard industry resolution: when the suffix is exactly `MM` or `AM`, treat it
as an operational indicator (maritime mobile / aeronautical mobile) and look up the BASE
call, not the suffix.

---

## Table Stakes

Features operators expect from callsign entity display. Missing these = product feels broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Country flag icon next to callsign in log view | Every major logger (Ham Radio Deluxe, Log4OM, GridTracker, CloudLog) shows a flag beside the callsign in the log table | LOW | SVGs already present; inject `iso_code` via `_qso_to_view_dict()`; render with `<img>` in `qso_row.html` |
| Graceful fallback when prefix unknown | No flag shown, no error, no broken layout | LOW | `iso_code = None` → template skips `<img>` entirely; no placeholder needed |
| Flag lookup at render time (server-side) | Stateless rendering; no AJAX round-trips for individual rows | LOW | Prefix resolver called in `_qso_to_view_dict()`; result passed as template context variable |
| Correct flag for common DX callsigns | W, K, N, VE, G, DL, F, JA, VK, ZL resolve correctly | LOW | Covered by ITU prefix table and longest-match algorithm |
| Handle callsign entered in uppercase | ADIF CALL field is convention uppercase; `build_qso_dict()` already uppercases CALL | LOW | Resolver operates on uppercase input; no lowercasing needed |
| Paginated log view unchanged in structure | Existing sort/filter/pagination must continue to work | LOW | Flag is additive to `qso_row.html`; no table structure changes required |

---

## Differentiators

Features that improve the product beyond baseline expectations.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Country name tooltip on flag | Hovering the flag shows full country name (e.g., "United States") | LOW | `title` attribute on `<img>`; no JS needed; country name already in prefix table data |
| Consistent flag size / styling | Small, uniform flag icons that don't break table row height | LOW | CSS `width: 20px; height: auto; vertical-align: middle;` or similar; SVG scales cleanly |
| Flag also in SSE live feed rows | New QSOs appearing in the shared station feed show the flag too | MEDIUM | `feed_row.html` uses plain variables not a QSO dict; resolver would need to be called in feed manager or SSE push path |

---

## Anti-Features

Features to explicitly NOT build in v1.2.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Store `DXCC_COUNTRY` or `ISO_CODE` in the QSO document | Country attribution can change (prefix reassignments, entity splits); storing it bakes in a point-in-time answer that may become wrong and adds migration complexity | Resolve at render time from the live prefix table; never persist to QSO data |
| Per-callsign manual country override | Operator-managed exceptions for rare edge cases (special allocations, vanity prefix ops) add UI surface and data model complexity for an extremely rare case | Graceful "no flag" fallback handles unresolvable calls cleanly |
| External callsign API integration (QRZ, HamQTH, hamcall.net) | These have rate limits, subscriptions, and external network dependencies; inappropriate for a self-hosted single-instance logger | Use the ITU prefix table only; external callbook lookup is explicitly deferred to v2 per PROJECT.md |
| DXCC entity numbering / CQ zone / ITU zone derivation | These require cty.dat or equivalent and add significant data complexity; out of scope per PROJECT.md | Deferred to v2 |
| Flag in ADIF export | Flags are display decoration only; no ADIF field exists for flag or ISO code; exporting them would break ADIF compliance | ADIF export unchanged; flag is a render-time artifact |
| "New country" / DXCC worked indicator | Award tracking requires a persistent "worked" database per operator; adds model complexity | Deferred to v2 per PROJECT.md |
| Animated flag or interactive flag click (opens QRZ profile) | Adds JS complexity; external link may not load in self-hosted deployments; QRZ is a subscription service | Static SVG with `title` tooltip is sufficient for v1.2 |

---

## Feature Dependencies

```
ITU prefix table (seed data or static Python dict)
    └──required by──> Prefix resolver function
                          └──called by──> _qso_to_view_dict() in ui_router.py
                                              └──produces──> iso_code, country_name in template context
                                                                 └──consumed by──> qso_row.html (log view)
                                                                                  qso_row_edit.html (inline edit, optional)

Prefix resolver
    └──needs──> Suffix stripper (strip /P, /M, /MM, /AM, digits)
    └──needs──> Range comparator (lexicographic: start <= candidate <= end)

Flag SVGs (already present at app/static/flags/{iso_code}.svg)
    └──consumed by──> qso_row.html via <img src="/static/flags/{{ iso_code }}.svg">
```

### Dependency Notes

- **Prefix resolver requires suffix stripper:** CALL field may contain `/P`, `/M` etc.; resolver must strip before attempting prefix match.
- **Resolver requires range comparator:** ITU data is expressed as ranges, not enumerated prefixes; lexicographic comparison against `(start, end)` tuples is required.
- **`_qso_to_view_dict()` is the correct injection point:** It already prepares the dict for all log-view templates; adding `iso_code` and `country_name` here requires no changes to the service layer, models, or database.
- **`qso_row.html` for log view; `feed_row.html` for SSE feed:** These are separate templates. Flag in the feed is a differentiator (not table stakes); defer if complexity warrants.
- **`qso_row_edit.html` (inline edit row):** May also need to show the flag or at minimum preserve it across the edit/cancel cycle; check template structure.

---

## MVP Definition

### Launch With (v1.2)

Minimum viable set — validates the feature delivers value.

- [ ] Prefix resolver module: suffix stripping + range-aware lookup → `(country_name, iso_code) | None`
- [ ] ITU prefix range data loaded into the resolver (static Python dict or MongoDB collection seeded at startup)
- [ ] `_qso_to_view_dict()` extended to call resolver and include `iso_code` and `country_name` in output dict
- [ ] `qso_row.html` updated to render flag `<img>` when `iso_code` is present, silent when absent
- [ ] `country_name` surfaced as `title` tooltip attribute on the flag `<img>`
- [ ] Graceful no-flag path verified (unknown prefix, empty CALL, malformed callsign → no error)

### Add After Validation (v1.x)

- [ ] Flag in SSE live feed rows (`feed_row.html`) — requires resolver call in SSE push path
- [ ] Flag in inline-edit row (`qso_row_edit.html`) if it disappears during edit/cancel cycle

### Future Consideration (v2+)

- [ ] DXCC "worked before" indicator (requires per-operator worked-entity tracking)
- [ ] CQ zone / ITU zone derivation
- [ ] cty.dat-based full DXCC entity lookup
- [ ] Award tracking (DXCC, WAS, WAZ, IOTA)

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Flag icon in log view | HIGH | LOW | P1 |
| Country name tooltip | HIGH | LOW | P1 |
| Graceful no-flag fallback | HIGH | LOW | P1 |
| Suffix stripping (/P, /M, /MM, /AM, digits) | HIGH | LOW | P1 |
| Resolver seeded from ITU range table | HIGH | MEDIUM | P1 |
| Flag in SSE live feed | MEDIUM | MEDIUM | P2 |
| Flag in inline edit row | LOW | LOW | P2 |
| Per-callsign override | LOW | HIGH | P3 |

---

## Ham Radio Domain Gotchas

These are specific to the amateur radio domain and not obvious from general web app patterns.

### 1. The /MM and /AM Suffix Conflict

`G3YWX/MM` is a British station operating maritime mobile — NOT a Scottish station (MM = Scotland).
`EA5XY/AM` is a Spanish station operating aeronautical mobile — NOT a Spanish call resolving via the AM prefix (AM = Spain).
Strip these suffixes before lookup; do not attempt to use them as a country prefix.

### 2. Single-Digit Suffixes Are Call Area Indicators, Not Country Changes

`W6ABC/7` is a US station operating in call area 7 (Pacific Northwest), NOT a different country.
`VE7BC/3` is a Canadian station in Ontario call area, NOT a different country.
Strip single-digit suffixes before lookup; they do not change country.

### 3. Callsigns With No Number (Rare But Valid)

Some UK special event and club callsigns omit the numeric separator: `GB2HQ`, `GX4BJC`.
The standard ITU structure (letters, then digit, then letters) does not hold for these.
Longest-prefix match on progressively shorter substrings still works correctly: `GB` matches
the UK range in the ITU table.

### 4. The 3DA–3DM / 3DN–3DZ Sub-Range Example

Both Eswatini and Fiji share the `3D` two-character prefix. The ITU resolves this by allocating
sub-ranges at the third character. A callsign `3DA0JK` must be matched at 3-character prefix
granularity (`3DA`) to land in the correct range `3DA–3DM`. A 2-character lookup for `3D`
alone is ambiguous and must not be used as the final answer.
Longest-match with range comparison handles this correctly by preferring the 3-character match.

### 5. US Callsigns: Multiple Valid Prefixes

The US holds: `AA–AL`, `K`, `N`, `W` (full single-letter blocks), plus `KA–KZ`, `NA–NZ`,
`WA–WZ`. All of these resolve to United States. The longest-match algorithm will correctly
match `W6ABC` to `W` (or `WA`–`WZ` if the data includes those sub-ranges).

### 6. Special Prefixes With No ISO Country Code

| Prefix | Entity | ISO Code | Note |
|--------|--------|----------|------|
| `1A` | Sovereign Military Order of Malta | None (not a UN member state) | No flag SVG; graceful fallback |
| `4U1ITU` | ITU Geneva | None | No ISO alpha-2; graceful fallback |
| `4U1UN` | United Nations NY | None | No ISO alpha-2; graceful fallback |

These will return a country name but no valid ISO alpha-2 → no flag shown, no error.
The country name is still useful for tooltip display even without a flag.

### 7. Callsigns From Entities Not in ISO 3166-1 alpha-2

Some DXCC entities recognized for amateur radio purposes are not UN-recognized states and
have no ISO 3166-1 alpha-2 code (and thus no flag SVG in the existing set):
- Kosovo (DXCC entity Z6; ISO code XK exists in practice but is not officially assigned)
- Various dependent territories may use their parent country's ISO code in flag collections

The resolver should return `iso_code = None` when the country name has no ISO mapping;
the template renders no flag without error.

---

## Sources

| Source | Confidence | Use |
|--------|------------|-----|
| [ITU Table of International Call Sign Series (Appendix 42)](https://www.itu.int/en/ITU-R/terrestrial/fmd/Pages/call_sign_series.aspx) | HIGH | Authoritative ITU prefix range allocations |
| [ITU prefix — Wikipedia](https://en.wikipedia.org/wiki/ITU_prefix) | HIGH | Prefix structure, range examples, sub-range explanation |
| [Amateur radio call signs — Wikipedia](https://en.wikipedia.org/wiki/Amateur_radio_call_signs) | HIGH | Callsign structure, suffix conventions, international operating |
| [Portable operation (amateur radio) — Wikipedia](https://en.wikipedia.org/wiki/Portable_operation_(amateur_radio)) | HIGH | /P, /M, /A suffix semantics |
| [pyhamtools on GitHub](https://github.com/dh1tw/pyhamtools) | MEDIUM | Industry reference: Python callsign-to-country library using longest-prefix-match approach |
| [hamradio on PyPI](https://pypi.org/project/hamradio/) | MEDIUM | cty.dat-based Python lookup; confirms longest-match is standard |
| [Ham-Locator on GitHub](https://github.com/SheldonT/Ham-Locator) | MEDIUM | Example of flag + city + country display in log table (visual UX confirmation) |
| [Ham Radio Deluxe Country List docs](https://support.hamradiodeluxe.com/support/solutions/articles/51000052697-the-hrd-country-list) | MEDIUM | Confirms country list display is standard in logging software |
| [/MM and /AM conflict note — river.cat](https://river.cat/radio/mobile-or-portable.html) | MEDIUM | /MM vs MM Scotland, /AM vs AM Spain ambiguity — documented community pattern |
| Existing ollog codebase inspection | HIGH | Template structure, `_qso_to_view_dict()`, flag SVG inventory, QSO model |

---
*Feature research for: ollog v1.2 — callsign entity lookup & country flag display*
*Researched: 2026-04-04*
