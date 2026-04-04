# Phase 9: QSO Auto-Stamping - Research

**Researched:** 2026-04-04
**Domain:** FastAPI dependency injection, Beanie/MongoDB, QSO service layer extension
**Confidence:** HIGH

## Summary

Phase 9 requires auto-stamping newly created QSOs with profile fields from the authenticated operator's User document. The entire implementation is an extension of the existing `build_qso_dict()` function in `app/qso/service.py`, combined with dependency injection changes in the two QSO creation endpoints.

The core design is straightforward: `build_qso_dict()` receives an optional `User` profile argument. When provided, it conditionally injects `OPERATOR`, `STATION_CALLSIGN`, `MY_GRIDSQUARE`, `MY_RIG`, `MY_ANTENNA`, and `TX_PWR` into the QSO dict — skipping any field that is `None` on the User document. The two creation call sites (REST API `create_qso` and UI `submit_qso`) each already depend on the current user via FastAPI's dependency system; they need only switch from the lightweight callsign dependency to the full `get_current_user`/`get_current_user_cookie` dependency and pass the user to `build_qso_dict()`.

The ADIF import path (`process_import()` in `app/adif/router.py`) calls `build_qso_dict()` with only the bare operator callsign string — no User object. As long as the new `profile` parameter is optional (default `None`), the import path requires zero changes, satisfying STAMP-03 by construction.

**Primary recommendation:** Add an optional `profile: Optional[User] = None` parameter to `build_qso_dict()`; stamp fields only when profile is not None and the relevant profile attribute is not None. Swap the two creation endpoint dependencies from callsign-only to the full User dependency.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI `Depends` | already in use | Dependency injection for current user | Project standard; all auth uses it |
| Beanie `Document` | already in use | User model is a Beanie document with all profile fields | No new libraries needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `Optional` from `typing` | stdlib | Type-hint for optional profile param | Function signature |

**Installation:** No new packages required.

## Architecture Patterns

### Recommended Project Structure
No structural changes — all changes are confined to:
```
app/qso/service.py          # extend build_qso_dict()
app/qso/router.py           # swap dependency, pass user to build_qso_dict()
app/qso/ui_router.py        # swap dependency, pass user to build_qso_dict()
tests/test_qso_stamping.py  # new integration test file
```

### Pattern 1: Optional Profile Parameter on build_qso_dict()
**What:** Add `profile: Optional[User] = None` as a new parameter. When not None, inject profile fields — omit any field whose profile attribute is None. The existing call sites in `process_import()` pass no profile argument and continue to work without modification.

**When to use:** Any time a creation path should respect the operator's profile defaults.

**Example (conceptual):**
```python
from typing import Optional
from app.auth.models import User

def build_qso_dict(body_dict: dict, operator: str, profile: Optional[User] = None) -> dict:
    result = dict(body_dict)
    # ... existing normalisation and parsing logic ...

    result["operator_callsign"] = operator
    result["is_deleted"] = False

    if profile is not None:
        # STAMP-01: always stamp OPERATOR from profile callsign
        result["OPERATOR"] = profile.callsign

        # STAMP-02: STATION_CALLSIGN only when set (not None, not empty string)
        if profile.station_callsign:
            result["STATION_CALLSIGN"] = profile.station_callsign

        # Conditional stamps — omit entirely when None
        if profile.my_gridsquare:
            result["MY_GRIDSQUARE"] = profile.my_gridsquare
        if profile.my_rig:
            result["MY_RIG"] = profile.my_rig
        if profile.my_antenna:
            result["MY_ANTENNA"] = profile.my_antenna
        if profile.tx_pwr is not None:
            result["TX_PWR"] = str(profile.tx_pwr)

    return result
```

Key notes:
- `tx_pwr` is `Optional[float]` so the check must be `is not None` (0.0 is a valid value), then convert to string for ADIF compatibility.
- `station_callsign` uses truthiness check (`if profile.station_callsign:`) because the `ProfileUpdateRequest.normalize_station_callsign` validator already converts empty string to `None` — so `None` and falsy values are the only cases where it should be omitted.

### Pattern 2: Dependency Upgrade in REST API Endpoint
**What:** `create_qso` in `app/qso/router.py` currently uses `get_current_operator_callsign` (returns `str`). Switch to `get_current_user` (returns `User`) and derive the callsign from `user.callsign`.

**Current call site (router.py):**
```python
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_qso(
    body: QSOCreateRequest,
    force: bool = Query(False),
    operator: str = Depends(get_current_operator_callsign),  # <-- returns str
) -> dict:
    merged: dict = {**body.model_dump(exclude_unset=False), **(body.model_extra or {})}
    qso_dict = build_qso_dict(merged, operator)
```

**After change:**
```python
from app.auth.dependencies import get_current_user
from app.auth.models import User

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_qso(
    body: QSOCreateRequest,
    force: bool = Query(False),
    user: User = Depends(get_current_user),  # <-- returns User
) -> dict:
    merged: dict = {**body.model_dump(exclude_unset=False), **(body.model_extra or {})}
    qso_dict = build_qso_dict(merged, user.callsign, profile=user)
```

`get_current_user` already fetches the full User document from MongoDB (`User.find_one({"username": username})`), so it will include all profile fields — no extra DB call needed.

### Pattern 3: Dependency Upgrade in UI Endpoint
**What:** `submit_qso` in `app/qso/ui_router.py` currently uses `get_current_operator_callsign_cookie`. Switch to `get_current_user_cookie` (returns `User`) and derive callsign from `user.callsign`.

**Current call site (ui_router.py):**
```python
@ui_router.post("/qsos", response_class=HTMLResponse)
async def submit_qso(
    ...
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    qso_dict = build_qso_dict(
        {k: v for k, v in form_data.items() if v is not None},
        operator=callsign,
    )
```

**After change:**
```python
from app.auth.dependencies import get_current_user_cookie

@ui_router.post("/qsos", response_class=HTMLResponse)
async def submit_qso(
    ...
    user: User = Depends(get_current_user_cookie),
):
    callsign = user.callsign
    qso_dict = build_qso_dict(
        {k: v for k, v in form_data.items() if v is not None},
        operator=callsign,
        profile=user,
    )
```

Note: `callsign` is still needed in `submit_qso` for the `find_duplicate` call and the template response — so it must be derived from `user.callsign` and kept as a local variable.

### Pattern 4: ADIF Import Path — No Change Required
`process_import()` in `app/adif/router.py` calls:
```python
qso_dict = build_qso_dict(record, operator)
```
This passes no `profile` argument. Since the new parameter defaults to `None`, this call is unchanged and auto-stamping is not applied — satisfying STAMP-03 by construction. No changes needed to `app/adif/router.py`.

### Anti-Patterns to Avoid
- **Don't add a new `get_current_user_with_profile` dependency:** The existing `get_current_user` already returns the full User document including profile fields. No new dependency needed.
- **Don't fetch User inside build_qso_dict():** The service function must remain a pure synchronous function. Async DB fetches belong in the router.
- **Don't inject empty strings for absent profile fields:** An absent field must be completely absent from the QSO dict (not `""` or `None`). STAMP-02 is explicit: "omitted entirely when blank — not empty string."
- **Don't modify process_import() to opt-out:** The right design is opt-in via an optional parameter. The import path never passes a profile, so it can never accidentally stamp.
- **Don't guard against missing User profile at the router level:** If the user has no profile fields set, `profile.station_callsign` etc. are already `None` — the conditional checks in `build_qso_dict()` handle this. Success Criterion 3 (operator with no profile can still log QSOs) is satisfied by the `if profile.X` guards.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fetching authenticated user | Custom DB lookup in route | `get_current_user` / `get_current_user_cookie` dependency | Already implemented; already fetches full User document |
| Profile field access | Extra profile fetch | `user.station_callsign`, `user.my_gridsquare`, etc. | User document already has all profile fields as Optional attributes |

## Common Pitfalls

### Pitfall 1: tx_pwr Zero Value
**What goes wrong:** Using `if profile.tx_pwr:` would skip stamping when `tx_pwr = 0.0` (a valid value meaning 0 watts).
**Why it happens:** Python's truthiness treats `0.0` as falsy.
**How to avoid:** Use `if profile.tx_pwr is not None:`.
**Warning signs:** Test with `tx_pwr=0.0` in profile — QSO should get `TX_PWR` stamped.

### Pitfall 2: station_callsign Empty String vs None
**What goes wrong:** The validator in `ProfileUpdateRequest` normalizes empty string to `None`, but the User document might theoretically have `station_callsign = ""` if set before the validator existed (unlikely in this project but worth guarding).
**Why it happens:** ADIF importers and LoTW reject empty STATION_CALLSIGN fields.
**How to avoid:** Use `if profile.station_callsign:` (truthiness) which catches both `None` and `""`. This is consistent with the prior decision "STATION_CALLSIGN omitted entirely when blank."

### Pitfall 3: Existing Tests Breaking
**What goes wrong:** Existing `test_qso_api.py` creates users without profile fields and checks that QSOs do NOT have unexpected extra fields.
**Why it happens:** If the stamping logic injects `None`-valued keys, they appear in the QSO response.
**How to avoid:** Only inject fields whose profile values are not None/falsy. Tests creating users without profiles should see no stamp fields in the response.

### Pitfall 4: Import Path Getting Stamped
**What goes wrong:** A refactor of `process_import()` accidentally passes a User object.
**Why it happens:** Copy-paste from router code.
**How to avoid:** Verify `process_import` signature only takes `raw: bytes, operator: str`. The test suite should include an ADIF import test asserting that `OPERATOR` field is absent from imported QSO documents.

### Pitfall 5: conftest.py Not Including User Model
**What goes wrong:** New test file for stamping creates Users but `init_beanie` in the test fixture might not register the User model.
**Why it happens:** `tests/conftest.py` only registers `[QSO]` in `test_db`. `test_qso_api.py` uses its own `qso_db` fixture that registers `[User, QSO]`.
**How to avoid:** The new test file (`test_qso_stamping.py`) must use its own fixture (like `qso_db`) that registers both User and QSO — or create a new fixture. Do not modify the shared `conftest.py`.

## Code Examples

### Current build_qso_dict() signature
```python
# Source: app/qso/service.py
def build_qso_dict(body_dict: dict, operator: str) -> dict:
```

### Current REST API create_qso dependency
```python
# Source: app/qso/router.py
async def create_qso(
    body: QSOCreateRequest,
    force: bool = Query(False),
    operator: str = Depends(get_current_operator_callsign),
) -> dict:
    merged: dict = {**body.model_dump(exclude_unset=False), **(body.model_extra or {})}
    qso_dict = build_qso_dict(merged, operator)
```

### Current UI submit_qso dependency
```python
# Source: app/qso/ui_router.py
async def submit_qso(
    ...
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    qso_dict = build_qso_dict(
        {k: v for k, v in form_data.items() if v is not None},
        operator=callsign,
    )
```

### Current ADIF import — no change needed
```python
# Source: app/adif/router.py — process_import()
qso_dict = build_qso_dict(record, operator)
# operator is a str, no profile argument → no stamping
```

### User model profile fields (confirmed present)
```python
# Source: app/auth/models.py
station_callsign: Optional[str] = None
my_gridsquare: Optional[str] = None
my_rig: Optional[str] = None
my_antenna: Optional[str] = None    # ADIF 3.1.6 field name MY_ANTENNA (not MY_ANT)
tx_pwr: Optional[float] = None      # watts
```

### Existing auth dependencies available
```python
# Source: app/auth/dependencies.py
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:     # Bearer auth
async def get_current_user_cookie(access_token: str | None = Cookie(...)) -> User:  # Cookie auth
```

### Test fixture pattern to follow
```python
# Source: tests/test_qso_api.py (qso_db fixture)
@pytest_asyncio.fixture(scope="function")
async def qso_db():
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_qso_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_qso_test")
    await client.aclose()
```

The new stamping test file should use the same pattern with a distinct DB name (e.g., `ollog_stamping_test`).

## Key Facts for Test Planning

**What tests are needed (integration, live MongoDB):**

1. **STAMP-01**: Create user with callsign `W1AW`, no other profile fields. POST a QSO. Assert response has `OPERATOR == "W1AW"`.

2. **STAMP-02a**: Create user with `station_callsign = "W1AW/M"`. POST a QSO. Assert `STATION_CALLSIGN == "W1AW/M"` in response.

3. **STAMP-02b**: Create user with `station_callsign = None`. POST a QSO. Assert `STATION_CALLSIGN` key is ABSENT from response (not `None`, not `""`).

4. **All profile fields**: Create user with all profile fields set. POST a QSO. Assert `MY_GRIDSQUARE`, `MY_RIG`, `MY_ANTENNA`, `TX_PWR` are present in response with correct values.

5. **No-profile operator**: Create user with no profile fields set. POST a QSO. Assert no null keys were injected (OPERATOR is present since callsign is always available, but no other profile keys appear).

6. **STAMP-03 (ADIF import not stamped)**: POST an ADIF import. Assert accepted QSO documents do NOT have an `OPERATOR` field injected from profile.

7. **unit test**: `build_qso_dict()` called with `profile=None` returns no profile-derived keys. Called with a mock profile returns the expected keys/values.

## Open Questions

1. **Should OPERATOR stamp be skipped if the submitted QSO already contains an OPERATOR field?**
   - What we know: The requirements say "auto-stamped with OPERATOR from the operator's profile — no manual entry of OPERATOR is required" — suggesting it should always be set from profile, not user-supplied.
   - What's unclear: Whether a user submitting `OPERATOR` manually via the API should be overridden or respected.
   - Recommendation: Phase 9 should unconditionally set `OPERATOR` from the profile, overriding any user-supplied value. This matches "no manual entry required" and prevents spoofing.

2. **TX_PWR type in QSO document: float or string?**
   - What we know: Profile stores `tx_pwr` as `Optional[float]`. ADIF convention is a string field.
   - What's unclear: Whether to store as float or string in the QSO document.
   - Recommendation: Store as string for ADIF consistency (all other ADIF fields in model_extra are strings). Use `str(profile.tx_pwr)`.

## Sources

### Primary (HIGH confidence)
- Direct source code inspection: `app/qso/service.py` — `build_qso_dict()` signature and implementation
- Direct source code inspection: `app/qso/router.py` — `create_qso` endpoint, dependency usage
- Direct source code inspection: `app/qso/ui_router.py` — `submit_qso` endpoint, dependency usage
- Direct source code inspection: `app/adif/router.py` — `process_import()` function, confirmed no profile
- Direct source code inspection: `app/auth/dependencies.py` — `get_current_user`, `get_current_user_cookie`
- Direct source code inspection: `app/auth/models.py` — User document profile fields
- Direct source code inspection: `app/profile/schemas.py` — `station_callsign` normalization validator
- Direct source code inspection: `tests/test_qso_api.py` — test structure, fixture pattern

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all code inspected directly from source, no external libraries needed
- Architecture: HIGH — call sites and dependency chain fully traced; change surface is minimal and well-defined
- Pitfalls: HIGH — derived from direct reading of validator behavior, Beanie patterns, and existing test patterns
- Test plan: HIGH — based on direct reading of requirements and existing test file structure

**Research date:** 2026-04-04
**Valid until:** Stable — no external dependencies; valid until project code changes
