# Technology Stack

**Project:** Ham Radio Online Logbook (ollog)
**Researched:** 2026-04-03
**Confidence note:** All external research tools (WebSearch, WebFetch, Context7) were unavailable during this research session. All findings are drawn from training data (cutoff August 2025). Versions should be verified against PyPI and official docs before pinning in requirements files.

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12+ | Runtime | Active LTS with full async support, type annotation improvements, and the widest library compatibility. Avoid 3.13 in production until libraries catch up. | [MEDIUM confidence — 3.12 was stable as of Aug 2025]
| FastAPI | 0.111+ | HTTP framework / REST API | Async-native, OpenAPI auto-docs out of the box, Pydantic v2 integration for request/response validation. Directly models the QSO record schema as Pydantic models, validating ADIF fields at the boundary. Flask requires manual OpenAPI tooling; Django is overkill for a JSON API with no ORM need. | [MEDIUM confidence]
| Uvicorn | 0.29+ | ASGI server | FastAPI's recommended production server. Pair with Gunicorn for multi-worker deployments. | [MEDIUM confidence]
| Pydantic | 2.x | Data validation / serialization | Ships with FastAPI. Use it to define the QSO document model with ADIF field names as Python attributes. Pydantic v2 is 5-17x faster than v1 for validation — important for bulk ADIF import operations. | [MEDIUM confidence]

### Database

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| MongoDB | 7.x | Primary datastore | Required by spec. Document model maps naturally to ADIF: each QSO is a document whose keys are ADIF field names (CALL, BAND, MODE, QSO_DATE, etc.). No schema migration pain when new ADIF fields are added. | [HIGH confidence — project requirement]
| Motor | 3.x | Async MongoDB driver | The official async Python driver for MongoDB, built on top of PyMongo. Required for use with FastAPI's async request handlers. Using PyMongo (sync) directly in async FastAPI routes causes thread-pool exhaustion under load. | [MEDIUM confidence]
| Beanie | 1.x | ODM (optional, recommended) | Async ODM built on Motor + Pydantic. Define QSO as a Beanie Document, get typed queries, validation, and index management for free. Eliminates boilerplate for insert/find/aggregate. Alternative: use Motor directly for full control, but Beanie reduces code volume significantly. | [MEDIUM confidence]

### Authentication

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| python-jose | 3.x | JWT token handling | Standard JWT library for Python. Use with FastAPI's OAuth2PasswordBearer for per-callsign auth. Each operator authenticates as their callsign; JWT encodes the callsign so all queries are automatically scoped. | [MEDIUM confidence]
| passlib[bcrypt] | 1.7+ | Password hashing | Industry-standard bcrypt hashing. `passlib` provides a stable API layer. | [MEDIUM confidence]

### File Import / Export (ADIF)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| adif-io | 0.0.6+ | ADIF file parsing | Pure-Python ADIF parser. Handles .adi and .adif file formats. Returns records as dicts, which map directly to MongoDB document insertion. This is the most widely cited lightweight ADIF library in the Python ham radio community. | [LOW confidence — verify on PyPI; project is small and may have gone unmaintained] |
| adif3 | latest | Alternative ADIF parser | Another Python ADIF library. If adif-io is abandoned, adif3 is a fallback. Evaluate both at project start. | [LOW confidence — verify on PyPI] |
| Custom parser (fallback) | N/A | ADIF parsing | ADIF format is simple enough to implement a robust parser in ~100 lines of Python if neither library is actively maintained. The format spec is at adif.org. Prefer a maintained library first. | [HIGH confidence on feasibility] |

### Web UI

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| HTMX | 1.9+ | Frontend interactivity | Delivers a functional, interactive UI without a JavaScript build pipeline. Operators submit QSOs via forms; HTMX swaps in results in-place. Right-size for a logbook: no React/Vue complexity for what is essentially a CRUD interface. Works naturally with Jinja2 server-side rendering. | [MEDIUM confidence]
| Jinja2 | 3.x | Server-side templating | Ships with FastAPI optionally; standard Python templating. Renders QSO list, import results, and log views. | [MEDIUM confidence]
| TailwindCSS | 3.x (CDN) | Styling | Use via CDN for simplicity. No Node.js build step required. Sufficient for a logbook UI. If a richer UI is needed later, upgrade to a full Vite+Tailwind pipeline. | [MEDIUM confidence]

### Infrastructure / Deployment

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Docker | latest | Containerization | Single `docker compose up` for self-hosted deployments. Bundles Python app + MongoDB + optional reverse proxy. Essential for the "self-hosted or cloud" requirement. | [HIGH confidence]
| Docker Compose | v2 | Local dev + self-hosted | Defines app, MongoDB, and Caddy/Nginx as services. Makes onboarding trivial for self-hosters. | [HIGH confidence]
| Caddy | 2.x | Reverse proxy / TLS | Automatic HTTPS via Let's Encrypt with zero config. Better DX than Nginx for self-hosted scenarios where the operator may not be a sysadmin. | [MEDIUM confidence]

### Testing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | 8.x | Test runner | Standard. | [MEDIUM confidence]
| httpx | 0.27+ | Async HTTP test client | FastAPI's TestClient is synchronous; httpx provides an async client for testing async endpoints. FastAPI's official docs recommend httpx for async testing. | [MEDIUM confidence]
| pytest-asyncio | 0.23+ | Async test support | Required to `await` coroutines inside pytest tests. | [MEDIUM confidence]
| mongomock-motor | latest | In-memory MongoDB for tests | Allows unit tests to run without a live MongoDB instance. Speeds up CI. | [LOW confidence — verify it supports Motor 3.x and your MongoDB version] |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| HTTP Framework | FastAPI | Flask | Flask is sync-first; async support via Quart is a workaround. No built-in OpenAPI. Would require flask-smorest or flasgger for docs. FastAPI wins on DX and async native. |
| HTTP Framework | FastAPI | Django + DRF | Django's ORM is wasted (MongoDB backend). DRF's serializer system duplicates Pydantic. Significant added complexity for no benefit here. |
| MongoDB Driver | Motor (async) | PyMongo (sync) | PyMongo blocks the event loop inside FastAPI async handlers. Wrapping in `run_in_executor` is possible but defeats the purpose. Motor is the correct choice. |
| ODM | Beanie | MongoEngine | MongoEngine is sync-only. Not compatible with Motor/async FastAPI. |
| ODM | Beanie | Motor (raw) | Using Motor directly is fine; Beanie just reduces boilerplate. For a small project, Motor direct is also acceptable if the team prefers minimal abstraction. |
| Frontend | HTMX + Jinja2 | React / Vue SPA | SPA adds a Node.js build pipeline, CORS config, separate deployment concern, and JS bundle size for what is a CRUD interface. Operators accessing a self-hosted logbook do not need SPA performance characteristics. |
| Frontend | HTMX + Jinja2 | Flask-Admin / FastAPI-Admin | Admin UIs look like admin UIs. A purpose-built logbook UI can present QSO data in ham radio conventions (band plan colors, log table format, etc.) |
| TLS / Proxy | Caddy | Nginx | Nginx requires manual certificate management. Caddy's automatic HTTPS is a significant UX win for self-hosters. |
| ADIF Parsing | adif-io | Custom parser | Only use custom if adif-io is unmaintained or has correctness bugs. Do not build custom first. |

---

## Installation

```bash
# Core application
pip install "fastapi[all]" motor beanie python-jose[cryptography] passlib[bcrypt] adif-io Jinja2

# Dev / test
pip install -D pytest httpx pytest-asyncio mongomock-motor ruff mypy

# Pin versions in requirements.txt after verification:
# fastapi>=0.111,<0.200
# motor>=3.0,<4.0
# beanie>=1.0,<2.0
# python-jose[cryptography]>=3.3
# passlib[bcrypt]>=1.7
# adif-io>=0.0.6        # VERIFY current version on PyPI
# jinja2>=3.1
# uvicorn[standard]>=0.29
```

---

## Key Architecture Decisions Driven by Stack

**ADIF fields as MongoDB keys:** Store each QSO document with ADIF field names directly as top-level keys (`CALL`, `BAND`, `MODE`, `QSO_DATE`, `RST_SENT`, etc.). Do not map to "Pythonic" snake_case internally — it adds a translation layer and breaks round-trip fidelity on ADIF import/export. Pydantic model aliases can present snake_case in Python while serializing to ADIF names.

**Callsign as partition key:** Every QSO document includes `operator_callsign` (or use the ADIF `OPERATOR` field). All queries filter by this field first. Create a compound index on `(operator_callsign, QSO_DATE)` as the primary access pattern.

**ADIF import as streaming:** For large .adif file imports (contest logs can be 10,000+ QSOs), use `Motor`'s `insert_many` in batches of 500. Do not load the entire file into memory as a single Pydantic list.

---

## Version Verification Needed (LOW confidence items)

The following must be verified against PyPI / official docs before project kickoff:

- [ ] `adif-io` — confirm still maintained, check current version and last release date
- [ ] `adif3` — same check; compare parse correctness against ADIF 3.1.4 spec
- [ ] `mongomock-motor` — confirm Motor 3.x compatibility
- [ ] `python-jose` — check for any security advisories (JWT libraries accumulate CVEs)
- [ ] FastAPI version — confirm 0.111+ is still current stable (may have moved to 0.11x or higher)

---

## Sources

**Confidence note:** All recommendations are based on training data (cutoff August 2025). No external verification was possible during this research session due to tool restrictions. Confidence levels reflect this:

- **HIGH**: Project requirements (MongoDB, Python) or industry-stable choices (Docker, bcrypt, pytest) unlikely to have changed
- **MEDIUM**: Well-established libraries that were current as of Aug 2025 but versions should be verified
- **LOW**: Smaller ecosystem libraries (especially ADIF-specific) where maintainership is uncertain

Authoritative sources to verify at project start:
- FastAPI docs: https://fastapi.tiangolo.com
- Motor docs: https://motor.readthedocs.io
- Beanie docs: https://beanie-odm.dev
- adif-io on PyPI: https://pypi.org/project/adif-io/
- adif3 on PyPI: https://pypi.org/project/adif3/
- ADIF spec: https://adif.org/adif
