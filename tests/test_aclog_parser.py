from app.aclog.parser import aclog_enterevent_to_adif, parse_cmd


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
