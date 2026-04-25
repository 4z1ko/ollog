---
phase: 51
plan: "02"
subsystem: llms-txt
tags: [routes, file-response, tdd-green, wave-2]
dependency_graph:
  requires:
    - static/llms.txt (Plan 01 stub)
    - static/llms-full.txt (Plan 01 stub)
    - tests/test_llms.py (Plan 01 TDD RED tests)
  provides:
    - GET /llms.txt — FileResponse route wired in app/main.py
    - GET /llms-full.txt — FileResponse route wired in app/main.py
  affects:
    - app/main.py (2 new routes + 1 import addition)
tech_stack:
  added: []
  patterns:
    - FileResponse with hardcoded path and explicit media_type for public static routes
    - include_in_schema=False on @app.get decorator to exclude from OpenAPI
    - Unauthenticated public routes matching /health pattern (no Depends())
key_files:
  created: []
  modified:
    - app/main.py
decisions:
  - "FileResponse path is relative string 'static/llms.txt' (not pathlib.Path) — matches StaticFiles mount convention and works with uvicorn run from project root"
  - "media_type='text/plain; charset=utf-8' passed explicitly — auto-detection omits charset=utf-8 and fails LLMS-03"
  - "No filename= parameter — we want browser to render content, not trigger download"
  - "Routes placed between /static mount (line 179) and exception_handler (line 182) — matches existing ordering convention"
metrics:
  duration: "3m"
  completed: "2026-04-25"
  tasks_completed: 1
  files_created: 1
  files_modified: 1
---

# Phase 51 Plan 02: Route Wiring — /llms.txt and /llms-full.txt

Two `@app.get` routes added to `app/main.py` using `FileResponse` with explicit `text/plain; charset=utf-8` media type and `include_in_schema=False`, wiring the stub files created in Plan 01 to the HTTP endpoints.

## What Was Built

**Task 1 — FileResponse import + two route handlers (feat, 5c9023f)**

Made exactly two edits to `app/main.py`:

1. Updated line 9: added `FileResponse` to the `from fastapi.responses import ...` line (alphabetical order: `FileResponse, JSONResponse, RedirectResponse`).

2. Inserted two `@app.get` route handlers between the `/static` `StaticFiles` mount and the `@app.exception_handler(HTTPException)` block. Each route returns a `FileResponse` with a hardcoded relative path and explicit `media_type="text/plain; charset=utf-8"`. Both carry `include_in_schema=False` to exclude them from `/openapi.json`.

No other part of `app/main.py` was modified — lifespan, router includes, `/health`, `/api/whoami` all unchanged.

## Success Criteria Met

- `app/main.py` imports `FileResponse` from `fastapi.responses`: YES
- `@app.get("/llms.txt", include_in_schema=False)` route defined: YES
- `@app.get("/llms-full.txt", include_in_schema=False)` route defined: YES
- `test_llms_index` passes (GET /llms.txt returns 200 with "# ollog"): YES
- `test_llms_full` passes (GET /llms-full.txt returns 200 with all 3 section headers): YES
- `test_llms_content_type` passes (both routes return `text/plain; charset=utf-8`): YES
- `test_llms_not_in_schema` passes (neither path in `/openapi.json`): YES
- Content tests 5-7 still FAIL as expected (Plan 03 addresses them): YES — 4 passed, 3 failed
- `app/main.py` is syntactically valid: YES (`ast.parse` exits 0)
- No other files modified: YES (only 1 file changed in commit)

## TDD Gate Compliance

- RED gate (test commit): 8e68a49 — from Plan 01 `test(51-01): add failing smoke tests ...`
- GREEN gate (feat commit): 5c9023f — `feat(51-02): add /llms.txt and /llms-full.txt FileResponse routes to app/main.py`
- Tests 1-4 were RED (404) before this plan; they are GREEN (200) after this plan.
- Tests 5-7 remain RED intentionally — Plan 03 is the GREEN gate for content tests.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None introduced by this plan. The stub static files from Plan 01 remain unchanged — they are intentionally documented in 51-01-SUMMARY.md and will be replaced by Plan 03.

## Threat Flags

No new threat surface introduced. Threat register from plan's `<threat_model>` fully mitigated:

- T-51-02 (Tampering via path param): Mitigated — path is a hardcoded string literal, no user input reaches FileResponse.
- T-51-03 (OpenAPI exposure): Mitigated — `include_in_schema=False` on both decorators; `test_llms_not_in_schema` enforces at test level.
- T-51-04 (DoS via file read): Accepted — files are small static text; no DB query; standard reverse proxy rate limiting out of scope.
- T-51-05 (Unauth access to sensitive data): Accepted — content is intentionally public LLM tooling discovery; stubs contain no secrets.

## Self-Check: PASSED

- `app/main.py` modified: FOUND
- Commit 5c9023f exists: CONFIRMED (git log)
- `grep -c "^from fastapi.responses import FileResponse" app/main.py` = 1: CONFIRMED
- `grep -c '@app.get("/llms.txt", include_in_schema=False)' app/main.py` = 1: CONFIRMED
- `grep -c '@app.get("/llms-full.txt", include_in_schema=False)' app/main.py` = 1: CONFIRMED
- `grep -c 'media_type="text/plain; charset=utf-8"' app/main.py` = 2: CONFIRMED
- 4 tests pass, 3 fail (expected): CONFIRMED
- `schema OK` from openapi schema check: CONFIRMED
