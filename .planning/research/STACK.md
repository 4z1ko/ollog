# Technology Stack

**Project:** Ham Radio Online Logbook (ollog) — Operator & Station Profiles Milestone
**Researched:** 2026-04-04
**Scope:** NEW capabilities only. Existing validated stack (FastAPI 0.135+, Beanie 2.1+, pymongo 4.16+, HTMX 2.0.4, PyJWT, pwdlib, MongoDB 7 replica set) is not re-researched here.

---

## Stack Additions for Operator Profile Feature

This milestone adds one new Beanie Document, grid square conversion, and email
validation. No framework changes are needed. All additions are additive.

---

### New Library: Maidenhead Grid Conversion

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| maidenhead | 1.8.0 | Grid square ↔ lat/lon conversion | Pure Python, no C extensions, zero system dependencies. Two-function API: `to_maiden(lat, lon, level)` returns a grid locator string; `to_location(locator)` returns (lat, lon) tuple (southwest corner by default, `center=True` for centroid). Production/Stable classifier. Works on Python ≥ 3.9. Maintained by space-physics group. |

**Confidence:** MEDIUM — PyPI page confirms 1.8.0 released May 25, 2025. API shape (to_maiden / to_location) confirmed by multiple sources. WebFetch was unavailable to verify README directly, but the API is stable and consistent across search results.

**API in use:**
```python
import maidenhead as mh

# lat/lon -> grid (level=2 gives 4-char, level=3 gives 6-char)
grid = mh.to_maiden(lat=51.4778, lon=-0.0015, level=3)   # "IO91wm"

# grid -> lat/lon (southwest corner of square)
lat, lon = mh.to_location("IO91wm")

# grid -> center point of square
lat, lon = mh.to_location("IO91wm", center=True)
```

**Why not a custom implementation:** Maidenhead encoding has edge cases at field
boundaries and the precision arithmetic is fiddly. The library is 15 lines of
math tested by the wider ham radio community. Do not reimplement.

---

### New Library: Email Validation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| email-validator | 2.3.0 | Pydantic EmailStr backend | Required for Pydantic's `EmailStr` type to function. Without it, `from pydantic import EmailStr` raises an ImportError at runtime. Install via `pydantic[email]` to get the correct version pin. |

**Confidence:** HIGH — email-validator 2.3.0 is the current release (August 2025). Pydantic v2 requires email-validator ≥ 2.0. This is standard Pydantic ecosystem practice.

**Install path:** Add `pydantic[email]` to pyproject.toml dependencies (pydantic itself
is already a transitive dependency of FastAPI; adding the `[email]` extra is
sufficient — no separate version pin needed for email-validator).

---

### No New Libraries for MY_* Field Storage

The ADIF MY_* fields (MY_RIG, MY_ANTENNA, MY_POWER, MY_GRIDSQUARE, MY_CITY,
MY_CITY_INTL, MY_COUNTRY, MY_COUNTRY_INTL, MY_STATE, MY_LAT, MY_LON,
MY_GRIDSQUARE_EXT, MY_POTA_REF, MY_SOTA_REF, MY_IOTA, etc.) are all simple
string or numeric values. Pydantic handles validation of these as `Optional[str]`
or `Optional[float]` fields. No additional library is needed.

---

## Beanie Model Design Decision: Explicit Fields vs model_extra="allow"

**Decision: Use explicit Pydantic fields for all MY_* fields on OperatorProfile.**

Rationale:

1. **Profile is user-entered, not arbitrary:** Unlike QSO documents where operators
   can import arbitrary ADIF fields from third-party software, the profile has a
   defined, finite set of fields (the ADIF MY_* namespace). Explicit fields give
   validation, type safety, and IDE autocomplete at no cost.

2. **model_extra="allow" carries a known Beanie projection risk:** Beanie's
   default projection is derived from declared model fields. With extra="allow",
   Beanie returns `None` for the projection, fetching the full document — this is
   correct behavior but confirmed-by-source to be the mechanism. For a fixed-schema
   document like a profile, explicit fields give deterministic projection behavior.

3. **QSO uses extra="allow" correctly** because QSOs import arbitrary third-party
   ADIF fields. OperatorProfile does not need that property.

4. **All current ADIF MY_* fields are known:** ADIF 3.1.6 (current as of
   September 2025) defines a complete, enumerable MY_* field set. Explicit fields
   document the schema at the model layer.

**Exception:** If the project wants to future-proof for arbitrary MY_* fields not
yet in the spec, use `model_extra="allow"` and declare only the commonly-used ones
explicitly. This is acceptable but not the recommended default for a profile document.

---

## OperatorProfile Beanie Document: Integration Notes

**Collection:** `operator_profiles` (separate from `users` — keeps auth concern separate
from station data; allows profile upsert without touching password hash).

**User linkage:** Store `username: str` (matching `User.username`) as the lookup key.
Add a unique index on `username`. Do not use Beanie's Link type — a string foreign
key is simpler, avoids fetch-on-load overhead, and profile is always fetched alone.

**Upsert pattern:** Beanie 2.x supports `find_one(...).upsert(Set({...}), on_insert=...)`.
Use this for profile save: one round-trip, no race condition on first-time create.

**Stamping QSOs:** On new QSO creation, the router fetches the operator's profile
and stamps `OPERATOR`, `STATION_CALLSIGN`, and other MY_* fields. This is a
service-layer concern, not a model concern. Keep the profile model pure.

---

## Maidenhead Grid Validation

Use a Pydantic `field_validator` with a regex pattern rather than calling
`maidenhead.to_location()` for validation — the library raises on invalid input
but does not give clean Pydantic error messages.

Maidenhead grid format (ADIF MY_GRIDSQUARE / GRIDSQUARE field):
- 4 characters: `[A-R]{2}[0-9]{2}` (field + square, e.g., "FN31")
- 6 characters: `[A-R]{2}[0-9]{2}[a-x]{2}` (+ subsquare, e.g., "FN31pr")
- 8 characters: `[A-R]{2}[0-9]{2}[a-x]{2}[0-9]{2}` (extended, e.g., "FN31pr26")

The ADIF spec (MY_GRIDSQUARE field) accepts 4 or 6 character forms in common use.
MY_GRIDSQUARE_EXT (added in ADIF 3.1.4+) is for 8-character extended precision.

Recommended pattern for MY_GRIDSQUARE: `^[A-Ra-r]{2}[0-9]{2}([A-Xa-x]{2})?$`
(case-insensitive per ADIF spec; normalize to uppercase on save).

---

## ADIF MY_* Field Reference (ADIF 3.1.6)

Fields confirmed present in ADIF 3.1.6 specification. Group into profile
sections for the UI:

**Identity:**
- `MY_NAME` / `MY_NAME_INTL` — operator name

**Location:**
- `MY_CITY` / `MY_CITY_INTL` — city (QTH)
- `MY_STATE` — US state / subdivision
- `MY_CNTY` — US county
- `MY_COUNTRY` / `MY_COUNTRY_INTL` — DXCC entity name
- `MY_POSTAL_CODE` / `MY_POSTAL_CODE_INTL`
- `MY_STREET` / `MY_STREET_INTL`
- `MY_GRIDSQUARE` — 4 or 6 char Maidenhead
- `MY_GRIDSQUARE_EXT` — 8 char extended (ADIF 3.1.4+)
- `MY_LAT` — latitude (decimal degrees, ADIF Location type)
- `MY_LON` — longitude (decimal degrees, ADIF Location type)

**Awards / Programs:**
- `MY_CQ_ZONE` — CQ zone number
- `MY_ITU_ZONE` — ITU zone number
- `MY_DXCC` — DXCC entity code
- `MY_IOTA` — Islands on the Air reference
- `MY_SOTA_REF` — SOTA summit reference
- `MY_POTA_REF` — Parks on the Air reference (ADIF 3.1.4+)
- `MY_SIG` / `MY_SIG_INTL` / `MY_SIG_INFO` / `MY_SIG_INFO_INTL` — special interest group
- `MY_USACA_COUNTIES` — US county award
- `MY_VUCC_GRIDS` — VUCC grid squares
- `MY_FISTS` — FISTS CW club number

**Station / Equipment:**
- `MY_RIG` / `MY_RIG_INTL` — transceiver description
- `MY_ANTENNA` / `MY_ANTENNA_INTL` — antenna description (correct ADIF name; NOT MY_ANT)
- `MY_POWER` — transmit power in watts

**Note on MY_ANT vs MY_ANTENNA:** The correct ADIF field name is `MY_ANTENNA`.
Some logging software uses non-standard `MY_ANT`. Store as `MY_ANTENNA` in the
profile; the QSO stamping layer can output whichever name is needed.

**Confidence on field list:** MEDIUM — field names sourced from web search results
citing ADIF 3.1.6 and adif-mcp.com spec mirror. WebFetch to adif.org was
unavailable. Verify MY_ANTENNA vs MY_ANT against official spec before locking
the model.

---

## Recommended pyproject.toml Changes

```toml
[project]
dependencies = [
    # ... existing deps unchanged ...
    "fastapi[standard]>=0.135.0",
    "beanie>=2.1.0",
    "pymongo>=4.16.0",
    "pyjwt>=2.12.0",
    "pwdlib[argon2]>=0.3.0",
    "pydantic-settings>=2.0",
    # NEW for operator profile milestone:
    "maidenhead>=1.8.0",
    "pydantic[email]>=2.0",   # enables EmailStr; pins email-validator>=2.0
]
```

**No other dependency changes needed.**

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Grid conversion | maidenhead 1.8.0 | gridtools (miaowware) | gridtools is a smaller project with less adoption; maidenhead is the de facto standard in Python ham radio tooling |
| Grid conversion | maidenhead 1.8.0 | Custom math | Edge cases at field boundaries (e.g., longitude wrap); use the tested library |
| Email validation | pydantic[email] (EmailStr) | Manual regex | EmailStr validates deliverability-aware syntax per RFC; a regex misses subtleties |
| MY_* storage | Explicit Pydantic fields | model_extra="allow" | Profile schema is finite and known; explicit fields are better documented and avoid Beanie projection ambiguity |
| Profile collection | Separate `operator_profiles` | Embed in `users` doc | Keeps auth model clean; profile can be fetched/updated independently without touching password hash |
| Profile-to-user link | `username: str` (FK string) | Beanie `Link[User]` | Link requires eager/lazy fetch ceremony; string FK is simpler for a document that is always fetched alone |

---

## What NOT to Add

- **No geospatial index** on lat/lon — profiles are not queried by proximity; a 2dsphere index adds overhead with zero benefit for this use case.
- **No separate MY_* collection** — MY_* fields live directly on the profile document; no normalization needed.
- **No geocoding library** — lat/lon is entered by the operator or derived from Maidenhead grid; do not call external geocoding APIs.
- **No ADIF profile import** — profile fields are entered via web form, not imported from ADIF files.

---

## Sources

- maidenhead on PyPI: https://pypi.org/project/maidenhead/ (1.8.0, May 2025)
- space-physics/maidenhead GitHub: https://github.com/space-physics/maidenhead
- email-validator on PyPI: https://pypi.org/project/email-validator/ (2.3.0, August 2025)
- ADIF 3.1.6 specification: https://adif.org/316/ADIF_316.htm
- Beanie extra fields discussion: https://github.com/BeanieODM/beanie/issues/244
- Beanie upsert pattern: https://beanie-odm.dev/tutorial/updating-&-deleting/
- MY_ANTENNA field name: https://forum.log4om.com/viewtopic.php?t=5219 (confirmed MY_ANTENNA, not MY_ANT) — LOW confidence, verify against adif.org
- Maidenhead grid format: https://en.wikipedia.org/wiki/Maidenhead_Locator_System
