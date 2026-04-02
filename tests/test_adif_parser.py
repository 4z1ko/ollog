"""Tests for ADIF tag-stream parser."""
import pytest
from app.adif.parser import parse_adi


def test_parse_simple_record():
    text = "<CALL:4>W1AW<BAND:3>20M<MODE:3>SSB<EOR>"
    records, errors = parse_adi(text)
    assert len(records) == 1
    assert records[0]["CALL"] == "W1AW"
    assert records[0]["BAND"] == "20M"
    assert records[0]["MODE"] == "SSB"
    assert errors == []


def test_parse_multiple_records():
    text = "<CALL:4>W1AW<EOR><CALL:5>DL1AB<EOR>"
    records, errors = parse_adi(text)
    assert len(records) == 2
    assert records[0]["CALL"] == "W1AW"
    assert records[1]["CALL"] == "DL1AB"


def test_parse_skips_header():
    text = "<ADIF_VER:5>3.1.4<PROGRAMID:5>ollog<EOH><CALL:4>W1AW<EOR>"
    records, errors = parse_adi(text)
    assert len(records) == 1
    assert records[0]["CALL"] == "W1AW"
    # Header fields should NOT appear in records
    assert "ADIF_VER" not in records[0]
    assert "PROGRAMID" not in records[0]


def test_parse_missing_eoh():
    # No <EOH> — entire content treated as records
    text = "<CALL:4>W1AW<BAND:3>20M<EOR>"
    records, errors = parse_adi(text)
    assert len(records) == 1
    assert records[0]["CALL"] == "W1AW"


def test_parse_case_insensitive_fields():
    text = "<call:4>W1AW<band:3>20M<eor>"
    records, errors = parse_adi(text)
    assert len(records) == 1
    assert "CALL" in records[0]
    assert "BAND" in records[0]
    assert "call" not in records[0]


def test_parse_app_fields_preserved():
    text = "<CALL:4>W1AW<APP_MYLOGGER_SCORE:3>100<APP_MYLOGGER_MULT:1>5<EOR>"
    records, errors = parse_adi(text)
    assert len(records) == 1
    assert records[0]["APP_MYLOGGER_SCORE"] == "100"
    assert records[0]["APP_MYLOGGER_MULT"] == "5"


def test_parse_userdef_fields_preserved():
    text = "<CALL:4>W1AW<USERDEF1:4>TEST<EOR>"
    records, errors = parse_adi(text)
    assert len(records) == 1
    assert records[0]["USERDEF1"] == "TEST"


def test_parse_bad_length_continues():
    # Record with malformed length, followed by valid record
    text = "<CALL:XYZ>W1AW<EOR><CALL:5>DL1AB<EOR>"
    records, errors = parse_adi(text)
    # Bad record produces an error but parsing continues
    assert len(errors) >= 1
    # The valid record should still be parsed
    assert any(r.get("CALL") == "DL1AB" for r in records)


def test_parse_empty_input():
    records, errors = parse_adi("")
    assert records == []
    assert errors == []


def test_parse_field_with_type_indicator():
    # <FIELD:LENGTH:TYPE> — 3-part tag, type indicator ignored
    text = "<MODE:3:S>SSB<EOR>"
    records, errors = parse_adi(text)
    assert len(records) == 1
    assert records[0]["MODE"] == "SSB"
