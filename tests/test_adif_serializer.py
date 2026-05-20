"""Tests for ADIF serializer."""
import pytest
from app.adif.serializer import serialize_adi


def test_serialize_simple_record():
    records = [{"CALL": "W1AW", "BAND": "20M"}]
    output = serialize_adi(records)
    assert "<CALL:4>W1AW" in output
    assert "<BAND:3>20M" in output
    assert "<EOR>" in output


def test_serialize_utf8_byte_length():
    # "André" is 5 chars but 6 UTF-8 bytes (é = 2 bytes)
    name = "André"
    byte_len = len(name.encode("utf-8"))
    char_len = len(name)
    assert byte_len != char_len  # confirm test premise
    records = [{"NAME": name}]
    output = serialize_adi(records)
    # The tag must use byte length, not char length
    assert f"<NAME:{byte_len}>{name}" in output
    assert f"<NAME:{char_len}>{name}" not in output


def test_serialize_multiple_records():
    records = [{"CALL": "W1AW"}, {"CALL": "DL1AB"}]
    output = serialize_adi(records)
    assert output.count("<EOR>") == 2
    assert "W1AW" in output
    assert "DL1AB" in output


def test_serialize_with_header():
    records = [{"CALL": "W1AW"}]
    output = serialize_adi(records, header="ADIF_VER:5>3.1.4")
    assert "<EOH>" in output
    assert output.index("<EOH>") < output.index("<EOR>")


def test_serialize_deterministic_field_order():
    records = [{"MODE": "SSB", "CALL": "W1AW", "BAND": "20M"}]
    output1 = serialize_adi(records)
    output2 = serialize_adi(records)
    assert output1 == output2
    # Fields should be sorted alphabetically: BAND, CALL, MODE
    band_pos = output1.index("<BAND:")
    call_pos = output1.index("<CALL:")
    mode_pos = output1.index("<MODE:")
    assert band_pos < call_pos < mode_pos


def test_serialize_app_fields():
    records = [{"CALL": "W1AW", "APP_MYLOGGER_SCORE": "100"}]
    output = serialize_adi(records)
    assert "<APP_MYLOGGER_SCORE:3>100" in output
