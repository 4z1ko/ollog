# ollog — Ham Radio Online Logbook

## What This Is

A self-hosted, ADIF-native, multi-operator logbook for amateur radio operators. Each operator maintains their own individual logbook identified by their callsign. Operators log QSOs in real-time via REST API or browser web UI, import/export full ADIF logbooks, and see each other's QSOs appear live in a shared station feed. All QSO data is stored using native ADIF field names, enabling seamless round-trip import/export with external logging tools. Each operator has a profile with personal info, station details, and grid location — auto-stamped onto every new QSO they log. Complete operator and admin documentation is available at `/guide` (deployment guide, operator walkthrough, API reference, ADIF field reference, troubleshooting).

## Core Value

Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss — the shared platform stays out of their way and just works.

## Requirements

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

### Active

(No active requirements — v2.1 shipped. Next milestone TBD.)

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

## Current State

**Version:** v2.1 Database Restore (shipped 2026-04-14)
**Tech stack:** FastAPI 0.135+, Beanie 2.1+, pymongo 4.16+ (sync MongoClient for backup/restore, AsyncMongoClient for app), HTMX 2.0.4, Jinja2, Tailwind CSS v3 + PostCSS (autoprefixer), Docker Compose, maidenhead 1.8+, pydantic[email] 2.0+, pycountry 26.2.16+, mkdocs-material 9.7.6 (dev-only), APScheduler 3.x (backup scheduler)
**Database:** MongoDB 7 (single-node replica set for change streams)
**Auth:** PyJWT + pwdlib Argon2; HTTP-only cookie auth for UI/SSE, Bearer token for REST API, `X-API-Key` for REST API (v1.7+), `admin_token` cookie for admin UI (v1.8+)
**Codebase:** ~8,300+ LOC Python (+ HTML templates + Tailwind component system) + 7-page MkDocs docs site (pre-built `site/` in Docker image)

**Shipped features (cumulative, v1.0–v2.1):**
All v2.0 features (custom ADIF parser, QSO REST API, operator profiles, callsign flags, typed OpenAPI, MkDocs docs, UDP listener, live log table, API tokens, admin container isolation, backup CLI+scheduler, Apple design token system, dark mode, glass card login, admin backup page + download endpoint) plus:
- Admin Restore page at `/admin/ui/restore` with Apple-style card, `.gz` file upload form, HTMX-wired — no page reloads
- `POST /admin/ui/restore/upload` — validates gzip decompressibility + NDJSON format, returns password modal fragment on success, inline error on failure
- `POST /admin/ui/restore/confirm` — path traversal guard, password verification, auto-backup before any `db.drop()`, full drop+restore all collections, finally-block tempfile cleanup
- `app/backup/restore.py` sync/async split: `_restore_from_file` (sync MongoClient + `bson.json_util.loads`) + `run_restore` async orchestrator via `asyncio.to_thread`
- Password confirmation modal with blurred backdrop (`modal-backdrop`, `modal-box`, CSS component classes compiled into output.css)
- All three admin pages (Operators, Backup, Restore) show complete three-link sidebar nav with correct active states

**Known tech debt:**
- `QSO.find_active()` in models.py — dead production code
- `from_mongo_dt()` in utils.py — tested, not called in production
- Docker end-to-end verification pending (requires live Docker environment)

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

---
## Last Milestone: v2.1 Database Restore (shipped 2026-04-14)

Gave the admin a safe, authenticated way to restore the full MongoDB database from a `.gz` backup file — with integrity validation, password confirmation, auto-backup-before-wipe, and HTMX-wired UI with no page reloads.

---
*Last updated: 2026-04-14 after v2.1 milestone shipped*
