"""Parsing helpers for N3FJP ACLog TCP API messages."""

from __future__ import annotations

import re

_TAG_RE = re.compile(r"<([A-Z0-9_]+)>(.*?)</\1>", re.DOTALL | re.IGNORECASE)


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


def aclog_enterevent_to_adif(fields: dict[str, str]) -> dict[str, str]:
    """Convert an ACLog ENTEREVENT payload to an ollog ADIF-style dict."""
    result: dict[str, str] = {}

    for source, dest in [
        ("CALL", "CALL"),
        ("MODE", "MODE"),
        ("QSO_DATE", "QSO_DATE"),
        ("TIME_ON", "TIME_ON"),
        ("COUNTRY", "COUNTRY"),
        ("DXCC", "DXCC"),
        ("CONT", "CONT"),
    ]:
        value = fields.get(source)
        if value:
            result[dest] = value.strip()

    band = fields.get("BAND")
    if band:
        band = band.strip().upper()
        result["BAND"] = band if band.endswith("M") or band.endswith("CM") else f"{band}M"

    return result
