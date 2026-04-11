# ADIF Import/Export

ollog supports bulk import of existing logbooks in ADIF format and export of your complete log as an ADIF file.

## Importing an ADIF File

### POST /api/adif/import

Import QSOs from an ADIF (.adi or .adif) file.

- **Auth:** Bearer token or X-API-Key
- **Request:** `multipart/form-data` with a `file` field containing the ADIF file (max 10 MB)
- **Response:** 200 with an import report:

```json
{
  "total_records": 150,
  "accepted": [{"record_index": 0, "call": "DL1ABC", "id": "..."}],
  "duplicates": [{"record_index": 1, "call": "W1AW", "existing_id": "..."}],
  "errors": [{"record_index": 2, "call": null, "error": "missing required field: BAND"}]
}
```

```bash
curl -X POST http://localhost:8000/api/adif/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@mylog.adi"
```

### Import Behavior Notes

- **Duplicate detection:** Same ±2 minute window as manual QSO entry (CALL + BAND + MODE + operator).
- **OPERATOR / STATION_CALLSIGN:** Values from the file are preserved as-is. They are NOT auto-stamped from your profile. This maintains historical record fidelity.
- **All errors accumulated:** Every record error is returned in the report — no records are silently dropped.
- **No force override:** The import endpoint does not support `?force=true`. To re-import an already-imported file, delete the existing records first, then import again.
- **File size limit:** 10 MB. Files larger than this receive a 413 response.

## Exporting Your Log

### GET /api/adif/export

Export your complete log as an ADIF 3.1.4 file.

- **Auth:** Bearer token or X-API-Key
- **Response:** 200 with `text/plain` streaming body (Content-Disposition: attachment). Filename is `{callsign}_logbook.adi`.
- **Includes:** Only your own QSOs (operator-isolated). Soft-deleted QSOs are excluded.

```bash
curl http://localhost:8000/api/adif/export \
  -H "Authorization: Bearer $TOKEN" \
  -o mylog.adi
```

The ADIF header in the export specifies `ADIF_VER:3.1.4` and `PROGRAMID:ollog`.

## Working with Popular Logging Software

### Log4OM

Export from Log4OM: **File > Export > ADIF**. Then import the exported file using the curl command above.

For live logging from Log4OM via UDP, see [UDP ADIF](udp-adif.md).

### WSJT-X

WSJT-X writes a running log to `WSJTX_LOG.ADI` in its data directory. Periodically import this file:

```bash
curl -X POST http://localhost:8000/api/adif/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/WSJTX_LOG.ADI"
```

Note: WSJT-X's UDP output uses a binary-framed protocol that is not compatible with ollog's UDP listener. Use the ADIF file import path instead.

### N1MM+ (N1MM Logger Plus)

Export to ADIF from N1MM+ via **File > Export to ADIF**, then import:

```bash
curl -X POST http://localhost:8000/api/adif/import \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/your-log.adi"
```

Note: N1MM+ broadcasts contact data as XML, not ADIF text. Use the file import path.
