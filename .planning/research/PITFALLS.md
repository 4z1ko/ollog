# Domain Pitfalls

**Domain:** Multi-operator ham radio QSO logbook (Python/MongoDB/ADIF)
**Researched:** 2026-04-03
**Confidence note:** WebSearch, WebFetch, and Bash tools were unavailable during this research session. All findings are drawn from training data (knowledge cutoff August 2025) covering ADIF specification behavior, real-world logbook software patterns, MongoDB concurrency patterns, and Python ecosystem. Confidence levels are assigned conservatively.

---

## Critical Pitfalls

Mistakes that cause data loss, silent corruption, or rewrites.

---

### Pitfall 1: ADIF Field Length Is Byte Count, Not Character Count

**What goes wrong:** The ADIF tag format is `<FIELDNAME:N>value` where N is the byte-length of the value in UTF-8, not the number of characters. If a parser or writer uses Python `len(str)` — which counts Unicode code points — it will produce wrong byte counts when the value contains non-ASCII characters (e.g., UTF-8 encoded operator names, QTH strings, comments). Readers that trust the length field will silently truncate or misparse subsequent fields.

**Why it happens:** Python 3 strings are Unicode by default. Developers assume `len()` is sufficient and don't think about encoding. ADIF files from non-English-locale software (JA, EU contesters) routinely contain non-ASCII in NAME, QTH, COMMENT, and NOTE fields.

**Consequences:** Silent data corruption on import/export. Other logbook software truncates records at the wrong byte boundary. Corrupted exports that pass no validation but lose data.

**Prevention:**
- Always compute length as `len(value.encode('utf-8'))` when writing ADIF tags.
- When parsing, read exactly N bytes after the `>`, then decode; do not use string slicing before decoding.
- Add a round-trip test: import a file with multi-byte UTF-8 values, export, re-import, assert equality.

**Detection:** A NAME field like "Jörg" will have `len()` = 4 but byte length = 5. Unit test with a fixture containing `ä`, `ö`, `ü`, `é`, or CJK characters.

**Phase:** ADIF import/export foundation (earliest phase touching file I/O).

---

### Pitfall 2: QSO_DATE and TIME_ON Are Separate Fields With No Timezone Indicator — And Operators Often Log Local Time

**What goes wrong:** ADIF stores date as `QSO_DATE` (YYYYMMDD) and time as `TIME_ON` / `TIME_OFF` (HHMM or HHMMSS) with no timezone field. The ADIF spec requires UTC, but a significant fraction of real-world ADIF files exported from consumer logging software contain local time — especially files from operators in non-UTC timezones who didn't configure their logger correctly. Storing these as-is and treating them as UTC silently poisons every downstream calculation: duplicate detection, DXCC credit, contest exchange validation, award tracking.

**Why it happens:** The spec is clear but enforcement is absent. Popular logging programs (Log4OM, DXKeeper, older versions of Ham Radio Deluxe) have had bugs or defaults that export local time. Users don't notice because their own display looks right.

**Consequences:**
- Duplicate detection fails (same QSO appears as two different records offset by timezone delta).
- Export to LoTW/eQSL rejects or mismatches QSOs.
- Multi-operator logbook shows ops making QSOs "before" each other when times don't align.
- Band/time overlap detection for contest logs is wrong.

**Prevention:**
- Store all timestamps in MongoDB as UTC `datetime` objects, never as bare strings.
- During import: warn the user if `TIME_ON` values cluster suspiciously away from UTC (e.g., nearly all QSOs at XX:00-XX:59 local business hours — not typical of ham radio patterns).
- Provide an import wizard option: "This file may be in local time — apply UTC offset?" with timezone picker.
- Never store the raw ADIF date/time strings as the canonical record. Normalize to a single `datetime` field at ingest.
- On export, always reconstruct `QSO_DATE` and `TIME_ON` from the stored UTC datetime.

**Detection:** If imported QSOs show times clustering in the 08:00–22:00 range for a callsign in UTC-5 without any QSOs in 23:00–07:00, suspect local time. Flag this in the import validation report.

**Phase:** Data model design (must be decided before first QSO is persisted).

---

### Pitfall 3: No Authoritative Duplicate Detection Strategy Causes Both False Positives and False Negatives

**What goes wrong:** Duplicate QSO detection is deceptively hard. The naive approach — check exact match on (CALL, QSO_DATE, TIME_ON, BAND, MODE) — produces false negatives when time is off by one minute (logging delay, time sync drift) and false positives when the same station is worked twice on the same band/mode in a short contest window (perfectly valid). More subtle: if two operators in a multi-op setup both log the same contact (e.g., both hear the QSO on split), you get a real duplicate that the naive key won't catch because the CALL+TIME+BAND+MODE match exactly.

**Why it happens:** Developers copy the most obvious key and ship it. The edge cases only emerge from real import data.

**Consequences:**
- Users import their existing logs and get thousands of false positives, lose trust in the system.
- Real duplicates (multi-op same-contact logging) slip through and inflate QSO counts for awards.
- LoTW and ARRL award submissions with duplicate QSOs cause credit reversals.

**Prevention:**
- Define a configurable fuzzy window (default: ±2 minutes) for time matching during import deduplication.
- Treat (CALL, BAND, MODE, datetime within window) as a "probable duplicate" requiring confirmation, not auto-deletion.
- For multi-op systems: add an `operator` field to every QSO and make the same-contact problem explicit in the data model. A QSO logged by two operators in the same session is a data integrity violation that needs a dedicated resolution flow, not silent deduplication.
- Expose a dedupe report on import, let the operator decide.
- Store `import_source` and `import_batch_id` on every imported QSO to enable full rollback of a bad import.

**Detection:** After import, run a query for QSOs within 2-minute windows of each other on the same band/mode to the same callsign. Surface this as an import report, not a silent filter.

**Phase:** Import pipeline and data model (before allowing imports from multiple operators).

---

### Pitfall 4: ADIF Enumeration Values Are Case-Insensitive in Spec, But Real Files Use Mixed Case — Validation Must Normalize Before Rejecting

**What goes wrong:** The ADIF spec defines enumeration values for BAND (40m, 20m, etc.) and MODE (SSB, CW, FT8, etc.) but explicitly states field names and enumeration values are case-insensitive. Real-world files contain `FT8`, `ft8`, `Ft8`, `SSB`, `ssb`, `USB` (which is not a valid ADIF mode — it maps to SSB), `PHONE` (not valid — maps to SSB), `PSK31` (not a valid ADIF mode — should be PSK with submode PSK31). Strict validation that rejects on case or non-canonical aliases will reject valid real-world data.

**Why it happens:** Different logging software uses different internal representations. HRD historically used `USB`/`LSB`. WSJT-X uses `FT8` correctly, but older WSPR exports used non-standard mode strings.

**Consequences:**
- Overly strict import rejects files from valid software that users have years of history in.
- Overly loose import stores junk mode strings that break downstream award lookups (DXCC band/mode credits require canonical values).

**Prevention:**
- Build a normalization map before validation: `USB → SSB`, `LSB → SSB`, `PHONE → SSB`, `PSK31 → PSK (submode: PSK31)`, `JT65A → JT65`, etc.
- Normalize to canonical ADIF 3.x values at ingest time, store normalized value plus original in `mode_raw` field.
- Apply case normalization (uppercase) before any enum lookup.
- Log all normalizations applied during import in the import report.
- Define the normalization map as a data file (not hardcoded), so it can be updated as new modes emerge without a code deploy.

**Detection:** During import dry-run, count MODE values that don't match canonical list before normalization vs. after. If a large percentage require normalization, warn the user their source software uses non-standard values.

**Phase:** ADIF import pipeline (before data model is finalized — normalization must be part of the schema contract).

---

### Pitfall 5: MongoDB Without a Compound Unique Index on QSO Identity Fields Allows Silent Duplicates at Scale

**What goes wrong:** Application-layer duplicate checking (check then insert) has a race condition in concurrent multi-operator scenarios. Two operators import simultaneously; both check for a duplicate, both find none, both insert — resulting in duplicate documents. MongoDB's document model has no built-in foreign key or uniqueness constraint unless you create an explicit unique index.

**Why it happens:** Developers add duplicate-check logic in the service layer and never add the database-level constraint, assuming application logic is sufficient. Under light single-user load it works. Under concurrent imports it fails.

**Consequences:**
- Silent duplicate QSOs that inflate award counts and confuse operators.
- Dedupe is now a data-repair operation, not a prevention operation.
- If QSO IDs are used in external references (LoTW sync state, eQSL match), duplicates cause cascading reference corruption.

**Prevention:**
- Create a MongoDB compound unique index on the natural QSO key: `{owner_id, call, qso_date_utc, band, mode}`. Use a partial unique index if the time-window fuzzy logic is not practical at DB level.
- Use MongoDB's `update_one` with `upsert=True` and the natural key as the filter for all inserts, not `insert_one`. This is atomic and idempotent.
- For imports: use bulk `update_many` with `upsert=True` rather than per-document checks.
- Accept that the unique index will reject some legitimate same-band/same-mode contacts within the same minute; surface these as "requires manual review" rather than silently failing.

**Detection:** After any concurrent import test, run `db.qsos.aggregate([{$group: {_id: {owner, call, date, band, mode}, count: {$sum:1}}}, {$match: {count: {$gt:1}}}])` — if count > 0, the constraint is missing.

**Phase:** Data model design (index must exist before first production write).

---

### Pitfall 6: ADIF Header Is Optional But Many Parsers Choke on Its Absence or Presence

**What goes wrong:** An ADIF file may or may not have a header block (text before the first `<EOH>` tag). If `<EOH>` is absent, the entire file is records. If `<EOH>` is present, everything before it is header. Parsers that always expect `<EOH>` reject valid header-less files. Parsers that treat the absence of `<EOH>` as "no header" will misparse files where the generator emitted a header without `<EOH>` (which is a spec violation but happens in the wild). Additionally, some generators include a free-text preamble before any tags — lines of comments before `<ADIF_VER:3>3.1.0` — which a strict parser treats as invalid.

**Why it happens:** The "optional header" rule is ambiguous in practice. Generators like the built-in export of some contest logging software omit `<EOH>` when there are no header fields.

**Consequences:** Import fails entirely for valid real-world files. Users see a cryptic parse error and give up.

**Prevention:**
- Treat any text before the first `<` as a free-text preamble — ignore it, don't error on it.
- If no `<EOH>` is found after scanning all tags, treat the file as header-less and parse all tags as records.
- Test against: (a) file with full header + `<EOH>`, (b) file with `<EOH>` but no header tags, (c) file with no `<EOH>` at all, (d) file with multi-line text preamble before first tag.

**Detection:** Maintain a corpus of at least 10 real-world ADIF files from different generators (HRD, Log4OM, WSJT-X, N1MM, MacLoggerDX, CQRLOG) as integration test fixtures. Run all against the parser before each release.

**Phase:** ADIF parser implementation (foundational; must be correct before any other logic builds on it).

---

## Moderate Pitfalls

---

### Pitfall 7: ADIF `<EOR>` Whitespace and Line-Ending Variations

**What goes wrong:** End-of-record tag `<EOR>` may be followed by `\n`, `\r\n`, multiple blank lines, or nothing. Some generators put `<EOR>` mid-line after other fields on the same line. Parsers that split on newlines before parsing tags will misparse records where fields and `<EOR>` share a line. ADIF is explicitly a tag-stream format, not a line-oriented format — treat it as such.

**Prevention:** Write the parser as a state machine over the raw character stream, not as a line-splitting operation. Tags delimit records; newlines are irrelevant whitespace.

**Phase:** ADIF parser (foundational).

---

### Pitfall 8: `TIME_OFF` Is Often Missing — Don't Require It

**What goes wrong:** `TIME_OFF` (end time of QSO) is optional in the ADIF spec, and the majority of real-world files omit it. Systems that require `TIME_OFF` for storage or display break on standard exports from nearly all logging software.

**Prevention:** Make `TIME_OFF` optional in the data model. Default to `None`/`null`. Never use `TIME_OFF` in duplicate detection logic unless `TIME_ON` is also present and the two bracket the suspect contact.

**Phase:** Data model design.

---

### Pitfall 9: Frequency vs. Band — Real Files Have Both, Conflicting, or Neither

**What goes wrong:** ADIF has both `FREQ` (in MHz, e.g., `14.225`) and `BAND` (e.g., `20m`). The spec says if both are present they should be consistent. Real files have: only FREQ and no BAND, only BAND and no FREQ, both where FREQ doesn't map to the stated BAND (e.g., FREQ=14.225 with BAND=15m — a typo or export bug), and neither (rare but possible from broken exports). Systems that require BAND will reject FREQ-only files; systems that blindly store both will have inconsistent band data that breaks award tracking.

**Prevention:**
- At ingest, normalize: if BAND is missing but FREQ is present, derive BAND from FREQ using the standard ITU ham band plan.
- If both are present and inconsistent, use FREQ as authoritative (it's more specific), derive BAND from it, and log the discrepancy.
- Store the derived `band` as the canonical field; store `freq_mhz` as a supplementary field.
- Build the FREQ-to-BAND mapping as a data table (not hardcoded conditionals) to accommodate 60m, 630m, 2200m, and future allocations.

**Detection:** After import, run a query for QSOs where `band` is null or empty string. Any such records indicate missing both FREQ and BAND — flag for operator review.

**Phase:** Import normalization pipeline.

---

### Pitfall 10: Multi-Operator Station Callsign vs. Operator Callsign Confusion

**What goes wrong:** In a multi-op setup, `STATION_CALLSIGN` (the call used on the air, often a club or contest call) differs from `OPERATOR` (the individual's callsign). Many single-op logging programs only populate `CALL` (the contacted station) and don't emit `STATION_CALLSIGN` or `OPERATOR` at all. When you import such a file into a multi-op system, you can't determine which operator made the QSO from the ADIF fields alone — the account performing the import is the only attribution available.

**Prevention:**
- Add an `imported_by_operator_id` field on every QSO document.
- During import, if `OPERATOR` field is absent in the ADIF, attribute to the importing account.
- Never derive operator attribution solely from ADIF fields — treat it as advisory, not authoritative.
- Expose an "import as" option in the UI for admins to import on behalf of a specific operator.

**Phase:** Multi-operator account system (before import is available to operators).

---

### Pitfall 11: MongoDB `datetime` Naive vs. Aware Objects — PyMongo Strips Timezone Info

**What goes wrong:** PyMongo stores Python `datetime` objects. If you pass a timezone-aware `datetime` (with tzinfo=UTC), PyMongo strips the tzinfo and stores it as naive UTC in BSON. When you read it back, you get a naive `datetime` — which Python treats as "local time" in some contexts, causing incorrect comparisons with timezone-aware datetimes elsewhere in the application. This creates a silent timezone corruption bug that only manifests in time-comparison logic.

**Prevention:**
- Establish a codebase-wide convention: all `datetime` objects in the application layer are UTC-aware (`datetime.timezone.utc`).
- After reading from MongoDB, immediately re-attach UTC tzinfo: `dt.replace(tzinfo=timezone.utc)`.
- Write a utility function `from_mongo_dt(dt) -> datetime` that handles this consistently.
- Never compare a naive datetime to an aware datetime; set up a linter rule or add a type guard.

**Detection:** A unit test that stores a UTC-aware datetime, reads it back, and asserts `dt.tzinfo is not None` will catch this immediately.

**Phase:** Data access layer (before any timestamp logic is written).

---

### Pitfall 12: ADIF `APP_` (Application-Defined) Fields Are Silently Lost on Round-Trip

**What goes wrong:** Many logging programs write `APP_FIELDNAME` tags to embed software-specific data (e.g., `APP_HRDDM_LOGID`, `APP_N1MM_POINTS`, `APP_WSJT_SNRATIO`). These are valid ADIF. A parser that only handles known fields drops them silently. The user imports their HRD log, loses all the HRD internal IDs, then exports and re-imports back into HRD — all HRD-internal cross-references are gone.

**Prevention:**
- Store all unrecognized `APP_` fields in a MongoDB subdocument: `app_fields: {"HRDDM_LOGID": "12345", ...}`.
- On export, emit all stored `APP_` fields back into the ADIF output.
- This is a lossless round-trip guarantee that users with existing software will rely on.

**Detection:** Import a real HRD or N1MM export file, export it back to ADIF, diff the `APP_` fields between input and output.

**Phase:** ADIF parser and exporter (before first public import feature).

---

### Pitfall 13: ADIF `USERDEF` (User-Defined) Fields Are a Different Mechanism From `APP_` Fields

**What goes wrong:** ADIF 3.x added `USERDEF` fields defined in the header (`<USERDEF1:N:T>fieldname`). These are different from `APP_` prefixed fields but serve a similar purpose. Parsers that handle `APP_` but ignore `USERDEF` header definitions will fail to properly parse `USERDEF`-style fields in the record body (they may appear as unknown tags without the `APP_` prefix). This is a less common case but appears in exports from software that adopted ADIF 3.x extensions.

**Prevention:**
- Parse the header to extract `USERDEF` definitions before parsing records.
- Store `USERDEF` values similarly to `APP_` fields — in a subdocument that round-trips.

**Phase:** ADIF parser (after basic parsing works, before claiming ADIF 3.x compliance).

---

### Pitfall 14: REST API Returns Full QSO Documents — Pagination Not Added Until It's a Performance Crisis

**What goes wrong:** A logbook endpoint returns all QSOs for a given operator. Works fine at 500 QSOs. At 50,000 QSOs (active DXer after 2 years) the response is 15+ MB, the browser tab hangs, and the server memory spikes. Pagination is retrofitted under pressure, which breaks any client that assumed full-list responses.

**Prevention:**
- Implement cursor-based pagination from day one on every QSO list endpoint. Default page size 100, max 500.
- Add a `total_count` field in the response envelope from the start so clients can show "showing 1-100 of 12,450".
- Index MongoDB on `{owner_id: 1, qso_date_utc: -1}` (the default sort) from the start.

**Phase:** REST API design (foundational; changing pagination contract after clients are built is costly).

---

## Minor Pitfalls

---

### Pitfall 15: ADIF Field Name Matching Must Be Case-Insensitive

**What goes wrong:** ADIF field names like `<CALL:5>` and `<call:5>` are equivalent per spec. Parsers that use dict lookups with case-sensitive keys will fail on files from generators that use lowercase or mixed-case tag names (e.g., some CQRLOG versions emit lowercase tags).

**Prevention:** Normalize all field names to uppercase immediately on parsing. Use `field_name.upper()` before any lookup or storage.

**Phase:** ADIF parser.

---

### Pitfall 16: Concurrency on Import — Don't Process Large Files Synchronously in the Request Handler

**What goes wrong:** A 10,000 QSO ADIF file takes 5–30 seconds to parse and insert. Processing it synchronously in the API request handler ties up the worker for that entire time, blocking other operators and causing HTTP timeouts. Users retry, causing duplicate import attempts.

**Prevention:**
- Accept the uploaded file, validate it superficially (magic bytes, file size limit), enqueue an async job, return a `202 Accepted` with a job ID.
- Use Celery + Redis or similar for the async worker.
- Provide a `/imports/{job_id}/status` polling endpoint.
- Design idempotency: re-submitting the same file should detect the in-progress import and not start a second one (hash the file content on receipt).

**Phase:** Import pipeline (before allowing file uploads larger than a few hundred QSOs).

---

### Pitfall 17: LoTW and eQSL Sync State Must Be Stored Per-QSO, Not Per-Import-Batch

**What goes wrong:** Operators want to know which QSOs have been confirmed via LoTW or eQSL. Some systems store "this batch was uploaded to LoTW on date X" but not per-QSO confirmed status. When a QSO is edited or re-imported, the sync state becomes ambiguous. LoTW confirmation is per-QSO (LOTW_QSL_RCVD field in ADIF), not per-batch.

**Prevention:**
- Store `lotw_qsl_sent`, `lotw_qsl_rcvd`, `eqsl_qsl_sent`, `eqsl_qsl_rcvd` as first-class fields on the QSO document.
- These are standard ADIF fields — preserve them on import.
- On export for LoTW upload, emit the correct ADIF subset and mark `lotw_qsl_sent` = "Y" on those documents.

**Phase:** Data model (must be in initial schema; hard to retrofit cleanly).

---

### Pitfall 18: Gridsquare / Maidenhead Locator Validation Is Non-Trivial

**What goes wrong:** GRIDSQUARE field accepts Maidenhead locator strings (e.g., `FN31`, `FN31pr`). Validation that only checks length will pass garbage values. The Maidenhead system has specific character rules: positions 1-2 are letters A-R, positions 3-4 are digits 0-9, positions 5-6 are letters A-X. Files with `GRIDSQUARE:4>????` or truncated grids from buggy software are common. Storing invalid grids breaks map display and distance calculations.

**Prevention:**
- Validate with a regex: `^[A-Ra-r]{2}[0-9]{2}([A-Xa-x]{2}([0-9]{2})?)?$`
- On failure: store the raw value in `gridsquare_raw`, set `gridsquare` to null, flag for operator review.

**Phase:** Import normalization.

---

### Pitfall 19: MongoDB Atlas Free Tier Has 512 MB Storage — Plan for Data Volume Early

**What goes wrong:** Each QSO document with all ADIF fields stored is roughly 1–2 KB. An active DXer may have 50,000+ QSOs. 50,000 × 2 KB = 100 MB per operator. With multiple operators and import of historical logs, Atlas free tier fills up silently and starts rejecting writes with opaque errors.

**Prevention:**
- If using Atlas free tier in development: set up storage alerts.
- In production: use paid tier or self-hosted MongoDB from the start if multi-operator scale is expected.
- Don't store binary blobs (audio, images) in QSO documents; use GridFS or external object storage.

**Phase:** Infrastructure planning (before going to production).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| ADIF parser implementation | Header optional / EOH missing (Pitfall 6); case-insensitive fields (Pitfall 15); byte vs. char length (Pitfall 1) | Build from tag-stream state machine, not line splitter; test with real-world corpus |
| Data model design | UTC datetime naive/aware (Pitfall 11); band vs. freq (Pitfall 9); LoTW fields omitted (Pitfall 17); pagination missing (Pitfall 14) | Define schema contract before writing any queries; all datetimes UTC-aware |
| Import pipeline | Duplicate detection race condition (Pitfall 3, 5); async required for large files (Pitfall 16); normalization before validation (Pitfall 4) | Compound unique index before first import; async job queue from day one |
| Multi-operator accounts | Operator attribution from ADIF vs. account (Pitfall 10); concurrent write safety (Pitfall 5) | `imported_by_operator_id` on every QSO; upsert not insert |
| ADIF export | APP_ fields dropped (Pitfall 12); byte length on write (Pitfall 1); time from UTC (Pitfall 2) | Round-trip test suite; normalize on read AND write |
| LoTW/eQSL integration | Sync state per-batch vs. per-QSO (Pitfall 17) | Per-QSO fields in initial schema |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| ADIF parsing gotchas | MEDIUM-HIGH | ADIF spec behavior is well-documented in training data; real-world file quirks corroborated by multiple open-source parser implementations (adif-parsepy, cabrillo, etc.) |
| UTC/timezone pitfalls | HIGH | Standard Python/MongoDB datetime hazard; well-documented across community |
| Duplicate detection complexity | HIGH | Known hard problem in ham radio; documented in LoTW and ARRL documentation patterns |
| MongoDB concurrency | HIGH | Standard check-then-insert race condition; well-understood |
| LoTW/eQSL sync model | MEDIUM | Based on ADIF field definitions and LoTW documentation patterns; specific API behavior not verified |
| Atlas storage limits | MEDIUM | Figures approximated; verify current Atlas tier limits before committing to free tier |

---

## Sources

- ADIF specification knowledge (training data, knowledge cutoff August 2025) — HIGH confidence for spec-defined behaviors
- PyMongo documentation patterns — HIGH confidence for datetime stripping behavior
- Real-world ADIF parser implementations (adif-parsepy, ham-tools, python-adif-io) — MEDIUM confidence, cross-referenced mentally from training data
- MongoDB upsert/unique index patterns — HIGH confidence (standard MongoDB documentation)
- Note: External verification (ADIF.org spec, PyMongo docs, MongoDB docs) was not possible in this session due to tool unavailability. Flag for validation before implementation decisions are finalized.
