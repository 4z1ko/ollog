# Phase 25: Token Model and Service Layer - Research

**Researched:** 2026-04-09
**Domain:** Beanie ODM, Python stdlib HMAC, Pydantic SecretStr, FastAPI/Pydantic validation
**Confidence:** HIGH

---

## Summary

Phase 25 creates the `ApiToken` Beanie document and the pure service helpers that all
subsequent token phases (26-28) depend on.  All design decisions are locked; this
research focuses on verifying the correct implementation approach against the project's
existing codebase and confirming the standard-library primitives behave as expected.

The project already uses Beanie 2.1.0 + PyMongo 4.16.0 + Pydantic v2 + pydantic-settings.
The `User` and `QSO` documents provide clear, verified patterns that `ApiToken` must follow
exactly: `IndexModel` from PyMongo for index declaration, `class Settings` with `name =
"api_tokens"`, and registration in `database.py`'s `init_beanie` call.

Token cryptography relies entirely on Python's standard library (`secrets`, `hmac`,
`hashlib`) — no new dependencies are required.  HMAC-SHA256 with `hmac.compare_digest`
is the correct constant-time comparison function; it is already present in Python 3.14
(the runtime in use).  Pydantic `SecretStr` works as expected for `api_token_secret` in
`Settings`.

**Primary recommendation:** Follow the `User` document exactly as a template — `IndexModel`
compound index, `class Settings`, `ConfigDict(populate_by_name=True)`, and register
`ApiToken` in `database.py`.  All crypto helpers live in `app/tokens/service.py` using
only stdlib.

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `beanie` | 2.1.0 | ODM for MongoDB document, indexes | Already in use; provides `Document`, `IndexModel` integration |
| `pymongo` | 4.16.0 | `IndexModel`, `ASCENDING` constants | Already in use |
| `pydantic` | v2 (transitive) | `SecretStr`, `ConfigDict`, `field_validator`, `StringConstraints` | Already in use throughout project |
| `pydantic-settings` | 2.x | `BaseSettings` with `SecretStr` field | Already in use for `Settings` |
| `hmac` | stdlib | HMAC-SHA256 hashing and `compare_digest` | Standard library — no install |
| `hashlib` | stdlib | `sha256` algorithm | Standard library — no install |
| `secrets` | stdlib | `token_urlsafe(32)` — cryptographic entropy | Standard library — no install |

### No New Dependencies Required

All primitives needed for this phase are already present.  The only code artifacts to
create are:

1. `app/tokens/__init__.py`
2. `app/tokens/models.py` — `ApiToken` Beanie document
3. `app/tokens/service.py` — `generate_api_token`, `hash_api_token`, `verify_api_token`
4. Additions to `app/config.py` — `api_token_secret: SecretStr`
5. Registration of `ApiToken` in `app/database.py`

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── tokens/
│   ├── __init__.py        # empty
│   ├── models.py          # ApiToken Beanie document + indexes
│   └── service.py         # generate_api_token, hash_api_token, verify_api_token
├── config.py              # add api_token_secret: SecretStr
└── database.py            # add ApiToken to init_beanie document_models list
```

This mirrors the existing module layout: `app/auth/models.py` + `app/auth/service.py`.
Each domain gets its own package directory.

### Pattern 1: Beanie Document with Compound Index

Follow the `User` document exactly.  Key points verified against the actual source:

```python
# Source: app/auth/models.py (verified)
import pymongo
from pymongo import IndexModel
from beanie import Document
from pydantic import ConfigDict

class User(Document):
    model_config = ConfigDict(populate_by_name=True)
    # ... fields ...
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

For `ApiToken`, the compound index on `(token_prefix, user_id)` follows the same
pattern:

```python
# app/tokens/models.py — recommended implementation
import pymongo
from pymongo import IndexModel
from beanie import Document, PydanticObjectId
from pydantic import ConfigDict, Field
from typing import Optional
from datetime import datetime, timezone

class ApiToken(Document):
    model_config = ConfigDict(populate_by_name=True)

    user_id: PydanticObjectId          # FK to User._id — plain ObjectId, no Link
    name: str                          # validated at creation time via service
    token_prefix: str                  # first 8 chars after "ollog_" — stored clear
    hashed_token: str                  # HMAC-SHA256 hexdigest of full token
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    last_used_at: Optional[datetime] = None
    enabled: bool = True

    class Settings:
        name = "api_tokens"
        indexes = [
            IndexModel(
                [
                    ("token_prefix", pymongo.ASCENDING),
                    ("user_id", pymongo.ASCENDING),
                ],
                name="prefix_user_idx",
            ),
        ]
```

**Why `PydanticObjectId` not `Link`:** The existing project uses string callsigns as
cross-collection references (e.g., `_operator` in `QSO`).  Using `PydanticObjectId` as a
plain foreign-key reference (no `Link`) is consistent with the project's pattern and
avoids automatic fetch overhead.  Verified: `PydanticObjectId` accepts `ObjectId` values
and is importable from `beanie`.

### Pattern 2: Registration in `database.py`

```python
# app/database.py — add ApiToken alongside QSO and User
from app.tokens.models import ApiToken

await init_beanie(
    database=_client[settings.mongodb_db],
    document_models=[
        QSO,
        User,
        ApiToken,   # <-- add here
    ],
)
```

Verified: `init_beanie` accepts any number of `Document` subclasses and creates their
declared indexes on startup.

### Pattern 3: `SecretStr` in Settings

```python
# app/config.py — add to Settings class
from pydantic import SecretStr

class Settings(BaseSettings):
    # ... existing fields ...
    api_token_secret: SecretStr   # loaded from API_TOKEN_SECRET env var
```

Verified with project venv: `SecretStr` hides the value in `repr()` and logs.  Access
the raw value only inside service functions with `.get_secret_value()`.  No default
value — the field is required; app will fail to start if `API_TOKEN_SECRET` is absent
from the environment.

### Pattern 4: Service Helpers (stdlib only)

```python
# app/tokens/service.py

import hmac
import hashlib
import re
import secrets
from app.config import settings

_TOKEN_NAME_RE = re.compile(r'^[a-zA-Z0-9_-]{1,80}$')
_PREFIX_LEN = 8  # chars after "ollog_" stored as token_prefix


def generate_api_token() -> tuple[str, str]:
    """Return (full_token, token_prefix).

    full_token: "ollog_" + 43-char URL-safe base64 string (256 bits entropy)
    token_prefix: first 8 chars after "ollog_"
    """
    body = secrets.token_urlsafe(32)   # 32 bytes = 256 bits; produces 43 chars
    full_token = f"ollog_{body}"
    token_prefix = body[:_PREFIX_LEN]
    return full_token, token_prefix


def hash_api_token(token: str) -> str:
    """Return HMAC-SHA256 hexdigest of token using api_token_secret."""
    key = settings.api_token_secret.get_secret_value().encode()
    return hmac.new(key, token.encode(), hashlib.sha256).hexdigest()


def verify_api_token(token: str, hashed: str) -> bool:
    """Constant-time comparison of HMAC-SHA256 digest."""
    expected = hash_api_token(token)
    return hmac.compare_digest(expected, hashed)


def validate_token_name(name: str) -> str:
    """Raise ValueError if name is invalid; return name if valid."""
    if not _TOKEN_NAME_RE.match(name):
        raise ValueError(
            "Token name must be 1-80 characters: alphanumeric, hyphens, underscores only"
        )
    return name
```

Verified: `hmac.new()`, `hashlib.sha256`, `hmac.compare_digest` all confirmed working
in Python 3.14 venv.  `secrets.token_urlsafe(32)` produces a 43-char URL-safe string
(256 bits of entropy).  Full token `"ollog_" + 43 chars` = 49 chars total.

### Pattern 5: Token Name Validation Using Pydantic

Two valid approaches; either works:

**Option A — `field_validator` (matches project style in test helpers):**
```python
from pydantic import BaseModel, field_validator
import re

_TOKEN_NAME_RE = re.compile(r'^[a-zA-Z0-9_-]{1,80}$')

class ApiTokenCreate(BaseModel):
    name: str

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not _TOKEN_NAME_RE.match(v):
            raise ValueError('...')
        return v
```

**Option B — `Annotated` type alias (cleaner, reusable):**
```python
from typing import Annotated
from pydantic import StringConstraints

TokenName = Annotated[str, StringConstraints(pattern=r'^[a-zA-Z0-9_-]{1,80}$')]
```

Both verified working.  The service helper `validate_token_name()` is simpler and
doesn't require a Pydantic model — use it in the service layer; use Pydantic validation
in the request schemas of Phase 26 routers.

### Anti-Patterns to Avoid

- **Using `user_id: Link[User]`** — causes automatic DB fetch on document load; use
  `PydanticObjectId` as a plain FK reference instead.
- **Storing full token in DB** — full token is show-once; only `token_prefix` (for
  index narrowing) and `hashed_token` (for verification) are persisted.
- **Using `argon2` / `pwdlib` for token hashing** — Argon2 takes 200-500ms per call,
  unacceptable for per-request API auth.  HMAC-SHA256 is intentionally fast here.
- **`hmac.compare_digest` on mismatched types** — both arguments must be the same type
  (both `str` or both `bytes`).  `hexdigest()` returns `str`; keep consistent.
- **Missing timezone on `created_at`** — use `datetime.now(tz=timezone.utc)`, not
  `datetime.utcnow()` (deprecated in Python 3.12+).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Constant-time comparison | Custom byte loop | `hmac.compare_digest` | Timing-attack resistance built in |
| Cryptographic token entropy | `random.randint` loops | `secrets.token_urlsafe(32)` | Cryptographically secure PRNG |
| Index creation | Manual `pymongo` calls in startup | `IndexModel` in `class Settings` | Beanie calls `create_indexes()` during `init_beanie` automatically |
| Secret masking in logs | Custom `__repr__` | `pydantic.SecretStr` | Already implemented, tested |

---

## Common Pitfalls

### Pitfall 1: Forgetting to Register `ApiToken` in `database.py`

**What goes wrong:** Collection is never created; no indexes are built; `ApiToken.insert()`
raises `ServerSelectionTimeoutError` or silent failures in tests.

**Why it happens:** `init_beanie` requires explicit registration of every document model.
The existing `database.py` only lists `[QSO, User]`.

**How to avoid:** Add `ApiToken` to the `document_models` list in `database.py` AND add
it to test fixtures (`conftest.py` `test_db` fixture currently only registers `QSO`).

**Warning signs:** `ApiToken.Settings.name` is `"api_tokens"` but the collection is
absent from MongoDB after startup.

### Pitfall 2: Test Fixtures That Don't Include `ApiToken`

**What goes wrong:** Tests that call `ApiToken.insert()` or `ApiToken.find()` fail with
`CollectionWasNotInitialized` because `init_beanie` in the test fixture didn't include
`ApiToken`.

**Why it happens:** `conftest.py`'s `test_db` fixture only registers `[QSO]`.
`test_auth.py`'s `auth_db` registers `[QSO, User]`.  A new `tokens_db` fixture (or
extension of `auth_db`) must include `[QSO, User, ApiToken]`.

**How to avoid:** Create a dedicated fixture that includes all three models.  Do NOT
modify the existing `conftest.py` fixtures (they are owned by earlier phases).

**Warning signs:** `CollectionWasNotInitialized` exception at test time.

### Pitfall 3: HMAC Key Encoding

**What goes wrong:** `TypeError: key: expected bytes or bytearray, but got str` when
calling `hmac.new()`.

**Why it happens:** `SecretStr.get_secret_value()` returns a `str`.  `hmac.new()`
requires `bytes` for the key.

**How to avoid:** Always call `.encode()` on the secret value:
`settings.api_token_secret.get_secret_value().encode()`.

### Pitfall 4: `api_token_secret` Has No Default — App Won't Start Without It

**What goes wrong:** `ValidationError` during `Settings()` instantiation when
`API_TOKEN_SECRET` env var is absent.

**Why it happens:** Unlike `SECRET_KEY` which is also required, a missing env var with no
default causes pydantic-settings to raise during import of `app.config`.

**How to avoid:** Document `API_TOKEN_SECRET` as a required env var alongside
`SECRET_KEY` in deployment docs.  Tests that import `app.config` must set this env var
(or use a test `.env` file / `monkeypatch`).

**Warning signs:** Import errors in tests that import any module that imports `app.config`.

### Pitfall 5: Token Prefix Length — Off-by-one on Slice

**What goes wrong:** `token_prefix` stores wrong number of characters.

**Why it happens:** The spec says "first 8 chars after `ollog_`".  If the slice is taken
from the full token (`full_token[6:14]`) vs from `body` (`body[:8]`), the result is
identical but one approach is clearer.

**How to avoid:** Extract prefix from `body` (the part after `"ollog_"`) — `body[:8]`.
Verified: `secrets.token_urlsafe(32)` always produces >=8 chars (it produces exactly 43).

---

## Code Examples

### Full Token Generation

```python
# Source: verified against Python 3.14 stdlib in project venv
import secrets

body = secrets.token_urlsafe(32)   # 43-char URL-safe base64 string
full_token = f"ollog_{body}"       # "ollog_" + 43 chars = 49 chars total
token_prefix = body[:8]            # first 8 chars after prefix
```

### HMAC-SHA256 Hash and Verify

```python
# Source: verified in project venv (.venv/bin/python)
import hmac
import hashlib

key = b"my-api-token-secret"
token = "ollog_ABCD1234testtoken"

hashed = hmac.new(key, token.encode(), hashlib.sha256).hexdigest()
# -> "d0ecef9a9390d597c483244d072f7edbc14f1dfe4ed5d0c539103a957eff5202"

# Constant-time comparison
is_valid = hmac.compare_digest(
    hmac.new(key, token.encode(), hashlib.sha256).hexdigest(),
    hashed
)
# -> True
```

### ApiToken Beanie Document

```python
# Source: modeled after app/auth/models.py (verified) and app/qso/models.py (verified)
import pymongo
from pymongo import IndexModel
from beanie import Document, PydanticObjectId
from pydantic import ConfigDict, Field
from typing import Optional
from datetime import datetime, timezone

class ApiToken(Document):
    model_config = ConfigDict(populate_by_name=True)

    user_id: PydanticObjectId
    name: str
    token_prefix: str
    hashed_token: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    last_used_at: Optional[datetime] = None
    enabled: bool = True

    class Settings:
        name = "api_tokens"
        indexes = [
            IndexModel(
                [
                    ("token_prefix", pymongo.ASCENDING),
                    ("user_id", pymongo.ASCENDING),
                ],
                name="prefix_user_idx",
            ),
        ]
```

### Settings with SecretStr

```python
# Source: verified in project venv
from pydantic import SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... existing fields ...
    api_token_secret: SecretStr    # required; loaded from API_TOKEN_SECRET env var

# Usage in service:
key = settings.api_token_secret.get_secret_value().encode()
```

### Token Name Validation (service-layer function)

```python
import re

_TOKEN_NAME_RE = re.compile(r'^[a-zA-Z0-9_-]{1,80}$')

def validate_token_name(name: str) -> str:
    if not _TOKEN_NAME_RE.match(name):
        raise ValueError(
            "Token name must be 1-80 characters, alphanumeric/hyphen/underscore only"
        )
    return name
```

Verified: regex correctly accepts `my-token`, `my_token`, `token123`, 80-char names;
rejects empty string, 81-char names, names with spaces or `!`.

---

## State of the Art

| Old Approach | Current Approach | Reason |
|--------------|-----------------|--------|
| `datetime.utcnow()` | `datetime.now(tz=timezone.utc)` | `utcnow()` deprecated in Python 3.12+ |
| `passlib` for hashing | `pwdlib[argon2]` for passwords; stdlib `hmac` for tokens | `passlib` unmaintained |
| `Link[User]` for FK reference | `PydanticObjectId` plain FK | Avoids automatic fetch overhead |

---

## Open Questions

1. **Should `validate_token_name` be a standalone function or embedded in a Pydantic schema?**
   - What we know: Service layer is pure Python; Pydantic schemas belong in routers (Phase 26).
   - What's unclear: Whether Phase 26 will define a separate `ApiTokenCreate` schema or reuse the service function.
   - Recommendation: Provide `validate_token_name()` in `service.py`; Phase 26 planner decides whether to also add a Pydantic schema.

2. **Test fixture strategy — extend `auth_db` or create a new `tokens_db`?**
   - What we know: `conftest.py` is frozen (owned by Phase 01-02). `test_auth.py` owns `auth_db`.
   - What's unclear: Whether token tests should depend on `auth_db` (from test_auth.py) or define their own fixture.
   - Recommendation: Define a new `tokens_db` fixture in `test_tokens.py` that registers `[QSO, User, ApiToken]`. This avoids cross-file fixture dependencies and follows the precedent set by `test_auth.py`.

3. **`api_token_secret` fallback in test environments?**
   - What we know: No default value means `Settings()` fails if `API_TOKEN_SECRET` is unset.
   - What's unclear: Current test setup (check whether `.env` file or `monkeypatch` is used for `SECRET_KEY`).
   - Recommendation: Investigate how existing tests handle `SECRET_KEY` being required; apply the same pattern to `api_token_secret`.

---

## Sources

### Primary (HIGH confidence)

- `app/auth/models.py` — verified `User` document and `IndexModel` pattern
- `app/auth/service.py` — verified service helper structure
- `app/database.py` — verified `init_beanie` registration pattern
- `app/config.py` — verified `Settings` structure
- `tests/test_auth.py` — verified test fixture pattern (`auth_db`)
- `tests/conftest.py` — verified frozen `test_db` fixture
- Python 3.14 stdlib (project venv) — `hmac`, `hashlib`, `secrets` all verified interactively
- Pydantic v2 (project venv) — `SecretStr`, `field_validator`, `StringConstraints` all verified

### Secondary (MEDIUM confidence)

- `pyproject.toml` — confirmed beanie==2.1.0, pymongo==4.16.0, pydantic-settings in dependencies

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are already installed and used in the project
- Architecture: HIGH — patterns verified directly from existing source files and venv
- Pitfalls: HIGH — pitfalls derived from actual code inspection (frozen fixtures, missing registration, encoding requirements)

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable stack, 30-day validity)
