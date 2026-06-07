import pytest

from app.aclog.client import _map_other_slots_to_custom_fields
from app.aclog.parser import aclog_enterevent_to_adif, update_state_from_message
from app.auth.models import CustomQSOField, User
from app.qso.custom_fields import (
    apply_custom_field_normalization,
    default_custom_qso_fields,
    normalize_custom_qso_fields,
)
from app.qso.fields import build_field_values, get_field_catalog_for_user
from app.qso.models import QSO
from app.qso.service import build_qso_dict


def _user_with_custom_fields(fields: list[CustomQSOField]) -> User:
    return User.model_construct(
        username="op",
        hashed_password="hash",
        callsign="W1AW",
        custom_qso_fields=fields,
    )


def test_default_custom_qso_fields_are_eight_disabled_slots():
    fields = default_custom_qso_fields()

    assert len(fields) == 8
    assert fields[0].label == "Other 1"
    assert fields[0].adif_name == "OTHER_1"
    assert fields[7].label == "Other 8"
    assert fields[7].adif_name == "OTHER_8"
    assert all(not field.enabled for field in fields)


def test_custom_qso_field_validation_rejects_duplicate_tags():
    with pytest.raises(ValueError, match="Duplicate custom ADIF field name"):
        normalize_custom_qso_fields([
            {"slot": 1, "label": "Park", "adif_name": "POTA_REF"},
            {"slot": 2, "label": "Park Again", "adif_name": "POTA_REF"},
        ])


def test_custom_qso_field_validation_rejects_protected_names():
    with pytest.raises(ValueError, match="Protected ADIF field name"):
        normalize_custom_qso_fields([
            {"slot": 1, "label": "Hash", "adif_name": "rowHash"},
        ])


def test_field_catalog_includes_enabled_custom_fields():
    user = _user_with_custom_fields(
        [
            CustomQSOField(
                slot=1,
                label="POTA Ref",
                adif_name="POTA_REF",
                enabled=True,
            )
        ]
    )

    catalog = get_field_catalog_for_user(user)

    assert {"key": "custom_1", "label": "POTA Ref", "adif_name": "POTA_REF", "default": False, "sortable": False} in catalog


def test_build_field_values_includes_custom_field_value():
    user = _user_with_custom_fields(
        [
            CustomQSOField(
                slot=1,
                label="POTA Ref",
                adif_name="POTA_REF",
                enabled=True,
            )
        ]
    )
    qso = QSO.model_construct(_operator="W1AW", CALL="K1ABC", POTA_REF="K-1234")

    values = build_field_values(qso, user=user)

    assert values["custom_1"] == "K-1234"


def test_build_qso_dict_uppercases_configured_custom_field():
    user = _user_with_custom_fields(
        [
            CustomQSOField(
                slot=1,
                label="POTA Ref",
                adif_name="POTA_REF",
                enabled=True,
                force_uppercase=True,
            )
        ]
    )

    qso_dict = build_qso_dict(
        {
            "CALL": "K1ABC",
            "BAND": "20m",
            "MODE": "ssb",
            "QSO_DATE": "20240601",
            "TIME_ON": "123000",
            "POTA_REF": "k-1234",
        },
        "W1AW",
        profile=user,
    )

    assert qso_dict["POTA_REF"] == "K-1234"


def test_apply_custom_field_normalization_ignores_disabled_fields():
    user = _user_with_custom_fields(
        [
            CustomQSOField(
                slot=1,
                label="POTA Ref",
                adif_name="POTA_REF",
                enabled=False,
                force_uppercase=True,
            )
        ]
    )

    result = apply_custom_field_normalization({"POTA_REF": "k-1234"}, user)

    assert result["POTA_REF"] == "k-1234"


def test_aclog_enterevent_preserves_custom_adif_like_fields():
    record = aclog_enterevent_to_adif({
        "CALL": "K1ABC",
        "BAND": "20",
        "MODE": "SSB",
        "QSO_DATE": "20240601",
        "TIME_ON": "123000",
        "POTA_REF": "K-1234",
    })

    assert record["POTA_REF"] == "K-1234"


def test_aclog_text_update_caches_other_slot_fields():
    state: dict[str, str] = {}

    update_state_from_message(
        "UPDATERESPONSE",
        {"CONTROL": "txtEntryOther1", "VALUE": "K-1234"},
        state,
    )

    assert state["OTHER_1"] == "K-1234"


def test_aclog_other_slots_map_to_user_configured_adif_tags():
    user = _user_with_custom_fields(
        [
            CustomQSOField(
                slot=1,
                label="POTA Ref",
                adif_name="POTA_REF",
                enabled=True,
            )
        ]
    )

    mapped = _map_other_slots_to_custom_fields({"CALL": "K1ABC", "OTHER_1": "K-1234"}, user)

    assert mapped["POTA_REF"] == "K-1234"
    assert "OTHER_1" not in mapped
