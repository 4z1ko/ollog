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

