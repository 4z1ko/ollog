# Project Research Summary

**Project:** Ham Radio Online Logbook (ollog) — Operator & Station Profiles Milestone (v1.1)
**Domain:** Ham radio QSO logbook — per-operator profile with ADIF MY_* field storage and QSO auto-stamping
**Researched:** 2026-04-04
**Confidence:** HIGH (architecture from direct codebase inspection; stack and features from ADIF spec cross-checks)

## Executive Summary

This milestone adds operator and station profiles to an existing, production-tested FastAPI/MongoDB/HTMX logbook. The v1.0 foundation (QSO logging, ADIF import/export, auth, admin, SSE feed) is complete and validated. The new work is narrowly scoped: a profile data model, a settings UI, and auto-stamping of ADIF MY_* fields onto new QSOs. The overall pattern is additive — nothing in the existing QSO flow, ADIF serializer, or auth system requires redesign.

The recommended architecture embeds profile fields directly in the existing `User` Beanie document rather than creating a separate `OperatorProfile` collection. This is the right call for this codebase: the authenticated `User` is already fetched on every protected request, so profile data comes at zero extra DB cost. The key implementation change is extending `build_qso_dict()` to accept the `User` document and stamp ADIF fields conditionally. Both the REST and UI QSO creation paths converge there, so the stamp happens in exactly one place.

The two highest-stakes risks are both security and data-integrity concerns: operator isolation (profile routes must derive the operator identity from the JWT, never from a client-supplied parameter) and auto-stamp null safety (a profile-less operator must not produce `OPERATOR: null` in QSO documents). A third significant risk is the `OPERATOR` vs. `STATION_CALLSIGN` distinction, which is a documented recurring operator support problem. Clear UI labeling and correct conditional stamping are the mitigation. The Maidenhead `center=True` parameter (not the library default) must be used whenever converting grid to lat/lon — using the SW corner produces systematic location errors of up to 80 km.

## Key Findings

### Recommended Stack

The existing stack (FastAPI 0.135+, Beanie 2.1+, pymongo 4.16+, HTMX 2.0.4, PyJWT, pwdlib, MongoDB 7 replica set) is unchanged. Two new dependencies are needed and nothing else: `maidenhead>=1.8.0` for Maidenhead grid-to-lat/lon conversion (pure Python, zero system deps, de facto standard in Python ham radio tooling) and `pydantic[email]>=2.0` to enable `EmailStr` validation. Both are additive — add them to `pyproject.toml` and the rest of the stack is unaffected.

All ADIF MY_* profile fields are simple `Optional[str]` or `Optional[float]` values. No additional library is needed for their storage or serialization. The existing `_qso_to_adif_dict()` serializer already handles `model_extra` passthrough losslessly — once MY_* fields are stamped onto QSO documents, they export correctly with no serializer changes.

**Core technologies (new additions only):**
- `maidenhead 1.8.0`: Maidenhead grid conversion — pure Python, well-tested, two-function API (`to_maiden` / `to_location`)
- `pydantic[email] 2.0`: enables `EmailStr` on the `User` model — required for Pydantic v2's email type to function
- No new frameworks, no new DB, no geospatial index needed

### Expected Features

**Must have (table stakes):**
- Profile storage per operator (name, QTH city, state, country) — every logger has a "My Station" page
- `STATION_CALLSIGN` and `OPERATOR` as distinct profile fields — mandatory for club, POTA, and special-event operations
- Maidenhead grid locator (`MY_GRIDSQUARE`) — required for FT8/WSJT-X, VHF contests, POTA spot maps
- Decimal lat/lon auto-derived from grid on profile save — operators think in grid squares, not coordinates
- Rig description (`MY_RIG`) and antenna description (`MY_ANT`) — present in every logging application
- Default transmit power stamped as `TX_PWR` on new QSOs — note: `MY_POWER` does not exist in the ADIF spec
- Auto-stamp `OPERATOR`, `STATION_CALLSIGN`, `MY_GRIDSQUARE`, `MY_RIG`, `MY_ANT`, `TX_PWR` on new interactive QSOs
- Profile settings UI at `/log/profile` — HTMX form consistent with existing UI patterns

**Should have (differentiators):**
- Grid-to-lat/lon auto-compute storing center of grid square (not SW corner)
- Profile completeness nudge before first QSO — reduces missing data in ADIF exports
- Clear `OPERATOR` vs. `STATION_CALLSIGN` UI labeling with explanatory tooltip — this is a documented recurring operator confusion point

**Defer (v2+):**
- Multiple station profiles per operator
- `MY_SOTA_REF` and `MY_POTA_REF` in the profile form — these are per-activation, not permanent station attributes
- DXCC and CQ zone auto-derivation from callsign prefix (requires cty.dat lookup)
- QRZ / HamQTH callbook prefill
- INTL field variants (`MY_NAME_INTL`, `MY_CITY_INTL`, etc.)
- Niche award fields (`MY_DARC_DOK`, `MY_FISTS`, `MY_USACA_COUNTIES`, `MY_MORSE_KEY_*`)

### Architecture Approach

Profile fields are embedded directly as `Optional` fields on the existing `User` Beanie document. This is the architecturally correct choice: the `User` is already in scope on every authenticated request, no second DB fetch is needed, and Beanie adds optional fields to existing documents transparently with no migration. The profile module adds two routers (`app/profile/router.py` and `app/profile/ui_router.py`), one grid utility (`app/profile/grid.py`), and Pydantic schemas. The single service-layer integration point is `build_qso_dict()` in `app/qso/service.py`, which gains an optional `profile` parameter with a `None` default — fully backward-compatible. ADIF import (`process_import()`) is explicitly excluded from auto-stamping to preserve historical record integrity.

**Major components:**
1. `User` model extensions (`app/auth/models.py`) — add ~10 Optional profile fields; no migration required; existing documents get `None` for absent keys
2. Grid conversion utility (`app/profile/grid.py`) — wraps `maidenhead` library; pure function; testable in complete isolation
3. Profile Pydantic schemas — `ProfileUpdateRequest` (validates form input with grid format regex), `ProfileResponse` (read shape)
4. Profile API router (`GET /api/profile`, `PATCH /api/profile`) — JWT auth; no callsign param on GET
5. Profile UI router and template (`GET /log/profile`, `POST /log/profile`) — HTMX form, cookie auth
6. `build_qso_dict()` extension — accepts `profile=None`; stamps fields additively (body always wins over profile defaults)

### Critical Pitfalls

1. **Profile endpoint isolation leak** — profile GET/PATCH must derive operator from JWT only, never from a client-supplied callsign param or request body; add a cross-operator isolation test matching existing v1.0 audit patterns

2. **Auto-stamp null crash for profile-less operators** — `profile is None` must be guarded in `build_qso_dict()`; omit the field entirely rather than writing `OPERATOR: null` (the existing serializer converts `None` via `str(None)` producing the literal string `"None"` in ADIF output)

3. **Maidenhead SW corner vs. center** — always use `maidenhead.to_location(grid, center=True)`; the default returns the SW corner of the grid square, introducing up to 80 km systematic location error for 4-char grids

4. **`STATION_CALLSIGN` absent breaks LoTW and POTA upload for club calls** — stamp both `OPERATOR` and `STATION_CALLSIGN` when the profile has a station callsign set; omit `STATION_CALLSIGN` entirely (do not write an empty string) when it is blank

5. **Auto-stamp must not apply during ADIF import** — `process_import()` in `app/adif/router.py` must remain unchanged; stamping profile values over imported historical records corrupts original logging data

6. **ADIF `MY_LAT`/`MY_LON` export format** — the ADIF spec defines these as strings in `XDDD MM.MMM` format, not decimal degrees; store as float internally for computation, convert to spec format on ADIF export

## Implications for Roadmap

Dependencies flow from data model outward to UI. The recommended build order is:

### Phase 1: Profile Data Model and Grid Utility

**Rationale:** Everything downstream — schemas, service logic, routers, UI — depends on the `User` model field names being defined first. The grid utility is a pure function with no DB dependency and can be tested immediately after installation. Locking field names first prevents cascading rework in later phases.

**Delivers:** Extended `User` Beanie document with Optional profile fields; `app/profile/grid.py` with `grid_to_latlon()` and `latlon_to_grid()`; maidenhead and pydantic[email] added to pyproject.toml

**Addresses:** Table stakes profile storage; grid/lat/lon conversion feature

**Avoids:** Pitfalls 6 (grid/lat/lon dual-truth drift), 7 (SW corner default), 10 (ADIF field naming must match spec exactly), 12 (Beanie index handling on new fields)

### Phase 2: Profile Service, Schemas, and API Router

**Rationale:** With field names locked, schemas can be written and the API router gives a testable surface for profile CRUD before the UI exists. Operator isolation tests and null-guard tests are written in this phase before any QSO stamping logic is touched.

**Delivers:** `ProfileUpdateRequest` and `ProfileResponse` schemas; `GET /api/profile` and `PATCH /api/profile` endpoints; grid/lat/lon bidirectional sync on profile save; cross-operator isolation tests

**Addresses:** Must-have: profile persistence, lat/lon auto-compute, operator-scoped access

**Avoids:** Pitfalls 1 (isolation leak), 17 (PII enumeration via callsign param), 4 (null profile on read)

### Phase 3: QSO Auto-Stamping

**Rationale:** Profile data layer must exist before `build_qso_dict()` can consume it. This phase changes both QSO creation call sites (`create_qso()` and `submit_qso()`) from `get_current_operator_callsign` to `get_current_user`. The `profile=None` default makes the change backward-compatible and verifiable in isolation against existing QSO tests.

**Delivers:** Modified `build_qso_dict()` with additive profile stamping; both QSO creation paths updated; ADIF export of `OPERATOR`, `STATION_CALLSIGN`, `MY_GRIDSQUARE`, `MY_RIG`, `MY_ANTENNA`, `TX_PWR` without any serializer changes

**Addresses:** Must-have: auto-stamp all table-stakes fields on new interactive QSOs

**Avoids:** Pitfalls 4 (null stamp into QSO), 5 (overwriting explicit OPERATOR from body), 8 (missing STATION_CALLSIGN for club calls breaking LoTW and POTA upload)

### Phase 4: Profile UI

**Rationale:** UI depends on all preceding layers being stable and tested. The HTMX form is the lowest-risk surface — it consumes the API layer already verified in Phase 2. UI copy can explain the new-QSOs-only stamping behavior, preventing operator confusion about retroactive updates.

**Delivers:** `GET /log/profile` and `POST /log/profile` routes; `templates/log/profile.html` HTMX form; nav link added to log templates; `OPERATOR` vs. `STATION_CALLSIGN` explanatory tooltip

**Addresses:** Must-have: settings UI; differentiator: clear callsign distinction labeling; optional: profile completeness nudge

**Avoids:** Pitfall 20 (retroactive update misunderstanding — UI copy clarifies new-QSOs-only behavior explicitly)

### Phase Ordering Rationale

- Model before schema before router before UI is forced by Beanie and Pydantic import dependencies — there is no flexibility in this order
- Grid utility is decoupled from DB and can be validated immediately after Phase 1 without standing up the full app
- QSO auto-stamping (Phase 3) is deferred until the profile API is verified — the `profile=None` default means Phase 3 can be developed and shipped without breaking existing QSO creation at any point
- ADIF import path (`process_import()`) is explicitly out-of-scope for all phases — it is not touched

### Research Flags

Phases that need verification during planning:

- **Phase 2:** Verify the exact ADIF 3.1.7 field name (`MY_ANT` vs. `MY_ANTENNA`) against adif.org before locking the schema — field name confidence is MEDIUM because WebFetch to adif.org was unavailable during research. A single direct fetch of the spec at planning time resolves this permanently and affects only one field name in the schema and stamp mapping.

- **Phase 4 (ADIF lat/lon export):** Verify the `XDDD MM.MMM` format against ADIF 3.1.7 spec before writing the export conversion utility — confidence on the exact format string is MEDIUM.

Phases with standard, well-documented patterns (can skip research-phase):

- **Phase 1:** Beanie optional field addition is the canonical documented pattern; `maidenhead` API confirmed via PyPI and multiple sources
- **Phase 3:** `build_qso_dict()` extension is a local function change; the additive stamp pattern is straightforward and follows patterns established in v1.0
- **Phase 4:** HTMX form follows established patterns from existing log templates in the codebase

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing stack unchanged; maidenhead API confirmed via PyPI and multiple sources; pydantic[email] is standard Pydantic ecosystem practice |
| Features | MEDIUM-HIGH | ADIF spec cross-checked via multiple search snippets; POTA, LoTW, and N1MM+ behavior from official docs; direct adif.org fetch unavailable — field list assembled from spec mirrors |
| Architecture | HIGH | Based on direct inspection of the live codebase; all integration points identified with specific file and function references; no guesswork |
| Pitfalls | HIGH | 8 of 8 v1.1-specific pitfalls derived from direct code inspection; `center=True` and LoTW STATION_CALLSIGN behavior verified via WebSearch against official sources |

**Overall confidence:** HIGH

### Gaps to Address

- **`MY_ANT` vs. `MY_ANTENNA` field name:** STACK.md identifies `MY_ANTENNA` as the correct ADIF name; ARCHITECTURE.md stores `my_ant` internally and maps to `MY_ANTENNA` at stamp time; FEATURES.md lists `MY_ANT`. The research source for this is LOW confidence (a forum post). Resolve at Phase 2 planning by fetching adif.org/317 directly. This affects only one field name in the schema and stamp mapping.

- **ADIF `MY_LAT`/`MY_LON` export format:** Stored as decimal float internally (correct for computation). The ADIF `Location` data type specifies `XDDD MM.MMM` format for export. A conversion utility is needed in Phase 4 but the exact format string should be verified against the spec before writing tests.

- **`MY_POWER` vs. `TX_PWR`:** Research is conclusive — `MY_POWER` does not exist in ADIF; `TX_PWR` is the correct field. Profile stores `power_watts`; `build_qso_dict()` stamps it as `TX_PWR`. No blocker, but worth checking whether any existing imported QSO documents carry `MY_POWER` from third-party ADIF imports (cosmetic concern only).

## Sources

### Primary (HIGH confidence)
- Live codebase inspection (`app/auth/models.py`, `app/qso/models.py`, `app/qso/service.py`, `app/adif/router.py`, `app/auth/dependencies.py`, `app/database.py`, `app/main.py`) — architecture decisions, integration points, existing field names
- ADIF for POTA Technical Reference (https://docs.pota.app/docs/activator_reference/ADIF_for_POTA_reference.html) — STATION_CALLSIGN mandate for club logs
- POTA Club Activation Guide (https://docs.pota.app/docs/activator_reference/activator_guide_clubs.html) — club call requirements
- N1MM+ The Configurer (https://n1mmwp.hamdocs.com/setup/the-configurer/) — OPERATOR per-QSO, STATION_CALLSIGN model
- WSJT-X User Guide 2.6.1 (https://wsjt.sourceforge.io/wsjtx-doc/wsjtx-main-2.6.1.html) — 6-char grid as primary station location input
- Maidenhead Locator System Wikipedia (https://en.wikipedia.org/wiki/Maidenhead_Locator_System) — 4/6/8-char precision levels, SW corner vs. center
- maidenhead PyPI 1.8.0 (https://pypi.org/project/maidenhead/) — `center=True` parameter confirmed
- email-validator PyPI 2.3.0 (https://pypi.org/project/email-validator/) — pydantic[email] integration
- Beanie ODM initialization (https://beanie-odm.dev/tutorial/initialization/) — `allow_index_dropping=False` default, index creation behavior
- LoTW developer docs (https://lotw.arrl.org/lotw-help/developer-submit-qsos/?lang=en) — STATION_CALLSIGN certificate mismatch behavior

### Secondary (MEDIUM confidence)
- ADIF 3.1.7 specification (https://adif.org/317/ADIF_317.htm) — MY_* field list assembled from search snippets; direct page fetch unavailable during research
- ADIF 3.1.4 specification (https://www.adif.org/314/ADIF_314.htm) — baseline MY_* field set confirmed via multiple snippets
- ADIF 3.1.6 release notes — MY_CNTY_ALT, MY_DARC_DOK, MY_MORSE_KEY_* additions
- HAMRS Community thread (https://community.hamrs.app/t/field-day-help-ive-confused-myself-with-adif-station-callsign-and-operator/584) — confirms OPERATOR/STATION_CALLSIGN confusion is a real, recurring operator problem

### Tertiary (LOW confidence — verify before implementation)
- Log4OM forum (https://forum.log4om.com/viewtopic.php?t=5219) — `MY_ANTENNA` vs. `MY_ANT` field name; needs verification against adif.org spec directly

---
*Research completed: 2026-04-04*
*Ready for roadmap: yes*
