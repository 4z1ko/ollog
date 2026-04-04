# Phase 7: Profile Data Model and Grid Utility - Research

**Researched:** 2026-04-04
**Domain:** Beanie/Pydantic data modeling, Maidenhead grid conversion, Python unit testing
**Confidence:** HIGH

## Summary

Phase 7 adds operator profile fields to the existing `User` Beanie Document and implements a standalone grid-to-lat/lon conversion utility. Both tasks are well-bounded and low-risk. The existing codebase already uses the exact patterns needed — `Optional[str] = None` fields exist in `QSO`, and unit tests follow a consistent static-tests-first structure. No new patterns are introduced.

The two new dependencies are `maidenhead>=1.8.0` (latest: 1.8.0, released 2025-05-25) and `pydantic[email]>=2.0` (which installs `email-validator>=2.0.0`). Both integrate cleanly into the project's existing pyproject.toml `[project] dependencies` list. The maidenhead library API is verified: `maidenhead.to_location(maiden: str, center: bool = False) -> tuple[float, float]`. The `center=True` argument is required to return the center of the grid square rather than the southwest corner.

The User model uses `extra` not set (implicitly `extra='ignore'`), meaning only declared fields are stored. All new profile fields must be explicitly declared as `Optional[T] = None`. The `keep_nulls` Beanie behavior defaults to True (nulls stored), which is acceptable for profile fields — they are absent by choice, not error.

**Primary recommendation:** Follow the `Optional[str] = None` pattern from QSO for all profile fields; import `EmailStr` from `pydantic`; call `maidenhead.to_location(grid, center=True)` and catch `ValueError` for invalid input.

---

## Prior Decisions (from phase context — no CONTEXT.md exists)

These decisions were provided in the phase brief and are locked:

- Profile fields embedded in existing `User` Beanie document — no separate collection, no migration
- `maidenhead>=1.8.0` + `pydantic[email]>=2.0` are the only new dependencies
- `center=True` required for `maidenhead.to_location()` — SW corner default causes up to 80 km error
- Use `MY_ANT` as the field name in the User model (ADIF alignment deferred to Phase 8)

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| beanie | >=2.1.0 (already in project) | MongoDB ODM — User Document | Already used; no alternatives |
| pydantic | >=2.0 (already pulled by beanie) | Field validation, EmailStr | Already used; v2 required |
| maidenhead | >=1.8.0 | Grid square to lat/lon conversion | Only maintained Python maidenhead library; 1.8.0 is latest (2025-05-25) |
| pydantic[email] | >=2.0 | Installs email-validator>=2.0, enables EmailStr | Official pydantic extra for email validation |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=8.0 (already in dev) | Unit test runner | All tests in this phase are pure unit tests (no MongoDB needed) |
| pytest-asyncio | >=0.23 (already in dev) | Async test support | Not needed for grid.py tests (synchronous), available if needed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| maidenhead 1.8.0 | gridtools, custom math | maidenhead is the standard; custom is error-prone, gridtools is less maintained |
| pydantic[email] | email-validator directly | pydantic[email] is the documented official approach; same result |

**Installation (uv add syntax for this project):**
```bash
uv add maidenhead>=1.8.0 "pydantic[email]>=2.0"
```

**pyproject.toml format (matching existing style):**
```toml
[project]
dependencies = [
    "fastapi[standard]>=0.135.0",
    "beanie>=2.1.0",
    "pymongo>=4.16.0",
    "pyjwt>=2.12.0",
    "pwdlib[argon2]>=0.3.0",
    "pydantic-settings>=2.0",
    "maidenhead>=1.8.0",
    "pydantic[email]>=2.0",
]
```

---

## Architecture Patterns

### Existing Project Structure (relevant parts)
```
app/
├── auth/
│   ├── models.py        # User Beanie Document — ADD profile fields here
│   └── ...
├── qso/
│   └── models.py        # Reference: Optional[str] = None pattern to follow
└── profile/             # NEW: create this module
    ├── __init__.py
    └── grid.py          # NEW: grid_to_latlon() utility

tests/
├── conftest.py          # DO NOT MODIFY — owned by 01-02
├── test_auth.py         # Reference: static test pattern to follow
└── test_profile_grid.py # NEW: unit tests for grid.py
```

### Pattern 1: Adding Optional Fields to Beanie Document

**What:** Extend an existing Beanie Document with Optional fields that default to None. Beanie stores null in MongoDB for unset fields (keep_nulls=True default).

**When to use:** When extending an existing document with non-required fields.

**Example (verified from QSO model in this codebase):**
```python
# Source: /Users/royco/ollog/app/qso/models.py (confirmed pattern)
from typing import Optional
from pydantic import EmailStr

class User(Document):
    # Existing required fields
    username: str
    hashed_password: str
    callsign: str
    role: str = "operator"
    enabled: bool = True

    # New profile fields — all Optional with None default
    station_callsign: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    qth: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    my_gridsquare: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    my_rig: Optional[str] = None
    my_ant: Optional[str] = None
    tx_pwr: Optional[float] = None
```

### Pattern 2: grid_to_latlon() Utility Function

**What:** Wrap `maidenhead.to_location()` with center=True, validate input length (2-6 chars, even count), and raise ValueError for invalid grids.

**When to use:** Whenever a grid square string must be converted to decimal lat/lon.

**Example (verified from maidenhead GitHub source):**
```python
# Source: https://github.com/space-physics/maidenhead (to_location.py)
import maidenhead

def grid_to_latlon(grid: str) -> tuple[float, float]:
    """Convert Maidenhead grid locator to (latitude, longitude).

    Returns center of grid square, not SW corner.
    Supports 4-char (field+square) and 6-char (field+square+subsquare) grids.
    Raises ValueError for invalid grid strings.
    """
    if not grid or len(grid) not in (2, 4, 6) or len(grid) % 2 != 0:
        raise ValueError(f"Grid must be 2, 4, or 6 characters: {grid!r}")
    return maidenhead.to_location(grid, center=True)
```

### Pattern 3: Static Unit Tests (no MongoDB)

**What:** Pure unit tests that test synchronous Python logic without any database. Pattern seen throughout this codebase.

**When to use:** Grid utility has no async/DB dependencies — use plain `def test_...()` functions.

**Example (verified from test_auth.py in this codebase):**
```python
# Source: /Users/royco/ollog/tests/test_auth.py (static test block pattern)
import pytest
from app.profile.grid import grid_to_latlon

def test_4char_grid_returns_center():
    lat, lon = grid_to_latlon("FN31")
    assert isinstance(lat, float)
    assert isinstance(lon, float)
    # FN31 center: approximately lat=41.5, lon=-73.0 (verify exact values)

def test_6char_grid_returns_center():
    lat, lon = grid_to_latlon("FN31pr")
    assert isinstance(lat, float)
    assert isinstance(lon, float)

def test_invalid_grid_raises_value_error():
    with pytest.raises(ValueError):
        grid_to_latlon("INVALID")

def test_odd_length_grid_raises_value_error():
    with pytest.raises(ValueError):
        grid_to_latlon("FN3")
```

### Pattern 4: EmailStr in Pydantic v2

**What:** EmailStr is a Pydantic type that validates email format. Requires `email-validator>=2.0` installed (via `pydantic[email]`).

**Import (verified from Pydantic v2 official docs):**
```python
from pydantic import EmailStr
```

### Anti-Patterns to Avoid

- **Using `Optional[T]` without `= None`:** In Pydantic v2, `Optional[T]` without a default is REQUIRED (allows None but must be provided). Always pair with `= None`.
- **Calling `maidenhead.to_location(grid)` without `center=True`:** Returns SW corner, not center. Error up to ~80 km.
- **Validating grid in the model setter:** Grid-to-latlon conversion should happen in service/API layer, not as a Pydantic validator on the User model. Keep the model as a simple data container.
- **Creating a separate `Profile` collection:** Locked decision — embed in User document only.
- **Modifying `tests/conftest.py`:** The conftest.py is owned by phase 01-02 and must not be modified. Grid tests are pure functions needing no fixtures from conftest.py.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Grid square to lat/lon math | Custom Maidenhead parser | `maidenhead.to_location(grid, center=True)` | Handles all grid sizes (2/4/6/8/10 chars), correct modular math, maintained |
| Email validation | Regex email check | `pydantic.EmailStr` | RFC-correct, handles edge cases, already in ecosystem |

**Key insight:** Maidenhead math is deceptively simple-looking but involves modular arithmetic across multiple character classes. The center offset calculation per grid level is easy to get wrong. Use the library.

---

## Common Pitfalls

### Pitfall 1: SW Corner vs Center
**What goes wrong:** `maidenhead.to_location(grid)` returns the southwest corner of the grid square (default `center=False`). For a 4-char grid (~1° latitude x ~2° longitude), this puts coordinates up to ~80 km from center.
**Why it happens:** Library default preserves historical behavior.
**How to avoid:** Always call with `center=True`: `maidenhead.to_location(grid, center=True)`.
**Warning signs:** Coordinates feel "off" relative to expected location; all points within a grid map to same corner value.

### Pitfall 2: Pydantic v2 Optional Without Default
**What goes wrong:** `field: Optional[str]` raises ValidationError at construction because the field is required (no default set).
**Why it happens:** Pydantic v2 changed semantics — `Optional[T]` means "can be None" not "has default None".
**How to avoid:** Always write `field: Optional[str] = None`.
**Warning signs:** `ValidationError: field required` when constructing User without profile fields.

### Pitfall 3: EmailStr Import Fails Without email-validator
**What goes wrong:** `from pydantic import EmailStr` succeeds at import time but raises `PydanticUserError` or `ImportError` when a model with EmailStr is instantiated, if `email-validator` is not installed.
**Why it happens:** EmailStr is a lazy type in Pydantic v2 — import works but validation fails.
**How to avoid:** Ensure `pydantic[email]>=2.0` is in `[project] dependencies` (not just dev extras).
**Warning signs:** Tests pass locally but fail in CI if email-validator not installed.

### Pitfall 4: Beanie keep_nulls Storing Null Profile Fields
**What goes wrong:** Every User document in MongoDB gains null fields for all profile fields even when not set, bloating documents.
**Why it happens:** Beanie default is `keep_nulls = True`.
**How to avoid:** Either accept null fields (simpler, fine for this scale) or set `keep_nulls = False` in `User.Settings`. The prior decision does not specify, so keep_nulls=True (default) is acceptable.
**Warning signs:** MongoDB documents show many null fields. Not a correctness problem, only a storage concern.

### Pitfall 5: conftest.py Not Including User Model
**What goes wrong:** The existing `conftest.py` `test_db` fixture only initializes Beanie with `[QSO]`. Tests that need the User model with init_beanie will fail with "Document not initialized" error.
**Why it happens:** conftest.py is owned by 01-02, predates User model being needed in test_db.
**How to avoid:** Grid tests do NOT need MongoDB at all (pure unit tests). If auth-layer profile tests are needed later, use the `auth_db` fixture pattern from `test_auth.py` which includes both QSO and User. Do not modify conftest.py.
**Warning signs:** `CollectionWasNotInitialized` or `DocumentWasNotInitialized` Beanie errors in tests.

---

## Code Examples

### maidenhead.to_location verified signature
```python
# Source: https://github.com/space-physics/maidenhead/blob/main/src/maidenhead/to_location.py
# Verified: 2026-04-04, version 1.8.0 (latest as of 2025-05-25)
def to_location(maiden: str, center: bool = False) -> tuple[float, float]:
    ...
```

### EmailStr import (Pydantic v2)
```python
# Source: https://docs.pydantic.dev/latest/api/networks/
from pydantic import EmailStr
# Requires pydantic[email]>=2.0 installed (email-validator>=2.0.0)
```

### Existing User model structure (current state)
```python
# Source: /Users/royco/ollog/app/auth/models.py (read 2026-04-04)
class User(Document):
    model_config = ConfigDict(populate_by_name=True)

    username: str
    hashed_password: str
    callsign: str
    role: str = "operator"
    enabled: bool = True

    class Settings:
        name = "users"
        indexes = [
            IndexModel(
                [("username", pymongo.ASCENDING)],
                unique=True,
                name="username_unique",
            ),
        ]
```

### pyproject.toml current structure (verified)
```toml
# Source: /Users/royco/ollog/pyproject.toml (read 2026-04-04)
[project]
dependencies = [
    "fastapi[standard]>=0.135.0",
    "beanie>=2.1.0",
    ...
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
]
```
Note: Project uses both `[project.optional-dependencies]` and `[dependency-groups]` for dev deps (both present, redundant). New runtime deps go in `[project] dependencies`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Optional[T]` implicitly optional (Pydantic v1) | `Optional[T] = None` required (Pydantic v2) | Pydantic 2.0 release | Must always include `= None` |
| `from pydantic import EmailStr` with `email-validator` v1 | Requires `email-validator>=2.0` | Pydantic 2.0 | `pydantic[email]>=2.0` handles this automatically |

**Deprecated/outdated:**
- Pydantic v1 `Optional` implicit default: replaced by explicit `= None` in Pydantic v2.

---

## Open Questions

1. **keep_nulls behavior for profile fields**
   - What we know: Beanie default is keep_nulls=True; all Optional=None fields are stored as null in MongoDB
   - What's unclear: Whether the project wants null-free documents (only store fields that have values)
   - Recommendation: Accept the default (keep_nulls=True) for Phase 7; document as a future config option if desired

2. **MY_ANT vs MY_ANTENNA ADIF alignment**
   - What we know: ADIF spec alignment deferred to Phase 8 planning per prior decisions
   - What's unclear: Correct ADIF field name for antenna
   - Recommendation: Use `my_ant: Optional[str] = None` in Phase 7 as specified; update in Phase 8 if needed

3. **latitude/longitude field precision**
   - What we know: `maidenhead.to_location()` returns Python floats (64-bit)
   - What's unclear: Whether MongoDB storage precision is a concern
   - Recommendation: Use `Optional[float]` — MongoDB stores floats as IEEE 754 double, sufficient for grid-derived coordinates

---

## Sources

### Primary (HIGH confidence)
- `/Users/royco/ollog/app/auth/models.py` — current User model structure, confirmed fields
- `/Users/royco/ollog/app/qso/models.py` — `Optional[str] = None` pattern confirmed in use
- `/Users/royco/ollog/pyproject.toml` — dependency format, existing deps confirmed
- `/Users/royco/ollog/tests/conftest.py` — fixture pattern, Beanie init pattern
- `/Users/royco/ollog/tests/test_auth.py` — static test pattern, auth_db fixture pattern
- `https://github.com/space-physics/maidenhead` (raw source) — `to_location(maiden: str, center: bool = False) -> tuple[float, float]` confirmed
- `https://pypi.org/pypi/maidenhead/json` — version 1.8.0 confirmed as latest (released 2025-05-25)
- `https://docs.pydantic.dev/latest/api/networks/` — `from pydantic import EmailStr` confirmed, requires email-validator

### Secondary (MEDIUM confidence)
- `https://beanie-odm.dev/tutorial/defining-a-document/` — keep_nulls behavior confirmed, Optional[str] = None pattern confirmed

### Tertiary (LOW confidence)
- WebSearch results for Beanie 2.1 + Pydantic v2 Optional fields — corroborates findings but secondary to official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies verified via PyPI JSON API and GitHub source
- Architecture: HIGH — patterns taken directly from existing codebase files
- maidenhead API: HIGH — verified from raw GitHub source, exact function signature confirmed
- Pitfalls: HIGH for Pydantic v2 semantics (official docs); MEDIUM for keep_nulls behavior (beanie docs)
- EmailStr: HIGH — Pydantic official docs confirm import and email-validator requirement

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable libraries; maidenhead and pydantic are not fast-moving)
