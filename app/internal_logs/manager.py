"""Live internal log broadcast manager."""

from __future__ import annotations

import asyncio
from typing import Any


class LogConnectionManager:
    def __init__(self) -> None:
        self._queues: set[asyncio.Queue] = set()

    async def connect(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues.add(queue)
        return queue

    def disconnect(self, queue: asyncio.Queue) -> None:
        self._queues.discard(queue)

    async def broadcast(self, event: dict[str, Any]) -> None:
        for queue in set(self._queues):
            await queue.put(event)


log_manager = LogConnectionManager()
