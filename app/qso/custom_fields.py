"""ACLog-style per-operator custom QSO field helpers."""
from __future__ import annotations

import re
from typing import Any, Iterable

from app.auth.models import CustomQSOField, User
from app.qso.models import QSO

ADIF_NAME_RE = re.compile(r"^[A-Z0-9_]+$")
FILL_BEHAVIORS = {"none", "previous_qso", "previous_same_call"}
PROTECTED_ADIF_NAMES = {
    "_OPERATOR",
    "_DELETED",
    "_ID",
    "ID",
    "REVISION_ID",
    "_CREATED_AT",
    "CREATED_AT",
    "QSO_DATE_UTC",
    "ROWHASH",
    "ROW_HASH",
    "APP_OLLOG_TOKEN",
}


def default_custom_qso_fields() -> list[CustomQSOField]:
    """Return the eight default ACLog-style custom field slots."""
    return [
        CustomQSOField(
            slot=slot,
            label=f"Other {slot}",
            adif_name=f"OTHER_{slot}",
            enabled=False,
            fill_behavior="none",
            force_uppercase=False,
        )
        for slot in range(1, 9)
    ]


def normalize_custom_qso_fields(fields: Iterable[Any] | None) -> list[CustomQSOField]:
    """Validate and normalize a submitted custom field configuration."""
    by_slot: dict[int, CustomQSOField] = {
        field.slot: field for field in default_custom_qso_fields()
    }

    for item in fields or []:
        field = item if isinstance(item, CustomQSOField) else CustomQSOField(**item)
        slot = int(field.slot)
        if slot < 1 or slot > 8:
            raise ValueError("Custom QSO field slot must be between 1 and 8")

        label = field.label.strip() or f"Other {slot}"
        adif_name = field.adif_name.strip().upper()
        if not adif_name:
            adif_name = f"OTHER_{slot}"
        if not ADIF_NAME_RE.match(adif_name):
            raise ValueError(f"Invalid ADIF field name: {field.adif_name!r}")
        if adif_name in PROTECTED_ADIF_NAMES:
            raise ValueError(f"Protected ADIF field name cannot be used: {adif_name}")
        if field.fill_behavior not in FILL_BEHAVIORS:
            raise ValueError(f"Invalid custom field fill behavior: {field.fill_behavior!r}")

        by_slot[slot] = CustomQSOField(
            slot=slot,
            label=label,
            adif_name=adif_name,
            enabled=bool(field.enabled),
            fill_behavior=field.fill_behavior,
            force_uppercase=bool(field.force_uppercase),
        )

    names = [field.adif_name for field in by_slot.values()]
    duplicates = {name for name in names if names.count(name) > 1}
    if duplicates:
        raise ValueError(f"Duplicate custom ADIF field name: {sorted(duplicates)[0]}")

    return [by_slot[slot] for slot in range(1, 9)]


def custom_fields_for_user(user: User | None) -> list[CustomQSOField]:
    return normalize_custom_qso_fields(user.custom_qso_fields if user else None)


def enabled_custom_fields_for_user(user: User | None) -> list[CustomQSOField]:
    return [field for field in custom_fields_for_user(user) if field.enabled]


def apply_custom_field_normalization(record: dict[str, Any], user: User | None) -> dict[str, Any]:
    """Apply configured custom-field value normalization to a QSO record/update."""
    result = dict(record)
    for field in enabled_custom_fields_for_user(user):
        if field.adif_name in result and result[field.adif_name] is not None:
            value = str(result[field.adif_name]).strip()
            result[field.adif_name] = value.upper() if field.force_uppercase else value
    return result


async def custom_field_defaults(user: User, call: str | None = None) -> dict[str, str]:
    """Return configured custom field defaults for the QSO entry form."""
    defaults: dict[str, str] = {}
    for field in enabled_custom_fields_for_user(user):
        if field.fill_behavior == "previous_qso":
            qso = await QSO.find(
                {
                    "_operator": user.callsign,
                    "_deleted": False,
                    field.adif_name: {"$exists": True, "$ne": ""},
                }
            ).sort("-_created_at").first_or_none()
        elif field.fill_behavior == "previous_same_call" and call:
            qso = await QSO.find(
                {
                    "_operator": user.callsign,
                    "_deleted": False,
                    "CALL": call.strip().upper(),
                    field.adif_name: {"$exists": True, "$ne": ""},
                }
            ).sort("-_created_at").first_or_none()
        else:
            qso = None

        if qso is not None:
            value = (qso.model_extra or {}).get(field.adif_name)
            if value is not None:
                defaults[field.adif_name] = str(value)
    return defaults
