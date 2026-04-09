# Stack Research: API Token Authentication

**Domain:** Named API token auth — hashed storage, X-API-Key header validation, UDP ADIF datagram extraction
**Researched:** 2026-04-09
**Confidence:** HIGH for all core findings (verified against official FastAPI docs, pwdlib source, Python stdlib docs)

---

## Context: What Already Exists (Do Not Re-Research)

Existing validated stack (in `pyproject.toml`, locked at listed versions):

| Component | Version | Role |
|-----------|---------|------|
| FastAPI | 0.135+ | Web framework, `APIKeyHeader` is in `fastapi.security` |
| Beanie | 2.1+ | ODM — `Document` class hosts the User model |
| pwdlib[argon2] | 0.3.0 | `PasswordHash.recommended()` — Argon2 via `hash()`/`verify()` |
| PyJWT | 2.12+ | JWT session tokens (not involved in API token path) |
| pymongo | 4.16+ | `IndexModel` for MongoDB indexes |
| asyncio.DatagramProtocol | stdlib | UDP listener — `QSODatagramProtocol` in `app/udp/server.py` |
| `app/adif/parser.py` | internal | `parse_adi()` — already preserves `APP_*` fields verbatim |

---

## Answer: No New Libraries Required

All three capabilities (hashed storage, X-API-Key dependency, UDP extraction) are fully satisfied by existing dependencies plus Python stdlib. Zero new `pyproject.toml` additions.

---

## Recommended Stack Additions/Changes

### (1) Named API Tokens Stored Hashed in MongoDB

**Approach:** Add an embedded Pydantic `BaseModel` inside the existing `User` Document. Beanie supports `List[BaseModel]` fields natively — no separate collection needed.

**Token document shape:**

```python
from pydantic import BaseModel
from datetime import datetime

class ApiToken(BaseModel):
    name: str                        # human-readable label, e.g. "n1mm-station1"
    hashed_token: str                # Argon2 hash via pwdlib
    created_at: datetime
    enabled: bool = True
```

**Added to `User` Document:**

```python
api_tokens: list[ApiToken] = []
```

**Hashing:** Use the existing `PasswordHash` instance from `app/auth/service.py`. `password_hash.hash(plain_token)` accepts any `str`. `password_hash.verify(plain_token, stored_hash)` returns `bool`. Argon2 is appropriate here — API tokens are high-entropy secrets that must survive offline attacks if the DB is leaked; the performance cost is acceptable because token validation happens once per request, not in a tight loop. (HIGH confidence — pwdlib 0.3.0 `hash()`/`verify()` are generic string operations with no password-specific restrictions.)

**Token generation:** `secrets.token_urlsafe(32)` — 256 bits of entropy, URL-safe base64, stdlib `secrets` module. No new library. Recommended by Python docs as the canonical way to generate security tokens. (HIGH confidence — official Python docs.)

**Index:** Add a sparse unique index on `api_tokens.name` per user if duplicate-name prevention is enforced at DB level, using `IndexModel` with dot-notation path. This is standard pymongo syntax already used in the project. Whether to enforce at DB or app layer is an architecture decision; app-layer check is simpler and sufficient for this use case.

---

### (2) X-API-Key Header Validation as a FastAPI Dependency

**Approach:** Use `fastapi.security.APIKeyHeader` — built into FastAPI, already in the dependency tree.

**Import (no new install):**

```python
from fastapi.security import APIKeyHeader
```

**Usage:**

```python
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def get_current_user_api_key(
    api_key: str = Depends(api_key_header),
) -> User:
    # Iterate user's api_tokens, verify with pwdlib
    ...
```

**`auto_error=True`** (default): FastAPI returns HTTP 403 automatically when the header is absent. Use this for endpoints that require API key auth.

**`auto_error=False`**: Header missing returns `None` instead of raising. Use this for dual-auth endpoints (accept either JWT Bearer OR X-API-Key — check whichever is present).

**Timing attack protection:** When comparing tokens (before Argon2 verification, e.g. checking if the token format is valid), use `secrets.compare_digest()` from the stdlib `secrets` module. For the Argon2 `verify()` call itself, pwdlib already handles constant-time comparison internally.

**HIGH confidence** — `APIKeyHeader` is documented in FastAPI reference docs at https://fastapi.tiangolo.com/reference/security/. The `name` parameter sets the OpenAPI security scheme header name. The dependency yields a `str` containing the raw header value.

---

### (3) Token Extraction from ADIF APP_ Fields in the UDP Path

**Approach:** Zero new code needed in `app/adif/parser.py`. The existing `parse_adi()` function already preserves `APP_*` fields verbatim (line 98: `current_record[field_name] = value` — `field_name` is uppercased, no filtering). A datagram containing `<APP_OLLOG_TOKEN:43>abc...xyz` will produce `record["APP_OLLOG_TOKEN"] = "abc...xyz"` in the parsed dict.

**ADIF field naming:** `APP_OLLOG_TOKEN` follows the ADIF spec convention `APP_[PROGRAMID]_[FIELDNAME]` (confirmed in ADIF 2.2.6+ spec: applications use their PROGRAMID as the middle component to avoid naming collisions). PROGRAMID `OLLOG` is the natural choice.

**Extraction in `_handle_datagram()`:**

```python
token_value = record.get("APP_OLLOG_TOKEN")
```

No parser changes. The UDP handler already has `record` available before the `build_qso_dict()` call. Token lookup against the DB is the only new code.

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `itsdangerous` or `authlib` | Overkill — full OAuth/signing frameworks for a simple token hash | `secrets.token_urlsafe(32)` + pwdlib `hash()` |
| A separate `api_tokens` MongoDB collection | Adds a join-equivalent lookup on every request; tokens belong to a user and there are few per user | Embed `ApiToken` as a list inside `User` |
| `hmac.compare_digest` directly on the raw token | Bypasses Argon2's purpose — raw comparison is only safe for fixed-length equal-entropy tokens; Argon2 protects stored tokens if DB leaks | pwdlib `verify()` which uses Argon2 internally with constant-time comparison |
| BCRYPT for token hashing | Lower memory-hardness than Argon2id; less resistant to GPU cracking | Argon2 via `pwdlib[argon2]` (already installed) |
| Separate FastAPI security middleware | Middleware runs on every request; dependency injection is the FastAPI-idiomatic pattern and applies only to routes that need it | `Depends(api_key_header)` on specific routers |

---

## Integration Points with Existing Code

| Existing Component | How API Token Auth Connects |
|-------------------|----------------------------|
| `app/auth/models.py` — `User` Document | Add `api_tokens: list[ApiToken] = []` field; `ApiToken` is a `pydantic.BaseModel` (not a `Document`) |
| `app/auth/service.py` — `password_hash` instance | Reuse `password_hash.hash()` and `password_hash.verify()` for token hash/verify; same Argon2 instance |
| `app/auth/dependencies.py` | Add `get_current_user_api_key()` alongside existing `get_current_user()` and `get_current_user_cookie()` |
| `app/udp/server.py` — `_handle_datagram()` | Extract `record.get("APP_OLLOG_TOKEN")` before `build_qso_dict()`; resolve token to User; pass user to `build_qso_dict()` |
| `app/adif/parser.py` — `parse_adi()` | No changes needed — `APP_*` fields already preserved |

---

## Installation

No new dependencies. All capabilities are in the existing stack:

```bash
# Nothing to install — all required libraries already in pyproject.toml:
# fastapi[standard]>=0.135.0  →  APIKeyHeader in fastapi.security
# pwdlib[argon2]>=0.3.0       →  PasswordHash.hash() / verify()
# beanie>=2.1.0               →  List[BaseModel] embedding in Document
# pymongo>=4.16.0             →  IndexModel for any new indexes
# Python stdlib               →  secrets.token_urlsafe(), secrets.compare_digest()
```

---

## Version Compatibility

| Package | Version in Lock | API Token Auth Usage | Notes |
|---------|----------------|---------------------|-------|
| fastapi | 0.135+ | `APIKeyHeader`, `Depends` | `APIKeyHeader` stable since FastAPI 0.63; no breaking changes |
| pwdlib[argon2] | 0.3.0 | `PasswordHash.hash(str)` / `verify(str, str)` | Generic string input; no password-specific restrictions |
| beanie | 2.1+ | `List[BaseModel]` in `Document` | Pydantic v2 model embedding fully supported |
| pymongo | 4.16+ | `IndexModel` with dot-notation path | Standard MongoDB behavior for embedded field indexing |
| Python stdlib | 3.12+ | `secrets.token_urlsafe(32)`, `secrets.compare_digest()` | Available since Python 3.6 |

---

## Sources

- [FastAPI Security Reference — APIKeyHeader](https://fastapi.tiangolo.com/reference/security/) — constructor signature (`name`, `auto_error`), import path, dependency yield type (`str`). HIGH confidence.
- [pwdlib 0.3.0 on PyPI](https://pypi.org/project/pwdlib/) — version confirmed in `uv.lock` (upload-time 2025-10-25). HIGH confidence.
- [pwdlib Guide — frankie567.github.io](https://frankie567.github.io/pwdlib/guide/) — `hash(str)` / `verify(str, str)` signatures confirmed. HIGH confidence.
- [Python docs — secrets module](https://docs.python.org/3/library/secrets.html) — `token_urlsafe(32)` recommendation (32 bytes = 256 bits), `compare_digest()` for constant-time comparison. HIGH confidence.
- [ADIF 2.2.6 Specification — APP_ field format](https://www.adif.org/adif226.htm) — `APP_[PROGRAMID]_[FIELDNAME]` convention confirmed. HIGH confidence.
- [Beanie — Defining a Document](https://beanie-odm.dev/tutorial/defining-a-document/) — `List[BaseModel]` embedding in `Document` confirmed. HIGH confidence.
- Existing codebase (`app/auth/service.py`, `app/auth/models.py`, `app/auth/dependencies.py`, `app/adif/parser.py`, `app/udp/server.py`) — direct inspection confirming reuse points and `APP_*` field handling. HIGH confidence.

---

*Stack research for: API Token Authentication milestone (ollog)*
*Researched: 2026-04-09*
