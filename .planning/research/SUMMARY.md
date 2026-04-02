# Project Research Summary

**Project:** Ham Radio Online Logbook (ollog)
**Domain:** Multi-operator ADIF-native web logbook
**Researched:** 2026-04-03
**Confidence:** MEDIUM (all research from training data; external tool access blocked during session)

## Executive Summary

ollog is a web-native, multi-operator ham radio QSO logbook with ADIF as the central data contract. The key architectural insight from research is that ADIF field names should be stored verbatim as MongoDB document keys — no translation layer, no snake_case mapping. This eliminates an entire class of import/export bugs and makes round-trip fidelity trivial. The recommended stack is FastAPI + Motor + Beanie (Python async throughout), with HTMX + Jinja2 for the UI, deployed via Docker Compose with Caddy for automatic TLS. This is a layered monolith with clean internal component boundaries, not microservices.

The market gap this project fills is real: there is no well-supported, modern, web-native, multi-operator logbook with a clean REST API that is not either self-hosted PHP (CloudLog) or tightly coupled to a commercial callsign registry (QRZ). The closest analog is CloudLog, which has a dated UI, complex self-hosting, and a PHP stack. ollog's differentiator is a clean Python API, ADIF-native data model, and first-class multi-operator support from day one.

The dominant risk category is data integrity, not technical complexity. Operators will not migrate logs to a system they cannot trust. The most dangerous pitfalls — ADIF byte-vs-character length corruption, UTC datetime naive/aware mixing, and silent duplicate insertion under concurrent load — must be addressed at the foundation before any user-facing features are built. Getting the ADIF parser, MongoDB schema, and duplicate detection right in phase 1 is more important than shipping a UI quickly.

---

## Key Findings

### Recommended Stack

The stack is Python-first and async throughout. FastAPI is the correct framework choice: async-native, Pydantic v2 for ADIF field validation at the boundary, and automatic OpenAPI docs. Motor (async MongoDB driver) is mandatory — using PyMongo (sync) inside async FastAPI handlers causes thread-pool exhaustion. Beanie ODM on top of Motor reduces boilerplate significantly for a project of this size. For the UI, HTMX + Jinja2 delivers full interactivity without a JavaScript build pipeline, which is right-sized for a CRUD logbook. Docker Compose with Caddy (automatic HTTPS) is the deployment target.

ADIF library selection carries LOW confidence: both `adif-io` and `adif3` are small ecosystem libraries whose maintenance status needs PyPI verification at project start. The ADIF format is simple enough (~100 lines of Python) that a custom parser is a viable fallback, and given the critical pitfalls identified in parsing (see below), a custom parser may be preferable anyway.

**Core technologies:**
- Python 3.12 + FastAPI 0.111+: async-native API framework with automatic OpenAPI and Pydantic v2 validation
- Motor 3.x + Beanie 1.x: async MongoDB driver and ODM; Beanie eliminates query boilerplate
- MongoDB 7.x: document model maps 1:1 to ADIF flat records; no schema migration pain for new ADIF fields
- python-jose + passlib[bcrypt]: JWT auth with bcrypt password hashing; callsign from JWT scopes all queries
- HTMX 1.9+ + Jinja2 3.x: interactive UI without a JS build pipeline; TailwindCSS via CDN for styling
- Docker + Docker Compose + Caddy: single-command self-hosted deployment with automatic TLS

**Version verification required before kickoff:** `adif-io`, `adif3`, `mongomock-motor`, `python-jose` (check CVEs), FastAPI current stable version.

### Expected Features

**Must have (table stakes):**
- Manual QSO entry form (CALL, QSO_DATE, TIME_ON, BAND, FREQ, MODE, RST_SENT, RST_RCVD)
- Per-operator logbook scoped by callsign
- ADIF import (.adi/.adif) with duplicate detection and lossless N+1 field passthrough
- ADIF export with full round-trip fidelity (no field loss)
- QSO list view with pagination, sort, and filter (callsign, date range, band, mode)
- Duplicate QSO detection (fuzzy ±2 min window, not exact match)
- UTC date/time handling everywhere
- DXCC entity derivation using cty.dat (no external API dependency)
- QSO count and basic per-operator statistics
- Admin account management UI
- Multi-operator concurrent write safety
- QSO editing and soft-delete with confirmation

**Should have (differentiators):**
- Real-time multi-operator visibility (WebSocket/SSE — the primary differentiator over single-user logbooks)
- Band/mode statistics dashboard with charts
- QSO confirmation status display (LOTW_QSL_SENT/RCVD, EQSL fields)
- Per-operator activity log/audit trail
- Flexible QSO editing with clean UX
- APP_ field passthrough (preserves HRD, N1MM, WSJT-X internal IDs on round-trip)
- QSO notes/comment field (ADIF COMMENT and NOTES)

**Defer (v2+):**
- LoTW direct upload integration (TQSL certificate management per-operator is operationally complex)
- Callsign lookup via QRZ XML / HamQTH (external API dependency; adds signup friction)
- CSV export (easy addition, not urgent)
- Award tracking (DXCC, WAS, VUCC) — complex rule sets, a separate product concern

### Architecture Approach

The architecture is a layered service-oriented monolith: Web UI (thin) → REST API + Auth → MongoDB, with ADIF Library and Import/Export Services as internal modules. The two hard constraints that keep the architecture clean: the UI never touches MongoDB directly, and the ADIF Library never touches MongoDB. Operator isolation is enforced by injecting the callsign from the JWT at the auth boundary — it never comes from user-supplied request data. The shared `qsos` collection with `_operator` as the leading field in all compound indexes is the correct multi-tenancy model (not per-operator collections, which create operational problems).

**Major components:**
1. ADIF Library (`app/adif/parser.py`) — pure functions, parse .adi/.adif to Python dicts and back; no framework dependencies; fully testable in isolation
2. Auth Service — JWT issuance/validation, callsign-to-account binding, admin role check; single enforcement point for operator identity
3. QSO API — CRUD endpoints, enforces operator isolation via `_operator` injection, validates ADIF fields
4. Import Service — multipart file upload, batch insert with `ordered=False`, returns summary with accepted/rejected/errors
5. Export Service — query by operator + optional filters, streaming response to avoid memory spikes on large logs
6. Admin API — user/account management; no QSO logic
7. Web UI — form-based QSO entry, log view, import/export triggers, admin panel; consumes REST API only

**Recommended build order:** ADIF Library → MongoDB Schema + Indexes → Auth Service → QSO API → Import Service → Export Service → Admin API → Web UI.

### Critical Pitfalls

1. **ADIF byte-vs-character length** — Use `len(value.encode('utf-8'))` not `len(value)` when writing ADIF tags. UTF-8 multi-byte characters (common in European operator names/QTH) cause silent data corruption if `len()` is used. Add a round-trip test with non-ASCII fixtures before shipping.

2. **UTC datetime naive/aware mixing in PyMongo** — PyMongo strips tzinfo when storing datetime objects. Establish a codebase-wide convention: all datetimes are UTC-aware. After every MongoDB read, re-attach UTC tzinfo via a utility function `from_mongo_dt()`. A unit test that stores and reads back a UTC-aware datetime will catch this immediately.

3. **Concurrent duplicate insertion race condition** — Application-layer check-then-insert has a race condition under concurrent imports. Requires a MongoDB compound unique index on `{_operator, CALL, qso_date_utc, BAND, MODE}` plus `upsert=True` (not `insert_one`) for all QSO writes. The index must exist before the first production write.

4. **Duplicate detection false positives/negatives** — Exact-match on (CALL, QSO_DATE, TIME_ON, BAND, MODE) produces both false positives (same station worked twice in a contest) and false negatives (same QSO with 1-minute time drift). Use configurable fuzzy window (default ±2 min), surface a dedup report for operator review, never auto-delete.

5. **ADIF parser correctness** — The ADIF header is optional; `<EOH>` may be absent; `<EOR>` whitespace varies; field names are case-insensitive; `APP_` and `USERDEF` fields must round-trip. Write the parser as a tag-stream state machine (not line-splitter). Test against a corpus of real-world files from HRD, Log4OM, WSJT-X, N1MM, MacLoggerDX, CQRLOG before claiming any ADIF compliance.

---

## Implications for Roadmap

Based on research, the architecture's build-order dependency chain and the data-integrity-first imperative suggest this phase structure:

### Phase 1: Foundation — ADIF Library, Data Model, and Auth

**Rationale:** The ADIF Library and MongoDB schema are the foundation everything else builds on. Both must be correct before any QSO data is persisted. Auth is required before any endpoint can be protected. This phase has no user-visible UI but produces the entire skeleton.

**Delivers:** Correct ADIF parser + serializer (with full round-trip test suite), MongoDB schema with all required indexes (including the compound unique index for dedup), Auth Service with JWT issuance and callsign scoping.

**Addresses:** Manual QSO entry prerequisite, per-operator logbook scoping, admin account model

**Avoids:** Pitfall 1 (byte/char length), Pitfall 2 (UTC datetime), Pitfall 5 (concurrent duplicate insertion), Pitfall 6 (ADIF header variants), Pitfall 11 (naive datetime from PyMongo), Pitfall 15 (case-insensitive field names)

**Research flag:** Needs verification of ADIF library maintainership (`adif-io`, `adif3`) before committing to a library vs. custom parser decision.

---

### Phase 2: Core QSO API and Log View

**Rationale:** With the foundation in place, build the QSO CRUD API and the basic log view. This is the first phase with user-visible functionality. Pagination must be built from day one — retrofitting it breaks API contracts.

**Delivers:** QSO CRUD endpoints (POST, GET, PATCH, DELETE with soft-delete), paginated and filterable log view (callsign, date range, band, mode), basic per-operator QSO count, manual QSO entry web form.

**Addresses:** Manual QSO entry, QSO list view with pagination, search/filter, QSO editing, soft-delete with confirmation, UTC display, band/mode fields, RST fields

**Avoids:** Pitfall 14 (pagination missing until it's a crisis), Pitfall 4 (mode/band normalization on entry)

**Uses:** FastAPI + Motor/Beanie, HTMX + Jinja2 for form and list view

---

### Phase 3: ADIF Import and Export

**Rationale:** Import is the trust-building feature. Operators evaluate any logbook by importing their existing log. If import is lossy or slow, they leave. Export must be equally correct — operators use ADIF exports for LoTW uploads and software migrations. These two features share the ADIF Library from Phase 1 and build on the QSO API from Phase 2.

**Delivers:** ADIF file upload with async processing (202 Accepted + job status polling), duplicate detection with fuzzy window and import report, lossless N+1 / APP_ field passthrough, ADIF export with streaming response and optional filters, import rollback via import_batch_id.

**Addresses:** ADIF import, ADIF export, duplicate detection, N+1 field passthrough, APP_ field round-trip

**Avoids:** Pitfall 3 (duplicate detection strategy), Pitfall 4 (ADIF enumeration normalization), Pitfall 9 (FREQ vs BAND derivation), Pitfall 12 (APP_ field loss), Pitfall 16 (sync import blocks worker), Pitfall 7 (EOR whitespace), Pitfall 8 (TIME_OFF optional)

**Research flag:** Needs validation of async job queue choice (Celery + Redis vs. FastAPI BackgroundTasks vs. RQ) — for self-hosted deployments, adding Redis is an operational burden; FastAPI BackgroundTasks may be sufficient for typical file sizes.

---

### Phase 4: Multi-Operator and Admin

**Rationale:** Multi-operator concurrent safety is built into the data model from Phase 1, but the operator attribution, admin UI, and account management features are grouped here. Real-time visibility (WebSocket) is the primary differentiator and belongs in its own phase after the write path is proven.

**Delivers:** Admin UI for account creation/disable/reset, operator attribution on all QSOs (`imported_by_operator_id`), multi-operator concurrent write safety validation, basic DXCC entity derivation from cty.dat.

**Addresses:** Admin user management, multi-operator logging, operator attribution from import, DXCC entity display

**Avoids:** Pitfall 10 (STATION_CALLSIGN vs OPERATOR confusion on import)

---

### Phase 5: Real-Time Visibility and Statistics

**Rationale:** Real-time multi-operator visibility (seeing other operators' QSOs appear without page refresh) is the primary differentiator over single-user logbooks and CloudLog. It belongs after the write path is stable. Statistics dashboard is low-risk (reads only) and grouped here as a natural companion.

**Delivers:** WebSocket or SSE live QSO feed per station/session, band/mode/time statistics dashboard, QSO confirmation status display (LOTW_QSL_SENT/RCVD, EQSL fields).

**Addresses:** Real-time multi-operator visibility, statistics dashboard, QSO confirmation status

**Avoids:** Pitfall 17 (LoTW sync state per-QSO, not per-batch — fields must be in schema from Phase 1)

**Research flag:** WebSocket vs SSE tradeoff in FastAPI for this use case; also whether Beanie's watch/change-stream support is sufficient or requires raw Motor.

---

### Phase Ordering Rationale

- The ADIF Library must precede everything that touches QSO data — parser correctness cannot be retrofitted without data migration risk.
- The compound unique index (Pitfall 5) and UTC datetime convention (Pitfall 11) must exist before the first production write. No exceptions.
- Import/Export (Phase 3) depends on a stable QSO API contract (Phase 2) so the import pipeline writes through the same validation logic as manual entry.
- Real-time features (Phase 5) are intentionally last — concurrent write safety from the data model handles the correctness requirement; the visibility layer is additive.
- Admin and operator management (Phase 4) is placed before real-time because it establishes the account model that WebSocket sessions will authenticate against.

### Research Flags

Phases needing deeper research during planning:
- **Phase 1:** Verify ADIF library maintainership on PyPI (`adif-io`, `adif3`) before choosing library vs. custom parser. Custom is ~100 lines and avoids a dependency risk — lean toward custom given the parser correctness requirements documented in PITFALLS.md.
- **Phase 3:** Validate async job queue choice for import. For self-hosted Docker deployments, adding Redis/Celery is a non-trivial operational dependency. Research whether FastAPI BackgroundTasks + status polling is sufficient for expected file sizes (most operator logs are under 50,000 QSOs).
- **Phase 5:** Research FastAPI WebSocket patterns for multi-operator live feed; verify Beanie/Motor change stream support.

Phases with standard patterns (can skip `/gsd:research-phase`):
- **Phase 2:** Standard FastAPI CRUD with pagination — well-documented, no novel patterns.
- **Phase 4:** Standard admin panel CRUD with HTMX — well-documented. DXCC lookup from cty.dat is a solved problem with multiple Python implementations.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | Core choices (FastAPI, Motor, MongoDB, Docker) are solid. ADIF library selection is LOW — verify on PyPI before kickoff. python-jose should be checked for CVEs. |
| Features | HIGH | ADIF spec is stable. Ham radio logbook feature expectations are well-established across QRZ, CloudLog, LoTW documentation. Competitive landscape should be spot-checked on current product pages. |
| Architecture | MEDIUM-HIGH | ADIF-as-internal-format and shared-collection multi-tenancy are strong, well-reasoned recommendations. Specific FastAPI/Beanie integration patterns should be validated against current docs. |
| Pitfalls | MEDIUM-HIGH | ADIF parsing gotchas and MongoDB concurrency hazards are well-documented. UTC/datetime issues are a known Python/PyMongo problem. ADIF byte-length issue is spec-defined and verifiable. |

**Overall confidence:** MEDIUM — sufficient to begin implementation with the phase structure above. The main uncertainty is ADIF library maintainership and async job queue choice for import, both of which should be resolved before Phase 1 and Phase 3 planning respectively.

### Gaps to Address

- **ADIF library selection:** Verify `adif-io` and `adif3` on PyPI before Phase 1. If both are unmaintained or have correctness issues, build a custom parser — the PITFALLS research makes clear it needs to be a tag-stream state machine anyway, which a maintained library may not be.
- **Async import job queue:** Before Phase 3 planning, decide whether to accept Redis/Celery as a Docker Compose service dependency or stay with FastAPI BackgroundTasks. This affects the deployment architecture.
- **cty.dat integration:** DXCC entity lookup from cty.dat is needed for Phase 4. The format is well-documented (AD1C Country Files) but a Python library needs to be identified or a simple parser written.
- **LoTW/eQSL field schema:** The per-QSO LoTW/eQSL sync fields (`LOTW_QSL_SENT`, `LOTW_QSL_RCVD`, etc.) must be in the Phase 1 schema even though the LoTW integration feature is deferred to v2. Adding them later requires a data migration.
- **Version pinning:** All library versions in STACK.md carry MEDIUM confidence and require PyPI verification before writing `requirements.txt`.

---

## Sources

### Primary (HIGH confidence)
- ADIF 3.x specification (training data) — field names, format structure, enumeration values, byte-length encoding, EOH/EOR semantics
- MongoDB multi-tenancy and compound index patterns (training data) — shared collection vs. per-collection recommendation, upsert idempotency
- Python/PyMongo naive datetime behavior (training data) — PyMongo BSON datetime storage, tzinfo stripping

### Secondary (MEDIUM confidence)
- CloudLog (open source, GitHub) — multi-operator feature set, self-hosted PHP reference implementation
- QRZ Logbook, LoTW documentation (training data) — feature expectations, LoTW TQSL architecture
- FastAPI, Motor, Beanie documentation (training data, Aug 2025 cutoff) — async patterns, ODM usage

### Tertiary (LOW confidence — verify before implementation)
- `adif-io` on PyPI: https://pypi.org/project/adif-io/ — verify maintained, current version
- `adif3` on PyPI: https://pypi.org/project/adif3/ — evaluate as fallback
- `mongomock-motor` — verify Motor 3.x compatibility
- `python-jose` — check for security advisories
- FastAPI current stable version: https://fastapi.tiangolo.com

---

*Research completed: 2026-04-03*
*Ready for roadmap: yes*
