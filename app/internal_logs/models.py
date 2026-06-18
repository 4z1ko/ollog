"""MongoDB models for internal application logs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pymongo
from beanie import Document
from pydantic import Field, field_validator
from pymongo import IndexModel

LOG_LEVELS = ("Trace", "Debug", "Info", "Warn", "Error", "Fatal")
LOG_SEVERITY = {level: index for index, level in enumerate(LOG_LEVELS)}
DEFAULT_LOG_LEVEL = "Info"
DEFAULT_RETENTION_DAYS = 30


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def expires_at_for_retention(retention_days: int) -> datetime:
    return utcnow() + timedelta(days=max(1, retention_days))


def normalize_log_level(value: str | None) -> str:
    candidate = (value or DEFAULT_LOG_LEVEL).strip().lower()
    for level in LOG_LEVELS:
        if candidate == level.lower():
            return level
    raise ValueError(f"Invalid log level: {value!r}")


class ApplicationLog(Document):
    """One internal app log event stored for admin visibility."""

    timestamp: datetime = Field(default_factory=utcnow)
    level: str
    severity: int
    message: str
    source: str
    event_type: str | None = None
    correlation_id: str | None = None
    qso_id: str | None = None
    bridge_name: str | None = None
    remote_software: str | None = None
    transport: str = "system"
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None
    expires_at: datetime

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: str) -> str:
        return normalize_log_level(value)

    class Settings:
        name = "application_logs"
        indexes = [
            IndexModel([("timestamp", pymongo.DESCENDING)], name="app_logs_timestamp_idx"),
            IndexModel(
                [("level", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)],
                name="app_logs_level_timestamp_idx",
            ),
            IndexModel(
                [("severity", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)],
                name="app_logs_severity_timestamp_idx",
            ),
            IndexModel(
                [("source", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)],
                name="app_logs_source_timestamp_idx",
            ),
            IndexModel(
                [("correlation_id", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)],
                name="app_logs_correlation_timestamp_idx",
            ),
            IndexModel(
                [("expires_at", pymongo.ASCENDING)],
                name="app_logs_ttl_idx",
                expireAfterSeconds=0,
            ),
        ]


class ApplicationLogSettings(Document):
    """Singleton internal logging configuration."""

    key: str = "global"
    minimum_level: str = DEFAULT_LOG_LEVEL
    retention_days: int = DEFAULT_RETENTION_DAYS
    updated_at: datetime = Field(default_factory=utcnow)
    updated_by: str | None = None

    @field_validator("minimum_level")
    @classmethod
    def validate_minimum_level(cls, value: str) -> str:
        return normalize_log_level(value)

    @field_validator("retention_days")
    @classmethod
    def validate_retention_days(cls, value: int) -> int:
        if value < 1 or value > 3650:
            raise ValueError("retention_days must be between 1 and 3650")
        return value

    class Settings:
        name = "application_log_settings"
        indexes = [
            IndexModel(
                [("key", pymongo.ASCENDING)],
                name="app_log_settings_key_unique",
                unique=True,
            ),
        ]
