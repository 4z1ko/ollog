import pytest

from app.qso.ui_router import _decode_import_record, _encode_import_record
from app.qso.service import import_qsos_from_bytes


def test_import_record_token_roundtrip():
    record = {
        "CALL": "W1AW",
        "QSO_DATE": "20240115",
        "TIME_ON": "1430",
        "BAND": "20m",
        "MODE": "SSB",
    }

    token = _encode_import_record(record)

    assert _decode_import_record(token) == record


@pytest.mark.asyncio
async def test_import_duplicates_include_original_record(monkeypatch):
    record = {
        "CALL": "W1AW",
        "QSO_DATE": "20240115",
        "TIME_ON": "1430",
        "BAND": "20m",
        "MODE": "SSB",
    }
    adif = "<CALL:4>W1AW<QSO_DATE:8>20240115<TIME_ON:4>1430<BAND:3>20m<MODE:3>SSB<EOR>"

    class ExistingQSO:
        id = "existing123"

    async def fake_find_duplicate(**kwargs):
        return ExistingQSO()

    monkeypatch.setattr("app.qso.service.find_duplicate", fake_find_duplicate)

    report = await import_qsos_from_bytes(adif.encode("utf-8"), "VK2ABC")

    assert report["accepted"] == []
    assert len(report["duplicates"]) == 1
    duplicate = report["duplicates"][0]
    assert duplicate["call"] == "W1AW"
    assert duplicate["existing_id"] == "existing123"
    assert duplicate["record"] == record
