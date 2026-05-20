"""Tests for callsign prefix resolver module — PRFX-01 through PRFX-04."""

import pytest
from app.callsign.prefixes import lookup_prefix, _RANGES, _STARTS, _ITU_RAW_DATA


@pytest.mark.parametrize("callsign,expected", [
    # PRFX-01: Common DX prefixes resolve correctly
    ("W1AW", "US"),
    ("DL1ABC", "DE"),
    ("JA1YWX", "JP"),
    ("F5ABC", "FR"),
    ("G3YWX", "GB"),
    ("K1ABC", "US"),
    ("VK2ABC", "AU"),

    # PRFX-01: Overlapping sub-ranges (Eswatini vs Fiji)
    ("3DA0ABC", "SZ"),    # 3DA-3DM = Eswatini
    ("3DN1ABC", "FJ"),    # 3DN-3DZ = Fiji

    # PRFX-02: Portable/operational suffixes stripped
    ("W1AW/P", "US"),     # Portable
    ("W1AW/7", "US"),     # Area suffix
    ("W1AW/QRP", "US"),   # QRP suffix
    ("DL1ABC/M", "DE"),   # Mobile

    # PRFX-03: /MM and /AM are unresolvable
    ("G3YWX/MM", None),   # Maritime mobile
    ("G3YWX/AM", None),   # Aeronautical mobile
    ("W1AW/MM", None),
    ("DL1ABC/AM", None),

    # Prefix/callsign format (operating from foreign country)
    ("EA3/G3YWX", "ES"),  # Operating from Spain

    # PRFX-04: Non-country entities return None ISO
    ("4U1ITU", None),     # United Nations
    ("C7A", None),        # World Meteorological Organization
    ("4Y1A", None),       # ICAO

    # Edge cases
    ("UNKNOWN", None),    # Unrecognized prefix
    ("", None),           # Empty string
    ("w1aw", "US"),       # Lowercase input normalized
    ("dl1abc", "DE"),     # Lowercase input normalized
])
def test_lookup_prefix(callsign, expected):
    assert lookup_prefix(callsign) == expected


def test_itu_data_completeness():
    """ITU raw data should have ~300+ range entries."""
    assert len(_ITU_RAW_DATA) >= 300


def test_ranges_sorted():
    """Ranges must be sorted by start prefix for bisect to work."""
    for i in range(len(_STARTS) - 1):
        assert _STARTS[i] <= _STARTS[i + 1], f"Unsorted at index {i}: {_STARTS[i]} > {_STARTS[i+1]}"


def test_non_country_entities_have_none_iso():
    """Non-country ITU entities must have None ISO in the range table."""
    non_country_prefixes = ["4U", "C7", "4Y"]
    for prefix in non_country_prefixes:
        result = lookup_prefix(prefix + "1ABC")
        assert result is None, f"Expected None for {prefix}, got {result}"
