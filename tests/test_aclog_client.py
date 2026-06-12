import pytest
from beanie import PydanticObjectId

from app.aclog.sync import ACLOG_SYNC_COMMAND, sync_aclog_bridge
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
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    async def readline(self) -> bytes:
        return self.payload


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
        return FakeReader(b"<CMD><LIST></LIST></CMD>"), writer

    monkeypatch.setattr("app.aclog.sync.asyncio.open_connection", fake_open_connection)
    monkeypatch.setattr("app.aclog.sync.get_user_qso_collection", lambda user: object())

    report = await sync_aclog_bridge(_user(), _bridge())

    assert report.failed is False
    assert writer.writes == [ACLOG_SYNC_COMMAND.encode("utf-8")]
    assert writer.writes == [b"<CMD><LIST><INCLUDEALL></CMD>\r\n"]


@pytest.mark.asyncio
async def test_manual_sync_counts_imported_duplicates_and_errors(monkeypatch):
    writer = FakeWriter()
    payload = (
        "<CMD><LIST>"
        "<RECORD><CALL>K1ABC</CALL><BAND>20</BAND><MODE>SSB</MODE>"
        "<DATE>20240601</DATE><TIMEON>123000</TIMEON></RECORD>"
        "<RECORD><CALL>K1DEF</CALL><BAND>40</BAND><MODE>CW</MODE>"
        "<DATE>20240601</DATE><TIMEON>124000</TIMEON></RECORD>"
        "<RECORD><CALL>K1BAD</CALL><BAND>15</BAND><DATE>20240601</DATE>"
        "<TIMEON>125000</TIMEON></RECORD>"
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
        return FakeReader(payload), writer

    async def fake_ingest_qso_record(**kwargs):
        return next(statuses)

    monkeypatch.setattr("app.aclog.sync.asyncio.open_connection", fake_open_connection)
    monkeypatch.setattr("app.aclog.sync.get_user_qso_collection", lambda user: object())
    monkeypatch.setattr("app.aclog.sync.ingest_qso_record", fake_ingest_qso_record)

    report = await sync_aclog_bridge(_user(), _bridge())

    assert report.received == 3
    assert report.imported == 1
    assert report.skipped == 1
    assert report.errors == 1
    assert report.examples == [
        {"index": "3", "call": "K1BAD", "reason": "missing required field: MODE"}
    ]


@pytest.mark.asyncio
async def test_manual_sync_timeout_reports_failure_without_importing(monkeypatch):
    imported: list[dict] = []

    async def fake_open_connection(host, port):
        raise TimeoutError

    async def fake_ingest_qso_record(**kwargs):
        imported.append(kwargs["record"])
        return {"status": "accepted", "id": "qso-1"}

    monkeypatch.setattr("app.aclog.sync.asyncio.open_connection", fake_open_connection)
    monkeypatch.setattr("app.aclog.sync.ingest_qso_record", fake_ingest_qso_record)

    report = await sync_aclog_bridge(_user(), _bridge(), timeout=0.01)

    assert report.failed is True
    assert report.imported == 0
    assert imported == []


@pytest.mark.asyncio
async def test_handle_enterevent_requests_includeall_before_ingest(monkeypatch):
    ingested: list[dict[str, str]] = []

    async def fake_ingest(config, record):
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

    async def fake_ingest(config, record):
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
            "FREQ": "14.255",
            "POTA_REF": "K-1234",
            "OTHER_1": "Summit",
            "RST_SENT": "59",
        }
    ]


@pytest.mark.asyncio
async def test_handle_full_record_mismatch_falls_back_to_enterevent(monkeypatch):
    ingested: list[dict[str, str]] = []

    async def fake_ingest(config, record):
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
    assert ingested == [
        {
            "CALL": "K1ABC",
            "BAND": "20M",
            "MODE": "SSB",
            "QSO_DATE": "20240601",
            "TIME_ON": "123000",
        }
    ]
