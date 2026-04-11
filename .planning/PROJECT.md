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

## Current Milestone: v1.9 Admin & Login UI Redesign

**Goal:** Redesign the admin console and login page with an Apple-like UI aesthetic (clean typography, generous whitespace, refined controls), properly-sized and resolution-appropriate icons, and a dark/light mode with a persistent toggle at the bottom of the screen.

**Target features:**
- Apple-inspired UI: clean sans-serif typography, card-based layouts, subtle shadows, smooth transitions for admin console and login page
- Icons: correct sizing and rendering sharpness for browser display (no blurry/oversized icons)
- Dark mode: full dark color scheme for admin console and login page
- Light mode: clean light color scheme (current default baseline)
- Mode toggle: persistent dark/light toggle pinned at bottom of screen, preference saved across sessions

## Current State

**Version:** v1.8 Admin Isolation, Backup & Docs (in progress)
**Tech stack:** FastAPI 0.135+, Beanie 2.1+, pymongo 4.16+ (AsyncMongoClient), HTMX 2.0.4, Jinja2, Docker Compose, maidenhead 1.8+, pydantic[email] 2.0+, pycountry 26.2.16+, mkdocs-material 9.7.6 (dev-only)
**Database:** MongoDB 7 (single-node replica set for change streams)
**Auth:** PyJWT + pwdlib Argon2; HTTP-only cookie auth for UI/SSE, Bearer token for REST API
**Codebase:** ~8,102 LOC Python (+ HTML templates) + 7-page MkDocs docs site (pre-built `site/` in Docker image)

**Shipped features (cumulative):**
- Custom ADIF parser + serializer (no third-party ADIF lib)
- QSO REST API (POST/GET/PATCH/soft-DELETE) with operator isolation
- HTMX operator UI: login, QSO form with duplicate warning, paginated log view with filters
- Admin HTMX UI: operator account management (create/enable/disable/reset)
- ADIF import (file upload, duplicate detection, import report) and export (streaming .adi download)
- Real-time SSE station feed — MongoDB change streams → ConnectionManager → htmx-ext-sse DOM injection
- Programmatic operator isolation audit — route introspection test + cross-operator data layer tests
- Operator profile: 12 optional fields (personal info, station equipment, grid/location) embedded in User document
- `grid_to_latlon()` utility — Maidenhead → decimal lat/lon using center=True (17 unit tests)
- Profile API: GET/PATCH `/api/profile` with JWT auth, lat/lon auto-sync on grid change, operator isolation
- QSO auto-stamping: OPERATOR always, STATION_CALLSIGN/equipment conditionally; ADIF import path excluded
- Profile UI at `/log/profile` — HTMX inline save, OPERATOR vs STATION_CALLSIGN clearly labeled
- `app/callsign/prefixes.py` — pure-Python ITU prefix resolver: 313 Series Range entries, bisect-based longest-prefix-match, suffix stripping, ISO mapping (28 unit tests)
- Country flag icons displayed in QSO log table rows — render-time `lookup_prefix()` enrichment in `_qso_to_view_dict()`, conditional `<img>` tag with tooltip, graceful no-flag fallback
- Typed OpenAPI schema: all 16 REST endpoints annotated; HTMX/SSE routes excluded from `/docs`
- MkDocs Material documentation site at `/guide`: deployment guide (incl. UDP env vars + Docker Compose snippet), operator walkthrough (incl. Step 8 UDP sending guide for nc/Log4OM/WSJT-X/N1MM+), admin guide, API reference, ADIF field reference, troubleshooting (incl. 4 UDP entries with verbatim log strings)
- UDP listener (`app/udp/server.py`): `asyncio.DatagramProtocol` on configurable port (default 2399); `_handle_datagram` pipeline: parse_adi → validate → build_qso_dict(profile=user) → find_duplicate → QSO.insert; operator identity pinned to `UDP_OPERATOR` config (never from datagram); operator `User` document cached at startup; structured `disposition=accepted|rejected|duplicate` log tokens; Docker UDP port exposed
- SSE-triggered live log table: `htmx:sseMessage` listener on `#log-table` fires `htmx.ajax('GET', '/log/view')` on `new_qso` events; server-side `#auto-refresh-ok` sentinel guards against refresh during pagination/filtering/sorting; `#log-table input` guard blocks refresh during inline edit; LIVE/OFFLINE indicator in nav bar
- JWT session lifetime configurable via `JWT_EXPIRE_MINUTES` env var; default raised to 480 min (`app/config.py`)

**Known tech debt:**
- `QSO.find_active()` defined in models.py but superseded by `get_qso_page()` in service.py — dead code
- `from_mongo_dt()` in utils.py — tested utility, not called from production modules
- Docker not verified end-to-end on a machine with Docker installed (code is correct; environment constraint)

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

---
*Last updated: 2026-04-11 after v1.9 milestone start*
