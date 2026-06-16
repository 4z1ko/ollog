# ACLog Operator Identity Research

**Date:** 2026-06-16
**Milestone:** v3.5 ACLog Registered Operator Routing

## Question

When two ollog operators configure ACLog bridges to the same remote ACLog computer, how can ollog ensure each operator imports only their own ACLog QSOs?

## Official API Findings

N3FJP's ACLog TCP API is command/response based over TCP. The logging program is the TCP server, commonly on port `1100`, and clients send XML-like `<CMD>...</CMD>` messages terminated with CRLF.

Relevant commands:

- `<CMD><GETUSERSETTINGS></CMD>` returns setup values including `<OPERATOR>...`.
- `<CMD><LIST><INCLUDEALL></CMD>` returns all QSO records and includes every field whose value length is greater than zero.
- The docs recommend filling every field in an edited record and trying the API command to see the returned tags.

Source:

- https://www.n3fjp.com/help/api.html

## Local Implementation Findings

Current ollog behavior routes ACLog records by bridge ownership:

- `app/aclog/manager.py` starts one bridge runtime per enabled saved bridge.
- `app/aclog/client.py` builds runtime config from the owning ollog `User`.
- Live ingestion calls `ingest_qso_record(... operator=user.callsign, profile=user, collection=get_user_qso_collection(user))`.
- Manual sync in `app/aclog/sync.py` imports all records returned from `<CMD><LIST><INCLUDEALL></CMD>` into the authenticated user's collection.

That means two operators pointed at the same ACLog API endpoint can both ingest the same remote QSO set unless ollog filters records by ACLog-side operator identity.

## Open Field Discovery

The official API confirms that ACLog exposes a current setup `OPERATOR`, but it does not explicitly guarantee which operator identity field is present on each saved QSO record returned by `LIST INCLUDEALL`.

Phase 66 should therefore collect or simulate representative raw `LIST INCLUDEALL` records and detect candidate identity fields in priority order. Likely candidates include:

- `OPERATOR`
- `STATION_CALLSIGN`
- `OWNER_CALLSIGN`
- `MY_CALL`
- `MYCALL`
- ACLog-specific/custom identity tags that appear in real responses

Only verified record-level identity fields should be used for automatic filtering.

## Recommended Behavior

Use ACLog record identity as a gate, not as a dynamic cross-user router:

1. For each live bridge or manual sync record, parse the full ACLog record.
2. Extract a normalized operator identity from recognized record-level fields.
3. Compare the identity to the configured/authenticated ollog operator callsign and profile identity.
4. If it matches, ingest normally into that operator's `<username>_qsos` collection.
5. If it is missing or unmatched, skip the record and count/report it.

The user confirmed on 2026-06-16 that missing or unmatched ACLog operator records should be skipped.

## Risks

- ACLog may not persist record-level operator identity unless the operator field is configured/populated in ACLog.
- Existing shared ACLog databases may contain historical records without an operator field.
- `GETUSERSETTINGS` returns the currently configured ACLog setup operator, but that value alone is not enough to safely split a shared remote log if old records belong to multiple operators.
- Field names may differ by ACLog version, contest logger variant, or user-customized fields.

## Validation Strategy

- Unit-test candidate field extraction and normalization.
- Unit-test skip behavior for missing and unmatched operator identity.
- Add manual sync tests where two ollog users target the same bridge response and each imports only matching records.
- Add live bridge tests for `ENTEREVENT` plus `LIST INCLUDEALL` enrichment where only matching records are ingested.
- Update ACLog bridge docs to tell operators how to confirm their ACLog records include operator identity.
