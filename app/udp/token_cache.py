"""In-memory UDP token cache for per-datagram operator identity resolution.

Provides a lazy-loaded, dirty-flag cache that maps hashed API tokens to User
objects. The cache is loaded at startup (inside the udp_enabled block in
app/main.py) and marked dirty when any token is created or revoked.

No MongoDB round-trip occurs per datagram — the cache is consulted directly.
notify_refresh() is synchronous; the reload happens lazily on the next
resolve() call after the dirty flag is set.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.auth.models import User

logger = logging.getLogger(__name__)


class UDPTokenCache:
    """Singleton in-memory cache mapping hashed_token → User.

    Lifecycle:
    - load() is called once at app startup (inside udp_enabled block).
    - resolve(raw_token) is called per-datagram to look up the operator.
    - notify_refresh() is called synchronously after any token mutation
      (create or revoke) to mark the cache dirty for lazy reload.

    Thread safety: uses asyncio.Lock (single-threaded asyncio app).
    """

    def __init__(self) -> None:
        self._lock: asyncio.Lock = asyncio.Lock()
        self._cache: dict[str, "User"] = {}
        self._dirty: bool = True

    async def load(self) -> None:
        """Load all active, non-expired tokens from MongoDB into memory.

        Lazy imports are used to avoid circular imports at module level.
        Cache key is the stored hashed_token from ApiToken — the resolver
        calls hash_api_token(raw_token) to produce the lookup key at
        resolve time.
        """
        # Lazy imports to avoid circular imports at module level
        from app.tokens.models import ApiToken
        from app.tokens.service import token_is_active
        from app.auth.models import User

        tokens = await ApiToken.find(ApiToken.enabled == True).to_list()  # noqa: E712
        new_cache: dict[str, "User"] = {}
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
        """Resolve a raw API token to a User.

        If the cache is dirty, reloads from MongoDB before lookup.
        The dirty check is performed BEFORE acquiring the lock to allow
        reload without blocking concurrent datagrams.
        """
        # Check dirty BEFORE acquiring lock to allow reload without blocking
        if self._dirty:
            await self.load()
        from app.tokens.service import hash_api_token
        hashed = hash_api_token(raw_token)
        async with self._lock:
            return self._cache.get(hashed)

    def notify_refresh(self) -> None:
        """Mark the cache dirty — triggers lazy reload on next resolve()."""
        self._dirty = True
        logger.debug("UDP token cache marked dirty — will reload on next resolve")


token_cache = UDPTokenCache()
