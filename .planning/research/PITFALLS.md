# Pitfalls Research

**Domain:** Adding REST API documentation and app documentation to an existing FastAPI + HTMX + MongoDB app (ollog ham radio logbook)
**Researched:** 2026-04-04
**Confidence:** HIGH for FastAPI-specific schema pitfalls (codebase confirmed + official docs); MEDIUM for workflow doc drift and over-engineering (community evidence + general principle); HIGH for JWT dual-auth documentation (confirmed from codebase analysis).

---

## Critical Pitfalls

Mistakes that produce incorrect, misleading, or trust-destroying documentation.

---

### Pitfall 1: Documenting Cookie Auth Routes in the OpenAPI "Try It Out" Flow

**What goes wrong:**
The ollog app has two distinct auth flows. REST API endpoints under `/api/*` use Bearer token auth (`OAuth2PasswordBearer`, `get_current_user`). UI routes under `/log/*` and `/admin/ui/*` use an HttpOnly cookie (`get_current_user_cookie`). FastAPI's Swagger UI only understands the Bearer scheme that `OAuth2PasswordBearer` exposes. The cookie-auth dependencies (`get_current_user_cookie`, `require_admin_cookie`) produce no lock icon in the Swagger UI and cannot be tested interactively. If documentation does not clearly separate these two flows, a reader will attempt to use the Swagger "Authorize" button for cookie routes, get 401s, and conclude the docs are wrong or the app is broken.

**Why it happens:**
FastAPI auto-generates security schemes only for dependencies that inherit from `fastapi.security.SecurityBase`. `OAuth2PasswordBearer` does this. Cookie dependencies using `Cookie(default=None)` do not register as a security scheme — they appear in OpenAPI as a cookie parameter with no lock icon. Developers adding docs often copy the Bearer pattern to describe all auth without checking which dependency type each route actually uses.

**How to avoid:**
In the OpenAPI schema enhancement phase, mark UI routes explicitly as excluded from the "Try It Out" contract. Use `include_in_schema=False` on HTMX-specific routes (`/log/*`, `/admin/ui/*`) that exist only for browser rendering — they should not appear in Swagger at all, since they cannot be tested without a browser cookie context. For the narrative app documentation, dedicate a section called "Two Auth Flows" that draws a clear line: the `/auth/token` endpoint issues a token for REST API use (Bearer, Authorization header); the browser UI uses the same token stored in an HttpOnly cookie set by the login form submission.

**Warning signs:**
- Draft docs describe "logging in" without specifying where the token goes (header vs cookie).
- Swagger UI shows lock icons on `/api/*` endpoints but no lock icons on `/log/*` endpoints, and the docs don't explain why.
- The `/auth/token` endpoint is described as "how to log in" without distinguishing which consumers use that endpoint (REST clients) vs. which consumers use the `/log/login` form (browser operators).

**Phase to address:** OpenAPI schema cleanup phase (the first documentation phase). This must be resolved before writing narrative auth documentation, because the narrative must accurately reflect what Swagger shows.

**Confidence:** HIGH — confirmed by reading `app/auth/dependencies.py` (two parallel dependency chains) and FastAPI official security documentation.

---

### Pitfall 2: QSO Endpoints Return `dict` — OpenAPI Schema Shows `{}` (Empty Object)

**What goes wrong:**
Every QSO endpoint in `app/qso/router.py` declares `-> dict` as its return type and has no `response_model` parameter. FastAPI cannot infer a schema from a bare `dict` return annotation. The OpenAPI schema for `POST /api/qsos/`, `GET /api/qsos/`, `GET /api/qsos/{qso_id}`, `PATCH /api/qsos/{qso_id}` will all show `{}` as the response schema — an empty object. API consumers reading the docs have no way to know what fields the response contains without making a live request.

**Why it happens:**
The `dict` return type was chosen deliberately to handle the MongoDB `ObjectId`-to-string conversion and the arbitrary ADIF extra fields from `model_extra`. A Pydantic response model would need to declare `extra="allow"` and handle the `id` vs `_id` field renaming, which adds complexity. The shortcut (return dict, handle serialization manually in `_qso_to_dict`) is correct at runtime but invisible to OpenAPI.

**How to avoid:**
Add `response_model` Pydantic classes for the fields that are always present in QSO responses: `id`, `CALL`, `BAND`, `MODE`, `QSO_DATE`, `TIME_ON`, `FREQ`, `RST_SENT`, `RST_RCVD`, `qso_date_utc`. Mark extra ADIF fields with `model_config = ConfigDict(extra="allow")` in the response model so OpenAPI shows the declared fields plus an `additionalProperties: true` annotation. For the paginated list response, add a `QSOListResponse` model with `items`, `total`, `page`, `page_size` fields.

Alternatively: use `openapi_extra` on each route to inject a hand-authored response schema, keeping the `dict` return type but adding schema documentation without changing runtime behavior.

**Warning signs:**
- Swagger UI shows `{}` for any QSO endpoint's response schema.
- The "Schema" tab in Swagger shows only `object` with no properties.
- A developer reading the docs cannot determine what `id` field type is (string ObjectId, not int) without running the app.

**Phase to address:** OpenAPI schema cleanup phase. The response models are schema-only artifacts — they do not need to change runtime behavior.

**Confidence:** HIGH — confirmed by reading `app/qso/router.py` (all endpoints return `dict`, none have `response_model`).

---

### Pitfall 3: ADIF Import/Export Response Schema Is Undocumented

**What goes wrong:**
`POST /api/adif/import` returns a structured dict (`total_records`, `accepted`, `duplicates`, `errors`) with no `response_model`. `GET /api/adif/export` returns a `StreamingResponse` (raw `.adi` file download), which FastAPI cannot schema-ify at all. Neither endpoint has a meaningful OpenAPI response schema. The import report structure is non-obvious (each list contains dicts with `record_index`, `call`, `id`/`existing_id`/`error` keys). Without docs, consumers attempt to parse the response blindly.

**Why it happens:**
ADIF import/export was implemented for functionality, not for API consumers. The `StreamingResponse` for export is a deliberate choice (memory efficiency) and genuinely cannot be described with a JSON schema. The import report was built for the UI to parse — it was never explicitly designed as a public API contract.

**How to avoid:**
For the import endpoint: create a `ADIFImportReport` response model with typed fields. The `errors` list can be `list[dict]` with `openapi_extra` describing the error object shape, or a proper `ADIFImportError` model. For the export endpoint: use `openapi_extra={"responses": {"200": {"description": "ADIF file download", "content": {"text/plain": {}}}}}` to override the default JSON response schema. Document the `Content-Disposition` header and the `.adi` file format in the endpoint description.

**Warning signs:**
- Swagger UI shows no schema for `POST /api/adif/import` response.
- `GET /api/adif/export` shows `application/json` as the response content type in Swagger, not `text/plain`.
- Documentation says "import returns a report" without describing the report's structure.

**Phase to address:** OpenAPI schema cleanup phase.

**Confidence:** HIGH — confirmed by reading `app/adif/router.py`.

---

### Pitfall 4: JWT Auth Flow Under-Documented — Cookie vs. Bearer Confusion for Operators

**What goes wrong:**
Ham radio operators self-hosting ollog are not developers. The narrative app documentation must explain how authentication works in plain language without assuming HTTP knowledge. The two common failures: (1) docs describe the login flow only for the browser UI (cookie), leaving API users (scripters, log-sync tools) without instructions for Bearer token usage; (2) docs describe the Bearer flow only, leaving operators confused about why the browser "just works" without them manually setting Authorization headers.

A secondary failure: the JWT token expiry is not documented. If an operator's script stops working after a session expires and the docs say nothing about token lifetime or how to re-authenticate, the support burden falls entirely on the app README.

**Why it happens:**
Developers understand the distinction intuitively. When writing for ham radio operators who may be experts in RF propagation but novices in API authentication, the mental model gap is invisible to the author.

**How to avoid:**
Write two explicit paths in the narrative docs: "Using ollog from a browser" (automatic cookie, no manual steps) and "Using ollog from a script or external tool" (POST to `/auth/token`, extract `access_token`, include as `Authorization: Bearer <token>` on subsequent requests). Include the token expiry setting from `app/config.py` (`ACCESS_TOKEN_EXPIRE_MINUTES`). Show a curl example for each path.

**Warning signs:**
- Docs describe authentication in one unified section without distinguishing the two use cases.
- No mention of `Authorization: Bearer` anywhere in the narrative docs.
- No mention of token expiry or what happens when the token expires.
- No curl example for obtaining a token via `/auth/token`.

**Phase to address:** Narrative app documentation phase (after OpenAPI schema is correct, the narrative can reference it).

**Confidence:** HIGH — confirmed from codebase inspection of the two dependency chains.

---

### Pitfall 5: ADIF Field Names Not Explained in Any Documentation Layer

**What goes wrong:**
The ollog REST API uses bare ADIF field names as JSON keys: `CALL`, `BAND`, `MODE`, `QSO_DATE`, `TIME_ON`, `FREQ`, `RST_SENT`, `RST_RCVD`. These are opaque to anyone who has not read the ADIF specification. The format for `QSO_DATE` is `YYYYMMDD` (not ISO 8601). The format for `TIME_ON` is `HHMM` or `HHMMSS`. `RST` stands for Readability-Strength-Tone (a signal report scale). `BAND` uses amateur radio band designators (`40m`, `20m`, `2m`, not frequency ranges). These are not documented in the OpenAPI schema or in any current README.

**Why it happens:**
The developer writing the app is a ham radio operator and knows these terms. The assumption is that users of a ham radio logbook also know ADIF. This is partially true for experienced operators, but partially false for newly licensed operators or developers building integrations.

**How to avoid:**
Add `description` strings to every ADIF field in the QSO request/response Pydantic models (or via `openapi_extra` field descriptions). At minimum document: `QSO_DATE` format (YYYYMMDD, UTC), `TIME_ON` format (HHMM, UTC), `BAND` enumeration (link to ADIF band table), `MODE` enumeration (common values: SSB, CW, FT8, RTTY), `RST_SENT`/`RST_RCVD` explanation. In the narrative docs, include a "ADIF Field Reference" section that lists all fields the API accepts and their expected formats with examples.

**Warning signs:**
- OpenAPI schema shows `CALL: string` with no description.
- `QSO_DATE` description says "string" without the `YYYYMMDD` format.
- A reader cannot tell from the docs alone what value to put in `BAND` for a 14 MHz contact.

**Phase to address:** OpenAPI schema cleanup phase (descriptions on models) and narrative docs phase (ADIF field reference section).

**Confidence:** HIGH — confirmed by reading `QSOCreateRequest` in `app/qso/router.py` (no `Field(description=...)` on any ADIF field).

---

### Pitfall 6: Duplicate Detection Behavior Undocumented (409 Response + `force` Query Parameter)

**What goes wrong:**
`POST /api/qsos/` returns `409 Conflict` when a duplicate QSO is detected (same callsign, band, mode within ±2 minutes). The response body is a structured dict with `duplicate: true`, `existing_id`, and other fields. The `force=true` query parameter overrides duplicate detection. Neither the 409 response schema nor the `force` parameter semantics appear in the current OpenAPI schema (no `responses={409: ...}` on the route, no description on `force`). An API consumer who hits a 409 has no schema to parse the response against.

**Why it happens:**
The 409 behavior was implemented for correctness, not for external API consumers. The `force` parameter was added as a coding convenience for the ADIF import path, not as a documented feature.

**How to avoid:**
Add `responses={status.HTTP_409_CONFLICT: {"model": DuplicateQSOError, "description": "Duplicate QSO detected"}}` to the `create_qso` route decorator. Define `DuplicateQSOError` as a Pydantic model with `duplicate: bool`, `existing_id: str`, `existing_call: str`, `existing_band: str`, `existing_mode: str`, `existing_date: str`. Add a `Query(description=...)` string to the `force` parameter explaining what overriding duplicate detection means.

**Warning signs:**
- Swagger UI shows no 409 in the response section for `POST /api/qsos/`.
- The `force` query parameter has no description in Swagger.
- Documentation says "the API prevents duplicate QSOs" without explaining what a duplicate means (the ±2 minute window) or how to override it.

**Phase to address:** OpenAPI schema cleanup phase.

**Confidence:** HIGH — confirmed by reading `create_qso` in `app/qso/router.py`.

---

## Moderate Pitfalls

Issues that reduce documentation quality or trust without causing complete failure.

---

### Pitfall 7: Over-Engineering the Documentation Stack

**What goes wrong:**
A small self-hosted app with ~15 REST endpoints and a single-operator or small-group audience does not need MkDocs, Sphinx, Read the Docs, doctest runners, or auto-generated SDK clients. Adding a full documentation build pipeline (MkDocs Material + mike versioning + GitHub Actions deploy) to a self-hosted app creates maintenance overhead without proportional value. The operators who self-host ollog are reading documentation on a GitHub README or a locally served page — not browsing a polished documentation portal.

**Why it happens:**
Documentation tooling tutorials use impressive setups. Developers copy the impressive setup without asking whether it serves the actual audience.

**How to avoid:**
Keep documentation as Markdown files committed to the repository. FastAPI's built-in Swagger UI (`/docs`) serves as the interactive API reference with zero additional tooling. Narrative documentation lives in one or two well-organized Markdown files (or a flat directory). The threshold for adding MkDocs is "more than one person maintaining docs" or "documentation needs search." For ollog v1.x, that threshold is not met.

**Warning signs:**
- A `mkdocs.yml` appears in the project root before any Markdown content exists.
- The documentation milestone has more commits touching tooling config than actual content.
- Setup instructions for reading the docs are longer than the docs themselves.

**Phase to address:** The documentation architecture decision should be made before any content is written. Commit to Markdown-only early.

**Confidence:** MEDIUM — general principle backed by community evidence; no ollog-specific data.

---

### Pitfall 8: Workflow Documentation Written Before the UI Is Stable

**What goes wrong:**
HTMX apps with server-rendered partial HTML are particularly prone to small UI changes: a button label changes, a form field is renamed, a nav link moves. If the operator workflow documentation ("how to log a QSO," "how to import an ADIF file") is written before the UI iteration is complete, the screenshots and step-by-step instructions will be stale by the time anyone reads them. The workflow docs describe a flow that no longer matches the actual UI.

**Why it happens:**
Documentation feels like it should happen alongside development. But HTMX partial-response apps are hard to document mid-flight because every template change is potentially a documentation change.

**How to avoid:**
Write workflow documentation as the last act of the milestone, after the UI is in a committed stable state. Do not include screenshots in the first version of workflow docs — describe actions ("click Import in the navigation bar") rather than pointing at pixels. If a screen reference is necessary, use a descriptive title rather than an image file that must be kept in sync.

**Warning signs:**
- Workflow docs reference a UI element that has since been renamed or moved.
- Docs say "click the green button" but the button color changed.
- Docs describe a three-step flow that is now a two-step flow because a confirmation dialog was removed.

**Phase to address:** Narrative app documentation phase (write workflow docs last in that phase).

**Confidence:** MEDIUM — general principle; confirmed by examining ollog's HTMX template structure.

---

### Pitfall 9: Soft-Delete Behavior Not Documented in API Reference

**What goes wrong:**
`DELETE /api/qsos/{qso_id}` does not actually delete the MongoDB document — it sets `_deleted: true`. The QSO remains in the database. A `GET /api/qsos/{qso_id}` on a soft-deleted QSO returns 404. An API consumer who reads "DELETE returns 204" will assume the record is gone permanently and may write integration code that doesn't account for the `_deleted` flag. Operators importing ADIF files may not know that "deleting" a QSO in the UI doesn't remove it from MongoDB, which affects duplicate detection behavior (a soft-deleted QSO is invisible to `find_duplicate`).

**Why it happens:**
Soft-delete is an implementation detail that affects visible API behavior but is not surfaced anywhere in the current schema or any documentation.

**How to avoid:**
Add a note to the `DELETE /api/qsos/{qso_id}` endpoint description: "Soft-delete — the record is marked as deleted in the database but not physically removed. Soft-deleted QSOs do not appear in GET responses and are excluded from duplicate detection." In the narrative docs, include this behavior in the "Managing Your Log" section.

**Warning signs:**
- The DELETE endpoint description says only "Delete a QSO" with no soft-delete clarification.
- The 204 response description says nothing about the record being retained.
- There is no mention of the word "soft-delete" or "permanent" anywhere in the docs.

**Phase to address:** OpenAPI schema cleanup phase (endpoint descriptions); narrative docs phase (data management section).

**Confidence:** HIGH — confirmed from `app/qso/router.py` and `app/qso/models.py`.

---

### Pitfall 10: Health Endpoint and `/api/whoami` Not Placed Correctly in API Reference

**What goes wrong:**
`GET /health` is a monitoring endpoint that returns MongoDB connection status. `GET /api/whoami` is a diagnostic endpoint that returns the authenticated callsign from the JWT. Neither has a tag, so they appear in an ungrouped "default" section in Swagger. They do not have `response_model` declarations. Health is particularly problematic: its 503 response (when MongoDB is disconnected) is not documented in OpenAPI, and the response shape for 200 vs 503 differs (`{"status": "ok", "mongodb": "connected"}` vs `{"status": "error", "mongodb": "disconnected"}`). An operator monitoring the app does not know to look for a 503 from `/health` — only the 200 is obvious.

**Why it happens:**
Health and diagnostic endpoints are added quickly and never revisited. They feel "not part of the real API."

**How to avoid:**
Tag `/health` with `tags=["ops"]` or `tags=["monitoring"]`. Add `responses={503: {"description": "MongoDB unreachable"}}` to the health endpoint. Either tag `/api/whoami` with `tags=["auth"]` and include it as a diagnostic tool in the auth section of the narrative docs, or mark it `include_in_schema=False` if it is only a development diagnostic.

**Warning signs:**
- Swagger UI has a "default" group containing `/health` and `/api/whoami`.
- The health endpoint has no 503 documented.
- Operators do not know the app has a health check endpoint they can ping.

**Phase to address:** OpenAPI schema cleanup phase.

**Confidence:** HIGH — confirmed from `app/main.py`.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Return `dict` instead of `response_model` in QSO endpoints | Handles ObjectId and ADIF extras easily | OpenAPI schema shows `{}` for all QSO responses; API consumers cannot introspect shape | Never acceptable once docs are written — add response models or `openapi_extra` |
| No `Field(description=...)` on ADIF field names | Faster initial development | Every ADIF field is opaque in Swagger; operators must guess formats | Never acceptable in a documented API |
| Skipping `responses={409: ...}` on routes with custom error shapes | One fewer decorator argument | 409 error structure is invisible to API consumers | Acceptable only in pre-documentation phase |
| Writing workflow docs before UI is final | Feels productive | Docs are stale before anyone reads them | Never — always write narrative docs after UI stabilizes |
| Treating cookie-auth UI routes as "also documented in Swagger" | No extra work | Operators try to use Swagger for UI routes, hit 401s, lose trust in docs | Never — exclude UI routes from schema or explicitly call them out |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Swagger UI + Bearer token | Pasting the full "Bearer abc123" string into the Authorize dialog | The Swagger UI `OAuth2PasswordBearer` dialog wants only the token value, not the `Bearer ` prefix — document this explicitly |
| ADIF import via `/api/adif/import` | Sending JSON body instead of `multipart/form-data` file upload | The endpoint requires `UploadFile` — document `Content-Type: multipart/form-data` and show a curl example with `-F file=@logbook.adi` |
| ADIF export via `/api/adif/export` | Expecting JSON response | The endpoint returns `text/plain` with `Content-Disposition: attachment` — document that the response is a file download, not JSON |
| Bearer token in curl | Omitting the `Authorization: Bearer` prefix | Show explicit curl examples: `curl -H "Authorization: Bearer <token>" https://...` |
| `QSO_DATE` field format | Sending ISO 8601 (`2024-01-15`) instead of ADIF format (`20240115`) | Document the ADIF `YYYYMMDD` format with an explicit example; the API will return a 422 if the format is wrong |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Documenting the admin credentials used in environment variables (ADMIN_USERNAME, ADMIN_PASSWORD) | Credential exposure if docs are published | Docs should reference env var names only, never example values that look like real credentials |
| Showing a JWT token in documentation examples that could be mistaken for a real token | Social engineering / confusion | Use obviously fake tokens in examples: `eyJ...EXAMPLE_TOKEN_NOT_REAL` |
| Documenting the Bearer token flow without noting token expiry | Operators write scripts that break silently after session expiry | Always document `ACCESS_TOKEN_EXPIRE_MINUTES` and the re-authentication pattern |
| Publishing Swagger UI publicly on a self-hosted instance without auth | Exposes API surface to scanning | Note in docs that operators should restrict `/docs` access in production (nginx basic auth or network-level restriction) |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Narrative docs use developer-centric language ("JWT", "Bearer token", "OAuth2") for operator-facing sections | Ham radio operators who are not web developers disengage | Use plain language in operator sections: "the app issues a session token" not "the app issues a JWT via OAuth2 password flow" |
| ADIF field reference buried in technical API docs | Operators logging their first QSO cannot find what format `QSO_DATE` expects | Put the ADIF field reference in a prominent "Quick Reference" section early in the docs |
| Swagger UI is the only interactive interface documented | Self-hosters who are not developers will not use Swagger | Include curl examples for every API endpoint in the narrative docs; not all users will open Swagger |
| Workflow docs written in passive voice ("a QSO can be logged by...") | Operators don't know what action to take | Use imperative voice ("To log a QSO, click New QSO in the navigation bar") |

---

## "Looks Done But Isn't" Checklist

- [ ] **OpenAPI schema:** Every endpoint has a non-empty response schema (not `{}`) — verify by opening `/docs` and clicking each endpoint's Schema tab.
- [ ] **Auth documentation:** Both the Bearer token path and the browser cookie path are explicitly described — verify that the narrative docs contain the word "Bearer" at least once.
- [ ] **ADIF field formats:** `QSO_DATE` description includes "YYYYMMDD"; `TIME_ON` description includes "HHMM" — verify in Swagger field descriptions.
- [ ] **409 duplicate response:** `POST /api/qsos/` shows 409 in its Swagger responses section with a schema — verify in `/docs`.
- [ ] **503 health response:** `GET /health` shows 503 in its Swagger responses section — verify in `/docs`.
- [ ] **Soft-delete disclosure:** `DELETE /api/qsos/{qso_id}` description contains "soft" or "not physically removed" — verify in `/docs`.
- [ ] **Cookie-auth routes excluded:** `/log/*` and `/admin/ui/*` routes do not appear in Swagger (or are explicitly marked as browser-only in narrative docs) — verify by inspecting `/docs`.
- [ ] **ADIF export content-type:** `GET /api/adif/export` shows `text/plain` as response content type in Swagger, not `application/json` — verify in `/docs`.
- [ ] **curl examples exist:** Narrative docs contain at least one curl example for obtaining a token and one for making an authenticated request.
- [ ] **Token expiry documented:** Narrative docs mention that tokens expire and show how to re-authenticate.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| OpenAPI schema shows `{}` for QSO endpoints | LOW | Add `response_model` Pydantic classes or `openapi_extra` to route decorators; no runtime change |
| Cookie-auth confusion already in published docs | MEDIUM | Add a prominent "Auth Flows" table at the top of the API reference, mark UI routes as browser-only |
| Workflow docs stale after UI change | LOW | Update the specific steps that changed; use text descriptions not screenshots to minimize future churn |
| ADIF field formats not documented | LOW | Add `Field(description=...)` to request model fields; regenerates automatically in OpenAPI |
| Over-engineering (MkDocs pipeline added prematurely) | MEDIUM | Remove the pipeline, move content to Markdown files; the tooling removal is more work than the content migration |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Cookie vs Bearer confusion in OpenAPI | OpenAPI schema cleanup | Open `/docs`, confirm UI routes absent or marked browser-only; auth section has two distinct flows |
| QSO endpoints show `{}` response schema | OpenAPI schema cleanup | Every QSO endpoint in Swagger has a non-empty Schema tab |
| ADIF import/export schemas missing | OpenAPI schema cleanup | Import shows typed response; export shows `text/plain` not `application/json` |
| ADIF field names unexplained | OpenAPI schema cleanup + narrative docs | Every ADIF field has a `description` in Swagger; field reference exists in narrative docs |
| Duplicate detection (409 + force) undocumented | OpenAPI schema cleanup | `POST /api/qsos/` Swagger shows 409 with schema and `force` param has description |
| Soft-delete not disclosed | OpenAPI schema cleanup | DELETE endpoint description mentions soft-delete |
| JWT dual-auth under-documented | Narrative docs phase | Narrative contains "Bearer" and "cookie" in auth section; token expiry is stated |
| Workflow docs stale vs UI | Narrative docs phase (write last) | Walk through each documented workflow step against the live app before committing |
| Over-engineering documentation stack | Architecture decision (first) | No MkDocs/Sphinx config files in repo; docs are Markdown + FastAPI built-in Swagger |
| Health/whoami misplaced in Swagger | OpenAPI schema cleanup | `/health` is tagged and has 503 documented; `/api/whoami` is tagged or hidden |

---

## Sources

- FastAPI official security documentation: https://fastapi.tiangolo.com/tutorial/security/ and https://fastapi.tiangolo.com/reference/security/
- FastAPI additional responses in OpenAPI: https://fastapi.tiangolo.com/advanced/additional-responses/
- FastAPI response model documentation: https://fastapi.tiangolo.com/tutorial/response-model/
- FastAPI GitHub issue — securitySchemes description gap: https://github.com/fastapi/fastapi/issues/2840
- FastAPI GitHub issue — 422 OpenAPI schema customization: https://github.com/fastapi/fastapi/issues/3650
- FastAPI best practices (community): https://github.com/zhanymkanov/fastapi-best-practices
- Bearer auth in FastAPI Swagger UI: https://medium.com/@zyroneenergy/enabling-bearer-auth-instead-of-basic-auth-in-fast-apis-swagger-ui-9d15f754fdca
- ADIF specification (current): https://adif.org/adif/
- Swagger Bearer authentication spec: https://swagger.io/docs/specification/v3_0/authentication/bearer-authentication/
- Codebase: `app/auth/dependencies.py`, `app/qso/router.py`, `app/adif/router.py`, `app/main.py`, `app/qso/models.py` (direct inspection, HIGH confidence)

---
*Pitfalls research for: adding API documentation and operator documentation to ollog (FastAPI + HTMX + MongoDB ham radio logbook)*
*Researched: 2026-04-04*
