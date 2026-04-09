# Architecture Research

**Domain:** Named API Token Auth — FastAPI/Beanie/MongoDB integration
**Researched:** 2026-04-09
**Confidence:** HIGH (based on direct codebase inspection of all relevant files)

---

## Context: Existing Architecture

Relevant components inspected:

- `app/auth/models.py` — `User` Beanie Document, `users` collection, Argon2 hashed passwords via pwdlib, embedded profile fields (callsign, station_callsign, gridsquare, etc.)
- `app/auth/service.py` — `hash_password()` and `verify_password()` using `pwdlib.PasswordHash.recommended()` (Argon2)
- `app/auth/dependencies.py` — `get_current_user` (JWT Bearer via `OAuth2PasswordBearer`), `get_current_user_cookie` (HttpOnly cookie), `get_current_operator_callsign`, `get_current_operator_callsign_cookie`, `require_admin`, `require_admin_cookie`
- `app/config.py` — `Settings` with `udp_operator: str | None = None`, `udp_enabled: bool`
- `app/main.py` — lifespan resolves `UDP_OPERATOR` to `(udp_op, udp_user)` at startup, passes to `start_udp_listener()`
- `app/udp/server.py` — `_handle_datagram(data, addr, operator, user)` accepts `operator: str | None` and `user: User | None`; `QSODatagramProtocol` caches them at construction
- `app/qso/router.py` — all endpoints use `get_current_user` or `get_current_operator_callsign` via `Depends()`
- `app/database.py` — `init_beanie(document_models=[QSO, User])`

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                           HTTP Clients                               │
│  ┌─────────────────┐  ┌───────────────────────┐  ┌────────────────┐ │
│  │  Browser (UI)   │  │  REST API Client       │  │ UDP Datagram   │ │
│  │  Cookie JWT     │  │  Authorization: Bearer │  │ (ADIF sender)  │ │
│  │                 │  │  — OR —                │  │ (no per-packet │ │
│  │                 │  │  X-API-Key: ollog_...  │  │  auth header)  │ │
│  └────────┬────────┘  └────────────┬───────────┘  └───────┬────────┘ │
└───────────┼────────────────────────┼─────────────────────┼──────────┘
            │                        │                      │
┌───────────▼────────────────────────▼──────────────────────▼──────────┐
│                         Auth Layer (app/auth/)                        │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  Existing                                                        │ │
│  │  get_current_user_cookie        get_current_user (JWT Bearer)   │ │
│  │  get_current_operator_callsign_cookie                           │ │
│  │                   get_current_operator_callsign                 │ │
│  │                                                                  │ │
│  │  New (this milestone)                                            │ │
│  │  get_current_user_api_key  (X-API-Key header)                   │ │
│  │  get_current_operator_callsign_api_key                          │ │
│  └──────────────────────────────┬──────────────────────────────────┘ │
└─────────────────────────────────┼────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────────┐
│                      MongoDB (Beanie Documents)                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │  users           │  │  qsos            │  │  api_tokens (new)│   │
│  │  (User)          │  │  (QSO)           │  │  (ApiToken)      │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Question 1: Separate `ApiToken` Collection vs. Embedded in `User`

**Recommendation: Separate `api_tokens` collection.**

### Why not embedded

An embedded `api_tokens: list[...]` array on `User` means:

- Every `User.find_one()` in the existing auth path loads the full token list into memory, even on JWT-only requests where tokens are irrelevant.
- Token lookup by prefix requires MongoDB `$elemMatch` on an array field — more complex than a top-level `find_one`.
- A unique index on `users.api_tokens.token_prefix` is a compound array path index — valid, but harder to reason about and document.
- Revocation requires `$pull` with a nested filter. A top-level `await token.delete()` is simpler and less error-prone.
- Listing a user's tokens requires loading the full User document and slicing the array rather than a targeted `find({"user_id": user_id})`.

### `ApiToken` Document

```python
import secrets
from datetime import datetime, timezone
from typing import Optional

import pymongo
from pymongo import IndexModel
from beanie import Document
from pydantic import ConfigDict
from bson import ObjectId
from beanie.odm.fields import PydanticObjectId


class ApiToken(Document):
    """Named API token. Plaintext shown once at creation; only hash stored."""

    model_config = ConfigDict(populate_by_name=True)

    name: str                          # human-readable label, e.g. "n1mm-logger"
    token_prefix: str                  # first 8 chars of plaintext after "ollog_"; stored clear for lookup narrowing
    hashed_token: str                  # Argon2 hash of full plaintext token
    user_id: PydanticObjectId          # FK → users._id
    created_at: datetime
    last_used_at: Optional[datetime] = None
    enabled: bool = True

    class Settings:
        name = "api_tokens"
        indexes = [
            IndexModel(
                [("user_id", pymongo.ASCENDING)],
                name="user_id_idx",
            ),
            IndexModel(
                [("token_prefix", pymongo.ASCENDING)],
                name="token_prefix_idx",
            ),
        ]
```

### Token fields rationale

| Field | Why |
|-------|-----|
| `name` | Lets users identify which token belongs to which client (n1mm, fldigi, script, etc.) |
| `token_prefix` | First 8 chars of the plaintext stored in clear; used to narrow the Argon2 verify target to one document rather than scanning all tokens |
| `hashed_token` | Argon2 hash of the full `ollog_<32chars>` plaintext — reuses `hash_password()` from `app/auth/service.py` |
| `user_id` | Foreign key to `users._id`; enables listing and revoking tokens per user |
| `created_at` | Audit and display |
| `last_used_at` | Optional; updated on successful verification; useful for identifying stale tokens |
| `enabled` | Soft-revocation without deletion; hard delete is also supported |

### Token format and generation

```python
import secrets

def generate_api_token() -> str:
    """Return a new plaintext API token. Call once; do not store the return value."""
    return "ollog_" + secrets.token_urlsafe(24)  # 32 URL-safe base64 chars

def token_prefix_from_plaintext(plaintext: str) -> str:
    """Extract the 8-char prefix used for DB lookup narrowing."""
    # plaintext = "ollog_<32chars>"; prefix is chars 6–14
    return plaintext[6:14]
```

`secrets.token_urlsafe(24)` produces 32 characters. The `ollog_` prefix makes tokens recognisable in config files and enables log redaction rules. Total length: 38 characters.

### Hashing strategy

Reuse `hash_password()` from `app/auth/service.py` directly — it is `pwdlib.PasswordHash.recommended()` which selects Argon2. No new crypto surface. Token verification:

```python
# In auth/dependencies.py — new api key dep
prefix = token_prefix_from_plaintext(raw_key)
candidates = await ApiToken.find(
    {"token_prefix": prefix, "enabled": True}
).to_list()
for candidate in candidates:
    if verify_password(raw_key, candidate.hashed_token):
        # update last_used_at, resolve User, return
        ...
```

In normal operation the `token_prefix` index returns exactly one candidate; Argon2 verify runs once. The prefix is not a secret — it narrows the candidate set but cannot authenticate on its own.

---

## Question 2: FastAPI Dependency Integration — X-API-Key Without Breaking JWT Deps

**Recommendation: Add new parallel dependency functions. Do not modify existing deps.**

### Why not modify existing deps

`get_current_user` and `get_current_operator_callsign` are imported and used directly across `qso/router.py`, `admin/router.py`, `profile/router.py`, `main.py`, and others. Modifying their signatures or adding fallback logic introduces regression risk across all callsites. The existing JWT path must remain unchanged.

### New dependencies to add in `app/auth/dependencies.py`

```python
from fastapi.security import APIKeyHeader
from fastapi import Security

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user_api_key(
    api_key: str | None = Security(api_key_header),
) -> User:
    """FastAPI dependency: resolve X-API-Key header to a User.

    Raises 401 if header is missing, token not found, or disabled.
    Updates last_used_at on the ApiToken document on success.
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header required",
        )
    from app.auth.models import ApiToken
    prefix = api_key[6:14]  # chars after "ollog_"
    candidates = await ApiToken.find(
        {"token_prefix": prefix, "enabled": True}
    ).to_list()
    for candidate in candidates:
        if verify_password(api_key, candidate.hashed_token):
            user = await User.get(candidate.user_id)
            if user is None or not user.enabled:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="Could not validate credentials")
            await candidate.update(
                {"$set": {"last_used_at": datetime.now(tz=timezone.utc)}}
            )
            return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )


async def get_current_operator_callsign_api_key(
    user: User = Depends(get_current_user_api_key),
) -> str:
    """API key version of callsign injection for REST endpoints."""
    return user.callsign
```

### Opt-in per route — no global middleware

Do not use a middleware or override all existing deps. Wire the new dep only into routes you explicitly want to open to API key auth. For the initial milestone, that means `POST /api/qsos/` and the token CRUD endpoints themselves.

For routes where both JWT Bearer and API key should work:

```python
async def _try_bearer(
    token: str | None = Depends(OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)),
) -> User | None:
    if token is None:
        return None
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if username is None:
            return None
        user = await User.find_one({"username": username})
        return user if (user and user.enabled) else None
    except InvalidTokenError:
        return None


async def get_operator_any_auth(
    bearer_user: User | None = Depends(_try_bearer),
    api_key_user: User | None = Depends(_try_get_user_api_key_optional),
) -> str:
    user = bearer_user or api_key_user
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Could not validate credentials",
                            headers={"WWW-Authenticate": "Bearer"})
    return user.callsign
```

For the initial milestone, adding `get_current_operator_callsign_api_key` to `POST /api/qsos/` (alongside the existing `get_current_user` dep, or replacing it with the union) is sufficient to unblock N1MM+ and similar clients. The token CRUD endpoints themselves use `get_current_user` (JWT only) so users must be logged in via the browser to manage their tokens.

---

## Question 3: UDP `_handle_datagram` — Where to Check `APP_OLLOG_TOKEN`

**Recommendation: Resolve at lifespan startup in `main.py`, not inside `_handle_datagram`.**

### Why not per-datagram

`_handle_datagram` is a hot path. Every UDP packet dispatches an `asyncio.create_task` to this function. Adding a DB query plus Argon2 verification per datagram would:

- Add ~100–200ms of latency per datagram (Argon2 cost)
- Introduce DB failure modes to a path that currently never touches the database for identity resolution
- Create head-of-line blocking if a burst of datagrams arrives simultaneously

The existing architecture is explicit: `QSODatagramProtocol.__init__` accepts `operator` and `user` at construction time, and `_handle_datagram` receives them as arguments. This is by design. Token resolution should follow the same pattern.

`_handle_datagram` itself does not change.

### Changes in `main.py` lifespan

Add `app_ollog_token: str | None = None` to `Settings` in `config.py`, then extend the UDP startup block:

```python
# In lifespan, replacing the current UDP startup block:
if settings.udp_enabled:
    from app.auth.models import User as UserModel, ApiToken
    from app.auth.service import verify_password, token_prefix_from_plaintext
    from app.udp.server import start_udp_listener

    udp_user: UserModel | None = None
    udp_op: str | None = None

    if settings.app_ollog_token:
        # Token-based identity takes precedence over UDP_OPERATOR
        raw = settings.app_ollog_token
        prefix = token_prefix_from_plaintext(raw)
        candidates = await ApiToken.find(
            {"token_prefix": prefix, "enabled": True}
        ).to_list()
        for candidate in candidates:
            if verify_password(raw, candidate.hashed_token):
                udp_user = await UserModel.get(candidate.user_id)
                if udp_user and udp_user.enabled:
                    udp_op = udp_user.callsign
                    logger.info(
                        "UDP identity resolved via APP_OLLOG_TOKEN: %s", udp_op
                    )
                    await candidate.update(
                        {"$set": {"last_used_at": datetime.now(tz=timezone.utc)}}
                    )
                break
        if udp_op is None:
            logger.warning(
                "APP_OLLOG_TOKEN set but could not resolve to a valid user — "
                "falling back to UDP_OPERATOR"
            )

    if udp_op is None and settings.udp_operator:
        # Existing behaviour: callsign-pinned identity
        udp_op = settings.udp_operator.upper()
        udp_user = await UserModel.find_one({"callsign": udp_op})
        if udp_user is None:
            logger.warning(
                "UDP_OPERATOR callsign %r not found in DB — profile stamping disabled",
                udp_op,
            )

    udp_transport, _ = await start_udp_listener(
        settings.udp_bind_host,
        settings.udp_port,
        operator=udp_op,
        user=udp_user,
    )
```

Priority order: `APP_OLLOG_TOKEN` → `UDP_OPERATOR` → `None` (datagrams discarded, existing behaviour).

---

## New vs. Modified Components

| Component | Status | Nature of change |
|-----------|--------|-----------------|
| `app/auth/models.py` | Modified | Add `ApiToken` Beanie Document |
| `app/auth/service.py` | Unchanged | `hash_password` / `verify_password` reused as-is; add `generate_api_token()` and `token_prefix_from_plaintext()` helper functions (pure, no deps) |
| `app/auth/dependencies.py` | Modified | Add `get_current_user_api_key`, `get_current_operator_callsign_api_key`; optionally add `_try_bearer` + `get_operator_any_auth` union dep |
| `app/auth/router.py` | Modified | Add `POST /auth/tokens`, `GET /auth/tokens`, `DELETE /auth/tokens/{id}` behind JWT auth |
| `app/config.py` | Modified | Add `app_ollog_token: str | None = None` |
| `app/database.py` | Modified | Add `ApiToken` to `init_beanie` `document_models` list |
| `app/main.py` | Modified | Extend lifespan UDP block for `APP_OLLOG_TOKEN` resolution |
| `app/udp/server.py` | Unchanged | `_handle_datagram`, `QSODatagramProtocol`, `start_udp_listener` all unchanged |
| `app/qso/router.py` | Optionally modified | Swap or supplement `get_current_user` dep on `POST /api/qsos/` to accept API key |

---

## Recommended Build Order

The quality gate requires that UDP changes depend on token lookup working first.

| Step | Component | Why this order |
|------|-----------|----------------|
| 1 | `ApiToken` model in `auth/models.py` + `database.py` registration | No other step can query tokens until the collection exists and Beanie knows about it |
| 2 | `generate_api_token()` + `token_prefix_from_plaintext()` in `auth/service.py` | Pure functions; testable in isolation; required by steps 3 and 4 |
| 3 | Token CRUD in `auth/router.py` (`POST`, `GET`, `DELETE /auth/tokens`) | Allows manual creation and verification of the full token lifecycle before wiring into auth deps or UDP |
| 4 | `get_current_user_api_key` in `auth/dependencies.py` | Depends on steps 1–2; uses `verify_password` already in service.py |
| 5 | Opt-in to REST routes in `qso/router.py` | Depends on step 4; surgical `Depends()` change per route |
| 6 | `app_ollog_token` in `config.py` + lifespan block in `main.py` | Depends on steps 1–2 for `ApiToken.find()` and `token_prefix_from_plaintext()`; `_handle_datagram` untouched |

Steps 1–3 can be delivered and tested end-to-end (token creation, listing, deletion via JWT auth) before any existing endpoint is modified. Steps 4–6 are independent branches that can proceed in parallel once step 2 is complete.

---

## Data Flow

### Token Creation

```
POST /auth/tokens
  Authorization: Bearer <jwt>
  {"name": "n1mm-logger"}
        |
        ▼
get_current_user → current_user verified
        |
        ▼
generate_api_token() → "ollog_<32chars>"
token_prefix = plaintext[6:14]
hashed = hash_password(plaintext)   # Argon2
        |
        ▼
ApiToken(name, token_prefix, hashed_token, user_id=current_user.id,
         created_at=now).insert()
        |
        ▼
{"token": "ollog_<32chars>", "id": "...", "name": "n1mm-logger"}
  # plaintext returned ONCE — not stored, not re-fetchable
```

### API Key Request Auth

```
POST /api/qsos/
  X-API-Key: ollog_<32chars>
        |
        ▼
get_current_user_api_key dependency
        |
        ▼
prefix = key[6:14]
ApiToken.find({"token_prefix": prefix, "enabled": True})
  → usually 0 or 1 result
        |
        ▼
verify_password(raw_key, candidate.hashed_token)  # Argon2 ~100ms
        |
        ▼  (match)
User.get(candidate.user_id) → return user
candidate.last_used_at = now  (fire-and-forget update)
        |
        ▼
build_qso_dict(record, user.callsign, profile=user)
QSO.insert()
```

### UDP Token Resolution (startup only)

```
lifespan startup
        |
        ▼
APP_OLLOG_TOKEN set?
  YES → prefix = token[6:14]
        ApiToken.find(prefix, enabled=True) → Argon2 verify → User.get()
        udp_op = user.callsign, udp_user = user
  NO  → UDP_OPERATOR set?
          YES → User.find_one(callsign)  [existing behaviour]
          NO  → udp_op = None
        |
        ▼
start_udp_listener(host, port, operator=udp_op, user=udp_user)
        |
        ▼
QSODatagramProtocol stores (operator, user) for process lifetime
  — _handle_datagram unchanged —
```

---

## Anti-Patterns

### Anti-Pattern 1: Embedding Tokens in `User`

**What people do:** Add `api_tokens: list[ApiToken] = []` as a subdocument array on the `User` document.

**Why it's wrong:** Every `User.find_one()` loads the full token array. Token lookup by prefix requires `$elemMatch`. Revocation requires `$pull` with nested filter. Adding a user's second token requires `$push`. All operations are more complex than equivalent top-level document ops.

**Do this instead:** Separate `api_tokens` collection with a `user_id` index.

### Anti-Pattern 2: Per-Datagram Token Lookup

**What people do:** Check `APP_OLLOG_TOKEN` inside `_handle_datagram`, doing a DB query + Argon2 verify on every UDP packet.

**Why it's wrong:** Argon2 is ~100ms. A burst of datagrams queues behind serial verifications. DB failure modes enter the hot path. The existing design explicitly resolves identity once at startup.

**Do this instead:** Resolve the token during `lifespan` startup, cache `(operator, user)` on `QSODatagramProtocol`. Same pattern as `UDP_OPERATOR` today.

### Anti-Pattern 3: Modifying Existing JWT Dependencies

**What people do:** Add `X-API-Key` fallback logic directly into `get_current_user` or `get_current_operator_callsign`.

**Why it's wrong:** These deps are used across every authenticated route. Adding a second auth path touches all callsites and conflates two distinct mechanisms in a single function.

**Do this instead:** New parallel dep functions. Existing routes unchanged. New routes opt in explicitly.

### Anti-Pattern 4: Storing Plaintext Tokens

**What people do:** Store the full token plaintext for "show again" convenience.

**Why it's wrong:** If `api_tokens` is exfiltrated, all tokens are immediately usable. The one-time display pattern is standard (GitHub, Stripe, etc.).

**Do this instead:** Store only the Argon2 hash and the clear-text prefix. Return plaintext in the creation response and never again.

### Anti-Pattern 5: Full Token Scan for Verification

**What people do:** On every API key request, load all tokens for the user and Argon2-verify each one to find a match.

**Why it's wrong:** With N tokens per user, N Argon2 operations at ~100ms each means N*100ms latency. Even with 5 tokens that is 500ms worst-case.

**Do this instead:** Use the `token_prefix` index to narrow to one candidate, then verify that one. Prefix lookup is O(1) index read; verification is one Argon2 call.

---

## Integration Points: Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `auth/dependencies.py` → `auth/models.py` (ApiToken) | Beanie `find()` | Same pattern as existing `User.find_one()` |
| `auth/dependencies.py` → `auth/service.py` | `verify_password()` call | No new surface; existing Argon2 function |
| `main.py` lifespan → `auth/models.py` (ApiToken) | Beanie `find()` | Added to existing UDP startup block |
| `auth/router.py` → `auth/service.py` | `generate_api_token()`, `token_prefix_from_plaintext()`, `hash_password()` | Token CRUD uses same service module as user password management |
| `qso/router.py` → `auth/dependencies.py` | `Depends(get_current_operator_callsign_api_key)` | Opt-in per route |

---

## Sources

- Direct codebase inspection: `app/auth/models.py`, `app/auth/dependencies.py`, `app/auth/service.py`, `app/udp/server.py`, `app/main.py`, `app/config.py`, `app/database.py`, `app/qso/router.py` (HIGH confidence — live codebase)
- FastAPI `APIKeyHeader` security utility: `fastapi.security.APIKeyHeader` — standard FastAPI pattern for header-based API keys (HIGH confidence — stable FastAPI API)
- Argon2 prefix-narrowing pattern: industry standard for API key design; prefix stored clear for lookup, hash stored for verification — used by GitHub personal access tokens, Stripe API keys, and others (HIGH confidence — widely documented pattern)
- `secrets.token_urlsafe` for cryptographic token generation: Python stdlib, appropriate for secrets (HIGH confidence)

---

*Architecture research for: named API token auth integration — ollog FastAPI/Beanie/MongoDB*
*Researched: 2026-04-09*
