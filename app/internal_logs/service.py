"""Reusable internal application logger."""

from __future__ import annotations

import logging
import json
import re
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from beanie.exceptions import CollectionWasNotInitialized

from app.internal_logs.manager import log_manager
from app.internal_logs.models import (
    DEFAULT_LOG_LEVEL,
    DEFAULT_RETENTION_DAYS,
    LOG_SEVERITY,
    ApplicationLog,
    ApplicationLogSettings,
    expires_at_for_retention,
    normalize_log_level,
    utcnow,
)

logger = logging.getLogger(__name__)

_SENSITIVE_KEY_RE = re.compile(
    r"(password|passwd|pwd|token|api[_-]?key|authorization|secret|credential|mongodb_uri|connection[_-]?string)",
    re.IGNORECASE,
)
_MONGO_CREDENTIAL_RE = re.compile(r"(mongodb(?:\+srv)?://)([^:@/\s]+):([^@/\s]+)@")
_MASK = "***"
_SETTINGS_KEY = "global"


@dataclass(frozen=True)
class LogSettingsSnapshot:
    minimum_level: str = DEFAULT_LOG_LEVEL
    retention_days: int = DEFAULT_RETENTION_DAYS


_settings_cache: LogSettingsSnapshot | None = None


def should_log(level: str, minimum_level: str) -> bool:
    return LOG_SEVERITY[normalize_log_level(level)] >= LOG_SEVERITY[normalize_log_level(minimum_level)]


def sanitize_log_value(value: Any) -> Any:
    """Return a log-safe copy of a metadata/error value."""
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            cleaned[key_text] = _MASK if _SENSITIVE_KEY_RE.search(key_text) else sanitize_log_value(item)
        return cleaned
    if isinstance(value, list):
        return [sanitize_log_value(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_log_value(item) for item in value]
    if isinstance(value, str):
        return _MONGO_CREDENTIAL_RE.sub(r"\1***:***@", value)
    return value


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    return sanitize_log_value(metadata or {})


def error_details(exc: BaseException | None = None, details: Any | None = None) -> dict[str, Any] | None:
    if exc is None and details is None:
        return None
    result: dict[str, Any] = {}
    if exc is not None:
        result.update(
            {
                "type": exc.__class__.__name__,
                "message": str(exc),
                "stack": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            }
        )
    if details is not None:
        result["details"] = details
    return sanitize_log_value(result)


def log_to_dict(log: ApplicationLog) -> dict[str, Any]:
    return {
        "id": str(log.id) if log.id is not None else None,
        "timestamp": log.timestamp.isoformat(),
        "level": log.level,
        "severity": log.severity,
        "message": log.message,
        "source": log.source,
        "event_type": log.event_type,
        "correlation_id": log.correlation_id,
        "qso_id": log.qso_id,
        "bridge_name": log.bridge_name,
        "remote_software": log.remote_software,
        "transport": log.transport,
        "metadata": log.metadata,
        "error": log.error,
    }


def format_log_detail(value: Any) -> str:
    """Pretty-print structured log details for compact admin display."""
    if value is None or value == {} or value == []:
        return ""
    return json.dumps(value, indent=2, sort_keys=True, default=str)


async def get_log_settings(*, refresh: bool = False) -> LogSettingsSnapshot:
    global _settings_cache
    if _settings_cache is not None and not refresh:
        return _settings_cache
    try:
        doc = await ApplicationLogSettings.find_one({"key": _SETTINGS_KEY})
    except CollectionWasNotInitialized:
        return LogSettingsSnapshot()
    except Exception as exc:
        logger.debug("internal log settings lookup failed: %s", exc)
        return LogSettingsSnapshot()

    if doc is None:
        _settings_cache = LogSettingsSnapshot()
    else:
        _settings_cache = LogSettingsSnapshot(
            minimum_level=doc.minimum_level,
            retention_days=doc.retention_days,
        )
    return _settings_cache


async def set_log_settings(
    *,
    minimum_level: str,
    retention_days: int,
    updated_by: str | None = None,
) -> ApplicationLogSettings:
    global _settings_cache
    normalized_level = normalize_log_level(minimum_level)
    if retention_days < 1 or retention_days > 3650:
        raise ValueError("retention_days must be between 1 and 3650")

    doc = await ApplicationLogSettings.find_one({"key": _SETTINGS_KEY})
    if doc is None:
        doc = ApplicationLogSettings(
            key=_SETTINGS_KEY,
            minimum_level=normalized_level,
            retention_days=retention_days,
            updated_at=utcnow(),
            updated_by=updated_by,
        )
        await doc.insert()
    else:
        doc.minimum_level = normalized_level
        doc.retention_days = retention_days
        doc.updated_at = utcnow()
        doc.updated_by = updated_by
        await doc.save()

    _settings_cache = LogSettingsSnapshot(
        minimum_level=doc.minimum_level,
        retention_days=doc.retention_days,
    )
    return doc


class InternalLogger:
    async def log(
        self,
        level: str,
        message: str,
        *,
        source: str,
        event_type: str | None = None,
        correlation_id: str | None = None,
        qso_id: str | None = None,
        bridge_name: str | None = None,
        remote_software: str | None = None,
        transport: str = "system",
        metadata: dict[str, Any] | None = None,
        exc: BaseException | None = None,
        error: dict[str, Any] | None = None,
        force: bool = False,
    ) -> ApplicationLog | None:
        """Save one internal app log if it meets the active threshold.

        This method is deliberately failure-isolated; logging failures are routed to
        normal process debug logs and never raised into application flows.
        """
        try:
            normalized_level = normalize_log_level(level)
            settings = await get_log_settings()
            if not force and not should_log(normalized_level, settings.minimum_level):
                return None

            log = ApplicationLog(
                timestamp=utcnow(),
                level=normalized_level,
                severity=LOG_SEVERITY[normalized_level],
                message=message,
                source=source,
                event_type=event_type,
                correlation_id=correlation_id,
                qso_id=qso_id,
                bridge_name=bridge_name,
                remote_software=remote_software,
                transport=transport,
                metadata=sanitize_metadata(metadata),
                error=error_details(exc, error),
                expires_at=expires_at_for_retention(settings.retention_days),
            )
            await log.insert()
            await log_manager.broadcast(log_to_dict(log))
            return log
        except CollectionWasNotInitialized:
            return None
        except Exception as exc:
            logger.debug("internal application logging failed: %s", exc)
            return None

    async def trace(self, message: str, **kwargs: Any) -> ApplicationLog | None:
        return await self.log("Trace", message, **kwargs)

    async def debug(self, message: str, **kwargs: Any) -> ApplicationLog | None:
        return await self.log("Debug", message, **kwargs)

    async def info(self, message: str, **kwargs: Any) -> ApplicationLog | None:
        return await self.log("Info", message, **kwargs)

    async def warn(self, message: str, **kwargs: Any) -> ApplicationLog | None:
        return await self.log("Warn", message, **kwargs)

    async def error(self, message: str, **kwargs: Any) -> ApplicationLog | None:
        return await self.log("Error", message, **kwargs)

    async def fatal(self, message: str, **kwargs: Any) -> ApplicationLog | None:
        return await self.log("Fatal", message, **kwargs)


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def query_logs(
    *,
    level: str | None = None,
    source: str | None = None,
    search: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[ApplicationLog], int]:
    query: dict[str, Any] = {}
    if level:
        normalized_level = normalize_log_level(level)
        query["severity"] = {"$gte": LOG_SEVERITY[normalized_level]}
    if source:
        query["source"] = {"$regex": re.escape(source), "$options": "i"}
    if start or end:
        date_query: dict[str, datetime] = {}
        if start:
            date_query["$gte"] = start
        if end:
            date_query["$lte"] = end
        query["timestamp"] = date_query
    if search:
        pattern = {"$regex": re.escape(search), "$options": "i"}
        query["$or"] = [{"message": pattern}, {"source": pattern}, {"event_type": pattern}]

    safe_page = max(1, page)
    safe_page_size = min(max(1, page_size), 200)
    total = await ApplicationLog.find(query).count()
    items = (
        await ApplicationLog.find(query)
        .sort("-timestamp")
        .skip((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .to_list()
    )
    return items, total


async def clear_application_logs() -> int:
    """Delete stored application log records and return the deleted count."""
    result = await ApplicationLog.find({}).delete_many()
    return int(getattr(result, "deleted_count", 0))


app_logger = InternalLogger()
