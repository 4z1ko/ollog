from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.internal_logs.manager import LogConnectionManager
from app.internal_logs.models import (
    ApplicationLog,
    LOG_SEVERITY,
    expires_at_for_retention,
    normalize_log_level,
)
from app.internal_logs.router import list_application_logs
from app.internal_logs.service import (
    InternalLogger,
    LogSettingsSnapshot,
    log_to_dict,
    sanitize_metadata,
    should_log,
)


class FakeApplicationLog:
    def __init__(self, **kwargs):
        self.id = None
        self.__dict__.update(kwargs)

    async def insert(self):
        return None


def test_log_level_threshold_ordering():
    assert should_log("Warn", "Info") is True
    assert should_log("Error", "Warn") is True
    assert should_log("Info", "Warn") is False
    assert normalize_log_level("debug") == "Debug"


def test_sensitive_metadata_is_masked():
    cleaned = sanitize_metadata(
        {
            "username": "admin",
            "password": "secret",
            "nested": {
                "api_key": "abc",
                "uri": "mongodb://user:pass@mongodb:27017/ollog",
            },
        }
    )

    assert cleaned["username"] == "admin"
    assert cleaned["password"] == "***"
    assert cleaned["nested"]["api_key"] == "***"
    assert cleaned["nested"]["uri"] == "mongodb://***:***@mongodb:27017/ollog"


def test_log_expiry_uses_retention_days():
    before = datetime.now(timezone.utc)
    expires_at = expires_at_for_retention(30)

    assert (expires_at - before).days in {29, 30}


@pytest.mark.asyncio
async def test_logger_saves_records_at_or_above_configured_level(monkeypatch):
    saved: list[FakeApplicationLog] = []
    broadcasts: list[dict] = []

    async def fake_insert(self):
        saved.append(self)

    async def fake_settings(*, refresh=False):
        return LogSettingsSnapshot(minimum_level="Warn", retention_days=30)

    async def fake_broadcast(payload):
        broadcasts.append(payload)

    monkeypatch.setattr("app.internal_logs.service.get_log_settings", fake_settings)
    monkeypatch.setattr("app.internal_logs.service.log_manager.broadcast", fake_broadcast)
    monkeypatch.setattr(FakeApplicationLog, "insert", fake_insert)
    monkeypatch.setattr("app.internal_logs.service.ApplicationLog", FakeApplicationLog)

    logger = InternalLogger()
    skipped = await logger.info("below threshold", source="test")
    stored = await logger.error("at threshold", source="test", metadata={"token": "abc"})

    assert skipped is None
    assert stored is saved[0]
    assert stored.level == "Error"
    assert stored.metadata == {"token": "***"}
    assert broadcasts[0]["message"] == "at threshold"


@pytest.mark.asyncio
async def test_logger_force_saves_below_configured_level(monkeypatch):
    saved: list[FakeApplicationLog] = []

    async def fake_insert(self):
        saved.append(self)

    async def fake_settings(*, refresh=False):
        return LogSettingsSnapshot(minimum_level="Fatal", retention_days=30)

    monkeypatch.setattr("app.internal_logs.service.get_log_settings", fake_settings)
    monkeypatch.setattr("app.internal_logs.service.log_manager.broadcast", AsyncMock())
    monkeypatch.setattr(FakeApplicationLog, "insert", fake_insert)
    monkeypatch.setattr("app.internal_logs.service.ApplicationLog", FakeApplicationLog)

    stored = await InternalLogger().info("settings changed", source="test", force=True)

    assert stored is saved[0]
    assert stored.level == "Info"


@pytest.mark.asyncio
async def test_log_manager_broadcast_emits_new_log_records():
    manager = LogConnectionManager()
    queue = await manager.connect()

    await manager.broadcast({"message": "live"})

    assert await queue.get() == {"message": "live"}
    manager.disconnect(queue)


@pytest.mark.asyncio
async def test_log_viewer_api_returns_paginated_results(monkeypatch):
    log = ApplicationLog.model_construct(
        id=None,
        timestamp=datetime(2026, 6, 18, tzinfo=timezone.utc),
        level="Info",
        severity=LOG_SEVERITY["Info"],
        message="QSO inserted",
        source="app.qso.service",
        event_type="qso_inserted",
        transport="HTTP",
        metadata={"call": "K1ABC"},
        expires_at=datetime(2026, 7, 18, tzinfo=timezone.utc),
    )

    async def fake_query_logs(**kwargs):
        assert kwargs["page"] == 2
        assert kwargs["page_size"] == 25
        assert kwargs["level"] == "Info"
        return [log], 51

    monkeypatch.setattr("app.internal_logs.router.query_logs", fake_query_logs)

    response = await list_application_logs(
        level="Info",
        source=None,
        search=None,
        date_from=None,
        date_to=None,
        page=2,
        page_size=25,
    )

    assert response == {
        "items": [log_to_dict(log)],
        "total": 51,
        "page": 2,
        "page_size": 25,
    }
