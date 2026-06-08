import asyncio
import logging
from typing import Any

from fastapi.templating import Jinja2Templates
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)
_templates = Jinja2Templates(directory="templates")


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


def qso_feed_context(qso: Any) -> dict:
    """Build the existing live-feed template context from a QSO-like object."""
    extra = getattr(qso, "model_extra", None) or {}
    return {
        "call": getattr(qso, "CALL", "") or extra.get("CALL", ""),
        "band": getattr(qso, "BAND", "") or extra.get("BAND", ""),
        "mode": getattr(qso, "MODE", "") or extra.get("MODE", ""),
        "freq": extra.get("FREQ", ""),
        "operator": getattr(qso, "operator_callsign", "") or extra.get("_operator", ""),
        "qso_date_utc": getattr(qso, "qso_date_utc", None) or extra.get("qso_date_utc"),
    }


async def broadcast_qso(qso: Any, mgr: ConnectionManager = manager, templates=None) -> None:
    """Render and broadcast a live-feed row for an app-created QSO insert."""
    templates = templates or _templates
    ctx = qso_feed_context(qso)
    try:
        html = templates.get_template("log/feed_row.html").render(ctx)
        logger.debug("SSE broadcast call=%s operator=%s", ctx["call"], ctx["operator"])
        await mgr.broadcast(html)
    except Exception as exc:
        logger.error("feed_row render/broadcast failed: %s", exc)


async def watch_qsos(collection, mgr: ConnectionManager, templates) -> None:
    """Watch the qsos collection for inserts and broadcast rendered HTML to all SSE clients."""
    logger.info("watch_qsos: starting change stream watcher")
    pipeline = [{"$match": {"operationType": "insert"}}]
    while True:
        try:
            logger.info("watch_qsos: opening change stream cursor")
            async with await collection.watch(pipeline, full_document="updateLookup") as stream:
                logger.info("watch_qsos: change stream open, waiting for events")
                async for change in stream:
                    doc = change.get("fullDocument", {})
                    if not doc:
                        continue
                    try:
                        from app.qso.service import qso_from_mongo_doc

                        await broadcast_qso(qso_from_mongo_doc(doc), mgr=mgr, templates=templates)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.error("feed_row render/broadcast failed: %s", e)
                        continue
        except PyMongoError as e:
            logger.warning("Change stream error, reconnecting: %s", e)
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Change stream watcher cancelled")
            break
