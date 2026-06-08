---
phase: 63
title: ACLog Full-Record Import via INCLUDEALL
status: complete
researched: 2026-06-08
---

# Phase 63 Research: ACLog Full-Record Import via INCLUDEALL

## Research Question

How should ollog extend the existing ACLog TCP bridge so saved contacts import the full ACLog record, including user-customized Other fields, without regressing the current live `ENTEREVENT` import behavior?

## External API Findings

Official N3FJP API documentation indicates:

- ACLog emits `ENTEREVENT` when a contact is entered, but that event is a compact notification payload rather than a full QSO export.
- `LIST INCLUDEALL` returns every non-empty field for records.
- `LIST INCLUDEALL VALUE 20` returns the most recent 20 QSOs with every non-empty field.
- `SEARCH INCLUDEALL ...` also returns every non-empty matching field.
- `SETUPDATESTATE TRUE` streams textbox updates; ollog already uses this as a state cache for frequency, reports, and `txtEntryOther1` through `txtEntryOther8`.
- `GETOTHERFIELDTITLES` is documented in API 2.2 for retrieving user-customized Other field titles.
- N3FJP release notes from 2025 mention API tags for user-customized Other fields sent with `INCLUDEALL`.

References:

- N3FJP API documentation: `https://www.n3fjp.com/help/api.html`
- N3FJP 2025 release notes: `https://www.n3fjp.com/news/news2025-01-02.html`

## Current ollog Behavior

Relevant files:

- `app/aclog/client.py`
- `app/aclog/parser.py`
- `app/qso/custom_fields.py`
- `app/qso/service.py`
- `tests/test_aclog_parser.py`
- `tests/test_custom_qso_fields.py`
- `docs/operator-guide/aclog-bridges.md`

Current flow:

1. `run_aclog_bridge()` opens one TCP connection per enabled per-user bridge.
2. `_initialize_connection()` sends:
   - `SETUPDATESTATE TRUE`
   - `READBMF`
   - `GETOTHERFIELDTITLES`
3. `update_state_from_message()` caches:
   - `FREQ`
   - `RST_SENT`
   - `RST_RCVD`
   - `OTHER_1` through `OTHER_8` from `txtEntryOtherN`
4. On `ENTEREVENT`, `_handle_message()` converts the event via `aclog_enterevent_to_adif(...)`.
5. `_map_other_slots_to_custom_fields(...)` maps `OTHER_N` to the user's configured custom field ADIF names.
6. `ingest_qso_record(...)` inserts through the same QSO service path as other live ingestion sources.

Current gap:

- The bridge does not request `LIST INCLUDEALL` after `ENTEREVENT`.
- The bridge does not parse full-record `LIST`/`SEARCH` style responses.
- `GETOTHERFIELDTITLES` is sent but its response is not currently parsed or used.
- Fields absent from the compact `ENTEREVENT` payload are only captured if they arrived through live textbox update state.

## Recommended Design

Add a full-record enrichment step after each `ENTEREVENT`:

1. Convert `ENTEREVENT` immediately into a base record using existing logic.
2. Send a full-record request, preferably `LIST INCLUDEALL VALUE 1`, on the same TCP connection.
3. Correlate the next full-record response to the triggering event by matching stable QSO identity fields such as:
   - `CALL`
   - `QSO_DATE`
   - `TIME_ON`
   - `BAND`
   - `MODE`
4. Merge full-record fields over the base event record where the full-record value is non-empty.
5. Keep cached live state as a fallback for fields not present in either the event or the full-record response.
6. Preserve every valid ADIF-like field name returned by ACLog.
7. Map `OTHER_1` through `OTHER_8` into configured custom QSO field ADIF names after merging.
8. If full-record response fails, times out, or cannot be correlated, ingest the base `ENTEREVENT` record exactly as today.

## Implementation Shape

Parser additions:

- Add parsing helpers for ACLog full-record responses:
  - normalize field tags to uppercase.
  - preserve all non-empty ADIF-like tags.
  - apply band suffix normalization consistently.
  - skip transport/control metadata such as count/status wrapper fields.
- Add a merge helper:
  - `merge_aclog_records(base, full, state) -> dict[str, str]`
  - full record wins for non-empty values.
  - base event wins where full is missing.
  - state fills known live fields (`FREQ`, reports, Other slots) when both are missing.

Client additions:

- Track a pending full-record request after `ENTEREVENT`.
- Avoid indefinite blocking in the read loop; use a short timeout or pending-state window.
- Keep a fallback path that ingests the event record when full-record data is unavailable.
- Consider sending `LIST INCLUDEALL VALUE 1` immediately after `ENTEREVENT` and ingesting once the matching response arrives.

Other field handling:

- Continue storing `OTHER_N` when no custom mapping exists.
- Continue mapping `OTHER_N` to configured `CustomQSOField.adif_name` when configured.
- Parse `OTHERFIELDTITLESRESPONSE` if documented response shape is available from ACLog fixtures/logs.
- Do not block full-record import on title parsing; title support can improve diagnostics and future auto-mapping.

## Risks

- ACLog response shape for `LIST INCLUDEALL` may not be identical to `ENTEREVENT`; tests need realistic fixture messages.
- `LIST INCLUDEALL VALUE 1` might race if ACLog returns previous record before the new one is committed. Correlation and fallback are required.
- The bridge currently uses a simple line-by-line loop; request/response pairing must not stall unrelated update messages.
- Some ACLog fields may not be valid ADIF names. The parser should preserve only safe uppercase alphanumeric/underscore keys unless a specific mapping is added.
- Duplicate detection must remain unchanged and per-user scoped through `ingest_qso_record(...)`.

## Validation Architecture

Validation should include deterministic parser/client tests without requiring live ACLog:

- parser test for full-record response preserving arbitrary non-empty ADIF-like fields.
- merge test for full-record-over-event precedence.
- fallback test when no matching full record arrives.
- Other field mapping test for `OTHER_1` to configured custom field name.
- bridge/client test with fake reader/writer or direct message handler around `ENTEREVENT` plus full-record response.
- regression tests for existing `ENTEREVENT`, `READBMF`, textbox update, and ingestion paths.

Live/manual validation remains useful:

- Configure a real ACLog bridge.
- Save a QSO with frequency, reports, and multiple populated Other fields.
- Confirm ollog stores the complete record under the correct user's `<username>_qsos` collection.
