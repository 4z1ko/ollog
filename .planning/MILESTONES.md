# Milestones

## v3.7 Admin Log Controls (Shipped: 2026-06-20)

**Phases:** 70 (1 phase) | **Plans:** 1 | **Timeline:** 2026-06-20 → 2026-06-20 (1 day)
**Requirements:** 8/8 satisfied | **UAT:** 5/5 passed | **Audit:** PASS

**Key accomplishments:**

- Added current-browser Pause/Start controls to the admin Application Logs Recent Logs table with LIVE/PAUSED/OFFLINE status.
- Kept Pause scoped to automatic SSE row insertion and near-live polling only, preserving explicit filters, reset, Previous, and Next actions.
- Added a confirmation-gated Clear Log Messages action that deletes only `ApplicationLog` records.
- Added post-clear forced `application_logs_cleared` audit logging with safe admin/deleted-count metadata and audit-failure isolation.
- Documented the controls and added focused tests for pause/resume behavior, modal safety copy, clear route behavior, settings preservation, and audit continuity.
- Completed UAT, security review, Nyquist validation, and milestone audit with no critical gaps or tech debt.

**Stats:** 23 files changed, +1711 / -25 lines across planning, code, docs, templates, generated CSS, and tests; 11 commits in the v3.7 slice before final archive commits.

**Known deferred items at close:** 0 critical gaps. Future ideas remain out of scope: export/download filtered logs, clear by date range/filter, password-confirmed clear, global live-stream pause, and cross-node live-control coordination.

**Archive:** `.planning/milestones/v3.7-ROADMAP.md` | `.planning/milestones/v3.7-REQUIREMENTS.md` | `.planning/milestones/v3.7-MILESTONE-AUDIT.md` | `.planning/milestones/v3.7-phases/`

---

## v3.6 Internal Application Logging (Shipped: 2026-06-20)

**Phases:** 67–69 (3 phases) | **Plans:** 3 | **Timeline:** 2026-06-18 → 2026-06-20 (3 days)
**Requirements:** 17/17 satisfied | **UAT:** 18/18 passed | **Audit:** PASS

**Key accomplishments:**

- Added MongoDB-backed `ApplicationLog` and `ApplicationLogSettings` models with severity ordering, threshold settings, TTL retention, query indexes, and live broadcast plumbing.
- Added a reusable failure-isolated internal logger that masks sensitive metadata and MongoDB URI credentials before storage and broadcast.
- Added an admin Logs page with level/source/search/date filters, configurable minimum level and retention days, Previous/Next pagination, formatted collapsed JSON details, and live/near-live updates.
- Instrumented service lifecycle, MongoDB, QSO API/UI/import paths, UDP ingest/callbacks, ACLog live bridge/manual sync, authentication, token, admin, backup, restore, and log-settings flows.
- Fixed UAT-discovered live viewer issues: server-rendered live rows, cross-process polling fallback for manual sync logs, and preservation of open metadata/error detail sections during polling refresh.
- Completed focused tests, UAT, security review, Nyquist validation, and milestone audit with no critical gaps.

**Stats:** 59 files changed, +5539 / -87 lines across planning, code, docs, templates, generated CSS, and tests; 30 commits in the v3.6 slice before final archive commits.

**Known deferred items at close:** 0 critical gaps. Notes: formal `*-VERIFICATION.md` artifacts are absent for phases 67-69, with equivalent evidence in SUMMARY, UAT, SECURITY, VALIDATION, and milestone audit artifacts; full-suite MongoDB-backed tests remain host-environment-sensitive when the local replica-set hostname is unresolved.

**Archive:** `.planning/milestones/v3.6-ROADMAP.md` | `.planning/milestones/v3.6-REQUIREMENTS.md` | `.planning/milestones/v3.6-MILESTONE-AUDIT.md` | `.planning/milestones/v3.6-phases/`

---

## v3.5 ACLog Registered Operator Routing (Shipped: 2026-06-16)

**Phases:** 66 (1 phase) | **Plans:** 1 | **Timeline:** 2026-06-16 → 2026-06-16 (1 day)
**Requirements:** 9/9 satisfied | **UAT:** 6/7 passed, 1 optional external smoke skipped | **Audit:** PASS

**Key accomplishments:**

- Added ACLog record-level `OPERATOR` identity matching and made it the import gate for shared remote ACLog computers.
- Updated manual ACLog sync to skip missing or unmatched operator records before custom-field mapping or QSO ingest.
- Updated live ACLog bridge ingestion to skip unmatched full records and block identity-less `ENTEREVENT` fallback imports.
- Added Profile Settings sync report counts for missing and unmatched ACLog operator records.
- Documented shared remote ACLog behavior, recognized identity fields, and skipped-record troubleshooting.
- Completed focused tests, UAT, security review, Nyquist validation, and milestone audit with no critical gaps.

**Stats:** 18 files changed, +1281 / -70 lines across planning, code, docs, and tests; 6 commits in the v3.5 slice.

**Known deferred items at close:** 0 critical gaps. Notes: optional real shared-ACLog smoke test requires external station setup; local `ruff` smoke remains unavailable because `ruff` is not installed in the active virtual environment.

**Archive:** `.planning/milestones/v3.5-ROADMAP.md` | `.planning/milestones/v3.5-REQUIREMENTS.md` | `.planning/milestones/v3.5-MILESTONE-AUDIT.md`

---

## v3.4 Responsive Favicon (Shipped: 2026-06-13)

**Phases:** 65 (1 phase) | **Plans:** 1 | **Timeline:** 2026-06-13 → 2026-06-13 (1 day)
**Requirements:** 7/7 satisfied | **UAT:** 4/4 passed | **Audit:** PASS

**Key accomplishments:**

- Added `favicon/favicon.ico` as the source favicon and served matching ICO assets from app, docs, and generated guide paths.
- Added one shared ICO-only favicon link in `templates/base.html` so operator and admin full pages inherit it without per-page duplication.
- Configured MkDocs Material to use `assets/favicon.ico` and verified `uv run mkdocs build --strict` succeeds.
- Preserved HTMX partial templates, authentication flows, page behavior, styling, and existing static mounts.
- Completed UAT, security review, Nyquist validation, and milestone audit with no critical gaps.

**Known deferred items at close:** 0 critical gaps. Note: Phase 65 does not have a formal `*-VERIFICATION.md`; equivalent evidence is split across SUMMARY, UAT, SECURITY, VALIDATION, and milestone audit artifacts.

**Archive:** `.planning/milestones/v3.4-ROADMAP.md` | `.planning/milestones/v3.4-REQUIREMENTS.md` | `.planning/milestones/v3.4-MILESTONE-AUDIT.md`

---

## v3.3 ACLog QSO Sync (Shipped: 2026-06-13)

**Phases:** 64 (1 phase) | **Plans:** 1 | **Timeline:** 2026-06-12 → 2026-06-13 (2 days)
**Requirements:** 9/9 satisfied | **UAT:** 6/6 passed | **Audit:** Not run in this environment; Phase 64 UAT and verification artifacts passed

**Key accomplishments:**

- Added a saved-row-only Sync button to each configured ACLog bridge on the Profile Settings page.
- Added a manual ACLog sync helper that sends `<CMD><LIST><INCLUDEALL></CMD>`, parses full-record responses, and imports only addable records.
- Routed manual sync writes through the logged-in user's username-derived QSO collection while preserving duplicate, rowHash, profile stamping, and custom Other-field mapping behavior.
- Added an authenticated saved-bridge route and compact HTMX report with received, missing/imported, already-present, error, and example rejection counts.
- Preserved existing live ACLog bridge enrichment and fallback behavior.
- Updated operator documentation and focused tests for client, parser, profile UI, and collection routing behavior.

**Known deferred items at close:** formal milestone audit because `gsd-sdk` is unavailable.

**Archive:** `.planning/milestones/v3.3-ROADMAP.md` | `.planning/milestones/v3.3-REQUIREMENTS.md`

---

## v3.2 ACLog Full-Record Import (Shipped: 2026-06-09)

**Phases:** 63 (1 phase) | **Plans:** 1 | **Timeline:** 2026-06-08 → 2026-06-09 (2 days)
**Requirements:** 5/5 satisfied | **UAT:** 5/5 passed | **Audit:** Not run in this environment; Phase 63 UAT and verification artifacts passed

**Key accomplishments:**

- Added ACLog full-record parsing for `LIST INCLUDEALL` responses, preserving all non-empty safe ADIF-like fields.
- Updated the ACLog bridge to request `LIST INCLUDEALL` after each saved-QSO `ENTEREVENT` and ingest the enriched record only when it matches the pending event.
- Added deterministic merge behavior where full-record fields win, event fields fill gaps, and cached live textbox state provides fallback frequency, reports, and Other fields.
- Preserved ACLog `OTHER_1` through `OTHER_8` values and kept configured Custom QSO Field mapping intact.
- Preserved existing event-only fallback behavior for missing, nonmatching, or interrupted full-record responses.
- Added parser/client/custom-field coverage and updated operator ACLog bridge documentation.

**Known deferred items at close:** live ACLog end-to-end verification, local pytest execution in this shell, and formal milestone audit because `gsd-sdk` is unavailable.

**Archive:** `.planning/milestones/v3.2-ROADMAP.md` | `.planning/milestones/v3.2-REQUIREMENTS.md`

---

## v3.1 Per-User QSO Collections (Shipped: 2026-06-08)

**Phases:** 59–62 (4 phases) | **Plans:** 4 | **Timeline:** 2026-06-07 → 2026-06-08 (2 days)
**Requirements:** 25/25 satisfied | **UAT:** 21/21 passed | **Audit:** Not run in this environment; all phase UAT and verification artifacts passed

**Key accomplishments:**

- Added a single username-derived QSO collection routing foundation with strict `<username>_qsos` naming, validation, raw MongoDB access, and per-user index setup.
- Added a copy-only idempotent migration from the shared `qsos` collection into per-user collections, preserving rowHash, soft-delete state, ObjectIds, ADIF extras, profile-stamped fields, and custom fields.
- Routed REST, browser UI, service-layer CRUD, ADIF import/export/review, API-token, UDP, ACLog, custom defaults, and operator clear-log paths through the authenticated or resolved user's collection.
- Routed stats and admin clear-log to per-user collections while preserving UI shape, admin-owned password verification, and HTMX 200-fragment behavior.
- Replaced startup dependence on a shared `qsos` live-feed watcher with app-level broadcasts from successful write paths.
- Added dynamic collection backup/restore coverage and layered regression checks for representative QSO workflows, import/export, stats, admin, feed, UDP, custom fields, and SSE sentinels.

**Known deferred items at close:** optional migration-status admin UI, optional username rename tooling, and Docker/live-Mongo end-to-end verification.

**Archive:** `.planning/milestones/v3.1-ROADMAP.md` | `.planning/milestones/v3.1-REQUIREMENTS.md`

---

## v3.0 Configurable QSO Log Fields (Shipped: 2026-06-07)

**Phases:** 58 (1 phase) | **Plans:** 1 | **Timeline:** 2026-06-03 → 2026-06-07 (5 days)
**Requirements:** 17/17 satisfied | **UAT:** 5/5 passed | **Audit:** PASS

**Key accomplishments:**

- Shared QSO field catalog and extraction layer added for Log View rendering, with stable keys, human-readable labels, default metadata, and safe value formatting.
- Fresh-browser defaults preserved exactly: Date / Time, Callsign, Band, Mode, Frequency, and RST.
- Column configuration menu, table headers, view rows, and edit rows now render from the shared catalog while keeping the Actions column always visible.
- `ollog.log.columns` persistence preserved with stale/invalid key normalization and HTMX table-swap reapplication.
- Sort controls remain restricted to the existing Date/Time, entry timestamp, Callsign, Band, and Mode targets; non-sortable fields render plain headers.
- Focused verification passed: 7 pytest cases passed, 7 Mongo-dependent cases skipped cleanly, ruff passed, CSS build passed, and manual viewport UAT passed.

**Known deferred items at close:** 0 for v3.0.

**Archive:** `.planning/milestones/v3.0-ROADMAP.md` | `.planning/milestones/v3.0-REQUIREMENTS.md` | `.planning/milestones/v3.0-MILESTONE-AUDIT.md`

---

## v2.8 Clear Log (Shipped: 2026-05-18)

**Phases:** 54–56 (3 phases) | **Plans:** 6 | **Timeline:** 2026-05-06 → 2026-05-18 (13 days)
**Files changed:** 55 | **Source lines:** +685 / −1 | **Commits:** 49

**Key accomplishments:**

- `clear_operator_log(operator: str) -> int` async service in `app/qso/service.py` — single Beanie `delete_many({"_operator": <callsign>, "_deleted": False})` filter consumed by both operator and admin flows; no logic duplication, 6 async tests in `tests/test_clear_log.py` cover the path end-to-end
- Operator flow: Danger Zone card on `/log/profile` → `GET /log/profile/clear/modal` (live QSO count via Beanie) → `POST /log/profile/clear` gated by `verify_password(user.hashed_password)` → HTMX outerHTML swap to green success fragment; covers CLR-01..05
- Admin flow: per-operator "Clear log" button in `templates/admin/users_table.html` → 3 new admin routes (modal GET, confirm POST, cancel GET) all gated by `require_admin_cookie` → verify against admin's OWN password (`current_user.hashed_password`, NOT `target_user.hashed_password`) before calling Phase 54's service; covers ACLR-01..05
- Distinct modal target IDs (`#clear-log-modal` operator, `#admin-clear-log-modal` admin) and separate FastAPI sub-apps (port 8000 vs 8001) — zero DOM collision risk
- MkDocs Material `admonition` extension enabled in `mkdocs.yml`; `## Danger Zone` (operator-guide/profile.md) and `## Clear Operator Log` (admin-guide/account-management.md) sections with `!!! danger "This cannot be undone"` blocks rendered to styled HTML; `mkdocs build --strict` exits 0 with 0 warnings; covers DOC-01..03
- All 13 requirements verified, integration check PASS (13/13 wired, 5/5 routes auth-protected, 2/2 E2E flows complete), all 3 phases Nyquist-compliant after retroactive validation

**Known deferred items at close:** 2 (see STATE.md Deferred Items — visual-only HUMAN-UAT for Phase 54/55, behavioral coverage duplicated by passing integration tests)

**Archive:** `.planning/milestones/v2.8-ROADMAP.md` | `.planning/milestones/v2.8-REQUIREMENTS.md` | `.planning/milestones/v2.8-MILESTONE-AUDIT.md`

---

## v2.7 UTC Date/Time Entry (Shipped: 2026-05-02)

**Phases:** 52–53 (2 phases) | **Plans:** 3 | **Timeline:** 2026-04-26 → 2026-05-02 (7 days)
**Files changed:** 24 | **Lines:** +3,655 / −43 | **Commits:** 39

**Key accomplishments:**

- Idempotent `normalize_time_on()` startup migration pads all 4-digit `TIME_ON` records to `HHMM00` via anchored regex `^\d{4}$` + aggregation pipeline `$concat` — zero-op on re-run; 5 integration/unit tests covering DB-01 and DB-02
- `parse_adif_datetime()` in `app/qso/service.py` confirmed via explicit test coverage to accept both HHMM (4-digit) and HHMMSS (6-digit) — no code change needed (existing function satisfied DB-02)
- QSO_DATE and TIME_ON inputs wrapped in Heroicons padlock buttons — `readonly` (not `disabled`) so values always reach POST body; locked styling (grey background, `cursor-not-allowed`) renders before JS loads
- Live UTC clock via `setInterval` ticking `getUTCHours/Minutes/Seconds` exclusively — zero local-timezone leakage; stops on unlock, restarts on re-lock; `initDateTime()` is the canonical reset-to-locked entrypoint
- HHMM→HHMM00 normalization in `htmx:beforeRequest` before `validate()` fires; range-checking regex `/^([01]\d|2[0-3])([0-5]\d)([0-5]\d)$/` rejects out-of-range values (e.g. `9999→999900` fails hours=99)
- `localStorage`-backed reset-mode toggle ("Reset to live UTC" / "Keep current date/time") persists across page reloads; all 14 requirements (DB-01–02, DATE-01–04, TIME-01–05, RESET-01–03) browser-verified

**Archive:** `.planning/milestones/v2.7-ROADMAP.md` | `.planning/milestones/v2.7-REQUIREMENTS.md`

---

## v2.6 llms.txt Support (Shipped: 2026-04-25)

**Phases:** 51 (1 phase) | **Plans:** 3

**Key accomplishments:**

- `GET /llms.txt` and `GET /llms-full.txt` endpoints added to operator app via `FileResponse` (both `include_in_schema=False`)
- Static source files editable without touching Python code
- Full 610-line LLM reference document covering all 16 REST endpoints with curl examples, ADIF field reference tables, and operator getting-started walkthrough

**Archive:** `.planning/milestones/v2.6-ROADMAP.md` (not created — milestone archived inline)

---

## v2.5 QSO Sorting & Entry Timestamp (Shipped: 2026-04-23)

**Phases:** 48–50 (3 phases) | **Plans:** 3 | **Timeline:** 2026-04-21 → 2026-04-23 (3 days)
**Files changed:** 13 files | **Lines:** +629 / -27

**Key accomplishments:**

- `QSO._created_at` — UTC entry timestamp via `default_factory`, auto-stamped on all 4 insert paths (REST API, UI, UDP, ADIF import) with zero service-layer changes; protected from mutation in all PATCH handlers; excluded from API responses and ADIF exports
- `operator_created_at_idx` compound index `(_operator ASC, _created_at DESC)` created at startup; idempotent `backfill_created_at()` migration stamps pre-existing documents from their ObjectId timestamp
- `_ALLOWED_SORT_FIELDS` frozenset (10 values) in `get_qso_page()` — rejects arbitrary sort field names before reaching MongoDB, preventing field enumeration attacks; WARNING log on rejection
- MODE column sort header — ascending-first toggle, HTMX `hx-get` wired with full filter preservation in URL query string
- DATE header restructured — flex wrapper with date sort link + Heroicons clock icon link for `_created_at` sort (descending-first); SSE auto-refresh sentinel extended to fire on `-_created_at` sort
- Hollow double-chevron (`opacity-30 dark:opacity-25`) on all 5 inactive sortable elements; solid directional chevron on active sort — full visual sort state system

**Archive:** `.planning/milestones/v2.5-ROADMAP.md` | `.planning/milestones/v2.5-REQUIREMENTS.md`

---

## v2.4 Live Log & Sound Alerts (Shipped: 2026-04-20)

**Phases:** 44–47 (4 phases) | **Plans:** 5 | **Timeline:** 2026-04-16 → 2026-04-20 (4 days)
**Files changed:** ~32 files | **Commits:** 75

**Key accomplishments:**

- SSE watcher hardened — exception isolation (`try/except Exception`) in inner loop + `app.state.watcher_task` strong reference prevents Python 3.12+ GC from silently killing the live feed
- LIVE indicator message-first state machine — `eventsFlowing` sentinel turns green only on first `new_qso` SSE event, OFFLINE on error/close (not on bare connection open)
- `notify_sound: bool = False` on User model — per-operator sound preference persisted in MongoDB via profile form; hidden-input + checkbox pattern; no migration needed
- Web Audio API 440 Hz synthesized tone wired to SSE `new_qso` events with lazy `AudioContext` init on first user gesture — autoplay-policy compliant, zero external audio files
- Indigo pill badge above log table counts and dismisses new QSOs arriving while operator is on page 2+ or filtered view — DOM sibling placement survives HTMX SSE innerHTML swaps

**Archive:** `.planning/milestones/v2.4-ROADMAP.md` | `.planning/milestones/v2.4-REQUIREMENTS.md`

---

## v2.3 Operator Statistics (Shipped: 2026-04-16)

**Phases:** 42–43 (2 phases) | **Plans:** 2 | **Timeline:** 2026-04-16 (single session)
**Files changed:** 10 source files | **Tests:** 7 integration tests (100% pass)

**Key accomplishments:**

- `app/stats/service.py` — `get_stats()` with 3 JWT-isolated MongoDB aggregation pipelines (band, mode, CALL-level); Python-side DXCC rollup via `lookup_prefix()` + pycountry; top-8 truncation with "Other" guard; empty-state shape (STATS-06, STATS-07)
- `app/stats/router.py` — `stats_router` with `GET /log/stats` cookie-auth endpoint; registered in `app/main.py` with `include_in_schema=False`
- `templates/log/stats.html` — full Chart.js 4.5.1 stats page: 3 pie charts (By Band, By Mode, By DXCC Entity), dark/light palette switching via `themechange` CustomEvent, empty-state card, responsive 2-col grid (STATS-01–05, STATS-08)
- `templates/base.html` — `{% block extra_scripts %}` extension point established for page-specific scripts
- `templates/base_app.html` — Stats sidebar nav link; `CustomEvent('themechange')` broadcast in `toggleTheme()`
- Fixed `get_motor_collection()` → `get_pymongo_collection()` (Motor EOL May 2025); fixed `await collection.aggregate()` coroutine double-await pattern

---

## v1.0 MVP (Shipped: 2026-04-04)

**Phases:** 6 | **Plans:** 19 | **Timeline:** 2 days (2026-04-03 → 2026-04-04)
**LOC:** ~6,611 (Python + HTML) | **Files:** 122 | **Git commits:** 27+ feat

**Key accomplishments:**

- Custom ADIF tag-stream parser and serializer — UTF-8 byte-length handling, lossless APP_/USERDEF passthrough, full round-trip fidelity
- FastAPI + MongoDB (Beanie/pymongo async) multi-operator QSO logbook — JWT auth, soft-delete, ±2 min duplicate detection
- Admin HTMX UI — operator account management (create, enable/disable, reset password), role-enforced via JWT
- ADIF import/export — multipart file upload, per-record duplicate detection, streaming ADIF export, N+1 field passthrough
- MongoDB replica set upgrade + real-time SSE station feed — change streams, ConnectionManager asyncio.Queue broadcast, htmx-ext-sse DOM injection
- Programmatic operator isolation audit — route introspection verifies all 14+ QSO endpoints inject callsign from JWT, never from request body

**Archive:** `.planning/milestones/v1.0-ROADMAP.md` | `.planning/milestones/v1.0-REQUIREMENTS.md`

---

## v1.1 Operator & Station Profiles (Shipped: 2026-04-04)

**Phases:** 7–10 (4 phases) | **Plans:** 7 | **Timeline:** 1 day (2026-04-04)
**LOC:** ~7,465 (Python + HTML) | **Git commits:** 10+ feat

**Key accomplishments:**

- Extended User document with 12 Optional profile fields (personal info, station equipment, grid/location) — no migration required
- `grid_to_latlon()` Maidenhead utility with `center=True` — 17 unit tests, correct center-of-square coordinates (avoids up to 80 km SW-corner error)
- Profile REST API: GET/PATCH `/api/profile` with JWT-only operator derivation, lat/lon auto-sync on grid change, and full operator isolation (8 integration tests)
- QSO auto-stamping: `build_qso_dict()` extended with optional profile parameter — OPERATOR always, STATION_CALLSIGN/equipment conditionally; ADIF import path excluded by design
- Profile settings UI at `/log/profile` — HTMX inline save, OPERATOR read-only labeled distinctly from STATION_CALLSIGN, all station fields pre-populated
- Profile nav link added to all three log UI templates (form, log view, import) with consistent placement

**Archive:** `.planning/milestones/v1.1-ROADMAP.md` | `.planning/milestones/v1.1-REQUIREMENTS.md`

---

## v1.2 Callsign Entity Lookup & Country Flags (Shipped: 2026-04-04)

**Phases:** 11–12 (2 phases) | **Plans:** 2 | **Timeline:** 1 day (2026-04-04)
**LOC:** ~8,264 (Python + HTML) | **Git commits:** 3 feat

**Key accomplishments:**

- `app/callsign/prefixes.py` — pure-Python ITU prefix resolver: 313 Series Range entries, bisect-based longest-prefix-match, suffix stripping (`/MM`/`/AM` unresolvable, `/P`/`/7`/`/QRP` stripped, `EA3/G3YWX` prefix/callsign format)
- Solved ASCII digit/letter ordering problem with truncated bisect comparison + `_NOTFOUND` sentinel (ITU ranges use letter-padded keys like `WAA-WZZ` while callsigns contain digits like `W1AW`)
- 28-test suite covering PRFX-01–04 — common DX prefixes, overlapping sub-ranges (Eswatini vs Fiji), maritime/aeronautical mobile, non-country entities
- 271 SVG flag files relocated to `static/flags/` (now reachable by `StaticFiles` mount at `/static/flags/*.svg`)
- Render-time flag enrichment in `_qso_to_view_dict()` — single injection point for all 4 template render paths via `lookup_prefix()` + `pycountry`
- Conditional `<img>` tag in `qso_row.html` with country name tooltip (`title` attribute), graceful no-flag fallback for unresolvable callsigns

**Archive:** `.planning/milestones/v1.2-ROADMAP.md` | `.planning/milestones/v1.2-REQUIREMENTS.md`

---

## v1.3 Documentation (Shipped: 2026-04-05)

**Phases:** 13–15 (3 phases) | **Plans:** 8 | **Timeline:** 2 days (2026-04-03 → 2026-04-05)
**LOC:** +18,033 lines (89 files, mostly `site/` static build) | **Git commits:** 20+ feat/docs

**Key accomplishments:**

- All 16 REST endpoints annotated with typed Pydantic response models — QSOResponse (alias-aware `_operator`/`_deleted`), ADIFImportReport (per-record typed sub-models), StreamingResponse export; Swagger UI now shows complete schemas
- HTMX browser routes and SSE feed excluded from OpenAPI schema via `include_in_schema=False` — `/docs` shows only REST endpoints, no HTML fragment routes
- MkDocs Material 9.x build pipeline: `site_url` trailing-slash sub-path config, dev-only dep, `site/` committed and served via `StaticFiles(html=True)` at `/guide` — no MkDocs in production Docker image
- Complete 7-page documentation site at `/guide`: deployment guide, operator getting-started walkthrough, admin account management guide, full API reference with curl examples for all 16 endpoints, ADIF field format reference, troubleshooting
- Both auth flows documented with rationale: Bearer token (REST endpoints) and HttpOnly cookie (SSE/EventSource cannot send custom headers)

**Archive:** `.planning/milestones/v1.3-ROADMAP.md` | `.planning/milestones/v1.3-REQUIREMENTS.md`

---

## v1.4 UDP Interface (Shipped: 2026-04-06)

**Phases:** 16–18 (3 phases) | **Plans:** 4 | **Timeline:** 1 day (2026-04-06)

**Key accomplishments:**

- `asyncio.DatagramProtocol` UDP listener (`app/udp/server.py`): configurable port (default 2399), bind host, operator; starts/stops with FastAPI lifespan
- `_handle_datagram` pipeline: `parse_adi()` → validate `_REQUIRED_FIELDS` → `build_qso_dict(profile=user)` → `find_duplicate` → `QSO.insert()` — identical auto-stamping and duplicate detection as REST API path
- Operator `User` document cached once at startup; `UDP_OPERATOR` config pins identity — never derived from datagram ADIF content, preventing spoofing across overnight FT8 sessions
- Structured `disposition=accepted|rejected|duplicate` log tokens with `src=IP:PORT call=CALLSIGN` on every outcome branch; single `if parse_errors or not records:` guard eliminates double-WARNING for binary garbage

**Archive:** `.planning/milestones/v1.4-ROADMAP.md` | `.planning/milestones/v1.4-REQUIREMENTS.md`

---

## v1.5 Documentation Update (Shipped: 2026-04-08)

**Phases:** 19–22 (4 phases) | **Plans:** 4 | **Timeline:** 1 day (2026-04-08)
**Files changed:** 22 | **Lines:** +2,439 / -15

**Key accomplishments:**

- `docs/deployment.md` — 4 UDP env var rows (corrected port 2399, not 2237 from stale requirements) + "Enabling the UDP Listener" section with Docker Compose snippet calling out `UDP_BIND_HOST=0.0.0.0` for Docker
- `docs/getting-started.md` — Step 8 "Send QSOs via UDP": nc one-liner, Log4OM direct ADIF UDP steps, honest WSJT-X/N1MM+ incompatibility notes (binary/XML formats) with file-import workarounds
- `docs/troubleshooting.md` — 4 UDP troubleshooting entries with verbatim log strings from `app/udp/server.py` so operators can grep-match against live output; covers socket binding, both UDP_OPERATOR sub-cases, QSO disposition, and UDP_ENABLED
- Static site rebuilt with mkdocs-material 9.7.6 — `/guide` reflects all UDP documentation; installed via `pip3 --break-system-packages` (macOS PEP 668)

**Archive:** `.planning/milestones/v1.5-ROADMAP.md` | `.planning/milestones/v1.5-REQUIREMENTS.md`

---

## v1.6 Live Log Table (Shipped: 2026-04-08)

**Phases:** 23–24 (2 phases) | **Plans:** 2 | **Timeline:** 1 day (2026-04-08)
**Files changed:** 5 | **Lines:** +343 / -10

**Key accomplishments:**

- `htmx:sseMessage` listener on `#log-table` fires `htmx.ajax('GET', '/log/view')` on `new_qso` events — new QSOs appear in log table within seconds, no page reload required
- Server-side `#auto-refresh-ok` sentinel span rendered only at page 1 + default sort + no filters — auto-refresh silently suppressed during pagination, filtering, and sorting
- Client-side `#log-table input` guard blocks refresh while any inline edit row is open — unsaved edits are never destroyed
- LIVE/OFFLINE indicator badge in nav bar wired to `htmx:sseOpen`/`htmx:sseError`/`htmx:sseClose` events reflecting live SSE connection state
- `jwt_expire_minutes` default raised from 60 → 480 minutes in `app/config.py` — operators can run full 8-hour FT8 sessions without session expiry

**Archive:** `.planning/milestones/v1.6-ROADMAP.md` | `.planning/milestones/v1.6-REQUIREMENTS.md`

---

## v1.9 Admin & Login UI Redesign (Shipped: 2026-04-13)

**Phases completed:** 36 phases, 62 plans, 0 tasks

**Key accomplishments:**

- (none recorded)

---

## v2.0 Database Backup (Shipped: 2026-04-14)

**Phases:** 37–38 (2 phases) | **Plans:** 2 | **Timeline:** 11 days (2026-04-03 → 2026-04-14)
**Files changed:** 5 core files | **Lines:** +113 / -34

**Key accomplishments:**

- Wired existing `run_backup()` engine to `GET /admin/ui/backup/download` — cookie-protected, streams timestamped `.gz` file directly to browser
- Sync/async split in `dump.py`: sync `_write_backup` (MongoClient) + async `run_backup` orchestrator via `asyncio.to_thread` — event loop never blocked during backup I/O
- Added `./backups:/app/backups` Docker volume mount to `admin` service — backup files persist across container restarts
- Created `templates/admin/backup.html` with Apple-style card layout and plain `<a href>` download anchor (zero `hx-*` attributes — HTMX silently discards binary `Content-Disposition` responses)
- Updated admin sidebar on both Operators and Backup pages with correct active states — full nav between admin pages

**Archive:** `.planning/milestones/v2.0-ROADMAP.md` | `.planning/milestones/v2.0-REQUIREMENTS.md`

---

## v2.1 Database Restore (Shipped: 2026-04-14)

**Phases:** 39–40 (2 phases) | **Plans:** 2 | **Timeline:** 2026-04-14 (single session)
**Files changed:** 24 files | **Lines:** +2647 / -11

**Key accomplishments:**

- `app/backup/restore.py` — sync `_restore_from_file` (MongoClient + `bson.json_util.loads`) + async `run_restore` via `asyncio.to_thread`, mirroring `dump.py` pattern exactly
- `POST /restore/upload` validates gzip decompressibility + NDJSON structure, writes tempfile, returns password modal fragment on success or inline error at HTTP 200
- `POST /restore/confirm` enforces path traversal guard, password verification, auto-backup before any `db.drop()`, full drop+restore all collections, finally-block tempfile cleanup
- Admin Restore page at `/admin/ui/restore` with HTMX-wired `.gz` file upload form, modal CSS component classes, and auth gate — no page reloads
- Password confirmation modal with blurred backdrop (`modal-backdrop`, `modal-box` CSS classes compiled into output.css) — all three admin pages show three-link sidebar nav

**Archive:** `.planning/milestones/v2.1-ROADMAP.md` | `.planning/milestones/v2.1-REQUIREMENTS.md`

---

## v2.2 Multi-Operator UDP (Shipped: 2026-04-15)

**Phases:** 41 (1 phase) | **Plans:** 2 | **Timeline:** 2026-04-15 (single session)
**Files changed:** 18 files | **Lines:** +485 / -66

**Key accomplishments:**

- `app/udp/operator_cache.py` — UDPOperatorCache class with `load()/resolve()/notify_refresh()` dirty-flag singleton, mirroring token_cache.py pattern exactly; O(1) callsign lookup, zero per-datagram MongoDB queries
- `_handle_datagram` routes via OPERATOR ADIF field: `record.pop()` → resolve via operator_cache → drop+WARN if unknown callsign; stale early guard replaced by post-resolution no-operator guard
- `operator_cache.load()` wired at startup in main.py alongside token_cache; `notify_refresh()` hooks added to all 4 operator mutation sites in admin/router.py and admin/ui_router.py
- UDP_OPERATOR env var demoted to optional fallback — documented in deployment.md, udp-adif.md, environment-variables.md; Docker Compose examples updated to comment out optional var
- Multi-Operator Routing section added to udp-adif.md with example datagram and 4-step routing-order list; mkdocs rebuilt with `--strict` flag

**Archive:** `.planning/milestones/v2.2-ROADMAP.md` | `.planning/milestones/v2.2-REQUIREMENTS.md`

---
