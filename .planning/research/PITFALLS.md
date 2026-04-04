# Domain Pitfalls

**Domain:** Multi-operator ham radio QSO logbook (Python/MongoDB/ADIF)
**Researched:** 2026-04-04
**Scope:** Pitfalls specific to adding operator/station profiles to an existing system with live QSO data.
**Confidence note:** Findings draw from direct codebase inspection (actual models, routers, dependencies), ADIF spec research (WebSearch, verified against adif.org), Beanie ODM documentation (WebSearch + beanie-odm.dev), and training data (knowledge cutoff August 2025). Confidence levels are assigned per-finding.

---

## How This File Is Organized

Pitfalls 1–8 are **new** — specific to adding profile storage to the existing v1.0 system.
Pitfalls 9–27 are **carried forward** from v1.0 research (domain-wide ADIF, MongoDB, and multi-operator hazards that remain relevant to v1.1 work).

---

## Critical Pitfalls (v1.1 specific)

Mistakes that cause data loss, operator isolation breaks, or require rewrites.

---

### Pitfall 1: Profile Endpoint Returns Another Operator's Data (Isolation Leak)

**What goes wrong:** A `GET /api/profile` endpoint resolves operator identity from a query param, path param, or request body instead of the JWT-injected callsign. One operator can read or overwrite another's profile by supplying a different callsign in the request.

**Why it happens:** The existing pattern in this codebase correctly uses `get_current_operator_callsign` from the JWT dependency everywhere in QSO routes. A new profile route written without that discipline — for example, reading `callsign` from a request body to "allow updating any profile" — silently breaks isolation. The danger is highest if the route is modeled after an admin route that accepts arbitrary operator identifiers.

**Consequences:** Complete profile isolation failure. Operator A reads Operator B's personal info (name, QTH, grid, email). Operator A overwrites Operator B's profile. The app passes authentication checks (JWT is valid) but fails authorization checks (wrong data scope).

**Prevention:**
- Profile GET and PUT/PATCH routes MUST use `operator: str = Depends(get_current_operator_callsign)` (or its cookie variant) as the sole source of the operator key — never a body or path param.
- Profile document must be keyed by callsign (or user ID) and the service layer must filter by the JWT-derived value, not by any client-supplied value.
- Add a cross-operator profile test in the same style as the existing programmatic operator isolation audit: authenticate as Operator A, attempt GET/PUT on Operator B's profile URL or body, assert 404 or 403.

**Detection:** The existing isolation audit in the test suite is the pattern to follow. A profile-specific isolation test that authenticates as W1AAA and attempts to read/write W2BBB's profile must return a non-2xx status.

**Phase:** Profile data model and routing (first task before any profile logic is built).

**Confidence:** HIGH — this is the same isolation pattern enforced throughout v1.0; adding new routes without it is the canonical multi-tenant leak vector.

---

### Pitfall 2: Profile Embedded in the `User` Document Breaks Future Operability and Atomicity Assumptions

**What goes wrong:** Adding profile fields directly to the existing `User` Beanie document (`app/auth/models.py`) seems simple — just add `Optional[str]` fields. However, the `User` document has `model_config = ConfigDict(populate_by_name=True)` without `extra="allow"`, meaning any field not declared in the model is dropped on read and causes a Pydantic validation error on write. Adding 20+ ADIF MY_* fields as declared Optional fields inflates the auth model, couples the authentication concern to the logging concern, and makes the auth service carry profile data it has no business knowing about.

**Why it happens:** "Just add a field" is the path of least resistance in Beanie. Developers add `my_gridsquare: Optional[str] = None` and move on. This works initially, but every profile read now loads the full user document including all MY_* fields; every auth token check loads profile data.

**Consequences:**
- Auth model becomes a catch-all document — violates single responsibility.
- Changing profile schema requires migrating the `users` collection, which stores auth-critical data. A bad migration risks locking operators out of their accounts.
- The `users` collection has a unique index on `username` that is managed by Beanie. Adding index changes for profile fields to this model risks `allow_index_dropping` side effects on startup.

**Prevention:**
- Create a separate `OperatorProfile` Beanie Document in a dedicated `profiles` collection.
- Key the profile document by `operator_callsign` (matching the `callsign` field in `User`).
- Add `OperatorProfile` to the `document_models` list in `init_beanie()` in `app/database.py` — the collection is created lazily on first write; no migration of existing `users` data is needed.
- The profile document should use `extra="allow"` to absorb arbitrary ADIF MY_* fields without requiring a schema change for each new field.

**Detection:** If profile fields appear in `User` model, that is the anti-pattern. A clean separation is: `User` has only `username`, `hashed_password`, `callsign`, `role`, `enabled`. `OperatorProfile` has all ADIF MY_* fields and is fetched separately when needed.

**Phase:** Profile data model design (before any profile routes are written).

**Confidence:** HIGH — based on direct inspection of `app/auth/models.py` and Beanie documentation behavior.

---

### Pitfall 3: `init_beanie()` Not Updated With New Document Class — Profile Collection Never Initialized

**What goes wrong:** A new `OperatorProfile` Document class is defined but not added to `document_models` in `init_beanie()` in `app/database.py`. Beanie never connects the model to the database. Writes silently succeed (MongoDB creates the collection lazily) but indexes defined in `OperatorProfile.Settings.indexes` are never created. Queries against the model may fail with cryptic errors or scan the full collection.

**Why it happens:** The `init_beanie()` call in `database.py` is easy to miss when adding a new model in a different module. There is no compile-time check.

**Consequences:**
- Missing index on `operator_callsign` means profile lookups do a full collection scan — no functional impact at small scale, major performance issue as operator count grows.
- A unique constraint on `operator_callsign` (ensuring one profile per operator) is not enforced, allowing duplicate profiles to be created.
- Beanie's lazy collection creation masks the initialization gap during development.

**Prevention:**
- After defining `OperatorProfile`, immediately update `database.py` to add it to `document_models`.
- Add a unique index on `operator_callsign` in `OperatorProfile.Settings.indexes` — this is the enforcement mechanism for one-profile-per-operator.
- Integration test: after app startup, verify `db.list_collection_names()` includes `"profiles"` and `db.profiles.index_information()` contains the expected index.

**Detection:** After startup, run `db.profiles.getIndexes()` in the MongoDB shell. If only `_id_` is present, the Beanie initialization is missing the model.

**Phase:** Profile data model initialization (same commit that adds the document class).

**Confidence:** HIGH — based on direct inspection of `app/database.py` and Beanie initialization docs.

---

### Pitfall 4: QSO Auto-Stamp When Profile Does Not Exist Yet

**What goes wrong:** The plan is to stamp `OPERATOR` and `STATION_CALLSIGN` from the operator's profile onto every new QSO. On a fresh install, or for an operator who has never filled in their profile, the profile document does not exist. The QSO creation endpoint fetches the profile, gets `None`, and either crashes with an `AttributeError` or (worse) silently stamps `OPERATOR: None` into the QSO document.

**Why it happens:** Profile lookup is added as a new step in `build_qso_dict()` or `create_qso()`, and the `None` case is not handled explicitly. The developer tested with a fully populated profile and never hit the empty case.

**Consequences:**
- `OPERATOR: null` written into MongoDB QSO documents. When exported as ADIF, the serializer emits `<OPERATOR:0>` or skips the field depending on the null-handling code path. Either way, the exported ADIF is incorrect.
- QSO creation silently drops the operator stamp for new accounts — a data quality regression that is invisible at log time and only discovered on export.
- Existing export logic in `_qso_to_adif_dict()` coerces all values to `str(val)` — `str(None)` becomes the string `"None"`, which would be emitted as `<OPERATOR:4>None` in the ADIF output. That is a spec-invalid value.

**Prevention:**
- Profile fetch in QSO creation must be explicit: `profile = await OperatorProfile.find_one({"operator_callsign": operator})`.
- If `profile is None`, stamp nothing — do not write `OPERATOR` or `STATION_CALLSIGN` to the QSO document at all. Omitting the field is valid ADIF; writing null is not.
- If `profile` exists but `my_call` (STATION_CALLSIGN) is empty or None, same rule: omit the field.
- Never let a null profile value reach the QSO dict. Guard at the service layer, not the route layer.
- Write a test: create an operator with no profile, create a QSO, assert the QSO document has no `OPERATOR` key and no `STATION_CALLSIGN` key.

**Detection:** After QSO creation for a profile-less operator, inspect the raw MongoDB document: `db.qsos.findOne({_operator: "W1NEW"})` — if `OPERATOR` key is present with value `null` or `"None"`, the guard is missing.

**Phase:** QSO auto-stamp logic (the service layer change that introduces profile-lookup-on-QSO-create).

**Confidence:** HIGH — based on direct inspection of `build_qso_dict()`, `_qso_to_adif_dict()`, and QSO insert path.

---

### Pitfall 5: ADIF Field Name Collision — `OPERATOR` in Profile vs. `OPERATOR` in Existing QSO Documents

**What goes wrong:** Existing QSOs in the database may already contain an `OPERATOR` field in `model_extra` if they were imported from ADIF files that included `<OPERATOR:4>W1AW`. When the QSO auto-stamp logic writes `OPERATOR` from the profile onto new QSOs, it uses the same ADIF field name. On export, the `_qso_to_adif_dict()` function emits `model_extra` keys verbatim — so both imported and newly-logged QSOs will have `OPERATOR` in the export. This is correct behavior and is by design. The pitfall is in the auto-stamp logic trying to overwrite an existing `OPERATOR` value that was explicitly set by the user.

**Why it happens:** The auto-stamp logic runs before checking whether `OPERATOR` is already present in the incoming QSO dict. A user who explicitly provides `OPERATOR` in a PATCH or POST body (valid ADIF) gets it silently overwritten by the profile stamp.

**Consequences:**
- Multi-op club station where different operators send `OPERATOR: W1AAA` in their API calls gets all QSOs stamped with the profile's `OPERATOR` value, losing the per-QSO operator attribution.
- Imported ADIF files with pre-existing `OPERATOR` values get those values overwritten during import (if the import path also applies the profile stamp).

**Prevention:**
- Auto-stamp is additive, not overwriting: only stamp `OPERATOR` from profile if the QSO dict does not already contain an `OPERATOR` key.
- Apply the same rule to `STATION_CALLSIGN`.
- The import path (`process_import()` in `adif/router.py`) should NOT apply the profile auto-stamp — imported ADIF data already contains the operator's intent; stamping would corrupt historical records from multi-op operations.
- Rule: auto-stamp applies to new QSOs logged via the real-time UI and REST API, not to batch imports.

**Detection:** POST a QSO with `OPERATOR: "W9XYZ"` in the body while the profile has `my_call: "W1AW"`. Assert the stored QSO has `OPERATOR: "W9XYZ"`, not `"W1AW"`.

**Phase:** QSO auto-stamp logic implementation.

**Confidence:** HIGH — based on direct code inspection of `build_qso_dict()`, `process_import()`, and `_qso_to_adif_dict()`.

---

### Pitfall 6: Maidenhead Grid and Lat/Lon Stored as Separate Truths — They Drift Apart

**What goes wrong:** The profile stores both `MY_GRIDSQUARE` (Maidenhead locator) and `MY_LAT`/`MY_LON` (decimal degrees) as independent fields. The user sets the grid locator; lat/lon is left blank. Or the user sets lat/lon via a map picker; the grid is left blank. After a profile edit, the user updates lat/lon but forgets to update the grid. The two representations are now inconsistent, and downstream consumers (distance calculations, map display) use whichever field they happen to check first.

**Why it happens:** It seems convenient to store both. Letting users supply either one and derive the other requires implementing conversion logic. Developers skip the conversion to save time, leaving both fields as independent inputs.

**Consequences:**
- ADIF export emits both `MY_GRIDSQUARE` and `MY_LAT`/`MY_LON` with inconsistent values. External logbook software that uses both fields for award tracking (POTA, SOTA, VHF contests) will compute different distances depending on which field it uses.
- If the grid says FN31pr but lat/lon is from a different address, QSO distance calculations will disagree between two operators comparing logs.

**Prevention:**
- Designate one as the source of truth. Recommended: accept both, but derive the other on save.
  - If `MY_GRIDSQUARE` is provided, derive lat/lon from it (use center of grid square, not SW corner — see Pitfall 7).
  - If only lat/lon is provided, derive `MY_GRIDSQUARE` from it.
  - If both are provided and they are inconsistent (more than half a grid square apart), warn the user and ask which to trust.
- Alternatively, store only one canonical field in the profile document and compute the other on read. Given ADIF export needs both fields, derive on export rather than storing both independently.

**Detection:** After saving a profile with only `MY_GRIDSQUARE: FN31`, assert that `MY_LAT` and `MY_LON` are populated with values consistent with the center of FN31.

**Phase:** Profile save logic and profile data model.

**Confidence:** MEDIUM-HIGH — grid/lat/lon dual storage is a well-known inconsistency in ham radio software; the ADIF spec documents both fields as independent (not derived from each other).

---

### Pitfall 7: Maidenhead-to-Lat/Lon Returns SW Corner, Not Center — Distance Is Wrong

**What goes wrong:** The standard algorithm (and the popular Python `maidenhead` library's default) returns the southwest corner of the grid square when converting a Maidenhead locator to latitude/longitude. A 4-character grid square (e.g., FN31) covers 1° latitude × 2° longitude — roughly 100 km × 150 km at mid-latitudes. Storing the SW corner as the station's location introduces a systematic bias of up to ~60–80 km from the actual center, which corrupts distance calculations used for VHF/UHF contest scoring, POTA activation distance verification, and beacon path analysis.

**Why it happens:** The SW corner is the mathematically simpler result (no addition needed). The `center=True` parameter in the `maidenhead` Python library is not the default and is easy to miss.

**Consequences:**
- Distance between two stations in adjacent grid squares computed using SW corners will be wrong by up to a full grid square's dimension.
- VHF contest distance scoring that relies on grid-center-to-grid-center distance per IARU Region 1 rules will be incorrect.
- If the stored lat/lon feeds a map display, the pin appears at the corner of the grid square, not the operator's area.

**Prevention:**
- When converting a Maidenhead locator to lat/lon for storage, always use the center of the grid square.
- If using the `maidenhead` Python library: `maidenhead.to_location(grid, center=True)`.
- If implementing conversion manually: add `lat_span/2` and `lon_span/2` to the SW corner coordinates before storing.
- Document the convention in the codebase comment: "lat/lon stored as center of grid square per IARU convention."

**Detection:** Convert `FN31` to lat/lon. The center of FN31 is approximately 41.5°N, 74.0°W. If the result is 41°N, 76°W (SW corner), the `center=True` parameter was not used.

**Phase:** Grid/lat/lon conversion utility (implement and test before any distance or map feature uses these values).

**Confidence:** HIGH — `maidenhead` library behavior verified via WebSearch (pypi.org/project/maidenhead, space-physics/maidenhead GitHub). IARU center convention verified via WebSearch.

---

### Pitfall 8: `STATION_CALLSIGN` Absent in ADIF Export Breaks LoTW Submission for Club Calls

**What goes wrong:** When an operator uses a club callsign over the air (e.g., station is W1AW/club, operator is W1AAA), `STATION_CALLSIGN` in the profile differs from `OPERATOR`. The ADIF spec (since 2.1.5) says: if `STATION_CALLSIGN` is absent, `OPERATOR` shall be treated as both. If the auto-stamp only writes `OPERATOR` and omits `STATION_CALLSIGN`, external tools (LoTW submission, POTA upload) will treat the operator's personal call as the station callsign — which is incorrect for club/contest operations and will cause LoTW certificate mismatch errors.

**Why it happens:** Developers implement the simple case (stamp `OPERATOR`) and defer `STATION_CALLSIGN` because "it's the same callsign in most cases." It only fails in the club-call scenario, which is precisely the target use case of this application.

**Consequences:**
- LoTW TQSL rejects QSOs where `STATION_CALLSIGN` doesn't match the uploaded certificate's callsign.
- POTA upload requires `MY_CALLSIGN` (mapped from `STATION_CALLSIGN`) for activation credit — missing field = rejected log.
- Multi-op QSOs appear as if the personal callsign was used, misattributing the contact.

**Prevention:**
- The profile must store both `my_operator_callsign` (maps to ADIF `OPERATOR`) and `my_station_callsign` (maps to ADIF `STATION_CALLSIGN`) as distinct fields.
- Auto-stamp logic: write both `OPERATOR` and `STATION_CALLSIGN` to the QSO dict if both are set in the profile.
- UI: clearly label the two fields and explain the difference — "Your personal callsign (OPERATOR)" vs. "Callsign used on air (STATION_CALLSIGN — use club/contest call here)."
- ADIF fallback rule: if user leaves `STATION_CALLSIGN` blank in profile, do not stamp it (the ADIF spec's fallback to `OPERATOR` applies). Do not stamp an empty string.

**Detection:** Create a profile with `STATION_CALLSIGN: W1XYZ` and `OPERATOR: W1AAA`. Log a QSO. Export ADIF. Assert the ADIF record contains both `<STATION_CALLSIGN:5>W1XYZ` and `<OPERATOR:5>W1AAA`.

**Phase:** Profile schema and auto-stamp logic.

**Confidence:** HIGH — ADIF spec fallback rule verified via WebSearch (adif.org, HAMRS community forum, LoTW developer docs).

---

## Critical Pitfalls (carried forward from v1.0)

---

### Pitfall 9: ADIF Field Length Is Byte Count, Not Character Count

**What goes wrong:** The ADIF tag format `<FIELDNAME:N>value` uses N as the UTF-8 byte-length of the value, not the Unicode code-point count. `len(str)` in Python counts code points. Non-ASCII characters in profile fields (MY_NAME, MY_CITY, MY_QTH) will produce wrong byte counts.

**Prevention:** Always use `len(value.encode('utf-8'))` when writing ADIF tags. Affects the serializer for both QSO fields and MY_* profile fields.

**Phase:** ADIF serializer (hits profile data in v1.1 when MY_* fields are exported).

---

### Pitfall 10: ADIF MY_* Field Names Must Match the Spec Exactly

**What goes wrong:** Profile fields are stored internally with Python-friendly names (e.g., `my_gridsquare`, `my_lat`) and then mapped to ADIF on export. A mapping error or inconsistency produces non-standard field names in the exported ADIF. For example, emitting `<MY_GRID:6>FN31pr` instead of `<MY_GRIDSQUARE:6>FN31pr` will not be recognized by other logging software.

**Why it matters for v1.1:** This system uses `model_extra` for arbitrary ADIF fields. If profile fields are stored with Python-friendly names that differ from ADIF names, the export path that emits `model_extra` keys verbatim will produce wrong field names.

**Prevention:**
- Store MY_* fields in the `OperatorProfile` document using the exact ADIF 3.1.x field names as the MongoDB document keys (uppercase, e.g., `MY_GRIDSQUARE`, `MY_LAT`, `MY_LON`, `MY_NAME`, `MY_CITY`, `MY_OPERATOR`).
- Use the same naming convention as QSOs: ADIF field name = MongoDB key = model_extra key.
- Verify against ADIF 3.1.7 spec (https://adif.org/317/ADIF_317.htm) before implementation.

**Phase:** Profile data model and export path.

**Confidence:** HIGH — based on direct code inspection of `_qso_to_adif_dict()` and ADIF spec.

---

### Pitfall 11: QSO_DATE and TIME_ON Timezone — Applies to Profile Default Time Settings Too

See v1.0 Pitfall 2. If the profile stores a default QSO time offset or timezone preference for display, UTC must remain the storage canonical form. Any display-layer timezone conversion must be applied only at render time, never at storage time.

---

### Pitfall 12: Beanie `allow_index_dropping=False` Default — Profile Indexes Are Added, Not Dropped

**What goes wrong:** When `init_beanie()` is called with `OperatorProfile` included, Beanie will create any indexes defined in `Settings.indexes` that do not already exist. It will NOT drop indexes that exist in MongoDB but are no longer defined in the model (because `allow_index_dropping` defaults to `False`). This is safe behavior for adding new indexes to an existing system. However, if a developer defines an index, runs the app (index is created), then removes the index definition from the model, the index persists silently in MongoDB — consuming write overhead indefinitely.

**Prevention:** When removing or renaming index definitions during profile model iteration, manually drop the obsolete index from MongoDB. Never set `allow_index_dropping=True` in a production environment — it will drop all indexes not in the current model definition, including manually created operational indexes.

**Phase:** Profile data model initialization.

**Confidence:** HIGH — based on WebSearch confirming Beanie's `allow_index_dropping=False` default (beanie-odm.dev/tutorial/initialization/).

---

### Pitfall 13: Gridsquare / Maidenhead Validation Is Non-Trivial

**What goes wrong:** The Maidenhead locator character rules are: positions 1–2: letters A–R, positions 3–4: digits 0–9, positions 5–6: letters A–X, positions 7–8: digits 0–9. Validation that only checks length passes garbage values. Some software emits lowercase subsquare letters (legacy QRA locator confusion). Values like `AA00` (valid), `AA00AA` (valid 6-char), `AA00aa` (valid lowercase variant), `ZZ99` (invalid — Z not in A–R), and `FN31????` (invalid) must be handled correctly.

**Prevention:**
- Validate with: `^[A-Ra-r]{2}[0-9]{2}([A-Xa-x]{2}([0-9]{2})?)?$`
- Normalize to uppercase on save.
- On invalid input: reject with a clear validation error message (this is a user-supplied value in the profile form, not an imported file; strict rejection is appropriate here, unlike import where tolerance is needed).

**Phase:** Profile form validation and profile save endpoint.

**Confidence:** MEDIUM-HIGH — regex is from training data, consistent with ADIF spec character rules. Lowercase handling confirmed via WebSearch (Maidenhead Locator System Wikipedia).

---

## Moderate Pitfalls (carried forward from v1.0)

---

### Pitfall 14: ADIF Enumeration Values Case-Insensitive — Mode/Band Normalization

See v1.0 Pitfall 4. If the profile stores a default BAND or MODE preference, normalize to uppercase on save (consistent with the existing `BAND.upper()` / `MODE.upper()` normalization in `build_qso_dict()`).

---

### Pitfall 15: MongoDB `datetime` Naive vs. Aware Objects

See v1.0 Pitfall 11. If `OperatorProfile` stores any timestamp (profile created/updated datetime), apply the same UTC-aware convention: store UTC-aware `datetime`, re-attach `tzinfo=timezone.utc` on read. The existing `from_mongo_dt()` utility in `utils.py` handles this.

---

### Pitfall 16: Multi-Operator Station Callsign vs. Operator Callsign Confusion

See v1.0 Pitfall 10. This is now a first-class design concern for v1.1. The profile must clearly separate `STATION_CALLSIGN` (call used on air) from `OPERATOR` (personal callsign). See Pitfall 8 above for the v1.1-specific treatment.

---

### Pitfall 17: REST API Returns Full Profile — Expose Only the Authenticated Operator's Own Profile

**What goes wrong:** A `GET /api/profile` endpoint that accepts a callsign query parameter allows enumeration of all operators' profiles. Even if the profile contains only ham radio grid and name data, it exposes PII (email, address, real name via MY_NAME).

**Prevention:**
- Profile endpoint signature: `GET /api/profile` — no callsign parameter. Return the authenticated operator's own profile only.
- Admin endpoints that need to view any profile must be explicitly gated by `require_admin` dependency and prefixed under `/api/admin/`.

**Phase:** Profile routing.

**Confidence:** HIGH — same pattern as existing QSO endpoints; profile adds PII sensitivity.

---

## Minor Pitfalls (carried forward from v1.0 or v1.1-adjacent)

---

### Pitfall 18: ADIF Field Name Matching Must Be Case-Insensitive

See v1.0 Pitfall 15. Profile import (if supported) or profile display that reads MY_* fields must normalize to uppercase before any lookup.

---

### Pitfall 19: Lat/Lon Precision and Decimal Format

**What goes wrong:** ADIF defines `MY_LAT` and `MY_LON` as strings in the format `XDDD MM.MMM` (e.g., `N041 51.000`) — not decimal degrees. Many developers store decimal degrees (`41.85`) instead. If the ADIF export emits the decimal-degree form, it is technically non-spec-compliant. If the profile stores the ADIF-formatted string, arithmetic (distance calculation) requires parsing before use.

**Prevention:**
- Store lat/lon as decimal degrees (float) internally — this is the correct form for computation.
- On ADIF export of MY_LAT/MY_LON, convert to the ADIF XDDD MM.MMM format.
- Define a utility function `decimal_to_adif_lat(lat: float) -> str` and `decimal_to_adif_lon(lon: float) -> str` and test it with known values.
- Verify the format with ADIF 3.1.7 spec section on Location data type.

**Phase:** Profile ADIF export conversion.

**Confidence:** MEDIUM — ADIF location data type format confirmed via training data and cross-referenced with adif.org/306 search result. Verify against ADIF 3.1.7 spec before implementation.

---

### Pitfall 20: Profile Update Does Not Retroactively Update Stamped QSOs

**What goes wrong:** When an operator changes their `STATION_CALLSIGN` in their profile, all previously logged QSOs still carry the old callsign value in their `STATION_CALLSIGN` and `OPERATOR` fields. This is correct behavior — QSOs are historical records of what was logged at the time. However, if the UI does not make this clear, operators may expect profile changes to apply retroactively and interpret the historical values as bugs.

**Prevention:**
- Document the behavior explicitly: "Profile changes apply to new QSOs only. Existing QSOs retain the callsign that was stamped at log time."
- Do not provide a "re-stamp all QSOs with new profile" feature unless it is an explicit, opt-in admin action — and even then, treat it as a data migration with audit log, not a silent batch update.

**Phase:** Profile UI.

**Confidence:** HIGH — this is the documented behavior of N1MM+ and Ham Radio Deluxe (confirmed via WebSearch groups.io/N1MMLoggerPlus).

---

### Pitfall 21: `APP_` Fields in Exported ADIF Are Silently Lost

See v1.0 Pitfall 12. Profile data stored in `model_extra` will be included in ADIF export by the existing `_qso_to_adif_dict()` logic which iterates `model_extra`. This is not a new pitfall for v1.1 but verify that `OperatorProfile.model_extra` fields also round-trip correctly if a profile import feature is ever added.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| Profile data model | Embedding in User (Pitfall 2); init_beanie gap (Pitfall 3); ADIF MY_* field naming (Pitfall 10) | Separate `profiles` collection; add to `init_beanie()` immediately; use exact ADIF uppercase names |
| Profile routing | Isolation leak via wrong callsign source (Pitfall 1); PII enumeration (Pitfall 17) | Always use JWT-injected callsign; no callsign param on GET endpoint |
| QSO auto-stamp | Missing profile null crash (Pitfall 4); overwriting explicit OPERATOR (Pitfall 5); missing STATION_CALLSIGN (Pitfall 8) | Guard all profile lookups for None; auto-stamp is additive not overwriting; stamp both fields |
| Grid/lat/lon conversion | SW corner vs. center (Pitfall 7); dual-truth drift (Pitfall 6); format mismatch (Pitfall 19) | Use `center=True` in maidenhead lib; derive one from the other on save; store decimal internally |
| ADIF export of MY_* | Byte-count vs. char-count (Pitfall 9); ADIF lat/lon format (Pitfall 19); STATION_CALLSIGN absent (Pitfall 8) | `len(value.encode('utf-8'))`; convert decimal to ADIF format on export; test round-trip |
| Import path | Do not apply profile auto-stamp to imported records (Pitfall 5) | Auto-stamp only in live-logging path, not in `process_import()` |
| Beanie initialization | Index not created (Pitfall 3); allow_index_dropping (Pitfall 12) | Add OperatorProfile to init_beanie; never set allow_index_dropping=True in prod |

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| Operator isolation (Pitfalls 1, 17) | HIGH | Direct code inspection of existing dependency pattern; confirmed isolation audit exists |
| Profile collection design (Pitfall 2) | HIGH | Direct code inspection of User model; Beanie behavior is well-documented |
| Beanie init_beanie gap (Pitfall 3) | HIGH | Direct code inspection of database.py; Beanie docs confirm index creation on init |
| QSO auto-stamp null case (Pitfall 4) | HIGH | Direct code inspection of build_qso_dict() and _qso_to_adif_dict() |
| OPERATOR/STATION_CALLSIGN field collision (Pitfall 5) | HIGH | Direct code inspection of build_qso_dict() and process_import() |
| Grid/lat/lon dual-truth (Pitfall 6) | MEDIUM-HIGH | Known pattern in ham radio software; verified ADIF spec has both as independent fields |
| Maidenhead SW corner vs. center (Pitfall 7) | HIGH | Verified via WebSearch: maidenhead Python library default and IARU convention |
| STATION_CALLSIGN absent / LoTW (Pitfall 8) | HIGH | ADIF spec fallback rule verified WebSearch; LoTW error pattern confirmed via community sources |
| ADIF lat/lon format spec (Pitfall 19) | MEDIUM | Training data; verify against ADIF 3.1.7 spec before implementation |

---

## Sources

- Direct codebase inspection: `app/auth/models.py`, `app/qso/models.py`, `app/database.py`, `app/qso/service.py`, `app/adif/router.py`, `app/auth/dependencies.py`, `app/main.py`
- ADIF specification (training data + WebSearch): https://adif.org/317/ADIF_317.htm
- ADIF STATION_CALLSIGN vs OPERATOR: https://community.hamrs.app/t/field-day-help-ive-confused-myself-with-adif-station-callsign-and-operator/584 (MEDIUM confidence)
- LoTW developer docs: https://lotw.arrl.org/lotw-help/developer-submit-qsos/?lang=en (HIGH confidence)
- Beanie ODM initialization: https://beanie-odm.dev/tutorial/initialization/ (HIGH confidence)
- Beanie `allow_index_dropping`: WebSearch result referencing beanie-odm.dev/tutorial/initialization/ (HIGH confidence)
- Python `maidenhead` library: https://pypi.org/project/maidenhead/ and https://github.com/space-physics/maidenhead (HIGH confidence — `center=True` parameter confirmed)
- IARU grid center convention: https://en.wikipedia.org/wiki/Maidenhead_Locator_System (HIGH confidence)
- N1MM+ OPERATOR field stamp behavior: https://groups.io/g/N1MMLoggerPlus/topic/operator_field_in_adif_files/73971459 (MEDIUM confidence)
- FastAPI multi-tenant isolation patterns: https://medium.com/@ThinkingLoop/fastapi-multi-tenancy-5-isolation-patterns-that-scale-f381c50e262e (MEDIUM confidence — corroborates known patterns)
