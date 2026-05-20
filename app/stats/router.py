"""Stats UI router — operator statistics page.

Serves the stats page at /log/stats with cookie-based JWT auth.
Mounted by app/main.py with include_in_schema=False (UI route, not REST API).
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth.dependencies import get_current_operator_callsign_cookie
from app.stats.service import get_stats

templates = Jinja2Templates(directory="templates")

stats_router = APIRouter(prefix="/log", tags=["stats-ui"])


@stats_router.get("/stats", response_class=HTMLResponse)
async def stats_page(
    request: Request,
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    """Render the operator stats page."""
    data = await get_stats(callsign)
    return templates.TemplateResponse(
        request,
        "log/stats.html",
        {**data, "callsign": callsign},
    )
