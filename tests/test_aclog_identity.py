from app.aclog.identity import match_aclog_operator_identity
from app.auth.models import User


def _user(callsign: str = "W1AW") -> User:
    return User.model_construct(username="op", callsign=callsign)


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


def test_station_callsign_does_not_authorize_shared_station_record():
    result = match_aclog_operator_identity({"STATION_CALLSIGN": "W1AW"}, _user())

    assert result.disposition == "missing"
    assert result.matched is False


def test_operator_identity_takes_precedence_over_station_callsign():
    result = match_aclog_operator_identity(
        {"OPERATOR": "K1ABC", "STATION_CALLSIGN": "W1AW"},
        _user(),
    )

    assert result.disposition == "unmatched"
    assert result.field == "OPERATOR"
    assert result.value == "K1ABC"
