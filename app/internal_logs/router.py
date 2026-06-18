"""Admin API endpoints for internal application logs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth.dependencies import require_admin
from app.auth.models import User
from app.internal_logs.models import LOG_LEVELS
from app.internal_logs.service import (
    app_logger,
    get_log_settings,
    log_to_dict,
    parse_iso_datetime,
    query_logs,
    set_log_settings,
)

router = APIRouter(prefix="/admin/logs", tags=["admin-logs"])


class LogSettingsRequest(BaseModel):
    minimum_level: str = Field(description="Minimum level to store")
    retention_days: int = Field(ge=1, le=3650)


@router.get("/", dependencies=[Depends(require_admin)])
async def list_application_logs(
    level: str | None = Query(default=None),
    source: str | None = Query(default=None),
    search: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    items, total = await query_logs(
        level=level,
        source=source,
        search=search,
        start=parse_iso_datetime(date_from),
        end=parse_iso_datetime(date_to),
        page=page,
        page_size=page_size,
    )
    return {
        "items": [log_to_dict(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/settings", dependencies=[Depends(require_admin)])
async def get_application_log_settings():
    settings = await get_log_settings(refresh=True)
    return {
        "minimum_level": settings.minimum_level,
        "retention_days": settings.retention_days,
        "levels": list(LOG_LEVELS),
    }


@router.patch("/settings")
async def update_application_log_settings(
    body: LogSettingsRequest,
    admin: User = Depends(require_admin),
):
    try:
        settings = await set_log_settings(
            minimum_level=body.minimum_level,
            retention_days=body.retention_days,
            updated_by=admin.username,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await app_logger.info(
        "Application log settings updated",
        source="admin.logs",
        event_type="log_settings_updated",
        transport="admin",
        metadata={
            "minimum_level": settings.minimum_level,
            "retention_days": settings.retention_days,
            "updated_by": admin.username,
        },
        force=True,
    )
    return {
        "minimum_level": settings.minimum_level,
        "retention_days": settings.retention_days,
    }
