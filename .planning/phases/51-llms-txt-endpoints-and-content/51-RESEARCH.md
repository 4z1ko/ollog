# Phase 51: llms.txt Endpoints and Content — Research

**Researched:** 2026-04-24
**Domain:** FastAPI static file serving, llms.txt spec, content authoring from MkDocs source
**Confidence:** HIGH

## Summary

Phase 51 adds two plain-text endpoints to the operator app (`GET /llms.txt` and `GET /llms-full.txt`) backed by static files in `static/`. The files are read from disk on each request via `FileResponse`, meaning content updates require no Python changes — only editing the static files and restarting the app. Both routes carry `include_in_schema=False` to stay invisible to Swagger UI and `/openapi.json`.

The implementation has two distinct work streams: (1) the Python wiring (two routes in `app/main.py` or a new minimal router, plus two empty static files), and (2) content authoring (synthesizing existing MkDocs markdown from `docs/api-reference/`, `docs/reference/adif-field-reference.md`, and `docs/getting-started/` into well-structured plain text). The content authoring is the larger task — all 16+ REST endpoints must be documented with curl examples, the ADIF field reference must be reproduced in plain-text table form, and the getting-started walkthrough must be adapted from markdown to plain text.

All prior decisions are locked: `FileResponse` over `PlainTextResponse`, static files in `static/`, routes on the operator app only (port 8000), no admin app involvement, no dynamic generation.

**Primary recommendation:** Add both routes directly to `app/main.py` (no new router file needed — these are two trivial `@app.get` decorators at the app level, consistent with `/health` and `/api/whoami`). Write `static/llms.txt` and `static/llms-full.txt` as the sole content artifacts.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Endpoint routing (GET /llms.txt, /llms-full.txt) | API / Backend (FastAPI) | — | These are HTTP routes on the operator app; FastAPI owns route dispatch |
| File content serving | API / Backend (FileResponse) | CDN / Static | FileResponse reads from `static/` on each request; content is static text |
| Content updates | Static file authoring | — | Operator edits `static/llms.txt` directly; no Python layer involved |
| OpenAPI schema exclusion | API / Backend | — | `include_in_schema=False` is a FastAPI route decorator parameter |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | already installed | Route declaration, `FileResponse`, `include_in_schema` | Project foundation |
| `fastapi.responses.FileResponse` | n/a (bundled with FastAPI) | Serve static files with correct headers | Reads from disk per request; no in-memory caching means edits take effect on restart |

### No New Dependencies

This phase requires zero new `pyproject.toml` entries. All needed classes (`FileResponse`) are already part of the installed FastAPI package and are already imported in `app/admin/ui_router.py`.

[VERIFIED: project codebase — `from fastapi.responses import FileResponse` already used in `app/admin/ui_router.py`]

## Architecture Patterns

### System Architecture Diagram

```
Browser / curl client
       |
       | GET /llms.txt  or  GET /llms-full.txt
       v
  FastAPI route in app/main.py
  (@app.get, include_in_schema=False)
       |
       | FileResponse(path="static/llms.txt", media_type="text/plain; charset=utf-8")
       v
  static/llms.txt  (or  static/llms-full.txt)
  — plain text file on disk —
       |
       v
  HTTP 200  Content-Type: text/plain; charset=utf-8
  body = file contents
```

### Recommended Project Structure

No new directories. Changes are:

```
app/
└── main.py              # Add two @app.get routes here (consistent with /health)

static/
├── css/                 # Existing
├── flags/               # Existing
├── llms.txt             # NEW: index file (title + description + section links)
└── llms-full.txt        # NEW: full content (API ref + ADIF field guide + getting started)
```

### Pattern 1: FileResponse Route with include_in_schema=False

**What:** A FastAPI `@app.get` route that reads a file from disk and returns it with a specified `media_type`. `include_in_schema=False` prevents the route from appearing in `/docs` or `/openapi.json`.

**When to use:** Any endpoint serving static content that must not be documented in the OpenAPI schema.

**Example:**
```python
# Source: Context7 — /fastapi/fastapi (advanced/path-operation-advanced-configuration)
from fastapi.responses import FileResponse

@app.get("/llms.txt", include_in_schema=False)
async def llms_index():
    return FileResponse(
        path="static/llms.txt",
        media_type="text/plain; charset=utf-8",
    )

@app.get("/llms-full.txt", include_in_schema=False)
async def llms_full():
    return FileResponse(
        path="static/llms-full.txt",
        media_type="text/plain; charset=utf-8",
    )
```

**Key facts about FileResponse** [VERIFIED: Context7 /fastapi/fastapi]:
- Streams the file from disk — it does NOT cache content in memory
- Automatically adds `Content-Length`, `Last-Modified`, and `ETag` headers
- Reading from disk on every request means editing the file and restarting serves updated content (satisfies LLMS-04)
- `media_type` parameter sets `Content-Type` header verbatim — use `"text/plain; charset=utf-8"` to satisfy LLMS-03

### Pattern 2: Where to Place the Routes

**Decision (from STATE.md):** Routes belong in `app/main.py` directly — no new router file.

**Rationale:** The `/health` and `/api/whoami` endpoints in `app/main.py` demonstrate the project pattern for small, standalone routes that don't belong to a specific domain router. These llms.txt routes are similarly borderless — they serve static content, not domain logic.

**Placement:** Add after the `app.mount("/static", ...)` line and before the `@app.exception_handler` block. Import `FileResponse` at the top of `app/main.py` alongside the existing imports from `fastapi.responses`.

[VERIFIED: project codebase — `app/main.py` already imports from `fastapi.responses` (`JSONResponse`, `RedirectResponse`)]

### Anti-Patterns to Avoid

- **PlainTextResponse with file content read into memory:** `PlainTextResponse(content=open("static/llms.txt").read())` satisfies the content-type requirement but reads the entire file into memory at request time and — more critically — does NOT benefit from FileResponse's `Last-Modified` / `ETag` caching headers. More importantly, if the read happens outside the route (at import time), content changes would NOT be reflected without a full app restart restart, whereas FileResponse reads on each request.
- **Serving via StaticFiles mount:** The existing `app.mount("/static", StaticFiles(...))` would serve `static/llms.txt` at `/static/llms.txt`, not at `/llms.txt`. The llms.txt spec requires the endpoint to be at the root path. A StaticFiles mount cannot remap paths, so explicit routes are required.
- **New router file for two routes:** Creating `app/llms/router.py` for two trivial routes adds unjustified structural complexity. Place both in `app/main.py` like `/health`.
- **include_in_schema=False on the router include vs. the route:** Marking `include_in_schema=False` at the `app.include_router()` call level would be needed if these were router-based. For direct `@app.get` decorators on the FastAPI app instance, the parameter goes on the decorator itself.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File serving with correct headers | Custom streaming response, manual header construction | `FileResponse` | FileResponse auto-adds ETag, Last-Modified, Content-Length; handles range requests |
| Schema exclusion | Post-processing OpenAPI dict | `include_in_schema=False` on the route decorator | Built-in FastAPI parameter; zero custom code |
| Static file content updates | Runtime config reload, watchdog | Edit file + restart | App already restarts on deploy; FileResponse reads fresh on each request |

## Complete Endpoint Inventory (for llms-full.txt content)

This is the authoritative list of all 16 REST endpoints on the operator app (port 8000) that must be documented in `llms-full.txt` per CONTENT-01. Enumerated from all routers registered in `app/main.py`.

[VERIFIED: direct inspection of all router files]

### Auth Endpoints (`/auth/`, `app/auth/router.py`)

| # | Method | Path | Auth | Description |
|---|--------|------|------|-------------|
| 1 | POST | /auth/token | None (login) | OAuth2 form login; returns JWT `access_token` |
| 2 | GET | /auth/me | Bearer JWT | Returns authenticated user's username, callsign, role |

### QSO REST Endpoints (`/api/qsos/`, `app/qso/router.py`)

| # | Method | Path | Auth | Description |
|---|--------|------|------|-------------|
| 3 | POST | /api/qsos/ | Bearer JWT or X-API-Key | Create a new QSO; 201 on success, 409 on duplicate |
| 4 | GET | /api/qsos/ | Bearer JWT or X-API-Key | List QSOs with pagination + filters (call, band, mode, date, sort) |
| 5 | GET | /api/qsos/{qso_id} | Bearer JWT or X-API-Key | Fetch single QSO by ID; 404 if not owned or deleted |
| 6 | PATCH | /api/qsos/{qso_id} | Bearer JWT or X-API-Key | Partial update of QSO fields; 404 if not owned |
| 7 | DELETE | /api/qsos/{qso_id} | Bearer JWT or X-API-Key | Soft-delete QSO; 204 on success |

### ADIF Endpoints (`/api/adif/`, `app/adif/router.py`)

| # | Method | Path | Auth | Description |
|---|--------|------|------|-------------|
| 8 | POST | /api/adif/import | Bearer JWT | Import .adi/.adif file (multipart); returns JSON import report |
| 9 | GET | /api/adif/export | Bearer JWT | Stream operator's full logbook as .adi file download |

### Profile Endpoints (`/api/profile/`, `app/profile/router.py`)

| # | Method | Path | Auth | Description |
|---|--------|------|------|-------------|
| 10 | GET | /api/profile/ | Bearer JWT | Return operator's profile fields |
| 11 | PATCH | /api/profile/ | Bearer JWT | Update operator profile fields (partial update) |

### Token Endpoints (`/api/tokens/`, `app/tokens/router.py`)

| # | Method | Path | Auth | Description |
|---|--------|------|------|-------------|
| 12 | POST | /api/tokens/ | Bearer JWT | Create named API token; returns full token once |
| 13 | GET | /api/tokens/ | Bearer JWT | List all active tokens for the operator |
| 14 | DELETE | /api/tokens/{token_id} | Bearer JWT | Revoke (disable) a token; 204 on success |

### Health / Utility Endpoints (`app/main.py`)

| # | Method | Path | Auth | Description |
|---|--------|------|------|-------------|
| 15 | GET | /health | None | MongoDB health check; 200 ok or 503 error |
| 16 | GET | /api/whoami | Bearer JWT | Returns operator callsign from JWT |

**Total: 16 endpoints** — satisfies the "16+" requirement in CONTENT-01.

Note: UI routes (`/log/*`, `/feed/station`) and admin routes (`/admin/*`) are excluded from `llms-full.txt` per requirements (operator REST API focus, admin is separate).

## ADIF Field Reference (for llms-full.txt content)

Sourced from `docs/reference/adif-field-reference.md` and `app/qso/models.py` and `app/qso/router.py`.

[VERIFIED: direct inspection of codebase files]

### Required Fields (QSOCreateRequest)

| Field | Format | Example | Notes |
|-------|--------|---------|-------|
| CALL | Callsign string | DL1ABC | Contacted station; uppercased on ingest |
| QSO_DATE | YYYYMMDD | 20240415 | UTC date |
| TIME_ON | HHMM or HHMMSS | 1430 or 143045 | UTC start time |
| BAND | Amateur band designator | 40m, 20m, 2m | Uppercased on ingest |
| MODE | Uppercased mode string | SSB, CW, FT8, FM | Uppercased on ingest |

### Optional Fields

| Field | Format | Example | Notes |
|-------|--------|---------|-------|
| FREQ | MHz decimal string | 14.225 | Frequency |
| RST_SENT | Signal report string | 59, 599 | Report sent |
| RST_RCVD | Signal report string | 59, 599 | Report received |
| TX_PWR | Power string | 100 | Transmit power |
| COMMENT | Free text | — | Any comment |
| QTH | Location string | — | Contacted station location |
| GRIDSQUARE | Maidenhead grid | FN31pr | Contacted station grid |
| CONTEST_ID | Contest identifier | — | Contest reference |
| SRX / STX | Serial number strings | — | Contest exchange numbers |

### Auto-Stamped Fields (set by server, never in request body)

| Field | Source | Notes |
|-------|--------|-------|
| OPERATOR | JWT callsign | Always stamped; cannot be overridden |
| STATION_CALLSIGN | Operator profile `station_callsign` | Stamped when profile has it set |

### Application-Specific Fields

| Field | Context | Notes |
|-------|---------|-------|
| APP_OLLOG_TOKEN | UDP datagrams only | Per-datagram auth token for multi-operator UDP routing |

## llms.txt Format

The llms.txt convention (llmstxt.org) specifies:
- A short index document at `/llms.txt` containing: project title (H1), one-sentence description, and Markdown links to fuller content sections
- A full-content document at `/llms-full.txt` containing all machine-readable documentation

[ASSUMED: The llmstxt.org spec format — verified by the requirements description which explicitly names these fields in LLMS-01]

**Recommended `static/llms.txt` structure:**
```
# ollog

A self-hosted, multi-operator ham radio logbook with a REST API and ADIF import/export.

## Contents

- API Reference: https://your-host:8000/llms-full.txt#api-reference
- ADIF Field Reference: https://your-host:8000/llms-full.txt#adif-field-reference
- Getting Started: https://your-host:8000/llms-full.txt#getting-started
```

Note: Since `llms.txt` is served as plain text (not HTML), the links are literal URLs, not clickable anchors. The "section links" in LLMS-01 are best implemented as descriptive labels with the full URL to `llms-full.txt`. LLM tooling that fetches `llms.txt` will then fetch `llms-full.txt` for full content.

**Recommended `static/llms-full.txt` structure:**
```
# ollog — Full LLM Reference

[table of contents / anchors as plain-text section headers]

## API Reference
[16 endpoints with method, auth, request fields, response, status codes, curl example]

## ADIF Field Reference
[field tables, format conventions, duplicate detection]

## Getting Started
[login → profile → QSO via UI and REST API → ADIF import/export]
```

## Common Pitfalls

### Pitfall 1: StaticFiles Mount Intercepts the Path

**What goes wrong:** If `app.mount("/static", StaticFiles(directory="static"))` were mounted at `/` instead of `/static`, it would intercept all requests including `/llms.txt`. In the current codebase this is not a problem (mount is at `/static`), but the mount order matters.

**Why it happens:** FastAPI resolves mounts before route handlers when the path prefix matches. The `/static` mount only intercepts paths starting with `/static/`, so `GET /llms.txt` reaches route handlers normally.

**How to avoid:** Verify the static mount is at `/static` (it is). Add the new routes after the mounts in `app/main.py` to make the ordering explicit.

**Warning signs:** `GET /llms.txt` returns a 404 from StaticFiles rather than the route handler.

### Pitfall 2: media_type Does Not Auto-Detect for .txt

**What goes wrong:** `FileResponse(path="static/llms.txt")` without an explicit `media_type` will infer `text/plain` from the `.txt` extension, but the charset may not be explicitly set to `utf-8` in the Content-Type header. LLMS-03 requires `text/plain; charset=utf-8`.

**Why it happens:** FileResponse uses `mimetypes.guess_type()` for auto-detection, which returns `text/plain` but typically without charset.

**How to avoid:** Always pass `media_type="text/plain; charset=utf-8"` explicitly.

**Warning signs:** `curl -I http://localhost:8000/llms.txt` shows `content-type: text/plain` without `; charset=utf-8`.

### Pitfall 3: File Not Found Returns 500 Instead of 404

**What goes wrong:** If `static/llms.txt` does not exist, `FileResponse` raises a `FileNotFoundError` which FastAPI converts to a 500 Internal Server Error, not a 404.

**Why it happens:** FileResponse opens the file at response time, not at route definition time. If the file is missing, the error surfaces as an uncaught exception.

**How to avoid:** Create both static files (even as empty placeholders) before deploying the routes. The plan should include creating the static files as part of Wave 0 or the first task.

**Warning signs:** `GET /llms.txt` returns 500 even though the route is correctly defined.

### Pitfall 4: Routes After StaticFiles Mount in main.py

**What goes wrong:** The comment in `app/main.py` says `# Documentation site (served before /static — mount order is load-bearing in FastAPI)`. If the new `@app.get("/llms.txt")` decorators are placed before the mounts, they work correctly. If placed after the exception handler, they also work. The key is that they must be defined on the `app` object, not confused with any mount.

**Why it happens:** FastAPI processes routes before StaticFiles mounts when a path is not a prefix of the mount path. `/llms.txt` does not start with `/guide` or `/static`, so mount order is irrelevant for these routes.

**How to avoid:** Place the routes after the existing mounts for clarity. No functional risk either way.

### Pitfall 5: include_in_schema=False Must Be on the Route Decorator, Not the Router Include

**What goes wrong:** `app.include_router(router, include_in_schema=False)` suppresses the entire router from the schema. For routes defined directly on `app` (like `/health`), `include_in_schema=False` goes on the `@app.get(...)` decorator itself.

**Why it happens:** These are `@app.get` decorators, not router-based routes.

**How to avoid:** Use `@app.get("/llms.txt", include_in_schema=False)`.

[VERIFIED: Context7 /fastapi/fastapi — `@app.get("/items/", include_in_schema=False)` is the documented pattern]

## Code Examples

### Route Definition Pattern (in app/main.py)

```python
# Source: Context7 /fastapi/fastapi (advanced/path-operation-advanced-configuration)
from fastapi.responses import FileResponse  # Add to existing import

@app.get("/llms.txt", include_in_schema=False)
async def llms_index():
    """LLM tooling index — project title, description, section links."""
    return FileResponse(
        path="static/llms.txt",
        media_type="text/plain; charset=utf-8",
    )

@app.get("/llms-full.txt", include_in_schema=False)
async def llms_full():
    """Full LLM reference — API docs, ADIF field guide, getting started."""
    return FileResponse(
        path="static/llms-full.txt",
        media_type="text/plain; charset=utf-8",
    )
```

### Verification Commands

```bash
# Verify Content-Type header
curl -I http://localhost:8000/llms.txt

# Verify content-type and read content
curl http://localhost:8000/llms.txt

# Verify route is NOT in OpenAPI schema
curl http://localhost:8000/openapi.json | python3 -c "import json,sys; schema=json.load(sys.stdin); print('/llms.txt' in schema['paths'])"
# Expected output: False

# Full content endpoint
curl http://localhost:8000/llms-full.txt | head -20
```

### Test Pattern (no MongoDB required — pure HTTP)

```python
# Source: existing project test pattern (httpx.AsyncClient + ASGITransport)
from httpx import ASGITransport, AsyncClient
from app.main import app
import pytest, pytest_asyncio

@pytest.mark.asyncio
async def test_llms_txt_content_type():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/llms.txt")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert "charset=utf-8" in resp.headers["content-type"]

@pytest.mark.asyncio
async def test_llms_txt_not_in_schema():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/openapi.json")
    assert "/llms.txt" not in resp.json()["paths"]
    assert "/llms-full.txt" not in resp.json()["paths"]
```

Note: These tests do NOT require MongoDB because `FileResponse` routes have no database dependencies. However, they require that `static/llms.txt` and `static/llms-full.txt` exist on disk (even empty) for FileResponse to return 200 rather than 500.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| N/A — this is a new feature | FileResponse from static file | Phase 51 | First llms.txt support |

**llms.txt convention:** Introduced ~2024 by the llmstxt.org initiative. The standard places a short index at `/llms.txt` and optionally full content at `/llms-full.txt`. Most implementations serve static files rather than dynamically generating content.

## Open Questions

1. **Relative vs. absolute path in FileResponse**
   - What we know: FastAPI's `FileResponse` resolves paths relative to the process working directory (where `uvicorn` is started). In Docker, this is `/app`. The static directory is at `/app/static/`.
   - What's unclear: Whether `path="static/llms.txt"` works when running tests with `pytest` from a different working directory.
   - Recommendation: Use `path="static/llms.txt"` (relative, consistent with how `StaticFiles(directory="static")` is declared). The test harness should be run from the project root. If tests fail due to CWD issues, use `pathlib.Path(__file__).parent.parent / "static" / "llms.txt"` to construct an absolute path.

2. **Section links in llms.txt — URL format**
   - What we know: LLMS-01 requires "links to all content sections available in `/llms-full.txt`". LLMS-04 requires no Python changes for content updates.
   - What's unclear: Should links include the host (e.g., `http://localhost:8000/llms-full.txt`) or be relative (e.g., `/llms-full.txt`)?
   - Recommendation: Use relative paths (`/llms-full.txt`) so the file works regardless of the deployed hostname. LLM tooling that fetches `llms.txt` typically resolves relative links against the base URL.

## Environment Availability

Step 2.6: SKIPPED — Phase 51 is a pure code + static file change with no external tool dependencies beyond the already-running FastAPI app.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (already installed) |
| Config file | `pyproject.toml` (existing pytest config) |
| Quick run command | `uv run pytest tests/test_llms.py -x` |
| Full suite command | `uv run pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LLMS-01 | GET /llms.txt returns 200 with project title and section links | smoke | `uv run pytest tests/test_llms.py::test_llms_index -x` | No — Wave 0 |
| LLMS-02 | GET /llms-full.txt returns 200 with content sections present | smoke | `uv run pytest tests/test_llms.py::test_llms_full -x` | No — Wave 0 |
| LLMS-03 | Content-Type is text/plain; charset=utf-8 on both routes | smoke | `uv run pytest tests/test_llms.py::test_llms_content_type -x` | No — Wave 0 |
| LLMS-03 | Neither route appears in /openapi.json | unit | `uv run pytest tests/test_llms.py::test_llms_not_in_schema -x` | No — Wave 0 |
| LLMS-04 | Serving from static file (content change reflected without Python edit) | manual | N/A — edit file, restart, curl | N/A |
| CONTENT-01 | API reference present in llms-full.txt | content inspection | `uv run pytest tests/test_llms.py::test_llms_full_api_reference -x` | No — Wave 0 |
| CONTENT-02 | ADIF field reference present in llms-full.txt | content inspection | `uv run pytest tests/test_llms.py::test_llms_full_adif_reference -x` | No — Wave 0 |
| CONTENT-03 | Getting-started walkthrough present in llms-full.txt | content inspection | `uv run pytest tests/test_llms.py::test_llms_full_getting_started -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_llms.py -x`
- **Per wave merge:** `uv run pytest tests/`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_llms.py` — covers LLMS-01 through LLMS-04, CONTENT-01 through CONTENT-03
- [ ] `static/llms.txt` — must exist (even empty) before routes are added to avoid FileResponse 500
- [ ] `static/llms-full.txt` — must exist (even empty) before routes are added

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | These are public endpoints (no auth required) |
| V3 Session Management | No | Stateless file serving |
| V4 Access Control | No | Public endpoints; no operator-scoped data |
| V5 Input Validation | No | No user input; file path is hardcoded in source |
| V6 Cryptography | No | Plain text, no encryption |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal | Tampering | Hardcoded `path="static/llms.txt"` — no user-controlled path component |
| Information disclosure | Information Disclosure | Content is intentionally public; no secrets in static files (enforce in content authoring) |

**Security note:** The static files `static/llms.txt` and `static/llms-full.txt` must not contain any secrets, internal URLs, credentials, or deployment-specific configuration. Content should describe the API structure only.

## Project Constraints (from CLAUDE.md)

The following directives from CLAUDE.md apply to this phase:

| Directive | Impact on Phase 51 |
|-----------|-------------------|
| FastAPI sub-app StaticFiles: every sub-app that serves HTML must have its own StaticFiles mount | Not triggered — llms.txt routes are on the operator app (`app/main.py`) which already has `/static` mounted |
| apscheduler<4 upper bound is load-bearing | Not triggered — no pyproject.toml changes |
| FOUC prevention: inline IIFE in base.html is load-bearing | Not triggered — no template changes |
| Tailwind purge: new dark: classes must appear as complete literal strings | Not triggered — no CSS changes |
| Request flow: Router → Service → Beanie models | These routes bypass service/model layers; acceptable for static file serving |
| Tests require MongoDB on localhost:27017 | llms.txt tests do NOT need MongoDB — pure HTTP smoke tests. Mark with no mongo fixture. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | llmstxt.org convention uses H1 title + description + markdown links in the index file | llms.txt Format | Minor — content format can be adjusted without Python changes |
| A2 | Relative links in llms.txt (e.g., `/llms-full.txt`) are resolved correctly by LLM tooling | Open Questions | Low — worst case, use absolute URL template in static file |

## Sources

### Primary (HIGH confidence)

- Context7 `/fastapi/fastapi` — FileResponse constructor parameters, include_in_schema=False route decorator pattern
- `/Users/royco/ollog/app/main.py` — existing route structure, import patterns, StaticFiles mount positions
- `/Users/royco/ollog/app/admin/ui_router.py` — confirmed `FileResponse` import pattern already used in project
- `/Users/royco/ollog/app/qso/router.py` — endpoint enumeration (QSO CRUD)
- `/Users/royco/ollog/app/auth/router.py` — endpoint enumeration (auth)
- `/Users/royco/ollog/app/adif/router.py` — endpoint enumeration (ADIF import/export)
- `/Users/royco/ollog/app/profile/router.py` — endpoint enumeration (profile)
- `/Users/royco/ollog/app/tokens/router.py` — endpoint enumeration (API tokens)
- `/Users/royco/ollog/app/feed/router.py` — SSE endpoint (excluded from llms-full.txt per scope)
- `/Users/royco/ollog/docs/api-reference/index.md` — API reference source for CONTENT-01
- `/Users/royco/ollog/docs/reference/adif-field-reference.md` — ADIF field reference source for CONTENT-02
- `/Users/royco/ollog/docs/getting-started/first-qso.md` — getting started source for CONTENT-03
- `/Users/royco/ollog/.planning/STATE.md` — locked decisions (FileResponse, static files, operator app only)
- `/Users/royco/ollog/.planning/REQUIREMENTS.md` — requirement IDs and acceptance criteria

### Secondary (MEDIUM confidence)

- `/Users/royco/ollog/.planning/ROADMAP.md` — Phase 51 description and dependencies
- `/Users/royco/ollog/app/profile/schemas.py` — profile fields for ADIF auto-stamp documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — FileResponse already used in project; include_in_schema pattern verified in Context7
- Architecture: HIGH — route placement follows established project pattern (/health in app/main.py)
- Endpoint inventory: HIGH — enumerated from direct code inspection of all registered routers
- Content structure: MEDIUM — ADIF fields and getting-started walkthrough synthesized from existing docs; content authoring is the largest task
- Pitfalls: HIGH — based on direct code inspection of the working directory and FastAPI documentation

**Research date:** 2026-04-24
**Valid until:** 2026-06-01 (stable FastAPI APIs; static file pattern is unchanging)

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LLMS-01 | GET /llms.txt returns text/plain index with project title, description, section links | FileResponse pattern verified; route placement in app/main.py documented |
| LLMS-02 | GET /llms-full.txt returns text/plain with full API ref, ADIF field guide, getting-started | FileResponse pattern verified; all 16 endpoints enumerated; ADIF fields catalogued |
| LLMS-03 | Both routes return Content-Type: text/plain; charset=utf-8 and include_in_schema=False | media_type parameter documented; include_in_schema=False on @app.get() verified |
| LLMS-04 | Editing static/llms.txt or static/llms-full.txt and restarting serves updated content | FileResponse reads from disk per request — no in-memory caching |
| CONTENT-01 | llms-full.txt includes full API reference for all 16+ endpoints | All 16 endpoints enumerated with method, path, auth, and description |
| CONTENT-02 | llms-full.txt includes ADIF field reference (QSO_DATE, TIME_ON, BAND, MODE, etc.) | ADIF fields catalogued from model, router, and docs/reference/adif-field-reference.md |
| CONTENT-03 | llms-full.txt includes operator getting-started walkthrough | Source content in docs/getting-started/first-qso.md and docs/getting-started/index.md |
</phase_requirements>
