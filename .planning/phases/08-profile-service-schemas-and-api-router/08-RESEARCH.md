# Phase 8: Profile Service, Schemas, and API Router - Research

**Researched:** 2026-04-04
**Domain:** FastAPI PATCH endpoints, Pydantic schemas, Beanie document updates, ADIF field alignment
**Confidence:** HIGH

## Summary

Phase 8 builds two things on top of the existing User model and grid utility from Phase 7: (1) Pydantic request/response schemas for profile GET/PATCH, and (2) the `/api/profile` API router with service-layer grid-to-lat/lon sync. All required libraries are already installed (`pydantic[email]`, `maidenhead`, `beanie`, `fastapi`). No new dependencies.

The auth pattern is fully established: `get_current_user` dependency from `app.auth.dependencies` returns the authenticated `User` document. The router must depend on `get_current_user` (not `get_current_operator_callsign`) since it needs the full User object, not just the callsign string. Operator isolation is automatic — the JWT resolves to a single User document, and no other operator's document is ever touched.

The recommended PATCH pattern is: parse request body as `ProfileUpdateRequest` (all Optional fields), call `model_dump(exclude_unset=True)` to get only provided fields, compute lat/lon if `my_gridsquare` is in the update dict, then apply `await user.update({"$set": update_dict})`. This mirrors the QSO PATCH pattern already in the codebase. The GET pattern is simpler: fetch the current user from JWT, project to `ProfileResponse`, return.

**Primary recommendation:** Follow the QSO PATCH pattern (raw `$set` update) for the profile PATCH endpoint. Use `get_current_user` (returns full User) not `get_current_operator_callsign` (returns callsign string only). MY_ANT in the User model must be renamed to MY_ANTENNA before Phase 8 schema locks in — ADIF 3.1.6 (latest) lists MY_ANTENNA, not MY_ANT.

---

## ADIF Field Name Resolution (Critical Flagged Item)

**Question from prior decisions:** MY_ANT vs MY_ANTENNA — verify against adif.org/317 at Phase 8 planning.

**Finding:** ADIF 3.1.7 does not exist. The latest released version is **ADIF 3.1.6** (updated 2025-09-15). The specification at adif.org/316/ADIF_316.htm lists the antenna field as **`MY_ANTENNA`** (not `MY_ANT`). The field `MY_ANTENNA_INTL` also exists for international character support in ADX.

**MY_ fields confirmed in ADIF 3.1.6 (verified via adif.org/317 which also confirms MY_ANTENNA):**
- MY_ANTENNA, MY_ANTENNA_INTL
- MY_GRIDSQUARE (supports 1-4 pairs = 2/4/6/8 chars)
- MY_RIG, MY_RIG_INTL
- MY_STATE, MY_CITY, MY_COUNTRY, MY_LAT, MY_LON, MY_NAME, MY_POSTAL_CODE

**Decision required:** The `User` model currently stores `my_ant: Optional[str] = None` (from Phase 7). Phase 8 plan 08-01 must either:
1. Rename `my_ant` to `my_antenna` in the User model and in all references, OR
2. Keep `my_ant` in the model as an internal name and expose `MY_ANTENNA` in the schema only

**Recommendation:** Rename `my_ant` → `my_antenna` in `app/auth/models.py`. This is a field on an Optional column with no existing data — no migration needed. The Python attribute name `my_antenna` aligns with ADIF `MY_ANTENNA`, consistent with how `my_gridsquare` aligns with `MY_GRIDSQUARE`.

**Source:** adif.org/317 (redirect target confirmed MY_ANTENNA) and adif.org/316/ADIF_316.htm (latest released spec, 2025-09-15). Confidence: HIGH.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | >=0.135.0 (installed) | API router, dependency injection | Already used throughout codebase |
| beanie | >=2.1.0 (installed) | User document fetch and update | Already used; `update({"$set": ...})` is the established codebase pattern |
| pydantic | >=2.0 (installed) | Request/response schemas, EmailStr, field validation | Already used; v2 semantics required |
| pydantic[email] | >=2.0 (installed in Phase 7) | EmailStr type for email field | Installed in Phase 7; no new install needed |
| maidenhead | >=1.8.0 (installed in Phase 7) | grid_to_latlon utility (app.profile.grid) | Installed in Phase 7; called from service layer |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | >=0.27 (installed dev) | ASGITransport for API integration tests | Used in test_auth.py, test_qso_api.py — same pattern for profile tests |
| pytest-asyncio | >=0.23 (installed dev) | async test support | Required for async endpoint tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `user.update({"$set": dict})` | `user.save()` after field assignment | `save()` replaces full document; `$set` is targeted and mirrors QSO pattern already established |
| `get_current_user` dependency | `get_current_operator_callsign` | callsign dep returns str only; profile endpoint needs full User object |
| Separate `profile` service layer | Logic in router | Service layer is cleaner separation; consistent with qso/service.py pattern |

**No new dependencies required.** All libraries were installed in Phase 7 or earlier.

---

## Architecture Patterns

### Recommended Project Structure
```
app/
├── auth/
│   ├── models.py        # User document — rename my_ant → my_antenna
│   └── dependencies.py  # get_current_user — USE THIS (returns User, not str)
├── profile/
│   ├── __init__.py      # exists (created Phase 7)
│   ├── grid.py          # exists (created Phase 7): grid_to_latlon()
│   ├── schemas.py       # NEW: ProfileUpdateRequest, ProfileResponse
│   ├── service.py       # NEW: update_profile(), get_profile_response()
│   └── router.py        # NEW: GET/PATCH /api/profile

tests/
├── test_profile_api.py  # NEW: GET, PATCH, isolation, profile-less operator tests
```

### Pattern 1: Pydantic Schema for PATCH with All-Optional Fields
**What:** A request model with every field Optional[T] = None. Uses `model_dump(exclude_unset=True)` to capture only fields explicitly provided in the JSON body.
**When to use:** PATCH endpoint where any subset of fields can be updated.

```python
# Source: FastAPI official docs (fastapi.tiangolo.com/tutorial/body-updates/)
# Verified: 2026-04-04
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
import re

MY_GRIDSQUARE_RE = re.compile(
    r"^[A-Ra-r]{2}[0-9]{2}([A-Xa-x]{2})?$"
)

class ProfileUpdateRequest(BaseModel):
    station_callsign: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    qth: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    my_gridsquare: Optional[str] = None
    my_rig: Optional[str] = None
    my_antenna: Optional[str] = None
    tx_pwr: Optional[float] = None

    @field_validator("my_gridsquare")
    @classmethod
    def validate_gridsquare(cls, v):
        if v is not None and not MY_GRIDSQUARE_RE.match(v):
            raise ValueError(f"Invalid MY_GRIDSQUARE format: {v!r}")
        return v.upper() if v else v
```

Note: `station_callsign` should be omitted from the response (not stored as empty string) when blank — per prior decision. Handle at service layer by converting `""` to `None` or stripping empty strings.

### Pattern 2: ProfileResponse Schema
**What:** A response model that projects User fields to the API contract. Excludes internal User fields (username, hashed_password, role, enabled).

```python
class ProfileResponse(BaseModel):
    callsign: str            # from user.callsign (always present)
    station_callsign: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None   # str not EmailStr for response
    qth: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    my_gridsquare: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    my_rig: Optional[str] = None
    my_antenna: Optional[str] = None
    tx_pwr: Optional[float] = None
```

### Pattern 3: Service Layer — update_profile()
**What:** Takes the current User document and a dict of validated update fields, handles grid sync, applies `$set` update.

```python
# Source: mirrors app/qso/router.py PATCH pattern (verified in codebase)
from app.profile.grid import grid_to_latlon
from app.auth.models import User

async def update_profile(user: User, updates: dict) -> User:
    """Apply partial profile updates to user document.

    If my_gridsquare is updated, recomputes latitude/longitude.
    If my_gridsquare is set to None, clears latitude/longitude.
    """
    if "my_gridsquare" in updates:
        grid = updates["my_gridsquare"]
        if grid is not None:
            lat, lon = grid_to_latlon(grid)
            updates["latitude"] = lat
            updates["longitude"] = lon
        else:
            updates["latitude"] = None
            updates["longitude"] = None

    if updates:
        await user.update({"$set": updates})

    # Re-fetch to return current state
    return await User.get(user.id)
```

### Pattern 4: API Router Structure
**What:** APIRouter with prefix `/api/profile`, auth via `get_current_user` dependency, no callsign parameter.

```python
# Source: mirrors app/auth/router.py and app/qso/router.py patterns (verified)
from fastapi import APIRouter, Depends, status
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.profile.schemas import ProfileUpdateRequest, ProfileResponse
from app.profile.service import update_profile

router = APIRouter(prefix="/api/profile", tags=["profile"])

@router.get("/", response_model=ProfileResponse, status_code=status.HTTP_200_OK)
async def get_profile(user: User = Depends(get_current_user)) -> ProfileResponse:
    return ProfileResponse.model_validate(user.model_dump())

@router.patch("/", response_model=ProfileResponse, status_code=status.HTTP_200_OK)
async def patch_profile(
    body: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    updates = body.model_dump(exclude_unset=True)
    updated_user = await update_profile(user, updates)
    return ProfileResponse.model_validate(updated_user.model_dump())
```

### Pattern 5: Router Registration in main.py
**What:** Add profile router to app in `app/main.py`, following the established include_router pattern.

```python
# Source: app/main.py pattern (verified in codebase)
from app.profile.router import router as profile_router
app.include_router(profile_router)
```

### Pattern 6: Integration Test Pattern (AsyncClient + local db fixture)
**What:** Each test file has its own db fixture that initializes Beanie with `[User, QSO]` and creates test users via `_create_user()`. Token obtained via `/auth/token` POST.

```python
# Source: tests/test_qso_api.py and tests/test_auth.py (verified in codebase)
@pytest_asyncio.fixture(scope="function")
async def profile_db():
    client = AsyncMongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
    db = client["ollog_profile_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_profile_test")
    await client.aclose()
```

Note: conftest.py must NOT be modified (owned by 01-02). Each test file owns its own fixture.

### Anti-Patterns to Avoid
- **Using `get_current_operator_callsign` in profile routes:** This dependency returns `str` (callsign only). Profile routes need the full `User` object — use `get_current_user` instead.
- **Accepting callsign in query params or body:** Locked decision — operator identity from JWT only.
- **Setting `latitude`/`longitude` in the schema as updatable by client:** These are derived fields, computed server-side from `my_gridsquare`. Never accept them in `ProfileUpdateRequest`.
- **Not re-fetching after `$set`:** `user.update({"$set": ...})` modifies MongoDB but does NOT update the in-memory `user` object. Re-fetch via `User.get(user.id)` to return current state (mirrors QSO PATCH pattern).
- **Using `user.save()` for partial updates:** `save()` replaces the full document including internal fields. Stick with `$set` for safety.
- **Storing empty string for station_callsign:** Per prior decision, omit STATION_CALLSIGN entirely (None) when blank, not empty string.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Email validation | Regex email check | `pydantic.EmailStr` | Already in ecosystem, RFC-correct |
| Grid format validation | Custom regex | Use existing `grid_to_latlon()` in `app.profile.grid` | Already implemented in Phase 7 with correct character-class checks |
| Partial update dict construction | Manual field-by-field copy | `body.model_dump(exclude_unset=True)` | Built-in Pydantic v2 feature; handles the unset vs None distinction correctly |
| JWT user lookup | Query User by callsign from body | `get_current_user` dependency | Already implemented, tested; operator isolation is automatic |

**Key insight:** `model_dump(exclude_unset=True)` is the canonical Pydantic v2 way to get only the fields the client explicitly sent. Do not iterate `model_fields` or compare to None — that conflates "not sent" with "explicitly set to null".

---

## Common Pitfalls

### Pitfall 1: get_current_user vs get_current_operator_callsign
**What goes wrong:** Using `get_current_operator_callsign` in the profile router compiles fine but returns `str`, not `User`. The service layer then has no User object to update.
**Why it happens:** Both are valid dependencies; easy to grab the wrong one.
**How to avoid:** Profile routes always use `get_current_user` (returns `User`). QSO routes use `get_current_operator_callsign` (returns `str`). Check `app/auth/dependencies.py` when in doubt.
**Warning signs:** `AttributeError: 'str' object has no attribute 'update'` at runtime.

### Pitfall 2: latitude/longitude not clearing when gridsquare is set to None
**What goes wrong:** Client PATCHes `my_gridsquare: null` to clear the grid. Service only syncs lat/lon when grid is non-null. Stale lat/lon persists.
**Why it happens:** Sync logic checks `if grid is not None` but forgets the null case.
**How to avoid:** In `update_profile()`, always handle the `my_gridsquare is None` branch explicitly — set `latitude: None, longitude: None`.
**Warning signs:** GET after PATCH shows null gridsquare but non-null lat/lon.

### Pitfall 3: exclude_unset=True vs exclude_none=True confusion
**What goes wrong:** Using `exclude_none=True` drops fields the client explicitly set to null (intentional clear). Using `exclude_unset=True` correctly keeps explicit nulls while dropping fields not sent.
**Why it happens:** Both sound similar; documentation distinction is subtle.
**How to avoid:** Always use `exclude_unset=True` for PATCH payloads. `exclude_none=True` is wrong for partial updates.
**Warning signs:** Client sends `{"my_gridsquare": null}` to clear grid; server ignores it.

### Pitfall 4: $set does not update in-memory object
**What goes wrong:** After `await user.update({"$set": updates})`, returning `ProfileResponse.model_validate(user.model_dump())` returns stale data — the in-memory `user` object is unchanged.
**Why it happens:** Beanie's `update()` fires the MongoDB operation but does not mutate the Python object.
**How to avoid:** Re-fetch: `updated = await User.get(user.id); return ProfileResponse.model_validate(updated.model_dump())`. Mirrors the QSO PATCH pattern in `app/qso/router.py` lines 200-201.
**Warning signs:** GET after PATCH returns old values despite DB having new values.

### Pitfall 5: model_validate on User with profile-less operator
**What goes wrong:** A brand new operator has all profile fields as `None`. `ProfileResponse.model_validate(user.model_dump())` must succeed without errors.
**Why it happens:** If any ProfileResponse field lacks a default, Pydantic raises on None.
**How to avoid:** All ProfileResponse fields except `callsign` must be `Optional[T] = None`. Test with a user that has no profile fields set.
**Warning signs:** GET /api/profile returns 500 for new operators with no profile data.

### Pitfall 6: MY_ANTENNA vs MY_ANT in User model
**What goes wrong:** Phase 7 stored the field as `my_ant`. Phase 8 schemas expose it as `MY_ANTENNA` (correct ADIF name). Mismatch causes the value to never round-trip.
**Why it happens:** MY_ANT was a placeholder pending Phase 8 research (per Phase 7 prior decisions).
**How to avoid:** Rename `my_ant` → `my_antenna` in `app/auth/models.py` as part of 08-01 schema work. No migration needed (no existing data, column is Optional=None).
**Warning signs:** GET /api/profile returns `my_ant: "some value"` while schema sends/returns `my_antenna`.

### Pitfall 7: conftest.py User model not registered
**What goes wrong:** `conftest.py` test_db fixture only includes `[QSO]` in init_beanie. Profile API tests need `User` initialized.
**Why it happens:** conftest.py is owned by 01-02 and must not be modified.
**How to avoid:** Profile API test file uses its own local `profile_db` fixture that calls `init_beanie(database=db, document_models=[User, QSO])`. Pattern from `test_qso_api.py` (uses `qso_db` fixture) and `test_auth.py` (uses `auth_db` fixture).
**Warning signs:** `DocumentWasNotInitialized` Beanie error during tests.

---

## Code Examples

### exclude_unset=True — only captures explicitly sent fields
```python
# Source: FastAPI official docs (fastapi.tiangolo.com/tutorial/body-updates/) — verified 2026-04-04
class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

body = ProfileUpdateRequest(name="Alice")    # email not sent
updates = body.model_dump(exclude_unset=True)
# updates = {"name": "Alice"}   ← email omitted because not set
# (NOT {"name": "Alice", "email": None})

body2 = ProfileUpdateRequest(name="Alice", email=None)  # email explicitly null
updates2 = body2.model_dump(exclude_unset=True)
# updates2 = {"name": "Alice", "email": None}  ← email included because explicitly set
```

### Beanie $set update (mirror of QSO PATCH pattern)
```python
# Source: app/qso/router.py lines 197-201 (verified in codebase)
if body:
    await qso.update({"$set": body})
updated = await QSO.get(oid)  # ← re-fetch required; in-memory object not updated
return _qso_to_dict(updated)
```

### grid_to_latlon usage (from Phase 7 implementation)
```python
# Source: app/profile/grid.py (verified in codebase)
from app.profile.grid import grid_to_latlon

lat, lon = grid_to_latlon("FN31")    # returns (41.5, -73.0) approx center
lat, lon = grid_to_latlon("FN31pr")  # 6-char for higher precision
# Raises ValueError for invalid grids (e.g., "99AA", "FN3", "")
```

### MY_GRIDSQUARE regex (per prior decisions)
```python
# Source: Prior decisions — "pre-validates character classes (pos 0-1 letters, 2-3 digits, 4-5 letters)"
# Supports 4-char and 6-char only (2-char is valid per grid.py but spec says MY_GRIDSQUARE accepts 1-4 pairs)
import re
MY_GRIDSQUARE_RE = re.compile(
    r"^[A-Ra-r]{2}[0-9]{2}([A-Xa-x]{2})?$"
)
# Matches: FN31, FN31pr, fn31, FN31PR
# Rejects: 99AA, FN3, FN31pr55, empty
```

### Full test pattern for profile API integration test
```python
# Source: mirrors tests/test_qso_api.py pattern (verified in codebase)
@mongo_required
@pytest.mark.asyncio
async def test_get_profile_returns_empty_fields_for_new_operator(profile_db):
    await _create_user("op1", "pass1", "W1OP1")
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        token = await _get_token(ac, "op1", "pass1")
        resp = await ac.get("/api/profile/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["callsign"] == "W1OP1"
    assert body["my_gridsquare"] is None
    assert body["latitude"] is None
```

---

## Codebase State After Phase 7

The following files exist and are ready to build on:

| File | State | Notes |
|------|-------|-------|
| `app/auth/models.py` | EXISTS | User doc has all profile fields including `my_ant` (needs rename to `my_antenna`) |
| `app/auth/dependencies.py` | EXISTS | `get_current_user` returns full `User` object — use this for profile routes |
| `app/profile/__init__.py` | EXISTS | Empty module init |
| `app/profile/grid.py` | EXISTS | `grid_to_latlon(grid: str) -> tuple[float, float]` — ready to call from service |
| `app/profile/schemas.py` | MISSING | Create in plan 08-01 |
| `app/profile/service.py` | MISSING | Create in plan 08-02 |
| `app/profile/router.py` | MISSING | Create in plan 08-02 |
| `tests/test_profile_api.py` | MISSING | Create in plan 08-02 |

---

## Open Questions

1. **MY_GRIDSQUARE validation: 4-char only or 2/4/6-char?**
   - What we know: `grid_to_latlon()` accepts 2, 4, or 6 chars. ADIF 3.1.6 says MY_GRIDSQUARE supports "1 to 4 pairs" (2/4/6/8 chars). Prior decisions specify regex "pos 0-1 letters, 2-3 digits, 4-5 letters" which allows 2, 4, or 6.
   - What's unclear: Whether to accept 2-char (field-only, very imprecise) and 8-char grids in the API schema.
   - Recommendation: Accept 4 and 6-char in the schema regex (most common user input). Reject 2-char and 8-char in ProfileUpdateRequest validation since they're rare and the prior decisions regex example supports 4/6. If 2-char is needed, grid_to_latlon already handles it.

2. **station_callsign empty string handling**
   - What we know: Prior decision states "STATION_CALLSIGN omitted entirely (not empty string) when blank".
   - What's unclear: Whether this means: (a) strip empty string to None in the update dict before $set, or (b) validate in ProfileUpdateRequest that station_callsign cannot be empty string.
   - Recommendation: Add field_validator in ProfileUpdateRequest to convert empty string `""` to `None` for station_callsign.

3. **Response model: include callsign field from User.callsign?**
   - What we know: ProfileResponse should include enough to identify the operator.
   - What's unclear: Whether callsign should be in the response body.
   - Recommendation: Include `callsign: str` in ProfileResponse (read-only, from `user.callsign`) — useful for clients to confirm identity. This is not updatable via PATCH.

---

## Sources

### Primary (HIGH confidence)
- `/Users/royco/ollog/app/auth/models.py` — current User model with `my_ant` field (read 2026-04-04)
- `/Users/royco/ollog/app/auth/dependencies.py` — `get_current_user` signature and behavior confirmed
- `/Users/royco/ollog/app/auth/router.py` — router pattern and structure confirmed
- `/Users/royco/ollog/app/qso/router.py` — PATCH pattern with `$set` and re-fetch confirmed; exact lines 197-201
- `/Users/royco/ollog/app/profile/grid.py` — `grid_to_latlon()` function signature and behavior confirmed
- `/Users/royco/ollog/app/main.py` — router registration pattern confirmed
- `/Users/royco/ollog/tests/test_auth.py` — AsyncClient + ASGITransport test pattern confirmed
- `/Users/royco/ollog/tests/test_qso_api.py` — local `qso_db` fixture pattern confirmed
- `/Users/royco/ollog/pyproject.toml` — all required dependencies already installed
- `https://adif.org/317/` (redirects) + `https://adif.org/316/ADIF_316.htm` — MY_ANTENNA confirmed as correct field name; MY_ANT not in spec
- `https://fastapi.tiangolo.com/tutorial/body-updates/` — `model_dump(exclude_unset=True)` PATCH pattern confirmed

### Secondary (MEDIUM confidence)
- `https://beanie-odm.dev/tutorial/updating-&-deleting/` — `save()` replaces document; `$set` preferred for targeted updates; re-fetch required after `update()`
- WebSearch FastAPI PATCH patterns 2025 — multiple sources confirm `exclude_unset=True` as standard

### Tertiary (LOW confidence)
- None — all critical claims verified with primary sources

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in pyproject.toml and existing code
- Architecture patterns: HIGH — direct from existing codebase (QSO router, auth dependencies)
- MY_ANTENNA field name: HIGH — verified directly from adif.org/316 (latest spec, 2025-09-15); MY_ANT does not appear
- PATCH pattern (exclude_unset): HIGH — FastAPI official docs confirmed
- Beanie $set pattern: HIGH — confirmed in existing codebase (qso/router.py)
- Pitfalls: HIGH for re-fetch requirement (code-verified); HIGH for get_current_user selection (code-verified)

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable libraries; ADIF spec is version-locked to 3.1.6)
