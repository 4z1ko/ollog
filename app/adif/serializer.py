"""ADIF serializer — converts Python dicts to .adi format.

Pure functions — no framework dependencies. Fully testable in isolation.

CRITICAL: Field lengths use len(value.encode('utf-8')), NOT len(value).
Multi-byte UTF-8 characters (accented names, non-Latin QTH) require byte
counting to produce valid ADIF that other parsers can read correctly.
"""
from __future__ import annotations


def serialize_adi(
    records: list[dict[str, str]],
    header: str | None = None,
) -> str:
    """Serialize a list of QSO record dicts to ADIF .adi format.

    Args:
        records: List of dicts mapping UPPERCASE ADIF field names to string values.
        header: Optional header text. If provided, emitted before <EOH>.

    Returns:
        Valid ADIF string with each record terminated by <EOR>.

    Notes:
        - Fields within each record are emitted in sorted (alphabetical) order
          for deterministic, reproducible output.
        - Field length L in <FIELDNAME:L> is computed as len(value.encode('utf-8'))
          to correctly handle multi-byte UTF-8 characters.
    """
    parts: list[str] = []

    if header is not None:
        parts.append(header)
        parts.append("\n<EOH>\n\n")

    for record in records:
        for field_name in sorted(record.keys()):
            value = record[field_name]
            byte_len = len(value.encode("utf-8"))  # LOCKED: byte count, not char count
            parts.append(f"<{field_name}:{byte_len}>{value}")
        parts.append("<EOR>\n\n")

    return "".join(parts)
