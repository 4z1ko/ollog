# ollog — Ham Radio Online Logbook

## What This Is

A self-hosted, ADIF-native, multi-operator logbook for amateur radio operators. Each operator maintains their own individual logbook identified by their callsign. Operators log QSOs in real-time via REST API or browser web UI, import/export full ADIF logbooks, and see each other's QSOs appear live in a shared station feed. All QSO data is stored using native ADIF field names, enabling seamless round-trip import/export with external logging tools. Each operator has a profile with personal info, station details, and grid location — auto-stamped onto every new QSO they log.

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

## Current Milestone: v1.3 Documentation

**Goal:** Create comprehensive documentation for ollog — REST API reference, app setup/deployment guide, and operator workflow walkthrough.

**Target features:**
- REST API reference covering all endpoints (QSO CRUD, auth, profile, import/export, admin, SSE feed)
- App installation and deployment guide (Docker Compose, config, environment setup)
- Operator workflow documentation (login → profile setup → log QSOs → import/export → station feed)

## Current State

**Version:** v1.2 Callsign Entity Lookup & Country Flags (shipped 2026-04-04)
**Tech stack:** FastAPI 0.135+, Beanie 2.1+, pymongo 4.16+ (AsyncMongoClient), HTMX 2.0.4, Jinja2, Docker Compose, maidenhead 1.8+, pydantic[email] 2.0+, pycountry 26.2.16+
**Database:** MongoDB 7 (single-node replica set for change streams)
**Auth:** PyJWT + pwdlib Argon2; HTTP-only cookie auth for UI, Bearer token for REST API
**Codebase:** ~8,264 LOC (Python + HTML templates)

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
- Profile nav link in all log UI templates (form, log view, import)
- `app/callsign/prefixes.py` — pure-Python ITU prefix resolver: 313 Series Range entries, bisect-based longest-prefix-match, suffix stripping, ISO mapping (28 unit tests)
- Country flag icons displayed in QSO log table rows — render-time `lookup_prefix()` enrichment in `_qso_to_view_dict()`, conditional `<img>` tag with tooltip, graceful no-flag fallback

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

---
*Last updated: 2026-04-04 after v1.3 milestone start*
