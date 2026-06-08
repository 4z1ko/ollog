---
phase: 63
status: planned
created: 2026-06-08
---

# Phase 63 Validation Strategy

## Objective

Prove ACLog full-record import captures complete QSO data exposed by ACLog `INCLUDEALL` responses while preserving current `ENTEREVENT` fallback behavior.

## Required Evidence

- Parser tests for ACLog full-record response shapes, including arbitrary valid ADIF-like fields.
- Merge tests proving full-record fields override compact `ENTEREVENT` fields only when non-empty.
- Fallback tests proving existing `ENTEREVENT` plus cached textbox update behavior still imports when full-record enrichment is unavailable.
- Other field tests proving `OTHER_1` through `OTHER_8` are preserved or mapped to configured custom QSO field names.
- Client/bridge tests using deterministic fake messages rather than requiring live ACLog.
- Regression tests for current ACLog parser behavior, custom field mapping, and QSO ingestion path.

## Manual Validation

With a real ACLog instance:

1. Enable the ACLog API and configure an ollog bridge.
2. Save a contact with call, band, mode, date/time, frequency, reports, and at least two Other fields.
3. Confirm ollog stores the QSO under the logged-in user's `<username>_qsos` collection.
4. Confirm all populated ACLog fields appear in the stored QSO document or mapped custom ADIF fields.
5. Confirm duplicate handling still reports duplicates instead of inserting a second copy.

## Acceptable Skips

- Live ACLog validation may be manual-only if no ACLog instance is available in the test environment.
- Mongo-backed tests may skip cleanly when local MongoDB is unavailable, but parser/merge/client unit tests must run without MongoDB.
