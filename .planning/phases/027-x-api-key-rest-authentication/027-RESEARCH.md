# Phase 27: X-API-Key REST Authentication - Research

**Researched:** 2026-04-09
**Domain:** FastAPI dual-auth dependency (JWT Bearer + X-API-Key header), Beanie token lookup
**Confidence:** HIGH

## Summary

Phase 27 adds `X-API-Key` as a second valid credential type on all QSO REST API endpoints (`/api/qsos/*`) while keeping JWT Bearer as the only accepted method on admin (`/admin/users/*`), profile (`/api/profile`), and UI routes. The token infrastructure — `ApiToken` document, `hash_api_token()`, `verify_api_token()`, `token_is_active()` — is already complete from Phases 25–26. This phase is entirely about wiring those building blocks into a new FastAPI dependency.

The critical architectural challenge is that `OAuth2PasswordBearer(auto_error=True)` (the current setting in `app/auth/dependencies.py`) raises **HTTP 403** before any fallback scheme can execute. The fix is to use `auto_error=False` on **both** `OAuth2PasswordBearer` and `APIKeyHeader`, then raise HTTP 401 manually after both return `None`. This is confirmed by the official FastAPI source: `OAuth2PasswordBearer.__call__` with `auto_error=False` returns `None` rather than raising, and `APIKeyHeader.__call__` with `auto_error=False` also returns `None` when the header is absent.

The implementation requires one new dependency function — `get_current_user_jwt_or_apikey` — that resolves operator identity from either credential type and returns the same `User` object the existing `get_current_user` returns. QSO router endpoints must swap their `Depends(get_current_user)` / `Depends(get_current_operator_callsign)` calls to the new dual-auth dependency. Admin, profile, and token management endpoints retain the existing JWT-only dependencies unchanged.

**Primary recommendation:** Add `get_current_user_jwt_or_apikey` and `get_current_operator_callsign_jwt_or_apikey` to `app/auth/dependencies.py` using `auto_error=False` on both security schemes; update only `app/qso/router.py` to use them.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.135.0 | `APIKeyHeader`, `OAuth2PasswordBearer` security classes | Already in use; official security primitives |
| Beanie | >=2.1.0 | Async `ApiToken` document lookup by prefix + hash | Already in use; `find_one` matches the existing pattern |
| Python stdlib `hmac` | stdlib | `verify_api_token()`, `token_is_active()` | Already implemented in `app/tokens/service.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `fastapi.security.APIKeyHeader` | (bundled with FastAPI) | Extract `X-API-Key` header value | New in Phase 27 |
| `fastapi.security.OAuth2PasswordBearer` | (bundled) | Extract Bearer token (already used) | Keep on JWT path |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `APIKeyHeader` | `Header(None, alias="X-API-Key")` | Direct `Header()` works but doesn't appear in OpenAPI "Authorize" UI and skips FastAPI's built-in security plumbing |
| Single new dependency | Middleware | Middleware complicates per-route scoping — admin routes must never accept API keys |

**No new installation needed** — `fastapi.security.APIKeyHeader` ships with FastAPI, which is already in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure

No new files. All changes land in existing files:

```
app/
├── auth/
│   └── dependencies.py   # ADD: get_current_user_jwt_or_apikey,
│                         #      get_current_operator_callsign_jwt_or_apikey
│                         # KEEP: all existing JWT-only deps unchanged
├── qso/
│   └── router.py         # CHANGE: swap Depends() on 5 endpoints
└── tokens/
    └── service.py        # Already has verify_api_token(), token_is_active()
                          # (no changes needed)
```

### Pattern 1: Dual-Auth Dependency with auto_error=False

**What:** Create both security scheme objects with `auto_error=False`. In the dependency function, attempt JWT first, then API key. Raise 401 manually only when both fail.

**When to use:** Any endpoint that must accept either credential type with identical operator isolation.

**Example:**
```python
# Source: https://github.com/tiangolo/fastapi/blob/master/fastapi/security/oauth2.py
# Source: https://fastapi.tiangolo.com/reference/security/
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

# Both schemes with auto_error=False — neither raises automatically
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
_apikey_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_current_user_jwt_or_apikey(
    bearer_token: str | None = Depends(_oauth2_scheme),
    api_key: str | None = Depends(_apikey_scheme),
) -> User:
    # Path 1: JWT Bearer
    if bearer_token is not None:
        # reuse existing decode_access_token / User.find_one logic
        ...
        return user

    # Path 2: X-API-Key
    if api_key is not None:
        prefix = api_key[6:14]   # chars 6-14 of "ollog_<body>"
        candidates = await ApiToken.find(
            ApiToken.token_prefix == prefix
        ).to_list()
        for candidate in candidates:
            if token_is_active(candidate) and verify_api_token(api_key, candidate.hashed_token):
                user = await User.find_one({"_id": candidate.user_id})
                if user is not None and user.enabled:
                    return user

    # Both paths failed — raise 401 (NOT 403)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
```

**Key detail:** `_oauth2_scheme` and `_apikey_scheme` are module-level singletons (not instantiated per-request). The existing `oauth2_scheme` object in `dependencies.py` uses `auto_error=True` — the new objects are separate.

### Pattern 2: Callsign Projection Dependency

**What:** Thin wrapper over the dual-auth user dependency, exactly mirroring `get_current_operator_callsign`.

**Example:**
```python
async def get_current_operator_callsign_jwt_or_apikey(
    user: User = Depends(get_current_user_jwt_or_apikey),
) -> str:
    return user.callsign
```

### Pattern 3: Token Lookup via Prefix Index

**What:** The `ApiToken` compound index `(token_prefix, user_id)` was built for fast partial key scan. A lookup fetches only tokens matching the first 8 chars of the token body, then verifies the full HMAC.

**Why prefix lookup matters:** `hashed_token` cannot be searched directly without already knowing the full token (the hash requires the secret). The prefix lets MongoDB narrow to ≤O(n) candidates before HMAC verification.

```python
# token body starts at index 6 ("ollog_<body>")
prefix = api_key[6:14]  # first 8 chars of the 43-char URL-safe body
candidates = await ApiToken.find(ApiToken.token_prefix == prefix).to_list()
```

If the token does not start with `"ollog_"` or is shorter than 14 characters, prefix extraction should be guarded before the DB call to avoid a full-collection scan.

### Pattern 4: last_used_at Update (Optional but Useful)

**What:** After a successful API key authentication, update `last_used_at` on the token document. Not required by Phase 27 requirements but aligns with the model field that already exists.

**How:** `await candidate.set({ApiToken.last_used_at: datetime.now(tz=timezone.utc)})` after identity is confirmed. This is a fire-and-forget update — failure should not block the request.

### Anti-Patterns to Avoid

- **Keep `auto_error=True` on the original `oauth2_scheme`:** The existing `get_current_user` dependency must continue to use `auto_error=True` — it is still used by admin, profile, and token management routes that should return 401 when no Bearer token is present. Do not modify the existing scheme object.
- **Sharing the scheme object:** Do not reuse `oauth2_scheme` (the existing module-level object with `auto_error=True`) in the new dual-auth dependency. Create new scheme objects with `auto_error=False`.
- **Swapping deps on admin/profile routes:** `app/admin/router.py`, `app/profile/router.py`, `app/qso/ui_router.py`, and `app/tokens/router.py` must NOT change. Only `app/qso/router.py` gets the new dependency.
- **Accepting callsign from request body / query params:** Operator identity MUST still come exclusively from the resolved `User` document, never from the request. The new dependency must return the same `User` the JWT path returns.
- **Catching broad exceptions on HMAC verify:** `verify_api_token()` is pure Python; it cannot raise unless the arguments are wrong types. No broad `except Exception` is needed around it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Constant-time token comparison | Custom compare loop | `verify_api_token()` in `tokens/service.py` | Already uses `hmac.compare_digest` — timing-safe by construction |
| Token activity check | Inline `enabled` + `expires_at` checks | `token_is_active()` in `tokens/service.py` | Centralised; tested; handles timezone-aware comparison correctly |
| Header extraction | `request.headers.get("X-API-Key")` directly | `APIKeyHeader(name="X-API-Key", auto_error=False)` | Appears in OpenAPI Authorize UI; integrates with FastAPI's security plumbing |
| JWT decode + user lookup | Inline `decode_access_token` + DB call | Reuse the existing logic already in `get_current_user` (or factor into a private `_user_from_bearer` helper) | Avoids duplicating error handling and keeping two implementations in sync |

**Key insight:** Every cryptographic and persistence operation is already written and tested. Phase 27 is purely a dependency-wiring task.

## Common Pitfalls

### Pitfall 1: OAuth2PasswordBearer Returns 403 Before API Key Can Run

**What goes wrong:** `OAuth2PasswordBearer(auto_error=True)` raises `HTTPException(403)` the moment the `Authorization` header is missing or malformed — before `APIKeyHeader` Depends ever runs. A curl request with only `X-API-Key` gets 403 instead of the expected authenticated response.

**Why it happens:** FastAPI resolves all `Depends()` in the dependency graph, but `OAuth2PasswordBearer.__call__` raises immediately when `auto_error=True`. The exception propagates before subsequent scheme resolution.

**How to avoid:** Use `auto_error=False` on **both** `_oauth2_scheme` and `_apikey_scheme` in the new dual-auth dependency. Confirmed by FastAPI source: `OAuth2PasswordBearer.__call__` returns `None` (not raises) when `auto_error=False` and the header is absent.

**Warning signs:** Tests with `X-API-Key` header but no `Authorization` header returning 403 (not 401, not 200).

### Pitfall 2: Modifying the Existing oauth2_scheme Object

**What goes wrong:** If the existing `oauth2_scheme = OAuth2PasswordBearer(tokenUrl=..., auto_error=True)` is changed to `auto_error=False`, all admin, profile, and token-management endpoints lose their automatic 401 enforcement — unauthenticated requests silently pass `None` into `get_current_user`.

**Why it happens:** The module-level `oauth2_scheme` is shared across all existing dependencies.

**How to avoid:** Create two new private module-level scheme objects (`_oauth2_scheme_optional`, `_apikey_scheme_optional`) used only by the new dual-auth dependency.

### Pitfall 3: Token Prefix Out of Bounds

**What goes wrong:** An attacker (or misconfigured client) sends `X-API-Key: short` — a token shorter than 14 characters. `api_key[6:14]` silently returns a shorter string and queries the DB with a partial/wrong prefix.

**Why it happens:** Python string slicing does not raise on out-of-range indices.

**How to avoid:** Guard before DB call: `if not api_key.startswith("ollog_") or len(api_key) < 14: raise HTTPException(401, ...)`.

**Warning signs:** DB queries for `token_prefix == ""` in logs.

### Pitfall 4: HTTP 403 vs 401 Confusion in Tests

**What goes wrong:** Existing tests for admin/profile endpoints check `status_code in (401, 403)` (see `test_token_api.py` lines 301–321). If Phase 27 accidentally changes the behavior of those endpoints (by swapping their deps), those tests may still pass but the semantic contract breaks.

**Why it happens:** Tests for unauthenticated admin access were written permissively.

**How to avoid:** Phase 27 tests for QSO endpoints must assert exactly `status_code == 401` for missing/invalid credentials. Admin and profile endpoints should not be touched.

### Pitfall 5: Operator Isolation Audit Test Needs Updating

**What goes wrong:** `tests/test_operator_isolation.py` contains a `CALLSIGN_DEPS` set that lists acceptable dependency names for QSO routes (line 33–36). After Phase 27, QSO endpoints use `get_current_operator_callsign_jwt_or_apikey` instead of `get_current_operator_callsign`. The introspection test will fail if not updated.

**Why it happens:** The isolation audit checks dep names by string comparison.

**How to avoid:** Add `"get_current_operator_callsign_jwt_or_apikey"` to `CALLSIGN_DEPS` in that test. (Alternatively, both can be accepted — JWT-only routes remain valid.)

### Pitfall 6: create_qso Uses get_current_user, Not get_current_operator_callsign

**What goes wrong:** Looking at `app/qso/router.py`, `create_qso` uses `Depends(get_current_user)` (to access the full `User` object for profile stamping), while the other four endpoints use `Depends(get_current_operator_callsign)`. The dual-auth equivalent for `create_qso` must return a `User` object, not just a callsign string.

**Why it happens:** `build_qso_dict` takes `profile=user` to stamp OPERATOR, STATION_CALLSIGN, etc.

**How to avoid:** `get_current_user_jwt_or_apikey` returns a `User`. `create_qso` swaps to `Depends(get_current_user_jwt_or_apikey)`. The other four swap to `Depends(get_current_operator_callsign_jwt_or_apikey)`.

## Code Examples

Verified patterns from official sources:

### APIKeyHeader Import and Instantiation
```python
# Source: https://fastapi.tiangolo.com/reference/security/
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

_oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
_apikey_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
```

### auto_error=False Confirmed Behavior (from FastAPI source)
```python
# Source: github.com/tiangolo/fastapi/blob/master/fastapi/security/oauth2.py
async def __call__(self, request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    scheme, param = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != "bearer":
        if self.auto_error:
            raise self.make_not_authenticated_error()
        else:
            return None   # <-- returns None, not raises
    return param

# Source: github.com/tiangolo/fastapi/blob/master/fastapi/security/api_key.py
async def __call__(self, request: Request) -> str | None:
    api_key = request.headers.get(self.model.name)
    # check_api_key returns None when auto_error=False and header is absent
    return self.check_api_key(api_key)
```

### Prefix Extraction with Guard
```python
# Tokens have format: "ollog_<43-char-url-safe-body>"
# Prefix is chars 6-14 (first 8 chars of body)
_TOKEN_PREFIX_START = 6
_TOKEN_PREFIX_END = 14

def _extract_prefix(api_key: str) -> str | None:
    if not api_key.startswith("ollog_") or len(api_key) < _TOKEN_PREFIX_END:
        return None
    return api_key[_TOKEN_PREFIX_START:_TOKEN_PREFIX_END]
```

### Beanie Token Lookup Pattern
```python
# ApiToken has compound index (token_prefix, user_id) — prefix scan is indexed
from app.tokens.models import ApiToken
from app.tokens.service import token_is_active, verify_api_token

prefix = api_key[6:14]
candidates = await ApiToken.find(
    ApiToken.token_prefix == prefix,
    ApiToken.enabled == True,  # noqa: E712
).to_list()

for candidate in candidates:
    if token_is_active(candidate) and verify_api_token(api_key, candidate.hashed_token):
        user = await User.find_one({"_id": candidate.user_id})
        if user is not None and user.enabled:
            return user
```

### Testing Pattern — API Key Auth on QSO Endpoint
```python
# Pattern mirrors existing test_qso_api.py fixture structure
# Add ApiToken to init_beanie document_models in test fixture

async def _create_api_key(user: User, name: str = "test-key") -> str:
    from app.tokens.service import generate_api_token, hash_api_token
    full_token, prefix = generate_api_token()
    doc = ApiToken(
        user_id=user.id,
        name=name,
        token_prefix=prefix,
        hashed_token=hash_api_token(full_token),
    )
    await doc.insert()
    return full_token

# In test:
resp = await client.get(
    "/api/qsos/",
    headers={"X-API-Key": api_key},   # no Authorization header
)
assert resp.status_code == 200
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JWT-only QSO endpoints | JWT or X-API-Key (dual auth) | Phase 27 | Enables machine-to-machine and UDP-like REST clients without session management |
| `auto_error=True` on all schemes | `auto_error=False` + manual 401 for dual-auth deps | Phase 27 | Prevents premature 403 from OAuth2PasswordBearer |

**Note:** The existing JWT-only `get_current_user` and `get_current_operator_callsign` are not deprecated — they remain the correct choice for admin, profile, and token management endpoints.

## Open Questions

1. **Should `last_used_at` be updated on each API key auth?**
   - What we know: The `ApiToken.last_used_at` field exists and is `Optional[datetime]`. The Phase 27 requirements don't mention it.
   - What's unclear: Whether the planner should include this as an explicit task.
   - Recommendation: Include as an optional sub-task (low risk, high observability value). A fire-and-forget `await candidate.set(...)` after identity resolution adds no latency to the critical path.

2. **Does `test_operator_isolation.py` route introspection break?**
   - What we know: The test checks dep names by string (lines 33–36 of `test_operator_isolation.py`). `get_current_operator_callsign_jwt_or_apikey` is a new name.
   - What's unclear: Whether the test assertion needs `get_current_operator_callsign_jwt_or_apikey` added, or whether the QSO routes can still use a mix of both deps.
   - Recommendation: Add the new name to `CALLSIGN_DEPS` in the isolation audit test.

3. **Should the `create_qso` dual-auth dep also update `last_used_at`?**
   - What we know: `create_qso` needs `User` (not just callsign), so it uses `get_current_user_jwt_or_apikey`. Both the user-returning and callsign-returning deps share the same authentication logic.
   - Recommendation: Factor the authentication logic into a private helper to avoid duplicating the `last_used_at` update.

## Sources

### Primary (HIGH confidence)
- FastAPI source `fastapi/security/oauth2.py` — confirmed `OAuth2PasswordBearer.__call__` returns `None` (not raises) with `auto_error=False`
- FastAPI source `fastapi/security/api_key.py` — confirmed `APIKeyHeader.__call__` returns `None` with `auto_error=False`
- https://fastapi.tiangolo.com/reference/security/ — official parameter documentation for `APIKeyHeader` and `OAuth2PasswordBearer`
- `app/tokens/service.py` (codebase) — `verify_api_token()`, `token_is_active()` already implemented
- `app/tokens/models.py` (codebase) — `ApiToken` compound index on `(token_prefix, user_id)` confirmed
- `app/auth/dependencies.py` (codebase) — existing `oauth2_scheme` uses `auto_error=True`, confirmed it must not be changed
- `app/qso/router.py` (codebase) — 5 endpoints audited; `create_qso` uses `get_current_user`, others use `get_current_operator_callsign`

### Secondary (MEDIUM confidence)
- https://github.com/fastapi/fastapi/discussions/9601 — community-confirmed pattern for combining OAuth2PasswordBearer + APIKeyHeader with auto_error=False
- https://github.com/fastapi/fastapi/issues/2026 — confirmed auto_error=False on HTTP security schemes returns None rather than raising
- https://github.com/fastapi/fastapi/issues/10177 — multiple FastAPI security classes return 403 with auto_error=True; auto_error=False resolves this

### Tertiary (LOW confidence)
- None — all critical claims verified by source code or official docs.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — FastAPI security classes verified from official docs and source; token infrastructure verified from codebase
- Architecture: HIGH — auto_error=False behavior verified from FastAPI source; prefix lookup pattern verified from existing model/index; both confirmed from code
- Pitfalls: HIGH — 403 vs 401 issue confirmed from FastAPI source and GitHub issues; prefix guard is straightforward Python; operator isolation audit test confirmed from reading the test file

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (FastAPI security APIs are stable; no fast-moving changes expected)
