# Roadmap: ollog — Ham Radio Online Logbook

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-04)
- ✅ **v1.1 Operator & Station Profiles** — Phases 7–10 (shipped 2026-04-04)
- ✅ **v1.2 Callsign Entity Lookup & Country Flags** — Phases 11–12 (shipped 2026-04-04)
- ✅ **v1.3 Documentation** — Phases 13–15 (shipped 2026-04-05)
- 🔄 **v1.4 UDP Interface** — Phases 16–18 (in progress)


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

---

## v1.4 UDP Interface

**Goal:** Add a UDP listener that accepts ADIF-formatted QSO datagrams, delivering full operator authentication, auto-stamping, duplicate detection, and SSE feed integration — equivalent to the REST API path but over a fire-and-forget UDP socket.

**Coverage:** 15/15 v1.4 requirements mapped across 3 phases.

---

### Phase 16: UDP Infrastructure

**Goal:** The UDP listener socket is bound and lifecycle-managed — operators can verify the listener is running via the startup banner and confirm Docker UDP forwarding works before any QSO processing logic exists.

**Dependencies:** None (first phase of milestone)

**Requirements:** UDP-01, UDP-02, UDP-03, UDP-04, UDP-05, OBS-04

**Plans:** 2 plans

Plans:
- [x] 16-01-PLAN.md — Extract process_import into app/qso/service.py as import_qsos_from_bytes
- [x] 16-02-PLAN.md — UDP config, DatagramProtocol skeleton, lifespan hooks, Docker port

**Codebase prep (task within this phase):** Extract shared QSO insertion logic from `app/adif/router.py` `process_import()` into `app/qso/service.py`. The current function raises `HTTPException` which is uncatchable from a UDP async task. This extraction must complete before Phase 17 begins.

**Files created:** `app/udp/__init__.py`, `app/udp/server.py` (skeleton `QSODatagramProtocol`)

**Files modified:** `app/config.py` (add `udp_enabled`, `udp_host`, `udp_port`, `udp_operator` settings), `app/main.py` (lifespan startup/shutdown hooks), `docker-compose.yml` (add `"<port>:<port>/udp"` mapping)

**Success Criteria:**

1. Setting `UDP_ENABLED=true` in `.env` causes the app to bind a UDP socket on the configured host and port at startup; the log shows `"UDP listener bound to {host}:{port}"` before the first request is served.
2. Sending a raw UDP datagram to the configured port (e.g., `echo "test" | nc -u 127.0.0.1 2399`) produces a log line confirming datagram receipt — even though no QSO processing happens yet.
3. App shuts down cleanly (no `EADDRINUSE` on restart) — the transport is explicitly closed during lifespan shutdown before the database connection closes.
4. Docker Compose exposes the configured UDP port with `/udp` suffix; a datagram sent from the host reaches the container (verified with `nc -u`).
5. With `UDP_ENABLED=false` (the default), no UDP socket is created and the app starts identically to v1.3.

---

### Phase 17: QSO Processing Pipeline

**Goal:** A raw ADIF ADI datagram sent over UDP results in a QSO stored in MongoDB with correct operator attribution, profile auto-stamping, and duplicate detection — the same outcome as `POST /api/qsos/`, and the inserted QSO appears immediately in the SSE live station feed.

**Dependencies:** Phase 16 (skeleton protocol running; `process_import()` extraction complete)

**Requirements:** QSO-01, QSO-02, QSO-03, QSO-04, QSO-05, QSO-06

**Key design constraints:**
- `datagram_received()` is synchronous — all async work dispatched via `asyncio.create_task(_handle_datagram(data, addr))` with a `_background_tasks` set holding strong references.
- `_operator` is always sourced from `settings.udp_operator` — never from ADIF content in the datagram.
- Operator `User` document is fetched once at startup (lifespan) and cached — no MongoDB round-trip per datagram.
- Use `asyncio.get_running_loop()` (not deprecated `get_event_loop()`).

**Success Criteria:**

1. Sending a well-formed ADIF datagram (e.g., `<CALL:4>W1AW<BAND:3>20M<MODE:3>SSB<QSO_DATE:8>20260406<TIME_ON:4>1200<EOR>`) results in a QSO document inserted into MongoDB with `_operator` set to the value of `UDP_OPERATOR` — not to any value in the datagram.
2. The inserted QSO has all profile fields auto-stamped (OPERATOR, STATION_CALLSIGN when set, equipment fields) — identical to a QSO submitted via `POST /api/qsos/`.
3. A datagram missing any required field (CALL, BAND, MODE, QSO_DATE, TIME_ON) is rejected — no QSO is inserted and a log line explains which field was missing.
4. Sending the same valid datagram twice results in exactly one QSO in the database — the second datagram is detected as a duplicate and skipped.
5. Within 2 seconds of UDP insertion, the new QSO row appears in the live SSE station feed in the browser — no code changes to `app/feed/manager.py` are required.

---

### Phase 18: Error Handling and Observability

**Goal:** Every datagram outcome — accepted, rejected, or duplicate — is visible in structured log lines; the listener survives malformed input and OS-level transport errors without crashing; operators can diagnose the UDP path from logs alone.

**Dependencies:** Phase 17 (full pipeline in place)

**Requirements:** OBS-01, OBS-02, OBS-03

**Note:** OBS-04 (startup banner) is covered in Phase 16 and already mapped there.

**Success Criteria:**

1. Every accepted datagram produces a log line at INFO level containing: source IP:port, parsed callsign, and disposition `accepted`.
2. Every rejected datagram (missing required field or parse failure) produces a log line at WARNING level containing: source IP:port, disposition `rejected`, and the specific reason (e.g., `missing required field: BAND`).
3. Every duplicate datagram produces a log line at INFO level containing: source IP:port, callsign, and disposition `duplicate`.
4. Sending a binary garbage datagram (unparseable ADIF) produces exactly one WARNING log line and does not crash the listener — subsequent valid datagrams are processed normally.
5. A simulated transport error (e.g., `OSError` raised in `error_received()`) is logged at WARNING level and the listener continues running — it does not enter a stopped state.

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
| 16. UDP Infrastructure | v1.4 | 2/2 | ✓ Complete | 2026-04-05 |
| 17. QSO Processing Pipeline | v1.4 | 0/? | Pending | — |
| 18. Error Handling and Observability | v1.4 | 0/? | Pending | — |
