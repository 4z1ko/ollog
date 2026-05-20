from collections.abc import AsyncIterable

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.auth.dependencies import get_current_operator_callsign_cookie
from app.feed.manager import manager

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("/station", response_class=EventSourceResponse)
async def station_feed(
    _callsign: str = Depends(get_current_operator_callsign_cookie),
) -> AsyncIterable[ServerSentEvent]:
    q = await manager.connect()
    try:
        while True:
            html = await q.get()
            yield ServerSentEvent(data=html, event="new_qso")
    finally:
        manager.disconnect(q)
