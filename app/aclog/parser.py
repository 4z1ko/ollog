"""Parsing helpers for N3FJP ACLog TCP API messages."""

from __future__ import annotations

import re

_TAG_RE = re.compile(r"<([A-Z0-9_]+)>(.*?)</\1>", re.DOTALL | re.IGNORECASE)
_CMD_RE = re.compile(r"<CMD>.*?</CMD>", re.DOTALL | re.IGNORECASE)
_ADIF_NAME_RE = re.compile(r"^[A-Z0-9_]+$")
_OTHER_CONTROL_RE = re.compile(r"^TXTENTRYOTHER([1-8])$")

_UPDATE_CONTROL_MAP = {
    "TXTENTRYFREQUENCY": "FREQ",
    "TXTENTRYFREQ": "FREQ",
    "TXTENTRYRSTS": "RST_SENT",
    "TXTENTRYRSTR": "RST_RCVD",
    "TXTENTRYSENT": "RST_SENT",
    "TXTENTRYRECEIVED": "RST_RCVD",
}

_ENTEREVENT_SKIP_FIELDS = {
    "QSOCOUNT",
    "MODETEST",
}

_FULL_RECORD_SKIP_FIELDS = {
    "COUNT",
    "ERROR",
    "INDEX",
    "MODETEST",
    "QSOCOUNT",
    "RECORD",
    "RECORDS",
    "RESULT",
    "STATUS",
}

_FULL_RECORD_COMMANDS = {
    "LIST",
    "LISTRESPONSE",
    "SEARCH",
    "SEARCHRESPONSE",
}

_FULL_RECORD_WRAPPERS = {
    "CONTACT",
    "QSO",
    "RECORD",
}

_FIELD_ALIASES = {
    "DATE": "QSO_DATE",
    "DATESTR": "QSO_DATE",
    "FREQUENCY": "FREQ",
    "RSTS": "RST_SENT",
    "RSTR": "RST_RCVD",
    "TIMEON": "TIME_ON",
    "TIMEONSTR": "TIME_ON",
    "TIME_ON_STR": "TIME_ON",
}


def parse_cmd(message: str) -> tuple[str | None, dict[str, str]]:
    """Parse a single ACLog <CMD> message into command name and fields."""
    command, field_body = _command_and_field_body(message)
    if command is None:
        return None, {}

    fields: dict[str, str] = {}
    for key, value in _extract_ordered_leaf_tags(field_body):
        key = key.upper()
        if key == command:
            continue
        fields[key] = value
    return command, fields


def iter_cmd_messages(data: str) -> list[str]:
    """Split one TCP read into individual ACLog <CMD> messages."""
    messages = [match.group(0) for match in _CMD_RE.finditer(data)]
    return messages or ([data] if data.strip() else [])


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

    for source, value in fields.items():
        key = source.strip().upper()
        if key in _ENTEREVENT_SKIP_FIELDS or key in result:
            continue
        if key in {"RSTS", "RSTR"}:
            continue
        if value and _ADIF_NAME_RE.match(key):
            result[key] = value.strip()

    for key, value in state.items():
        if key.startswith("OTHER_") and key not in result and value:
            result[key] = value

    band = _normalize_band(fields.get("BAND"))
    if band:
        result["BAND"] = band

    return result


def aclog_full_record_to_adif(fields: dict[str, str]) -> dict[str, str]:
    """Convert an ACLog INCLUDEALL full-record payload to ADIF-style fields."""
    result: dict[str, str] = {}

    for source, value in fields.items():
        key = source.strip().upper()
        if not value or key in _FULL_RECORD_SKIP_FIELDS:
            continue
        if not _ADIF_NAME_RE.match(key):
            continue

        dest = _normalize_field_name(key)
        normalized = _normalize_field_value(dest, value)
        if normalized:
            result[dest] = normalized

    band = _normalize_band(result.get("BAND"))
    if band:
        result["BAND"] = band

    return result


def aclog_full_records_from_message(message: str) -> tuple[str | None, list[dict[str, str]]]:
    """Parse one ACLog LIST/SEARCH response into one or more ADIF-style records."""
    command, field_body = _command_and_field_body(message)
    if command not in _FULL_RECORD_COMMANDS:
        return command, []

    records: list[dict[str, str]] = []
    record_bodies = [
        value
        for key, value in _TAG_RE.findall(field_body)
        if key.strip().upper() in _FULL_RECORD_WRAPPERS
    ]
    if record_bodies:
        for body in record_bodies:
            record = aclog_full_record_to_adif(dict(_extract_ordered_leaf_tags(body)))
            if record:
                records.append(record)
        return command, records

    current: dict[str, str] = {}
    for key, value in _extract_ordered_leaf_tags(field_body):
        key = key.strip().upper()
        if key == command or key in _FULL_RECORD_SKIP_FIELDS:
            continue
        dest = _normalize_field_name(key)
        if dest == "CALL" and current.get("CALL"):
            record = aclog_full_record_to_adif(current)
            if record:
                records.append(record)
            current = {}
        current[key] = value

    record = aclog_full_record_to_adif(current)
    if record:
        records.append(record)
    return command, records


def is_aclog_full_record_response(command: str | None, fields: dict[str, str]) -> bool:
    """Return True when a parsed ACLog message looks like a full QSO record."""
    if command not in _FULL_RECORD_COMMANDS:
        return False
    normalized_keys = {_normalize_field_name(key) for key in fields}
    return any(key in normalized_keys for key in ("CALL", "QSO_DATE", "TIME_ON"))


def merge_aclog_records(
    base: dict[str, str],
    full: dict[str, str] | None = None,
    state: dict[str, str] | None = None,
) -> dict[str, str]:
    """Merge live ENTEREVENT, INCLUDEALL, and cached state fields deterministically."""
    merged = {key: value for key, value in base.items() if value}

    for key, value in (full or {}).items():
        if value:
            merged[key] = value

    for key, value in (state or {}).items():
        if not value:
            continue
        if key in {"FREQ", "RST_SENT", "RST_RCVD"} or key.startswith("OTHER_"):
            merged.setdefault(key, value)

    band = _normalize_band(merged.get("BAND"))
    if band:
        merged["BAND"] = band

    return merged


def aclog_records_match(base: dict[str, str], full: dict[str, str]) -> bool:
    """Check whether an ENTEREVENT record and INCLUDEALL record describe the same QSO."""
    for key in ("CALL", "QSO_DATE", "TIME_ON"):
        left = _comparison_value(key, base.get(key))
        right = _comparison_value(key, full.get(key))
        if not left or not right:
            return False
        if left != right:
            return False

    for key in ("BAND", "MODE"):
        left = _comparison_value(key, base.get(key))
        right = _comparison_value(key, full.get(key))
        if left and right and left != right:
            return False

    return True


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

    if command == "GETUSERSETTINGSRESPONSE":
        setup_call = fields.get("CALL")
        if setup_call and setup_call.strip():
            state["ACLOG_SETUP_CALL"] = setup_call.strip()
        else:
            state.pop("ACLOG_SETUP_CALL", None)
        return

    if command != "UPDATERESPONSE":
        return

    control = fields.get("CONTROL", "").strip().upper()
    value = fields.get("VALUE", "").strip()
    dest = _UPDATE_CONTROL_MAP.get(control)
    other_match = _OTHER_CONTROL_RE.match(control)
    if dest is None and other_match is not None:
        dest = f"OTHER_{other_match.group(1)}"
    if dest is not None:
        if value:
            state[dest] = value
        else:
            state.pop(dest, None)


def _normalize_field_name(key: str) -> str:
    return _FIELD_ALIASES.get(key, key)


def _normalize_field_value(key: str, value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    if key == "QSO_DATE":
        return _normalize_date(value) or value
    if key == "TIME_ON":
        return _normalize_time(value) or value
    return value


def _normalize_band(value: str | None) -> str | None:
    if not value:
        return None
    band = value.strip().upper()
    if not band:
        return None
    return band if band.endswith("M") or band.endswith("CM") else f"{band}M"


def _comparison_value(key: str, value: str | None) -> str | None:
    if not value:
        return None
    if key == "BAND":
        return _normalize_band(value)
    if key == "QSO_DATE":
        return _normalize_date(value)
    if key == "TIME_ON":
        return _normalize_time(value)
    return value.strip().upper()


def _command_and_field_body(message: str) -> tuple[str | None, str]:
    cmd_match = re.search(r"<CMD>(.*?)</CMD>", message, re.DOTALL | re.IGNORECASE)
    if not cmd_match:
        return None, ""

    body = cmd_match.group(1)
    first = re.match(r"\s*<([A-Z0-9_]+)>", body, re.IGNORECASE)
    if not first:
        return None, ""

    command = first.group(1).upper()
    wrapped = re.search(
        rf"<{re.escape(command)}>(.*)</{re.escape(command)}>",
        body,
        re.DOTALL | re.IGNORECASE,
    )
    return command, wrapped.group(1) if wrapped else body


def _extract_ordered_leaf_tags(text: str) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    for key, value in _TAG_RE.findall(text):
        nested = _extract_ordered_leaf_tags(value)
        if nested:
            fields.extend(nested)
        else:
            fields.append((key.upper(), value))
    return fields


def _normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) == 8:
        return digits
    return None


def _normalize_time(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) == 4:
        return f"{digits}00"
    if len(digits) == 6:
        return digits
    return None
