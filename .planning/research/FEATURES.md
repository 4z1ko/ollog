# Feature Landscape: Operator & Station Profile

**Domain:** Ham radio QSO logbook — per-operator profile with ADIF MY_* field storage and QSO auto-stamping
**Researched:** 2026-04-04
**Overall confidence:** MEDIUM-HIGH (ADIF spec verified via multiple search cross-checks; app-specific behavior MEDIUM; ADIF 3.1.7 field list assembled from 3.1.4 spec + 3.1.6/3.1.7 change notes since direct page fetch was unavailable)

---

## Scope Note

This document covers only what is NEW in this milestone. The existing feature set
(QSO logging, ADIF import/export, auth, admin, SSE feed) is already built and tested.
The codebase has been inspected. Key prior decisions that constrain this milestone:

- `User` document: `username`, `hashed_password`, `callsign`, `role`, `enabled` — no profile fields yet
- `QSO` document: uses `extra="allow"` — any ADIF field stored verbatim in MongoDB
- `build_qso_dict()`: injects `_operator` (login callsign) but does NOT inject MY_* fields
- `_qso_to_adif_dict()`: already passes all `model_extra` fields through to export verbatim — no export changes needed once fields are stored on QSOs
- Serializer: uses UTF-8 byte counting for ADIF field lengths — correct for MY_NAME, MY_CITY with non-ASCII characters

---

## OPERATOR vs STATION_CALLSIGN: The Core Distinction

This is the most important conceptual design decision in the milestone. Confusion between
these two fields is a documented, recurring operator problem (confirmed by HAMRS community
thread on Field Day logging and N1MM+ documentation).

**OPERATOR** (ADIF field) — The callsign of the person physically at the controls. In ollog,
this is always the login callsign — `User.callsign` pulled from the authenticated session.
This is already injected by `build_qso_dict()` as `_operator`; it needs to be surfaced as
the ADIF field `OPERATOR` in QSO records going forward.

**STATION_CALLSIGN** (ADIF field) — The callsign transmitted over the air; what the other
station logged you as. Equals OPERATOR for a typical solo home station. Differs when:

- Club activations: STATION_CALLSIGN = club call (e.g., W1AW), OPERATOR = member's personal call
- Special event stations: STATION_CALLSIGN = event call (e.g., G100RSGB), OPERATOR = member's call
- POTA/SOTA club activations: POTA documentation explicitly mandates STATION_CALLSIGN = club call, OPERATOR = individual operator for each QSO
- Operating portable under a host license (less common in US, more common internationally)

**ADIF spec rule (HIGH confidence):** If STATION_CALLSIGN is absent from a QSO record,
OPERATOR shall be treated as both the logging station's callsign and the logging
operator's callsign. The default case — solo operator, STATION_CALLSIGN left blank in
profile — is spec-compliant by omission. Only stamp STATION_CALLSIGN on QSOs when it
is explicitly set in the profile and differs from OPERATOR.

**N1MM+ implementation (HIGH confidence):** N1MM+ stores OPERATOR per-QSO (changes with
the `OPON` command for multi-op) and STATION_CALLSIGN from "Change Your Station Data."
This is the canonical model ollog should follow.

---

## Table Stakes

Features operators expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Profile storage per operator | Every logger (HRD, Log4OM, N1MM+, CloudLog) has a "My Station" settings page | Low | New `Profile` MongoDB document linked to `User.callsign` |
| Operator callsign display | Login call is the ADIF OPERATOR field; operators expect to see it on their profile | Low | Read from `User.callsign`; not editable here (login identity) |
| STATION_CALLSIGN (over-the-air call) | Required for club, portable, and special-event ops; POTA club logs mandate it | Low | Optional field; blank defaults to OPERATOR callsign per ADIF spec |
| Operator name (MY_NAME) | Used on QSL cards, displayed in HRD / CloudLog profile pages | Low | Free-text string; single field |
| QTH city (MY_CITY) | Standard location field in every logger | Low | Free-text; no enum enforcement needed |
| State/province (MY_STATE) | Required for ARRL WAS and many other award submissions | Low | Free-text; no enum needed for MVP |
| Country (MY_COUNTRY) | Standard DXCC-origin field | Low | Free-text DXCC entity name, not ISO code |
| Maidenhead grid locator (MY_GRIDSQUARE) | Mandatory for FT8/WSJT-X operation, VHF contests, POTA spot maps | Low | Accept 4, 6, or 8 chars; store verbatim; 6-char is the practical minimum |
| Decimal latitude and longitude (MY_LAT, MY_LON) | Used for distance/azimuth calculations; expected by DX-focused operators | Medium | Optional; can be auto-computed from grid (6-char → center of grid square) |
| Rig description (MY_RIG) | Operators log rig for QSL accuracy and award purposes; every logger surfaces this | Low | Free-text; "Icom IC-7300" or "Elecraft K3/100" style |
| Antenna description (MY_ANT) | Logged alongside rig in virtually all loggers | Low | Free-text; "80m doublet at 30ft" style |
| Default transmit power (stamped as TX_PWR) | Logged for QRP certificates, POTA, LOTW; virtually every logger has a power field | Low | Numeric watts, stored as string per ADIF convention; see power field note below |
| Auto-stamp OPERATOR on new QSOs | Core feature motivation; OPERATOR ADIF field must appear in each QSO | Low-Med | Inject in `build_qso_dict()` from authenticated callsign |
| Auto-stamp STATION_CALLSIGN on new QSOs | Required for club/event stations to produce valid ADIF | Low-Med | Only stamp when profile value is non-blank and differs from OPERATOR |
| Auto-stamp MY_GRIDSQUARE on new QSOs | Expected by WSJT-X users and POTA activators | Low | Only stamp when profile gridsquare is non-blank |
| Auto-stamp MY_RIG, MY_ANT, TX_PWR on new QSOs | Standard "station defaults" behavior in HRD, Log4OM, N1MM+ | Low | Only stamp when profile values are non-blank |
| Profile settings UI page | Operators must be able to view and edit their profile between sessions | Medium | HTMX form at `/profile`; consistent with existing QSO UI style |
| Profile persists across sessions | State must survive login/logout | Low | Stored in MongoDB; loaded on each request via callsign lookup |

---

## Complete ADIF MY_* Field Set (ADIF 3.1.7, 2026-03-22)

Confidence: MEDIUM. Assembled from ADIF 3.1.4 annotated specification (highest-quality source
found via search), plus ADIF 3.1.6 and 3.1.7 change summaries from search results. Direct
page fetch of adif.org.uk/317/ADIF_317.htm was unavailable. Cross-checked across multiple
search result snippets for consistency.

### Location Fields
| ADIF Field | Data Type | Description | Profile Priority |
|------------|-----------|-------------|-----------------|
| MY_CITY | String | Logging station city | Table stakes |
| MY_CITY_INTL | IntlString | MY_CITY in international (UTF-8) encoding | Skip (INTL variants deferred) |
| MY_CNTY | String | Secondary administrative subdivision (US county, German Kreis, Russian Oblast, etc.) | Optional |
| MY_CNTY_ALT | String | Alternate county designation (added ADIF 3.1.6) | Skip |
| MY_COUNTRY | String | Logging station country — DXCC entity name | Table stakes |
| MY_COUNTRY_INTL | IntlString | MY_COUNTRY in UTF-8 | Skip |
| MY_STATE | String | Primary administrative subdivision (state, province, Bundesland, etc.) | Table stakes |
| MY_STREET | String | Logging station street address | Optional |
| MY_STREET_INTL | IntlString | MY_STREET in UTF-8 | Skip |
| MY_POSTAL_CODE | String | Logging station postal/ZIP code | Optional |
| MY_POSTAL_CODE_INTL | IntlString | MY_POSTAL_CODE in UTF-8 | Skip |

### Grid and Coordinates
| ADIF Field | Data Type | Description | Profile Priority |
|------------|-----------|-------------|-----------------|
| MY_GRIDSQUARE | GridSquare | Maidenhead locator — 4, 6, or 8 characters | Table stakes |
| MY_GRIDSQUARE_EXT | String | Extended Maidenhead locator (added ADIF 3.1.4) | Accept if operator enters 8-char grid |
| MY_LAT | Latitude | Decimal latitude of logging station (WGS84) | Table stakes |
| MY_LON | Longitude | Decimal longitude of logging station (WGS84) | Table stakes |
| MY_VUCC_GRIDS | String | Grid squares for VUCC award (comma-separated, used for rover operations) | Skip for MVP |

### Operator Identity
| ADIF Field | Data Type | Description | Profile Priority |
|------------|-----------|-------------|-----------------|
| MY_NAME | String | Logging operator's name | Table stakes |
| MY_NAME_INTL | IntlString | MY_NAME in UTF-8 | Skip |

### Station Equipment
| ADIF Field | Data Type | Description | Profile Priority |
|------------|-----------|-------------|-----------------|
| MY_RIG | String | Logging station's equipment/transceiver description | Table stakes |
| MY_RIG_INTL | IntlString | MY_RIG in UTF-8 | Skip |
| MY_ANT | String | Logging station's antenna description | Table stakes |

**Note — MY_POWER does not exist in ADIF.** The power field in ADIF is `TX_PWR` (logging
station's transmit power in watts, at the QSO level). No `MY_POWER` field appears in the
ADIF 3.1.x specification. Logging software (HRD, Log4OM, N1MM+) stores a default power in
the station profile and stamps it as `TX_PWR` on each new QSO. The profile should store a
plain `power_watts` value; `build_qso_dict()` should stamp it as `TX_PWR`.

### Zone and DXCC (Derived — rarely entered manually)
| ADIF Field | Data Type | Description | Profile Priority |
|------------|-----------|-------------|-----------------|
| MY_CQ_ZONE | PositiveInteger | Logging station's CQ zone (1–40) | Low — deriving from callsign/country is a separate feature |
| MY_ITU_ZONE | PositiveInteger | Logging station's ITU zone (1–90) | Low — same |
| MY_DXCC | Integer | Logging station's DXCC entity code | Low — same |

### Award / Activation Program Fields
| ADIF Field | Data Type | Description | Profile Priority |
|------------|-----------|-------------|-----------------|
| MY_SOTA_REF | SOTARef | SOTA summit reference for the activation (e.g., W0C/SP-001) | NOT a profile field — per-activation |
| MY_POTA_REF | String | POTA park reference (added ADIF 3.1.4) | NOT a profile field — per-activation |
| MY_IOTA | IOTARef | IOTA island reference | Optional; skip for MVP |
| MY_IOTA_ISLAND_ID | PositiveInteger | IOTA island numeric identifier | Optional; skip for MVP |
| MY_SIG | String | Special interest group name (e.g., POTA, SOTA) | Optional; skip for MVP |
| MY_SIG_INFO | String | SIG additional info — used by POTA for park IDs (MY_SIG_INFO = park ref for POTA) | NOT a profile field — per-activation |
| MY_SIG_INTL | IntlString | MY_SIG in UTF-8 | Skip |
| MY_SIG_INFO_INTL | IntlString | MY_SIG_INFO in UTF-8 | Skip |
| MY_ARRL_SECT | ArrLSect | ARRL section (added ADIF 3.1.4) | Optional; skip for MVP |
| MY_FISTS | String | FISTS CW club member number | Niche; skip |
| MY_USACA_COUNTIES | String | US counties for USACA award | Niche; skip |

### German / European Program Fields
| ADIF Field | Data Type | Description | Profile Priority |
|------------|-----------|-------------|-----------------|
| MY_DARC_DOK | String | DARC DOK (District Operating Kontrol) — added ADIF 3.1.6 | Niche; skip |

### Morse Key Fields (Added ADIF 3.1.6)
| ADIF Field | Data Type | Description | Profile Priority |
|------------|-----------|-------------|-----------------|
| MY_MORSE_KEY_INFO | String | Description of the Morse key used | Niche; skip |
| MY_MORSE_KEY_TYPE | Enum | Type of Morse key (straight key, bug, paddle, etc.) | Niche; skip |

---

## Differentiators

Features that set the product apart. Not universally expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Grid-to-lat/lon auto-compute | Operators who enter grid get lat/lon for free — no manual coordinate lookup needed | Medium | Standard Maidenhead → WGS84 formula; implementable in pure Python; no external service |
| Profile completeness nudge | Prompt operators to fill grid, rig, antenna before first QSO — reduces missing data in exports | Low | Simple field-count indicator or checklist banner in UI |
| MY_GRIDSQUARE_EXT support (8-char) | Portable, VHF, and microwave operators care about sub-km precision | Low | Just store the full string; ADIF MY_GRIDSQUARE_EXT is the correct field |
| STATION_CALLSIGN / OPERATOR distinction clearly labeled in UI | This confuses operators constantly (documented on HAMRS, N1MM+ forums); clear labeling reduces support burden | Low | Add an explanatory tooltip or inline help text on the profile form |

---

## Anti-Features

Features to explicitly NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Multiple station profiles per operator | Log4OM and HRD support this but it adds significant DB schema and UI complexity | One profile per operator; all fields are freely editable at any time |
| MY_SOTA_REF and MY_POTA_REF in the profile form | These change on every activation outing — they are per-session, not permanent station attributes | Handle as per-QSO overrides in a future milestone; do not put in profile settings |
| DXCC / CQ zone auto-derivation from callsign | Requires callsign prefix parsing + cty.dat lookup; separate feature with its own complexity | Let operators enter MY_CQ_ZONE manually if they need it in exports; skip for this milestone |
| Per-QSO rig/antenna override in the profile UI | Profile supplies defaults; per-contact overrides belong in the QSO edit form | QSO edit already allows editing any ADIF field via extra= allow model |
| QRZ / HamQTH callbook prefill of profile fields | External API dependency, auth complexity, rate limits | Operator fills profile manually; callbook integration is a future milestone |
| INTL field variants (MY_NAME_INTL, MY_CITY_INTL, etc.) | Doubles storage and form fields for non-Latin script support; adds parsing complexity | The existing ADIF serializer already handles UTF-8 byte counting correctly for the base fields; INTL variants are for apps that store both a Latin and a native-script version simultaneously |
| MY_DARC_DOK, MY_FISTS, MY_USACA_COUNTIES, MY_MORSE_KEY_* | Highly niche award and equipment fields with minimal operator population | Operators who need these can import ADIF with those fields set; the existing `extra="allow"` model stores them verbatim |
| Email address on profile form | Email in profile is cosmetic for a private logbook; no notification or verification feature uses it | Skip unless a specific downstream feature (e.g., QSL notifications) requires it |

---

## Feature Dependencies

```
User.callsign (existing) → OPERATOR stamp on QSO (new)
Profile.station_callsign (new) → STATION_CALLSIGN stamp on QSO (new, conditional on non-blank)
Profile.gridsquare (new) → MY_GRIDSQUARE stamp on QSO (new, conditional on non-blank)
Profile.rig (new) → MY_RIG stamp on QSO (new, conditional on non-blank)
Profile.antenna (new) → MY_ANT stamp on QSO (new, conditional on non-blank)
Profile.power_watts (new) → TX_PWR stamp on QSO (new, conditional on non-blank)
build_qso_dict() (existing) → must accept profile snapshot arg to inject fields
_qso_to_adif_dict() (existing) → NO CHANGES NEEDED; model_extra passthrough already handles new fields
ADIF export (existing) → will include OPERATOR, STATION_CALLSIGN, MY_* fields automatically once stored
Profile settings UI → requires new router + Jinja2 template + HTMX wiring
```

---

## MVP Recommendation for This Milestone

**Phase 1 — Profile storage and settings UI:**
1. New `Profile` MongoDB document — separate from `User`, linked by `callsign` (clean migration path; no schema change to `User`)
2. Profile fields: `station_callsign`, `name`, `city`, `state`, `country`, `gridsquare`, `lat`, `lon`, `rig`, `antenna`, `power_watts`
3. Profile service: `get_or_create_profile(callsign)`, `update_profile(callsign, data)`
4. Profile settings UI at `/profile` — single HTMX form consistent with existing QSO UI patterns

**Phase 2 — QSO auto-stamping:**
5. Modify `build_qso_dict()` to accept a profile snapshot and inject:
   - `OPERATOR` = login callsign (always)
   - `STATION_CALLSIGN` = profile value (only if non-blank)
   - `MY_GRIDSQUARE` = profile gridsquare (only if non-blank)
   - `MY_RIG` = profile rig (only if non-blank)
   - `MY_ANT` = profile antenna (only if non-blank)
   - `TX_PWR` = profile power_watts (only if non-blank)
6. Update QSO creation endpoint to load the operator's profile before calling `build_qso_dict()`

**Phase 3 — Grid/coordinate helper (optional but high value):**
7. Auto-compute lat/lon from 6-char grid when operator saves profile grid (server-side Python, no external API)

**Defer:**
- Multiple station profiles
- POTA/SOTA per-activation fields
- Callbook lookup integration
- Award-specific fields (ARRL_SECT, CQ zone, etc.)
- Email on profile

---

## Surprising Fields Operators Expect

Findings from community research (HAMRS forum, POTA documentation, N1MM+ documentation):

1. **TX_PWR is the power field — MY_POWER does not exist in ADIF.** Apps store a default wattage in the station profile and stamp individual QSOs with `TX_PWR`. Operators searching for "MY_POWER" in ADIF output are looking for a non-standard field that some logging apps emit incorrectly. The correct field is `TX_PWR`.

2. **STATION_CALLSIGN confusion is widespread.** The HAMRS community thread on Field Day logging shows this is a recurring operator support issue. Operators running a club station often produce ADIF with only CALL and OPERATOR and miss STATION_CALLSIGN entirely, causing POTA log upload rejections. The profile UI should surface the OPERATOR vs STATION_CALLSIGN distinction with clear explanatory text.

3. **Grid locator is the primary location concept for most operators — not lat/lon.** Operators think in grid squares (EN52, FN20pi), not decimal degrees. Accept grid as the primary location input. WSJT-X, GridTracker, and every VHF contest tool use 6-char grid as the canonical station location identifier. Derive lat/lon from grid automatically.

4. **6-char grid minimum for practical use.** 4-char grid (e.g., EN52) is acceptable for ADIF storage but gives 120 km precision — too coarse for VHF DX and POTA spot maps. Operators expect 6-char (e.g., EN52ab) as the default. The ADIF spec accepts 4 or 6 chars; some apps accept 8. Store whatever is entered but nudge toward 6-char.

5. **MY_SOTA_REF and MY_POTA_REF are NOT profile fields — they are per-activation.** SOTA summits and POTA parks change with every trip. Operators who activate SOTA regularly expect to change MY_SOTA_REF for each activation session, not edit their station profile. Do not put these in the profile settings form.

6. **Log4OM's three-callsign model (owner / station / operator) is more nuanced than needed here.** Log4OM distinguishes the equipment owner from the station licensee from the operating control point. For this project's scope (admin-managed accounts, single-station context), the ADIF two-field model (OPERATOR + STATION_CALLSIGN) is sufficient and appropriate.

---

## Sources

| Source | Confidence | Use |
|--------|------------|-----|
| [ADIF 3.1.7 specification, 2026-03-22](https://adif.org.uk/317/ADIF_317.htm) | MEDIUM (page not directly fetched; assembled from search snippets) | MY_* field list, field data types |
| [ADIF 3.1.4 specification](https://www.adif.org/314/ADIF_314.htm) | MEDIUM (authoritative source, 3.1.4 field set confirmed by multiple snippets) | Baseline MY_* fields |
| [ADIF 3.1.6 release notes](https://adif.org/316/ADIF_316.htm) | MEDIUM | MY_CNTY_ALT, MY_DARC_DOK, MY_MORSE_KEY_* additions |
| [ADIF for POTA Technical Reference](https://docs.pota.app/docs/activator_reference/ADIF_for_POTA_reference.html) | HIGH (official POTA documentation) | STATION_CALLSIGN vs OPERATOR for club activations; MY_SIG_INFO for park IDs |
| [HAMRS Community — Field Day STATION_CALLSIGN confusion](https://community.hamrs.app/t/field-day-help-ive-confused-myself-with-adif-station-callsign-and-operator/584) | MEDIUM (community forum) | Confirms OPERATOR/STATION_CALLSIGN confusion is a real, recurring operator problem |
| [N1MM+ The Configurer](https://n1mmwp.hamdocs.com/setup/the-configurer/) | HIGH (official N1MM+ documentation) | OPERATOR per-QSO, STATION_CALLSIGN from station data; OPON command pattern |
| [Log4OM forum — Owner, Station & Operator Callsign](https://forum.log4om.com/viewtopic.php?t=227) | MEDIUM (community forum) | Three-callsign model; confirms Log4OM separates owner/station/operator |
| [Ham Radio Deluxe — My Station setup](https://support.hamradiodeluxe.com/support/solutions/articles/51000052682-setup-configuration-my-station) | MEDIUM (official HRD support docs) | Field inventory: street, city, county, state, postal code, email, locator, lat/lon |
| [MacLoggerDX Station Info](https://dogparksoftware.com/MacLoggerDX/Manual/Pages/stationinfo.html) | MEDIUM (official MacLoggerDX docs) | Callsign, lat/lon, grid, name/address fields |
| [WSJT-X User Guide 2.6.1](https://wsjt.sourceforge.io/wsjtx-doc/wsjtx-main-2.6.1.html) | HIGH (official WSJT-X documentation) | My Call + My Grid as primary station fields; 6-char preferred |
| [Maidenhead Locator System — Wikipedia](https://en.wikipedia.org/wiki/Maidenhead_Locator_System) | HIGH | 4/6/8-char precision levels: ±120 km / ±5 km / ±460 m |
| [POTA Club Activation Guide](https://docs.pota.app/docs/activator_reference/activator_guide_clubs.html) | HIGH (official POTA documentation) | STATION_CALLSIGN = club call mandate for club logs |
