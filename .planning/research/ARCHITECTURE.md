# Architecture Patterns

**Domain:** Operator profile integration — ham radio logbook (v1.1 milestone)
**Researched:** 2026-04-04
**Confidence:** HIGH — based on direct inspection of the live codebase

---

## Context: What Already Exists

The existing codebase has these components relevant to this milestone:

| Existing Component | Location | Notes |
|-------------------|----------|-------|
| `User` Beanie Document | `app/auth/models.py` | `username`, `callsign`, `hashed_password`, `role`, `enabled` — `model_config` has `extra` not set (defaults to `ignore`) |
| `QSO` Beanie Document | `app/qso/models.py` | `extra="allow"` — stores arbitrary ADIF fields |
| `build_qso_dict()` | `app/qso/service.py` | Constructs QSO dict from form input + injects `operator_callsign` |
| `get_current_user` / `get_current_operator_callsign` | `app/auth/dependencies.py` | Returns `User` doc or `user.callsign` string |
| QSO creation flow | `app/qso/router.py` `create_qso()`, `app/qso/ui_router.py` `submit_qso()` | Two call sites — both delegate to `build_qso_dict()` |
| `init_beanie()` | `app/database.py` | Document models list must be updated for any new Beanie document |

---

## Recommended Architecture

### Decision: Embed Profile Fields Directly in `User` — Do Not Create a Separate Collection

**Rationale:**

1. **Beanie supports it cleanly.** The `User` document currently uses `ConfigDict(populate_by_name=True)` with no `extra` setting. Adding `Optional` fields to the class body requires zero schema migration — MongoDB documents without the new fields simply return `None` for those attributes.

2. **No join problem.** Profile data is always accessed in the context of the authenticated user. A separate `OperatorProfile` collection would require a second DB round-trip on every profile read, or a `fetch_links()` call in Beanie. Embedding eliminates that entirely.

3. **Profile data is small and user-scoped.** Grid locators, rig descriptions, station callsigns — these are a handful of string fields, not a growing subdocument list. Embedding does not create document bloat.

4. **Separate collection does not solve any real problem here.** It would be appropriate if profile data were independently queried, shared across users, or had a different access control boundary. None of those apply.

**What to change in `User`:** Add `Optional` fields for all profile data. The existing `model_config = ConfigDict(populate_by_name=True)` is sufficient — do not add `extra="allow"` (profile fields are declared, not arbitrary).

---

## Component Boundaries (New vs Modified)

### New Components

| Component | Location | Responsibility |
|-----------|----------|---------------|
| Profile fields on `User` | `app/auth/models.py` | Store all MY_* ADIF fields, name, QTH, email, grid, lat/lon |
| Profile Pydantic schemas | `app/auth/models.py` or new `app/profile/schemas.py` | `ProfileUpdateRequest` (validates form input), `ProfileResponse` (read shape) |
| Grid conversion utility | `app/utils.py` or `app/profile/grid.py` | `grid_to_latlon()` and `latlon_to_grid()` wrappers around `maidenhead` library |
| Profile API router | `app/profile/router.py` | `GET /api/profile` and `PATCH /api/profile` — Bearer auth |
| Profile UI router | `app/profile/ui_router.py` | `GET /log/profile` and `POST /log/profile` — cookie auth, HTMX form |
| Profile template | `templates/log/profile.html` | Settings page form |

### Modified Components

| Component | What Changes | Why |
|-----------|-------------|-----|
| `app/auth/models.py` | Add profile fields to `User` | Core storage decision |
| `app/qso/service.py` `build_qso_dict()` | Accept optional `profile` param; stamp MY_* fields | Auto-stamp logic lives here |
| `app/qso/router.py` `create_qso()` | Fetch `User` doc, pass profile to `build_qso_dict()` | REST API QSO creation path |
| `app/qso/ui_router.py` `submit_qso()` | Fetch `User` doc, pass profile to `build_qso_dict()` | UI QSO creation path |
| `app/database.py` | No change if profile stays in `User` | Profile fields are on existing document |
| `app/main.py` | Register new profile routers | Wire profile routers into app |
| `templates/log/form.html` and nav partials | Add "Profile / Settings" nav link | UI navigation |

---

## `User` Model After Profile Fields

```python
class User(Document):
    model_config = ConfigDict(populate_by_name=True)

    # Auth fields (unchanged)
    username: str
    hashed_password: str
    callsign: str
    role: str = "operator"
    enabled: bool = True

    # Profile — personal info
    name: Optional[str] = None          # ADIF MY_NAME equivalent
    email: Optional[str] = None
    qth: Optional[str] = None           # City/location free text

    # Station identification
    station_callsign: Optional[str] = None  # ADIF STATION_CALLSIGN (club call etc.)

    # Location
    gridsquare: Optional[str] = None    # Maidenhead, stored uppercase, e.g. "FN31pr"
    lat: Optional[float] = None         # WGS84, derived from gridsquare or entered directly
    lon: Optional[float] = None         # WGS84

    # Station equipment — ADIF MY_* fields
    my_rig: Optional[str] = None
    my_ant: Optional[str] = None
    my_pwr: Optional[str] = None        # Stored as string per ADIF TX_PWR convention
    my_city: Optional[str] = None
    my_country: Optional[str] = None
    my_state: Optional[str] = None
    my_dxcc: Optional[str] = None
    my_cont: Optional[str] = None
    my_iota: Optional[str] = None
    my_cnty: Optional[str] = None

    class Settings:
        name = "users"
        indexes = [...]  # unchanged
```

All new fields are `Optional[str | float] = None`. Existing `User` documents with none of these fields continue to load correctly — Beanie/Pydantic fills `None` for absent keys.

---

## Data Flow: QSO Auto-Stamping

The auto-stamp behavior must work identically for both the REST API path and the UI path. Both already call `build_qso_dict()`. The modification is minimal.

### Current Flow (both paths)

```
JWT -> callsign string -> build_qso_dict(body_dict, operator=callsign) -> QSO dict
```

### New Flow

```
JWT -> User document -> build_qso_dict(body_dict, operator=user.callsign, profile=user) -> QSO dict
```

The dependency injection already returns the full `User` document via `get_current_user`. Both `create_qso()` (REST) and `submit_qso()` (UI) currently call `get_current_operator_callsign` which strips the `User` to just a string. Change the dependency to `get_current_user` (or `get_current_user_cookie` for UI routes), then derive both the callsign and profile from the same document. No extra DB round-trip.

### `build_qso_dict()` Changes

```python
def build_qso_dict(body_dict: dict, operator: str, profile=None) -> dict:
    result = dict(body_dict)
    # ... existing normalization unchanged ...

    result["operator_callsign"] = operator
    result["is_deleted"] = False

    # Always stamp OPERATOR (the logging callsign) as an explicit ADIF field
    if "OPERATOR" not in result:
        result["OPERATOR"] = operator

    # Stamp profile fields only if not already provided in body_dict
    if profile is not None:
        if profile.station_callsign and "STATION_CALLSIGN" not in result:
            result["STATION_CALLSIGN"] = profile.station_callsign
        if profile.name and "MY_NAME" not in result:
            result["MY_NAME"] = profile.name
        if profile.gridsquare and "MY_GRIDSQUARE" not in result:
            result["MY_GRIDSQUARE"] = profile.gridsquare
        if profile.my_rig and "MY_RIG" not in result:
            result["MY_RIG"] = profile.my_rig
        if profile.my_ant and "MY_ANTENNA" not in result:
            result["MY_ANTENNA"] = profile.my_ant
        if profile.my_pwr and "TX_PWR" not in result:
            result["TX_PWR"] = profile.my_pwr
        # ... additional MY_* fields ...

    return result
```

**Key behavior:** Body fields always win over profile defaults. This allows an operator to override their default station when logging from a different location — they can send `MY_GRIDSQUARE` in the QSO body and it takes precedence.

**OPERATOR field:** ADIF `OPERATOR` field is the callsign of the person logging — the same value as `_operator`. Stamping it as an explicit QSO field ensures it appears in ADIF export without touching the serializer.

---

## Data Flow: Profile Read and Update

```
GET /log/profile
  -> get_current_user_cookie() -> User document
    -> Render profile.html with user fields pre-filled

POST /log/profile  (HTMX form)
  -> get_current_user_cookie() -> User document
    -> Validate ProfileUpdateRequest (Pydantic schema)
      -> If gridsquare changed: derive lat/lon via grid_to_latlon()
      -> If lat/lon changed directly: derive gridsquare via latlon_to_grid()
      -> user.set({updated_fields})
        -> Return success partial (HTMX swap)
```

---

## Maidenhead Grid Conversion

### Where It Lives

`app/profile/grid.py` — keeps the module focused. `app/utils.py` is already small but is auth-adjacent; grid conversion is profile-specific.

### Library Choice

Use the **`maidenhead`** package (PyPI: `maidenhead`, maintained by space-physics).

- Pure Python, no compiled dependencies
- Well-established in the ham radio Python ecosystem
- API: `mh.to_maiden(lat, lon, level)` for lat/lon to grid; `mh.to_location(grid, center=True)` for grid to lat/lon center point
- `center=True` returns the center of the grid square — correct for display and distance calculation

Confidence: MEDIUM — confirmed as dominant PyPI library for this purpose via search. Specific function signatures (`to_maiden`, `to_location`, `center` kwarg) confirmed via search results. Validate exact API against installed version before coding.

```python
# app/profile/grid.py
import maidenhead as mh

def grid_to_latlon(grid: str) -> tuple[float, float] | None:
    """Convert Maidenhead grid locator to (lat, lon) center point.
    Returns None if the grid string is invalid.
    """
    try:
        lat, lon = mh.to_location(grid.upper(), center=True)
        return lat, lon
    except Exception:
        return None

def latlon_to_grid(lat: float, lon: float, precision: int = 3) -> str:
    """Convert WGS84 lat/lon to Maidenhead grid locator.
    precision=3 gives 6-character locator (field+square+subsquare).
    Returns uppercase grid string e.g. "FN31pr".
    """
    return mh.to_maiden(lat, lon, level=precision)
```

**Install:** `pip install maidenhead`

### Validation Rule

Grid locators are validated on profile save: 4, 6, or 8 characters matching the Maidenhead pattern `[A-R]{2}[0-9]{2}([a-x]{2}([0-9]{2})?)?` (case-insensitive). Reject anything else with a clear error message. When a valid grid is saved, derive and overwrite lat/lon immediately.

### Bidirectional Sync Rule

- If operator enters **grid locator**: derive and overwrite lat/lon.
- If operator enters **lat/lon directly**: derive and overwrite gridsquare (to 6-character precision).
- Never leave grid and lat/lon out of sync after a save.

---

## Profile API Shape

### `GET /api/profile`

Returns the authenticated operator's profile fields (not auth fields).

```json
{
  "callsign": "W1AW",
  "name": "Hiram Percy Maxim",
  "email": "op@example.com",
  "qth": "Hartford, CT",
  "station_callsign": null,
  "gridsquare": "FN31pr",
  "lat": 41.708,
  "lon": -72.708,
  "my_rig": "Icom IC-7300",
  "my_ant": "G5RV",
  "my_pwr": "100",
  "my_city": "Hartford",
  "my_state": "CT",
  "my_country": "United States",
  "my_dxcc": "291",
  "my_cont": "NA",
  "my_iota": null,
  "my_cnty": null
}
```

### `PATCH /api/profile`

Accepts partial updates. Any field not included in the body is left unchanged. Validates grid locator format if present. Returns updated profile.

---

## MongoDB Document Impact

No migration required. The `users` collection documents gain new optional fields on first profile save. The existing unique index on `username` is unchanged. No new indexes needed — profile is always read by authenticated user identity, which hits the `username` unique index directly.

**New `users` document shape (after first profile save):**

```json
{
  "_id": "ObjectId(...)",
  "username": "w1aw",
  "hashed_password": "argon2...",
  "callsign": "W1AW",
  "role": "operator",
  "enabled": true,
  "name": "Hiram Percy Maxim",
  "email": "op@example.com",
  "qth": "Hartford, CT",
  "station_callsign": null,
  "gridsquare": "FN31pr",
  "lat": 41.708,
  "lon": -72.708,
  "my_rig": "Icom IC-7300",
  "my_ant": "G5RV",
  "my_pwr": "100"
}
```

**QSO documents after auto-stamp:**

```json
{
  "_operator": "W1AW",
  "CALL": "K9XYZ",
  "OPERATOR": "W1AW",
  "STATION_CALLSIGN": "W1AW",
  "MY_NAME": "Hiram Percy Maxim",
  "MY_GRIDSQUARE": "FN31pr",
  "MY_RIG": "Icom IC-7300",
  "MY_ANTENNA": "G5RV",
  "TX_PWR": "100",
  "...": "..."
}
```

Auto-stamped fields are regular ADIF fields in the QSO document. Because `QSO` uses `extra="allow"`, they store and export losslessly without any change to the serializer.

---

## Patterns to Follow

### Pattern 1: Profile Embedded in User — Single Document Fetch

The authenticated `User` document is already fetched on every protected request via `get_current_user`. Profile data comes for free. No second collection, no `fetch_links()`, no extra query.

### Pattern 2: Auto-Stamp in Service Layer, Not Route Layer

`build_qso_dict()` in `app/qso/service.py` is the single function that constructs QSO documents. Profile stamping belongs here — it is business logic (what goes into a QSO), not routing logic (what HTTP request does what). Both the REST and UI routers call this function, so the stamp happens in exactly one place.

### Pattern 3: Body Wins Over Profile Defaults

When the QSO request body explicitly includes a MY_* field (e.g., during ADIF import of a legacy file that already has `MY_RIG`), the body value is preserved. Profile values are defaults, not overrides.

### Pattern 4: ADIF Import Bypass

Profile auto-stamping applies only to new QSOs logged interactively (REST POST, UI form). `process_import()` in `app/adif/router.py` must NOT auto-stamp profile fields — imported records already have their own MY_* values from when they were originally logged. Stamping over them would corrupt historical data.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Separate `OperatorProfile` Collection

**What goes wrong:** Every QSO creation requires a second DB round-trip to fetch profile, or Beanie `fetch_links()` with `LazyRef`. The `init_beanie()` document list grows. A foreign key relationship exists that Beanie handles loosely (no enforced referential integrity in MongoDB).

**Instead:** Embed profile fields in `User`. Beanie adds new optional fields to existing documents transparently. No migration, no extra query.

### Anti-Pattern 2: Nested Sub-Document for Profile

**What goes wrong:** `User.profile.gridsquare` vs `User.gridsquare` — the extra nesting adds dot-notation path complexity in Beanie `$set` operations (`{"profile.gridsquare": ...}`) and in Jinja2 templates. Sub-documents are appropriate for repeated/list structures. A flat set of optional string fields does not warrant nesting.

**Instead:** Flat optional fields directly on `User`.

### Anti-Pattern 3: Auto-Stamping During ADIF Import

**What goes wrong:** ADIF files being imported already contain `MY_RIG`, `MY_ANTENNA`, `OPERATOR` etc. from when they were originally logged. Overwriting with current profile values corrupts historical records — the wrong rig, wrong grid square from a different year.

**Instead:** `process_import()` stays as-is. Profile stamping only in the interactive QSO creation paths (`create_qso()` and `submit_qso()`).

### Anti-Pattern 4: Computing Grid/Lat/Lon at Query Time

**What goes wrong:** Computing `to_location(grid)` on every QSO creation or every API read is waste. More importantly, operators may want to fine-tune lat/lon independently of the grid (precise location vs. grid center).

**Instead:** Derive lat/lon on profile save and persist both values. They are independent stored fields that happen to start from a derived value.

---

## Build Order for This Milestone

Dependencies flow from data model outward to UI:

```
1. User model profile fields  (app/auth/models.py)
      Additive — Optional fields, no migration, no test infrastructure changes.

2. Grid conversion utility  (app/profile/grid.py)
      Pure function, no DB dependency. Install maidenhead package.
      Testable in complete isolation.

3. Profile Pydantic schemas  (ProfileUpdateRequest, ProfileResponse)
      Depends on: User model field names being defined.

4. Profile service logic
      Grid sync on update (grid -> lat/lon and lat/lon -> grid).
      Depends on: grid utility, User model.

5. Profile API router  (GET /api/profile, PATCH /api/profile)
      Depends on: schemas, service logic, existing get_current_user dependency.
      Wire into app/main.py.

6. build_qso_dict() auto-stamp addition  (app/qso/service.py)
      Depends on: User model profile fields being defined.
      Signature change is backward-compatible (profile=None default).

7. QSO creation route updates  (app/qso/router.py, app/qso/ui_router.py)
      Switch from get_current_operator_callsign to get_current_user.
      Pass user doc to build_qso_dict as profile.
      Depends on: step 6.

8. Profile UI router + template  (app/profile/ui_router.py, templates/log/profile.html)
      Depends on: steps 3–4.
      Add nav link in templates/log/form.html and log.html.
      Wire into app/main.py.
```

**Critical path:** Step 1 (User model) unlocks steps 3, 6, and 7. Steps 2 and 4 are the only grid-specific work. Steps 5 and 8 are the user-facing surfaces and can be built incrementally after the data layer is verified.

---

## Integration Point Risk Summary

| Integration Point | Change Type | Risk |
|-------------------|-------------|------|
| `User` model — add profile fields | Additive (backward-compatible) | Low — Optional fields, no migration required |
| `build_qso_dict()` — add `profile` param | Additive (`profile=None` default) | Low — all existing callers unaffected |
| `create_qso()` — change dependency | Modified — swap to `get_current_user` | Medium — derive callsign from `user.callsign`; test both REST and duplicate-override paths |
| `submit_qso()` — change dependency | Modified — swap to `get_current_user_cookie` | Medium — same risk; also affects duplicate warning flow |
| `process_import()` | No change | None |
| ADIF export serializer | No change | None — MY_* fields already export as model_extra |
| `init_beanie()` document list | No change if profile stays in User | None |

---

## Sources

- Live codebase inspection: `/Users/royco/ollog/app/` (all Python modules read directly, 2026-04-04)
- PyPI `maidenhead` library: https://pypi.org/project/maidenhead/
- `maidenhead` GitHub: https://github.com/space-physics/maidenhead
- ADIF 3.1.7 specification field names (MY_* fields, OPERATOR, STATION_CALLSIGN): https://adif.org/317/ADIF_317.htm
