"""Curated QSO log-view field catalog.

The log view intentionally exposes a known allowlist of ADIF/common fields
instead of discovering arbitrary MongoDB keys from QSO documents.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.auth.models import User
from app.qso.custom_fields import enabled_custom_fields_for_user
from app.qso.models import QSO


@dataclass(frozen=True)
class QSOField:
    key: str
    label: str
    adif_name: str | None = None
    default: bool = False
    sortable: bool = False


DEFAULT_COLUMN_KEYS: tuple[str, ...] = (
    "date",
    "call",
    "band",
    "mode",
    "freq",
    "rst",
)

QSO_FIELD_CATALOG: tuple[QSOField, ...] = (
    QSOField("date", "Date / Time UTC", default=True, sortable=True),
    QSOField("call", "Callsign", default=True, sortable=True),
    QSOField("band", "Band", default=True, sortable=True),
    QSOField("mode", "Mode", default=True, sortable=True),
    QSOField("freq", "Freq (MHz)", "FREQ", default=True),
    QSOField("rst", "RST S / R", default=True),
    QSOField("operator", "Operator", "OPERATOR"),
    QSOField("station", "Station Callsign", "STATION_CALLSIGN"),
    QSOField("qso_date", "QSO Date", "QSO_DATE"),
    QSOField("time_on", "Time On", "TIME_ON"),
    QSOField("time_off", "Time Off", "TIME_OFF"),
    QSOField("created_at", "Entry Time UTC", sortable=True),
    QSOField("rst_sent", "RST Sent", "RST_SENT"),
    QSOField("rst_rcvd", "RST Rcvd", "RST_RCVD"),
    QSOField("freq_rx", "RX Freq (MHz)", "FREQ_RX"),
    QSOField("band_rx", "RX Band", "BAND_RX"),
    QSOField("tx_pwr", "TX Power", "TX_PWR"),
    QSOField("comment", "Comment", "COMMENT"),
    QSOField("notes", "Notes", "NOTES"),
    QSOField("qth", "QTH", "QTH"),
    QSOField("gridsquare", "Grid Square", "GRIDSQUARE"),
    QSOField("my_gridsquare", "My Grid Square", "MY_GRIDSQUARE"),
    QSOField("contest_id", "Contest ID", "CONTEST_ID"),
    QSOField("srx", "SRX", "SRX"),
    QSOField("srx_string", "SRX String", "SRX_STRING"),
    QSOField("stx", "STX", "STX"),
    QSOField("stx_string", "STX String", "STX_STRING"),
    QSOField("pota_ref", "POTA Ref", "POTA_REF"),
    QSOField("my_pota_ref", "My POTA Ref", "MY_POTA_REF"),
    QSOField("sota_ref", "SOTA Ref", "SOTA_REF"),
    QSOField("my_sota_ref", "My SOTA Ref", "MY_SOTA_REF"),
    QSOField("wwff_ref", "WWFF Ref", "WWFF_REF"),
    QSOField("my_wwff_ref", "My WWFF Ref", "MY_WWFF_REF"),
    QSOField("iota", "IOTA", "IOTA"),
    QSOField("dxcc", "DXCC", "DXCC"),
    QSOField("country", "Country", "COUNTRY"),
    QSOField("cqz", "CQ Zone", "CQZ"),
    QSOField("ituz", "ITU Zone", "ITUZ"),
    QSOField("state", "State", "STATE"),
    QSOField("cnty", "County", "CNTY"),
    QSOField("qsl_rcvd", "QSL Rcvd", "QSL_RCVD"),
    QSOField("qsl_sent", "QSL Sent", "QSL_SENT"),
    QSOField("eqsl_qsl_rcvd", "eQSL Rcvd", "EQSL_QSL_RCVD"),
    QSOField("eqsl_qsl_sent", "eQSL Sent", "EQSL_QSL_SENT"),
    QSOField("lotw_qsl_rcvd", "LoTW QSL Rcvd", "LOTW_QSL_RCVD"),
    QSOField("lotw_qsl_sent", "LoTW QSL Sent", "LOTW_QSL_SENT"),
    QSOField("qsl_via", "QSL Via", "QSL_VIA"),
)


def get_field_catalog() -> list[dict[str, Any]]:
    """Return a template-friendly copy of the configured field catalog."""
    return _serialize_field_catalog(QSO_FIELD_CATALOG)


def get_field_catalog_for_user(user: User | None) -> list[dict[str, Any]]:
    """Return the configured field catalog plus enabled custom fields."""
    return _serialize_field_catalog((*QSO_FIELD_CATALOG, *custom_qso_field_catalog(user)))


def custom_qso_field_catalog(user: User | None) -> tuple[QSOField, ...]:
    return tuple(
        QSOField(
            key=f"custom_{field.slot}",
            label=field.label,
            adif_name=field.adif_name,
        )
        for field in enabled_custom_fields_for_user(user)
    )


def _serialize_field_catalog(fields: tuple[QSOField, ...]) -> list[dict[str, Any]]:
    return [
        {
            "key": field.key,
            "label": field.label,
            "adif_name": field.adif_name,
            "default": field.default,
            "sortable": field.sortable,
        }
        for field in fields
    ]


def get_default_column_keys() -> list[str]:
    return list(DEFAULT_COLUMN_KEYS)


def get_configurable_column_keys() -> list[str]:
    return [field.key for field in QSO_FIELD_CATALOG]


def get_default_column_keys_for_user(user: User | None) -> list[str]:
    return get_default_column_keys()


def get_configurable_column_keys_for_user(user: User | None) -> list[str]:
    return [field["key"] for field in get_field_catalog_for_user(user)]


def build_field_values(qso: QSO, user: User | None = None) -> dict[str, str]:
    """Build human-readable field values keyed by catalog key."""
    extra = qso.model_extra or {}
    values: dict[str, str] = {}

    for field in (*QSO_FIELD_CATALOG, *custom_qso_field_catalog(user)):
        if field.key == "date":
            values[field.key] = _format_utc(qso.qso_date_utc)
        elif field.key == "created_at":
            values[field.key] = _format_utc(qso.created_at)
        elif field.key == "call":
            values[field.key] = _display(qso.CALL)
        elif field.key == "band":
            values[field.key] = _display(qso.BAND)
        elif field.key == "mode":
            values[field.key] = _display(qso.MODE)
        elif field.key == "operator":
            values[field.key] = _display(qso.operator_callsign)
        elif field.key == "station":
            values[field.key] = _display(extra.get("STATION_CALLSIGN"))
        elif field.key == "rst":
            values[field.key] = _paired_rst(extra.get("RST_SENT"), extra.get("RST_RCVD"))
        elif field.adif_name:
            values[field.key] = _display(extra.get(field.adif_name))
        else:
            values[field.key] = ""

    return values


def _display(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _format_utc(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _paired_rst(sent: Any, received: Any) -> str:
    sent_display = _display(sent)
    received_display = _display(received)
    if not sent_display and not received_display:
        return ""
    if sent_display and received_display:
        return f"{sent_display} / {received_display}"
    return sent_display or received_display
