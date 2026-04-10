# Phase 28: UDP APP_OLLOG_TOKEN Support - Research

**Researched:** 2026-04-09
**Domain:** asyncio UDP datagram processing, in-memory token cache, cross-coroutine cache invalidation
**Confidence:** HIGH

---

## Summary

Phase 28 adds per-datagram operator identity resolution via an `APP_OLLOG_TOKEN` ADIF field
embedded in UDP datagrams. When the field is present, the in-memory token cache resolves it
to a callsign + User object; when absent, existing `UDP_OPERATOR` behaviour is unchanged
(zero regression). The cryptographic machinery (`hash_api_token`, `verify_api_token`,
`token_is_active`) already exists in `app/tokens/service.py` and must be reused exactly.

The central design problem is cache invalidation: the ASGI request handlers that create and
revoke tokens (in `app/tokens/router.py` and `app/qso/ui_router.py`) must signal the UDP
datagram handler to refresh its in-memory cache — all within the same asyncio event loop.
The correct primitive for this is a module-level `UDPTokenCache` object that holds a `dict`
protected by `asyncio.Lock`, exposed to router code via a `notify_cache_refresh()` function.
`QSODatagramProtocol` holds a reference to this shared cache instance.

No new dependencies are required. All needed primitives are Python stdlib (`asyncio.Lock`),
the already-installed Beanie/PyMongo stack, and the existing token service layer. The
implementation follows the `ConnectionManager` module-global singleton pattern already used
in `app/feed/manager.py`.

**Primary recommendation:** Implement a `UDPTokenCache` singleton in `app/udp/token_cache.py`
using a dict + `asyncio.Lock`. Expose `load()` and `resolve(token)` methods and a
`notify_refresh()` call. Wire it into `QSODatagramProtocol._handle_datagram()` and call
`notify_refresh()` from every token create/revoke endpoint.

---

## Standard Stack

### Core (all already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `asyncio` | stdlib | `asyncio.Lock`, `asyncio.create_task` | Already used throughout `app/udp/server.py` and `app/feed/manager.py` |
| `beanie` | 2.1.0 | `ApiToken.find()` for cache population | Already used for all DB access |
| `pymongo` | 4.16.0 | Underlying driver | Already in use |
| `app/tokens/service.py` | local | `hash_api_token()`, `verify_api_token()`, `token_is_active()` | Phase 25/27 locked implementation |
| `app/auth/models.py` | local | `User` document lookup by callsign | Already used in UDP lifespan startup |

### No New Dependencies Required

All required primitives exist. New file: `app/udp/token_cache.py`.

---

## Architecture Patterns

### Recommended Project Structure

```
app/udp/
├── __init__.py         # unchanged
├── server.py           # extend _handle_datagram, pass cache ref to protocol
└── token_cache.py      # NEW: UDPTokenCache singleton + notify_refresh()
```

### Pattern 1: Module-Level Singleton Cache (matches app/feed/manager.py)

**What:** A single `UDPTokenCache` instance created at module import time, shared across
the lifespan startup (which calls `load()`) and the router endpoints (which call
`notify_refresh()`).

**When to use:** When ASGI code and asyncio protocol code share state within one event loop.

**Example:**
```python
# app/udp/token_cache.py
import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.auth.models import User

logger = logging.getLogger(__name__)


class UDPTokenCache:
    """In-memory HMAC-hash → (callsign, User) cache for UDP datagram auth.

    Loaded at startup; refreshed via notify_refresh() when any token is
    created or revoked. No MongoDB round-trip occurs per datagram.
    """

    def __init__(self) -> None:
        # Maps hashed_token → User object
        self._lock: asyncio.Lock = asyncio.Lock()
        self._cache: dict[str, "User"] = {}
        self._dirty: bool = True  # Force load on first resolve()

    async def load(self) -> None:
        """Full reload from MongoDB — called at startup and on invalidation."""
        from app.tokens.models import ApiToken
        from app.tokens.service import token_is_active
        from app.auth.models import User

        tokens = await ApiToken.find(ApiToken.enabled == True).to_list()  # noqa: E712
        new_cache: dict[str, User] = {}
        for token in tokens:
            if not token_is_active(token):
                continue
            user = await User.find_one({"_id": token.user_id})
            if user is not None and user.enabled:
                new_cache[token.hashed_token] = user

        async with self._lock:
            self._cache = new_cache
            self._dirty = False
        logger.info("UDP token cache loaded: %d active entries", len(new_cache))

    async def resolve(self, raw_token: str) -> "User | None":
        """Resolve a raw token string to a User, or None if invalid/unknown."""
        from app.tokens.service import hash_api_token

        async with self._lock:
            if self._dirty:
                # Snapshot dirty flag and release lock before the DB call
                pass  # handled by reload path below

        if self._dirty:
            await self.load()

        hashed = hash_api_token(raw_token)
        async with self._lock:
            return self._cache.get(hashed)

    def notify_refresh(self) -> None:
        """Mark cache dirty; next resolve() call will trigger a full reload.

        Synchronous — safe to call from any async context without awaiting.
        The actual reload is deferred to the next datagram that needs resolution.
        """
        self._dirty = True
        logger.debug("UDP token cache marked dirty — will reload on next resolve")


# Module-level singleton — imported by server.py and router endpoints
token_cache = UDPTokenCache()
```

**Note on `notify_refresh()` design:** Setting `_dirty = True` is the simplest
invalidation mechanism. Because the UDP server and all ASGI handlers run in the same
asyncio event loop (single thread), no OS-level thread safety is needed — only the
`asyncio.Lock` for dict swap atomicity during `load()`. An alternative is
`asyncio.create_task(token_cache.load())` called directly from router endpoints; both
approaches work. The `_dirty` flag approach defers the DB hit to the first datagram after
a token change, which is acceptable since UDP is low-frequency.

### Pattern 2: Extending `_handle_datagram` for Per-Datagram Token Resolution

**What:** Before falling back to `UDP_OPERATOR`, check for `APP_OLLOG_TOKEN` in the parsed
ADIF record. If present, resolve via cache. If resolution fails, reject with structured log.

**When to use:** Every datagram processing path — this is the core new branch.

**Example:**
```python
# Inside _handle_datagram(), after record = records[0] and before missing-fields check:

APP_TOKEN_FIELD = "APP_OLLOG_TOKEN"

token_value = record.pop(APP_TOKEN_FIELD, None)  # consume — don't pass to QSO dict
if token_value is not None:
    from app.udp.token_cache import token_cache
    resolved_user = await token_cache.resolve(token_value)
    if resolved_user is None:
        logger.warning(
            "UDP datagram src=%s:%s disposition=rejected reason=invalid-token",
            addr[0], addr[1],
        )
        return
    # Override operator and user with token-resolved identity
    operator = resolved_user.callsign
    user = resolved_user
# else: fall through to existing UDP_OPERATOR / user passed in from protocol
```

**Key points:**
- `record.pop(APP_TOKEN_FIELD, None)` removes the field from the record dict so it is
  never stored in the QSO document — it is a transport-layer auth field only.
- The existing `operator is None` guard immediately below is still the fallback path when
  no token field was present and no `UDP_OPERATOR` is configured.
- `_handle_datagram` signature gains an optional `cache` parameter — or it accesses the
  module singleton directly via lazy import. The lazy-import pattern matches existing code.

### Pattern 3: Wiring `notify_refresh()` into Token Create/Revoke Endpoints

All four endpoints that mutate token state must call `notify_refresh()`:

1. `app/tokens/router.py` — `POST /api/tokens/` (create)
2. `app/tokens/router.py` — `DELETE /api/tokens/{id}` (revoke)
3. `app/qso/ui_router.py` — `POST /log/tokens/create` (HTMX create)
4. `app/qso/ui_router.py` — `DELETE /log/tokens/{id}` (HTMX revoke)

```python
# After doc.insert() or token.set({ApiToken.enabled: False}):
from app.udp.token_cache import token_cache
token_cache.notify_refresh()
```

### Pattern 4: Startup Cache Load

In `app/main.py` lifespan, after `init_db()` completes and before `yield`, load the cache:

```python
# In lifespan(), after init_db() and _bootstrap_admin():
from app.udp.token_cache import token_cache
await token_cache.load()
```

This ensures the cache is warm before the first datagram arrives. If `udp_enabled` is
False, the load is still harmless (the cache sits unused).

### Anti-Patterns to Avoid

- **Per-datagram MongoDB query:** Never call `ApiToken.find()` inside `_handle_datagram`.
  This was the problem being solved. One DB round-trip per datagram at high ingestion
  rates is unacceptable.
- **Threading Lock instead of asyncio.Lock:** Do not use `threading.Lock`. The application
  is single-threaded asyncio. `threading.Lock` inside a coroutine blocks the event loop.
- **Storing the raw token value:** `APP_OLLOG_TOKEN` must be popped from the record dict
  before `build_qso_dict` — never persisted to MongoDB.
- **Silent fall-through on invalid token:** If `APP_OLLOG_TOKEN` is present but resolves
  to `None`, the datagram must be rejected with a WARNING log. It must NOT fall through
  to `UDP_OPERATOR` — that would be a security regression.
- **Blocking `notify_refresh()` call:** Do not `await token_cache.load()` inside the
  router handler's hot path. Mark dirty and let the next datagram trigger the reload, or
  fire-and-forget with `asyncio.create_task(token_cache.load())`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HMAC comparison | Custom token equality check | `verify_api_token()` in `app/tokens/service.py` | Already constant-time via `hmac.compare_digest`; timing-attack safe |
| Token active check | Custom expiry/enabled logic | `token_is_active()` in `app/tokens/service.py` | Handles timezone-naive UTC normalisation (documented edge case) |
| Token string hashing | Custom `sha256(token)` | `hash_api_token()` in `app/tokens/service.py` | Uses correct HMAC-SHA256 with `api_token_secret`; bare SHA-256 would be wrong |
| Thread-safe dict | `threading.RLock` or custom sentinel | `asyncio.Lock` | Single-threaded event loop; asyncio primitives are the right tool |

**Key insight:** The token cryptography is completely implemented in Phase 25/27. Phase 28
is a plumbing problem, not a crypto problem. Reuse, don't rebuild.

---

## Common Pitfalls

### Pitfall 1: APP_OLLOG_TOKEN Leaked into QSO Document

**What goes wrong:** The `APP_OLLOG_TOKEN` field from the ADIF record is passed to
`build_qso_dict()` and stored in MongoDB as a QSO field.

**Why it happens:** `build_qso_dict` takes `body_dict: dict` verbatim and passes extra
fields through. The parser preserves APP_ fields (`parser.py` line 24).

**How to avoid:** Use `record.pop("APP_OLLOG_TOKEN", None)` — not `.get()` — before the
`missing` fields check and before calling `build_qso_dict`.

**Warning signs:** QSO documents in MongoDB contain `APP_OLLOG_TOKEN` field.

### Pitfall 2: asyncio.Lock Created Outside Event Loop

**What goes wrong:** `asyncio.Lock()` created at module import time raises a deprecation
warning (Python 3.10+) or fails (Python 3.12+) if no running event loop exists at import.

**Why it happens:** Module-level instantiation of `asyncio.Lock()` runs during import,
before the event loop starts.

**How to avoid:** Python 3.10+ resolved this — `asyncio.Lock()` no longer requires a
running event loop at creation time. The `UDPTokenCache` class can instantiate `asyncio.Lock()`
in `__init__` safely. Verified: Python 3.12 docs confirm `asyncio.Lock()` constructor does
not require a running loop.

**Warning signs:** `DeprecationWarning: There is no current event loop` at import time
(Python 3.9 and earlier only — not relevant here since `requires-python = ">=3.12"`).

### Pitfall 3: Race Condition Between `_dirty` Flag and `load()`

**What goes wrong:** Two concurrent datagrams both see `_dirty=True`, both trigger
`load()`, causing two concurrent DB scans and a double-write to `_cache`.

**Why it happens:** The `_dirty` check and `load()` call are not atomic.

**How to avoid:** The double-load is harmless — both loads produce equivalent results and
the `async with self._lock` in `load()` serialises the final dict swap. The only cost is
a redundant DB read. For Phase 28's scale (ham radio UDP — low volume), this is acceptable.
A more rigorous fix (compare-and-swap with an additional loading flag) is not needed.

### Pitfall 4: Forgetting the HTMX Token Routes

**What goes wrong:** `notify_refresh()` is only wired into `app/tokens/router.py` but
not into the HTMX routes in `app/qso/ui_router.py`. Tokens created or revoked via the UI
do not invalidate the cache.

**Why it happens:** There are four token mutation endpoints across two routers. Easy to
miss the UI router.

**How to avoid:** The four endpoints are:
- `POST /api/tokens/` — `app/tokens/router.py:create_token`
- `DELETE /api/tokens/{id}` — `app/tokens/router.py:revoke_token`
- `POST /log/tokens/create` — `app/qso/ui_router.py:tokens_create`
- `DELETE /log/tokens/{id}` — `app/qso/ui_router.py:tokens_revoke`

All four must call `token_cache.notify_refresh()`.

### Pitfall 5: `operator` and `user` Shadowing in `_handle_datagram`

**What goes wrong:** The `operator` and `user` parameters of `_handle_datagram` are
passed from `QSODatagramProtocol` (the fallback `UDP_OPERATOR` values). When resolving
via token, local variables shadow these — but if the assignment is missed, the original
`UDP_OPERATOR` identity is used instead of the token identity.

**Why it happens:** Python function parameters are mutable local bindings. After
`operator = resolved_user.callsign`, the local variable shadows the parameter correctly.
But if the code path is wrong (e.g., setting only `operator` but not `user`), profile
stamping uses the wrong User.

**How to avoid:** The token resolution block must update both `operator` and `user` in
one place. Both must come from `resolved_user`.

---

## Code Examples

Verified from codebase inspection:

### ADIF Field Extraction Pattern (from existing `_handle_datagram`)
```python
# Source: app/udp/server.py lines 65-71
record = records[0]
missing = _REQUIRED_FIELDS - set(record)
if missing:
    logger.warning(
        'UDP datagram src=%s:%s disposition=rejected reason="missing required field: %s"',
        addr[0], addr[1], sorted(missing)[0],
    )
    return
```

### Rejection Log Format (matches existing disposition log pattern)
```python
# Pattern from app/udp/server.py — extend with token rejection:
logger.warning(
    "UDP datagram src=%s:%s disposition=rejected reason=invalid-token",
    addr[0], addr[1],
)
```

### asyncio.Lock-Protected Dict Swap (from Python official docs)
```python
# Source: https://docs.python.org/3/library/asyncio-sync.html
lock = asyncio.Lock()
async with lock:
    self._cache = new_cache
```

### Fire-and-Forget Cache Reload (alternative to _dirty flag)
```python
# Source: app/udp/server.py lines 131-135 — same pattern used for datagram tasks
task = asyncio.create_task(token_cache.load())
# No strong-reference set needed here — load() is short-lived
```

### Existing `_resolve_user_from_api_key` Pattern (Phase 27, for reference only)
```python
# Source: app/auth/dependencies.py lines 128-162
# This does a per-request DB lookup — exactly what UDP cache avoids.
# DO NOT copy this pattern for UDP datagram handling.
```

### Test Pattern — Mocking the Token Cache for `_handle_datagram`
```python
# Pattern consistent with existing test_udp_pipeline.py mock approach:
from unittest.mock import AsyncMock, patch

with patch("app.udp.token_cache.token_cache") as mock_cache:
    mock_cache.resolve = AsyncMock(return_value=resolved_user)
    await _handle_datagram(datagram_with_token, addr, operator="VK2ABC", user=fallback_user)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `UDP_OPERATOR` only — single static identity | `APP_OLLOG_TOKEN` per-datagram identity resolution | Phase 28 | Multi-operator UDP setups become possible |
| asyncio.Lock required running loop at creation | asyncio.Lock safe to instantiate without running loop | Python 3.10 | Module-level singleton is safe |
| Per-request DB token lookup (Phase 27 REST path) | In-memory cache with dirty-flag invalidation (Phase 28 UDP path) | Phase 28 | Zero DB round-trips per datagram |

---

## Open Questions

1. **`notify_refresh()` vs `asyncio.create_task(token_cache.load())`**
   - What we know: Both approaches invalidate the cache after a token mutation. The
     `_dirty` flag defers the reload to the first datagram; `create_task` reloads eagerly.
   - What's unclear: Which is preferred by this codebase's style. The prior decision notes
     record this as an open question from earlier research.
   - Recommendation: Use `_dirty = True` (lazy reload). It is simpler, has no risk of
     extra in-flight tasks accumulating, and UDP volume is low enough that the one-datagram
     delay on reload is not observable. If eager reload is required, change to
     `asyncio.create_task(token_cache.load())` — a one-line swap.

2. **Cache load at startup: before or inside UDP listener start?**
   - What we know: `start_udp_listener` is called after `init_db()` in `app/main.py`
     lifespan. The cache load requires Beanie to be initialised.
   - Recommendation: Call `await token_cache.load()` inside the `if settings.udp_enabled`
     block in lifespan, after `init_db()` and before `start_udp_listener`. This ensures
     the cache is warm and scopes the load to when UDP is actually enabled.

3. **Expired tokens in cache**
   - What we know: `token_is_active()` checks `expires_at` at cache-load time. A token
     that expires after the cache is loaded will remain in the cache until the next
     `notify_refresh()` triggers a reload.
   - What's unclear: Whether this is acceptable. No explicit requirement to handle
     mid-lifetime expiry for UDP tokens.
   - Recommendation: Acceptable for Phase 28. The cache is refreshed on every create/revoke.
     A background TTL sweeper is deferred scope. Document this limitation.

---

## Sources

### Primary (HIGH confidence)
- `/Users/royco/ollog/app/udp/server.py` — current `QSODatagramProtocol` and `_handle_datagram` implementation
- `/Users/royco/ollog/app/tokens/service.py` — `hash_api_token`, `verify_api_token`, `token_is_active` — locked Phase 25/27 implementation
- `/Users/royco/ollog/app/tokens/models.py` — `ApiToken` document, `token_prefix`, `hashed_token`, `enabled`
- `/Users/royco/ollog/app/tokens/router.py` — token create/revoke REST endpoints
- `/Users/royco/ollog/app/qso/ui_router.py` — HTMX token create/revoke routes (lines 659-733)
- `/Users/royco/ollog/app/main.py` — lifespan startup sequence, UDP listener init pattern
- `/Users/royco/ollog/app/feed/manager.py` — module-level singleton pattern (`manager = ConnectionManager()`)
- `/Users/royco/ollog/app/adif/parser.py` — APP_ field preservation confirmed (line 24)
- `/Users/royco/ollog/tests/test_udp_pipeline.py` — existing test patterns for `_handle_datagram`
- https://docs.python.org/3/library/asyncio-sync.html — `asyncio.Lock` and `asyncio.Event` API, constructor behaviour in Python 3.10+

### Secondary (MEDIUM confidence)
- Python 3.12 release notes: `asyncio.Lock()` does not require running event loop (consistent with pyproject.toml `requires-python = ">=3.12"`)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, no new dependencies
- Architecture: HIGH — directly derived from existing codebase patterns (`feed/manager.py` singleton, `udp/server.py` lazy imports, `auth/dependencies.py` token resolution)
- Pitfalls: HIGH — identified from direct codebase reading, not speculation

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable stdlib + existing project code)
