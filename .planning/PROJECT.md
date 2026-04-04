# ollog — Ham Radio Online Logbook

## What This Is

A self-hosted, ADIF-native, multi-operator logbook for amateur radio operators. Each operator maintains their own individual logbook identified by their callsign. Operators log QSOs in real-time via REST API or browser web UI, import/export full ADIF logbooks, and see each other's QSOs appear live in a shared station feed. All QSO data is stored using native ADIF field names, enabling seamless round-trip import/export with external logging tools.

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

### Active

(None — all v1.0 requirements shipped. Define v1.1 requirements with `/gsd:new-milestone`.)

### Out of Scope

- Award tracking (DXCC, WAS, WAZ, etc.) — deferred to v2
- Self-registration — admin controls all operator accounts
- Real-time chat or club coordination features — not core to logging
- Mobile native app — web UI is responsive, no native app in v1
- LoTW/eQSL direct upload — TQSL certificate management adds significant operational complexity (v2)
- Callsign lookup (QRZ/HamQTH) — external API dependency with subscription/rate-limit friction (v2)

## Context

- **ADIF Spec:** https://adif.org/317/ADIF_317.htm — all QSO fields conform to ADIF 3.1.7
- **Domain:** Ham radio operators log "QSOs" (contacts) — each QSO captures callsign, frequency/band, mode (CW, SSB, FT8, etc.), signal reports (RST), date, time, and optional fields
- **ADIF file format:** Tag-based encoding `<CALL:4>W1AW <BAND:3>20M <EOR>` — lossless import/export is non-negotiable
- **Simultaneous logging:** Club station or contest team with multiple operators active at the same time

## Constraints

- **Tech Stack**: Python backend, MongoDB for storage
- **ADIF Version**: ADIF 3.1.7
- **Deployment**: Self-hosted (Docker Compose) or cloud without code changes — twelve-factor config
- **Auth**: Admin-managed accounts only — no public self-registration endpoint

## Current State

**Version:** v1.0 MVP (shipped 2026-04-04)
**Tech stack:** FastAPI 0.135+, Beanie 2.1+, pymongo 4.16+ (AsyncMongoClient), HTMX 2.0.4, Jinja2, Docker Compose
**Database:** MongoDB 7 (single-node replica set for change streams)
**Auth:** PyJWT + pwdlib Argon2; HTTP-only cookie auth for UI, Bearer token for REST API
**Codebase:** ~6,611 LOC (Python + HTML templates)

**Shipped features:**
- Custom ADIF parser + serializer (no third-party ADIF lib)
- QSO REST API (POST/GET/PATCH/soft-DELETE) with operator isolation
- HTMX operator UI: login, QSO form with duplicate warning, paginated log view with filters
- Admin HTMX UI: operator account management (create/enable/disable/reset)
- ADIF import (file upload, duplicate detection, import report) and export (streaming .adi download)
- Real-time SSE station feed — MongoDB change streams → ConnectionManager → htmx-ext-sse DOM injection
- Programmatic operator isolation audit — route introspection test + cross-operator data layer tests

**Known tech debt:**
- `QSO.find_active()` defined in models.py but superseded by `get_qso_page()` in service.py — dead code
- `from_mongo_dt()` in utils.py — tested utility, not called from production modules
- Docker not verified end-to-end on a machine with Docker installed (code is correct; environment constraint)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Individual logs per operator | Each ham has their own callsign and logbook identity | ✓ Good — _operator as leading index key enables efficient per-operator queries |
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

---
*Last updated: 2026-04-04 after v1.0 milestone*
