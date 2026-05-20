"""ADIF tag-stream state machine parser.

Parses Amateur Data Interchange Format (ADIF) files into Python dicts.
Pure functions — no framework dependencies. Fully testable in isolation.

ADIF spec: https://adif.org/317/ADIF_317.htm
"""
from __future__ import annotations


def parse_adi(text: str) -> tuple[list[dict[str, str]], list[dict]]:
    """Parse ADIF text into a list of QSO records and a list of per-record errors.

    Args:
        text: Raw ADIF file content (already decoded as a Python str).

    Returns:
        (records, errors) where each record is a dict of UPPERCASE_FIELD: value.
        Errors are per-record dicts with 'record_index' and 'error' keys.
        A single bad record does NOT abort parsing of the rest of the file.

    Notes:
        - Field names are normalized to UPPERCASE (ADIF spec: case-insensitive).
        - APP_ and USERDEF fields are preserved verbatim.
        - Content before <EOH> is treated as the header and skipped.
        - If <EOH> is absent, the entire content is treated as records.
        - The length L in <FIELDNAME:L> is a UTF-8 byte count, not a char count.
          When extracting values, byte_length bytes are consumed from the text.
    """
    # Pre-scan: if no EOH exists, treat entire content as records (no header)
    in_header = "<EOH>" in text.upper()

    records: list[dict[str, str]] = []
    errors: list[dict] = []
    current_record: dict[str, str] = {}
    record_index = 0
    i = 0
    n = len(text)

    while i < n:
        # Scan for the next '<'
        lt = text.find("<", i)
        if lt == -1:
            break
        gt = text.find(">", lt)
        if gt == -1:
            break

        tag_content = text[lt + 1 : gt]
        i = gt + 1

        tag_upper = tag_content.upper()

        # Control tags
        if tag_upper == "EOH":
            in_header = False
            continue

        if tag_upper == "EOR":
            if not in_header and current_record:
                records.append(current_record)
                current_record = {}
            record_index += 1
            continue

        # Data tag: <FIELDNAME:LENGTH> or <FIELDNAME:LENGTH:TYPE>
        parts = tag_content.split(":")
        if len(parts) < 2:
            # Tag with no colon — not a data field, skip
            continue

        field_name = parts[0].upper()

        try:
            byte_length = int(parts[1])
        except ValueError:
            if not in_header:
                errors.append({
                    "record_index": record_index,
                    "error": f"Invalid byte length in tag: <{tag_content}>",
                })
            continue

        # Extract exactly byte_length UTF-8 bytes from the remaining text.
        # ADIF length L is a byte count. For multi-byte UTF-8 characters, we
        # must consume byte_length bytes, which may be fewer than byte_length chars.
        remaining_bytes = text[i:].encode("utf-8")
        value_bytes = remaining_bytes[:byte_length]
        try:
            value = value_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback: decode with replacement
            value = value_bytes.decode("utf-8", errors="replace")

        # Advance i by the number of characters consumed (not bytes)
        i += len(value)

        if not in_header:
            current_record[field_name] = value

    return records, errors
