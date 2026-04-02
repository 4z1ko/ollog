# Phase 1: Foundation - Research

**Researched:** 2026-04-03
**Domain:** FastAPI + MongoDB (Beanie/PyMongo async) + JWT auth + ADIF parser
**Confidence:** HIGH (core stack), MEDIUM (ecosystem migration warnings)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### ADIF Parser
- **UTF-8 encoding required throughout** — ADIF byte-length fields must use `len(value.encode('utf-8'))`, not `len(value)`. Non-ASCII characters in NAME, QTH, COMMENT fields will silently corrupt data if `len()` is used.
- Build a custom tag-stream state machine parser (not line-splitter) — the ADIF format has enough real-world variants (missing EOH, case-insensitive field names, whitespace around EOR) that a custom ~100-line parser is safer than a small-ecosystem library whose maintenance status is uncertain.
- Field names normalized to uppercase on parse (ADIF spec: field names are case-insensitive).
- APP_ and USERDEF fields must round-trip losslessly — they are stored verbatim, never dropped.
- Parser errors on a single record should not abort the full file — collect errors per-record, continue parsing.

#### MongoDB Schema & Indexes
- ADIF field names stored verbatim as document keys (uppercase: CALL, BAND, MODE, etc.) — no translation layer, no snake_case mapping.
- Shared `qsos` collection with `_operator` as the leading field in all compound indexes (not per-operator collections).
- Compound unique index: `{_operator, CALL, qso_date_utc, BAND, MODE}` — must exist before first write.
- All datetimes stored as UTC-aware. After every MongoDB read, UTC tzinfo is re-attached via a `from_mongo_dt()` utility — never trust PyMongo to preserve tzinfo.
- Soft-deleted QSOs get `_deleted: true` flag; default queries exclude them.

#### Auth & JWT
- JWT carries: operator callsign, username, role (operator | admin), expiry.
- Operator callsign is injected from the validated JWT into all QSO queries — never from request body or query params.
- Initial admin account bootstrapped via environment variable or first-run seed script (no web endpoint for admin self-registration).

### Claude's Discretion
- JWT expiry duration
- Exact bcrypt work factor (or: algorithm choice — see library notes below)
- Docker Compose service naming conventions
- Health endpoint path and response format
- Python project structure (src layout vs flat)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

The locked stack (FastAPI + Beanie/PyMongo async + MongoDB 7.x) is sound for 2026, but two libraries listed in the original stack description are now unmaintained: **python-jose** (last release 2021, incompatible with Python 3.10+) and **passlib** (last release 2020, broken on Python 3.13). The official FastAPI documentation now recommends **PyJWT 2.12+** and **pwdlib[argon2]** as their direct replacements. These are not locked decisions in CONTEXT.md, so they are researchable.

**Motor**, the async MongoDB driver that Beanie previously depended on, has been deprecated by MongoDB as of May 2025, with end-of-life May 2026. Beanie 2.x has already migrated to use `AsyncMongoClient` from `pymongo` directly — Motor is no longer needed and should not be installed. PyMongo 4.16+ provides the native async API.

The ADIF format is well-specified at adif.org. The locked decision to build a custom state machine parser is correct: the `<FIELDNAME:LENGTH>DATA` format requires byte-level counting (the L in `<F:L>` is a byte count, not a character count for multi-byte UTF-8 data), and the parser must handle real-world variants like missing `<EOH>` and case-insensitive field names.

**Primary recommendation:** Use FastAPI 0.135+, Beanie 2.1 + PyMongo 4.16 (no Motor), PyJWT 2.12, pwdlib[argon2] (or pwdlib[bcrypt] if bcrypt is preferred per discretion). Python 3.12 with uv + pyproject.toml for dependency management.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi[standard] | 0.135.3 | HTTP framework, OpenAPI, dependency injection | Official recommendation, includes uvicorn |
| beanie | 2.1.0 | Async MongoDB ODM, Pydantic v2 models, index management | Only maintained async MongoDB ODM for Python |
| pymongo | 4.16.0 | Async MongoDB driver (AsyncMongoClient) | Motor deprecated May 2025; PyMongo async is the replacement |
| pyjwt | 2.12.1 | JWT encode/decode, RFC 7519 | FastAPI docs now recommends PyJWT; python-jose abandoned |
| pwdlib[argon2] | 0.3.0 | Password hashing | passlib unmaintained/broken on Python 3.13; FastAPI docs recommends pwdlib+Argon2 |
| pydantic-settings | 2.x | Config from environment variables | Built into fastapi[standard]; type-safe settings |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.x | Test runner | All test suites |
| pytest-asyncio | 0.23+ | Async test support | Async route and service tests |
| mongomock-motor | latest | In-memory MongoDB for tests | Unit tests without a real MongoDB instance |
| httpx | 0.27+ | Async HTTP client | FastAPI TestClient async support |
| python-multipart | latest | Form data parsing | Included with fastapi[standard] for OAuth2 form login |

### Alternatives Considered (and rejected)
| Instead of | Rejected | Reason Rejected |
|------------|----------|-----------------|
| PyJWT | python-jose | python-jose last release 2021, incompatible with Python >=3.10 |
| pwdlib[argon2] | passlib[bcrypt] | passlib last release 2020, broken on Python 3.13; crypt module removed |
| pymongo (async) | motor | Motor deprecated May 2025, end-of-life May 2026 |
| Beanie 2.x | custom Motor queries | Beanie provides index management, Pydantic integration, query DSL |
| pwdlib[bcrypt] | pwdlib[argon2] | Both are valid per Claude's Discretion; Argon2 is memory-hard and newer recommendation |

**Installation:**
```bash
pip install "fastapi[standard]" "beanie>=2.1.0" "pymongo>=4.16.0" "pyjwt>=2.12.0" "pwdlib[argon2]" pydantic-settings
# Dev/test
pip install pytest pytest-asyncio httpx
```

Or via pyproject.toml with uv:
```toml
[project]
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.135.0",
    "beanie>=2.1.0",
    "pymongo>=4.16.0",
    "pyjwt>=2.12.0",
    "pwdlib[argon2]>=0.3.0",
    "pydantic-settings>=2.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
]
```

---

## Architecture Patterns

### Recommended Project Structure

Flat layout (simpler for a focused service; src layout adds no benefit without packaging):
```
ollog/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app factory, lifespan
│   ├── config.py            # pydantic-settings Settings class
│   ├── database.py          # AsyncMongoClient + init_beanie call
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── models.py        # User Beanie Document
│   │   ├── router.py        # /auth/token, /auth/me endpoints
│   │   ├── service.py       # JWT create/verify, password hash/verify
│   │   └── dependencies.py  # get_current_user, require_admin Depends
│   ├── adif/
│   │   ├── __init__.py
│   │   ├── parser.py        # State machine parser: .adi → list[dict]
│   │   └── serializer.py    # list[dict] → .adi string
│   └── qso/
│       ├── __init__.py
│       └── models.py        # QSO Beanie Document with indexes
├── tests/
│   ├── conftest.py
│   ├── test_adif_parser.py
│   ├── test_adif_serializer.py
│   ├── test_auth.py
│   └── test_qso_schema.py
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

### Pattern 1: FastAPI Lifespan for Database Init

Use `lifespan` (not deprecated `@app.on_event`). Initialize Beanie here — this creates collections and indexes.

```python
# Source: https://fastapi.tiangolo.com/advanced/events/ + beanie-odm.dev/tutorial/initialization/
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pymongo import AsyncMongoClient
from beanie import init_beanie
from app.qso.models import QSO
from app.auth.models import User
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncMongoClient(settings.mongodb_uri)
    await init_beanie(
        database=client[settings.mongodb_db],
        document_models=[QSO, User],
    )
    yield
    client.close()

app = FastAPI(lifespan=lifespan)
```

### Pattern 2: Beanie Document with Compound Unique Index

The `Settings` inner class (Beanie 2.x) uses `IndexModel` from pymongo for full control.

```python
# Source: https://beanie-odm.dev/tutorial/indexes/
import pymongo
from pymongo import IndexModel
from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime

class QSO(Document):
    _operator: str           # injected from JWT, leading index field
    CALL: str
    BAND: Optional[str] = None
    MODE: Optional[str] = None
    qso_date_utc: Optional[datetime] = None
    _deleted: bool = False
    # All other ADIF fields stored as extras via model_config extra="allow"

    class Settings:
        name = "qsos"
        indexes = [
            IndexModel(
                [
                    ("_operator", pymongo.ASCENDING),
                    ("CALL", pymongo.ASCENDING),
                    ("qso_date_utc", pymongo.ASCENDING),
                    ("BAND", pymongo.ASCENDING),
                    ("MODE", pymongo.ASCENDING),
                ],
                unique=True,
                name="operator_qso_unique",
            ),
            IndexModel(
                [("_operator", pymongo.ASCENDING)],
                name="operator_idx",
            ),
        ]
```

**Note on dynamic ADIF fields:** Since ADIF has 100+ optional fields, use `model_config = ConfigDict(extra="allow")` to store arbitrary ADIF fields verbatim without pre-declaring all of them. The mandatory fields (CALL, BAND, MODE, dates) are declared explicitly for indexing; all others pass through.

### Pattern 3: JWT Auth with Dependency Injection

```python
# Source: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
import jwt
from jwt.exceptions import InvalidTokenError
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")

async def get_current_operator(token: str = Depends(oauth2_scheme)) -> str:
    """Returns operator callsign from JWT. Inject into all QSO operations."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        callsign: str = payload.get("callsign")
        if callsign is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    return callsign
```

### Pattern 4: UTC Datetime Re-attachment After MongoDB Read

PyMongo does not guarantee tzinfo is preserved on datetime objects read back from MongoDB. The CONTEXT.md decision requires re-attaching UTC tzinfo explicitly.

```python
# Pattern for from_mongo_dt() utility
from datetime import datetime, timezone

def from_mongo_dt(dt: datetime | None) -> datetime | None:
    """Re-attach UTC tzinfo to a datetime read from MongoDB."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
```

Apply this after every `QSO.find()` result, or override Beanie's `model_post_init` hook to run it automatically on all datetime fields.

### Pattern 5: ADIF State Machine Parser Structure

```python
# State machine parser — handles missing EOH, case-insensitive names
# Source: ADIF spec interpretation + locked decision in CONTEXT.md

def parse_adi(text: str) -> tuple[list[dict], list[dict]]:
    """
    Returns (records, errors) where each record is a dict of UPPERCASE_FIELD: value.
    Errors are per-record dicts with 'record_index' and 'error'.
    Does not abort on single-record errors.
    """
    records = []
    errors = []
    i = 0
    in_header = True
    current_record: dict = {}
    record_index = 0

    while i < len(text):
        if text[i] != '<':
            i += 1
            continue
        end = text.find('>', i)
        if end == -1:
            break
        tag_content = text[i+1:end]
        i = end + 1

        tag_upper = tag_content.upper()

        if tag_upper == 'EOH':
            in_header = False
            continue
        if tag_upper == 'EOR':
            if current_record:
                records.append(current_record)
                current_record = {}
            record_index += 1
            continue

        # Parse <FIELDNAME:LENGTH> or <FIELDNAME:LENGTH:TYPE>
        parts = tag_content.split(':')
        field_name = parts[0].upper()
        if len(parts) < 2:
            continue
        try:
            byte_len = int(parts[1])
        except ValueError:
            errors.append({'record_index': record_index, 'error': f'Bad length in tag: {tag_content}'})
            continue

        # Read exactly byte_len bytes, decode as UTF-8
        raw_bytes = text[i:i + byte_len].encode('latin-1')[:byte_len]
        value = text[i:i + byte_len]
        i += byte_len

        if not in_header:
            current_record[field_name] = value

    return records, errors
```

**Critical note:** The length L in `<FIELDNAME:L>` is a **byte count**. When the text has been read as a Python str, indexing by character position is correct for pure ASCII files; however, when writing (serializing), compute `len(value.encode('utf-8'))` — not `len(value)` — to correctly handle multi-byte characters. Locked decision confirmed by ADIF spec.

### Anti-Patterns to Avoid

- **Using `@app.on_event("startup")`:** Deprecated in FastAPI; use `lifespan` context manager.
- **Installing Motor alongside Beanie 2.x:** Beanie 2.x already uses PyMongo async directly; Motor is not needed and will conflict in 2026+.
- **Importing from `python_jose`:** Library is abandoned and incompatible with Python 3.10+. Use `import jwt` from PyJWT.
- **Using `passlib.context.CryptContext`:** passlib is unmaintained; its crypt backend is removed in Python 3.13. Use `pwdlib.PasswordHash`.
- **Trusting PyMongo datetime tzinfo:** Always call `from_mongo_dt()` after every read. PyMongo may return naive datetimes.
- **Using `len(value)` for ADIF field length:** Multi-byte UTF-8 chars (accented names, etc.) require `len(value.encode('utf-8'))`.
- **Blocking admin self-registration via API:** CONTEXT.md locks this: admin is seeded by env var or seed script only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT encode/decode | Custom HMAC signing | `jwt.encode/decode` (PyJWT) | Algorithm agility, expiry handling, InvalidTokenError hierarchy |
| Password hashing | Custom bcrypt loop | `pwdlib.PasswordHash.recommended()` | Timing-safe verification, algorithm upgrades, proper salt handling |
| MongoDB index management | Manual `create_index` calls in routes | `Beanie Settings.indexes` + `init_beanie` | Idempotent on startup, handles index creation once |
| Config from env | Manual `os.environ.get()` | `pydantic-settings BaseSettings` | Type coercion, .env file support, validation |
| Async test client | Raw httpx calls | `httpx.AsyncClient(app=app)` | Full ASGI test support without running server |
| MongoDB connection lifecycle | Module-level client | `lifespan` context manager | Proper open/close on startup/shutdown |

**Key insight:** Python's async ecosystem for MongoDB has undergone a significant transition (Motor → PyMongo async). Using Beanie 2.x handles this transparently — don't bypass it with direct Motor imports.

---

## Common Pitfalls

### Pitfall 1: Installing Motor (deprecated)
**What goes wrong:** Motor 3.x still installs and imports without error, but is deprecated as of May 2025 and will reach end-of-life May 2026. Any Beanie 2.x init that receives a Motor `AsyncIOMotorDatabase` instead of a PyMongo `AsyncMongoClient` database may produce type warnings or fail silently.
**Why it happens:** Many tutorials and blog posts from 2023-2024 use Motor; those results still appear in searches.
**How to avoid:** Use `from pymongo import AsyncMongoClient`, not `from motor.motor_asyncio import AsyncIOMotorClient`.
**Warning signs:** `motor` appears in `pip freeze`; imports reference `motor.motor_asyncio`.

### Pitfall 2: python-jose Import Failures on Python 3.10+
**What goes wrong:** `from jose import jwt` raises `ImportError` or produces cryptography backend errors on Python 3.10+ due to an incompatible `ecdsa` dependency.
**Why it happens:** python-jose was last released in 2021 and never updated for Python 3.10+ ecosystem changes.
**How to avoid:** Use `import jwt` from PyJWT (package name: `pyjwt`). The FastAPI official docs now show PyJWT.
**Warning signs:** Any import from `jose` module.

### Pitfall 3: passlib Failure on Python 3.13
**What goes wrong:** `from passlib.context import CryptContext` raises `ModuleNotFoundError` for `crypt` on Python 3.13+, because the stdlib `crypt` module was removed.
**Why it happens:** passlib depends on `crypt` which was deprecated in 3.11 and removed in 3.13.
**How to avoid:** Use `pwdlib[argon2]` or `pwdlib[bcrypt]` as the password hashing library.
**Warning signs:** Any `passlib` in requirements; Python version is 3.13+.

### Pitfall 4: ADIF Byte Length vs Character Length
**What goes wrong:** `<NAME:4>Müller` — "Müller" is 6 characters but `len("Müller")` = 6. However `len("Müller".encode('utf-8'))` = 7 because ü is 2 bytes. Writing length 6 when the byte length is 7 means the parser at the other end reads 6 bytes and gets a truncated/corrupt value.
**Why it happens:** Python 3 strings are Unicode; `len()` counts codepoints not bytes.
**How to avoid:** Always compute `len(value.encode('utf-8'))` when serializing ADIF tags. Locked in CONTEXT.md.
**Warning signs:** Test with non-ASCII name like "André" — the round-trip test must produce identical output.

### Pitfall 5: Naive Datetimes from PyMongo
**What goes wrong:** MongoDB stores BSON Date objects. PyMongo reads them back as Python `datetime` objects, but the tzinfo attribute may be `None` (naive). Comparing a naive datetime to an aware datetime raises `TypeError`. Timezone-aware calculations on a naive datetime silently give wrong results.
**Why it happens:** PyMongo's behavior on tzinfo preservation is not guaranteed across driver versions.
**How to avoid:** Call `from_mongo_dt()` on every datetime field after any MongoDB read. Locked in CONTEXT.md. Consider Beanie's `model_post_init` to apply it automatically.
**Warning signs:** `dt.tzinfo is None` evaluates True after a round-trip through MongoDB.

### Pitfall 6: Missing Compound Index on First Write
**What goes wrong:** If the first QSO insert runs before `init_beanie` creates the compound unique index, duplicate QSOs can be silently inserted with no uniqueness constraint. The index only prevents duplicates going forward.
**Why it happens:** Race condition between app startup and first write, or tests that bypass `init_beanie`.
**How to avoid:** `init_beanie` is called in the `lifespan` startup before `yield`. Tests must call `init_beanie` in their fixture before any write. Locked in CONTEXT.md: "must exist before first write."
**Warning signs:** Tests that use direct `QSO.insert()` without calling `init_beanie` first.

### Pitfall 7: APP_ Fields Dropped During Parse
**What goes wrong:** A custom ADIF parser that only recognizes standard ADIF field names silently drops `APP_LOGGER_SCORE` and similar application-defined fields. Re-exporting the file loses the data.
**Why it happens:** Parsers built from a field whitelist.
**How to avoid:** Parse ALL `<FIELDNAME:L>` tags regardless of name, storing them in the record dict. Only skip `EOH` and `EOR` control tags. Locked in CONTEXT.md.
**Warning signs:** Round-trip test on a file with APP_ fields shows data loss.

### Pitfall 8: Docker Compose Startup Race
**What goes wrong:** FastAPI app starts, calls `init_beanie`, but MongoDB is still initializing. Connection refused → app crashes → Docker restarts loop.
**Why it happens:** `depends_on: mongodb` without `condition: service_healthy` only waits for container start, not MongoDB readiness.
**How to avoid:** Add a `healthcheck` to the MongoDB service using `mongosh --eval "db.adminCommand('ping')"`, then use `depends_on: condition: service_healthy` on the app service.

---

## Code Examples

Verified patterns from official sources:

### PyJWT Token Creation and Verification
```python
# Source: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
import jwt
from jwt.exceptions import InvalidTokenError
from datetime import datetime, timedelta, timezone

SECRET_KEY = "..."  # openssl rand -hex 32
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### pwdlib Password Hashing
```python
# Source: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
from pwdlib import PasswordHash

# Argon2 recommended; use PasswordHash.recommended() for new projects
# For bcrypt (per discretion): PasswordHash(("bcrypt",))
password_hash = PasswordHash.recommended()

def hash_password(plain: str) -> str:
    return password_hash.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return password_hash.verify(plain, hashed)
```

### Beanie Compound Unique Index
```python
# Source: https://beanie-odm.dev/tutorial/indexes/
import pymongo
from pymongo import IndexModel
from beanie import Document
from pydantic import ConfigDict

class QSO(Document):
    model_config = ConfigDict(extra="allow")  # store arbitrary ADIF fields
    _operator: str
    CALL: str
    # ... other declared fields

    class Settings:
        name = "qsos"
        indexes = [
            IndexModel(
                [
                    ("_operator", pymongo.ASCENDING),
                    ("CALL", pymongo.ASCENDING),
                    ("qso_date_utc", pymongo.ASCENDING),
                    ("BAND", pymongo.ASCENDING),
                    ("MODE", pymongo.ASCENDING),
                ],
                unique=True,
                name="operator_qso_unique",
            ),
        ]
```

### init_beanie with PyMongo AsyncMongoClient
```python
# Source: https://beanie-odm.dev/tutorial/initialization/
from pymongo import AsyncMongoClient  # NOT motor.motor_asyncio
from beanie import init_beanie

client = AsyncMongoClient("mongodb://localhost:27017")
await init_beanie(
    database=client["ollog"],
    document_models=[QSO, User],
)
```

### Docker Compose Health Check for MongoDB
```yaml
# Source: Docker Compose docs + MongoDB community
services:
  mongodb:
    image: mongo:7
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  api:
    build: .
    depends_on:
      mongodb:
        condition: service_healthy
```

### FastAPI Lifespan (not deprecated on_event)
```python
# Source: https://fastapi.tiangolo.com/advanced/events/
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: runs before first request
    await startup_db()
    yield
    # Shutdown: runs after last request
    await shutdown_db()

app = FastAPI(lifespan=lifespan)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `from motor.motor_asyncio import AsyncIOMotorClient` | `from pymongo import AsyncMongoClient` | May 2025 (Motor deprecated) | Motor still works until May 2026 but should not be used in new projects |
| `from jose import jwt` (python-jose) | `import jwt` (PyJWT) | ~2023 (python-jose abandoned) | python-jose incompatible with Python 3.10+; PyJWT is now the FastAPI official example |
| `passlib.context.CryptContext` | `pwdlib.PasswordHash` | 2024 (passlib unmaintained) | passlib broken on Python 3.13+; pwdlib[argon2] is the FastAPI official example |
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.93+ | on_event still works but is deprecated; lifespan is the current pattern |
| Beanie depends on Motor | Beanie 2.x uses pymongo async directly | Beanie 2.0 (2025) | Installing Motor separately is no longer needed |

**Deprecated/outdated (do not use):**
- `motor` package: deprecated May 2025, EOL May 2026
- `python-jose`: abandoned 2021, incompatible with Python 3.10+
- `passlib`: last release 2020, broken on Python 3.13; `crypt` stdlib module removed
- `@app.on_event("startup/shutdown")`: deprecated; use `lifespan`

---

## Open Questions

1. **bcrypt vs Argon2 for password hashing**
   - What we know: CONTEXT.md gives Claude discretion on "exact bcrypt work factor" — implying bcrypt preference. But the official FastAPI docs now recommend Argon2 via pwdlib.
   - What's unclear: Whether the project prefers bcrypt for any specific reason (portability, ops familiarity, existing tooling).
   - Recommendation: Use `pwdlib[argon2]` with `PasswordHash.recommended()` for new projects. If bcrypt is explicitly required, use `pwdlib[bcrypt]` — both are available in pwdlib. Do NOT use passlib.

2. **Beanie extra="allow" for dynamic ADIF fields**
   - What we know: ADIF has 100+ fields; only a handful need to be indexed. Declaring all fields is impractical.
   - What's unclear: Whether Beanie 2.x + Pydantic v2 `model_config = ConfigDict(extra="allow")` performs well with 50-100 extra fields per document.
   - Recommendation: Use `extra="allow"`. This is the standard Pydantic v2 pattern for passthrough of unknown fields. No evidence of performance issues at this scale.

3. **Test MongoDB approach: mongomock vs real MongoDB in Docker**
   - What we know: `mongomock-motor` mocks Motor; Beanie 2.x uses pymongo async, so compatibility needs verification.
   - What's unclear: Whether mongomock supports pymongo async client in 2026.
   - Recommendation: Use a real MongoDB 7.x container in Docker Compose for tests (`docker compose up -d mongodb` + pytest). Avoids mock compatibility issues entirely. For CI, use a service container.

---

## Sources

### Primary (HIGH confidence)
- https://beanie-odm.dev/tutorial/indexes/ — compound unique index syntax with IndexModel
- https://beanie-odm.dev/tutorial/initialization/ — init_beanie with AsyncMongoClient
- https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ — PyJWT + pwdlib pattern (current as of 2026-04-03)
- https://fastapi.tiangolo.com/advanced/events/ — lifespan context manager pattern
- https://pypi.org/project/fastapi/ — confirmed version 0.135.3 released 2026-04-01
- https://pypi.org/project/beanie/ — confirmed version 2.1.0 released 2026-03-26
- https://pypi.org/project/PyJWT/ — confirmed version 2.12.1 released 2026-03-13
- https://pypi.org/project/pwdlib/ — confirmed version 0.3.0 released 2025-10-25
- https://pypi.org/project/pymongo/ — confirmed version 4.16.0 released 2026-01-07
- https://motor.readthedocs.io/ — confirmed Motor 3.7.1 deprecated May 2025, EOL May 2026
- https://github.com/BeanieODM/beanie/blob/main/pyproject.toml — confirmed Beanie depends on pymongo >=4.11, NOT motor
- ADIF 3.1.4 spec (https://www.adif.org/314/ADIF_314_annotated.htm) — data specifier format, field case-insensitivity

### Secondary (MEDIUM confidence)
- https://github.com/fastapi/fastapi/discussions/11345 — community discussion on abandoning python-jose
- https://github.com/fastapi/fastapi/discussions/11773 — community discussion on abandoning passlib
- https://github.com/fastapi/fastapi/pull/13917 — PR updating FastAPI docs from passlib to pwdlib
- https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/ — Motor → PyMongo async migration guide

### Tertiary (LOW confidence)
- Various blog posts on Docker Compose health check patterns — confirmed by Docker official docs pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions confirmed via PyPI as of 2026-04-03
- Architecture patterns: HIGH — confirmed via official FastAPI and Beanie docs
- ADIF parser approach: HIGH — locked decision in CONTEXT.md, confirmed correct by spec
- Library migration warnings (Motor, python-jose, passlib): HIGH — confirmed via official deprecation announcements and PyPI
- Pitfalls: HIGH — all pitfalls derived from official docs or confirmed deprecation notices

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (stable ecosystem, but Motor EOL is May 2026 — recheck if timeline slips)
