import pytest
from beanie import PydanticObjectId

from app.aclog.client import ACLogBridgeRuntimeConfig, _handle_message


class FakeWriter:
    def __init__(self) -> None:
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.writes.append(data)

    async def drain(self) -> None:
        return None


def _config() -> ACLogBridgeRuntimeConfig:
    return ACLogBridgeRuntimeConfig(
        user_id=PydanticObjectId(),
        bridge_id="bridge-1",
        name="ACLog",
        host="127.0.0.1",
        port=1100,
        reconnect_seconds=5,
    )


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
