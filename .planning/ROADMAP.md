# Roadmap: ollog — Ham Radio Online Logbook

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-04)
- ✅ **v1.1 Operator & Station Profiles** — Phases 7–10 (shipped 2026-04-04)
- 🚧 **v1.2 Callsign Entity Lookup & Country Flags** — Phases 11–12 (in progress)

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

<details>
<summary>✅ v1.1 Operator & Station Profiles (Phases 7–10) — SHIPPED 2026-04-04</summary>

- [x] Phase 7: Profile Data Model and Grid Utility (2/2 plans) — completed 2026-04-04
- [x] Phase 8: Profile Service, Schemas, and API Router (2/2 plans) — completed 2026-04-04
- [x] Phase 9: QSO Auto-Stamping (1/1 plan) — completed 2026-04-04
- [x] Phase 10: Profile UI (2/2 plans) — completed 2026-04-04

Full archive: `.planning/milestones/v1.1-ROADMAP.md`

</details>

### 🚧 v1.2 Callsign Entity Lookup & Country Flags (In Progress)

**Milestone Goal:** Resolve any logged callsign to its ITU-allocated country/entity and display the corresponding flag in the QSO log view. Purely presentational — no new database schema, no stored data.

- [ ] **Phase 11: Prefix Resolver Module** — Pure Python module with bundled ITU prefix range table, range-aware longest-match lookup, suffix stripping, and ISO mapping
- [ ] **Phase 12: Flag Display Integration** — Wire resolver into _qso_to_view_dict(), fix static file path, render flag img tag in qso_row.html

#### Phase 11: Prefix Resolver Module

**Goal:** A self-contained, fully-tested callsign-to-ISO-code resolver exists and is verifiable in isolation before any UI work begins
**Depends on:** Phase 10 (project foundation stable)
**Requirements:** PRFX-01, PRFX-02, PRFX-03, PRFX-04
**Success Criteria** (what must be TRUE):
  1. `lookup_prefix("W1AW")` returns `"US"`, `lookup_prefix("DL1ABC")` returns `"DE"`, `lookup_prefix("JA1YWX")` returns `"JP"` — common DX prefixes resolve correctly
  2. `lookup_prefix("3DA0ABC")` returns `"SZ"` (Eswatini) and `lookup_prefix("3DN1ABC")` returns `"FJ"` (Fiji) — overlapping sub-ranges resolve to the correct country
  3. `lookup_prefix("G3YWX/MM")` returns `None` and `lookup_prefix("EA3/G3YWX")` returns `"ES"` — `/MM` and `/AM` treated as unresolvable operating suffixes, not country prefixes
  4. `lookup_prefix("W1AW/P")`, `lookup_prefix("W1AW/7")`, `lookup_prefix("W1AW/QRP")` all return `"US"` — portable and area suffixes stripped before lookup
  5. `lookup_prefix("4U1ITU")` returns `None` and `lookup_prefix("UNKNOWN")` returns `None` — non-country entities and unknown prefixes return None without raising exceptions
**Plans:** TBD

Plans:
- [ ] 11-01: Prefix data and resolver module

#### Phase 12: Flag Display Integration

**Goal:** Country flag icons appear next to callsigns in the QSO log table, with graceful no-flag fallback for unresolvable callsigns
**Depends on:** Phase 11
**Requirements:** FLAG-01, FLAG-02
**Success Criteria** (what must be TRUE):
  1. Opening the log view shows a flag icon to the left of each callsign where the prefix resolved — e.g., a US flag beside W1AW, a German flag beside DL1ABC
  2. QSO rows where the callsign is unresolvable (unknown prefix, `/MM`, non-country entity) show no flag and no broken image icon
  3. Flag icons persist correctly after HTMX pagination (clicking Next/Previous page) — no flags disappear or become broken images on partial swap
  4. Hovering a flag shows a country name tooltip (`title` attribute) — zero JavaScript required
**Plans:** TBD

Plans:
- [ ] 12-01: Static file path fix and flag display wiring

## Progress

**Execution Order:**
Phases execute in numeric order: 11 → 12

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation | v1.0 | 4/4 | ✓ Complete | 2026-04-03 |
| 2. Admin & Accounts | v1.0 | 2/2 | ✓ Complete | 2026-04-03 |
| 3. QSO Entry & Log View | v1.0 | 4/4 | ✓ Complete | 2026-04-03 |
| 4. ADIF Import & Export | v1.0 | 4/4 | ✓ Complete | 2026-04-03 |
| 5. Multi-Operator & Live Feed | v1.0 | 4/4 | ✓ Complete | 2026-04-04 |
| 6. Navigation Fix | v1.0 | 1/1 | ✓ Complete | 2026-04-04 |
| 7. Profile Data Model and Grid Utility | v1.1 | 2/2 | ✓ Complete | 2026-04-04 |
| 8. Profile Service, Schemas, and API Router | v1.1 | 2/2 | ✓ Complete | 2026-04-04 |
| 9. QSO Auto-Stamping | v1.1 | 1/1 | ✓ Complete | 2026-04-04 |
| 10. Profile UI | v1.1 | 2/2 | ✓ Complete | 2026-04-04 |
| 11. Prefix Resolver Module | v1.2 | 0/TBD | Not started | - |
| 12. Flag Display Integration | v1.2 | 0/TBD | Not started | - |
