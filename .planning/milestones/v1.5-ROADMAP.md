# Roadmap: ollog — Ham Radio Online Logbook

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-04)
- ✅ **v1.1 Operator & Station Profiles** — Phases 7–10 (shipped 2026-04-04)
- ✅ **v1.2 Callsign Entity Lookup & Country Flags** — Phases 11–12 (shipped 2026-04-04)
- ✅ **v1.3 Documentation** — Phases 13–15 (shipped 2026-04-05)
- ✅ **v1.4 UDP Interface** — Phases 16–18 (shipped 2026-04-06)
- 📋 **v1.5 Documentation Update** — Phases 19–22 (planned)


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

<details>
<summary>✅ v1.2 Callsign Entity Lookup & Country Flags (Phases 11–12) — SHIPPED 2026-04-04</summary>

- [x] Phase 11: Prefix Resolver Module — completed 2026-04-04
- [x] Phase 12: Flag Display Integration — completed 2026-04-04

Full archive: `.planning/milestones/v1.2-ROADMAP.md`

</details>

<details>
<summary>✅ v1.3 Documentation (Phases 13–15) — SHIPPED 2026-04-05</summary>

- [x] Phase 13: OpenAPI Schema Cleanup (2/2 plans) — completed 2026-04-04
- [x] Phase 14: MkDocs Infrastructure (2/2 plans) — completed 2026-04-04
- [x] Phase 15: Narrative Documentation Content (4/4 plans) — completed 2026-04-05

Full archive: `.planning/milestones/v1.3-ROADMAP.md`

</details>

<details>
<summary>✅ v1.4 UDP Interface (Phases 16–18) — SHIPPED 2026-04-06</summary>

- [x] Phase 16: UDP Infrastructure (2/2 plans) — completed 2026-04-06
- [x] Phase 17: QSO Processing Pipeline (1/1 plan) — completed 2026-04-06
- [x] Phase 18: Error Handling and Observability (1/1 plan) — completed 2026-04-06

Full archive: `.planning/milestones/v1.4-ROADMAP.md`

</details>

## v1.5 Documentation Update

**Milestone Goal:** Update the MkDocs documentation site to cover the v1.4 UDP Interface. Three doc source files receive targeted additions, then the static site is rebuilt and committed.

### Phase 19: Deployment Guide — UDP Configuration

**Goal:** Operators can find all UDP configuration options documented in `docs/deployment.md`.
**Depends on:** Phase 18
**Requirements:** DOC-01, DOC-02
**Success Criteria** (what must be TRUE):
  1. The Environment Variables table in `deployment.md` includes `UDP_ENABLED`, `UDP_PORT`, `UDP_BIND_HOST`, and `UDP_OPERATOR` with their types, defaults, and descriptions.
  2. A Docker Compose example snippet shows how to enable UDP: the relevant env vars set and the `"2399:2399/udp"` port mapping present.
**Plans:** 1 plan

Plans:
- [ ] 19-01: Add UDP env vars and Docker Compose UDP example to deployment.md

---

### Phase 20: Getting-Started Guide — Sending QSOs via UDP

**Goal:** Operators can configure their logging software (nc, WSJT-X, N1MM+, Log4OM) to send QSOs to ollog via UDP by following `docs/getting-started.md`.
**Depends on:** Phase 19
**Requirements:** DOC-03, DOC-04, DOC-05, DOC-06, DOC-07
**Success Criteria** (what must be TRUE):
  1. `getting-started.md` contains a "Sending QSOs via UDP" section explaining that ADIF datagrams sent to the configured port are logged under the `UDP_OPERATOR` callsign.
  2. A `nc` one-liner example for manual testing is present and copy-pasteable.
  3. Step-by-step WSJT-X configuration (Settings → Reporting → UDP Server) is documented with host/port fields.
  4. Step-by-step N1MM+ configuration (Config → Configure Ports → UDP ADIF broadcast) is documented with host/port fields.
  5. Log4OM configuration steps for sending ADIF messages to ollog over UDP are documented.
**Plans:** 1 plan

Plans:
- [ ] 20-01: Add "Sending QSOs via UDP" section with nc, WSJT-X, N1MM+, Log4OM examples to getting-started.md

---

### Phase 21: Troubleshooting Guide — UDP Issues

**Goal:** Operators can diagnose and resolve common UDP integration problems using `docs/troubleshooting.md`.
**Depends on:** Phase 20
**Requirements:** DOC-08, DOC-09, DOC-10, DOC-11
**Success Criteria** (what must be TRUE):
  1. `troubleshooting.md` contains an entry for UDP socket binding failures, listing port-in-use and `UDP_BIND_HOST` mismatch as causes with concrete fixes.
  2. An entry covers the `UDP_OPERATOR` callsign-not-found WARNING with fix steps (operator account must exist, callsign must match exactly).
  3. An entry covers QSOs arriving but not appearing in the log, with causes (missing required ADIF field, duplicate within ±2 min) and log-based diagnosis steps.
  4. An entry covers no UDP activity in logs, identifying `UDP_ENABLED` not set or `false` as the cause with the fix.
**Plans:** 1 plan

Plans:
- [ ] 21-01: Add four UDP troubleshooting entries to troubleshooting.md

---

### Phase 22: Static Site Rebuild

**Goal:** The published static site at `site/` reflects all UDP documentation changes from Phases 19–21.
**Depends on:** Phase 21
**Requirements:** DOC-12
**Success Criteria** (what must be TRUE):
  1. `mkdocs build` completes without errors.
  2. The updated `site/` output is committed alongside the doc source changes so the repository's static site is current.
**Plans:** 1 plan

Plans:
- [ ] 22-01: Run mkdocs build and commit updated site/

---

## Progress

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
| 11. Prefix Resolver Module | v1.2 | 1/1 | ✓ Complete | 2026-04-04 |
| 12. Flag Display Integration | v1.2 | 1/1 | ✓ Complete | 2026-04-04 |
| 13. OpenAPI Schema Cleanup | v1.3 | 2/2 | ✓ Complete | 2026-04-04 |
| 14. MkDocs Infrastructure | v1.3 | 2/2 | ✓ Complete | 2026-04-04 |
| 15. Narrative Documentation Content | v1.3 | 4/4 | ✓ Complete | 2026-04-05 |
| 16. UDP Infrastructure | v1.4 | 2/2 | ✓ Complete | 2026-04-06 |
| 17. QSO Processing Pipeline | v1.4 | 1/1 | ✓ Complete | 2026-04-06 |
| 18. Error Handling and Observability | v1.4 | 1/1 | ✓ Complete | 2026-04-06 |
| 19. Deployment Guide — UDP Configuration | v1.5 | 0/1 | Not started | - |
| 20. Getting-Started Guide — Sending QSOs via UDP | v1.5 | 0/1 | Not started | - |
| 21. Troubleshooting Guide — UDP Issues | v1.5 | 0/1 | Not started | - |
| 22. Static Site Rebuild | v1.5 | 0/1 | Not started | - |
