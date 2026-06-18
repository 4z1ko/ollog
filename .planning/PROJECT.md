# ollog — Ham Radio Online Logbook

## What This Is

A self-hosted, ADIF-native, multi-operator logbook for amateur radio operators. Each operator maintains their own individual logbook identified by their callsign. Operators log QSOs in real-time via REST API or browser web UI, import/export full ADIF logbooks, and see each other's QSOs appear live in a shared station feed. All QSO data is stored using native ADIF field names, enabling seamless round-trip import/export with external logging tools. Each operator has a profile with personal info, station details, and grid location — auto-stamped onto every new QSO they log. Complete operator and admin documentation is available at `/guide` (deployment guide, operator walkthrough, API reference, ADIF field reference, troubleshooting).

## Core Value

Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss — the shared platform stays out of their way and just works.

## Current State

**Shipped through:** v3.5 ACLog Registered Operator Routing (2026-06-16)
**Current milestone:** v3.6 Internal Application Logging

Operators now store QSO records in dedicated MongoDB collections named `<username>_qsos`. Legacy shared `qsos` data can be migrated idempotently into per-user collections, and runtime QSO workflows route by authenticated or resolved `User.username` while keeping `_operator` callsign semantics for ADIF/profile/display compatibility.

The ACLog bridge now enriches saved QSO events by requesting ACLog `LIST INCLUDEALL` full-record data, preserving non-empty ADIF-like fields including ACLog Other fields, mapping configured custom fields, and manually syncing saved ACLog bridges from Profile Settings into each operator's username-derived collection.

All operator/admin full-page web surfaces now inherit one shared ICO favicon based on `favicon/favicon.ico` through the shared base template. The generated `/guide` site uses the same favicon through MkDocs Material configuration.

Shared remote ACLog computers are safe for multiple ollog operators: live bridge imports and manual sync records are filtered through ACLog record-level `OPERATOR` identity, and missing or unmatched ACLog operator records are skipped and reported instead of being imported to the bridge owner's collection.

## Current Milestone: v3.6 Internal Application Logging

**Goal:** Give administrators MongoDB-backed operational visibility into QSO ingestion, bridge connectivity, and service health without exposing secrets or changing existing QSO behavior.

**Target features:**
- Reusable internal application logger with configurable `Trace`, `Debug`, `Info`, `Warn`, `Error`, and `Fatal` thresholding.
- MongoDB log storage with structured metadata, sensitive-value masking, indexes, live broadcast support, and default 30-day retention.
- Admin configuration and live log viewer with filters for level, source/module, text, and date/time range.
- Focused instrumentation of startup/shutdown, MongoDB, HTTP/UDP/ACLog ingestion, QSO validation/insert/duplicate decisions, auth/admin actions, and log configuration changes.

## Shipped: v2.8 Clear Log (2026-05-18)

**Goal achieved:** Operators can permanently delete all their QSOs from the profile page; admins can clear any operator's log from the admin console — both gated behind password confirmation against the requester's OWN hashed password. A single `clear_operator_log()` service powers both flows. Guide documentation updated with Danger Zone and Clear Operator Log sections rendered as `!!! danger` admonitions; MkDocs site rebuilt with the admonition extension. All 13 requirements (CLR-01..05, ACLR-01..05, DOC-01..03) verified; integration check PASS; all 3 phases Nyquist-compliant.

## Shipped: v2.7 UTC Date/Time Entry (2026-05-02)

**Goal achieved:** Log QSO form now displays live UTC date/time by default with padlock toggles, HHMMSS precision (idempotent DB migration for existing records), and a `localStorage`-backed post-submit reset mode. All 14 requirements (DB-01–02, DATE-01–04, TIME-01–05, RESET-01–03) verified in a live browser session.

## Requirements

### Active

- [ ] Administrators can configure the internal application minimum log level from the admin area, defaulting to `Info`.
- [ ] Internal application logs are stored in MongoDB only when they meet or exceed the configured threshold.
- [ ] Administrators can view recent application logs in a live-updating admin page with level/source/text/date filters.
- [ ] Application log records include timestamp, level, source/module, message, event type, correlation/request ID when available, QSO/bridge/remote-software/transport context when relevant, structured metadata, and sanitized error details.
- [ ] Log retention prevents unbounded MongoDB growth, defaulting to 30 days.
- [ ] Important service, QSO ingestion, UDP, ACLog bridge, authentication, and admin configuration events are logged without exposing passwords, API keys, tokens, secrets, or full connection strings.

### Validated (v3.5)

- ✓ **ACOP-01:** ollog can identify an ACLog record's operator identity from full-record API data using record-level `OPERATOR` — Phase 66.
- ✓ **ACOP-02:** Manual ACLog sync imports only remote QSOs whose ACLog operator identity matches the authenticated ollog operator's callsign/profile identity — Phase 66.
- ✓ **ACOP-03:** Live ACLog bridge ingestion imports only saved ACLog QSOs whose ACLog operator identity matches the ollog operator who owns the bridge — Phase 66.
- ✓ **ACOP-04:** ACLog records with missing, blank, or unmatched operator identity are skipped and counted/reported instead of being imported into the bridge owner's collection — Phase 66.
- ✓ **ACOP-05:** Two ollog operators can point saved ACLog bridges at the same remote ACLog computer without importing each other's QSOs — Phase 66.
- ✓ **ACOP-06:** Existing full-record import behavior remains intact for all matching records, including non-empty returned fields, Other/custom-field mapping, duplicate handling, rowHash behavior, and per-user `<username>_qsos` collection routing — Phase 66.
- ✓ **ACOP-07:** Profile Settings sync reports include operator-filter results, including matched/imported records, skipped missing-operator records, skipped unmatched-operator records, duplicates/already-present records, and errors — Phase 66.
- ✓ **ACOP-08:** Tests cover parser/operator-field detection, manual sync filtering, live bridge filtering, skip/report behavior, and the shared-remote two-operator scenario — Phase 66.
- ✓ **ACOP-09:** Operator documentation explains how shared ACLog remote computers are handled, which ACLog operator identity fields ollog recognizes, and why records without a matching identity are skipped — Phase 66.

### Validated (v3.6 Phase 67)

- ✓ **LOG-01:** MongoDB-backed `ApplicationLog` and `ApplicationLogSettings` models are registered with Beanie — Phase 67.
- ✓ **LOG-02:** Internal logger applies configured level thresholding with default `Info` behavior — Phase 67.
- ✓ **LOG-03:** Sensitive metadata and MongoDB URI credentials are masked before log storage and broadcast — Phase 67.
- ✓ **LOG-04:** Log records include structured operational context fields and sanitized error details — Phase 67.
- ✓ **LOG-05:** Retention uses an `expires_at` TTL index with default 30-day behavior and supporting query indexes — Phase 67.
- ✓ **LOG-06:** Live broadcast plumbing and focused tests verify logger behavior without requiring live MongoDB for core unit coverage — Phase 67.

### Validated (v3.4)

- ✓ **FAV-01:** Every full-page operator web page includes a favicon link based on `favicon/favicon.ico` — Phase 65.
- ✓ **FAV-02:** Every full-page admin web page includes a favicon link based on `favicon/favicon.ico` — Phase 65.
- ✓ **FAV-03:** The favicon is served from an app-accessible static URL in both the operator app and admin app — Phase 65.
- ✓ **FAV-04:** Shared template wiring adds favicon metadata once without duplicating tags across individual pages — Phase 65.
- ✓ **FAV-05:** Partial HTMX templates remain unchanged and do not gain invalid standalone `<head>` favicon markup — Phase 65.
- ✓ **FAV-06:** Browser-friendly responsive favicon metadata is available for modern desktop browsers using the ICO source and MkDocs guide configuration — Phase 65.
- ✓ **FAV-07:** Existing page behavior, authentication, HTMX swaps, styling, and guide/static serving remain unchanged — Phase 65.

### Validated (v3.3)

- ✓ **ACSYNC-01:** Operator can start a manual sync for an enabled configured ACLog bridge from Profile Settings — Phase 64.
- ✓ **ACSYNC-02:** Sync requests all remote ACLog QSOs with `<CMD><LIST><INCLUDEALL></CMD>` — Phase 64.
- ✓ **ACSYNC-03:** Sync parses all returned full-record responses and preserves non-empty safe ADIF-like fields, including Other fields — Phase 64.
- ✓ **ACSYNC-04:** Sync inserts only QSOs missing from the authenticated operator's username-derived collection and skips existing duplicates — Phase 64.
- ✓ **ACSYNC-05:** Operator sees an inline sync report with imported/missing count and useful totals/errors after the process finishes — Phase 64.
- ✓ **ACSYNC-06:** Existing ACLog live bridge behavior, profile saving, and custom QSO field mapping continue to work unchanged — Phase 64.
- ✓ **ACSYNC-07:** Sync is available only for saved bridge rows and preserves unsaved draft bridge behavior — Phase 64.
- ✓ **ACSYNC-08:** Sync failures use a fixed timeout and report failure inline without saving partial UI state — Phase 64.
- ✓ **ACSYNC-09:** Duplicate remote QSOs are skipped and counted as duplicates using exact `rowHash` matching before insert — Phase 64.

### Validated (v3.2)

- ✓ **ACLOG-FULL-01:** ACLog bridge can request and parse full-record data using ACLog's `INCLUDEALL` API flow after a saved QSO event — Phase 63.
- ✓ **ACLOG-FULL-02:** ACLog imports preserve all non-empty fields exposed by ACLog, not only the `ENTEREVENT` subset — Phase 63.
- ✓ **ACLOG-FULL-03:** ACLog Other fields map to the operator's configured Custom QSO Fields when configured and remain safely preserved otherwise — Phase 63.
- ✓ **ACLOG-FULL-04:** Existing `ENTEREVENT` plus live textbox update behavior remains as a fallback for older ACLog versions or timing edge cases — Phase 63.
- ✓ **ACLOG-FULL-05:** Tests cover parser behavior, full-record merge precedence, Other field mapping, and bridge ingestion compatibility — Phase 63.

### Validated (v3.1)

- ✓ **UCOLL-01:** Each user has a dedicated MongoDB QSO collection named exactly `<username>_qsos` — Phases 59–62.
- ✓ **UCOLL-02:** All QSO reads/writes dynamically target the collection derived from the authenticated or resolved `User.username` — Phases 59, 61, 62.
- ✓ **UCOLL-03:** Existing shared-collection QSO data is migrated idempotently into per-user collections without data loss — Phase 60.
- ✓ **UCOLL-04:** Existing QSO workflows remain externally unchanged across REST, browser UI, ADIF, UDP, stats, admin, and live-feed paths — Phases 61–62.
- ✓ **UCOLL-05:** Tests cover collection-name derivation, migration behavior, operator isolation, and representative CRUD/import/export flows — Phases 59–62.

### Validated (v3.0)

- ✓ **FIELDS-01:** The Log View configuration menu lists every selectable QSO field from the supported display catalog, including core fields, profile-stamped fields, common ADIF fields, app-specific fields, and safe internal display fields — Phase 58.
- ✓ **FIELDS-02:** A fresh browser uses the current default visible columns: Date / Time, Callsign, Band, Mode, Frequency, and RST — Phase 58.
- ✓ **FIELDS-03:** Operators can select or deselect any configurable field without hiding the Actions column or breaking row actions — Phase 58.
- ✓ **FIELDS-04:** The selected column set persists across page loads and HTMX partial table swaps — Phase 58.
- ✓ **FIELDS-05:** The table header and every QSO row render selected fields from the same field catalog, using ADIF-native field names and human-readable labels — Phase 58.
- ✓ **FIELDS-06:** Unknown or absent values render as blank cells without raising template errors — Phase 58.
- ✓ **FIELDS-07:** Existing sort, filter, pagination, inline edit, delete, SSE auto-refresh, LIVE indicator, new-QSO badge, and sound-notification behavior continue to work with configurable columns — Phase 58.
- ✓ **FIELDS-08:** The column menu remains usable on desktop and mobile, with a scrollable bounded menu and readable labels in light and dark themes — Phase 58.
- ✓ **FIELDS-09:** Tests cover field catalog construction, row value extraction, default/persisted column behavior, and HTMX partial refresh compatibility — Phase 58.

### Validated (v1.0)

- ✓ Operators can be created and managed by an admin (no self-registration) — v1.0
- ✓ Each operator authenticates with username/password and has their own individual logbook — v1.0
- ✓ Operators can log QSOs via REST API using ADIF field format in real-time — v1.0
- ✓ Operators can log QSOs via web UI (callsign, band, mode, RST, date/time, and all ADIF fields) — v1.0
- ✓ QSOs are stored internally using ADIF field names as the data model (MongoDB) — v1.0
- ✓ Operators can import existing logbooks via .adi/.adif file upload — v1.0
- ✓ Operators can export their logbook as an ADIF file — v1.0
- ✓ Multiple operators can log simultaneously without data conflicts — v1.0
- ✓ Operators can search and filter their QSO history (by callsign, band, mode, date) — v1.0
- ✓ Basic duplicate detection (warn if callsign already worked on same band/mode within ±2 min) — v1.0

### Validated (v1.1)

- ✓ Operator profile stores OPERATOR callsign (from login) and optional STATION_CALLSIGN — v1.1
- ✓ Operator profile stores personal info: name, email, QTH city, state/province, country — v1.1
- ✓ Operator profile stores Maidenhead grid locator (MY_GRIDSQUARE, 4- or 6-char) — v1.1
- ✓ Operator profile stores decimal lat/lon auto-derived from grid square (center, not SW corner) — v1.1
- ✓ Operator profile stores station equipment: MY_RIG, MY_ANTENNA, TX_PWR — v1.1
- ✓ New QSOs logged via UI or REST API are auto-stamped with OPERATOR from profile — v1.1
- ✓ STATION_CALLSIGN only stamped when set in profile (omitted entirely when blank) — v1.1
- ✓ ADIF import path is NOT auto-stamped — historical records preserved as-is — v1.1
- ✓ Operators can retrieve and update their own profile via GET/PATCH /api/profile (JWT auth) — v1.1
- ✓ Profile API enforces operator isolation — cannot read/write another operator's profile — v1.1
- ✓ Operator has a profile settings page at /log/profile with an HTMX form — v1.1
- ✓ Profile form distinguishes OPERATOR (read-only) from STATION_CALLSIGN with explanatory note — v1.1
- ✓ Profile page accessible via navigation link in the log UI — v1.1

### Validated (v1.2)

- ✓ ITU callsign prefix range data bundled at runtime (313 Series Range entries, pure-Python) — v1.2
- ✓ Callsign → country/entity resolver (range-aware, handles sub-ranges like 3DA–3DM vs 3DN–3DZ) — v1.2
- ✓ Country name → ISO 3166-1 alpha-2 mapping (to match flag SVG filenames) — v1.2
- ✓ Flag icon rendered next to callsign in QSO log table rows (display-only, no QSO data stored) — v1.2
- ✓ Graceful fallback when no prefix match found (no flag shown, no error) — v1.2
- ✓ Maritime/aeronautical mobile suffixes (/MM, /AM) treated as unresolvable — v1.2

### Validated (v1.4)

- ✓ Operator can enable a UDP listener on a configurable port (`UDP_PORT` env var, default `2399`) by setting `UDP_ENABLED=true` — v1.4
- ✓ Operator can configure the bind address via `UDP_BIND_HOST` env var (default `127.0.0.1`; set `0.0.0.0` for LAN access) — v1.4
- ✓ Operator can configure which user account receives UDP-submitted QSOs via `UDP_OPERATOR` env var (operator callsign) — v1.4
- ✓ UDP listener starts automatically on app startup and stops cleanly on shutdown (FastAPI lifespan integration) — v1.4
- ✓ Docker Compose exposes the UDP port with `/udp` suffix so datagrams are not silently dropped — v1.4
- ✓ App accepts raw ADIF ADI text as the entire UDP datagram payload and parses it using the existing `parse_adi()` function — v1.4
- ✓ App validates required ADIF fields (CALL, BAND, MODE, QSO_DATE, TIME_ON) before inserting — invalid records are rejected and logged — v1.4
- ✓ `_operator` field on every UDP-submitted QSO is set from `UDP_OPERATOR` config — never from datagram ADIF content — v1.4
- ✓ UDP-submitted QSOs receive the same profile auto-stamping as REST API QSOs (OPERATOR, STATION_CALLSIGN, equipment fields from profile) — v1.4
- ✓ Duplicate detection applies to UDP-submitted QSOs using the same ±2 min CALL+BAND+MODE+operator window as the REST API — v1.4
- ✓ UDP-inserted QSOs appear in the SSE live station feed without any additional changes — v1.4
- ✓ App logs accepted, rejected, and duplicate datagrams with: source IP:port, callsign (if parsed), disposition, and reason — v1.4
- ✓ Malformed ADIF datagrams (parse failure) are logged at WARNING level and silently dropped — app does not crash — v1.4
- ✓ UDP listener transport errors are caught in `error_received()` and logged — listener continues running — v1.4
- ✓ App logs a startup banner confirming UDP listener is bound when `UDP_ENABLED=true` — v1.4

### Validated (v1.6)

- ✓ Operator's log view table auto-refreshes when a new QSO is inserted while viewing page 1 with no active filters — v1.6
- ✓ Auto-refresh fires a re-fetch of `/log/view` (SSE-triggered via `/feed/station`) — operator QSO isolation preserved via JWT on every re-fetch — v1.6
- ✓ Auto-refresh suppressed on page 2+, active filters, or non-default sort (server-side `#auto-refresh-ok` sentinel) — v1.6
- ✓ Auto-refresh suppressed while inline QSO edit row is open (`#log-table input` guard) — v1.6
- ✓ LIVE/OFFLINE indicator badge in nav bar reflects SSE connection state — v1.6
- ✓ JWT session lifetime configurable via `JWT_EXPIRE_MINUTES` env var; default raised to 480 min for overnight FT8 sessions — v1.6

### Validated (v1.5)

- ✓ `docs/deployment.md` documents all four UDP env vars (`UDP_ENABLED`, `UDP_PORT`, `UDP_BIND_HOST`, `UDP_OPERATOR`) with types, defaults, and descriptions — v1.5
- ✓ `docs/deployment.md` includes a Docker Compose snippet showing port `2399:2399/udp` mapping and required env vars — v1.5
- ✓ `docs/getting-started.md` Step 8 explains ADIF UDP datagrams are logged under `UDP_OPERATOR` callsign — v1.5
- ✓ nc one-liner example for manual UDP testing is present with port 2399, -u/-w1 flags, all five required ADIF fields — v1.5
- ✓ WSJT-X menu path documented with explicit note that binary-framed output is incompatible; ADIF file import workaround provided — v1.5
- ✓ N1MM+ menu path documented with explicit note that XML output is incompatible; ADIF export/import workaround provided — v1.5
- ✓ Log4OM direct ADIF UDP integration steps documented (Setup > Connections, port 2399) as the only compatible direct path — v1.5
- ✓ Four UDP troubleshooting entries in `docs/troubleshooting.md` with verbatim log strings from `app/udp/server.py` — v1.5
- ✓ Static site rebuilt with mkdocs-material 9.7.6; `/guide` now reflects all UDP documentation — v1.5

### Validated (v1.3)

- ✓ Every QSO endpoint in Swagger shows fully typed response schema (QSOResponse with alias-aware fields) — v1.3
- ✓ POST /api/qsos shows 409 DuplicateQSOError schema and force=true query param description — v1.3
- ✓ ADIF import shows typed ADIFImportReport model; export annotated with text/plain StreamingResponse — v1.3
- ✓ ADIF request fields carry description strings explaining format conventions (YYYYMMDD, HHMM/HHMMSS, band designators) — v1.3
- ✓ HTMX browser routes (/log/*, /admin/ui/*) absent from Swagger UI and /openapi.json — v1.3
- ✓ SSE feed route (/feed/station) excluded from OpenAPI schema — v1.3
- ✓ mkdocs-material dev dependency only (not in production Docker image) — v1.3
- ✓ mkdocs.yml configured with Material theme, site_url at /guide/ (trailing slash for sub-path asset resolution) — v1.3
- ✓ uv run mkdocs build --strict completes without errors — v1.3
- ✓ site/ built and committed to repo; Dockerfile gains COPY site/ site/ — v1.3
- ✓ /guide endpoint serves MkDocs site via FastAPI StaticFiles (html=True, mounted before /static) — v1.3
- ✓ Deployment guide covers prerequisites, .env setup, docker compose up -d, bootstrap admin, verification — v1.3
- ✓ Operator getting-started walkthrough: login → profile (OPERATOR vs STATION_CALLSIGN explained) → QSO via UI → QSO via API → import → export → station feed — v1.3
- ✓ Admin guide: create/enable-disable/reset-password operators, last-admin lockout guard documented — v1.3
- ✓ API reference: all 16 endpoints with method, auth, request/response, status codes, curl examples — v1.3
- ✓ Both auth flows documented with rationale: Bearer token (REST) and HttpOnly cookie (SSE/EventSource) — v1.3
- ✓ ADIF field reference: QSO_DATE, TIME_ON, BAND, MODE, OPERATOR vs STATION_CALLSIGN format tables — v1.3
- ✓ Troubleshooting: SSE not updating (replica set), login fails after restart (SECRET_KEY/JWT), ADIF import all duplicates (delete-then-import) — v1.3

### Validated (v1.9)

- ✓ Toggle button fixed at bottom of sidebar nav (admin + operator), showing sun/moon icon for current mode — v1.9
- ✓ Selected theme persists across page loads via localStorage — v1.9
- ✓ Page loads without theme flash — FOUC-prevention inline script preserved and annotated as load-bearing — v1.9
- ✓ Browser native controls (scrollbars, form inputs) respect active theme via `color-scheme` meta tag — v1.9
- ✓ Theme icon stays correct after HTMX partial swaps (`htmx:afterSettle` handler) — v1.9
- ✓ Theme transitions animate on user-initiated toggle only — no color-fade animation on page load — v1.9
- ✓ Apple background colors applied (canvas: `#f2f2f7`/`#0f0f0f`, card surface: white/`#1c1c1e`) — v1.9
- ✓ System font stack (`-apple-system, BlinkMacSystemFont`) applied globally, CDN font link removed — v1.9
- ✓ Card shadows use two-layer depth in light mode, removed in dark mode — v1.9
- ✓ Status badges use rectangular shape (`rounded-md`) instead of pill (`rounded-full`) — v1.9
- ✓ Section headers use sentence-case `font-semibold` typography, no uppercase letter-spacing — v1.9
- ✓ Nav/card icons sized at `w-6 h-6` (24px, 1:1 Heroicons viewBox); secondary button icons at `w-4 h-4` — v1.9
- ✓ Admin operator management table redesigned with Apple card container and refined tokens — v1.9
- ✓ Admin sidebar uses Apple dark surface (`#1c1c1e`), generous padding, properly-spaced nav items — v1.9
- ✓ Operator action buttons (enable/disable/reset) have `aria-label` attributes and correctly-sized icons — v1.9
- ✓ Admin login card redesigned with Apple glassmorphism (`glass-card`, `shadow-2xl`, semi-transparent border) — v1.9
- ✓ Operator login card redesigned with the same Apple glass card pattern — v1.9
- ✓ Glass card renders correctly in Safari (explicit `-webkit-backdrop-filter` with fixed pixel values) — v1.9
- ✓ Operator log view (`log.html`, `log_table.html`) uses Apple component tokens; dark mode preserved through SSE swaps — v1.9
- ✓ Operator QSO form (`form.html`) uses Apple form input and button styles — v1.9
- ✓ Operator import page (`import.html`) uses Apple card and button styles — v1.9

### Validated (v2.0)

- ✓ Admin can trigger a full MongoDB database backup from the admin console UI — v2.0
- ✓ Backup file downloads directly to the browser on demand — v2.0
- ✓ Backup filename includes UTC date and time timestamp (`ollog-backup-2026-04-14-15-30-42.gz`) — v2.0

### Validated (v2.1)

- ✓ Admin can upload a `.gz` backup file and restore the full database from it — v2.1
- ✓ System validates the backup file integrity (gzip decompressibility + NDJSON format) before attempting any restore — v2.1
- ✓ Admin must re-enter their password in a confirmation modal before the destructive overwrite proceeds — v2.1
- ✓ System auto-backs up the current database before wiping, so recovery is possible if the restore fails — v2.1

### Validated (v2.2)

- ✓ UDP datagrams containing an OPERATOR field are routed to that operator's log — multiple operators can send ADIF via UDP simultaneously without sharing a single UDP_OPERATOR account — v2.2
- ✓ Operator routing uses an in-memory callsign→User cache (no per-datagram MongoDB round-trip) — v2.2
- ✓ Unrecognized OPERATOR callsigns are dropped with a WARNING log — v2.2
- ✓ UDP_OPERATOR env var is an optional fallback — if absent and datagram has no OPERATOR field, QSO is dropped with WARNING — v2.2

### Validated (v2.3)

- ✓ Operator can view a dedicated statistics page at `/log/stats` linked from the sidebar nav — v2.3
- ✓ Stats page shows a pie chart of QSO count by band — v2.3
- ✓ Stats page shows a pie chart of QSO count by mode — v2.3
- ✓ Stats page shows a pie chart of top 8 DXCC entities by QSO count (remaining grouped as "Other") — v2.3
- ✓ Stats page displays total count of unique DXCC entities worked — v2.3
- ✓ All statistics are scoped to the authenticated operator's log (JWT-isolated) — v2.3
- ✓ Stats page shows an empty-state message when the operator has no QSOs logged — v2.3
- ✓ Charts adapt to dark/light theme toggle without a page reload (re-initialized on theme change) — v2.3

### Validated (v2.8)

- ✓ Operator can see a "Clear my log" action in a Danger Zone section at the bottom of the profile/settings page — v2.8 (CLR-01)
- ✓ Clicking it opens a confirmation modal showing the number of QSOs that will be deleted and requiring the operator to enter their password — v2.8 (CLR-02)
- ✓ On successful password verification, all of the operator's QSOs are permanently deleted from MongoDB — v2.8 (CLR-03)
- ✓ Operator sees an inline success message with the count of QSOs deleted; the modal closes — v2.8 (CLR-04)
- ✓ Incorrect password shows an inline error inside the modal — deletion does not proceed — v2.8 (CLR-05)
- ✓ Admin can trigger "Clear log" for any operator from the admin operators management page — v2.8 (ACLR-01)
- ✓ A confirmation modal opens showing the target operator's callsign and QSO count, requiring the admin to re-enter their own password — v2.8 (ACLR-02)
- ✓ On successful admin password verification, all QSOs for the target operator are permanently deleted — v2.8 (ACLR-03)
- ✓ Admin sees an inline success confirmation with the operator callsign and QSO count deleted — v2.8 (ACLR-04)
- ✓ Incorrect admin password shows an inline error — deletion does not proceed — v2.8 (ACLR-05)
- ✓ Operator getting-started guide updated with a "Clear my log" section explaining the Danger Zone flow and password confirmation — v2.8 (DOC-01)
- ✓ Admin guide updated with "Clear operator log" instructions including the admin-password confirmation step — v2.8 (DOC-02)
- ✓ MkDocs site rebuilt and `site/` committed to repo — v2.8 (DOC-03)

### Out of Scope

- Award tracking (DXCC, WAS, WAZ, etc.) — deferred to v2
- Self-registration — admin controls all operator accounts
- Real-time chat or club coordination features — not core to logging
- Mobile native app — web UI is responsive, no native app in v1
- LoTW/eQSL direct upload — TQSL certificate management adds significant operational complexity (v2)
- Callsign lookup (QRZ/HamQTH) — external API dependency with subscription/rate-limit friction (v2)
- MY_LAT / MY_LON in ADIF export — ADIF Location format is non-trivial (XDDD MM.MMM); lat/lon stored as float internally for future use
- DXCC entity / CQ zone / ITU zone derivation from callsign — requires cty.dat lookup (v2)
- Per-activation fields (MY_SOTA_REF, MY_POTA_REF) — session-level overrides, deferred (v2)
- Multiple station profiles per operator — deferred (v2)

### Validated (v2.4 — Phase 44)

- ✓ The SSE change-stream watcher survives a Jinja2 render exception and continues broadcasting subsequent change events (LIVE-01a)
- ✓ The watcher task is stored in `app.state.watcher_task` (strong reference) — Python 3.12+ GC cannot reclaim it (LIVE-01b)
- ✓ A QSO document with `qso_date_utc=None` does not kill the watcher (LIVE-01c)
- ✓ The LIVE indicator does NOT turn green on bare SSE connection open (`htmx:sseOpen`) (LIVE-02)
- ✓ The LIVE indicator turns green only after the first `htmx:sseMessage` with `type='new_qso'` is received (LIVE-02)
- ✓ The LIVE indicator shows OFFLINE on `htmx:sseError` and hides on `htmx:sseClose` (LIVE-02)

### Validated (v2.4 — Phase 45)

- ✓ `User.notify_sound: bool = False` field on User model — off by default, no migration needed (SND-03)
- ✓ `ProfileUpdateRequest` and `ProfileResponse` both include `notify_sound: bool = False`
- ✓ Profile Settings page shows a "Sound Notifications" checkbox, unchecked by default (SND-04)
- ✓ Sound preference persists per-operator via `update_profile()` → MongoDB `$set` (SND-05)

### Validated (v2.5 — Phase 48)

- ✓ QSO records are automatically stamped with `_created_at` (UTC datetime) via `default_factory` when first inserted — applies to REST API, UI, UDP, and ADIF import paths with no service-layer changes required (TS-01)
- ✓ `_created_at` is stripped from PATCH/update handlers in both REST API and UI routers so it is never overwritten after initial insert (TS-02)
- ✓ MongoDB compound index `operator_created_at_idx` on `(_operator ASC, _created_at DESC)` is declared in `QSO.Settings.indexes` and synced at app startup via Beanie `init_beanie()` (TS-03)
- ✓ `_created_at` is excluded from REST API `GET /api/qsos` responses (popped in `_qso_to_dict`) and from ADIF `.adi` export files (`_SKIP_FIELDS`)
- ✓ Pre-existing QSO documents that lack `_created_at` are backfilled from their ObjectId timestamp at app startup via `backfill_created_at()` idempotent migration

### Validated (v2.4 — Phase 47)

- ✓ When new QSOs arrive while the operator is on page 2+ or has active filters, a "N new QSO(s)" indigo pill badge appears above the log table — counter increments with each SSE event, singular/plural text correct (LIVE-03)
- ✓ Clicking the badge dismisses it and resets the counter to zero — no page jump, no auto-scroll (LIVE-04)
- ✓ Badge is a DOM sibling of #log-table so HTMX SSE innerHTML swaps cannot destroy it — badge survives all page navigations (LIVE-03)
- ✓ Badge auto-dismisses when operator navigates to page 1 with no filters (htmx:afterSettle + auto-refresh-ok sentinel) (LIVE-03)

### Validated (v2.4 — Phase 46)

- ✓ `log_view()` uses `get_current_user_cookie` and injects `notify_sound` into Jinja2 context (SND-01)
- ✓ `const NOTIFY_SOUND = "true"/"false"` rendered server-side in `log.html` — Python bool → JS string (SND-01)
- ✓ Web Audio API 440 Hz synthesized tone plays on `new_qso` SSE event when sound enabled (SND-01)
- ✓ Lazy `AudioContext` created on first user gesture; tone silent before interaction (SND-02)
- ✓ No external audio files — tone is synthesized client-side via `OscillatorNode` + `GainNode` (SND-01)

### Validated (v2.5 — Phase 49)

- ✓ Invalid sort fields (e.g. `_deleted`, `hashed_password`) passed to `get_qso_page()` fall back to `-qso_date_utc` — never reach MongoDB (SORT-04)
- ✓ All 10 allowed sort values (`-qso_date_utc`, `qso_date_utc`, `-CALL`, `CALL`, `-BAND`, `BAND`, `-MODE`, `MODE`, `-_created_at`, `_created_at`) are accepted without fallback (SORT-04)
- ✓ WARNING log emitted containing both the rejected field name and the operator callsign (SORT-04)
- ✓ View dict returned by `_qso_to_view_dict()` contains a `created_at` key with a datetime value (Phase 50 template consumption)
- ✓ SSE auto-refresh sentinel fires for both `-qso_date_utc` and `-_created_at` sorts on page 1 with no filters (SORT-03)
- ✓ SSE auto-refresh sentinel does NOT fire for non-newest-first sorts like `CALL` (SORT-03)

### Validated (v2.5 — Phase 50)

- ✓ MODE column header is clickable and sorts ascending on first click (`?sort=MODE`), descending on second click (`?sort=-MODE`) — SORT-01
- ✓ Clock icon in DATE header sorts by `_created_at` descending on first click (`?sort=-_created_at`), ascending on second click — SORT-02
- ✓ All inactive sortable columns (DATE text, clock icon, CALL, BAND, MODE) display a faint hollow double-chevron (`opacity-30 dark:opacity-25`) — UX-01
- ✓ Active sort column displays a solid directional chevron (down for desc, up for asc) — UX-02
- ✓ All sort clicks preserve active filter parameters (call, band, mode, date_from, date_to) in the URL — UX-01
- ✓ DATE header restructured with flex wrapper: date sort link + clock icon sort link side-by-side — D-01
- ✓ Non-sortable columns (Freq MHz, RST S/R, Actions) have no sort indicators — UX-01

### Validated (v2.6 — Phase 51)

- ✓ `GET /llms.txt` serves `static/llms.txt` with `Content-Type: text/plain; charset=utf-8`, `include_in_schema=False` (LLMS-01, LLMS-04)
- ✓ `GET /llms-full.txt` serves `static/llms-full.txt` with `Content-Type: text/plain; charset=utf-8`, `include_in_schema=False` (LLMS-02, LLMS-04)
- ✓ `static/llms.txt` contains title, one-sentence description, and section links to `/llms-full.txt` (LLMS-03)
- ✓ `static/llms-full.txt` contains complete API reference (all 16 REST endpoints with curl examples), ADIF field reference tables, and operator getting-started walkthrough (CONTENT-01, CONTENT-02, CONTENT-03)
- ✓ Both routes are absent from `/openapi.json` (LLMS-04)

### Validated (v2.7 — Phase 52)

- ✓ `normalize_time_on()` idempotent startup migration in `app/main.py` pads all 4-digit `TIME_ON` values to 6-digit `HHMM00` using anchored regex `^\d{4}$` filter + aggregation pipeline (DB-01)
- ✓ Migration called in `lifespan()` immediately after `backfill_created_at()` — runs on every startup, modifies 0 documents if already migrated (idempotent) (DB-01)
- ✓ `parse_adif_datetime()` in `app/qso/service.py` confirmed to accept both HHMM (4-digit) and HHMMSS (6-digit) `TIME_ON` — unchanged, test-covered (DB-02)
- ✓ `tests/test_migration.py` — 5 tests: padding, idempotency, skip-6-digit (integration), HHMM/HHMMSS parse acceptance (unit) (DB-01, DB-02)

### Validated (v2.7 — Phase 53)

- ✓ Log QSO form: QSO_DATE and TIME_ON wrapped in padlock UI — `readonly` by default, closed-padlock SVG, locked CSS; click toggles editable with open-padlock icon and aria-label swap (DATE-02, DATE-03, TIME-03)
- ✓ Live UTC clock: `initDateTime()` populates both fields on load using `getUTC*` exclusively; `setInterval` ticks TIME_ON every second while locked; `initDateTime()` resets icons/aria-labels on post-submit reset (DATE-01, TIME-01, TIME-02)
- ✓ HHMM normalization: `htmx:beforeRequest` pads 4-digit unlocked TIME_ON to 6 digits before validation fires (TIME-04)
- ✓ Locked-field validation: `validate()` skips `readonly` fields; TIME_ON range regex `^([01]\d|2[0-3])([0-5]\d)([0-5]\d)$` rejects out-of-range values client-side (DATE-04, TIME-05)
- ✓ Reset-mode toggle: pill widget in submit row; `localStorage` key `ollog.resetMode` persists choice across reloads (RESET-01)
- ✓ Post-submit branching: "Reset to live UTC" replays `form.reset()` + `initDateTime()`; "Keep current date/time" preserves all field state; both modes clear CALL and focus it (RESET-02, RESET-03)
- ✓ Clear button: `form.addEventListener('reset', ...)` defers `initDateTime()` via `setTimeout(0)` so date/time repopulate instead of going blank

## Current State

**Version:** v3.0 Configurable QSO Log Fields — **PLANNING** (2026-06-03)
**Tech stack:** FastAPI 0.135+, Beanie 2.1+, pymongo 4.16+ (sync MongoClient for backup/restore, AsyncMongoClient for app), HTMX 2.0.4, Jinja2, Tailwind CSS v3 + PostCSS (autoprefixer), Docker Compose, maidenhead 1.8+, pydantic[email] 2.0+, pycountry 26.2.16+, mkdocs-material 9.7.6 (dev-only), APScheduler 3.x (backup scheduler)
**Database:** MongoDB 7 (single-node replica set for change streams)
**Auth:** PyJWT + pwdlib Argon2; HTTP-only cookie auth for UI/SSE, Bearer token for REST API, `X-API-Key` for REST API (v1.7+), `admin_token` cookie for admin UI (v1.8+)
**Codebase:** ~9,000+ LOC Python (+ HTML templates + Tailwind component system) + 7-page MkDocs docs site (pre-built `site/` in Docker image)

**Shipped features (cumulative, v1.0–v2.5 complete):**
All v2.4 features plus (Phases 48–50 complete):
- `app/qso/models.py` — `created_at: datetime` field with `alias="_created_at"`, `serialization_alias="_created_at"`, `default_factory=lambda: datetime.now(timezone.utc)`; `operator_created_at_idx` compound index `(_operator ASC, _created_at DESC)` added as 4th entry in `Settings.indexes`
- `app/qso/router.py` — PATCH handler strips `_created_at`/`created_at` from update body; `_qso_to_dict` pops `_created_at` from API responses
- `app/qso/ui_router.py` — PATCH handler strips `_created_at`/`created_at` from update body; `_qso_to_view_dict()` exposes `"created_at": qso.created_at` for template use
- `app/adif/router.py` — `_created_at` added to `_SKIP_FIELDS` to exclude from ADIF exports
- `app/main.py` — `backfill_created_at()` idempotent startup migration: stamps `_created_at` from ObjectId timestamp on pre-existing documents lacking the field
- `app/qso/service.py` — `_ALLOWED_SORT_FIELDS` frozenset (10 values), `_DEFAULT_SORT` constant, guard block in `get_qso_page()` with WARNING log for invalid sort fields (prevents MongoDB field enumeration)
- `templates/log/log_table.html` — SSE auto-refresh sentinel extended to fire on `-_created_at` sort; MODE sort header (ascending-first); DATE header restructured with flex wrapper (date sort + clock icon sort); CALL/BAND/MODE/clock inactive hollow chevron indicators; `dark:opacity-25` for dark mode faint indicators
- `static/css/output.css` — rebuilt with `dark:opacity-25` class
- `tests/test_qso_schema.py` — 7 new/updated tests: index count, field alias, default_factory, MongoDB storage, compound index existence, PATCH immutability, backfill correctness and idempotency
- `tests/test_watcher.py` — updated lifespan mock to include `backfill_created_at`
- `tests/test_service_sort.py` — SORT-04 allowlist validation tests
- `tests/test_sse_sentinel.py` — SORT-03 sentinel integration tests
- `tests/test_view_dict.py` — view dict `created_at` key presence and type test

**Known tech debt:**
- `QSO.find_active()` in models.py — dead production code
- `from_mongo_dt()` in utils.py — tested, not called in production
- Docker end-to-end verification pending (requires live Docker environment)
- `aria-label` inversion on padlock buttons in `templates/log/form.html` — reads "Lock field" when locked (should say "Unlock"); screen-reader-only, no functional impact (v2.7)

## Context

- **ADIF Spec:** https://adif.org/317/ADIF_317.htm — all QSO fields conform to ADIF 3.1.7 (MY_ANTENNA confirmed as correct field name per 3.1.6)
- **Domain:** Ham radio operators log "QSOs" (contacts) — each QSO captures callsign, frequency/band, mode (CW, SSB, FT8, etc.), signal reports (RST), date, time, and optional fields
- **ADIF file format:** Tag-based encoding `<CALL:4>W1AW <BAND:3>20M <EOR>` — lossless import/export is non-negotiable
- **Simultaneous logging:** Club station or contest team with multiple operators active at the same time

## Constraints

- **Tech Stack**: Python backend, MongoDB for storage
- **ADIF Version**: ADIF 3.1.7
- **Deployment**: Self-hosted (Docker Compose) or cloud without code changes — twelve-factor config
- **Auth**: Admin-managed accounts only — no public self-registration endpoint

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Individual logs per operator | Each ham has their own callsign and logbook identity | ✓ Good — operator as leading index key enables efficient per-operator queries |
| ADIF field names as internal data model | Eliminates translation layer; stays spec-compliant | ✓ Good — model_extra stores arbitrary ADIF fields losslessly |
| Admin-managed accounts | Prevents unauthorized access; club/team deployments | ✓ Good — admin bootstrap from env vars; no web signup endpoint |
| MongoDB for QSO storage | Flexible schema fits ADIF's large optional field set | ✓ Good — Beanie ODM + pymongo async works well |
| pymongo AsyncMongoClient (not Motor) | pymongo 4.9+ has native async; Motor is a redundant wrapper | ✓ Good — Motor EOL confirmed May 2025 |
| Shared `qsos` collection with `_operator` leading index | Per-operator collections add operational complexity | ✓ Good — compound index efficient; operator isolation enforced at query layer |
| Unique compound index dropped (03-02) | Soft-delete re-insertion and force=true use cases broke unique constraint | ✓ Good — app-level find_duplicate() is the enforcement mechanism |
| SSE over WebSockets for live feed | Unidirectional broadcast, HTMX-native, works through proxies | ✓ Good — htmx-ext-sse 2.2.4 + FastAPI native EventSourceResponse |
| MongoDB single-node replica set | Change streams require oplog; single node sufficient for self-hosted | ✓ Good — self-initiating healthcheck pattern works reliably |
| Cookie auth for SSE endpoint | Browser EventSource API cannot send Authorization headers | ✓ Good — get_current_operator_callsign_cookie used on /feed/station |
| directConnection=true in test fixtures | Enables test fixtures to connect to replica set node directly | ✓ Good — works for both standalone and replica set environments |
| Profile fields embedded in User document | No separate collection, no migration required | ✓ Good — Optional fields default to None; existing users unaffected |
| grid-to-latlon conversion in service layer (not model) | Keeps User model as plain data; separation of concerns | ✓ Good — update_profile() in service.py handles lat/lon sync |
| center=True for maidenhead grid conversion | SW corner default causes up to 80 km error | ✓ Good — grid_to_latlon() uses center of grid square |
| MY_ANTENNA (not MY_ANT) field name | ADIF 3.1.6 spec lists MY_ANTENNA — my_ant was a placeholder | ✓ Good — renamed in 08-01; no migration needed (Optional, no production data) |
| STATION_CALLSIGN omitted (not empty string) when blank | Empty string causes LoTW/POTA upload failures | ✓ Good — schema validator normalizes "" → None |
| ADIF import path excluded from auto-stamping | Historical records must be preserved as-is | ✓ Good — profile param defaults to None; import callers pass no profile |
| UI profile POST calls service directly (not /api/profile) | Avoids internal HTTP round-trip; follows existing UI route pattern | ✓ Good — consistent with how submit_qso calls build_qso_dict |
| User.model_construct() in stamping unit tests | Beanie Document() requires DB init; model_construct() bypasses it | ✓ Good — enables fast synchronous unit tests without MongoDB |
| Truncated bisect comparison for ITU range lookup | ITU ranges use letter keys (WAA-WZZ); callsigns have digits (W1AW); ASCII digits sort before letters — exact comparison fails | ✓ Good — compare start[:n] <= prefix <= end[:n]; all 28 tests pass |
| `_NOTFOUND` sentinel in range lookup | iso=None is valid (non-country entity); need to distinguish "range found, iso=None" from "no range found" | ✓ Good — object() sentinel prevents 4U1ITU from falling through to shorter prefix match |
| Digit presence required in callsign | `UNKNOWN` resolves to Kazakhstan via UNA-UQZ range; all valid callsigns contain a digit | ✓ Good — validation rejects digit-free strings before lookup |
| `iso.lower()` before flag path construction | `lookup_prefix` returns "US" but SVG files are named "us.svg" | ✓ Good — .lower() in _qso_to_view_dict(); flag_iso always lowercase |
| `git mv app/static/flags static/flags` for flag serving | StaticFiles mounts root `static/` at `/static`; `app/static/flags/` was unreachable | ✓ Good — 271 SVG files now at `static/flags/`, served at `/static/flags/*.svg` |
| Render-time flag enrichment in `_qso_to_view_dict()` | Single injection point for all 4 render paths; prefix allocations can change — not stored in QSO | ✓ Good — no schema change; enrichment transparent to all existing render paths |
| QSOResponse uses `Field(alias='_operator'/'_deleted')` | `_qso_to_dict()` uses `model_dump(by_alias=True)` — response model must declare aliases to pass validation | ✓ Good — `populate_by_name=True` + `extra='ignore'` handles both construction and arbitrary ADIF passthrough |
| `extra='ignore'` on QSOResponse | Arbitrary ADIF `model_extra` fields must not cause 500 validation errors | ✓ Good — silently drops extra fields at response serialization boundary |
| Export annotated with `responses=` (not `response_model=`) | `StreamingResponse` body cannot be Pydantic-validated | ✓ Good — `response_class=StreamingResponse` + `responses={200: {"content": {"text/plain": {}}}}` |
| Feed/HTMX routers excluded from OpenAPI (`include_in_schema=False`) | `/feed/station` uses cookie auth — cannot be exercised from Swagger UI | ✓ Good — clean `/docs` with REST-only endpoints |
| `site_url` in mkdocs.yml ends with `/guide/` (trailing slash) | Sub-path serving without trailing slash generates broken relative asset URLs | ✓ Good — CSS/JS assets resolve correctly at `/guide` |
| `site/` committed to repo; `COPY site/ site/` in Dockerfile | No MkDocs in production image; no CI pipeline needed | ✓ Good — pre-built docs served directly from static files |
| `/guide` StaticFiles mount registered before `/static` with `html=True` | Mount order is load-bearing in FastAPI; `html=True` enables automatic `index.html` serving | ✓ Good — `/guide` serves MkDocs index at directory paths |
| SECRET_KEY signs JWTs only; Argon2 password hashing is independent | Clearing cookies (not resetting passwords) fixes most login-after-restart issues | ✓ Good — documented clearly in troubleshooting |
| ADIF import has no `force=true` | Bulk re-import requires delete-then-import; single QSO creation supports `force=true` | ✓ Good — documented in troubleshooting and API reference |
| `UDP_OPERATOR` config for operator identity (not JWT in datagrams) | JWTs expire with no UDP refresh path; overnight FT8 sessions would silently stop logging | ✓ Good — config-pinned identity prevents spoofing; works for long-running unattended sessions |
| Default UDP port 2399 | Port 2237 (WSJT-X) and 12060 (N1MM+) are ecosystem-occupied; dedicated port avoids silent conflict | ✓ Good — no conflicts with common ham radio logging software |
| `UDP_BIND_HOST=127.0.0.1` default (loopback) | Protects against LAN exposure by default; matches ham radio ecosystem convention | ✓ Good — operators opt in to LAN exposure by setting `0.0.0.0` |
| `UDP_ENABLED=false` default | Existing deployments unaffected on upgrade | ✓ Good — clean opt-in; no surprise socket on upgrade |
| `asyncio.DatagramProtocol` (stdlib) | No new production dependencies; runs on uvicorn's event loop | ✓ Good — zero new deps; transport.close() is synchronous (never awaited) |
| `build_qso_dict(profile=user)` called directly (not `import_qsos_from_bytes`) | `import_qsos_from_bytes` omits `profile=` parameter, breaking auto-stamping for UDP path | ✓ Good — UDP QSOs get identical profile stamping to REST API QSOs |
| Operator `User` document cached once at startup | Avoids MongoDB round-trip per datagram | ✓ Good — WARNING logged if UDP_OPERATOR callsign not found in DB |
| `_background_tasks` set + `add_done_callback(discard)` for create_task | Python 3.12+ GCs tasks without strong references; Ruff RUF006 confirms this is required | ✓ Good — tasks complete reliably under burst load |
| Merge parse_errors + no-records into single WARNING branch | Two separate WARNING paths produced double-logging for binary garbage input; criterion required exactly one | ✓ Good — `if parse_errors or not records:` single guard satisfies "exactly one WARNING" |
| Structured `disposition=accepted|rejected|duplicate` log tokens | Operators need grep-able logs to diagnose UDP path in production | ✓ Good — `src=IP:PORT call=CALLSIGN disposition=` on every outcome branch |

| `htmx:sseMessage` listener instead of `hx-trigger="sse:event [condition]"` | JS filter evaluation on SSE hx-trigger had only MEDIUM confidence from research (inferred from htmx source, not documented) | ✓ Good — event listener approach is fully reliable and equally concise |
| SSE attributes on `#log-table` container (not inside `log_table.html` partial) | `#log-table` is the HTMX swap target — its innerHTML is replaced but the element persists; SSE attrs inside the partial would be destroyed on every pagination/filter/sort swap | ✓ Good — SSE connection survives all navigation |
| Server-side `#auto-refresh-ok` hidden sentinel span | Client-side JS cannot evaluate server-side predicates (page number, active filters); server renders marker only at page 1 + default sort + no filters; client checks `getElementById` | ✓ Good — single source of truth; marker disappears atomically on any navigation |
| `#log-table input` selector for edit-row guard | `qso_row_edit.html` renders `<tr>` with NO `.editing` class — the prior research assumption was wrong; input presence is the correct discriminator | ✓ Good — catches any open edit row without relying on a CSS class convention |
| `jwt_expire_minutes` default raised 60 → 480 | Overnight FT8 sessions run 8+ hours; 60-min default would expire mid-SSE-connection, silently breaking live log table feature | ✓ Good — existing env var mechanism unchanged; operators can still override |
| FOUC IIFE placed before `<link rel=stylesheet>` in `<head>` | Class applied synchronously before any CSS loads; any other position (deferred, external file, after link) causes visible white flash | ✓ Good — zero flash on cold page load across Chrome, Firefox, Safari |
| rAF-rAF pattern for transition suppression | Inject `.no-transition` before adding `dark` class, remove after two animation frames — prevents color-fade on load while preserving user-initiated toggle animation | ✓ Good — smooth toggle, no load animation |
| `document.body` htmx:afterSettle listener (not `document`) | Matches existing HTMX event patterns in codebase; body is the correct target for afterSettle | ✓ Good — theme icon stays in sync after all HTMX swaps |
| `.glass-card` uses raw `-webkit-backdrop-filter: blur(12px)` (not `@apply backdrop-blur-md`) | `@apply backdrop-blur-md` generates `backdrop-filter: var(--tw-backdrop-blur)` — Safari pre-18.0 ignores `-webkit-backdrop-filter` with variable references; fixed pixel values are the only reliable path | ✓ Good — frosted glass renders in Safari and all major browsers |
| `postcss.config.js` with `autoprefixer({ remove: false })` | Default autoprefixer silently strips manually-added `-webkit-backdrop-filter` during Tailwind build — build artifact was missing the prefix until this was discovered | ✓ Good — `-webkit-backdrop-filter` survives every build |
| FastAPI sub-app (`admin_main.py`) requires its own `StaticFiles` mount | Main app `StaticFiles` mount does not propagate to sub-apps; admin was 404-ing on `/static/css/output.css` until this was added | ✓ Good — each FastAPI sub-app is isolated; mount must be explicit |
| Canvas/surface token classes as literal strings in templates (not Jinja expressions) | Tailwind purge scanner reads template files as text — dynamic class construction (e.g. `class="{{ dark_class }}"`) is invisible to the scanner; new `dark:` classes dropped from output.css | ✓ Good — all tokens present in output.css |
| `{% block sidebar_class %}{% endblock %}` in `<aside>` class attribute | Minimal-invasive extension point; empty default block adds no whitespace artifact; `users.html` injects `dark:bg-surface-dark` as a literal string for Tailwind scanner | ✓ Good — admin sidebar dark surface without touching base_app.html for every template |
| `asyncio.to_thread(_write_backup, settings)` (sync helper, not async run_backup) | `asyncio.to_thread` requires a sync callable — passing the `async def run_backup` silently returns a coroutine object instead of a Path; extracted `_write_backup` sync helper is the correct target | ✓ Good — event loop unblocked during all MongoDB + gzip I/O |
| Plain `<a href>` anchor for download button (no `hx-*` attributes) | HTMX intercepts XHR responses — `Content-Disposition: attachment` is silently ignored and binary payload discarded; plain anchor causes browser-native navigation that HTMX does not intercept | ✓ Good — file save dialog fires correctly; confirmed no `hx-boost` on `<body>` in base_app.html |
| Per-page `{% block sidebar_nav %}` override in admin templates | Each admin page owns its entire sidebar nav block with both links and correct active state — avoids fragile conditional logic in base_app.html | ✓ Good — Operators page shows Operators active; Backup page shows Backup active |
| FileResponse filename from `backup_path.stem` (not a second datetime call) | Guarantees download filename matches actual file on disk; eliminates clock skew between generation and naming | ✓ Good — `ollog-backup-{stem}.gz` always matches the file returned |
| `bson.json_util.loads` (not `json.loads`) for restore deserialization | `json.loads` silently corrupts ObjectId as `{"$oid":"..."}` dict — BSON types must round-trip correctly | ✓ Good — ObjectId, datetime, and all BSON extended types restored with correct Python types |
| Auto-backup runs before any `db.drop()` in `restore_confirm` | OPS-01 safety requirement: if restore fails mid-wipe, the pre-restore backup filename is included in the error response so admin can recover | ✓ Good — failure response always includes auto-backup path |
| Path traversal guard: `resolve(temp_path).startswith(gettempdir())` + `.gz` suffix + `.exists()` | All three checks required before any file read — prevents directory traversal attacks on the temp file path in the hidden form field | ✓ Good — three-layer guard; any missing check is a security hole |
| All HTMX error fragments return HTTP 200 | HTMX 2.x silently drops response body on 4xx — error HTML would never appear in the UI | ✓ Good — all five fragment templates return 200 with HTMX-consumable error HTML |
| `#restore-modal` div is a sibling of `#restore-result` (not nested in form) | Cancel button targets `#restore-modal` with `hx-swap="outerHTML"` — element must be independently addressable in the DOM | ✓ Good — modal clears cleanly; upload form and result div unaffected |
| GET `/admin/ui/restore` returns bare `<div id="restore-modal"></div>` on HTMX request | Cancel button fires `hx-get="/admin/ui/restore"` — dual-render pattern returns empty div to clear modal without page reload | ✓ Good — modal dismissal is a pure DOM swap; no data lost |
| `.modal-backdrop` uses raw `-webkit-backdrop-filter: blur(4px)` (not `@apply`) | Consistent with glass-card Safari fix: fixed pixel values required; CSS variable references ignored by Safari | ✓ Good — backdrop blur renders across Safari, Chrome, Firefox |
| `get_pymongo_collection()` (not `get_motor_collection()`) for raw MongoDB aggregation | Motor was EOL'd May 2025; Beanie now exposes `get_pymongo_collection()` as the official raw-collection accessor | ✓ Good — correct API; Motor import would fail in current dependency set |
| `(await collection.aggregate(pipeline)).to_list()` double-await pattern | `AsyncCollection.aggregate()` is a coroutine returning a cursor — must await it to get the cursor, then call `.to_list()` | ✓ Good — single-await pattern silently returned a coroutine object instead of results |
| `unique_entity_count` computed from `iso_seen` set before top-8 truncation | Scalar must reflect total distinct entities worked, not just the visible top-8 slice | ✓ Good — count is accurate regardless of "Other" grouping |
| Chart.js 4.5.1 UMD bundle via jsDelivr CDN, loaded only in `{% block extra_scripts %}` override | ESM-only build fails silently; CDN avoids bundling; loading in base.html penalizes all pages with Chart.js parse cost | ✓ Good — stats page loads Chart.js; all other pages unaffected |
| `themechange` CustomEvent broadcast from `toggleTheme()` (zero-coupling) | `toggleTheme()` does not know about charts; event listener pattern lets any future chart page opt in independently | ✓ Good — pattern established; any future chart page just adds `window.addEventListener('themechange', ...)` |
| `{% if total_qsos > 0 %}{% block extra_scripts %}...{% endblock %}{% endif %}` conditional block | Prevents Chart.js script tag from loading on empty-state render; Jinja2 evaluates block declarations at parse time so the conditional only guards render-time output | ✓ Good — no Chart.js CDN request on empty log |
| `app.state.watcher_task` strong reference (not local variable) | Python 3.12+ GCs asyncio tasks without a strong reference; local variable in lifespan `yield` block is not sufficient | ✓ Good — watcher task survives GC cycles between event loop ticks |
| `try/except Exception` in watch_qsos inner loop (not outer) | Catching at the inner loop level lets the watcher continue after a single bad event; outer-level catch would restart the entire change stream | ✓ Good — watcher survives Jinja2 render errors and null-field documents |
| `eventsFlowing` sentinel for LIVE indicator (not sseOpen) | `htmx:sseOpen` fires when the HTTP connection opens, before any events flow; green on open is premature and misleading when the watcher is unhealthy | ✓ Good — indicator only turns green after first confirmed `new_qso` event |
| `NOTIFY_SOUND` as Jinja2 string `"true"/"false"` (not Python bool) | Python `True`/`False` renders as `"True"`/`"False"` in templates — JS strict comparison `=== "true"` would silently fail | ✓ Good — explicit string rendering with `'true' if x else 'false'` pattern |
| Sound check fires BEFORE auto-refresh-ok guard in htmx:sseMessage | Badge and tone should work on page 2+ and with active filters — placing sound/badge logic after the `return` guard would silence them on all non-page-1 views | ✓ Good — tone and badge both work on page 2+ and filtered views |
| `#new-qso-badge` as DOM sibling of `#log-table` (not child) | HTMX SSE innerHTML swap replaces all children of the swap target; badge nested inside would be destroyed on every SSE refresh | ✓ Good — badge persists across all HTMX SSE swaps and pagination |
| `classList.remove('hidden')` before `classList.add('flex')` for badge show | Tailwind `hidden` compiles to `display: none !important`; adding `flex` without removing `hidden` has no visible effect | ✓ Good — badge appears correctly on first increment |
| Single `clear_operator_log()` service in `app/qso/service.py` consumed by both operator and admin flows (v2.8) | Two callers, one filter — eliminates the drift risk of duplicating `delete_many({_operator, _deleted: False})` in admin code | ✓ Good — Phase 55 imports + calls Phase 54's service; centralized Beanie filter |
| Admin clear-log verifies admin's OWN password (`current_user.hashed_password`), never `target_user.hashed_password` (v2.8) | A compromised admin session must not be able to delete a target user's QSOs just because their callsign is known; password gate must defend the admin account itself | ✓ Good — integration check confirmed zero references to `target_user.hashed_password` in verify_password calls; docstring at admin/ui_router.py:458 explicitly warns against it |
| Distinct modal target IDs (`#clear-log-modal` operator, `#admin-clear-log-modal` admin) (v2.8) | Operator and admin UIs are served from separate FastAPI sub-apps but identical IDs would risk collision if pages were ever co-rendered | ✓ Good — no DOM collision possible |
| MkDocs Material `admonition` extension required for `!!! danger` blocks (v2.8) | Without `markdown_extensions: [admonition]`, `!!! danger` syntax silently renders as literal plain text — no build warning | ✓ Good — extension wired; HTML render verified via grep `class="admonition danger"` |
| Documentation paths use `docs/operator-guide/profile.md` + `docs/admin-guide/account-management.md` (NOT stale ROADMAP paths) (v2.8) | ROADMAP referenced `docs/getting-started.md` and `docs/admin.md` which are excluded from nav via `not_in_nav`; Phase 56 D-04 explicitly resolves to the actual MkDocs source files | ✓ Good — verified by two accepted overrides in 56-VERIFICATION.md |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-16 after completing v3.5 ACLog Registered Operator Routing*
