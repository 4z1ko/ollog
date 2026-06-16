"""ACLog record-level operator identity helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.auth.models import User

ACLOG_OPERATOR_IDENTITY_FIELDS = ("OPERATOR",)


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
) -> ACLogOperatorIdentityResult:
    """Compare ACLog record identity with the current ollog operator.

    Only verified operator-like fields are authoritative. Station callsign fields are
    intentionally excluded because shared station callsigns are not operator identity.
    """
    expected = _expected_callsign(user_or_callsign)
    for field in ACLOG_OPERATOR_IDENTITY_FIELDS:
        value = normalize_aclog_operator_identity(record.get(field))
        if value is None:
            continue
        if value == expected:
            return ACLogOperatorIdentityResult(
                disposition="matched",
                expected=expected,
                field=field,
                value=value,
            )
        return ACLogOperatorIdentityResult(
            disposition="unmatched",
            expected=expected,
            field=field,
            value=value,
        )

    return ACLogOperatorIdentityResult(disposition="missing", expected=expected)


def _expected_callsign(user_or_callsign: User | str) -> str:
    callsign = (
        user_or_callsign.callsign
        if isinstance(user_or_callsign, User)
        else user_or_callsign
    )
    return normalize_aclog_operator_identity(callsign) or ""
