from app.aclog.parser import (
    aclog_enterevent_to_adif,
    aclog_full_records_from_message,
    aclog_full_record_to_adif,
    aclog_records_match,
    iter_cmd_messages,
    merge_aclog_records,
    parse_cmd,
    update_state_from_message,
)


def test_parse_enterevent_message():
    message = (
        "<CMD><ENTEREVENT><QSOCOUNT>765</QSOCOUNT><CALL>LA9A</CALL>"
        "<BAND>10</BAND><MODE>CW</MODE><MODETEST>CW</MODETEST>"
        "<COUNTRY>Norway</COUNTRY><DXCC>266</DXCC><CONT>EU</CONT>"
        "<QSO_DATE>20160810</QSO_DATE><TIME_ON>144300</TIME_ON></ENTEREVENT></CMD>"
    )

    command, fields = parse_cmd(message)

    assert command == "ENTEREVENT"
    assert fields["CALL"] == "LA9A"
    assert fields["BAND"] == "10"
    assert fields["QSO_DATE"] == "20160810"


def test_aclog_enterevent_to_adif_adds_band_suffix():
    fields = {
        "CALL": "LA9A",
        "BAND": "10",
        "MODE": "CW",
        "QSO_DATE": "20160810",
        "TIME_ON": "144300",
        "COUNTRY": "Norway",
        "DXCC": "266",
        "CONT": "EU",
    }

    record = aclog_enterevent_to_adif(fields)

    assert record == {
        "CALL": "LA9A",
        "BAND": "10M",
        "MODE": "CW",
        "QSO_DATE": "20160810",
        "TIME_ON": "144300",
        "COUNTRY": "Norway",
        "DXCC": "266",
        "CONT": "EU",
    }


def test_aclog_enterevent_to_adif_uses_cached_freq_and_rst():
    fields = {
        "CALL": "LA9A",
        "BAND": "10",
        "MODE": "CW",
        "QSO_DATE": "20160810",
        "TIME_ON": "144300",
    }
    state = {
        "FREQ": "28.042",
        "RST_SENT": "599",
        "RST_RCVD": "579",
    }

    record = aclog_enterevent_to_adif(fields, state=state)

    assert record["FREQ"] == "28.042"
    assert record["RST_SENT"] == "599"
    assert record["RST_RCVD"] == "579"


def test_update_state_from_readbmf_and_text_updates():
    state: dict[str, str] = {}
    update_state_from_message(
        "READBMFRESPONSE",
        {"BAND": "40", "MODE": "SSB", "FREQ": "7.22802"},
        state,
    )
    update_state_from_message(
        "UPDATERESPONSE",
        {"CONTROL": "txtEntryRSTS", "VALUE": "59"},
        state,
    )
    update_state_from_message(
        "UPDATERESPONSE",
        {"CONTROL": "txtEntryRSTR", "VALUE": "57"},
        state,
    )

    assert state == {
        "BAND": "40",
        "MODE": "SSB",
        "FREQ": "7.22802",
        "RST_SENT": "59",
        "RST_RCVD": "57",
    }


def test_update_state_from_get_user_settings_tracks_setup_call():
    state: dict[str, str] = {}

    update_state_from_message(
        "GETUSERSETTINGSRESPONSE",
        {"CALL": " W1AW ", "OPERATOR": "K1OP"},
        state,
    )

    assert state == {"ACLOG_SETUP_CALL": "W1AW"}


def test_aclog_full_record_to_adif_preserves_includeall_fields():
    fields = {
        "CALL": "K1ABC",
        "BAND": "20",
        "MODE": "SSB",
        "QSO_DATE": "20240601",
        "TIME_ON": "123000",
        "FREQ": "14.255",
        "RSTS": "59",
        "RSTR": "57",
        "POTA_REF": "K-1234",
        "OTHER_1": "Summit",
        "EMPTY": "",
        "QSOCOUNT": "99",
    }

    record = aclog_full_record_to_adif(fields)

    assert record == {
        "CALL": "K1ABC",
        "BAND": "20M",
        "MODE": "SSB",
        "QSO_DATE": "20240601",
        "TIME_ON": "123000",
        "FREQ": "14.255",
        "RST_SENT": "59",
        "RST_RCVD": "57",
        "POTA_REF": "K-1234",
        "OTHER_1": "Summit",
    }


def test_aclog_full_records_from_nested_includeall_response():
    message = (
        "<CMD><LIST><RECORD><CALL>OLD1</CALL><BAND>40</BAND><MODE>CW</MODE>"
        "<DATE>2024-05-31</DATE><TIMEON>23:59</TIMEON></RECORD>"
        "<RECORD><CALL>K1ABC</CALL><BAND>20</BAND><MODE>SSB</MODE>"
        "<DATE>2024-06-01</DATE><TIMEON>12:30:00</TIMEON>"
        "<FREQUENCY>14.255</FREQUENCY><POTA_REF>K-1234</POTA_REF>"
        "<OTHER_2>County</OTHER_2></RECORD></LIST></CMD>"
    )

    command, records = aclog_full_records_from_message(message)

    assert command == "LIST"
    assert records == [
        {
            "CALL": "OLD1",
            "BAND": "40M",
            "MODE": "CW",
            "QSO_DATE": "20240531",
            "TIME_ON": "235900",
        },
        {
            "CALL": "K1ABC",
            "BAND": "20M",
            "MODE": "SSB",
            "QSO_DATE": "20240601",
            "TIME_ON": "123000",
            "FREQ": "14.255",
            "POTA_REF": "K-1234",
            "OTHER_2": "County",
        },
    ]


def test_aclog_full_records_from_repeated_flat_includeall_response():
    message = (
        "<CMD><LIST><CALL>OLD1</CALL><BAND>40</BAND><MODE>CW</MODE>"
        "<QSO_DATE>20240531</QSO_DATE><TIME_ON>235900</TIME_ON>"
        "<CALL>K1ABC</CALL><BAND>20</BAND><MODE>SSB</MODE>"
        "<QSO_DATE>20240601</QSO_DATE><TIME_ON>123000</TIME_ON>"
        "<STATE>MA</STATE></LIST></CMD>"
    )

    _, records = aclog_full_records_from_message(message)

    assert records[-1]["CALL"] == "K1ABC"
    assert records[-1]["STATE"] == "MA"


def test_iter_cmd_messages_splits_concatenated_tcp_payload():
    payload = (
        "<CMD><UPDATERESPONSE><CONTROL>txtEntryRSTS</CONTROL><VALUE>59</VALUE>"
        "</UPDATERESPONSE></CMD><CMD><LIST><CALL>K1ABC</CALL></LIST></CMD>"
    )

    assert iter_cmd_messages(payload) == [
        "<CMD><UPDATERESPONSE><CONTROL>txtEntryRSTS</CONTROL><VALUE>59</VALUE></UPDATERESPONSE></CMD>",
        "<CMD><LIST><CALL>K1ABC</CALL></LIST></CMD>",
    ]


def test_merge_aclog_records_prefers_full_record_and_fills_state():
    base = {
        "CALL": "K1ABC",
        "BAND": "20M",
        "MODE": "SSB",
        "QSO_DATE": "20240601",
        "TIME_ON": "123000",
        "FREQ": "14.250",
    }
    full = {"FREQ": "14.255", "POTA_REF": "K-1234"}
    state = {"RST_SENT": "59", "OTHER_1": "Summit"}

    record = merge_aclog_records(base, full=full, state=state)

    assert record["FREQ"] == "14.255"
    assert record["POTA_REF"] == "K-1234"
    assert record["RST_SENT"] == "59"
    assert record["OTHER_1"] == "Summit"


def test_aclog_records_match_normalizes_band_and_detects_mismatch():
    base = {
        "CALL": "K1ABC",
        "BAND": "20M",
        "MODE": "SSB",
        "QSO_DATE": "20240601",
        "TIME_ON": "123000",
    }
    matching_full = {
        "CALL": "k1abc",
        "BAND": "20",
        "MODE": "ssb",
        "QSO_DATE": "20240601",
        "TIME_ON": "123000",
    }
    different_full = {**matching_full, "CALL": "N0CALL"}
    incomplete_full = {key: value for key, value in matching_full.items() if key != "TIME_ON"}
    aliased_full = {
        "CALL": "K1ABC",
        "BAND": "20",
        "MODE": "SSB",
        "QSO_DATE": "2024-06-01",
        "TIME_ON": "12:30",
    }

    assert aclog_records_match(base, matching_full)
    assert aclog_records_match(base, aliased_full)
    assert not aclog_records_match(base, different_full)
    assert not aclog_records_match(base, incomplete_full)
