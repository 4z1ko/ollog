"""Unit tests for _qso_to_view_dict() — confirms created_at key presence and type.

These tests do NOT require MongoDB — QSO objects are constructed in-memory
using model_construct() with an explicit created_at datetime value, bypassing
Beanie's collection initialization requirement while still validating the
view dict correctly includes the 'created_at' key with a datetime value.
"""
from datetime import datetime, timezone

from app.qso.models import QSO
from app.qso.ui_router import _qso_to_view_dict


def test_view_dict_contains_created_at():
    """_qso_to_view_dict() must include a 'created_at' key with a datetime value.

    Uses QSO.model_construct() with an explicit created_at to bypass Beanie's
    DB init requirement for unit testing. The key behaviour under test is that
    _qso_to_view_dict() maps qso.created_at -> result["created_at"].
    """
    now = datetime.now(timezone.utc)
    qso = QSO.model_construct(
        operator_callsign="TESTOP",
        CALL="W1AW",
        created_at=now,
    )
    result = _qso_to_view_dict(qso)

    assert "created_at" in result, "View dict must contain 'created_at' key"
    assert isinstance(result["created_at"], datetime), (
        f"'created_at' must be a datetime instance, got {type(result['created_at'])}"
    )
    assert result["created_at"] == now, (
        "'created_at' in view dict must match the value from the QSO object"
    )
