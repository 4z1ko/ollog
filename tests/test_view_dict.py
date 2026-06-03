"""Unit tests for _qso_to_view_dict() — confirms created_at key presence and type.

These tests do NOT require MongoDB — QSO objects are constructed in-memory
using model_construct() with an explicit created_at datetime value, bypassing
Beanie's collection initialization requirement while still validating the
view dict correctly includes the 'created_at' key with a datetime value.
"""
from datetime import datetime, timezone

from app.qso.fields import get_configurable_column_keys, get_default_column_keys, get_field_catalog
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


def test_qso_field_catalog_defaults_and_order():
    """The log view catalog keeps the current default columns first."""
    assert get_default_column_keys() == ["date", "call", "band", "mode", "freq", "rst"]

    keys = get_configurable_column_keys()
    assert keys[:6] == get_default_column_keys()
    assert len(keys) == len(set(keys))
    assert "operator" in keys
    assert "station" in keys
    assert "tx_pwr" in keys
    assert "contest_id" in keys


def test_qso_field_catalog_excludes_internal_and_token_fields():
    """Internal Mongo fields and credential-like app tokens are not selectable."""
    keys = set(get_configurable_column_keys())
    labels = {field["label"] for field in get_field_catalog()}

    unsafe_keys = {
        "id",
        "_id",
        "revision_id",
        "_deleted",
        "_operator",
        "_created_at",
        "rowHash",
        "row_hash",
        "app_ollog_token",
    }
    assert unsafe_keys.isdisjoint(keys)
    assert "APP Ollog Token" not in labels


def test_qso_field_catalog_sortable_fields_are_current_sort_targets_only():
    """Catalog sortable metadata does not expand the backend sort surface."""
    sortable_keys = {field["key"] for field in get_field_catalog() if field["sortable"]}

    assert sortable_keys == {"date", "call", "band", "mode", "created_at"}


def test_view_dict_adds_humanized_catalog_values():
    now = datetime(2024, 6, 1, 12, 34, tzinfo=timezone.utc)
    created = datetime(2024, 6, 1, 12, 35, tzinfo=timezone.utc)
    qso = QSO.model_construct(
        _operator="TESTOP",
        CALL="W1AW",
        BAND="20M",
        MODE="FT8",
        qso_date_utc=now,
        created_at=created,
        FREQ="14.074",
        RST_SENT="59",
        RST_RCVD="57",
        STATION_CALLSIGN="W1AW/P",
        TX_PWR="100",
        COMMENT="portable",
        CONTEST_ID="FIELD-DAY",
    )

    result = _qso_to_view_dict(qso)

    assert result["fields"]["date"] == "2024-06-01 12:34 UTC"
    assert result["fields"]["created_at"] == "2024-06-01 12:35 UTC"
    assert result["fields"]["call"] == "W1AW"
    assert result["fields"]["freq"] == "14.074"
    assert result["fields"]["rst"] == "59 / 57"
    assert result["fields"]["station"] == "W1AW/P"
    assert result["fields"]["tx_pwr"] == "100"
    assert result["fields"]["comment"] == "portable"
    assert result["fields"]["contest_id"] == "FIELD-DAY"


def test_view_dict_catalog_values_are_blank_when_missing():
    qso = QSO.model_construct(
        _operator="TESTOP",
        CALL="W1AW",
        created_at=datetime(2024, 6, 1, 12, 35, tzinfo=timezone.utc),
    )

    result = _qso_to_view_dict(qso)

    assert result["fields"]["date"] == ""
    assert result["fields"]["freq"] == ""
    assert result["fields"]["rst"] == ""
    assert result["fields"]["tx_pwr"] == ""
