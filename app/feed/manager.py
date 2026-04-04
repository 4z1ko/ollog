import asyncio
import logging

from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self._queues: set[asyncio.Queue] = set()

    async def connect(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.add(q)
        return q

    def disconnect(self, q: asyncio.Queue) -> None:
        self._queues.discard(q)

    async def broadcast(self, event: str) -> None:
        for q in set(self._queues):  # snapshot to avoid mutation during iteration
            await q.put(event)


manager = ConnectionManager()


async def watch_qsos(collection, mgr: ConnectionManager, templates) -> None:
    """Watch the qsos collection for inserts and broadcast rendered HTML to all SSE clients."""
    pipeline = [{"$match": {"operationType": "insert"}}]
    while True:
        try:
            async with await collection.watch(pipeline, full_document="updateLookup") as stream:
                async for change in stream:
                    doc = change.get("fullDocument", {})
                    if doc:
                        ctx = {
                            "call": doc.get("CALL", ""),
                            "band": doc.get("BAND", ""),
                            "mode": doc.get("MODE", ""),
                            "freq": doc.get("FREQ", ""),
                            "operator": doc.get("_operator", ""),
                            "qso_date_utc": doc.get("qso_date_utc"),
                        }
                        # Render HTML partial — no Request object needed
                        html = templates.get_template("log/feed_row.html").render(ctx)
                        await mgr.broadcast(html)
        except PyMongoError as e:
            logger.warning("Change stream error, reconnecting: %s", e)
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Change stream watcher cancelled")
            break
