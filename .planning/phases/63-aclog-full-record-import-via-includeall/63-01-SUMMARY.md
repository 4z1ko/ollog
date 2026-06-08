# Phase 63 Plan 01 Summary: ACLog INCLUDEALL Full-Record Import

**Completed:** 2026-06-08
**Status:** Implementation complete; UAT pending

## Delivered

- Added ACLog full-record parsing for `LIST`/`LISTRESPONSE` and related response commands.
- Added deterministic merge behavior where matched INCLUDEALL full-record data overrides the minimal `ENTEREVENT` payload and cached live text-box state fills remaining fallback fields.
- Updated the ACLog bridge to request `<CMD><LIST><INCLUDEALL><VALUE>1</VALUE></CMD>` after each `ENTEREVENT`.
- Added pending-event correlation so enriched records are ingested only when the full-record response matches the saved QSO identity.
- Preserved the existing fallback path: if enrichment is unavailable, nonmatching, or the connection drops before a full record arrives, the bridge ingests the original `ENTEREVENT` record.
- Preserved ACLog Other fields and kept existing Custom QSO Field mapping behavior.
- Updated operator documentation for enriched imports, Other fields, and troubleshooting.

## Code Touchpoints

- `app/aclog/parser.py`
- `app/aclog/client.py`
- `tests/test_aclog_parser.py`
- `tests/test_aclog_client.py`
- `tests/test_custom_qso_fields.py`
- `docs/operator-guide/aclog-bridges.md`

## Notes

- The implementation is intentionally conservative: full-record enrichment only applies to a pending event when `CALL`, `QSO_DATE`, `TIME_ON`, and optional band/mode comparisons are compatible.
- The old no-writer `_handle_message()` path still ingests `ENTEREVENT` immediately, which keeps existing direct/unit call behavior compatible.
