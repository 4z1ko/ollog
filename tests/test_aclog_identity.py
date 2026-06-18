from app.aclog.identity import match_aclog_operator_identity
from app.auth.models import User


def _user(callsign: str = "W1AW") -> User:
    return User.model_construct(username="op", callsign=callsign)


def _station_user(callsign: str = "K1OP", station_callsign: str = "W1AW") -> User:
    return User.model_construct(
        username="op",
        callsign=callsign,
        station_callsign=station_callsign,
    )


def test_operator_identity_matches_normalized_user_callsign():
    result = match_aclog_operator_identity({"OPERATOR": " w1aw "}, _user())

    assert result.disposition == "matched"
    assert result.matched is True
    assert result.field == "OPERATOR"
    assert result.value == "W1AW"


def test_missing_operator_identity_returns_missing_disposition():
    result = match_aclog_operator_identity({"CALL": "K1ABC"}, _user())

    assert result.disposition == "missing"
    assert result.matched is False
    assert result.field is None
    assert result.value is None


def test_blank_operator_identity_returns_missing_disposition():
    result = match_aclog_operator_identity({"OPERATOR": "   "}, _user())

    assert result.disposition == "missing"
    assert result.matched is False


def test_unmatched_operator_identity_returns_unmatched_disposition():
    result = match_aclog_operator_identity({"OPERATOR": "K1ABC"}, _user())

    assert result.disposition == "unmatched"
    assert result.matched is False
    assert result.field == "OPERATOR"
    assert result.value == "K1ABC"


def test_mycall_identity_matches_profile_station_callsign_before_operator():
    result = match_aclog_operator_identity(
        {"CALL": "DX1ABC", "MYCALL": "w1aw", "OPERATOR": "K1OTHER"},
        _station_user(),
    )

    assert result.disposition == "matched"
    assert result.matched is True
    assert result.field == "MYCALL"
    assert result.value == "W1AW"


def test_setup_call_identity_matches_profile_station_callsign_before_operator():
    result = match_aclog_operator_identity(
        {"CALL": "DX1ABC", "OPERATOR": "K1OTHER"},
        _station_user(),
        setup_station_call=" w1aw ",
    )

    assert result.disposition == "matched"
    assert result.field == "ACLOG_SETUP_CALL"
    assert result.value == "W1AW"


def test_operator_identity_is_fallback_when_station_identity_missing():
    result = match_aclog_operator_identity({"CALL": "DX1ABC", "OPERATOR": "K1OP"}, _station_user())

    assert result.disposition == "matched"
    assert result.field == "OPERATOR"
    assert result.value == "K1OP"


def test_contacted_call_is_not_used_as_local_station_identity():
    result = match_aclog_operator_identity({"CALL": "W1AW"}, _station_user())

    assert result.disposition == "missing"
    assert result.matched is False
    assert result.field is None
    assert result.value is None


def test_unmatched_station_identity_blocks_operator_fallback():
    result = match_aclog_operator_identity(
        {"MYCALL": "N0CALL", "OPERATOR": "K1OP"},
        _station_user(),
    )

    assert result.disposition == "unmatched"
    assert result.matched is False
    assert result.field == "MYCALL"
    assert result.value == "N0CALL"
