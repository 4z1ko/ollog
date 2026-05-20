"""In-memory UDP operator cache for multi-operator datagram routing.

Provides a lazy-loaded, dirty-flag cache that maps uppercase callsign strings
to User objects. The cache is loaded at startup (inside the udp_enabled block
in app/main.py) and marked dirty when any operator is created, enabled, or
disabled via the admin panel.

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


class UDPOperatorCache:
    """Singleton in-memory cache mapping uppercase callsign → User.

    Lifecycle:
    - load() is called once at app startup (inside udp_enabled block).
    - resolve(callsign) is called per-datagram to look up the operator.
    - notify_refresh() is called synchronously after any operator mutation
      (create, enable, disable) to mark the cache dirty for lazy reload.

    Thread safety: uses asyncio.Lock (single-threaded asyncio app).
    """

    def __init__(self) -> None:
        self._lock: asyncio.Lock = asyncio.Lock()
        self._cache: dict[str, "User"] = {}
        self._dirty: bool = True

    async def load(self) -> None:
        """Load all enabled operators from MongoDB into memory.

        Lazy imports are used to avoid circular imports at module level.
        Cache key is the uppercased callsign from User.callsign.
        """
        from app.auth.models import User

        users = await User.find(User.enabled == True).to_list()  # noqa: E712
        new_cache: dict[str, "User"] = {u.callsign.upper(): u for u in users}
        async with self._lock:
            self._cache = new_cache
            self._dirty = False
        logger.info("UDP operator cache loaded: %d enabled operators", len(new_cache))

    async def resolve(self, callsign: str) -> "User | None":
        """Resolve a callsign string to a User.

        If the cache is dirty, reloads from MongoDB before lookup.
        The dirty check is performed BEFORE acquiring the lock to allow
        reload without blocking concurrent datagrams.
        Callsign is uppercased before lookup — senders may use mixed case.
        """
        if self._dirty:
            await self.load()
        async with self._lock:
            return self._cache.get(callsign.upper())

    def notify_refresh(self) -> None:
        """Mark the cache dirty — triggers lazy reload on next resolve()."""
        self._dirty = True
        logger.debug("UDP operator cache marked dirty — will reload on next resolve")


operator_cache = UDPOperatorCache()
