# Project Research Summary

**Project:** ollog — Named API Token Auth (v1.7)
**Domain:** API token authentication — REST X-API-Key + UDP ADIF APP_ field identity resolution
**Researched:** 2026-04-09
**Confidence:** HIGH (all four files grounded in direct codebase inspection and official docs)

---

## Executive Summary

ollog v1.7 adds named API tokens to a FastAPI + Beanie + MongoDB ham radio logging app that already has JWT Bearer (REST) and HTTP-only cookie (browser UI) auth. The core driver is overnight FT8 sessions: JWT tokens expire after 480 minutes with no automated refresh path in tools like N1MM+ or WSJT-X; named tokens with optional expiry (defaulting to never) solve this permanently. The feature has three interlocking parts that must ship together: a token management UI in the operator profile page, X-API-Key header validation on QSO REST endpoints, and APP_OLLOG_TOKEN field extraction from UDP ADIF datagrams to resolve operator identity per datagram.

The recommended implementation requires zero new libraries. FastAPI's built-in `APIKeyHeader`, Python's `secrets` and `hmac` stdlib modules, Beanie's Document class, and the existing `pymongo` index tooling cover all needs. The data model question (embed tokens in `User` vs. separate collection) and the hashing algorithm choice (Argon2 vs. HMAC-SHA256) are the two decisions that must be resolved before a single line of token code is written — both have clear right answers that differ from what one of the research agents recommended. The UDP path has an architectural constraint (startup-pinned operator) that the milestone goal partially conflicts with; the correct resolution is also documented below.

The main integration risk is the FastAPI `OAuth2PasswordBearer`/`APIKeyHeader` stacking behavior: `OAuth2PasswordBearer` with `auto_error=True` returns HTTP 403 (not 401) before an API key can be inspected. The combined auth dependency must use `auto_error=False` on both schemes. This is a documented FastAPI quirk (GitHub issues #2026 and #10177) with a known fix. All other pitfalls are either low-risk or have straightforward preventions at the schema or dependency layer.

---

## Key Findings

### Recommended Stack

No new dependencies are required. All capabilities are satisfied by the existing lock file.

**Core technologies:**

- `fastapi[standard] 0.135+`: `APIKeyHeader` in `fastapi.security`; `Depends`/`Security` injection — already installed
- `Python stdlib hmac + hashlib`: HMAC-SHA256 for token hashing — use this, NOT pwdlib Argon2 (see Decision 1)
- `Python stdlib secrets`: `secrets.token_urlsafe(32)` for token generation (256-bit entropy, URL-safe base64) — already available
- `beanie 2.1+`: `ApiToken` as a separate Beanie `Document` (see Decision 2) — already installed
- `pymongo 4.16+`: `IndexModel` for token prefix + user_id composite index — already installed
- `pwdlib[argon2] 0.3.0`: retained for password hashing only — do not use for token verification

`secrets.token_urlsafe(32)` is the canonical Python token generator. An `ollog_` prefix on every token makes tokens self-identifying in config files and enables secret-scanning tool detection (GitHub, GitLab scanners recognize the prefix). The full token string (38 chars including prefix) is what the operator copies; only the HMAC-SHA256 digest and the first 8 chars (prefix for lookup narrowing) are stored in MongoDB.

See `.planning/research/STACK.md` for full integration point mapping.

### Expected Features

**Must have — table stakes (v1.7):**
- Create token: required name (1-80 chars, alphanumeric + hyphen/underscore), optional expiry date defaulting to never
- Show token plaintext exactly once at creation with a copy button; "will not be shown again" warning required
- List tokens: name, created date, expiry or "Never", last 4 chars hint, last used date, Revoke action
- Revoke individual token: immediate effect; soft-delete (`enabled=False`) preferred to preserve audit trail
- `X-API-Key: ollog_<token>` accepted on all QSO REST endpoints alongside existing JWT Bearer
- `APP_OLLOG_TOKEN` ADIF field in UDP datagrams resolves operator identity per datagram; `UDP_OPERATOR` remains valid fallback
- Reject datagram with invalid `APP_OLLOG_TOKEN` present — do not silently fall through to `UDP_OPERATOR`
- Structured log tokens for UDP auth outcomes matching existing `disposition=accepted|rejected` convention

**Should have — differentiators:**
- `last_used_at` timestamp updated on every successful authentication (low cost, high audit value)
- `ollog_` token prefix for recognizability and secret scanning compatibility
- Token count limit of 20 per operator with a clear 422 error message
- 8-char plaintext prefix stored for lookup narrowing — avoids N-verify scan problem
- Inline copy button using `navigator.clipboard.writeText()` at creation
- Clipboard copy confirmation ("Token copied — this value is no longer shown") replacing the plaintext display

**Defer to v2+:**
- Token scopes/permissions — no meaningful read vs. write distinction in a single-operator logbook
- Admin token management across operators — disable operator account as current workaround for compromised tokens
- Token usage audit log — `last_used_at` covers 95% of the need; full log requires separate storage design
- Token rotation (regenerate same name, new secret) — revoke + create is equivalent for personal tokens

See `.planning/research/FEATURES.md` for full feature dependency graph and MVP checklist.

### Architecture Approach

The architecture adds one new Beanie Document (`ApiToken`), two new FastAPI dependency functions, one new token CRUD router, and extensions to the lifespan UDP startup block. No existing components are modified beyond additive opt-in. The QSO router opts individual routes into the new dependency; existing JWT-only routes are untouched.

**Major components:**

1. `app/auth/models.py` — `ApiToken` Beanie Document (separate collection); fields: `name`, `token_prefix` (8 chars, plaintext), `hashed_token` (HMAC-SHA256 digest), `user_id` (FK to `users._id`), `created_at`, `last_used_at`, `enabled`; composite index on `(token_prefix, user_id)`; registered in `app/database.py`
2. `app/auth/service.py` — add `generate_api_token()` and `token_prefix_from_plaintext()` pure helpers; add `hash_api_token()` and `verify_api_token()` using `hmac`/`hashlib`; existing `hash_password`/`verify_password` (Argon2) remain for password use only
3. `app/auth/dependencies.py` — add `get_current_user_api_key` and `get_current_operator_callsign_api_key`; add `get_operator_any_auth` union dependency (Bearer first, API key fallback) for routes accepting both
4. `app/auth/router.py` — add `POST /auth/tokens`, `GET /auth/tokens`, `DELETE /auth/tokens/{id}` (JWT auth only — operators manage tokens via browser)
5. `app/config.py` — add `api_token_secret: SecretStr` for HMAC key; separate from `SECRET_KEY` for independent rotation
6. `app/main.py` lifespan — load enabled `ApiToken` documents into in-memory cache at startup; extend UDP block to resolve `APP_OLLOG_TOKEN` from cache; `_handle_datagram` itself is unchanged

**Validated build order (from ARCHITECTURE.md):**
1. `ApiToken` model + DB registration (no other step works without this)
2. `generate_api_token()`, `token_prefix_from_plaintext()`, `hash_api_token()`, `verify_api_token()` helpers (pure, testable in isolation)
3. Token CRUD router (POST/GET/DELETE, testable end-to-end before touching auth deps)
4. `get_current_user_api_key` dependency
5. Opt-in on QSO REST routes
6. Config + lifespan cache + UDP block extension

Steps 1-3 can be delivered and smoke-tested before any existing endpoint is modified.

See `.planning/research/ARCHITECTURE.md` for full data flow diagrams and anti-pattern catalogue.

### Critical Pitfalls

1. **Wrong HTTP 403 on missing API key** — `OAuth2PasswordBearer(auto_error=True)` fires before `APIKeyHeader` can run and returns 403 (not 401). Prevention: `auto_error=False` on both schemes in the combined dependency; raise `HTTPException(401)` manually. Highest-integration-risk issue; existing tests must pass before and after the change.

2. **Argon2 used for token verification** — 200-500ms per verify added to every API-key request; event loop starvation under concurrent load. Prevention: use HMAC-SHA256 for tokens, Argon2 only for passwords. Recovery from this mistake requires re-issuing all tokens.

3. **Plaintext token stored in DB or logged** — accidental `plain_token` field on the model, or a debug `logger.info(token)` call, constitutes full credential exposure. Prevention: schema has no plaintext field; add a grep test asserting no token-format string appears in log output.

4. **CSRF on token create/revoke forms** — cookie-authenticated state-changing endpoints. Prevention: verify `SameSite=Lax` on the `access_token` cookie; use `DELETE` (not `POST`) for revocation — HTML forms cannot trigger DELETE.

5. **ADIF APP_ field name injection** — if a token label is used as part of a field name (`APP_OLLOG_{token_name}`), special chars produce invalid ADIF. Prevention: validate token names to alphanumeric + hyphen/underscore, max 32 chars at creation; if stamping source info use fixed field name `APP_OLLOG_SOURCE` with the label as the value.

See `.planning/research/PITFALLS.md` for full pitfall-to-phase mapping, recovery strategies, and a "Looks Done But Isn't" checklist.

---

## Decisions Required Before Planning

Three cross-file conflicts emerged from synthesis. Each has a clear recommended answer, but the decision must be recorded explicitly before phase plans are written.

---

### Decision 1 — TOKEN HASHING ALGORITHM (UNRESOLVED — DECIDE BEFORE PHASE 1)

**Conflict:**
STACK.md recommends reusing `pwdlib` Argon2 (`hash_password` / `verify_password`) for token hashing, arguing that API tokens are high-entropy secrets that must survive offline attacks if the DB leaks.

PITFALLS.md says do NOT use Argon2 for token hashing. Argon2 with recommended parameters takes 200-500ms per operation. Every X-API-Key request must verify a token — this adds 200-500ms to every such request and starves the asyncio event loop under concurrent load. Recovery from this mistake requires re-issuing all tokens (there is no migration path that does not break existing tokens).

**Recommended resolution: Use HMAC-SHA256, not Argon2, for API token storage and verification.**

Rationale: Argon2 is the right choice for passwords because passwords have low entropy and must be slow to crack offline. API tokens generated with `secrets.token_urlsafe(32)` have 256 bits of entropy — the brute-force search space is infeasible regardless of hash speed, so the intentional slowness of Argon2 provides zero additional security benefit. HMAC-SHA256 with a secret key (stored in `Settings.api_token_secret`, separate from `SECRET_KEY`) is constant-time via `hmac.compare_digest`, takes microseconds to verify, and is the appropriate algorithm for this use case. OWASP explicitly documents this distinction.

**Implementation pattern:**
```python
import hmac, hashlib

def hash_api_token(raw_token: str, secret: str) -> str:
    return hmac.new(secret.encode(), raw_token.encode(), hashlib.sha256).hexdigest()

def verify_api_token(raw_token: str, stored_hash: str, secret: str) -> bool:
    return hmac.compare_digest(hash_api_token(raw_token, secret), stored_hash)
```

The `password_hash.verify()` function from `app/auth/service.py` must NOT appear anywhere in token verification code. Add a grep assertion in tests.

---

### Decision 2 — API TOKEN DATA MODEL: EMBEDDED VS. SEPARATE COLLECTION (UNRESOLVED — DECIDE BEFORE PHASE 1)

**Conflict:**
STACK.md recommends embedding `ApiToken` as a `pydantic.BaseModel` list inside the `User` Document (`api_tokens: list[ApiToken] = []`). Rationale: Beanie supports this natively, tokens belong to a user, there are few per user, and no separate collection lookup is needed.

ARCHITECTURE.md recommends a separate `api_tokens` collection (`ApiToken` as a Beanie `Document` with a `user_id` FK). Rationale: embedding loads the full token list on every `User.find_one()` even on JWT-only requests; lookup by prefix requires MongoDB `$elemMatch`; revocation requires `$pull` with a nested filter; a unique index on an embedded array path is harder to reason about; all operations are simpler as top-level document ops.

**Recommended resolution: Use a separate `api_tokens` collection.**

Rationale: The existing auth path calls `User.find_one()` on every JWT-authenticated request. Embedding tokens in `User` causes the token list to be deserialized on every request even when tokens are completely irrelevant — cost grows with token count over time. A separate collection with a `user_id` index makes all token operations (list, lookup by prefix, revoke) straightforward. Top-level document revocation is `await token.set({ApiToken.enabled: False})` vs. a nested `$pull` on the User document. The ARCHITECTURE.md rationale is the stronger argument; the STACK.md "convenience" argument does not outweigh the performance and maintainability costs at this access pattern.

The `ApiToken` Beanie Document fields (from ARCHITECTURE.md, updated with Decision 1 hash choice):
- `name: str` — human-readable label (validated: alphanumeric + hyphen/underscore, 1-80 chars)
- `token_prefix: str` — first 8 chars of plaintext after `ollog_`; stored clear for lookup narrowing
- `hashed_token: str` — HMAC-SHA256 digest (not Argon2)
- `user_id: PydanticObjectId` — FK to `users._id`
- `created_at: datetime`
- `expires_at: Optional[datetime] = None`
- `last_used_at: Optional[datetime] = None`
- `enabled: bool = True`
- Indexes: `user_id` ascending; composite `(token_prefix, user_id)` ascending

---

### Decision 3 — UDP APP_OLLOG_TOKEN: STARTUP PIN VS. PER-DATAGRAM RESOLUTION (UNRESOLVED — DECIDE BEFORE PHASE 5)

**Conflict:**
ARCHITECTURE.md recommends resolving `APP_OLLOG_TOKEN` once at startup (in the lifespan block), exactly like `UDP_OPERATOR`. The resolved `(operator, user)` tuple is cached on `QSODatagramProtocol` for the process lifetime. Rationale: `_handle_datagram` is a hot path; per-datagram DB lookup + hash verify would add 100-200ms and introduce DB failure modes.

PITFALLS.md warns that the UDP path is startup-pinned by design and that adding any per-datagram token resolution breaks this architectural invariant. Pitfall 4 explicitly states the new feature should be REST-only and `_handle_datagram` should be left untouched.

The milestone goal (per FEATURES.md) requires `APP_OLLOG_TOKEN` to resolve operator identity per datagram — enabling multi-operator UDP setups where different operators' logging software sends datagrams on the same UDP listener session.

**The core tension:** Startup-pin satisfies only single-operator UDP, which `UDP_OPERATOR` already handles. The value of `APP_OLLOG_TOKEN` in datagrams is specifically for multi-operator scenarios where different datagrams within a session come from different operators. Startup-pin for `APP_OLLOG_TOKEN` delivers no new capability.

**Recommended resolution: Per-datagram in-memory cache lookup in `_handle_datagram`.**

This approach eliminates the DB round-trip concern while delivering the per-datagram capability:

1. At startup (lifespan), load all enabled `ApiToken` documents into an in-memory dict: `{token_prefix: [(hashed_token, user_id)]}`. Pass the cache reference into `QSODatagramProtocol.__init__` alongside `operator` and `user`.
2. In `_handle_datagram`, extract `record.get("APP_OLLOG_TOKEN")`. If present, compute its 8-char prefix, look up candidates in the in-memory dict, HMAC-verify against the stored digest (microseconds with HMAC-SHA256, per Decision 1), resolve `user_id` to a `User` object (cached separately at startup or fetched once on first use).
3. Priority: `APP_OLLOG_TOKEN` in datagram (valid) → datagram token user. `APP_OLLOG_TOKEN` in datagram (invalid) → reject, do not fall through. `APP_OLLOG_TOKEN` absent → fall through to startup-pinned `UDP_OPERATOR` user.
4. Cache invalidation: token create/revoke via browser triggers a cache refresh. For a self-hosted app with at most 20 tokens, a full reload on any token mutation is acceptable. A short TTL (60 seconds) is the fallback if the signal path is complex.

**Note:** The ARCHITECTURE.md lifespan code pattern (resolving `APP_OLLOG_TOKEN` env var at startup) is still useful for a single-operator operator who wants to configure their token via environment variable rather than per-datagram. This is a separate use case from the per-datagram field. Phase 5 planning must decide whether the env-var form is needed or whether the per-datagram ADIF field form alone is sufficient.

**Open design question for Phase 5 planning:** How does a token create/revoke HTTP request (ASGI app) notify the long-running `QSODatagramProtocol` (asyncio transport) to refresh its in-memory cache? Options include an `asyncio.Event`, a shared `asyncio.Lock`-protected dict reference, or TTL-based refresh. This is the only unresolved technical design question in the milestone.

---

## Implications for Roadmap

Based on research and the feature dependency graph from FEATURES.md, the natural phase structure is:

### Phase 1: Token Data Model and Service Layer

**Rationale:** Every subsequent phase depends on the `ApiToken` collection existing in MongoDB and Beanie knowing about it. This is the foundation with no dependencies of its own.

**Delivers:** `ApiToken` Beanie Document registered in `database.py`; `generate_api_token()`, `token_prefix_from_plaintext()`, `hash_api_token()`, `verify_api_token()` service helpers; `api_token_secret` in Settings; token name validation (charset + length) at Pydantic model level.

**Must have resolved:** Decision 1 (hashing algorithm) and Decision 2 (data model) before writing any code in this phase.

**Avoids pitfalls:** Plaintext in DB (P2) — schema has no plaintext field; ADIF token name injection (P5) — name validation enforced at model creation.

**Research flag:** Standard patterns. No deeper research needed. Beanie Document creation and HMAC stdlib usage are both well-documented.

---

### Phase 2: Token CRUD API (JWT-Authenticated)

**Rationale:** With the model in place, the full token lifecycle (create, list, delete) can be built and tested end-to-end before touching any existing auth paths. This is the safest possible build order.

**Delivers:** `POST /auth/tokens` (returns plaintext once), `GET /auth/tokens` (returns name + prefix + metadata, never hash), `DELETE /auth/tokens/{id}` — all behind existing JWT auth.

**Avoids pitfalls:** Token returned in wrong response field (P2 variant) — GET response schema must be covered by test; CSRF on revocation (P6) — `DELETE` verb, not `POST`.

**Research flag:** Standard patterns. FastAPI routing and Beanie CRUD are well-documented.

---

### Phase 3: Token Management UI (Profile Page)

**Rationale:** Operators need a way to create and manage tokens before any API clients can use them. The UI depends on Phase 2 endpoints.

**Delivers:** Token creation form in `/log/profile` (name input, optional expiry); show-once plaintext banner with copy button; token listing table (name, created, expires, last-used, 4-char hint, Revoke); HTMX-powered revoke (DELETE).

**Avoids pitfalls:** HTMX swap caching the token value (P2 variant) — `hx-swap="outerHTML"` replaces the creation form with a confirmation state after copy; CSRF on cookie-auth forms (P6) — verify `SameSite=Lax` on auth cookie before building forms; use `DELETE` for revocation.

**Research flag:** Shallow research recommended on HTMX one-time-display pattern — specifically, preventing the token plaintext from being re-renderable via browser back/forward or HTMX swap history. Not a blocker but the `hx-swap` strategy must be planned carefully.

---

### Phase 4: X-API-Key REST Authentication

**Rationale:** With tokens creatable and the service layer proven, the REST auth dependency can be added. This is the highest-integration-risk phase because it touches the existing dependency chain.

**Delivers:** `get_current_user_api_key` and `get_current_operator_callsign_api_key` in `app/auth/dependencies.py`; opt-in `Depends()` on QSO REST endpoints; `last_used_at` update on successful auth (background task or fire-and-forget to avoid latency); `get_operator_any_auth` union dep for routes accepting both JWT and API key.

**Avoids pitfalls:** Wrong 403 (P3, critical) — `auto_error=False` on both schemes; manual `HTTPException(401)` raise; prefix timing oracle (P7) — dummy-verify on not-found branch.

**Research flag:** Needs careful review of FastAPI dependency resolution order before writing the combined dependency. The `auto_error=False` pattern is documented but the two-scheme composition is non-trivial. A spike or targeted research session before planning Phase 4 is recommended.

---

### Phase 5: UDP APP_OLLOG_TOKEN Support

**Rationale:** UDP is the last piece. It depends on the token model (Phase 1) and the in-memory cache design (Decision 3). It does not depend on the REST auth phases (3-4) and can proceed in parallel once Phase 1 is complete — but the cache invalidation signal path design should be resolved before Phase 2 token CRUD is finalized, since token create/revoke must trigger cache refresh.

**Delivers:** In-memory token cache loaded at startup; per-datagram `APP_OLLOG_TOKEN` extraction and resolution in `_handle_datagram` (cache lookup, HMAC verify); `UDP_OPERATOR` preserved as fallback; invalid token present → reject (no silent fallthrough); structured log lines for UDP token auth outcomes (`auth=token|udp_operator`, `reason=invalid_token`); `/guide` UDP section updated with `nc` example showing `APP_OLLOG_TOKEN`.

**Avoids pitfalls:** UDP regression (P4) — `test_udp_pipeline.py` must pass unchanged post-deploy; per-datagram DB round trip (Decision 3) — use in-memory cache; startup invariant confusion — document explicitly in code that `_handle_datagram` uses cache, not DB.

**Research flag:** Needs a spike on asyncio shared state between ASGI app and UDP protocol (cache invalidation signal path). The ASGI app and the `asyncio.DatagramProtocol` run in the same event loop but are not in the same call stack. A shared `asyncio.Lock`-protected dict or an `asyncio.Event`-based reload signal are the candidate approaches. This is the one unresolved technical design question in the milestone.

---

### Phase Ordering Rationale

- Phases 1-2 are pure foundation work with zero regression risk to existing behavior. Always build first.
- Phase 3 (UI) and Phase 4 (REST auth) can proceed in parallel after Phase 2 is complete.
- Phase 5 (UDP) can begin design after Phase 1 but the cache invalidation signal path should be resolved before Phase 2 token CRUD is finalized (since CRUD endpoints must trigger cache refresh).
- The "Looks Done But Isn't" checklist in PITFALLS.md should be treated as a mandatory acceptance gate for Phase 4 and Phase 5.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new dependencies confirmed by direct codebase inspection; all APIs verified against official docs; hashing algorithm conflict resolved by OWASP guidance |
| Features | HIGH | Pattern validated against GitHub PAT, Stripe, GitLab, Cloudflare docs; ham radio ADIF convention confirmed from spec; APP_OLLOG_TOKEN per-datagram is novel but sound |
| Architecture | HIGH | Based on direct codebase read of all relevant files; separate-collection recommendation is well-reasoned; build order is validated |
| Pitfalls | HIGH | FastAPI 403 bug confirmed in official GitHub issues; HMAC vs. Argon2 guidance confirmed by OWASP; CSRF pattern well-established |

**Overall confidence: HIGH**

### Gaps to Address

- **Cache invalidation signal path (UDP):** How does a token create/revoke HTTP request notify the long-running `QSODatagramProtocol` to refresh its in-memory token cache? Candidate approaches: asyncio shared dict with `asyncio.Lock`, `asyncio.Event`-based reload signal, TTL-based refresh. Address with a spike before Phase 5 planning — or before Phase 2 if the Phase 2 token CRUD implementation needs to emit the refresh signal.

- **Combined auth dependency composition (REST):** The exact FastAPI dependency composition for routes that accept both JWT Bearer and X-API-Key needs a code spike before Phase 4 planning. The `auto_error=False` pattern is documented; the two-scheme fallback chain is not a simple copy-paste. Existing test suite must remain green throughout.

- **`APP_OLLOG_TOKEN` as env var vs. as ADIF datagram field:** The Architecture research conflated two use cases. Decide in Phase 5 planning: (a) only support per-datagram ADIF field, (b) support both ADIF field and env var as alternatives, or (c) env var only with startup-pin (delivers no new capability over UDP_OPERATOR). Recommendation is (a) or (b).

- **HTMX one-time display pattern (UI):** The specific `hx-swap` strategy to prevent the token plaintext from being re-renderable after creation (browser back/forward, HTMX history) needs to be designed in Phase 3 planning. Not a blocker but requires deliberate attention.

- **QSO endpoint enumeration for API key auth:** The exact set of QSO routes that should accept both JWT and API key (vs. JWT-only) must be enumerated in Phase 4 planning. FEATURES.md says "all QSO endpoints" but admin and profile routes should remain JWT-only (token management itself is JWT-only by design).

---

## Sources

### Primary (HIGH confidence)
- FastAPI Security Reference — `APIKeyHeader`, `auto_error`, import path: https://fastapi.tiangolo.com/reference/security/
- FastAPI GitHub issues #2026 and #10177 — `OAuth2PasswordBearer` returns 403 not 401 on missing header
- FastAPI GitHub discussions #9076, #9601 — multiple auth schemes composition
- OWASP Password Storage Cheat Sheet — HMAC for tokens, Argon2 for passwords: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- OWASP REST Security Cheat Sheet — token in header not URL: https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html
- ADIF 2.2.6 / 3.1.7 specification — `APP_{PROGRAMID}_{FIELDNAME}` field naming convention
- GitHub Personal Access Tokens documentation — creation flow, show-once, metadata display
- GitLab Token Management Guide — last-used metadata, token listing UI
- Atlassian: Track API token usage — last-used pattern
- Auth0 Token Best Practices — expiry, long-running sessions
- pwdlib 0.3.0 PyPI + guide — `hash()` / `verify()` signatures; Argon2 parameters
- Python stdlib docs — `secrets.token_urlsafe`, `secrets.compare_digest`, `hmac.new`, `hashlib.sha256`
- Beanie ODM documentation — `Document` class, `List[BaseModel]` embedding, `Settings` indexes
- Direct codebase inspection: `app/auth/models.py`, `app/auth/service.py`, `app/auth/dependencies.py`, `app/auth/router.py`, `app/udp/server.py`, `app/adif/parser.py`, `app/adif/serializer.py`, `app/config.py`, `app/main.py`, `app/database.py`, `app/qso/router.py`

### Secondary (MEDIUM confidence)
- QSL Buddy Bridge — analogous token-in-bridge-config pattern for ham radio UDP (not per-datagram; closest ham radio precedent)
- freeCodeCamp: Building Secure API Keys — prefix pattern, show-once, hashing
- seamapi/prefixed-api-key — prefix + short-token identification pattern
- X-API-Key header convention (Stoplight, AWS API Gateway, Google Cloud docs) — header over query param
- HMAC-SHA256 vs Argon2 for API tokens: https://mojoauth.com/compare-hashing-algorithms/hmac-sha256-vs-argon2

---

*Research completed: 2026-04-09*
*Ready for roadmap: yes*
