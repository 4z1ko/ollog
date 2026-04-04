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

