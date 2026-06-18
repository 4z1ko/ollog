"""ACLog record-level station/operator identity helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.auth.models import User

ACLOG_STATION_IDENTITY_FIELDS = ("MYCALL", "STATION_CALLSIGN")
ACLOG_OPERATOR_IDENTITY_FIELDS = ("OPERATOR",)
ACLOG_SETUP_CALL_FIELD = "ACLOG_SETUP_CALL"


@dataclass(frozen=True)
class ACLogOperatorIdentityResult:
    disposition: str
    expected: str
    field: str | None = None
    value: str | None = None

    @property
    def matched(self) -> bool:
        return self.disposition == "matched"


def normalize_aclog_operator_identity(value: object) -> str | None:
    """Normalize a callsign-like ACLog operator identity for comparison."""
    normalized = str(value).strip().upper() if value is not None else ""
    return normalized or None


def match_aclog_operator_identity(
    record: Mapping[str, object],
    user_or_callsign: User | str,
    *,
    setup_station_call: object | None = None,
) -> ACLogOperatorIdentityResult:
    """Compare ACLog record identity with the current ollog station/operator.

    QSO ``CALL`` is deliberately ignored here: in ACLog QSO records it is the
    contacted station, not the local station/setup callsign.
    """
    expected_operator = _expected_operator_callsign(user_or_callsign)
    expected_station_calls = _expected_station_callsigns(user_or_callsign)

    for field, raw_value in _station_identity_candidates(record, setup_station_call):
        value = normalize_aclog_operator_identity(raw_value)
        if value is None:
            continue
        if value in expected_station_calls:
            return ACLogOperatorIdentityResult(
                disposition="matched",
                expected="/".join(sorted(expected_station_calls)),
                field=field,
                value=value,
            )
        return ACLogOperatorIdentityResult(
            disposition="unmatched",
            expected="/".join(sorted(expected_station_calls)),
            field=field,
            value=value,
        )

    for field in ACLOG_OPERATOR_IDENTITY_FIELDS:
        value = normalize_aclog_operator_identity(record.get(field))
        if value is None:
            continue
        if value == expected_operator:
            return ACLogOperatorIdentityResult(
                disposition="matched",
                expected=expected_operator,
                field=field,
                value=value,
            )
        return ACLogOperatorIdentityResult(
            disposition="unmatched",
            expected=expected_operator,
            field=field,
            value=value,
        )

    return ACLogOperatorIdentityResult(disposition="missing", expected=expected_operator)


def _station_identity_candidates(
    record: Mapping[str, object],
    setup_station_call: object | None,
) -> list[tuple[str, object | None]]:
    candidates = [(field, record.get(field)) for field in ACLOG_STATION_IDENTITY_FIELDS]
    candidates.append((ACLOG_SETUP_CALL_FIELD, setup_station_call))
    return candidates


def _expected_operator_callsign(user_or_callsign: User | str) -> str:
    callsign = (
        user_or_callsign.callsign
        if isinstance(user_or_callsign, User)
        else user_or_callsign
    )
    return normalize_aclog_operator_identity(callsign) or ""


def _expected_station_callsigns(user_or_callsign: User | str) -> set[str]:
    expected = {_expected_operator_callsign(user_or_callsign)}
    if isinstance(user_or_callsign, User):
        station = normalize_aclog_operator_identity(user_or_callsign.station_callsign)
        if station:
            expected.add(station)
    return {value for value in expected if value}
