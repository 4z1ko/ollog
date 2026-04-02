# Phase 1: Foundation - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Project skeleton: ADIF parser/serializer, MongoDB QSO schema + indexes, JWT auth service, and Docker Compose setup. No user-visible UI. All correctness decisions for data handling must be locked here — retrofitting them later requires data migration.

</domain>

<decisions>
## Implementation Decisions

### ADIF Parser
- **UTF-8 encoding required throughout** — ADIF byte-length fields must use `len(value.encode('utf-8'))`, not `len(value)`. Non-ASCII characters in NAME, QTH, COMMENT fields will silently corrupt data if `len()` is used.
- Build a custom tag-stream state machine parser (not line-splitter) — the ADIF format has enough real-world variants (missing EOH, case-insensitive field names, whitespace around EOR) that a custom ~100-line parser is safer than a small-ecosystem library whose maintenance status is uncertain.
- Field names normalized to uppercase on parse (ADIF spec: field names are case-insensitive).
- APP_ and USERDEF fields must round-trip losslessly — they are stored verbatim, never dropped.
- Parser errors on a single record should not abort the full file — collect errors per-record, continue parsing.

### MongoDB Schema & Indexes
- ADIF field names stored verbatim as document keys (uppercase: CALL, BAND, MODE, etc.) — no translation layer, no snake_case mapping.
- Shared `qsos` collection with `_operator` as the leading field in all compound indexes (not per-operator collections).
- Compound unique index: `{_operator, CALL, qso_date_utc, BAND, MODE}` — must exist before first write.
- All datetimes stored as UTC-aware. After every MongoDB read, UTC tzinfo is re-attached via a `from_mongo_dt()` utility — never trust PyMongo to preserve tzinfo.
- Soft-deleted QSOs get `_deleted: true` flag; default queries exclude them.

### Auth & JWT
- JWT carries: operator callsign, username, role (operator | admin), expiry.
- Operator callsign is injected from the validated JWT into all QSO queries — never from request body or query params.
- Initial admin account bootstrapped via environment variable or first-run seed script (no web endpoint for admin self-registration).

### Claude's Discretion
- JWT expiry duration
- Exact bcrypt work factor
- Docker Compose service naming conventions
- Health endpoint path and response format
- Python project structure (src layout vs flat)

</decisions>

<specifics>
## Specific Ideas

- UTF-8 is explicitly required — this is the most critical correctness constraint for the parser. All string length calculations must account for multi-byte characters.
- The parser must be testable in isolation with no framework dependencies (pure functions, parse .adi/.adif → Python dicts, serialize Python dicts → .adi).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-04-03*
