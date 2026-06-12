# Phase 64: ACLog Bridge Manual Sync - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Add manual, operator-triggered ACLog synchronization from Profile Settings. A logged-in operator can press Sync beside an existing saved ACLog bridge, ollog requests all remote records with `<CMD><LIST><INCLUDEALL></CMD>`, imports only records that should be added to that operator's `<username>_qsos` collection, and renders a completion report through the existing profile-result area.

This phase is additive sync only. It must not update existing local QSOs, delete local QSOs, add scheduled/background sync, or allow cross-operator bridge/collection access.

</domain>

<decisions>
## Implementation Decisions

### Sync Button Placement
- **D-01:** Show Sync only for saved ACLog bridge rows that already have a stable bridge ID in the operator profile.
- **D-02:** New/unsaved bridge rows must be saved before they can be synced.
- **D-03:** Render sync results into the existing `#profile-result` target near the top of the Profile Settings page, instead of adding per-row report targets.

### Sync Runtime Behavior
- **D-04:** The Sync button should submit one HTMX request that waits until the sync completes, then swaps in the final report.
- **D-05:** Use a fixed timeout for offline, slow, or incomplete ACLog responses and report timeout/failure clearly through `#profile-result`.
- **D-06:** Do not add an app-side record cap. The sync command requests all records with `<CMD><LIST><INCLUDEALL></CMD>` and processes all records returned by ACLog within the timeout.
- **D-07:** Do not introduce a background job, polling status model, or persisted sync history in this phase.

### Report Details
- **D-08:** The report should be a simple summary, not a detailed diagnostics page.
- **D-09:** Main report wording should use **"Missing QSOs imported"**.
- **D-10:** Report counts should include missing/imported QSOs, already-present/skipped QSOs, and errors/rejections.
- **D-11:** If records are rejected because required fields are missing or invalid, show the count plus the first few examples so the operator can diagnose ACLog data issues without overwhelming the page.

### Duplicate Meaning
- **D-12:** For sync pre-checks, exact `rowHash` is the preferred definition of an already-existing QSO.
- **D-13:** If a remote ACLog QSO has no exact existing `rowHash` but the existing ingest path still flags it as a duplicate through current loose duplicate detection, skip it and count it as duplicate/already-present.
- **D-14:** Do not create a sync-only overwrite or merge path for near-duplicates. Sync remains additive and conservative.

### the agent's Discretion
- Choose the exact timeout value, number of rejection examples, route name, template fragment name, and button styling consistent with existing profile/HTMX patterns.
- Decide whether the rowHash pre-check is explicit before ingest or implemented by reusing existing insert/duplicate behavior, as long as the externally reported behavior matches D-12 and D-13.
- Decide how to structure the sync service/client helpers so live ACLog bridge behavior remains unchanged.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and Phase Scope
- `.planning/PROJECT.md` — v3.3 milestone goal and active ACSYNC requirements.
- `.planning/REQUIREMENTS.md` — ACSYNC-01 through ACSYNC-09 and explicit out-of-scope sync boundaries.
- `.planning/ROADMAP.md` — Phase 64 goal, dependencies, and success criteria.
- `.planning/STATE.md` — current milestone state and prior decisions.
- `.planning/research/ACLOG-SYNC.md` — ACLog API command research and implementation implications.

### Prior Phase Context
- `.planning/phases/61-qso-workflow-refactor/61-CONTEXT.md` — username-derived collection routing, `_operator` callsign semantics, and raw collection service boundary.
- `.planning/phases/62-cross-feature-integration-and-verification/62-CONTEXT.md` — app-level live feed broadcasts from write paths and dynamic collection integration decisions.
- `.planning/phases/63-aclog-full-record-import-via-includeall/63-01-SUMMARY.md` — existing ACLog `LIST INCLUDEALL` parser/client behavior and custom Other field preservation.

### Code Anchors
- `app/aclog/client.py` — live bridge runtime, existing recent-record INCLUDEALL request, `_ingest_aclog_record()`, and Other-field mapping helper.
- `app/aclog/parser.py` — ACLog `<CMD>` parsing, multi-record `LIST` parsing, field normalization, and full-record conversion.
- `app/qso/ui_router.py` — Profile Settings routes, HTMX profile result pattern, ACLog bridge form parsing, and operator clear-log route style.
- `templates/log/profile.html` — Profile Settings layout, saved/new ACLog bridge rows, bridge add/remove controls, and `#profile-result`.
- `app/qso/service.py` — `ingest_qso_record()`, duplicate handling, QSO construction, and collection-aware insert path.
- `app/qso/collections.py` — username-derived `<username>_qsos` collection access.
- `tests/test_aclog_client.py` — existing ACLog client tests and fake writer pattern.
- `tests/test_aclog_parser.py` — parser coverage for ACLog full-record responses.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `aclog_full_records_from_message()` in `app/aclog/parser.py`: already parses multi-record `LIST`/`LISTRESPONSE` responses into ADIF-style record dicts.
- `_map_other_slots_to_custom_fields()` in `app/aclog/client.py`: existing custom field mapping behavior should be reused for sync imports.
- `ingest_qso_record()` in `app/qso/service.py`: existing validation, profile stamping, duplicate handling, and collection-aware insert result shape.
- `get_user_qso_collection()` in `app/qso/collections.py`: required storage target for the logged-in operator's collection.
- `profile_result.html` and `#profile-result`: existing HTMX result target for profile actions.

### Established Patterns
- Browser profile actions return HTML fragments with HTTP 200 so HTMX swaps error and success results reliably.
- User-facing QSO storage routes derive the raw MongoDB collection from authenticated `User.username`, not callsign.
- `_operator` remains the operator callsign in QSO documents for display and ADIF semantics.
- ACLog live bridge behavior must continue to use recent-record enrichment after `ENTEREVENT`; manual all-log sync is a separate action.
- Mongo-dependent tests should skip cleanly where live MongoDB is unavailable; parser/client logic should remain testable with fakes.

### Integration Points
- Add one sync POST route under the profile UI route family, targeting a saved bridge ID owned by the logged-in user.
- Add Sync controls to saved ACLog bridge rows in `templates/log/profile.html`; do not add Sync to the blank new bridge row.
- Add a sync helper/service that opens a TCP connection to the selected bridge, sends `<CMD><LIST><INCLUDEALL></CMD>`, reads/parses returned records until completion or timeout, then loops through records and ingests accepted records into the user's collection.
- Keep live-feed behavior consistent with other app-created QSO write paths if accepted sync imports should appear in station feed.

</code_context>

<specifics>
## Specific Ideas

- Report headline should say "Missing QSOs imported".
- The final report can stay compact, for example: "Missing QSOs imported: X. Already present: Y. Errors: Z."
- Rejection details should show only the first few examples.
- Sync should be visibly tied to saved bridges only, but the report itself should use the existing top-of-page profile result target.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 64 scope.

</deferred>

---

*Phase: 64-aclog-bridge-manual-sync*
*Context gathered: 2026-06-12*
