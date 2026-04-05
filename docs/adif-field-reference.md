# ADIF Field Reference

ollog uses ADIF (Amateur Data Interchange Format) for QSO data. This page describes how key fields are formatted and handled.

## Core Fields

| Field | Format | Example | Notes |
|-------|--------|---------|-------|
| QSO_DATE | YYYYMMDD | 20240415 | UTC date of contact |
| TIME_ON | HHMM or HHMMSS | 1430 or 143045 | UTC time of contact |
| CALL | Callsign string | DL1ABC | Station worked |
| BAND | Amateur band designator | 20m, 40m, 2m | Standard ADIF band values |
| MODE | Uppercased mode | SSB, CW, FT8, FM | Standard ADIF mode values |
| RST_SENT | Signal report string | 59, 599 | 599 for CW, 59 for phone |
| RST_RCVD | Signal report string | 59, 599 | Received signal report |

## Auto-Stamped Fields

| Field | Source | When Stamped | Notes |
|-------|--------|--------------|-------|
| OPERATOR | JWT callsign (account) | Every QSO created via API/UI | Always stamped. Cannot be overridden by the user. |
| STATION_CALLSIGN | Profile station_callsign | When profile has station_callsign set | Optional. Represents the station being operated (e.g., club call). |

When importing ADIF files, OPERATOR and STATION_CALLSIGN are **not** auto-stamped. The values from the file are preserved as-is. This ensures historical records maintain their original attribution.

## Extra Fields

ollog accepts any standard ADIF field beyond the core set. Extra fields are stored as-is in the QSO record and included in ADIF exports. The QSO creation endpoint uses `extra="allow"` on its Pydantic model — any additional fields in the JSON body are accepted and persisted.

Examples of extra fields: `FREQ`, `TX_PWR`, `COMMENT`, `QTH`, `GRIDSQUARE`, `CONTEST_ID`, `SRX`, `STX`

## Duplicate Detection

ollog checks for duplicate QSOs on every new record, whether created via the API or imported from an ADIF file. The detection algorithm:

- **Window:** +/- 2 minutes on QSO_DATE + TIME_ON
- **Match fields:** CALL + BAND + MODE + operator (the logged-in user)
- **Response:** 409 Conflict with error details (single QSO creation endpoint)
- **Override:** Append `?force=true` to the POST URL to bypass duplicate detection for single QSO creation

Note: The ADIF import endpoint does not support `?force=true`. To re-import a file that was already imported, delete the existing records first, then import again.
