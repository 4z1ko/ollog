"""Callsign prefix resolver — maps amateur radio callsigns to ISO 3166-1 alpha-2 country codes using ITU Series Ranges data."""

import bisect
import re

# ---------------------------------------------------------------------------
# Section A: ITU name → ISO 3166-1 alpha-2 mapping
# None = non-country entity (UN, ICAO, WMO, etc.)
# ---------------------------------------------------------------------------

_ITU_NAME_TO_ISO: dict[str, str | None] = {
    "Adelie Land": None,             # French Southern Territories — no standard alpha-2 for this ITU entity; use None
    "Afghanistan": "AF",
    "Alaska": "US",                  # US state
    "Albania": "AL",
    "Algeria": "DZ",
    "American Samoa": "AS",
    "Andorra": "AD",
    "Angola": "AO",
    "Antigua and Barbuda": "AG",
    "Argentine Republic": "AR",
    "Armenia": "AM",
    "Ascension Island": "SH",        # Part of Saint Helena, Ascension and Tristan da Cunha
    "Australia": "AU",
    "Austria": "AT",
    "Azerbaijan": "AZ",
    "Azores": "PT",                  # Portugal
    "Bahamas": "BS",
    "Bahrain": "BH",
    "Bangladesh": "BD",
    "Barbados": "BB",
    "Belarus": "BY",
    "Belgium": "BE",
    "Belize": "BZ",
    "Benin": "BJ",
    "Bermuda": "BM",
    "Bhutan": "BT",
    "Bolivia": "BO",
    "Bosnia and Herzegovina": "BA",
    "Botswana": "BW",
    "Brazil": "BR",
    "British Virgin Islands": "VG",
    "Brunei Darussalam": "BN",
    "Bulgaria": "BG",
    "Burkina Faso": "BF",
    "Burundi": "BI",
    "Cabo Verde": "CV",
    "Cambodia": "KH",
    "Cameroon": "CM",
    "Canada": "CA",
    "Cayman Islands": "KY",
    "Central African Republic": "CF",
    "Chad": "TD",
    "Chile": "CL",
    "China (People's Republic of)": "CN",
    "Colombia": "CO",
    "Comoros": "KM",
    "Congo (Republic of the)": "CG",
    "Cook Islands": "CK",
    "Costa Rica": "CR",
    "Cote d'Ivoire": "CI",
    "Croatia": "HR",
    "Cuba": "CU",
    "Cyprus": "CY",
    "Czech Republic": "CZ",
    "Democratic People's Republic of Korea": "KP",
    "Democratic Republic of the Congo": "CD",
    "Denmark": "DK",
    "Djibouti": "DJ",
    "Dominica": "DM",
    "Dominican Republic": "DO",
    "East Timor": "TL",              # Timor-Leste
    "Ecuador": "EC",
    "Egypt": "EG",
    "El Salvador": "SV",
    "Equatorial Guinea": "GQ",
    "Eritrea": "ER",
    "Estonia": "EE",
    "Eswatini": "SZ",
    "Ethiopia": "ET",
    "Falkland Islands (Malvinas)": "FK",
    "Fiji": "FJ",
    "Finland": "FI",
    "France": "FR",
    "French Polynesia": "PF",
    "Gabonese Republic": "GA",
    "Gambia": "GM",
    "Georgia": "GE",
    "Germany (Federal Republic of)": "DE",
    "Ghana": "GH",
    "Greece": "GR",
    "Greenland": "GL",
    "Grenada": "GD",
    "Guam": "GU",
    "Guatemala": "GT",
    "Guinea": "GN",
    "Guinea-Bissau": "GW",
    "Guyana": "GY",
    "Haiti": "HT",
    "Hawaii": "US",                  # US state
    "Honduras": "HN",
    "Hungary": "HU",
    "Iceland": "IS",
    "India": "IN",
    "Indonesia": "ID",
    "International Civil Aviation Organization": None,  # 4Y prefix
    "Iran (Islamic Republic of)": "IR",
    "Iraq": "IQ",
    "Ireland": "IE",
    "Israel": "IL",
    "Italy": "IT",
    "Jamaica": "JM",
    "Japan": "JP",
    "Jordan": "JO",
    "Kazakhstan": "KZ",
    "Kenya": "KE",
    "Kiribati": "KI",
    "Korea (Republic of)": "KR",
    "Kosovo": "XK",                  # User-assigned code, not official ISO but universally used
    "Kuwait": "KW",
    "Kyrgyzstan": "KG",
    "Lao People's Democratic Republic": "LA",
    "Latvia": "LV",
    "Lebanon": "LB",
    "Lesotho": "LS",
    "Liberia": "LR",
    "Libya": "LY",
    "Liechtenstein": "LI",
    "Lithuania": "LT",
    "Luxembourg": "LU",
    "Madagascar": "MG",
    "Malawi": "MW",
    "Malaysia": "MY",
    "Maldives": "MV",
    "Mali": "ML",
    "Malta": "MT",
    "Marshall Islands": "MH",
    "Mauritania": "MR",
    "Mauritius": "MU",
    "Mexico": "MX",
    "Micronesia": "FM",
    "Moldova (Republic of)": "MD",
    "Monaco": "MC",
    "Mongolia": "MN",
    "Montenegro": "ME",
    "Morocco": "MA",
    "Mozambique": "MZ",
    "Myanmar": "MM",
    "Namibia": "NA",
    "Nauru": "NR",
    "Nepal": "NP",
    "Netherlands (Kingdom of the)": "NL",
    "New Zealand": "NZ",
    "Nicaragua": "NI",
    "Niger": "NE",
    "Nigeria": "NG",
    "Niue": "NU",
    "North Macedonia": "MK",
    "Norway": "NO",
    "Oman": "OM",
    "Pakistan": "PK",
    "Palau": "PW",
    "Palestine": "PS",
    "Panama": "PA",
    "Papua New Guinea": "PG",
    "Paraguay": "PY",
    "Peru": "PE",
    "Philippines": "PH",
    "Poland": "PL",
    "Portugal": "PT",
    "Puerto Rico": "PR",
    "Qatar": "QA",
    "Romania": "RO",
    "Russian Federation": "RU",
    "Rwanda": "RW",
    "Saint Kitts and Nevis": "KN",
    "Saint Lucia": "LC",
    "Saint Vincent and the Grenadines": "VC",
    "Samoa": "WS",
    "San Marino": "SM",
    "Sao Tome and Principe": "ST",
    "Saudi Arabia": "SA",
    "Senegal": "SN",
    "Serbia": "RS",
    "Seychelles": "SC",
    "Sierra Leone": "SL",
    "Singapore": "SG",
    "Slovak Republic": "SK",
    "Slovenia": "SI",
    "Solomon Islands": "SB",
    "Somalia": "SO",
    "South Africa (Republic of)": "ZA",
    "South Sudan (Republic of)": "SS",
    "Spain": "ES",
    "Sri Lanka": "LK",
    "Sudan": "SD",
    "Suriname": "SR",
    "Swaziland": "SZ",              # Legacy name — same as Eswatini
    "Sweden": "SE",
    "Switzerland": "CH",
    "Syrian Arab Republic": "SY",
    "Taiwan (China)": "TW",
    "Tajikistan": "TJ",
    "Tanzania": "TZ",
    "Thailand": "TH",
    "Togolese Republic": "TG",
    "Tonga": "TO",
    "Trinidad and Tobago": "TT",
    "Tunisia": "TN",
    "Turkey": "TR",            # Note: ISO still uses TR despite Turkiye rename
    "Turkmenistan": "TM",
    "Tuvalu": "TV",
    "Uganda": "UG",
    "Ukraine": "UA",
    "United Arab Emirates": "AE",
    "United Kingdom of Great Britain and Northern Ireland": "GB",
    "United Nations Organization": None,    # 4U prefix
    "United States of America": "US",
    "Uruguay": "UY",
    "Uzbekistan": "UZ",
    "Vanuatu": "VU",
    "Vatican City State": "VA",
    "Venezuela": "VE",
    "Viet Nam": "VN",
    "World Meteorological Organization": None,  # C7 prefix
    "Yemen": "YE",
    "Zambia": "ZM",
    "Zimbabwe": "ZW",
}

# ---------------------------------------------------------------------------
# Section B: ITU Table of International Call Sign Series (raw data)
# ---------------------------------------------------------------------------

_ITU_RAW_DATA: list[tuple[str, str]] = [
    ("AAA - ALZ", "United States of America"),
    ("AMA - AOZ", "Spain"),
    ("APA - ASZ", "Pakistan"),
    ("ATA - AWZ", "India"),
    ("AXA - AXZ", "Australia"),
    ("AYA - AZZ", "Argentine Republic"),
    ("A2A - A2Z", "Botswana"),
    ("A3A - A3Z", "Tonga"),
    ("A4A - A4Z", "Oman"),
    ("A5A - A5Z", "Bhutan"),
    ("A6A - A6Z", "United Arab Emirates"),
    ("A7A - A7Z", "Qatar"),
    ("A8A - A8Z", "Liberia"),
    ("A9A - A9Z", "Bahrain"),
    ("BAA - BZZ", "China (People's Republic of)"),
    ("CAA - CEZ", "Chile"),
    ("CFA - CKZ", "Canada"),
    ("CLA - CMZ", "Cuba"),
    ("CNA - CNZ", "Morocco"),
    ("COA - COZ", "Cuba"),
    ("CPA - CPZ", "Bolivia"),
    ("CQA - CUZ", "Portugal"),
    ("CVA - CXZ", "Uruguay"),
    ("CYA - CZZ", "Canada"),
    ("C2A - C2Z", "Nauru"),
    ("C3A - C3Z", "Andorra"),
    ("C4A - C4Z", "Cyprus"),
    ("C5A - C5Z", "Gambia"),
    ("C6A - C6Z", "Bahamas"),
    ("C7A - C7Z", "World Meteorological Organization"),
    ("C8A - C9Z", "Mozambique"),
    ("DAA - DRZ", "Germany (Federal Republic of)"),
    ("DSA - DTZ", "Korea (Republic of)"),
    ("DUA - DUZ", "Philippines"),
    ("DVA - DXZ", "Philippines"),
    ("DYA - DZZ", "Philippines"),
    ("D2A - D3Z", "Angola"),
    ("D4A - D4Z", "Cabo Verde"),
    ("D5A - D5Z", "Liberia"),
    ("D6A - D6Z", "Comoros"),
    ("D7A - D9Z", "Korea (Republic of)"),
    ("EAA - EHZ", "Spain"),
    ("EIA - EJZ", "Ireland"),
    ("EKA - EKZ", "Armenia"),
    ("ELA - ELZ", "Liberia"),
    ("EMA - EOZ", "Ukraine"),
    ("EPA - EQZ", "Iran (Islamic Republic of)"),
    ("ERA - ERZ", "Moldova (Republic of)"),
    ("ESA - ESZ", "Estonia"),
    ("ETA - ETZ", "Ethiopia"),
    ("EUA - EWZ", "Belarus"),
    ("EXA - EXZ", "Kyrgyzstan"),
    ("EYA - EYZ", "Tajikistan"),
    ("EZA - EZZ", "Turkmenistan"),
    ("E2A - E2Z", "Thailand"),
    ("E3A - E3Z", "Eritrea"),
    ("E4A - E4Z", "Palestine"),
    ("E5A - E5Z", "Cook Islands"),
    ("E6A - E6Z", "Niue"),
    ("E7A - E7Z", "Bosnia and Herzegovina"),
    ("FAA - FZZ", "France"),
    ("GAA - GZZ", "United Kingdom of Great Britain and Northern Ireland"),
    ("HAA - HAZ", "Hungary"),
    ("HBA - HBZ", "Switzerland"),
    ("HCA - HDZ", "Ecuador"),
    ("HEA - HEZ", "Switzerland"),
    ("HFA - HFZ", "Poland"),
    ("HGA - HGZ", "Hungary"),
    ("HHA - HHZ", "Haiti"),
    ("HIA - HIZ", "Dominican Republic"),
    ("HJA - HKZ", "Colombia"),
    ("HLA - HLZ", "Korea (Republic of)"),
    ("HMA - HMZ", "Democratic People's Republic of Korea"),
    ("HNA - HNZ", "Iraq"),
    ("HOA - HPZ", "Panama"),
    ("HQA - HRZ", "Honduras"),
    ("HSA - HSZ", "Thailand"),
    ("HTA - HTZ", "Nicaragua"),
    ("HUA - HUZ", "El Salvador"),
    ("HVA - HVZ", "Vatican City State"),
    ("HWA - HYZ", "France"),
    ("HZA - HZZ", "Saudi Arabia"),
    ("H2A - H2Z", "Cyprus"),
    ("H3A - H3Z", "Panama"),
    ("H4A - H4Z", "Solomon Islands"),
    ("H6A - H7Z", "Nicaragua"),
    ("H8A - H9Z", "Panama"),
    ("IAA - IZZ", "Italy"),
    ("JAA - JSZ", "Japan"),
    ("JTA - JVZ", "Mongolia"),
    ("JWA - JXZ", "Norway"),
    ("JYA - JYZ", "Jordan"),
    ("JZA - JZZ", "Indonesia"),
    ("J2A - J2Z", "Djibouti"),
    ("J3A - J3Z", "Grenada"),
    ("J4A - J4Z", "Greece"),
    ("J5A - J5Z", "Guinea-Bissau"),
    ("J6A - J6Z", "Saint Lucia"),
    ("J7A - J7Z", "Dominica"),
    ("J8A - J8Z", "Saint Vincent and the Grenadines"),
    ("KAA - KZZ", "United States of America"),
    ("LAA - LNZ", "Norway"),
    ("LOA - LWZ", "Argentine Republic"),
    ("LXA - LXZ", "Luxembourg"),
    ("LYA - LYZ", "Lithuania"),
    ("LZA - LZZ", "Bulgaria"),
    ("L2A - L9Z", "Argentine Republic"),
    ("MAA - MZZ", "United Kingdom of Great Britain and Northern Ireland"),
    ("NAA - NZZ", "United States of America"),
    ("OAA - OCZ", "Peru"),
    ("ODA - ODZ", "Lebanon"),
    ("OEA - OEZ", "Austria"),
    ("OFA - OJZ", "Finland"),
    ("OKA - OLZ", "Czech Republic"),
    ("OMA - OMZ", "Slovak Republic"),
    ("ONA - OTZ", "Belgium"),
    ("OUA - OZZ", "Denmark"),
    ("PAA - PIZ", "Netherlands (Kingdom of the)"),
    ("PJA - PJZ", "Netherlands (Kingdom of the)"),
    ("PKA - POZ", "Indonesia"),
    ("PPA - PYZ", "Brazil"),
    ("PZA - PZZ", "Suriname"),
    ("P2A - P2Z", "Papua New Guinea"),
    ("P3A - P3Z", "Cyprus"),
    ("P4A - P4Z", "Netherlands (Kingdom of the)"),
    ("P5A - P9Z", "Democratic People's Republic of Korea"),
    ("RAA - RZZ", "Russian Federation"),
    ("SAA - SMZ", "Sweden"),
    ("SNA - SRZ", "Poland"),
    ("SSA - SSM", "Egypt"),
    ("SSN - STZ", "Sudan"),
    ("SUA - SUZ", "Egypt"),
    ("SVA - SZZ", "Greece"),
    ("S2A - S3Z", "Bangladesh"),
    ("S5A - S5Z", "Slovenia"),
    ("S6A - S6Z", "Singapore"),
    ("S7A - S7Z", "Seychelles"),
    ("S8A - S8Z", "South Africa (Republic of)"),
    ("S9A - S9Z", "Sao Tome and Principe"),
    ("TAA - TCZ", "Turkey"),
    ("TDA - TDZ", "Guatemala"),
    ("TEA - TEZ", "Costa Rica"),
    ("TFA - TFZ", "Iceland"),
    ("TGA - TGZ", "Guatemala"),
    ("THA - THZ", "France"),
    ("TIA - TIZ", "Costa Rica"),
    ("TJA - TJZ", "Cameroon"),
    ("TKA - TKZ", "France"),
    ("TLA - TLZ", "Central African Republic"),
    ("TMA - TMZ", "France"),
    ("TNA - TNZ", "Congo (Republic of the)"),
    ("TOA - TQZ", "France"),
    ("TRA - TRZ", "Gabonese Republic"),
    ("TSA - TSZ", "Tunisia"),
    ("TTA - TTZ", "Chad"),
    ("TUA - TUZ", "Cote d'Ivoire"),
    ("TVA - TXZ", "France"),
    ("TYA - TYZ", "Benin"),
    ("TZA - TZZ", "Mali"),
    ("T2A - T2Z", "Tuvalu"),
    ("T3A - T3Z", "Kiribati"),
    ("T4A - T4Z", "Cuba"),
    ("T5A - T5Z", "Somalia"),
    ("T6A - T6Z", "Afghanistan"),
    ("T7A - T7Z", "San Marino"),
    ("T8A - T8Z", "Palau"),
    ("UAA - UIZ", "Russian Federation"),
    ("UJA - UMZ", "Uzbekistan"),
    ("UNA - UQZ", "Kazakhstan"),
    ("URA - UZZ", "Ukraine"),
    ("VAA - VGZ", "Canada"),
    ("VHA - VNZ", "Australia"),
    ("VOA - VOZ", "Canada"),
    ("VPA - VQZ", "United Kingdom of Great Britain and Northern Ireland"),
    ("VRA - VRZ", "China (People's Republic of)"),
    ("VSA - VSZ", "United Kingdom of Great Britain and Northern Ireland"),
    ("VTA - VWZ", "India"),
    ("VXA - VYZ", "Canada"),
    ("VZA - VZZ", "Australia"),
    ("V2A - V2Z", "Antigua and Barbuda"),
    ("V3A - V3Z", "Belize"),
    ("V4A - V4Z", "Saint Kitts and Nevis"),
    ("V5A - V5Z", "Namibia"),
    ("V6A - V6Z", "Micronesia"),
    ("V7A - V7Z", "Marshall Islands"),
    ("V8A - V8Z", "Brunei Darussalam"),
    ("WAA - WZZ", "United States of America"),
    ("XAA - XIZ", "Mexico"),
    ("XJA - XOZ", "Canada"),
    ("XPA - XPZ", "Denmark"),
    ("XQA - XRZ", "Chile"),
    ("XSA - XSZ", "China (People's Republic of)"),
    ("XTA - XTZ", "Burkina Faso"),
    ("XUA - XUZ", "Cambodia"),
    ("XVA - XVZ", "Viet Nam"),
    ("XWA - XWZ", "Lao People's Democratic Republic"),
    ("XXA - XXZ", "Portugal"),
    ("XYA - XZZ", "Myanmar"),
    ("YAA - YAZ", "Afghanistan"),
    ("YBA - YHZ", "Indonesia"),
    ("YIA - YIZ", "Iraq"),
    ("YJA - YJZ", "Vanuatu"),
    ("YKA - YKZ", "Syrian Arab Republic"),
    ("YLA - YLZ", "Latvia"),
    ("YMA - YMZ", "Turkey"),
    ("YNA - YNZ", "Nicaragua"),
    ("YOA - YRZ", "Romania"),
    ("YSA - YSZ", "El Salvador"),
    ("YTA - YUZ", "Serbia"),
    ("YVA - YYZ", "Venezuela"),
    ("YZA - YZZ", "Serbia"),
    ("Y2A - Y9Z", "Germany (Federal Republic of)"),
    ("ZAA - ZAZ", "Albania"),
    ("ZBA - ZJZ", "United Kingdom of Great Britain and Northern Ireland"),
    ("ZKA - ZMZ", "New Zealand"),
    ("ZNA - ZOZ", "United Kingdom of Great Britain and Northern Ireland"),
    ("ZPA - ZPZ", "Paraguay"),
    ("ZQA - ZQZ", "United Kingdom of Great Britain and Northern Ireland"),
    ("ZRA - ZUZ", "South Africa (Republic of)"),
    ("ZVA - ZZZ", "Brazil"),
    ("Z2A - Z2Z", "Zimbabwe"),
    ("Z3A - Z3Z", "North Macedonia"),
    ("Z6A - Z6Z", "Kosovo"),
    ("Z8A - Z8Z", "South Sudan (Republic of)"),
    ("2AA - 2ZZ", "United Kingdom of Great Britain and Northern Ireland"),
    ("3AA - 3AZ", "Monaco"),
    ("3BA - 3BZ", "Mauritius"),
    ("3CA - 3CZ", "Equatorial Guinea"),
    ("3DA - 3DM", "Eswatini"),
    ("3DN - 3DZ", "Fiji"),
    ("3EA - 3FZ", "Panama"),
    ("3GA - 3GZ", "Chile"),
    ("3HA - 3UZ", "China (People's Republic of)"),
    ("3VA - 3VZ", "Tunisia"),
    ("3WA - 3WZ", "Viet Nam"),
    ("3XA - 3XZ", "Guinea"),
    ("3YA - 3YZ", "Norway"),
    ("3ZA - 3ZZ", "Poland"),
    ("4AA - 4CZ", "Mexico"),
    ("4DA - 4IZ", "Philippines"),
    ("4JA - 4KZ", "Azerbaijan"),
    ("4LA - 4LZ", "Georgia"),
    ("4MA - 4MZ", "Venezuela"),
    ("4NA - 4OZ", "Serbia"),
    ("4PA - 4SZ", "Sri Lanka"),
    ("4TA - 4TZ", "Peru"),
    ("4UA - 4UZ", "United Nations Organization"),
    ("4VA - 4VZ", "Haiti"),
    ("4WA - 4WZ", "East Timor"),
    ("4XA - 4XZ", "Israel"),
    ("4YA - 4YZ", "International Civil Aviation Organization"),
    ("4ZA - 4ZZ", "Israel"),
    ("5AA - 5AZ", "Libya"),
    ("5BA - 5BZ", "Cyprus"),
    ("5CA - 5GZ", "Morocco"),
    ("5HA - 5IZ", "Tanzania"),
    ("5JA - 5KZ", "Colombia"),
    ("5LA - 5MZ", "Liberia"),
    ("5NA - 5OZ", "Nigeria"),
    ("5PA - 5QZ", "Denmark"),
    ("5RA - 5SZ", "Madagascar"),
    ("5TA - 5TZ", "Mauritania"),
    ("5UA - 5UZ", "Niger"),
    ("5VA - 5VZ", "Togolese Republic"),
    ("5WA - 5WZ", "Samoa"),
    ("5XA - 5XZ", "Uganda"),
    ("5YA - 5ZZ", "Kenya"),
    ("6AA - 6BZ", "Egypt"),
    ("6CA - 6CZ", "Syrian Arab Republic"),
    ("6DA - 6JZ", "Mexico"),
    ("6KA - 6NZ", "Korea (Republic of)"),
    ("6OA - 6OZ", "Somalia"),
    ("6PA - 6SZ", "Pakistan"),
    ("6TA - 6UZ", "Sudan"),
    ("6VA - 6WZ", "Senegal"),
    ("6XA - 6XZ", "Madagascar"),
    ("6YA - 6YZ", "Jamaica"),
    ("6ZA - 6ZZ", "Liberia"),
    ("7AA - 7IZ", "Indonesia"),
    ("7JA - 7NZ", "Japan"),
    ("7OA - 7OZ", "Yemen"),
    ("7PA - 7PZ", "Lesotho"),
    ("7QA - 7QZ", "Malawi"),
    ("7RA - 7RZ", "Algeria"),
    ("7SA - 7SZ", "Sweden"),
    ("7TA - 7YZ", "Algeria"),
    ("7ZA - 7ZZ", "Saudi Arabia"),
    ("8AA - 8IZ", "Indonesia"),
    ("8JA - 8NZ", "Japan"),
    ("8OA - 8OZ", "Botswana"),
    ("8PA - 8PZ", "Barbados"),
    ("8QA - 8QZ", "Maldives"),
    ("8RA - 8RZ", "Guyana"),
    ("8SA - 8SZ", "Sweden"),
    ("8TA - 8YZ", "India"),
    ("8ZA - 8ZZ", "Saudi Arabia"),
    ("9AA - 9AZ", "Croatia"),
    ("9BA - 9DZ", "Iran (Islamic Republic of)"),
    ("9EA - 9FZ", "Ethiopia"),
    ("9GA - 9GZ", "Ghana"),
    ("9HA - 9HZ", "Malta"),
    ("9IA - 9IZ", "Zambia"),
    ("9JA - 9JZ", "Zambia"),
    ("9KA - 9KZ", "Kuwait"),
    ("9LA - 9LZ", "Sierra Leone"),
    ("9MA - 9MZ", "Malaysia"),
    ("9NA - 9NZ", "Nepal"),
    ("9OA - 9TZ", "Democratic Republic of the Congo"),
    ("9UA - 9UZ", "Burundi"),
    ("9VA - 9VZ", "Singapore"),
    ("9WA - 9WZ", "Malaysia"),
    ("9XA - 9XZ", "Rwanda"),
    ("9YA - 9ZZ", "Trinidad and Tobago"),
]


# ---------------------------------------------------------------------------
# Section C: _build_ranges() — parse raw data into sorted (start, end, iso) tuples
# ---------------------------------------------------------------------------

def _build_ranges() -> list[tuple[str, str, str | None]]:
    """Parse _ITU_RAW_DATA into sorted list of (start, end, iso_or_none) tuples.

    Raises ValueError at import time if any ITU name is missing from _ITU_NAME_TO_ISO.
    """
    result: list[tuple[str, str, str | None]] = []
    for range_str, itu_name in _ITU_RAW_DATA:
        if itu_name not in _ITU_NAME_TO_ISO:
            raise ValueError(
                f"ITU name {itu_name!r} not found in _ITU_NAME_TO_ISO — update the mapping"
            )
        iso = _ITU_NAME_TO_ISO[itu_name]
        if " - " in range_str:
            start, end = range_str.split(" - ", 1)
            start = start.strip()
            end = end.strip()
        else:
            start = end = range_str.strip()
        result.append((start, end, iso))
    result.sort(key=lambda t: t[0])
    return result


# ---------------------------------------------------------------------------
# Section D: Module-level constants (built once at import)
# ---------------------------------------------------------------------------

_RANGES: list[tuple[str, str, str | None]] = _build_ranges()
_STARTS: list[str] = [r[0] for r in _RANGES]


# ---------------------------------------------------------------------------
# Section E: _strip_suffix() — handle "/" splitting
# ---------------------------------------------------------------------------

_UNRESOLVABLE_SUFFIXES = {"MM", "AM"}


def _strip_suffix(callsign: str) -> str | None:
    """Strip operational suffixes from callsign.

    Returns:
        Base callsign or prefix for lookup, or None if unresolvable (/MM, /AM).

    Handles:
        - No slash: return unchanged
        - prefix/callsign format (e.g. "EA3/G3YWX"): return left side (EA3)
        - /MM, /AM: return None (unresolvable operating suffixes)
        - Other suffixes (/P, /7, /QRP, /M): strip and return base
    """
    if "/" not in callsign:
        return callsign

    parts = callsign.split("/")

    # Check the last segment for unresolvable suffixes
    last = parts[-1].upper()
    if last in _UNRESOLVABLE_SUFFIXES:
        return None

    # Handle prefix/callsign format: if exactly 2 parts and left is shorter than right,
    # the left side is the operating location prefix (e.g. "EA3" in "EA3/G3YWX")
    if len(parts) == 2:
        left, right = parts[0], parts[1]
        if len(left) < len(right):
            return left

    # Otherwise strip suffix — return the base (first part)
    return parts[0]


# ---------------------------------------------------------------------------
# Section F: _range_lookup() — bisect-based truncated-comparison lookup
# ---------------------------------------------------------------------------

_NOTFOUND = object()  # Sentinel to distinguish "not found" from "found, iso=None"


def _range_lookup(prefix: str) -> object:
    """Look up prefix in sorted _RANGES using bisect with truncated comparison.

    Uses prefix+'~' for bisect upper-bound (tilde sorts after Z and digits).
    Truncates range endpoints to the prefix length for comparison, allowing
    short prefixes like 'W' to match 'WAA-WZZ' correctly.

    Returns:
        ISO code (str), None (non-country entity), or _NOTFOUND sentinel.
    """
    n = len(prefix)
    idx = bisect.bisect_right(_STARTS, prefix + "~") - 1
    while idx >= 0:
        start, end, iso = _RANGES[idx]
        ts = start[:n]
        te = end[:n]
        if ts <= prefix <= te:
            return iso
        if ts < prefix:
            # All earlier ranges start even lower — cannot match
            break
        idx -= 1
    return _NOTFOUND


# ---------------------------------------------------------------------------
# Section G: lookup_prefix() — public API
# ---------------------------------------------------------------------------

def lookup_prefix(callsign: str) -> str | None:
    """Resolve callsign to ISO 3166-1 alpha-2 country code, or None.

    Handles:
    - Standard letter-prefix callsigns (W1AW, DL1ABC, JA1YWX)
    - Digit-prefix callsigns (3DA0ABC, 4U1ITU)
    - Letter+digit prefix callsigns (C7A, H2A, 9H1A)
    - Operational suffixes (/P, /7, /QRP, /M) — stripped
    - Unresolvable operating modes (/MM, /AM) — return None
    - Prefix/callsign format (EA3/G3YWX) — resolve the prefix side
    - Non-country ITU entities (4U, C7, 4Y) — return None
    - Invalid/unrecognized strings — return None
    """
    callsign = callsign.upper().strip()
    if not callsign:
        return None
    base = _strip_suffix(callsign)
    if base is None:
        return None

    # Find first digit — absence of digit means not a valid callsign structure
    digit_pos = next((i for i, c in enumerate(base) if c.isdigit()), None)
    if digit_pos is None:
        return None  # e.g. "UNKNOWN" — no digit, not a valid callsign

    # Build candidate prefixes to try (longest first, most-specific first)
    candidates: list[str] = []

    if digit_pos == 0:
        # Callsign starts with digit: extract digit+following letters (e.g. 3DA, 4U, 4Y)
        m = re.match(r"^([0-9][A-Z]{1,2})", base)
        if m:
            candidates.append(m.group(1))
        # Fallback: single digit
        if base[0] not in candidates:
            candidates.append(base[0])
    else:
        # Callsign starts with letters:
        # Primary candidate: letter-prefix (letters before first serial digit, e.g. DL, JA, W)
        letter_prefix = base[:digit_pos]
        if len(letter_prefix) <= 3:
            candidates.append(letter_prefix)
        # Secondary candidate: letter+digit (for C7, H2, 9H type allocations)
        with_digit = base[: digit_pos + 1]
        if len(with_digit) <= 3 and with_digit not in candidates:
            candidates.insert(0, with_digit)  # Try longer/more-specific first

    # Try candidates from longest to shortest — return first match found
    for candidate in sorted(set(candidates), key=len, reverse=True):
        result = _range_lookup(candidate)
        if result is not _NOTFOUND:
            return result  # type: ignore[return-value]  # May be None for non-country entities

    return None
