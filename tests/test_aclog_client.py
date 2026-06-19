import pytest
from beanie import PydanticObjectId

from app.aclog.sync import ACLOG_SYNC_COMMAND, ACLOG_USER_SETTINGS_COMMAND, sync_aclog_bridge
from app.auth.models import ACLogBridge, User
from app.aclog.client import ACLogBridgeRuntimeConfig, _handle_message


class FakeWriter:
    def __init__(self) -> None:
        self.writes: list[bytes] = []
        self.closed = False

    def write(self, data: bytes) -> None:
        self.writes.append(data)

    async def drain(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return None


class FakeReader:
    def __init__(self, payload: bytes | list[bytes]) -> None:
        self.payloads = payload if isinstance(payload, list) else [payload]

    async def readline(self) -> bytes:
        return self.payloads.pop(0) if self.payloads else b""


class CapturingAppLogger:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def info(self, message, **kwargs):
        self.calls.append({"level": "Info", "message": message, **kwargs})

    async def warn(self, message, **kwargs):
        self.calls.append({"level": "Warn", "message": message, **kwargs})

    async def error(self, message, **kwargs):
        self.calls.append({"level": "Error", "message": message, **kwargs})


def _config() -> ACLogBridgeRuntimeConfig:
    return ACLogBridgeRuntimeConfig(
        user_id=PydanticObjectId(),
        bridge_id="bridge-1",
        name="ACLog",
        host="127.0.0.1",
        port=1100,
        reconnect_seconds=5,
    )


def _user() -> User:
    return User.model_construct(
        username="profileop",
        callsign="W1AW",
        enabled=True,
        custom_qso_fields=[],
    )


def _station_user() -> User:
    return User.model_construct(
        username="profileop",
        callsign="K1OP",
        station_callsign="W1AW",
        enabled=True,
        custom_qso_fields=[],
    )


def _bridge() -> ACLogBridge:
    return ACLogBridge(
        id="bridge-1",
        name="ACLog",
        host="127.0.0.1",
        port=1100,
    )


@pytest.mark.asyncio
async def test_manual_sync_sends_list_includeall_without_value(monkeypatch):
    writer = FakeWriter()

    async def fake_open_connection(host, port):
        return FakeReader(
            [
                b"<CMD><GETUSERSETTINGSRESPONSE><CALL>W1AW</CALL></GETUSERSETTINGSRESPONSE></CMD>",
                b"<CMD><LIST></LIST></CMD>",
            ]
        ), writer

    monkeypatch.setattr("app.aclog.sync.asyncio.open_connection", fake_open_connection)
    monkeypatch.setattr("app.aclog.sync.get_user_qso_collection", lambda user: object())

    report = await sync_aclog_bridge(_user(), _bridge())

    assert report.failed is False
    assert writer.writes == [
        ACLOG_USER_SETTINGS_COMMAND.encode("utf-8"),
        ACLOG_SYNC_COMMAND.encode("utf-8"),
    ]


@pytest.mark.asyncio
async def test_manual_sync_counts_imported_duplicates_and_errors(monkeypatch):
    writer = FakeWriter()
    capture = CapturingAppLogger()
    payload = (
        "<CMD><LIST>"
        "<RECORD><CALL>K1ABC</CALL><BAND>20</BAND><MODE>SSB</MODE>"
        "<DATE>20240601</DATE><TIMEON>123000</TIMEON><OPERATOR>W1AW</OPERATOR></RECORD>"
        "<RECORD><CALL>K1DEF</CALL><BAND>40</BAND><MODE>CW</MODE>"
        "<DATE>20240601</DATE><TIMEON>124000</TIMEON><OPERATOR>W1AW</OPERATOR></RECORD>"
        "<RECORD><CALL>K1BAD</CALL><BAND>15</BAND><DATE>20240601</DATE>"
        "<TIMEON>125000</TIMEON><OPERATOR>W1AW</OPERATOR></RECORD>"
        "</LIST></CMD>"
    ).encode()
    statuses = iter(
        [
            {"status": "accepted", "id": "qso-1"},
            {"status": "duplicate", "existing_id": "qso-2"},
            {"status": "rejected", "reason": "missing required field: MODE"},
        ]
    )

    async def fake_open_connection(host, port):
        return FakeReader(
            [
                b"<CMD><GETUSERSETTINGSRESPONSE><CALL>W1AW</CALL></GETUSERSETTINGSRESPONSE></CMD>",
                payload,
            ]
        ), writer

    async def fake_ingest_qso_record(**kwargs):
        return next(statuses)

    monkeypatch.setattr("app.aclog.sync.asyncio.open_connection", fake_open_connection)
    monkeypatch.setattr("app.aclog.sync.get_user_qso_collection", lambda user: object())
    monkeypatch.setattr("app.aclog.sync.ingest_qso_record", fake_ingest_qso_record)
    monkeypatch.setattr("app.aclog.sync.app_logger", capture)

    report = await sync_aclog_bridge(_user(), _bridge())

    assert report.received == 3
    assert report.imported == 1
    assert report.skipped == 1
    assert report.errors == 1
    assert report.examples == [
        {"index": "3", "call": "K1BAD", "reason": "missing required field: MODE"}
    ]
    event_types = [call["event_type"] for call in capture.calls]
    assert event_types == [
        "bridge_sync_started",
        "bridge_sync_records_received",
        "bridge_sync_qso_processed",
        "bridge_sync_qso_processed",
        "bridge_sync_qso_skipped",
        "bridge_sync_completed",
    ]
    processed = [call for call in capture.calls if call["event_type"] == "bridge_sync_qso_processed"]
    assert [call["metadata"]["status"] for call in processed] == ["accepted", "duplicate"]
    assert all(call["transport"] == "bridge" for call in capture.calls)
    assert all(call["remote_software"] == "ACLog" for call in capture.calls)


@pytest.mark.asyncio
async def test_manual_sync_filters_missing_and_unmatched_operator_records(monkeypatch):
    writer = FakeWriter()
    capture = CapturingAppLogger()
    payload = (
        "<CMD><LIST>"
        "<RECORD><CALL>K1OK</CALL><BAND>20</BAND><MODE>SSB</MODE>"
        "<DATE>20240601</DATE><TIMEON>123000</TIMEON><OPERATOR>W1AW</OPERATOR></RECORD>"
        "<RECORD><CALL>K1DUP</CALL><BAND>40</BAND><MODE>CW</MODE>"
        "<DATE>20240601</DATE><TIMEON>124000</TIMEON><OPERATOR>W1AW</OPERATOR></RECORD>"
        "<RECORD><CALL>K1MISS</CALL><BAND>15</BAND><MODE>FT8</MODE>"
        "<DATE>20240601</DATE><TIMEON>125000</TIMEON></RECORD>"
        "<RECORD><CALL>K1OTHER</CALL><BAND>10</BAND><MODE>SSB</MODE>"
        "<DATE>20240601</DATE><TIMEON>130000</TIMEON><OPERATOR>K1ABC</OPERATOR></RECORD>"
        "</LIST></CMD>"
    ).encode()
    statuses = iter([
        {"status": "accepted", "id": "qso-1"},
        {"status": "duplicate", "existing_id": "qso-2"},
    ])
    ingested: list[dict[str, str]] = []

    async def fake_open_connection(host, port):
        return FakeReader(
            [
                b"<CMD><GETUSERSETTINGSRESPONSE><CALL></CALL></GETUSERSETTINGSRESPONSE></CMD>",
                payload,
            ]
        ), writer

    async def fake_ingest_qso_record(**kwargs):
        ingested.append(kwargs["record"])
        return next(statuses)

    monkeypatch.setattr("app.aclog.sync.asyncio.open_connection", fake_open_connection)
    monkeypatch.setattr("app.aclog.sync.get_user_qso_collection", lambda user: object())
    monkeypatch.setattr("app.aclog.sync.ingest_qso_record", fake_ingest_qso_record)
    monkeypatch.setattr("app.aclog.sync.app_logger", capture)

    report = await sync_aclog_bridge(_user(), _bridge())

    assert report.received == 4
    assert report.imported == 1
    assert report.skipped == 1
    assert report.skipped_missing_operator == 1
    assert report.skipped_unmatched_operator == 1
    assert report.errors == 0
    assert [record["CALL"] for record in ingested] == ["K1OK", "K1DUP"]
    assert report.examples == [
        {
            "index": "3",
            "call": "K1MISS",
            "reason": "missing ACLog station/operator identity",
        },
        {
            "index": "4",
            "call": "K1OTHER",
            "reason": "unmatched ACLog OPERATOR: K1ABC",
        },
    ]
    skipped = [call for call in capture.calls if call["event_type"] == "bridge_sync_qso_skipped"]
    assert [call["metadata"]["disposition"] for call in skipped] == ["missing", "unmatched"]
    assert skipped[0]["metadata"]["call"] == "K1MISS"
    assert "local_station" not in skipped[0]["metadata"]
    assert "station_call" not in skipped[0]["metadata"]


@pytest.mark.asyncio
async def test_manual_sync_routes_by_setup_call_before_operator(monkeypatch):
    writer = FakeWriter()
    payload = (
        "<CMD><LIST>"
        "<RECORD><CALL>DX1ABC</CALL><BAND>20</BAND><MODE>SSB</MODE>"
        "<DATE>20240601</DATE><TIMEON>123000</TIMEON>"
        "<OPERATOR>K1OTHER</OPERATOR></RECORD>"
        "</LIST></CMD>"
    ).encode()
    ingested: list[dict[str, str]] = []

    async def fake_open_connection(host, port):
        return FakeReader(
            [
                b"<CMD><GETUSERSETTINGSRESPONSE><CALL>W1AW</CALL><OPERATOR>K1OTHER</OPERATOR></GETUSERSETTINGSRESPONSE></CMD>",
                payload,
            ]
        ), writer

    async def fake_ingest_qso_record(**kwargs):
        ingested.append(kwargs["record"])
        return {"status": "accepted", "id": "qso-1"}

    monkeypatch.setattr("app.aclog.sync.asyncio.open_connection", fake_open_connection)
    monkeypatch.setattr("app.aclog.sync.get_user_qso_collection", lambda user: object())
    monkeypatch.setattr("app.aclog.sync.ingest_qso_record", fake_ingest_qso_record)

    report = await sync_aclog_bridge(_station_user(), _bridge())

    assert report.received == 1
    assert report.imported == 1
    assert [record["CALL"] for record in ingested] == ["DX1ABC"]


@pytest.mark.asyncio
async def test_manual_sync_timeout_reports_failure_without_importing(monkeypatch):
    imported: list[dict] = []
    capture = CapturingAppLogger()

    async def fake_open_connection(host, port):
        raise TimeoutError

    async def fake_ingest_qso_record(**kwargs):
        imported.append(kwargs["record"])
        return {"status": "accepted", "id": "qso-1"}

    monkeypatch.setattr("app.aclog.sync.asyncio.open_connection", fake_open_connection)
    monkeypatch.setattr("app.aclog.sync.ingest_qso_record", fake_ingest_qso_record)
    monkeypatch.setattr("app.aclog.sync.app_logger", capture)

    report = await sync_aclog_bridge(_user(), _bridge(), timeout=0.01)

    assert report.failed is True
    assert report.imported == 0
    assert imported == []
    assert [call["event_type"] for call in capture.calls] == [
        "bridge_sync_started",
        "bridge_sync_failed",
    ]


@pytest.mark.asyncio
async def test_handle_enterevent_requests_includeall_before_ingest(monkeypatch):
    ingested: list[dict[str, str]] = []

    async def fake_ingest(config, record, **kwargs):
        ingested.append(record)

    monkeypatch.setattr("app.aclog.client._ingest_aclog_record", fake_ingest)
    monkeypatch.setattr("app.aclog.client.ACLOG_FULL_RECORD_DELAY_SECONDS", 0)
    writer = FakeWriter()

    pending = await _handle_message(
        _config(),
        (
            "<CMD><ENTEREVENT><CALL>K1ABC</CALL><BAND>20</BAND><MODE>SSB</MODE>"
            "<QSO_DATE>20240601</QSO_DATE><TIME_ON>123000</TIME_ON></ENTEREVENT></CMD>"
        ),
        {},
        writer=writer,
    )

    assert pending is not None
    assert ingested == []
    assert writer.writes == [b"<CMD><LIST><INCLUDEALL><VALUE>5</VALUE></CMD>\r\n"]


@pytest.mark.asyncio
async def test_handle_full_record_response_ingests_enriched_record(monkeypatch):
    ingested: list[dict[str, str]] = []

    async def fake_ingest(config, record, **kwargs):
        ingested.append(record)

    monkeypatch.setattr("app.aclog.client._ingest_aclog_record", fake_ingest)
    monkeypatch.setattr("app.aclog.client.ACLOG_FULL_RECORD_DELAY_SECONDS", 0)
    config = _config()
    writer = FakeWriter()
    state = {"RST_SENT": "59"}
    pending = await _handle_message(
        config,
        (
            "<CMD><ENTEREVENT><CALL>K1ABC</CALL><BAND>20</BAND><MODE>SSB</MODE>"
            "<QSO_DATE>20240601</QSO_DATE><TIME_ON>123000</TIME_ON></ENTEREVENT></CMD>"
        ),
        state,
        writer=writer,
    )

    pending = await _handle_message(
        config,
        (
            "<CMD><LIST><RECORD><CALL>OLD1</CALL><BAND>40</BAND><MODE>CW</MODE>"
            "<DATE>20240531</DATE><TIMEON>235900</TIMEON></RECORD>"
            "<RECORD><CALL>K1ABC</CALL><BAND>20</BAND><MODE>SSB</MODE>"
            "<DATE>2024-06-01</DATE><TIMEON>12:30</TIMEON>"
            "<OPERATOR>W1AW</OPERATOR>"
            "<FREQUENCY>14.255</FREQUENCY><POTA_REF>K-1234</POTA_REF>"
            "<OTHER_1>Summit</OTHER_1></RECORD></LIST></CMD>"
        ),
        state,
        pending=pending,
    )

    assert pending is None
    assert ingested == [
        {
            "CALL": "K1ABC",
            "BAND": "20M",
            "MODE": "SSB",
            "QSO_DATE": "20240601",
            "TIME_ON": "123000",
            "OPERATOR": "W1AW",
            "FREQ": "14.255",
            "POTA_REF": "K-1234",
            "OTHER_1": "Summit",
            "RST_SENT": "59",
        }
    ]


@pytest.mark.asyncio
async def test_handle_full_record_mismatch_skips_enterevent_fallback(monkeypatch):
    ingested: list[dict[str, str]] = []

    async def fake_ingest(config, record, **kwargs):
        ingested.append(record)

    monkeypatch.setattr("app.aclog.client._ingest_aclog_record", fake_ingest)
    monkeypatch.setattr("app.aclog.client.ACLOG_FULL_RECORD_DELAY_SECONDS", 0)
    config = _config()
    pending = await _handle_message(
        config,
        (
            "<CMD><ENTEREVENT><CALL>K1ABC</CALL><BAND>20</BAND><MODE>SSB</MODE>"
            "<QSO_DATE>20240601</QSO_DATE><TIME_ON>123000</TIME_ON></ENTEREVENT></CMD>"
        ),
        {},
        writer=FakeWriter(),
    )

    pending = await _handle_message(
        config,
        (
            "<CMD><LISTRESPONSE><CALL>N0CALL</CALL><BAND>20</BAND><MODE>SSB</MODE>"
            "<QSO_DATE>20240601</QSO_DATE><TIME_ON>123000</TIME_ON>"
            "<POTA_REF>K-1234</POTA_REF></LISTRESPONSE></CMD>"
        ),
        {},
        pending=pending,
    )

    assert pending is None
    assert ingested == []


@pytest.mark.asyncio
async def test_live_bridge_ingests_only_matching_full_record_identity(monkeypatch):
    ingested: list[dict[str, str]] = []

    async def fake_user_get(user_id):
        return _user()

    async def fake_ingest_qso_record(**kwargs):
        ingested.append(kwargs["record"])
        return {"status": "accepted", "id": "qso-1"}

    monkeypatch.setattr("app.aclog.client.User.get", fake_user_get)
    monkeypatch.setattr("app.aclog.client.ingest_qso_record", fake_ingest_qso_record)
    monkeypatch.setattr("app.qso.collections.get_user_qso_collection", lambda user: object())
    monkeypatch.setattr("app.aclog.client.ACLOG_FULL_RECORD_DELAY_SECONDS", 0)
    config = _config()

    pending = await _handle_message(
        config,
        (
            "<CMD><ENTEREVENT><CALL>K1ABC</CALL><BAND>20</BAND><MODE>SSB</MODE>"
            "<QSO_DATE>20240601</QSO_DATE><TIME_ON>123000</TIME_ON></ENTEREVENT></CMD>"
        ),
        {},
        writer=FakeWriter(),
    )

    pending = await _handle_message(
        config,
        (
            "<CMD><LIST><RECORD><CALL>K1ABC</CALL><BAND>20</BAND><MODE>SSB</MODE>"
            "<DATE>20240601</DATE><TIMEON>123000</TIMEON><OPERATOR>W1AW</OPERATOR>"
            "<POTA_REF>K-1234</POTA_REF></RECORD></LIST></CMD>"
        ),
        {},
        pending=pending,
    )

    assert pending is None
    assert [record["CALL"] for record in ingested] == ["K1ABC"]
    assert ingested[0]["OPERATOR"] == "W1AW"


@pytest.mark.asyncio
async def test_live_bridge_skips_unmatched_full_record_identity(monkeypatch):
    ingested: list[dict[str, str]] = []

    async def fake_user_get(user_id):
        return _user()

    async def fake_ingest_qso_record(**kwargs):
        ingested.append(kwargs["record"])
        return {"status": "accepted", "id": "qso-1"}

    monkeypatch.setattr("app.aclog.client.User.get", fake_user_get)
    monkeypatch.setattr("app.aclog.client.ingest_qso_record", fake_ingest_qso_record)
    monkeypatch.setattr("app.qso.collections.get_user_qso_collection", lambda user: object())
    monkeypatch.setattr("app.aclog.client.ACLOG_FULL_RECORD_DELAY_SECONDS", 0)
    config = _config()

    pending = await _handle_message(
        config,
        (
            "<CMD><ENTEREVENT><CALL>K1ABC</CALL><BAND>20</BAND><MODE>SSB</MODE>"
            "<QSO_DATE>20240601</QSO_DATE><TIME_ON>123000</TIME_ON></ENTEREVENT></CMD>"
        ),
        {},
        writer=FakeWriter(),
    )

    pending = await _handle_message(
        config,
        (
            "<CMD><LIST><RECORD><CALL>K1ABC</CALL><BAND>20</BAND><MODE>SSB</MODE>"
            "<DATE>20240601</DATE><TIMEON>123000</TIMEON><OPERATOR>K1ABC</OPERATOR>"
            "<POTA_REF>K-1234</POTA_REF></RECORD></LIST></CMD>"
        ),
        {},
        pending=pending,
    )

    assert pending is None
    assert ingested == []
