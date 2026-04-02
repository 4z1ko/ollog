# Roadmap: ollog — Ham Radio Online Logbook

## Overview

ollog is built in five phases that follow a strict dependency order: the ADIF parser and data model must be correct before any QSO data is persisted, authentication must gate every endpoint before any UI is exposed, and multi-operator concurrent safety is validated after the write path is proven stable. The result is a self-hosted, ADIF-native, multi-operator logbook where operators trust their data from day one.

## Phases

- [ ] **Phase 1: Foundation** - ADIF parser, MongoDB schema, auth service, and project scaffolding
- [ ] **Phase 2: Admin & Accounts** - Admin UI for operator account creation, enable/disable, and password reset
- [ ] **Phase 3: QSO Entry & Log View** - QSO logging via web form and REST API, editing, soft-delete, duplicate detection, and paginated log view
- [ ] **Phase 4: ADIF Import & Export** - File upload import with duplicate report, lossless N+1 field passthrough, and streaming ADIF export
- [ ] **Phase 5: Multi-Operator & Live Feed** - Concurrent write safety validation, strict operator data isolation, and real-time live QSO feed

## Phase Details

### Phase 1: Foundation
**Goal**: The project runs, the ADIF library is correct, the MongoDB schema and indexes are in place, and every API endpoint is protected by JWT authentication.
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-04, AUTH-05, AUTH-06
**Success Criteria** (what must be TRUE):
  1. Operator can log in with username and password and receive a JWT token
  2. Operator session persists across browser refresh — reloading the page does not require re-login
  3. Any API endpoint called without a valid JWT returns 401 — no unauthenticated data access is possible
  4. ADIF round-trip test passes: a known .adi file parses to Python dicts and serializes back to byte-identical ADIF output (including non-ASCII characters and APP_ fields)
  5. The application starts via Docker Compose with a single command and connects to MongoDB successfully
**Plans**: 4 plans

Plans:
- [ ] 01-01: Project scaffolding — FastAPI app, Docker Compose, config from environment, health endpoint
- [ ] 01-02: ADIF library — tag-stream parser and serializer with UTF-8 byte-length handling and round-trip test suite
- [ ] 01-03: MongoDB schema — QSO document model, compound indexes (operator + CALL + date + BAND + MODE), UTC datetime convention
- [ ] 01-04: Auth service — JWT issuance and validation, bcrypt password hashing, callsign injection from token, admin role check

### Phase 2: Admin & Accounts
**Goal**: An admin can fully manage operator accounts — create, enable/disable, and reset passwords — through a protected web UI and API.
**Depends on**: Phase 1
**Requirements**: AUTH-01, AUTH-02, AUTH-03
**Success Criteria** (what must be TRUE):
  1. Admin can create an operator account by supplying callsign, username, and password — the account is immediately usable for login
  2. Admin can disable an operator account — the disabled operator cannot log in and receives a clear error
  3. Admin can reset an operator's password — the operator can immediately log in with the new password
  4. All admin account management actions require admin-role JWT — no operator-level account can invoke them
**Plans**: 4 plans

Plans:
- [ ] 02-01: Admin API endpoints — create, enable/disable, reset password with admin role enforcement
- [ ] 02-02: Admin web UI — account management panel using HTMX + Jinja2

### Phase 3: QSO Entry & Log View
**Goal**: Operators can log QSOs via the web form and REST API, edit and soft-delete their own QSOs, see duplicate warnings, and browse their log with pagination, filtering, and sorting.
**Depends on**: Phase 2
**Requirements**: QSO-01, QSO-02, QSO-03, QSO-04, QSO-05, QSO-06, LOG-01, LOG-02, LOG-03
**Success Criteria** (what must be TRUE):
  1. Operator can submit a QSO via the web form with all required fields (CALL, QSO_DATE, TIME_ON, BAND, FREQ, MODE, RST_SENT, RST_RCVD) and it appears immediately in their log
  2. Operator can POST a QSO via REST API in ADIF field format and the QSO is stored and retrievable
  3. Operator can edit any field of an existing QSO and save the change — the updated values are reflected in the log
  4. Operator can soft-delete a QSO after confirmation — the QSO disappears from the default log view but is recoverable
  5. When logging a QSO that matches the same CALL, BAND, and MODE within a ±2 minute window, the system displays a duplicate warning before saving
  6. All QSO timestamps are stored and displayed in UTC — no local-time drift is visible in the UI
  7. Operator can page through their QSO log and filter by callsign, date range, band, and mode
**Plans**: 4 plans

Plans:
- [ ] 03-01: QSO API — POST, GET, PATCH, soft-DELETE with operator isolation from JWT callsign
- [ ] 03-02: Duplicate detection — fuzzy ±2 min window check on write, warning response
- [ ] 03-03: QSO entry web form — HTMX form with all ADIF fields, duplicate warning UI
- [ ] 03-04: Log view — paginated list, filter bar (callsign, date range, band, mode), sort controls

### Phase 4: ADIF Import & Export
**Goal**: Operators can upload existing ADIF logbooks for lossless import with a duplicate report, and download their logbook as a valid ADIF file that round-trips without data loss.
**Depends on**: Phase 3
**Requirements**: ADIF-01, ADIF-02, ADIF-03, ADIF-04, ADIF-05, ADIF-06
**Success Criteria** (what must be TRUE):
  1. Operator can upload a .adi or .adif file and see an import report showing how many QSOs were accepted, how many were flagged as potential duplicates, and any parse errors — no QSOs are silently dropped
  2. Duplicate detection during import uses the same fuzzy ±2 min window as live entry — no auto-deletion occurs; operator reviews and decides
  3. A QSO file with APP_ fields and USERDEF fields imports and exports with those fields intact — no non-standard field is dropped
  4. Operator can download their entire logbook as a valid .adi file that opens correctly in external logging software
  5. An ADIF file exported from ollog and re-imported produces zero data changes — field names, values, and custom fields are identical
  6. The ADIF parser correctly handles files with missing EOH, case-insensitive field names, and varying whitespace around EOR tags
**Plans**: 4 plans

Plans:
- [ ] 04-01: ADIF import endpoint — multipart upload, batch insert with ordered=False, import report response
- [ ] 04-02: Import duplicate detection — fuzzy window applied per-record, report includes duplicate candidates
- [ ] 04-03: ADIF export endpoint — streaming response, operator-scoped, optional filters
- [ ] 04-04: Round-trip validation — integration test covering APP_ fields, USERDEF fields, and edge-case file variants

### Phase 5: Multi-Operator & Live Feed
**Goal**: Multiple operators can log simultaneously without any data loss or cross-operator leakage, and can see each other's QSOs appear live in a shared station feed without page refresh.
**Depends on**: Phase 4
**Requirements**: MULTI-01, MULTI-02, MULTI-03
**Success Criteria** (what must be TRUE):
  1. Two operators logging QSOs simultaneously produce no data conflicts, no lost writes, and no duplicate insertions — all QSOs from both operators are present and correctly attributed after concurrent load
  2. An operator querying their own log never sees QSOs belonging to another operator — cross-operator data leakage is not possible through any API endpoint
  3. When one operator logs a QSO, other logged-in operators see it appear in the shared station feed within a few seconds without refreshing the page
**Plans**: 4 plans

Plans:
- [ ] 05-01: Concurrent write safety — verify compound unique index behavior under concurrent inserts; upsert strategy
- [ ] 05-02: Operator isolation audit — verify all QSO queries inject operator from JWT, not request body
- [ ] 05-03: Live feed — WebSocket or SSE broadcast of new QSOs to connected operator sessions

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/4 | Not started | - |
| 2. Admin & Accounts | 0/2 | Not started | - |
| 3. QSO Entry & Log View | 0/4 | Not started | - |
| 4. ADIF Import & Export | 0/4 | Not started | - |
| 5. Multi-Operator & Live Feed | 0/3 | Not started | - |
