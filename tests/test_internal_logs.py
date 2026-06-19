from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.admin import ui_router as admin_ui_router
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
    format_log_detail,
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


def test_format_log_detail_uses_pretty_json():
    formatted = format_log_detail({"nested": {"call": "K1ABC"}, "token": "***"})

    assert formatted.startswith("{\n")
    assert '  "nested": {' in formatted
    assert '    "call": "K1ABC"' in formatted
    assert '  "token": "***"' in formatted
    assert format_log_detail({}) == ""
    assert format_log_detail(None) == ""


@pytest.mark.asyncio
async def test_admin_logs_page_builds_previous_next_context(monkeypatch):
    captured = {}
    log = ApplicationLog.model_construct(
        id=None,
        timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc),
        level="Info",
        severity=LOG_SEVERITY["Info"],
        source="app.qso",
        message="Inserted QSO",
        metadata={"CALL": "W1AW"},
        expires_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    async def fake_get_log_settings(*, refresh=False):
        return LogSettingsSnapshot()

    async def fake_query_logs(**kwargs):
        assert kwargs["level"] == "Warn"
        assert kwargs["source"] == "app.qso"
        assert kwargs["search"] == "bridge"
        assert kwargs["page"] == 2
        assert kwargs["page_size"] == 50
        return [log] * 50, 120

    def fake_template_response(request, template_name, context):
        captured["template"] = template_name
        captured["context"] = context
        return context

    monkeypatch.setattr(admin_ui_router, "get_log_settings", fake_get_log_settings)
    monkeypatch.setattr(admin_ui_router, "query_logs", fake_query_logs)
    monkeypatch.setattr(admin_ui_router.templates, "TemplateResponse", fake_template_response)
    monkeypatch.setattr(admin_ui_router.app_logger, "info", AsyncMock())

    await admin_ui_router.logs_page(
        request=object(),
        hx_request="true",
        level="Warn",
        source="app.qso",
        search="bridge",
        date_from=None,
        date_to=None,
        page=2,
        admin=SimpleNamespace(username="admin"),
    )

    assert captured["template"] == "admin/logs_table.html"
    context = captured["context"]
    assert context["has_previous"] is True
    assert context["previous_page"] == 1
    assert context["has_next"] is True
    assert context["next_page"] == 3
    assert context["start_index"] == 51
    assert context["end_index"] == 100
    assert "level=Warn" in context["previous_query"]
    assert "source=app.qso" in context["next_query"]
    assert context["logs"][0]["metadata_json"].startswith("{\n")


@pytest.mark.asyncio
async def test_admin_logs_page_marks_final_page(monkeypatch):
    captured = {}
    log = ApplicationLog.model_construct(
        id=None,
        timestamp=datetime(2026, 1, 2, tzinfo=timezone.utc),
        level="Error",
        severity=LOG_SEVERITY["Error"],
        source="app.bridge",
        message="Bridge reconnect failed",
        error={"type": "TimeoutError", "message": "timed out"},
        expires_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
    )

    async def fake_get_log_settings(*, refresh=False):
        return LogSettingsSnapshot()

    async def fake_query_logs(**kwargs):
        return [log] * 20, 120

    def fake_template_response(request, template_name, context):
        captured["context"] = context
        return context

    monkeypatch.setattr(admin_ui_router, "get_log_settings", fake_get_log_settings)
    monkeypatch.setattr(admin_ui_router, "query_logs", fake_query_logs)
    monkeypatch.setattr(admin_ui_router.templates, "TemplateResponse", fake_template_response)
    monkeypatch.setattr(admin_ui_router.app_logger, "info", AsyncMock())

    await admin_ui_router.logs_page(
        request=object(),
        hx_request="true",
        level=None,
        source=None,
        search=None,
        date_from=None,
        date_to=None,
        page=3,
        admin=SimpleNamespace(username="admin"),
    )

    context = captured["context"]
    assert context["has_previous"] is True
    assert context["has_next"] is False
    assert context["start_index"] == 101
    assert context["end_index"] == 120
    assert context["logs"][0]["error_json"].startswith("{\n")
