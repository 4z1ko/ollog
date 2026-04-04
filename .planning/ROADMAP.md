# Roadmap: ollog — Ham Radio Online Logbook

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-04)
- 🚧 **v1.1 Operator & Station Profiles** — Phases 7–10 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–6) — SHIPPED 2026-04-04</summary>

- [x] Phase 1: Foundation (4/4 plans) — completed 2026-04-03
- [x] Phase 2: Admin & Accounts (2/2 plans) — completed 2026-04-03
- [x] Phase 3: QSO Entry & Log View (4/4 plans) — completed 2026-04-03
- [x] Phase 4: ADIF Import & Export (4/4 plans) — completed 2026-04-03
- [x] Phase 5: Multi-Operator & Live Feed (4/4 plans) — completed 2026-04-04
- [x] Phase 6: Navigation Fix (1/1 plan) — completed 2026-04-04

Full archive: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### 🚧 v1.1 Operator & Station Profiles (In Progress)

**Milestone Goal:** Each operator can save their personal info, station details, and location (grid/lat/lon), with callsigns auto-stamped onto every new QSO logged.

#### Phase 7: Profile Data Model and Grid Utility
**Goal**: The User document holds all operator profile fields and the grid conversion utility is correct and testable.
**Depends on**: Phase 6 (v1.0 complete)
**Requirements**: PROF-01, PROF-02, PROF-03, PROF-04, PROF-05
**Success Criteria** (what must be TRUE):
  1. User document stores OPERATOR callsign (from login) and optional STATION_CALLSIGN — existing documents get None for absent fields with no migration required
  2. User document stores personal info fields: name, email (validated format), QTH city, state/province, country
  3. User document stores MY_GRIDSQUARE (up to 6 characters) and the decimal lat/lon auto-derived from that grid using the center of the square (not the SW corner)
  4. User document stores station equipment fields: MY_RIG, MY_ANT, and TX_PWR (watts as a number)
  5. Grid conversion utility converts a valid 4- or 6-character Maidenhead locator to a (lat, lon) tuple using center=True — the returned coordinates match the center of the grid square, not the SW corner
**Plans:** 2 plans

Plans:
- [ ] 07-01-PLAN.md -- Extend User document with Optional profile fields and add maidenhead + pydantic[email] dependencies
- [ ] 07-02-PLAN.md -- TDD: grid_to_latlon() utility with maidenhead center=True and comprehensive unit tests

#### Phase 8: Profile Service, Schemas, and API Router
**Goal**: Operators can read and update their own profile via REST API and the profile is persisted correctly with grid-to-lat/lon auto-compute on save.
**Depends on**: Phase 7
**Requirements**: API-01, API-02, API-03
**Success Criteria** (what must be TRUE):
  1. Operator can GET /api/profile with their JWT and receive all profile fields — no callsign parameter is accepted on this endpoint
  2. Operator can PATCH /api/profile to update any combination of profile fields and the changes are immediately reflected on the next GET — including lat/lon auto-updating when MY_GRIDSQUARE changes
  3. An operator cannot read or modify another operator's profile — any attempt to access a different operator's profile data via the API returns an authorization error
  4. A profile-less operator (no fields set) can still use GET /api/profile — the response returns empty/null fields rather than an error
**Plans**: TBD

Plans:
- [ ] 08-01: ProfileUpdateRequest and ProfileResponse Pydantic schemas with MY_GRIDSQUARE format validation (regex) and EmailStr validation
- [ ] 08-02: GET /api/profile and PATCH /api/profile endpoints — JWT-only operator derivation, grid-to-lat/lon sync on save, cross-operator isolation tests

#### Phase 9: QSO Auto-Stamping
**Goal**: Every new QSO logged via the web UI or REST API is auto-stamped with OPERATOR and conditionally STATION_CALLSIGN from the operator's profile — without touching the ADIF import path.
**Depends on**: Phase 8
**Requirements**: STAMP-01, STAMP-02, STAMP-03
**Success Criteria** (what must be TRUE):
  1. A QSO submitted via the web form or REST API POST is stored with OPERATOR set to the operator's callsign from their profile — no manual entry of OPERATOR is required
  2. A QSO submitted by an operator with STATION_CALLSIGN set in their profile is stored with STATION_CALLSIGN present in the QSO document — and the field is entirely absent (not an empty string) when the profile has no station callsign set
  3. An operator with no profile set can still log QSOs — the missing profile produces no error and no null fields in the QSO document
  4. Importing a .adi/.adif file does not apply any profile auto-stamping — imported QSO documents are stored exactly as parsed from the file
**Plans:** 1 plan

Plans:
- [ ] 09-01-PLAN.md — Extend build_qso_dict with optional profile stamping, update REST and UI endpoints, integration tests

#### Phase 10: Profile UI
**Goal**: Operators can view and update their profile through a settings page in the log UI, with clear labeling distinguishing their personal callsign from any station callsign.
**Depends on**: Phase 9
**Requirements**: UI-01, UI-02, UI-03
**Success Criteria** (what must be TRUE):
  1. Operator can navigate to /log/profile from the log UI and see a form pre-populated with their current profile values
  2. Operator can update any profile field via the HTMX form and see a confirmation that changes were saved — without a full page reload
  3. The profile form clearly distinguishes OPERATOR (the operator's personal callsign, read-only derived from login) from STATION_CALLSIGN (optional club or event call) with an explanatory tooltip or note
  4. A navigation link to the profile settings page is present in the log UI templates — operators do not need to type the URL directly
**Plans**: TBD

Plans:
- [ ] 10-01: GET /log/profile and POST /log/profile routes plus templates/log/profile.html HTMX form — cookie auth, pre-populated fields, OPERATOR vs. STATION_CALLSIGN labeling with tooltip
- [ ] 10-02: Add profile nav link to log UI templates (form.html, log.html) — consistent with existing Import/Export nav pattern

## Progress

**Execution Order:**
Phases execute in numeric order: 7 → 8 → 9 → 10

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 4/4 | ✓ Complete | 2026-04-03 |
| 2. Admin & Accounts | v1.0 | 2/2 | ✓ Complete | 2026-04-03 |
| 3. QSO Entry & Log View | v1.0 | 4/4 | ✓ Complete | 2026-04-03 |
| 4. ADIF Import & Export | v1.0 | 4/4 | ✓ Complete | 2026-04-03 |
| 5. Multi-Operator & Live Feed | v1.0 | 4/4 | ✓ Complete | 2026-04-04 |
| 6. Navigation Fix | v1.0 | 1/1 | ✓ Complete | 2026-04-04 |
| 7. Profile Data Model and Grid Utility | v1.1 | 0/2 | Not started | - |
| 8. Profile Service, Schemas, and API Router | v1.1 | 0/2 | Not started | - |
| 9. QSO Auto-Stamping | v1.1 | 0/1 | Not started | - |
| 10. Profile UI | v1.1 | 0/2 | Not started | - |
