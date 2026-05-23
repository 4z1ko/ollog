from app.aclog.parser import aclog_enterevent_to_adif, parse_cmd, update_state_from_message


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
