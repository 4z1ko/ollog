"""Round-trip tests for ADIF parser + serializer."""
import pytest
from pathlib import Path
from app.adif.parser import parse_adi
from app.adif.serializer import serialize_adi

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_roundtrip_sample_file():
    """Parse sample.adi, serialize, parse again — record dicts must be identical."""
    original_text = (FIXTURES_DIR / "sample.adi").read_text(encoding="utf-8")
    records1, errors1 = parse_adi(original_text)
    assert len(records1) > 0, "sample.adi must contain at least one record"

    serialized = serialize_adi(records1)
    records2, errors2 = parse_adi(serialized)

    assert len(records1) == len(records2)
    for r1, r2 in zip(records1, records2):
        assert r1 == r2, f"Round-trip dict mismatch:\nOriginal: {r1}\nAfter round-trip: {r2}"


def test_roundtrip_non_ascii():
    """Records with non-ASCII values must survive round-trip via UTF-8 byte-length."""
    records_in = [
        {"CALL": "DL1AB", "NAME": "André", "QTH": "München"},
    ]
    serialized = serialize_adi(records_in)
    records_out, errors = parse_adi(serialized)

    assert len(records_out) == 1
    assert records_out[0]["NAME"] == "André"
    assert records_out[0]["QTH"] == "München"


def test_roundtrip_app_fields():
    """APP_ fields must survive round-trip without being dropped."""
    records_in = [
        {
            "CALL": "W1AW",
            "APP_MYLOGGER_SCORE": "100",
            "APP_MYLOGGER_MULT": "5",
        }
    ]
    serialized = serialize_adi(records_in)
    records_out, errors = parse_adi(serialized)

    assert len(records_out) == 1
    assert records_out[0]["APP_MYLOGGER_SCORE"] == "100"
    assert records_out[0]["APP_MYLOGGER_MULT"] == "5"
