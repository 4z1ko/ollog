---
phase: 026-token-crud-api-and-profile-ui
plan: "01"
subsystem: api, ui, auth
tags: [tokens, beanie, htmx, jinja2, fastapi, rest, crud]

# Dependency graph
requires:
  - phase: 025-api-token-model-and-service
    provides: ApiToken Beanie document, generate_api_token(), hash_api_token(), validate_token_name()

provides:
  - REST CRUD: POST /api/tokens (201), GET /api/tokens (200), DELETE /api/tokens/{id} (204) — Bearer JWT auth
  - HTMX UI routes: POST /log/tokens/create, GET /log/tokens, DELETE /log/tokens/{id} — cookie auth, always 200
  - token_is_active() helper in service.py for Phase 27 X-API-Key auth dependency
  - expires_at: Optional[datetime] = None on ApiToken model
  - templates/log/token_created.html — show-once reveal banner
  - templates/log/tokens_list.html — token table with revoke buttons
  - templates/log/profile.html — token creation form + lazy-loaded token list sections
  - 9 integration tests in tests/test_token_api.py — all passing

affects:
  - 027-xapikey-auth: requires token_is_active() from service.py and ApiToken.expires_at
  - 028-udp-token-auth: token lookup via token_prefix before hash verification

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "HTMX always-200 pattern: POST/DELETE UI routes always return HTTP 200, error state in partial body"
    - "Show-once token reveal: full plaintext returned in POST response only, HMAC hash stored — raw never persisted"
    - "Duck-typed service helper: token_is_active() accepts Any to avoid circular imports at module load"
    - "hx-trigger=load lazy-loading: token list loaded into profile page via HTMX after DOM ready"

key-files:
  created:
    - app/tokens/router.py
    - templates/log/token_created.html
    - templates/log/tokens_list.html
    - tests/test_token_api.py
  modified:
    - app/tokens/models.py
    - app/tokens/service.py
    - app/qso/ui_router.py
    - app/main.py
    - templates/log/profile.html

key-decisions:
  - "HTMX routes always return HTTP 200 — never 4xx — to ensure HTMX 2.x swaps the error partial into DOM"
  - "token_is_active() uses Any type hint with duck typing to avoid circular import from service.py to models.py"
  - "Integration test fixture uses directConnection=true to bypass replica set hostname resolution"

patterns-established:
  - "Token revoke: hx-swap=outerHTML removes row by targeting #token-row-{id} with empty 200 response"
  - "Token list lazy load: hx-trigger=load on #token-list div, refreshed after create/revoke actions"
  - "Show-once banner dismiss: hx-get=/log/tokens refreshes #token-list and clears banner in one HTMX request"

# Metrics
duration: 52min
completed: 2026-04-09
---

# Phase 26 Plan 01: Token CRUD API and Profile UI Summary

**REST token CRUD (POST/GET/DELETE /api/tokens) with Bearer JWT auth, HTMX-driven Profile Settings token section with show-once reveal banner, and 9 passing integration tests**

## Performance

- **Duration:** 52 min
- **Started:** 2026-04-09T18:23:37Z
- **Completed:** 2026-04-09T19:15:42Z
- **Tasks:** 3
- **Files modified:** 9 (4 created, 5 modified)

## Accomplishments

- REST token CRUD router with proper user_id ownership enforcement on every query and delete
- HTMX UI routes integrated into ui_router: lazy-loaded token list, show-once creation banner, silent revoke
- ApiToken model patched with expires_at field; token_is_active() helper ready for Phase 27 auth dependency
- Profile Settings page extended with API Tokens creation form and active token list section
- 9 integration tests covering create, expiry, invalid name, list, revoke, cross-user isolation, and unauthenticated access

## Task Commits

1. **Task 1: Patch ApiToken model and add token_is_active() service helper** - `94e53bd` (feat)
2. **Task 2: REST token router and HTMX UI routes, wired into main.py** - `1f6f0a9` (feat)
3. **Task 3: Templates, profile page token sections, and integration tests** - `542330b` (feat)

## Files Created/Modified

- `app/tokens/models.py` - Added `expires_at: Optional[datetime] = None` between last_used_at and enabled
- `app/tokens/service.py` - Added `token_is_active(token: Any) -> bool` with enabled + expiry checks; added `Any` import
- `app/tokens/router.py` - NEW: REST CRUD — POST /api/tokens (201), GET /api/tokens (200), DELETE /api/tokens/{id} (204)
- `app/qso/ui_router.py` - Added GET/POST/DELETE /log/tokens routes and ApiToken/service imports
- `app/main.py` - Registered token_router after profile_router
- `templates/log/token_created.html` - NEW: show-once reveal banner with copy + dismiss buttons
- `templates/log/tokens_list.html` - NEW: token table with Revoke buttons, empty-state card
- `templates/log/profile.html` - Added API Tokens creation form card and lazy-loaded active tokens card
- `tests/test_token_api.py` - NEW: 9 integration tests covering full CRUD lifecycle and auth enforcement

## Decisions Made

- HTMX UI routes always return HTTP 200 with error state in partial body — HTMX 2.x convention (won't swap on 4xx)
- `token_is_active()` uses `Any` duck typing to avoid a circular import from `service.py` → `models.py` at load time
- Integration test fixture uses `directConnection=true` in the MongoDB URI — without it PyMongo follows RS advertised hostname (`mongodb:27017`) which isn't reachable from localhost test context

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Integration test fixture initially used `mongodb://localhost:27017` without `directConnection=true`; PyMongo tried to contact the replica set's advertised hostname `mongodb:27017` and timed out. Fixed immediately (Rule 3 — blocking issue) before tests could pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 27 can import `token_is_active` from `app.tokens.service` — function is live and tested
- `ApiToken.expires_at` field is in production model; existing documents without the field deserialize with `expires_at=None` (Pydantic v2 default for `Optional` with `None` default)
- REST endpoints at `/api/tokens/` are registered and documented in FastAPI's OpenAPI schema
- UI token section in Profile Settings is wired and ready for operator use

---
*Phase: 026-token-crud-api-and-profile-ui*
*Completed: 2026-04-09*
