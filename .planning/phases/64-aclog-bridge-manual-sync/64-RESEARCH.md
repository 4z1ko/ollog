# Phase 64: ACLog Bridge Manual Sync - Research

**Researched:** 2026-06-12
**Status:** Research complete

## Research Complete

Phase 64 should be implemented as a small manual-sync layer on top of the existing v3.2 ACLog parser and v3.1/v3.2 collection-aware QSO ingestion primitives. No new external dependency is needed.

## Existing Assets To Reuse

### ACLog Parser

- `app/aclog/parser.py` already parses ACLog `<CMD>` payloads.
- `iter_cmd_messages()` splits concatenated TCP reads into individual command messages.
- `aclog_full_records_from_message()` already supports nested `<RECORD>` wrappers and repeated flat record responses for `LIST`, `LISTRESPONSE`, `SEARCH`, and `SEARCHRESPONSE`.
- `aclog_full_record_to_adif()` normalizes field names and values, skips control fields, preserves safe ADIF-like fields, and normalizes numeric bands.

### ACLog Client

- `app/aclog/client.py` already contains bridge config shape, connection setup, recent-record request behavior, and `_map_other_slots_to_custom_fields()`.
- Existing live bridge logic must remain unchanged: after `ENTEREVENT`, it requests `<CMD><LIST><INCLUDEALL><VALUE>5</VALUE></CMD>` and correlates a full record with the pending event.
- Manual sync should be separate from `run_aclog_bridge()` so it does not disturb the long-running background bridge manager.

### QSO Ingestion

- `app/qso/service.py::ingest_qso_record()` validates required fields, builds/stamps QSO docs, runs loose duplicate detection, inserts through the provided raw collection, catches exact `rowHash` duplicate key errors, and broadcasts accepted app-created QSOs.
- `insert_qso_dict()` returns explicit duplicate status on rowHash duplicate key errors.
- `get_user_qso_collection()` is the required storage target for the logged-in user's `<username>_qsos` collection.

### UI and Route Pattern

- `app/qso/ui_router.py` owns Profile Settings page and form handling.
- `templates/log/profile.html` contains saved bridge rows and one blank `new-0` bridge row.
- Existing profile feedback uses `#profile-result` and `templates/log/profile_result.html`, but sync likely needs a new report fragment because it has counts and optional rejected examples.
- HTMX fragments should return HTTP 200 for both success and failure so response bodies swap reliably.

## Recommended Implementation Shape

1. Add a manual sync service/helper in `app/aclog/client.py` or a new `app/aclog/sync.py`.
2. The helper should:
   - open one TCP connection to the selected bridge host/port;
   - send exactly `<CMD><LIST><INCLUDEALL></CMD>\r\n`;
   - read response bytes/messages until completion or a fixed timeout;
   - parse all records through `aclog_full_records_from_message()`;
   - map ACLog Other slots through the existing custom-field mapping;
   - ingest each record with `ingest_qso_record(..., collection=get_user_qso_collection(user))`;
   - return a structured report with `received`, `imported`, `skipped`, `errors`, and first few rejected examples.
3. Add a route under the profile UI route family, for example `POST /log/profile/aclog/{bridge_id}/sync`.
4. The route should:
   - resolve the logged-in `User`;
   - find the bridge by ID in `user.aclog_bridges`;
   - reject missing/unsaved/foreign bridge IDs with a profile-result-compatible error fragment;
   - call the sync helper;
   - render a new compact report partial into `#profile-result`.
5. Add Sync button only inside the `{% for bridge in profile.aclog_bridges %}` loop, not in the blank new bridge row.

## Duplicate and RowHash Notes

The user chose exact rowHash as the preferred "already present" definition for sync, but also chose to keep current loose duplicate blocking. The plan should therefore preserve both:

- If exact `rowHash` already exists, skip/count as already present.
- If exact `rowHash` is absent but `ingest_qso_record()` returns duplicate from the existing loose duplicate rule, skip/count as duplicate/already present.
- Do not import near-duplicates if the existing ingest path blocks them.
- Do not update, merge, or delete existing local records.

Planning should be careful that rowHash is computed from the same transformed/stamped document shape used for insert. The safest route may be to let `insert_qso_dict()` handle exact rowHash duplicates after `build_qso_dict()` and then count the returned duplicate status. If an explicit rowHash pre-check is added, it must compute the hash from the same final document shape or it can drift from insert behavior.

## Timeout and Completion Risk

The official ACLog command requests all records, but the local code has no current all-log read-completion protocol. The implementation needs a clear read loop rule:

- Use a fixed overall timeout.
- Do not add an app-side record cap.
- Treat timeout/incomplete reads as failure.
- Keep the report simple and avoid partial-success semantics unless the implementation can prove the response completed before timeout.

Planner should assign a concrete timeout value and ensure tests do not sleep in real time.

## Validation Architecture

Automated coverage should focus on deterministic parser/client/service behavior without requiring a live ACLog instance:

- Parser test for all-record `LIST INCLUDEALL` response with multiple records and extra fields.
- Client/helper test with fake reader/writer asserting exactly `<CMD><LIST><INCLUDEALL></CMD>\r\n` is sent.
- Sync service test with fake records asserting accepted/duplicate/rejected counts and first rejected examples.
- Route/template test asserting saved rows include Sync button, new row does not, and HTMX target is `#profile-result`.
- Ownership test asserting a missing bridge ID owned by no one else cannot be synced.
- Existing live bridge tests should continue to assert recent-record `<VALUE>5</VALUE>` behavior.

Manual UAT should use a live ACLog instance when available:

1. Configure and save an ACLog bridge.
2. Press Sync.
3. Confirm "Missing QSOs imported" count matches remote-only records.
4. Press Sync again and confirm those records are skipped, not duplicated.

## Watch Outs

- Do not alter `run_aclog_bridge()` live event behavior while adding manual sync.
- Do not render Sync for the `new-0` row.
- Do not use callsign to choose the collection; use the logged-in `User.username`.
- Do not return HTTP 4xx for HTMX error fragments.
- Do not add scheduled/background sync or sync history in this phase.
- Do not overwrite existing QSOs.
