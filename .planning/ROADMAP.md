# Roadmap: ollog — Ham Radio Online Logbook

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-04)
- ✅ **v1.1 Operator & Station Profiles** — Phases 7–10 (shipped 2026-04-04)
- ✅ **v1.2 Callsign Entity Lookup & Country Flags** — Phases 11–12 (shipped 2026-04-04)
- ✅ **v1.3 Documentation** — Phases 13–15 (shipped 2026-04-05)
- ✅ **v1.4 UDP Interface** — Phases 16–18 (shipped 2026-04-06)
- ✅ **v1.5 Documentation Update** — Phases 19–22 (shipped 2026-04-08)
- 🔄 **v1.6 Live Log Table** — Phases 23–24 (in progress)


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

<details>
<summary>✅ v1.5 Documentation Update (Phases 19–22) — SHIPPED 2026-04-08</summary>

- [x] Phase 19: Deployment Guide — UDP Configuration (1/1 plan) — completed 2026-04-08
- [x] Phase 20: Getting-Started Guide — Sending QSOs via UDP (1/1 plan) — completed 2026-04-08
- [x] Phase 21: Troubleshooting Guide — UDP Issues (1/1 plan) — completed 2026-04-08
- [x] Phase 22: Static Site Rebuild (1/1 plan) — completed 2026-04-08

Full archive: `.planning/milestones/v1.5-ROADMAP.md`

</details>

---

## v1.6 Live Log Table

Operators see new QSOs appear in the log table without a manual reload. The existing SSE infrastructure (`/feed/station`) and HTMX partial endpoint (`/log/view`) are already in place; this milestone wires them together via template changes only. Auto-refresh is guarded against disrupting pagination, active filters, and open inline edit rows. Session lifetime is raised to support overnight FT8 logging sessions.

### Phase 23: SSE-Triggered Log Table Reload

**Goal:** The operator's log table automatically shows new QSOs without a manual reload, scoped correctly to the operator and suppressed when the view is not in its default state.

**Dependencies:** None (all infrastructure exists — `/feed/station`, `/log/view`, htmx-ext-sse).

**Requirements:** LIVE-01, LIVE-02, LIVE-03, LIVE-04, LIVE-05

**Success Criteria:**

1. When a new QSO is inserted (via form, UDP, or API) and the operator is viewing page 1 with no filters and default sort, the log table row appears within seconds without any user action.
2. The operator's log table shows only their own QSOs after an SSE-triggered reload — QSOs from other operators are never visible (operator isolation enforced via JWT on every re-fetch).
3. When the operator navigates to page 2 or beyond, applies any filter, or changes the sort order, no auto-refresh fires — the table remains stable while they browse.
4. While an inline QSO edit row is open, no auto-refresh fires — the edit form is not destroyed and unsaved data is not lost.
5. A "Live" indicator is visible in the log view when the SSE connection is active, and it changes state (or disappears) when the connection drops.

---

### Phase 24: Session Robustness

**Goal:** Operators running overnight FT8 logging sessions are not silently logged out mid-session due to JWT expiry.

**Dependencies:** Phase 23 (SESSION-01 is a standalone config change but logically completes the live-log milestone — a session that expires mid-SSE undermines the live feature).

**Requirements:** SESSION-01

**Success Criteria:**

1. The `JWT_EXPIRE_MINUTES` environment variable controls session lifetime; setting it to any value changes how long a JWT remains valid without a code change.
2. With the default configuration (`JWT_EXPIRE_MINUTES=480`), an operator who logs in at the start of an 8-hour FT8 session can submit QSOs, paginate, and interact with the log table at the end of the session without being redirected to login.

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
| 19. Deployment Guide — UDP Configuration | v1.5 | 1/1 | ✓ Complete | 2026-04-08 |
| 20. Getting-Started Guide — Sending QSOs via UDP | v1.5 | 1/1 | ✓ Complete | 2026-04-08 |
| 21. Troubleshooting Guide — UDP Issues | v1.5 | 1/1 | ✓ Complete | 2026-04-08 |
| 22. Static Site Rebuild | v1.5 | 1/1 | ✓ Complete | 2026-04-08 |
| 23. SSE-Triggered Log Table Reload | v1.6 | 0/? | ○ Pending | — |
| 24. Session Robustness | v1.6 | 0/? | ○ Pending | — |
