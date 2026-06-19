from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.auth import router as auth_router
from app.auth.models import User
from app.admin import ui_router as admin_ui_router
from app.adif import router as adif_router
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
from app.qso import service as qso_service
from app.qso import ui_router as qso_ui_router
from app.tokens import router as tokens_router


class CapturingAppLogger:
    def __init__(self):
        self.calls: list[dict] = []

    async def info(self, message, **kwargs):
        self.calls.append({"level": "Info", "message": message, **kwargs})

    async def warn(self, message, **kwargs):
        self.calls.append({"level": "Warn", "message": message, **kwargs})

    async def error(self, message, **kwargs):
        self.calls.append({"level": "Error", "message": message, **kwargs})


class FakeUploadFile:
    filename = "import.adi"
    content_type = "text/plain"

    def __init__(self, raw: bytes):
        self.raw = raw

    async def read(self):
        return self.raw


FORBIDDEN_LOG_KEYS = {
    "password",
    "token",
    "full_token",
    "hashed_token",
    "authorization",
    "cookie",
}


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


def test_admin_logs_live_insert_uses_current_table_body():
    script = Path("templates/admin/logs.html").read_text()

    assert "function currentLogTableBody()" in script
    assert "var tbody = currentLogTableBody();" in script
    assert "var tbody = document.getElementById('logs-table-body');" not in script
    assert "function parseLogEventData(data)" in script
    assert "typeof parsed === 'string' ? JSON.parse(parsed) : parsed" in script
    assert "var log = parseLogEventData(event.data);" in script
    assert "fetch('/admin/ui/logs/' + encodeURIComponent(log.id) + '/row'" in script
    assert "if (!row) row = rowHtml(log);" in script
    assert "function refreshLogsTable()" in script
    assert "htmx.ajax('GET', '/admin/ui/logs?' + logsQuery()" in script
    assert "window.setInterval(refreshLogsTable, 5000);" in script
    assert "function openDetailKeys()" in script
    assert "function restoreOpenDetails(keys)" in script
    assert "var openKeys = openDetailKeys();" in script
    assert "restoreOpenDetails(openKeys);" in script
    assert "data-detail-kind=\"metadata\"" in Path("templates/admin/log_row.html").read_text()
    assert "data-detail-kind=\"error\"" in Path("templates/admin/log_row.html").read_text()


@pytest.mark.asyncio
async def test_admin_log_row_partial_uses_shared_row_context(monkeypatch):
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

    async def fake_get(log_id):
        assert log_id == "log-id"
        return log

    def fake_template_response(request, template_name, context):
        captured["template"] = template_name
        captured["context"] = context
        return context

    monkeypatch.setattr(admin_ui_router.ApplicationLog, "get", fake_get)
    monkeypatch.setattr(admin_ui_router.templates, "TemplateResponse", fake_template_response)

    await admin_ui_router.log_row_partial(
        request=object(),
        log_id="log-id",
        _admin=SimpleNamespace(username="admin"),
    )

    assert captured["template"] == "admin/log_row.html"
    assert captured["context"]["log"]["id"] == ""
    assert captured["context"]["log"]["metadata_json"].startswith("{\n")


@pytest.mark.asyncio
async def test_adif_import_logs_completed_summary_without_payload(monkeypatch):
    capture = CapturingAppLogger()
    monkeypatch.setattr(qso_service, "app_logger", capture)

    report = await qso_service.import_qsos_from_bytes(
        b"header without records",
        "W1AW",
        collection=object(),
    )

    assert report == {
        "total_records": 0,
        "accepted": [],
        "duplicates": [],
        "errors": [],
    }
    event = capture.calls[-1]
    assert event["event_type"] == "qso_import_completed"
    assert event["source"] == "app.qso.service"
    assert event["transport"] == "HTTP"
    assert event["metadata"] == {
        "operator": "W1AW",
        "total_records": 0,
        "accepted_count": 0,
        "duplicate_count": 0,
        "error_count": 0,
    }
    assert "raw" not in event["metadata"]
    assert "records" not in event["metadata"]


@pytest.mark.asyncio
async def test_oauth_login_logs_success_and_failure_without_credentials(monkeypatch):
    capture = CapturingAppLogger()
    user = User.model_construct(
        username="op1",
        callsign="W1AW",
        role="operator",
        enabled=True,
        hashed_password="hash",
    )

    async def fake_find_one(query):
        return user

    monkeypatch.setattr(auth_router, "app_logger", capture)
    monkeypatch.setattr(auth_router.User, "find_one", fake_find_one)
    monkeypatch.setattr(auth_router, "verify_password", lambda password, hashed: password == "good")
    monkeypatch.setattr(auth_router, "create_access_token", lambda data: "jwt-secret")

    response = await auth_router.login(SimpleNamespace(username="op1", password="good"))

    assert response == {"access_token": "jwt-secret", "token_type": "bearer"}
    success = capture.calls[-1]
    assert success["event_type"] == "oauth_login_succeeded"
    assert success["metadata"] == {"username": "op1", "callsign": "W1AW", "role": "operator"}
    assert FORBIDDEN_LOG_KEYS.isdisjoint(success["metadata"])

    with pytest.raises(HTTPException):
        await auth_router.login(SimpleNamespace(username="op1", password="bad"))

    failure = capture.calls[-1]
    assert failure["event_type"] == "oauth_login_failed"
    assert failure["metadata"] == {"username": "op1", "reason": "invalid_password"}
    assert FORBIDDEN_LOG_KEYS.isdisjoint(failure["metadata"])


@pytest.mark.asyncio
async def test_rest_api_token_create_logs_safe_metadata(monkeypatch):
    capture = CapturingAppLogger()
    inserted = {}

    class FakeApiToken:
        def __init__(self, **kwargs):
            self.id = "token-id"
            self.created_at = datetime(2026, 6, 19, tzinfo=timezone.utc)
            self.enabled = True
            self.__dict__.update(kwargs)

        async def insert(self):
            inserted["doc"] = self

    user = User.model_construct(username="op1", callsign="W1AW", id="user-id")

    monkeypatch.setattr(tokens_router, "app_logger", capture)
    monkeypatch.setattr(tokens_router, "ApiToken", FakeApiToken)
    monkeypatch.setattr(tokens_router, "generate_api_token", lambda: ("ollog_plain_secret", "prefix12"))
    monkeypatch.setattr(tokens_router, "hash_api_token", lambda token: "hashed-secret")
    monkeypatch.setattr("app.udp.token_cache.token_cache.notify_refresh", lambda: None)

    response = await tokens_router.create_token(user, name="logger", expires_at=None)

    assert response.full_token == "ollog_plain_secret"
    event = capture.calls[-1]
    assert event["event_type"] == "api_token_created"
    assert event["metadata"] == {
        "username": "op1",
        "callsign": "W1AW",
        "token_id": "token-id",
        "token_name": "logger",
        "token_prefix": "prefix12",
    }
    assert FORBIDDEN_LOG_KEYS.isdisjoint(event["metadata"])
    assert "ollog_plain_secret" not in str(event)
    assert "hashed-secret" not in str(event)
    assert inserted["doc"].hashed_token == "hashed-secret"


@pytest.mark.asyncio
async def test_operator_ui_token_create_logs_safe_metadata(monkeypatch):
    capture = CapturingAppLogger()

    class FakeApiToken:
        def __init__(self, **kwargs):
            self.id = "token-id"
            self.__dict__.update(kwargs)

        async def insert(self):
            return None

    def fake_template_response(request, template_name, context):
        return {"template": template_name, "context": context}

    user = User.model_construct(username="op1", callsign="W1AW", id="user-id")

    monkeypatch.setattr(qso_ui_router, "app_logger", capture)
    monkeypatch.setattr(qso_ui_router, "ApiToken", FakeApiToken)
    monkeypatch.setattr(qso_ui_router, "generate_api_token", lambda: ("ollog_plain_secret", "prefix12"))
    monkeypatch.setattr(qso_ui_router, "hash_api_token", lambda token: "hashed-secret")
    monkeypatch.setattr(qso_ui_router.templates, "TemplateResponse", fake_template_response)
    monkeypatch.setattr("app.udp.token_cache.token_cache.notify_refresh", lambda: None)

    response = await qso_ui_router.tokens_create(object(), user, name="logger", expires_at=None)

    assert response["context"]["full_token"] == "ollog_plain_secret"
    event = capture.calls[-1]
    assert event["event_type"] == "operator_api_token_created"
    assert event["metadata"]["token_prefix"] == "prefix12"
    assert FORBIDDEN_LOG_KEYS.isdisjoint(event["metadata"])
    assert "ollog_plain_secret" not in str(event)
    assert "hashed-secret" not in str(event)


@pytest.mark.asyncio
async def test_operator_ui_import_route_logs_operation_boundary(monkeypatch):
    capture = CapturingAppLogger()
    report = {"total_records": 2, "accepted": [{"id": "qso-1"}], "duplicates": [], "errors": []}

    async def fake_import_qsos_from_bytes(raw, operator, collection=None, transport="HTTP"):
        assert raw == b"<ADIF>"
        assert operator == "W1AW"
        return report

    def fake_template_response(request, template_name, context):
        return {"template": template_name, "context": context}

    user = User.model_construct(username="op1", callsign="W1AW", id="user-id")

    monkeypatch.setattr(qso_ui_router, "app_logger", capture)
    monkeypatch.setattr(qso_ui_router, "import_qsos_from_bytes", fake_import_qsos_from_bytes)
    monkeypatch.setattr(qso_ui_router, "get_user_qso_collection", lambda user: object())
    monkeypatch.setattr(qso_ui_router.templates, "TemplateResponse", fake_template_response)

    response = await qso_ui_router.import_submit(object(), FakeUploadFile(b"<ADIF>"), user)

    assert response["template"] == "log/import_report.html"
    assert [call["event_type"] for call in capture.calls] == [
        "qso_import_started",
        "qso_import_request_completed",
    ]
    assert capture.calls[0]["source"] == "log.import"
    assert capture.calls[0]["metadata"] == {
        "operator": "W1AW",
        "filename": "import.adi",
        "content_type": "text/plain",
        "bytes": 6,
    }
    assert capture.calls[1]["metadata"] == {
        "operator": "W1AW",
        "total_records": 2,
        "accepted_count": 1,
        "duplicate_count": 0,
        "error_count": 0,
    }
    assert "raw" not in capture.calls[1]["metadata"]
    assert "records" not in capture.calls[1]["metadata"]


@pytest.mark.asyncio
async def test_api_import_route_logs_operation_boundary(monkeypatch):
    capture = CapturingAppLogger()
    report = {"total_records": 1, "accepted": [], "duplicates": [], "errors": [{"error": "bad"}]}

    async def fake_import_qsos_from_bytes(raw, operator, collection=None, transport="HTTP"):
        assert raw == b"<ADIF>"
        assert operator == "W1AW"
        return report

    user = User.model_construct(username="op1", callsign="W1AW", id="user-id")

    monkeypatch.setattr(adif_router, "app_logger", capture)
    monkeypatch.setattr(adif_router, "import_qsos_from_bytes", fake_import_qsos_from_bytes)
    monkeypatch.setattr(adif_router, "get_user_qso_collection", lambda user: object())

    response = await adif_router.import_adif(FakeUploadFile(b"<ADIF>"), user)

    assert response == report
    assert [call["event_type"] for call in capture.calls] == [
        "qso_import_started",
        "qso_import_request_completed",
    ]
    assert capture.calls[0]["source"] == "app.adif.router"
    assert capture.calls[1]["metadata"] == {
        "operator": "W1AW",
        "total_records": 1,
        "accepted_count": 0,
        "duplicate_count": 0,
        "error_count": 1,
    }
