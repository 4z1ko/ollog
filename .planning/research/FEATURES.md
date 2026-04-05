# Feature Research: Documentation Milestone (v1.3)

**Domain:** Self-hosted ham radio logging application — REST API reference, deployment guide, operator walkthrough, admin guide
**Researched:** 2026-04-04
**Confidence:** HIGH for API reference scope (derived from codebase inspection); MEDIUM for deployment guide content (cross-referenced against real-world self-hosted app docs from n8n, Supabase, Infisical); MEDIUM for workflow documentation structure (derived from CloudLog wiki, ham radio community patterns, and general technical-user onboarding conventions)

---

## Scope Note

This document covers ONLY the documentation milestone (v1.3). All application features are already built and
tested. The question is: what documentation features to produce, in what form, at what depth?

The existing codebase provides the ground truth for all API endpoints, auth flows, request/response schemas,
and configuration surface. The research task is: what does a self-hosted technical tool's documentation need
to contain to be genuinely useful to its target audience (club/contest operators comfortable with self-hosting)?

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that self-hosting technical users assume exist. Missing any of these makes the product feel
unfinished. These are the baseline for trust-building with the target audience.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| REST API endpoint reference (all routes) | Any project exposing a REST API is expected to document every endpoint, especially when operators need to integrate external tools (FLdigi, macros, scripts) | MEDIUM | 13 routes across 6 groups: auth (/auth/token, /auth/me), QSOs (5 routes), profile (2 routes), ADIF import/export (2 routes), admin (4 routes), SSE feed (1 route) |
| Auth flow documentation | JWT-based auth has two distinct flows (Bearer token for REST, HTTP cookie for SSE); neither is self-evident | LOW | The dual-auth model is a genuine gotcha — must be documented explicitly with curl/fetch examples |
| Request/response schemas for every endpoint | Operators scripting against the API need exact field names, types, and optional/required status | MEDIUM | Request bodies: QSOCreateRequest, CreateUserRequest, SetEnabledRequest, ResetPasswordRequest, ProfileUpdateRequest. Response shapes vary; ADIF import returns a structured report object |
| HTTP status codes and error payloads | Self-hosting operators diagnosing problems need to know what 409 means (duplicate or last-admin lockout guard), what 401 means, what 413 means | LOW | Document per-endpoint: normal code, error codes, and the JSON error payload shape |
| Example curl requests for each endpoint | The single most-requested element in API docs for technical users; reduces time-to-first-call | MEDIUM | One curl example per endpoint covering the happy path; auth header pattern shown once, referenced everywhere else |
| Deployment guide: prerequisites and install steps | Self-hosters need Docker + Docker Compose version requirements, git clone, env file setup, and `docker compose up` in order | LOW | Prerequisites: Docker 20.10+, Docker Compose v2. Steps: clone → copy .env.example → set SECRET_KEY → docker compose up -d |
| Environment variable reference | Every env var must be documented: name, purpose, required vs optional, example value | LOW | Variables: SECRET_KEY (required), MONGODB_URI, MONGODB_DB, JWT_EXPIRE_MINUTES, ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_CALLSIGN |
| Bootstrap admin account explanation | The admin account bootstrapped from env vars is non-obvious; operators need to know ADMIN_USERNAME/PASSWORD/CALLSIGN are only read at first startup | LOW | Explain one-time bootstrap; explain how to create additional operators via admin UI/API afterward |
| Operator getting-started walkthrough | First-time operators need a linear path from login to first logged QSO; the UI is functional but not self-explanatory to non-developers | LOW | Steps: login → set profile (callsign, grid, equipment) → log a QSO → verify in log view → see it in station feed |
| ADIF import/export instructions | Operators migrating from HRD, Log4OM, or FLdigi need to know the import process, the file size limit (10 MB), and what the import report means | LOW | Document the import report fields (accepted, duplicates, errors) so operators know when to use force=true or when to investigate errors |
| Admin account management guide | Admins who are not developers need step-by-step instructions for creating accounts, enabling/disabling operators, and resetting passwords | LOW | Admin UI exists; also document the equivalent API calls for scripted provisioning |

### Differentiators (Value Beyond Baseline)

Features that go beyond a minimal reference dump and reflect the actual complexity of the domain and
deployment model.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Dual-auth model explanation (Bearer vs Cookie) | The SSE /feed/station endpoint requires cookie auth because the browser EventSource API cannot send Authorization headers; this is non-obvious and will block operators who try to curl the SSE endpoint or automate feed access | LOW | Include a dedicated auth section explaining both flows, why each is used, and what happens if wrong auth type is used |
| Duplicate detection behavior documentation | The ±2 minute fuzzy window for duplicate detection is not visible in the UI; operators importing historical logs or logging under contest conditions will encounter 409s they don't understand | LOW | Explain the window, what a 409 duplicate response contains (existing_id, existing_call), and when/how to use force=true |
| Soft-delete explanation | Deleted QSOs are not removed from MongoDB — they are flagged `_deleted: true`; this matters for operators who delete a QSO and then try to re-import it (the re-import will succeed because find_duplicate only looks at non-deleted records) | LOW | One paragraph in the QSO deletion section explaining soft-delete semantics |
| ADIF import report field guide | The import report returns four fields (total_records, accepted, duplicates, errors); each has a different shape; operators who get partial imports need to understand how to read the error list | LOW | Document the full import report schema with an annotated example response |
| Profile auto-stamp behavior | Operators logging via REST API may be surprised to find OPERATOR, STATION_CALLSIGN, MY_GRIDSQUARE etc. auto-injected into QSOs from their profile — document this clearly so they don't think the API is broken | LOW | Include a "profile stamping" section in operator walkthrough |
| Replica set requirement explanation | MongoDB must be configured as a single-node replica set to support change streams for the SSE feed; bare mongodb without --replSet rs0 will fail silently on the feed | LOW | Include in deployment guide: why the replica set is required, that the docker-compose.yml handles this automatically, what to check if the feed doesn't work |
| Extra ADIF fields (extensibility) | POST /api/qsos accepts arbitrary ADIF fields beyond the declared set (extra="allow"); documenting this lets operators log SOTA references, contest exchanges, or any ADIF field without waiting for a new release | MEDIUM | Include a section on arbitrary ADIF field storage with an example showing APP_HAMLOG_NOTE or SOTA_REF in a QSO body |
| Callsign prefix / flag lookup note | Flag display is render-time only; flag data is never stored in the QSO document and never appears in the REST API response or ADIF export — document this so operators don't search for a flag/country field in the API | LOW | One sentence in the QSO schema section |

### Anti-Features (Commonly Requested, Often Problematic)

Documentation patterns that seem valuable but create maintenance burden, confusion, or false expectations.
These are documentation anti-features — not application features.

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Auto-generated Swagger/ReDoc as the sole API reference | FastAPI generates Swagger UI at /docs automatically; seems like free documentation | Swagger UI requires the app to be running to be useful; it cannot be read offline or in a PR; it does not include narrative context (auth flows, duplicate behavior, SSE constraints); self-hosting operators often have the app on a LAN without public docs access | Write a static Markdown API reference that includes Swagger UI as a supplement, not as the primary reference |
| Video walkthrough as the operator guide | Video seems comprehensive and accessible | Videos go stale immediately when the UI changes; self-hosting technical users prefer copy-pasteable commands and scannable text; videos are inaccessible without audio and cannot be searched | Markdown walkthrough with annotated screenshots (or none) and numbered steps |
| Comprehensive "all ADIF fields" table | ADIF 3.1.7 has hundreds of fields; might seem valuable to enumerate them all | ollog stores all valid ADIF fields (extra="allow") but only requires 5; a full ADIF field table is a maintenance burden and belongs in the ADIF spec, not the app docs | Document only the required fields and the ~10 most common optional fields; link to adif.org/317 for the full spec |
| FAQ document without a search | FAQ sections appear in many self-hosted project docs | FAQs grow without structure; users cannot scan them; they become stale; they duplicate content from other pages | Put common-problem content in context: auth failures in the auth section, import errors in the import section, feed not working in deployment troubleshooting |
| API reference as a single monolithic page | Puts all 13 endpoints in one file; seems complete | Massive single page is hard to navigate, hard to link to individual endpoints, and hard to update incrementally | Organize by feature group (auth, QSOs, profile, ADIF, admin, SSE) as distinct sections within a structured document |
| Changelog in the documentation | Developers sometimes include changelogs in user-facing docs | Self-hosting club operators don't care about developer changelog entries; it adds noise and becomes stale | Keep changelog in git commit history and ROADMAP.md; link to GitHub releases if public |
| Architecture/internals documentation for operators | Some projects document MongoDB schema, Beanie models, etc. in user-facing docs | Club operators running ollog don't need to know about Beanie or change streams; it creates confusion and maintenance burden | Internal architecture belongs in ARCHITECTURE.md (planning), not in operator-facing docs. Admin guide covers only operational concerns |

---

## Feature Dependencies

```
REST API Reference
    └──requires──> Auth flow documentation
                       └──covers──> Bearer token (POST /auth/token → use in Authorization header)
                       └──covers──> Cookie auth (UI login only; SSE endpoint uses cookie, not Bearer)
    └──requires──> Request/response schema tables
    └──requires──> Example curl commands
    └──requires──> HTTP status code / error payload reference

Deployment Guide
    └──requires──> Environment variable reference (SECRET_KEY, MONGODB_URI, etc.)
    └──requires──> Bootstrap admin account explanation
                       └──prerequisite for──> Admin guide
    └──requires──> Replica set requirement note (why --replSet rs0 is in docker-compose.yml)

Operator Walkthrough
    └──requires──> Deployment Guide (app must be running first)
    └──requires──> Bootstrap admin + create-operator steps (operator account must exist)
    └──covers──> Profile setup (MY_GRIDSQUARE, STATION_CALLSIGN, equipment)
                     └──explains──> Profile auto-stamp behavior on POST /api/qsos
    └──covers──> Logging a QSO via UI
    └──covers──> Logging a QSO via REST API
    └──covers──> ADIF import + reading the import report
    └──covers──> ADIF export
    └──covers──> Station feed (SSE) in browser

Admin Guide
    └──requires──> Bootstrap admin account explanation (from Deployment Guide)
    └──covers──> Create operator account (UI + API)
    └──covers──> Enable/disable operator (UI + API)
    └──covers──> Reset password (UI + API)
    └──covers──> Last-admin lockout guard (409 when disabling last enabled admin)
```

### Dependency Notes

- **Deployment guide must come first:** Operator walkthrough and admin guide assume the app is running. Deployment guide is the prerequisite for all other documentation.
- **Bootstrap admin explanation bridges deployment and admin guide:** The ADMIN_USERNAME/PASSWORD/CALLSIGN env vars create the first account at startup. This is documented in the deployment guide and referenced again in the admin guide.
- **Auth flow explanation is the prerequisite for all REST API examples:** Every curl example depends on understanding how to obtain and pass a Bearer token. Auth must be documented before any endpoint examples.
- **Profile setup precedes QSO logging in the operator walkthrough:** Auto-stamp behavior makes profile setup a prerequisite for correct QSO logging. Document in that order.
- **Import report schema is standalone:** The ADIF import section has no hard dependency on other sections but should follow the basic operator walkthrough (so the reader has already logged QSOs before importing more).

---

## MVP Definition

### Launch With (v1.3)

Minimum viable documentation set — covers every shipped feature with enough detail for a self-hosting
technical operator to use the application without asking questions.

- [ ] REST API reference: all 13 endpoints, grouped by feature area, each with method + path, auth requirement, request schema, response schema, HTTP status codes, and one curl example
- [ ] Auth section: Bearer token flow (POST /auth/token + Authorization header), cookie auth for SSE (how the browser UI handles it, why curl cannot replicate the SSE endpoint without a session cookie), JWT expiry
- [ ] Deployment guide: prerequisites, clone/env setup, `docker compose up -d`, bootstrap admin account, how to verify the app is running
- [ ] Environment variable reference: SECRET_KEY (required, must change), MONGODB_URI, MONGODB_DB, JWT_EXPIRE_MINUTES (default 60), ADMIN_USERNAME / ADMIN_PASSWORD / ADMIN_CALLSIGN (one-time bootstrap)
- [ ] Operator getting-started walkthrough: login → profile setup → log first QSO via UI → log first QSO via API → ADIF import → ADIF export → station feed
- [ ] Admin account management guide: create operator, enable/disable, reset password, last-admin guard explanation

### Add After Validation (v1.x)

- [ ] Troubleshooting section for the deployment guide: SSE feed not updating (replica set issue), login fails (SECRET_KEY mismatch between containers, JWT expiry), import returns all duplicates (why and what to do)
- [ ] Integration example: how to point FLdigi or WSJT-X at ollog's REST API for automated QSO posting

### Future Consideration (v2+)

- [ ] OpenAPI spec file (openapi.json) published alongside the docs for tool integration
- [ ] Multi-language or localized documentation (English-only is correct for v1.3)
- [ ] Documentation versioning tied to application version tags

---

## Feature Prioritization Matrix

| Documentation Feature | User Value | Implementation Cost | Priority |
|-----------------------|------------|---------------------|----------|
| REST API endpoint reference (all 13 routes) | HIGH | MEDIUM | P1 |
| Auth flow (Bearer + cookie dual-auth explanation) | HIGH | LOW | P1 |
| Deployment guide (Docker Compose + env setup) | HIGH | LOW | P1 |
| Environment variable reference | HIGH | LOW | P1 |
| Bootstrap admin account explanation | HIGH | LOW | P1 |
| Operator getting-started walkthrough | HIGH | MEDIUM | P1 |
| Admin account management guide | MEDIUM | LOW | P1 |
| Duplicate detection behavior (±2 min window, force=true) | MEDIUM | LOW | P1 |
| ADIF import report schema (accepted/duplicates/errors) | MEDIUM | LOW | P1 |
| Replica set requirement explanation | MEDIUM | LOW | P1 |
| Profile auto-stamp behavior documentation | MEDIUM | LOW | P2 |
| Soft-delete semantics | LOW | LOW | P2 |
| Extra ADIF field extensibility (extra="allow") | LOW | LOW | P2 |
| Troubleshooting guide | HIGH | MEDIUM | P2 |
| FLdigi / WSJT-X integration example | MEDIUM | MEDIUM | P3 |

---

## Competitor / Comparable Project Reference

| Feature | CloudLog (PHP/MySQL, self-hosted) | ollog | Note |
|---------|-----------------------------------|-------|------|
| API reference | GitHub wiki, API key auth, curl examples | Bearer JWT auth, Markdown reference needed | CloudLog wiki is the closest comparable; demonstrates that API key examples in curl are sufficient for this audience |
| Deployment guide | Apache/MySQL manual install + Docker alternative | Docker Compose only | Docker-only is simpler; deployment guide is correspondingly shorter |
| Operator walkthrough | Basic wiki pages, no linear flow | Linear walkthrough needed | Ham radio self-hosters tolerate sparse docs but appreciate a clear first-run flow |
| Admin guide | Admin panel documented inline | Admin UI + API both need documentation | Admin audience is likely the same person as the deployer |

CloudLog's wiki (github.com/magicbug/Cloudlog/wiki/API) demonstrates that a curl-based API reference
with JSON request/response examples is the right format for this user population. It does not use
Swagger UI as the primary reference. The target audience (self-hosting hams) will recognize and
appreciate this pattern.

---

## Ham Radio Domain Notes Relevant to Documentation

These are domain facts that must be documented to prevent operator confusion; they are not obvious
from general web-app mental models.

1. **ADIF field names are uppercase by convention** — the API uses CALL, BAND, MODE, QSO_DATE, TIME_ON as JSON keys. This surprises developers used to snake_case APIs. Must be documented in the API reference with an explicit note.

2. **BAND values are strings, not numbers** — "20M", "40M", not 14.000 or similar. FREQ is a separate optional field. Document valid examples.

3. **QSO_DATE format is YYYYMMDD, TIME_ON format is HHMM or HHMMSS** — ADIF date/time format is not ISO 8601. Operators scripting against the API will use wrong formats. Examples are essential.

4. **STATION_CALLSIGN vs OPERATOR** — these are different ADIF fields with different semantics: OPERATOR is the person logging (from their login identity), STATION_CALLSIGN is the callsign transmitted over the air (e.g., club callsign). This distinction must be explained in the profile setup section.

5. **SSE /feed/station is browser-only in practice** — the endpoint requires cookie auth (not Bearer), because the browser EventSource API cannot send custom headers. Operators should not expect to consume the SSE feed programmatically without implementing cookie session management.

---

## Sources

| Source | Confidence | Use |
|--------|------------|-----|
| ollog codebase: app/qso/router.py, app/auth/router.py, app/admin/router.py, app/profile/router.py, app/adif/router.py, app/feed/router.py | HIGH | Ground truth for all endpoint paths, request/response schemas, auth dependencies, status codes |
| ollog docker-compose.yml | HIGH | Deployment surface: replica set config, env var names, service healthcheck |
| ollog app/config.py | HIGH | Complete env var inventory: SECRET_KEY, MONGODB_URI, MONGODB_DB, JWT_EXPIRE_MINUTES, ADMIN_* |
| [CloudLog API wiki](https://github.com/magicbug/Cloudlog/wiki/API) | MEDIUM | Comparable self-hosted ham radio API documentation format; curl examples are standard for this audience |
| [n8n Docker Compose self-hosted guide](https://docs.n8n.io/hosting/installation/server-setups/docker-compose/) | MEDIUM | Real-world self-hosted deployment guide structure: prerequisites, env vars, verification steps |
| [Supabase self-hosting Docker guide](https://supabase.com/docs/guides/self-hosting/docker) | MEDIUM | Env var reference format (.env.example pattern), secrets guidance, bootstrap account pattern |
| [Infisical Docker Compose docs](https://infisical.com/docs/self-hosting/deployment-options/docker-compose) | MEDIUM | Pre-launch checklist pattern; "CHANGEME" env var marking convention |
| [FastAPI OpenAPI documentation guide](https://fastapi.tiangolo.com/advanced/extending-openapi/) | HIGH | FastAPI auto-generates /docs (Swagger UI) and /redoc; these are supplementary, not the primary reference |
| [GitHub REST API getting started](https://docs.github.com/en/rest/using-the-rest-api/getting-started-with-the-rest-api) | MEDIUM | Pattern: curl examples, auth section first, then endpoint groups |

---
*Feature research for: ollog v1.3 — documentation milestone*
*Researched: 2026-04-04*
