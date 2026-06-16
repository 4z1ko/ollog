# Phase 66: ACLog Operator Identity Routing - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 66 makes ACLog imports safe when multiple ollog operators configure bridges to the same remote ACLog computer. The phase should use ACLog record-level operator identity to decide whether a QSO belongs to the ollog operator whose bridge or sync action is running.

Records with missing, blank, or unmatched ACLog operator identity must be skipped and counted/reported. They must not fall back to the bridge owner's ollog account.

</domain>

<decisions>
## Implementation Decisions

### Identity Source
- **D-01:** Prefer record-level identity returned by ACLog `LIST INCLUDEALL`; do not rely only on `GETUSERSETTINGS` for historical/full-log sync because one ACLog database can contain records from multiple operators.
- **D-02:** Treat `OPERATOR` as the first expected candidate field, but planning/implementation must verify real returned field names and support a small explicit candidate list.
- **D-03:** Normalize callsigns for comparison by trimming whitespace and uppercasing.

### Routing Model
- **D-04:** ACLog identity is a filter/gate for the current bridge owner, not a cross-user dispatcher. A bridge owned by operator A should not insert records into operator B's collection.
- **D-05:** Missing or unmatched identity records are skipped and reported, per user confirmation on 2026-06-16.
- **D-06:** Matching records continue through existing `ingest_qso_record` behavior so profile stamping, custom field mapping, duplicate handling, rowHash behavior, and per-user collection routing remain consistent.

### Surfaces
- **D-07:** Apply filtering to both live ACLog bridge ingestion and manual Profile Settings sync.
- **D-08:** Manual sync reports must show counts for missing/unmatched operator skips in addition to existing imported, already-present, and error counts.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone and Requirements
- `.planning/REQUIREMENTS.md` - v3.5 ACLog registered operator routing requirements `ACOP-01` through `ACOP-09`.
- `.planning/ROADMAP.md` - Phase 66 goal, dependencies, requirements, and success criteria.
- `.planning/research/ACLOG-OPERATOR-IDENTITY.md` - official API and local implementation research.
- `.planning/research/ACLOG-SYNC.md` - prior `LIST INCLUDEALL` sync research.

### Existing Code
- `app/aclog/client.py` - live TCP bridge runtime and full-record fetch/ingest path.
- `app/aclog/manager.py` - per-user saved bridge runtime reconciliation.
- `app/aclog/parser.py` - ACLog XML-like response parsing and field preservation.
- `app/aclog/sync.py` - manual `LIST INCLUDEALL` sync implementation.
- `app/auth/models.py` - `User` and `ACLogBridge` profile data.
- `app/qso/service.py` - shared QSO ingestion, profile stamping, duplicates, and rowHash behavior.
- `docs/operator-guide/aclog-bridges.md` - operator-facing bridge and sync documentation.
- `tests/test_aclog_client.py` and related ACLog/profile tests - focused regression coverage.

</canonical_refs>

<code_context>
## Existing Code Insights

### Current Risk
- Live ACLog ingestion currently uses the bridge owner's ollog user as the destination identity.
- Manual ACLog sync currently imports all returned remote records into the authenticated user's collection.
- Parser behavior already preserves ADIF-like fields such as `OPERATOR` if ACLog returns them and they are not control fields.

### Useful Existing Patterns
- UDP multi-operator support already resolves an incoming ADIF `OPERATOR` field to an ollog user. Phase 66 can borrow normalization ideas without changing the ACLog bridge into cross-user routing.
- Manual sync already has an inline HTMX report and additive-only import semantics.
- Per-user QSO collection routing is already centralized through `get_user_qso_collection(user)`.

</code_context>

<specifics>
## Specific Ideas

- Add a small helper such as `extract_aclog_operator_identity(record: Mapping[str, Any]) -> str | None`.
- Start with candidate fields `OPERATOR`, `STATION_CALLSIGN`, `OWNER_CALLSIGN`, `MY_CALL`, and `MYCALL`, then adjust based on real sample data.
- Return structured dispositions from sync/live import paths: `imported`, `duplicate`, `skipped_missing_operator`, `skipped_unmatched_operator`, and `error`.
- Include a few skipped examples in sync reports only if that matches the existing compact report style and does not expose another operator's full record details.

</specifics>

<deferred>
## Deferred Ideas

- Admin-managed mapping from arbitrary ACLog operator labels to ollog users.
- Preview/review import UI for unmatched records.
- Scheduled sync or background all-bridge reconciliation.
- Updating existing local QSOs from ACLog.

</deferred>

---

*Phase: 66-ACLog Operator Identity Routing*
*Context gathered: 2026-06-16*
