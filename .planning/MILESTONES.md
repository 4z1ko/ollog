# Milestones

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

