# Feature Research

**Domain:** Named API token auth for ham radio logging app (REST + UDP ADIF)
**Researched:** 2026-04-09
**Confidence:** HIGH (primary patterns verified against GitHub PAT docs, Stripe docs, Auth0 docs, ADIF spec; ham radio UDP precedent from QSL Buddy bridge + existing codebase)

---

## Context and Constraints

This research answers: what is the right feature set for v1.7 API Token Auth in ollog?

**What already exists (do not re-implement):**
- JWT Bearer token auth on all QSO REST API endpoints (`Authorization: Bearer <jwt>`)
- HTTP-only cookie auth for browser UI and SSE (`/feed/station`)
- `UDP_OPERATOR` env var that pins operator identity for all UDP datagrams (config-level, no per-datagram auth)
- Operator profile settings page at `/log/profile` (HTMX form, inline save)
- `pwdlib` Argon2 hashing already installed for password hashing

**What v1.7 adds:**
- Token CRUD UI in profile settings (create named token, list tokens, revoke token)
- `X-API-Key` header auth accepted as alternative to JWT Bearer on QSO REST endpoints
- `APP_OLLOG_TOKEN` ADIF field in UDP datagrams to carry token and resolve operator identity (replaces reliance on `UDP_OPERATOR` for multi-operator UDP)

**Long-running session requirement:**
FT8 digital mode operators run unattended overnight sessions (8+ hours). This is why `JWT_EXPIRE_MINUTES` was raised to 480. Named API tokens with optional expiry (defaulting to no expiry) are the right primitive for this use case: they never expire unless the operator sets an expiry or revokes them.

---

## Feature Landscape

### Category A: Token UI (Profile Settings)

Features surfaced in the browser at `/log/profile`.

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Create token with a required name | All major token systems (GitHub PAT, Stripe, Cloudflare, GitLab) require a descriptive name so operators can tell tokens apart. "Token for Log4OM" vs "Token for overnight FT8" is essential for a user managing 2+ tokens. | LOW | Single text input, 1–80 chars. Server validates uniqueness per operator. |
| Optional expiry date at creation | GitHub PAT, Azure DevOps PAT, Fastly all offer expiry. Operators running nightly automation need no-expiry tokens; security-conscious ones want time-limited tokens for one-off integrations. | LOW | Date picker (or "Never" default). Store as UTC datetime or null. Validate not in past. |
| Show token plaintext exactly once, immediately after creation | Universal security pattern: GitHub, Stripe, Cloudflare, GitLab all show the secret once. Storing hashed means the plaintext is unrecoverable. Operators must copy it on creation. | LOW | Render a dismissable banner with the full token value and a "Copy" button. Banner disappears on next page load or dismiss. Clear warning: "This will not be shown again." |
| List all tokens with metadata (name, created, expiry, last used) | GitHub PAT list shows name, creation date, expiry. GitLab shows last used date and last IPs. Atlassian tracks last used. Operators need to know which tokens are active to audit and clean up. | LOW | Table with columns: Name, Created, Expires (or "Never"), Last Used (or "Never"), Actions. |
| Masked display in token list | Token secret cannot be shown again after creation. Listing should show a non-sensitive identifier — either a short prefix/suffix hint (e.g., last 4 chars) or a prefix like `ollog_...xxxx`. This lets operators confirm "this is the token I gave to Log4OM." | LOW | Store and display only the last 4 chars of the raw token. Never store or display the full plaintext after creation. |
| Revoke individual token | All token systems support per-token revocation. Immediate effect. "If a token leaked, I can kill just that one." | LOW | "Revoke" button per row in the token list. HTMX inline confirm or a simple confirm dialog. Takes effect immediately (delete from DB). |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| "Last used" timestamp in token list | GitLab and Azure Databricks show last-used. Lets operators identify stale tokens for cleanup. "This token hasn't been used in 60 days — safe to revoke." Especially valuable for overnight automation users who need to confirm their automation is actually calling through. | LOW | Update a `last_used_at` field on every successful token authentication. Display in listing. |
| Inline copy button next to token on creation | Reduces friction at the critical moment. The operator is seeing the token for the only time. A clipboard copy button prevents fumbling with mouse selection on mobile or narrow windows. | LOW | `navigator.clipboard.writeText()` in a small `<script>` block. No dependency on HTMX. |
| Token count limit with clear error | GitHub allows many PATs; Stripe limits restricted keys. For a single-operator self-hosted app, 20 active tokens is a reasonable ceiling to prevent abuse (accidental loops creating tokens). | LOW | Check count in service layer before insert. Return 422 with human-readable message: "Token limit reached (20). Revoke unused tokens before creating new ones." |

#### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Scoped permissions per token (read/write/admin) | GitHub fine-grained PATs have per-resource permissions. Stripe restricted keys limit to specific resources. | In ollog, all API operations are already scoped to the operator's own data. There is no meaningful "read-only" vs "write" distinction within a single operator's logbook that would add security value. Adds UI complexity for zero practical benefit in this single-operator-per-token model. | Skip permissions entirely. All tokens have full access to the operator's own data, same as JWT Bearer. |
| Token rotation (regenerate same name, new secret) | GitHub offers token regeneration. Stripe has rotation with immediate replacement. | Rotation is valuable when a token is shared with infrastructure (you replace the value without changing references). Ollog tokens are personal, not infrastructure credentials. If a token leaks, revoke it and create a new one — same outcome with less UI complexity. | Revoke + create new token. No rotation UI needed. |
| Admin-level token management (admin can see/revoke any operator's tokens) | Admin can do everything else. | Tokens contain hashed secrets; admin cannot recover the plaintext. Admin revocation is a valid future need but adds cross-operator complexity to the service layer. The existing admin UI manages operator accounts, not credentials within accounts. | Defer to a future admin page. Operators self-manage their own tokens. If an operator's token is compromised, the admin disables the operator account instead. |
| Email notification on token expiry | "Alert me before my token expires." | Ollog has no email infrastructure. Adding SMTP config for expiry notifications is out of scope. | Operators check the token list; expiry date is visible. |
| Token usage logs / audit trail per token | "Show me every API call made with this token." | Full request audit logging is a separate feature with storage implications. Token-level tracking (`last_used_at`) covers the 95% case (is this token being used?). | `last_used_at` timestamp. |

---

### Category B: REST API Auth (X-API-Key Header)

Features affecting the QSO REST API endpoints.

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `X-API-Key: <token>` header accepted on all QSO endpoints | `X-API-Key` is the dominant convention (established by AWS API Gateway, used widely). Headers preferred over query params because URLs appear in logs and caches. Logging tools like Log4OM that call REST APIs need a stable long-lived credential that doesn't expire every 8 hours. | LOW | Middleware or FastAPI `Security()` dependency that checks for `X-API-Key` header, looks up token in DB, validates hash, returns operator. |
| X-API-Key and Bearer JWT both accepted (not mutually exclusive) | Different clients use different auth paths. The browser UI will always use JWT (cookie). External logging tools will use X-API-Key. Both must work on the same endpoints. | LOW | Auth dependency checks header order: `Authorization: Bearer` first, then `X-API-Key`. Falls through to 401 only if neither is present or both fail. |
| 401 with clear error when token not found or expired | Standard REST auth error response. Logging tools that hit 401 need to know why. | LOW | `{"detail": "Invalid or expired API token"}` — do not distinguish "not found" from "expired" (security: no oracle for token enumeration). |
| Token auth resolves operator identity (not just "valid/invalid") | The auth layer must return the operator callsign so the existing `get_current_operator()` dependency can be satisfied. QSO isolation is enforced per-operator at the data layer — this must work identically for token auth as for JWT. | LOW | Token lookup returns the `User` document. The FastAPI dependency returns the same `operator_callsign` string regardless of auth method. |
| Expired tokens rejected at auth time | If operator set an expiry date, tokens past that date must be rejected. | LOW | Check `expires_at` field during token lookup. If `expires_at is not None and expires_at < utcnow()` → 401. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Token prefix in the raw token value (e.g., `ollog_`) | GitHub uses `ghp_`, OpenAI uses `sk-`, Stripe uses `sk_live_`. A recognizable prefix enables secret scanning tools (GitHub, GitLab) to detect accidental commits. Also makes tokens self-identifying in pastebins/configs. | LOW | Prepend `ollog_` to the random token on generation. The full string (including prefix) is what the operator copies. The DB stores only the hash of the full string. |
| Token lookup by stored prefix (first 8 chars) | Without a lookup shortcut, every X-API-Key request must hash and compare against every token in the DB. With a stored prefix (non-secret first N chars), the lookup can WHERE-filter first then hash-compare. | LOW | Store `token_prefix` (first 8 chars of the raw token, plaintext) alongside the hash. Index on `(operator, token_prefix)`. Auth: extract prefix from header, find candidate rows, Argon2-verify against hash. For an operator with ≤20 tokens, a full scan is also acceptable — prefix is an optimization, not a requirement. |

#### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| API key in query param (`?api_key=...`) | "Simpler for curl testing." | Query params appear in server logs, browser history, nginx access logs, and are transmitted in the request line over cleartext. Logging tools (N1MM+, Log4OM) that include an API key in a URL would leak it. Header-only is the secure convention. | `X-API-Key` header only. Document `curl -H 'X-API-Key: ...'` in the guide. |
| Store token in plaintext for "admin recovery" | "What if the operator forgets it?" | Storing plaintext tokens defeats the purpose of hashing. If the DB leaks, all tokens are compromised. | Hash with Argon2 (same as passwords). Show once at creation. Operator revokes and re-creates if lost. |
| JWT-style expiry enforcement (check exp claim) | Tokens already have an `expires_at` field. | Tokens are not JWTs. There is no claim to check. The `expires_at` DB field is the source of truth. | DB-field expiry check on every token lookup. |

---

### Category C: UDP ADIF Auth (APP_OLLOG_TOKEN field)

Features for the UDP datagram path (`app/udp/server.py`).

#### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `APP_OLLOG_TOKEN` field in ADIF datagram resolves operator identity | ADIF `APP_` prefix convention (ADIF 3.1.x spec §Application-defined Fields) allows any application to embed custom fields as `APP_{PROGRAMID}_{FIELDNAME}`. `APP_OLLOG_TOKEN` follows this convention. QSL Buddy uses a similar pattern (paste API token into bridge app config). Operators using multi-operator UDP setups need per-datagram identity. | MEDIUM | Parse `APP_OLLOG_TOKEN` value from datagram ADIF after existing `parse_adi()` call. Look up token in DB (same path as REST auth). If found and valid, resolve operator. |
| `UDP_OPERATOR` remains valid fallback | Existing single-operator deployments use `UDP_OPERATOR` env var. This must not break. The majority of deployments sending WSJT-X or Log4OM UDP are single-operator and do not need per-datagram auth. | LOW | Priority: `APP_OLLOG_TOKEN` in datagram (if present and valid) overrides `UDP_OPERATOR`. If `APP_OLLOG_TOKEN` absent, fall back to `UDP_OPERATOR`. If both absent, reject with log. |
| Reject datagram if `APP_OLLOG_TOKEN` present but invalid | If the operator included a token field but it's wrong (typo, revoked, expired), the datagram should be rejected with a diagnostic log, not silently logged under `UDP_OPERATOR`. Silent fallback would mask misconfiguration. | LOW | If `APP_OLLOG_TOKEN` is present in the datagram: validate it. If invalid → `disposition=rejected reason=invalid_token`. Do not fall through to `UDP_OPERATOR`. |
| Structured log token for UDP token auth outcomes | The existing UDP server already logs `disposition=accepted|rejected|duplicate` with `src=IP:PORT call=CALLSIGN`. Token auth outcomes must follow the same structured logging convention for grep-ability. | LOW | Add `auth=token` or `auth=udp_operator` to existing structured log line. Add `reason=invalid_token` when token lookup fails. |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `APP_OLLOG_TOKEN` documented in Log4OM + nc examples in guide | Operators will not know this field exists unless it's in the docs. A `nc` one-liner showing `APP_OLLOG_TOKEN` alongside the other ADIF fields is the fastest path to adoption. Log4OM is the only logging tool that supports direct ADIF UDP output today (per existing docs). | LOW | Documentation work: update `/guide` UDP section. No code change. |
| Token cached at startup for UDP path (same as operator User doc) | The REST API path does DB lookups per request. UDP datagrams arrive in bursts during FT8 (every 15 seconds). Caching the token→operator mapping at startup avoids per-datagram DB round trips. | MEDIUM | Cache a dict `{token_hash_prefix: (token_doc, user_doc)}` at startup alongside the existing `UDP_OPERATOR` cache. Token creation/revocation requires a cache invalidation signal (or TTL-based refresh). For a single-operator deployment with 1–2 tokens, startup cache is sufficient. |

#### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Multiple operators per UDP datagram | "What if two operators are using the same software instance?" | ADIF format carries one QSO per record. Operator identity is per-datagram. One datagram = one QSO = one operator. Multi-operator UDP would require multiplexing at the sending software level. | `APP_OLLOG_TOKEN` per datagram. Each operator configures their software with their own token. |
| Plain-text token in APP_OLLOG_TOKEN without HTTPS | "UDP is local network only." | Plain-text tokens in UDP datagrams are readable by any process on the same host or VLAN. If `UDP_BIND_HOST=0.0.0.0` is set (LAN mode), adjacent hosts can sniff datagrams. | Document the risk. Recommend `UDP_BIND_HOST=127.0.0.1` (default) for single-machine setups. Accept the limitation: UDP has no encryption primitive; this is a known ham radio logging ecosystem constraint. |
| JWT in APP_OLLOG_TOKEN | "Reuse the existing JWT system." | JWTs expire (even at 480 min). An overnight FT8 session would silently fail when the JWT expires at 3 AM. The explicit rationale for named tokens (from PROJECT.md) is that JWTs with no UDP refresh path are unsuitable. | Named API tokens with no expiry (or long expiry). This is the core reason v1.7 exists. |

---

## Feature Dependencies

```
Token storage model (new)
    requires: Beanie Document model `APIToken` with fields:
              name, operator_callsign, token_prefix (8 chars, plaintext),
              token_hash (Argon2), created_at, expires_at (nullable),
              last_used_at (nullable), is_active
    required by: ALL other features in this milestone

Token creation service (new)
    requires: Token storage model
    requires: pwdlib Argon2 (already installed)
    required by: Token creation UI, X-API-Key auth, UDP token auth

Token creation UI (new)
    requires: Token creation service
    requires: existing /log/profile HTMX page (add a new section below existing form)
    required by: operators obtaining tokens for REST and UDP use

Token listing UI (new)
    requires: Token storage model (read)
    required by: operators auditing active tokens

Token revocation UI (new)
    requires: Token storage model (delete/deactivate)
    required by: operators cleaning up after credential leak or tool decommission

X-API-Key auth dependency (new FastAPI Security dependency)
    requires: Token creation service (same lookup/hash path)
    required by: all QSO REST endpoints accepting X-API-Key

last_used_at update on auth (new)
    requires: X-API-Key auth dependency
    required by: "last used" display in token listing UI

APP_OLLOG_TOKEN UDP auth (new)
    requires: Token creation service (same lookup/hash path)
    requires: APP_OLLOG_TOKEN parsed by existing parse_adi() (ADIF APP_ fields are standard)
    required by: multi-operator UDP datagram identity resolution
```

### Dependency Notes

- **`APP_` fields and `parse_adi()`:** The existing custom ADIF parser must already handle or be extended to handle `APP_`-prefixed fields. ADIF `APP_` fields follow the same `<FIELDNAME:LENGTH>VALUE` format as standard fields. If `parse_adi()` returns `model_extra` passthrough, `APP_OLLOG_TOKEN` will be in the parsed dict. Verify before assuming — this is a LOW complexity change if needed.

- **Token hash verification cost:** Argon2 is intentionally slow (~50–200ms per verify). For the REST API this is acceptable (one verify per request). For UDP, burst datagrams (FT8 every 15s) would amplify this cost. The startup-cache differentiator (cache token→operator at startup) mitigates this.

- **`UDP_OPERATOR` fallback order:** The priority chain must be explicit in the code comment: `APP_OLLOG_TOKEN present → validate token → use resolved operator | APP_OLLOG_TOKEN absent → use UDP_OPERATOR | UDP_OPERATOR also absent → reject`.

---

## MVP Definition

### Launch With (v1.7)

All three categories are required together. They do not make sense in isolation.

- [ ] **Token storage:** `APIToken` Beanie model with all required fields
- [ ] **Token creation:** service function generates `ollog_` prefixed token, hashes it, stores prefix + hash
- [ ] **Token creation UI:** form in `/log/profile` with name input, optional expiry, show-once plaintext banner
- [ ] **Token listing UI:** table showing name, created, expires, last used, last 4 chars hint, Revoke button
- [ ] **Token revocation:** HTMX inline action, immediate effect
- [ ] **X-API-Key auth:** FastAPI dependency that validates header and resolves operator, accepted on all QSO endpoints
- [ ] **APP_OLLOG_TOKEN UDP:** parse field from datagram, resolve operator, fallback to UDP_OPERATOR

### Add After Validation (v1.x)

- [ ] **Token prefix lookup optimization:** If `≤20` tokens per operator is enforced, full-scan + Argon2 verify is acceptable at launch. Add prefix-based pre-filtering if profiling shows latency under burst UDP load.
- [ ] **UDP token startup cache:** Low priority if single-operator deployments are the norm. Add if profiling shows Argon2 verify cost during FT8 burst is noticeable.
- [ ] **APP_OLLOG_TOKEN in guide:** Document in UDP setup section. `nc` one-liner example with `APP_OLLOG_TOKEN` field. This should ship with v1.7 but is not a code-change blocker.

### Future Consideration (v2+)

- [ ] **Admin token management page:** Admin views/revokes tokens across all operators. Requires cross-operator service layer changes.
- [ ] **Token usage audit log:** Full request log per token. Requires separate storage and retention policy.
- [ ] **Token scopes/permissions:** Only meaningful if ollog adds multi-resource APIs where read vs write matters.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Token creation UI (name + optional expiry) | HIGH | LOW | P1 |
| Show token once at creation | HIGH | LOW | P1 |
| Token listing (name, dates, last 4, last used) | HIGH | LOW | P1 |
| Token revocation | HIGH | LOW | P1 |
| X-API-Key header auth on QSO endpoints | HIGH | LOW | P1 |
| APP_OLLOG_TOKEN UDP identity resolution | HIGH | MEDIUM | P1 |
| UDP_OPERATOR fallback preserved | HIGH | LOW | P1 |
| Inline copy button at creation | MEDIUM | LOW | P2 |
| `ollog_` token prefix | MEDIUM | LOW | P2 |
| Token count limit (20) | LOW | LOW | P2 |
| last_used_at update on auth | MEDIUM | LOW | P2 |
| Structured log token for UDP token auth | MEDIUM | LOW | P2 |
| UDP token startup cache | LOW | MEDIUM | P3 |
| Admin token management | LOW | HIGH | P3 |
| Token scopes | LOW | HIGH | P3 |

---

## Answering the Specific Research Questions

### 1. Token creation UI — what is table stakes?

**Required at launch:** Name (required, descriptive), optional expiry (date picker with "Never" default), one-time plaintext reveal with copy affordance. The GitHub PAT flow is the canonical reference: name → expiry → permissions (skip for ollog) → create → copy.

**Confidence: HIGH** — GitHub Docs, Stripe Docs, Cloudflare Docs all converge on the same pattern.

### 2. Token listing — what metadata to show?

**Required:** Name, created date, expiry (or "Never"), masked value (last 4 chars), Revoke action.
**Recommended differentiator:** Last used timestamp.

GitLab shows last-used and last IPs. Azure Databricks shows last-used date. For an operator managing 3 tokens and wondering "which one is my overnight FT8 token?", last-used is the answer.

**Confidence: HIGH** — GitLab docs, Atlassian support docs, Azure Databricks docs confirm this pattern.

### 3. Token revocation — what behavior?

**Required:** Immediate revocation. Existing requests in-flight complete (HTTP is stateless; once the request passes auth middleware the token is valid for that request). No revocation grace period needed. Revoke = delete from DB or set `is_active=False`. Recommend soft-delete (`is_active=False`) to preserve `last_used_at` history.

**Confidence: HIGH** — universal industry behavior; Stripe, GitHub, Cloudflare all do immediate revocation.

### 4. X-API-Key header convention — is it standard?

Yes. `X-API-Key` is the dominant custom-header convention for API key auth, established by AWS API Gateway and widely adopted. Headers are preferred over query params because headers do not appear in URLs (which leak via logs, browser history, nginx access logs). The `X-` prefix technically marks it as non-standard per RFC 6648 (deprecated custom prefix), but `X-API-Key` is so widely recognized that using any other name would create friction for logging tools that have hardcoded header names.

**Confidence: HIGH** — Stoplight blog, Google Cloud docs, AWS docs, multiple API security guides converge.

### 5. Embedding auth in ADIF custom fields — what is the convention?

`APP_{PROGRAMID}_{FIELDNAME}` is the ADIF-standard way to add application-specific fields. Syntax: `<APP_OLLOG_TOKEN:LENGTH>value`. The ADIF spec (confirmed at adif.org, version 2.2.6+) states that application-defined fields must include the program name to avoid collisions. `APP_OLLOG_TOKEN` follows this convention exactly.

No other ham radio logging software was found to implement per-datagram token auth via `APP_` fields. This is a novel application of a standard mechanism. QSL Buddy's "Bridge" app uses a similar concept (API token pasted into the bridge config), but not embedded in the datagram. The ollog approach is more flexible for multi-operator setups.

**Confidence: MEDIUM** — ADIF `APP_` syntax is HIGH confidence from spec. The specific `APP_OLLOG_TOKEN` pattern is novel (no precedent found in other ham radio software); the decision to use it is sound engineering but not industry precedent.

### 6. Long-running session considerations

Named API tokens with no expiry are the right primitive for overnight FT8 sessions. OAuth refresh token patterns (short-lived access + refresh) add complexity without benefit here: there is no user session to refresh, no browser to prompt, and no back-channel refresh call in logging software like WSJT-X. A token that works for 8 hours unattended = a token that either never expires or expires at a long horizon the operator controls. The existing `UDP_OPERATOR` decision (PROJECT.md Key Decisions) documents this reasoning explicitly.

**Confidence: HIGH** — corroborated by Auth0 token best practices docs, Apigee antipattern docs, and the existing project decision rationale.

---

## Sources

- [GitHub Personal Access Tokens documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) — creation flow, show-once, metadata display (HIGH confidence)
- [Stripe API Keys best practices](https://docs.stripe.com/keys-best-practices) — restricted keys, rotation, revocation patterns (HIGH confidence)
- [Cloudflare: Create API Token](https://developers.cloudflare.com/fundamentals/api/get-started/create-token/) — show-once pattern (HIGH confidence)
- [ADIF Specification 2.2.6](https://www.adif.org/adif226.htm) — APP_{PROGRAMID}_{FIELDNAME} syntax (HIGH confidence)
- [X-API-Key header convention — Stoplight](https://blog.stoplight.io/api-keys-best-practices-to-authenticate-apis) — header over query param (MEDIUM confidence, corroborated by AWS/Google docs)
- [GitLab Token Management Guide](https://about.gitlab.com/blog/the-ultimate-guide-to-token-management-at-gitlab/) — last-used metadata, token listing UI (HIGH confidence)
- [Atlassian: Track API token usage](https://support.atlassian.com/organization-administration/docs/track-user-api-token-usage-in-your-organization/) — last-used pattern (HIGH confidence)
- [Auth0 Token Best Practices](https://auth0.com/docs/secure/tokens/token-best-practices) — expiry, long-running sessions (HIGH confidence)
- [freeCodeCamp: Building Secure API Keys](https://www.freecodecamp.org/news/best-practices-for-building-api-keys-97c26eabfea9/) — prefix pattern, show-once, hashing (MEDIUM confidence)
- [seamapi/prefixed-api-key GitHub](https://github.com/seamapi/prefixed-api-key) — prefix + short-token identification pattern (MEDIUM confidence)
- [QSL Buddy Bridge (API token in UDP bridge app)](https://www.qslbuddy.com/features) — closest ham radio precedent for token-based UDP bridge auth (MEDIUM confidence; pattern analogous, not identical)
- ollog `PROJECT.md` Key Decisions — `UDP_OPERATOR` rationale, overnight FT8 session requirement (HIGH confidence, first-party)

---

*Feature research for: ollog v1.7 — Named API Token Auth (token UI, X-API-Key REST, APP_OLLOG_TOKEN UDP)*
*Researched: 2026-04-09*

---
---

# Feature & UX Research: ollog v1.8

**Domain:** Ham radio logging — FastAPI + Beanie (MongoDB) + HTMX
**Researched:** 2026-04-10
**Scope:** Admin container isolation, database backup UX, docs rewrite
**Overall confidence:** HIGH (codebase inspected directly; standard patterns verified)

---

## Summary

Three feature areas are in scope for v1.8. The patterns for each are well-established. The
admin isolation is a Docker Compose service split, not a code rewrite — the existing
`app/admin/` routers already exist and only need a separate entry-point file and
compose service. The backup UX maps directly to the `lifespan + asyncio.create_task`
pattern already used in `app/main.py` for the change-stream watcher. The docs rewrite
is a nav structure problem: the current flat seven-item MkDocs nav should become a
section-grouped structure using `navigation.tabs` and `navigation.sections`.

Key decisions to make early:

1. S3 failure strategy: log-and-continue with one boto3 retry (standard) — do not abort the backup process.
2. Admin `/health`: each container must expose its own `/health` — Docker Compose depends_on needs a health check on the container it is waiting for.
3. API docs in MkDocs: manual hand-authored markdown is the correct choice given the small, stable endpoint surface and the need to embed usage examples.

---

## Section 1: Admin Container Isolation

### Architecture decision: two separate Docker services, not one container with two Uvicorn processes

The correct design is two Docker Compose services, each running a single Uvicorn
process on its own port. Running two Uvicorn instances in one container with `&` to
background one (`uvicorn admin:app & uvicorn main:app`) is fragile — process
supervision is lost, a crash in one silently leaves the other running, and Docker
health checks can only target one port per container.

The existing codebase already has `app/admin/router.py` (API) and
`app/admin/ui_router.py` (HTMX). The split requires:

1. A new `app/admin_main.py` entry point that includes only the admin routers and
   `app/auth/router.py` (the `/auth` login endpoint). It does NOT include `qso/`,
   `profile/`, `feed/`, `adif/`, `tokens/` routers.
2. The existing `app/main.py` (operator app) drops `admin_router` and `ui_router`
   includes when the admin container is active. Controlled with an env var
   (`ADMIN_CONTAINER=true`) or by making a second Dockerfile target.
3. `docker-compose.yml` gains an `admin` service: same image (same codebase), different
   `command:` override (`uvicorn app.admin_main:app --host 0.0.0.0 --port 8001`),
   different port mapping (`8001:8001`).

### Health check: each container must have its own `/health`

Docker Compose `depends_on: condition: service_healthy` requires the healthcheck to
run inside the container being waited on — it cannot probe a different container's
port. Therefore:

- The operator app (`app/main.py`) keeps its existing `GET /health` on port 8000.
  This health check is already present and pings MongoDB.
- The admin app (`app/admin_main.py`) must also expose a `GET /health` endpoint on
  port 8001. It shares the same MongoDB connection so the health check body is
  identical. It cannot reuse the operator container's `/health`.

The admin health endpoint can live directly in `admin_main.py` rather than in a
router — it is an operational endpoint, not part of the admin feature surface.

**Confidence:** HIGH. The existing `app/main.py` health check and the Docker Compose
`service_healthy` pattern are both directly inspectable in the codebase and official
Docker Compose docs.

### Docker Compose service pattern

```yaml
services:
  mongodb:
    # unchanged

  api:
    build: .
    ports:
      - "8000:8000"
      - "2399:2399/udp"
    depends_on:
      mongodb:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s
    env_file: .env

  admin:
    build: .
    command: ["uvicorn", "app.admin_main:app", "--host", "0.0.0.0", "--port", "8001"]
    ports:
      - "8001:8001"
    depends_on:
      mongodb:
        condition: service_healthy
      api:
        condition: service_healthy   # optional — ensures operator app is up first
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s
    env_file: .env
```

`start_period` matters: Beanie's `init_beanie()` and the MongoDB replica set handshake
take a few seconds, so failures during that window should not count toward health check
retries. 15 seconds is conservative and safe given the existing MongoDB healthcheck in
the project already uses `start_period: 0s` with 30 retries.

`curl` must be present in the Docker image. If the Dockerfile does not install it,
add `RUN apt-get install -y --no-install-recommends curl` or use a Python script
health probe (`CMD python -c "import urllib.request; urllib.request.urlopen(...)"`)
which requires no additional package.

### Operator app: conditional admin route inclusion

**Recommended approach — Strategy B (separate entry point, no shared flag):**

`app/main.py` never includes admin routers. A standalone `app/admin_main.py` includes
only admin + auth routers. The two containers are genuinely independent. No env var
flag is required; there is no risk of accidentally exposing admin routes on the
operator container.

**Backward compatibility for single-container deployments:**

Operators who do not run the admin container will need to either use `app/main.py`
with admin routes re-included, or accept that admin routes are only available on
port 8001. The cleanest backward-compatible option is to provide a Strategy A
fallback: `app/main.py` includes admin routes unless `ADMIN_CONTAINER=true`.

This avoids breaking single-container deployments. Document the migration path in
the deployment guide.

---

## Section 2: Database Backup UX

### 2a. Environment variable naming conventions (S3 + schedule)

**Standard AWS SDK vars — use these, do not invent alternatives:**

| Variable | Purpose | Notes |
|----------|---------|-------|
| `AWS_ACCESS_KEY_ID` | AWS IAM key ID | Standard boto3/AWS SDK env var, auto-detected by boto3 without any configuration |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret | Standard boto3/AWS SDK env var, auto-detected |
| `AWS_DEFAULT_REGION` | S3 bucket region | Canonical name (`AWS_REGION` also works but `AWS_DEFAULT_REGION` is official) |
| `S3_BUCKET` | Target bucket name | Not an AWS standard — project-specific. `S3_BUCKET` is the most common convention in open-source backup scripts (mongodump-s3 PyPI, halvves/mongodb-backup-s3, slim-mongodump-s3, etc.) |
| `S3_PREFIX` | Object key prefix | Optional, e.g. `ollog/backups/`. `S3_PREFIX` is the standard project-level name across multiple implementations |
| `BACKUP_SCHEDULE` | Cron expression | Project-specific; `"0 2 * * *"` style string |

`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are picked up automatically by boto3's
credential chain without explicit configuration. Do not add them to pydantic `Settings`
— boto3 handles them directly, and adding them to Settings requires `SecretStr`
handling and complicates `.env` files without benefit.

**Confidence:** HIGH for `AWS_*` vars (boto3 official docs). MEDIUM for `S3_BUCKET`
and `S3_PREFIX` (de-facto convention from multiple implementations, not an AWS
standard).

### 2b. Python in-process cron pattern for FastAPI lifespan

The project already uses the correct pattern in `app/main.py`:

```python
watcher_task = asyncio.create_task(
    watch_qsos(collection, feed_manager, _templates)
)
```

The scheduled backup follows the same structure.

**Option A: asyncio while-True with croniter (no heavy dependency) — RECOMMENDED**

```python
import asyncio
from datetime import datetime, timezone
import croniter as croniter_lib

async def run_backup_loop(cron_expr: str):
    it = croniter_lib.croniter(cron_expr, datetime.now(tz=timezone.utc))
    while True:
        next_run = it.get_next(datetime)
        delay = (next_run - datetime.now(tz=timezone.utc)).total_seconds()
        await asyncio.sleep(max(delay, 0))
        await run_backup()
```

`croniter` is a lightweight, pure-Python cron expression parser (no C extension, well
maintained, widely used). The `while True` task is started with `asyncio.create_task()`
in lifespan and cancelled on shutdown — identical to the `watcher_task` pattern already
in `app/main.py`.

**Option B: APScheduler 3.x AsyncIOScheduler**

APScheduler's `AsyncIOScheduler` with `CronTrigger` is the other common option and
handles DST transitions and missed-fire policies. For a single backup job it is
over-engineered. APScheduler 4.x (async-first rewrite) exists but has a different API
and significantly less community documentation as of early 2026. Avoid APScheduler 4.x
for now.

**Recommendation: Option A.** The project already uses the lifespan + asyncio pattern.
`croniter` is a focused addition. APScheduler is appropriate if scheduling needs expand
beyond a single backup job in a future milestone.

Lifespan integration in `app/admin_main.py` (or `app/main.py` if admin container is not separate):

```python
backup_task = None
if settings.backup_schedule and settings.s3_bucket:
    from app.backup.scheduler import run_backup_loop
    backup_task = asyncio.create_task(run_backup_loop(settings.backup_schedule))

yield

if backup_task is not None:
    backup_task.cancel()
    try:
        await backup_task
    except asyncio.CancelledError:
        pass
```

**Where the backup task runs:**

The backup job belongs in the admin container. The admin container owns operational
tasks. The operator container serves users. Keeping the backup task in the admin
lifespan means the operator container is unaffected if backup configuration is absent
or an S3 upload is slow.

If the admin container is not deployed, the CLI path (`python -m app.backup`) and
host cron are sufficient.

**Confidence:** HIGH for the lifespan + asyncio pattern (directly inspectable in
`app/main.py`). MEDIUM for `croniter` recommendation (widely used, not in FastAPI
official docs).

### 2c. S3 upload failure strategy

**Recommendation: one set of boto3 retries (3 attempts), then log ERROR and continue. Do not abort.**

Rationale:
- The local backup file already exists on disk. The `mongodump` step succeeded.
- The scheduled job must not raise an exception that kills the asyncio task and makes
  the container appear unhealthy.
- boto3's `standard` retry mode already retries transient S3 errors (throttling,
  5xx responses) with exponential backoff up to `max_attempts` total calls. Setting
  `max_attempts=3` and `mode="standard"` in a `botocore.config.Config` object covers
  transient failures without manual retry logic.
- After boto3 retries are exhausted, log at `ERROR` level with the exception message
  and continue. The next scheduled run will attempt upload again.
- Do NOT delete the local backup file if the S3 upload fails. Retain it for manual
  recovery.

```python
import boto3
from botocore.config import Config
import logging

logger = logging.getLogger(__name__)

def upload_to_s3(local_path: str, bucket: str, key: str) -> bool:
    """Upload a backup file to S3. Returns True on success, False on failure."""
    config = Config(retries={"max_attempts": 3, "mode": "standard"})
    s3 = boto3.client("s3", config=config)
    try:
        s3.upload_file(local_path, bucket, key)
        logger.info("Backup uploaded to s3://%s/%s", bucket, key)
        return True
    except Exception as exc:
        logger.error("S3 upload failed for %s: %s", local_path, exc)
        return False
```

The caller checks the return value for logging but does not re-raise. The local file
is retained regardless.

**Exit code for `python -m app.backup`:**
- Exit `0` if `mongodump` succeeded (even if S3 upload failed — the backup exists).
- Exit `1` only if `mongodump` itself failed (no backup created).

This makes the CLI safe to call from host cron without false alarms on transient S3
failures.

**Confidence:** HIGH for the boto3 retry approach (official boto3 docs). MEDIUM for
the log-and-continue strategy (community best practice, no official backup-specific
guidance found).

### 2d. Should backup be triggerable from the admin UI?

**Yes in principle, but defer to a follow-on plan item. CLI path is sufficient for v1.8.**

A "Run backup now" button in the admin UI is valuable (pre-migration safety net,
manual testing). Implementation in HTMX is straightforward: `POST /admin/backup/run`
returns an HTMX partial with result (filename, size, upload status).

The admin UI currently has no backup section, and building the UI adds scope. The
`python -m app.backup` CLI path satisfies v1.8. Flag the admin UI trigger as a
follow-on feature for a future milestone.

### 2e. Backup CLI UX

**Expected output:**

```
$ python -m app.backup
2026-04-10 02:00:01 [INFO] Starting backup: ollog database
2026-04-10 02:00:04 [INFO] mongodump complete: ./backups/2026-04-10T020001.gz (14.2 MB)
2026-04-10 02:00:06 [INFO] Backup uploaded to s3://my-bucket/ollog/2026-04-10T020001.gz
```

On S3 failure:

```
2026-04-10 02:00:06 [ERROR] S3 upload failed: ConnectionError — backup retained locally at ./backups/2026-04-10T020001.gz
```

On `mongodump` failure:

```
2026-04-10 02:00:02 [ERROR] mongodump failed: ... (exit code 1)
```

Exit 1 in this case.

### 2f. Settings additions to `app/config.py`

```python
# Backup (v1.8)
backup_schedule: str | None = None      # BACKUP_SCHEDULE cron expression "0 2 * * *"
s3_bucket: str | None = None            # S3_BUCKET
s3_prefix: str = "ollog/"              # S3_PREFIX (default key prefix)
# Do NOT add AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY to Settings.
# boto3's credential chain reads AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
# and AWS_DEFAULT_REGION from the environment automatically.
```

---

## Section 3: MkDocs Docs Rewrite

### 3a. Nav structure for the target sections

**Current nav (flat, 7 items):**

```yaml
nav:
  - Home: index.md
  - Deployment: deployment.md
  - Getting Started: getting-started.md
  - Admin Guide: admin-guide.md
  - API Reference: api-reference.md
  - ADIF Field Reference: adif-field-reference.md
  - Troubleshooting: troubleshooting.md
```

**Recommended nav for v1.8 (section-grouped, 2-level depth):**

```yaml
nav:
  - Home: index.md
  - Getting Started:
    - Install & First QSO: getting-started.md
    - Deployment: deployment.md
  - Admin Guide:
    - Managing Operators: admin-guide.md
    - API Tokens: admin-tokens.md
    - Backup: admin-backup.md
  - Operator Guide:
    - UDP Interface: udp.md
  - API Reference:
    - All Endpoints: api-reference.md
    - Token API: api-tokens.md
  - Reference:
    - ADIF Field Reference: adif-field-reference.md
  - Troubleshooting: troubleshooting.md
```

Keep section depth at two levels. Three levels is hard to navigate in the sidebar.
MkDocs Material warns against over-nesting in its own docs.

**Theme features to enable in `mkdocs.yml`:**

```yaml
theme:
  name: material
  palette:
    scheme: slate
    primary: indigo
  features:
    - navigation.sections    # render section titles as groups in sidebar
    - navigation.tabs        # top-level sections become header tabs
    - navigation.top         # back-to-top button
    - navigation.footer      # prev/next page links at page bottom
```

`navigation.tabs`: when enabled, top-level nav sections (`Getting Started`, `Admin
Guide`, etc.) appear as tabs in the header. Works well when there are 4+ top-level
sections and the docs are the primary reference interface. For ollog served at `/guide`,
tabs add visual clarity and make the admin/operator divide obvious.

`navigation.sections` + `navigation.tabs` together: top-level sections become header
tabs; sub-sections become expandable groups in the left sidebar. This is the standard
Material for MkDocs pattern for multi-area project documentation (confirmed in
Material docs GitHub discussions #7376 and #2173).

**Confidence:** HIGH. Material for MkDocs official setup page documents these features
directly. The existing `mkdocs.yml` already uses the Material theme.

### 3b. How to document the REST API

**Recommendation: manual hand-authored markdown. Not mkdocstrings. Not an OpenAPI plugin.**

| Approach | Assessment | Confidence |
|----------|-----------|------------|
| **Manual markdown** | Best fit. ~15 stable endpoints, prose examples, curl snippets more useful to ham radio operators than auto-generated class docs. Existing `api-reference.md` is already well-structured manual markdown. | HIGH |
| **mkdocstrings** | Designed for Python library API reference (classes, methods). Produces awkward results for FastAPI route functions — generates parameter tables from Python signatures, not HTTP request/response shapes. Wrong tool for REST API docs. | HIGH (wrong tool) |
| **Neoteroi mkdocs-plugins (OAD)** | Renders OpenAPI 3.x specs as styled pages inside MkDocs. FastAPI exposes `/openapi.json`. Output has known styling issues with Material dark theme (reported in squidfunk/mkdocs-material discussion #7778). Requires the running app at build time or a static spec file. For a small, hand-maintained API surface this adds build complexity for marginal benefit. | MEDIUM |

The existing Swagger UI at `http://localhost:8000/docs` (FastAPI auto-generated) is
already available for interactive exploration. The MkDocs guide's purpose is
human-readable reference with context and examples, not interactive testing.

For the API reference pages, use Material admonitions to highlight authentication
requirements (`!!! note "Authentication required"`) and common error responses.

**Confidence:** HIGH for manual markdown recommendation based on endpoint count and
audience. MEDIUM for the Neoteroi plugin assessment (limited direct testing evidence
with this specific theme configuration).

### 3c. Section-by-section content scope for v1.8

| Section | File | Status | Key changes |
|---------|------|--------|-------------|
| Getting Started / Install & First QSO | `getting-started.md` | Existing | Accuracy review; no major changes |
| Getting Started / Deployment | `deployment.md` | Existing, rewrite | Add: admin container setup, new env vars (`BACKUP_SCHEDULE`, `S3_BUCKET`, `S3_PREFIX`), admin container `depends_on` health check example |
| Admin Guide / Managing Operators | `admin-guide.md` | Existing, update | Update login URL to port 8001 when admin container is deployed; add token revocation section |
| Admin Guide / API Tokens | `admin-tokens.md` | New | Token creation, listing, revocation via UI; `X-API-Key` header usage examples for N1MM+ and Log4OM |
| Admin Guide / Backup | `admin-backup.md` | New | CLI backup usage; S3 setup (env vars); scheduled backup configuration; failure behavior |
| Operator Guide / UDP Interface | `udp.md` | New | UDP ADIF listener; `UDP_OPERATOR` and `APP_OLLOG_TOKEN`; WSJT-X and N1MM+ setup; `nc` test one-liner |
| API Reference / All Endpoints | `api-reference.md` | Existing, expand | Add admin endpoints, token endpoints; update auth section for `X-API-Key` |
| API Reference / Token API | `api-tokens.md` | New | Full token CRUD reference with request/response examples |
| Reference / ADIF Field Reference | `adif-field-reference.md` | Existing | Unchanged |
| Troubleshooting | `troubleshooting.md` | Existing, expand | Add: admin container port conflicts, S3 credential errors, backup failures, `curl` missing in health check |

New files to create: `admin-tokens.md`, `admin-backup.md`, `udp.md`, `api-tokens.md`.
Existing files needing substantive rewrite: `deployment.md`, `api-reference.md`,
`admin-guide.md`.

### 3d. Docs build and serving

The existing pattern (`app.mount("/guide", StaticFiles(directory="site", html=True))`)
is correct and unchanged. MkDocs is built at Docker image build time (`mkdocs build`);
the `site/` directory is baked into the image. No runtime MkDocs dependency. The v1.8
docs changes only affect content files under `docs/` and `mkdocs.yml` — no build
pipeline changes required.

---

## Section 4: Cross-Cutting UX Decisions

### Admin UI login URL when admin container is isolated

- Operator login: `http://host:8000/log/login` (unchanged)
- Admin login: moves to `http://host:8001/admin/ui/login`

The admin login page currently accessible at port 8000 should either be removed from
the operator app (clean) or redirect to port 8001 (safer for bookmarks). A 302
redirect from `http://host:8000/admin/ui/login` to `http://host:8001/admin/ui/login`
handles the transition without 404 confusion.

### Backward compatibility for single-container deployments

Operators who do not run the admin container should have an uninterrupted experience.
The env var gate (`ADMIN_CONTAINER=true`) in `app/main.py` is the cleanest mechanism:

- `ADMIN_CONTAINER` absent or `false` (default): `app/main.py` includes admin routers
  on port 8000 as today.
- `ADMIN_CONTAINER=true`: `app/main.py` drops admin routers; admin service on 8001
  serves them.

This is a non-breaking default.

---

## Sources (v1.8 research)

- FastAPI lifespan events: https://fastapi.tiangolo.com/advanced/events/
- FastAPI sub-applications / mounting: https://fastapi.tiangolo.com/advanced/sub-applications/
- Docker Compose startup order and depends_on: https://docs.docker.com/compose/how-tos/startup-order/
- Docker Compose service definition reference: https://docs.docker.com/reference/compose-file/services/
- boto3 retry configuration: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/retries.html
- AWS retry behavior: https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html
- MkDocs Material navigation setup: https://squidfunk.github.io/mkdocs-material/setup/setting-up-navigation/
- MkDocs Material OpenAPI discussion: https://github.com/squidfunk/mkdocs-material/discussions/7778
- MkDocs Material nav tabs + sections discussion: https://github.com/squidfunk/mkdocs-material/discussions/7376
- mkdocstrings overview: https://mkdocstrings.github.io/
- Neoteroi OpenAPI docs plugin: https://www.neoteroi.dev/mkdocs-plugins/web/oad/
- APScheduler 3.x user guide: https://apscheduler.readthedocs.io/en/3.x/userguide.html
- Schedule tasks with FastAPI (Sentry): https://sentry.io/answers/schedule-tasks-with-fastapi/
- mongodump-s3 PyPI (env var conventions reference): https://pypi.org/project/mongodump-s3/
- halvves/mongodb-backup-s3 (S3_BUCKET convention): https://github.com/halvves/mongodb-backup-s3
- Direct codebase inspection: `app/main.py`, `app/config.py`, `app/admin/router.py`,
  `app/admin/ui_router.py`, `docker-compose.yml`, `mkdocs.yml`, `docs/deployment.md`
  (HIGH confidence — live codebase, 2026-04-10)

---

*Feature & UX research for: ollog v1.8 — Admin container isolation, backup UX, docs rewrite*
*Researched: 2026-04-10*
