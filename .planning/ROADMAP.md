# Roadmap: ollog — Ham Radio Online Logbook

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-04)
- ✅ **v1.1 Operator & Station Profiles** — Phases 7–10 (shipped 2026-04-04)
- ✅ **v1.2 Callsign Entity Lookup & Country Flags** — Phases 11–12 (shipped 2026-04-04)
- ✅ **v1.3 Documentation** — Phases 13–15 (shipped 2026-04-05)
- ✅ **v1.4 UDP Interface** — Phases 16–18 (shipped 2026-04-06)
- ✅ **v1.5 Documentation Update** — Phases 19–22 (shipped 2026-04-08)
- ✅ **v1.6 Live Log Table** — Phases 23–24 (shipped 2026-04-08)
- 🚧 **v1.7 API Token Auth** — Phases 25–28 (in progress)


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

<details>
<summary>✅ v1.6 Live Log Table (Phases 23–24) — SHIPPED 2026-04-08</summary>

- [x] Phase 23: SSE-Triggered Log Table Reload (1/1 plan) — completed 2026-04-08
- [x] Phase 24: Session Robustness (1/1 plan) — completed 2026-04-08

Full archive: `.planning/milestones/v1.6-ROADMAP.md`

</details>

---

### 🚧 v1.7 API Token Auth (In Progress)

**Milestone Goal:** Operators can create named API tokens from Profile Settings and use them to authenticate REST API calls (`X-API-Key` header) and identify themselves in UDP ADIF datagrams (`APP_OLLOG_TOKEN` field).

- [x] **Phase 25: Token Model and Service Layer** — `ApiToken` Beanie document, HMAC-SHA256 helpers, `api_token_secret` config; foundation for all subsequent token phases
- [x] **Phase 26: Token CRUD API and Profile UI** — REST endpoints for token lifecycle (create/list/revoke) behind JWT, HTMX token section in Profile Settings with show-once plaintext banner; covers TOK-01–04
- [x] **Phase 27: X-API-Key REST Authentication** — combined JWT + API-key dependency with `auto_error=False`, opt-in on all QSO endpoints; covers API-01–03
- [ ] **Phase 28: UDP APP_OLLOG_TOKEN Support** — per-datagram in-memory HMAC cache, `APP_OLLOG_TOKEN` field resolution in `_handle_datagram`, `UDP_OPERATOR` fallback preserved; covers UDP-01–03

---

## Phase Details

### Phase 25: Token Model and Service Layer

**Goal:** The `ApiToken` Beanie document exists as a registered MongoDB collection with all fields, indexes, and pure HMAC-SHA256 service helpers in place — making the rest of v1.7 buildable and independently testable.
**Depends on:** Phase 24 (v1.6 complete)
**Requirements:** *(foundation phase — no directly observable v1.7 requirements; enables Phase 26–28)*
**Success Criteria** (what must be TRUE):
  1. `ApiToken` collection exists in MongoDB after app startup with the correct compound index on `(token_prefix, user_id)`
  2. `generate_api_token()` returns a string starting with `ollog_` containing 256 bits of URL-safe entropy
  3. `hash_api_token()` and `verify_api_token()` use HMAC-SHA256 (not Argon2); `verify_api_token()` is constant-time via `hmac.compare_digest`
  4. `api_token_secret` is loaded from `Settings` as a `SecretStr` separate from `SECRET_KEY`
  5. Token name validation rejects names outside alphanumeric + hyphen/underscore, 1–80 chars
**Plans:** 1 plan

Plans:
- [x] 025-01-PLAN.md — ApiToken model, HMAC-SHA256 service helpers, config, and tests

---

### Phase 26: Token CRUD API and Profile UI

**Goal:** Operators can create named API tokens, see them listed in Profile Settings, and revoke them — with the plaintext token shown exactly once at creation.
**Depends on:** Phase 25
**Requirements:** TOK-01, TOK-02, TOK-03, TOK-04
**Success Criteria** (what must be TRUE):
  1. Operator can submit a token creation form in Profile Settings with a required name and optional expiry date; the response shows the full plaintext token in a banner marked "will not be shown again"
  2. After closing or dismissing the creation banner, the plaintext token cannot be recovered — revisiting the profile page shows only the token prefix, label, creation date, and expiry
  3. The active token list displays label, creation date, expiry (or "Never"), and the first 8 characters of the token for identification
  4. Operator can revoke any individual token; the token immediately stops being accepted for authentication on subsequent requests
**Plans:** 1 plan

Plans:
- [ ] 026-01-PLAN.md — expires_at model patch, REST CRUD /api/tokens, HTMX profile UI, templates, and integration tests

---

### Phase 27: X-API-Key REST Authentication

**Goal:** All QSO REST API endpoints accept `X-API-Key: <token>` as a valid alternative to JWT Bearer, with identical operator isolation and correct HTTP 401 responses for invalid or missing credentials.
**Depends on:** Phase 26
**Requirements:** API-01, API-02, API-03
**Success Criteria** (what must be TRUE):
  1. A `curl` request to any QSO endpoint with `X-API-Key: <valid-token>` succeeds and returns the authenticated operator's data — no JWT needed
  2. The operator identity resolved from an API key is identical to the identity resolved from a JWT for the same operator — no cross-operator data access is possible
  3. A request with a missing, invalid, or expired credential (both JWT and API key absent or wrong) returns HTTP 401 — never HTTP 403
  4. Admin and profile endpoints continue to require JWT; they do not accept `X-API-Key` authentication
**Plans:** 1 plan

Plans:
- [ ] 027-01-PLAN.md — dual-auth dependencies (JWT + X-API-Key), QSO router Depends() swap, isolation audit update, integration tests

---

### Phase 28: UDP APP_OLLOG_TOKEN Support

**Goal:** UDP datagrams containing `APP_OLLOG_TOKEN` resolve operator identity from that token value per datagram, enabling multi-operator UDP setups — while datagrams without the field continue to fall back to `UDP_OPERATOR` with no regression.
**Depends on:** Phase 25
**Requirements:** UDP-01, UDP-02, UDP-03
**Success Criteria** (what must be TRUE):
  1. A UDP datagram containing a valid `APP_OLLOG_TOKEN` field is accepted and the QSO is logged under the operator whose token matches — not the `UDP_OPERATOR` config value
  2. A UDP datagram containing an invalid or revoked `APP_OLLOG_TOKEN` is rejected with a structured log line; it does not fall through silently to `UDP_OPERATOR`
  3. A UDP datagram without `APP_OLLOG_TOKEN` is processed exactly as before using `UDP_OPERATOR` — existing behavior is unchanged
  4. The in-memory token cache is loaded at startup and refreshed when any token is created or revoked; no MongoDB round-trip occurs per datagram
**Plans:** 1 plan

Plans:
- [ ] 028-01-PLAN.md — UDPTokenCache singleton, _handle_datagram APP_OLLOG_TOKEN branch, notify_refresh() wiring, tests

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
| 23. SSE-Triggered Log Table Reload | v1.6 | 1/1 | ✓ Complete | 2026-04-08 |
| 24. Session Robustness | v1.6 | 1/1 | ✓ Complete | 2026-04-08 |
| 25. Token Model and Service Layer | v1.7 | 1/1 | ✓ Complete | 2026-04-09 |
| 26. Token CRUD API and Profile UI | v1.7 | 1/1 | ✓ Complete | 2026-04-09 |
| 27. X-API-Key REST Authentication | v1.7 | 1/1 | ✓ Complete | 2026-04-09 |
| 28. UDP APP_OLLOG_TOKEN Support | v1.7 | 0/1 | Not started | - |
