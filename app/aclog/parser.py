"""Parsing helpers for N3FJP ACLog TCP API messages."""

from __future__ import annotations

import re

_TAG_RE = re.compile(r"<([A-Z0-9_]+)>(.*?)</\1>", re.DOTALL | re.IGNORECASE)

_UPDATE_CONTROL_MAP = {
    "TXTENTRYFREQUENCY": "FREQ",
    "TXTENTRYFREQ": "FREQ",
    "TXTENTRYRSTS": "RST_SENT",
    "TXTENTRYRSTR": "RST_RCVD",
    "TXTENTRYSENT": "RST_SENT",
    "TXTENTRYRECEIVED": "RST_RCVD",
}


def parse_cmd(message: str) -> tuple[str | None, dict[str, str]]:
    """Parse a single ACLog <CMD> message into command name and fields."""
    cmd_match = re.search(r"<CMD>(.*)</CMD>", message, re.DOTALL | re.IGNORECASE)
    if not cmd_match:
        return None, {}

    body = cmd_match.group(1)
    first = re.match(r"\s*<([A-Z0-9_]+)>", body, re.IGNORECASE)
    if not first:
        return None, {}

    command = first.group(1).upper()
    wrapped = re.search(
        rf"<{re.escape(command)}>(.*)</{re.escape(command)}>",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    field_body = wrapped.group(1) if wrapped else body

    fields: dict[str, str] = {}
    for key, value in _TAG_RE.findall(field_body):
        key = key.upper()
        if key == command:
            continue
        fields[key] = value
    return command, fields


def aclog_enterevent_to_adif(
    fields: dict[str, str],
    state: dict[str, str] | None = None,
) -> dict[str, str]:
    """Convert an ACLog ENTEREVENT payload to an ollog ADIF-style dict."""
    result: dict[str, str] = {}
    state = state or {}

    for source, dest in [
        ("CALL", "CALL"),
        ("MODE", "MODE"),
        ("QSO_DATE", "QSO_DATE"),
        ("TIME_ON", "TIME_ON"),
        ("COUNTRY", "COUNTRY"),
        ("DXCC", "DXCC"),
        ("CONT", "CONT"),
        ("FREQ", "FREQ"),
        ("RSTS", "RST_SENT"),
        ("RSTR", "RST_RCVD"),
        ("RST_SENT", "RST_SENT"),
        ("RST_RCVD", "RST_RCVD"),
    ]:
        value = fields.get(source)
        if value:
            result[dest] = value.strip()

    for key in ("FREQ", "RST_SENT", "RST_RCVD"):
        if key not in result and state.get(key):
            result[key] = state[key]

    band = fields.get("BAND")
    if band:
        band = band.strip().upper()
        result["BAND"] = band if band.endswith("M") or band.endswith("CM") else f"{band}M"

    return result


def update_state_from_message(
    command: str | None,
    fields: dict[str, str],
    state: dict[str, str],
) -> None:
    """Update cached bridge state from ACLog field-change messages."""
    if command == "READBMFRESPONSE":
        for key in ("BAND", "MODE", "FREQ"):
            value = fields.get(key)
            if value:
                state[key] = value.strip()
        return

    if command != "UPDATERESPONSE":
        return

    control = fields.get("CONTROL", "").strip().upper()
    value = fields.get("VALUE", "").strip()
    dest = _UPDATE_CONTROL_MAP.get(control)
    if dest is not None:
        if value:
            state[dest] = value
        else:
            state.pop(dest, None)
