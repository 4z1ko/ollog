# Pitfalls Research

**Domain:** Adding named API token auth (X-API-Key) alongside existing JWT Bearer + cookie auth in a FastAPI ham radio logging app
**Researched:** 2026-04-09
**Confidence:** HIGH (codebase read directly; FastAPI auth internals verified against official issues and GitHub discussions; hashing guidance verified against OWASP and pwdlib docs)

---

## Critical Pitfalls

### Pitfall 1: Using Argon2 (pwdlib) to hash API tokens — per-request latency kills the auth path

**What goes wrong:**
The app already uses `pwdlib[argon2]` via `PasswordHash.recommended()` for passwords. It is tempting to call `password_hash.hash(token)` for API tokens too, since the function is already imported and working. Argon2 with recommended parameters (64 MB memory, 3 iterations) takes 200–500 ms per hash. Every authenticated API request must verify the token — this means 200–500 ms of CPU-bound blocking added to every call that uses X-API-Key. Under concurrent load this also starves the asyncio event loop because `password_hash.verify()` is a synchronous CPU-intensive call run on the thread.

**Why it happens:**
The project already imports `hash_password` / `verify_password` from `app/auth/service.py`. Reusing them for tokens is the path of least resistance. Argon2 is correct for passwords because its cost is intentional (attacker must be slow). API tokens are long random strings — the entropy is already high, so the compute cost provides no security benefit over HMAC-SHA256.

**How to avoid:**
Store a prefix (first 8 chars of the plaintext, e.g., `ollog_`) for fast DB lookup, plus a HMAC-SHA256 digest of the full token. Verification is: `hmac.compare_digest(hmac.new(key, token, sha256).hexdigest(), stored_hash)`. The lookup is instant (index on prefix), the verify is microseconds, and `hmac.compare_digest` is constant-time. The HMAC key is a secret stored in settings (separate from `SECRET_KEY` to allow independent rotation). Do not use Argon2 for API tokens.

**Warning signs:**
- P95 latency on any endpoint using `X-API-Key` jumps to 400+ ms
- `top` shows Python worker pegged at 100% CPU on authenticated requests
- Profiler shows `argon2_cffi.core.hash_secret_raw` dominant on token-auth paths

**Phase to address:** Token model + hashing design plan — before any code is written for the token document or verification dependency

---

### Pitfall 2: Storing the full plaintext token in MongoDB (or logging it)

**What goes wrong:**
The token plaintext must be shown exactly once at creation and never again. If the full token is stored in the database (even "temporarily"), a MongoDB dump, backup leak, or read-only DB credential compromise exposes every token in cleartext. Equally dangerous: logging the token value anywhere in `_handle_datagram`, the token creation endpoint response body, or error messages.

**Why it happens:**
"Show it once" UX requires returning it from the POST /auth/tokens endpoint. It is easy to accidentally also persist the plaintext to the `ApiToken` document during construction, or to log `token_value` in a debug statement that stays in production.

**How to avoid:**
Generate plaintext token → return it in the HTTP response body → hash it → persist only the hash + prefix. The plaintext must never touch MongoDB. Add a `NO_LOG_TOKEN` comment at the generation site. In the UI, render the token value in the response and show a clear "You will not see this again" banner. Do not store it in the DOM as a data attribute or in a hidden field that could appear in server-side template logs.

**Warning signs:**
- The `ApiToken` Beanie document has a field named `token` or `plain_token` of type `str`
- Any log line contains a string that matches the token format regex (`ollog_[A-Za-z0-9]{32}`)
- The POST /auth/tokens response is stored in browser history or a `hx-swap` target that re-renders on navigation (HTMX OOB swap issue)

**Phase to address:** Token model design plan — the document schema must explicitly exclude a plaintext field; add a linter/grep check in tests

---

### Pitfall 3: `get_current_user` dependency silently breaks when API key auth is added — wrong 401/403 status codes returned

**What goes wrong:**
`get_current_user` in `app/auth/dependencies.py` uses `OAuth2PasswordBearer(tokenUrl="/auth/token")`. When a request arrives with `X-API-Key` but no `Authorization: Bearer` header, `OAuth2PasswordBearer` fires first (it runs before any API key check in a stacked dependency). With default `auto_error=True`, it immediately returns 403 Forbidden ("Not authenticated") — not 401 — and the API key is never inspected. The caller receives an opaque 403 that gives no indication the X-API-Key path exists.

FastAPI's `OAuth2PasswordBearer` returns 403 (not 401) when the header is absent. This is a documented FastAPI behavior (issues #2026, #10177) that surprises implementors expecting 401.

**Why it happens:**
The natural extension — "add API key check to the existing dependency" — fails because `OAuth2PasswordBearer` raises before the API key branch can run. FastAPI's dependency resolution calls sub-dependencies eagerly.

**How to avoid:**
Create a new unified dependency `get_current_user_or_token` that:
1. Uses `OAuth2PasswordBearer(auto_error=False)` — returns `None` when no Bearer header, no error raised
2. Uses `APIKeyHeader(name="X-API-Key", auto_error=False)` — returns `None` when no header
3. Tries Bearer first, then API key, raises 401 (not 403) if both are absent

Keep the existing `get_current_user` (Bearer-only) unchanged for cookie routes. The new dependency replaces it only on REST API endpoints that should accept both methods. Never put `auto_error=True` schemes in a combined fallback chain.

**Warning signs:**
- curl with only `-H "X-API-Key: ollog_..."` receives `403 Forbidden` instead of `200 OK`
- `/docs` Swagger UI shows only Bearer lock icon; no API key field visible in "Authorize"
- Existing `test_auth.py` tests start failing with unexpected 403s after the dependency change

**Phase to address:** Auth dependency refactor plan — this is the highest-risk integration point; existing tests must pass before and after the change

---

### Pitfall 4: UDP listener uses a startup-pinned `User` object — new API token assigned to the operator is never seen

**What goes wrong:**
In `app/main.py` lifespan, the UDP listener is started once:
```python
udp_user = await UserModel.find_one({"callsign": udp_op})
udp_transport, _ = await start_udp_listener(..., user=udp_user)
```
The `User` object (and the derived operator callsign) are captured at startup and passed into `QSODatagramProtocol.__init__`. They are held in `self._user` and `self._operator` for the process lifetime. If the feature being added includes a concept of "token-scoped operator" (where an API token can be associated with a user different from `UDP_OPERATOR`), the UDP path will never use it — it always uses the startup snapshot.

More concretely: if the UDP ingestion path is later modified to resolve the operator from an incoming token header (a reasonable future extension), the `_handle_datagram` function receives the stale startup operator, not the request-time resolved one.

**Why it happens:**
The current design is intentionally simple: UDP has no auth, no per-datagram identity, operator is config-pinned. Adding token auth to REST endpoints does not change this — but the implementation phase may accidentally try to "unify" auth paths between UDP and HTTP, creating confusion.

**How to avoid:**
Keep UDP operator resolution exactly as-is. The new API token feature is for REST endpoints only. Add an explicit comment in `_handle_datagram` and `start_udp_listener` that the operator/user are startup-pinned and are not affected by token auth. Do not add `X-API-Key` processing to the UDP path. If future UDP-per-token auth is needed, it requires a protocol-level change (not a dependency injection change).

**Warning signs:**
- A plan or code review mentions "make UDP listener use the token auth dependency"
- `_handle_datagram` receives an `api_key` or `token` parameter
- UDP integration tests start importing anything from a new `app/auth/tokens` module

**Phase to address:** UDP compatibility verification plan — add a regression test that UDP inserts still work with `UDP_OPERATOR` config unchanged after the token feature is added

---

### Pitfall 5: ADIF `APP_` field round-trip broken by case normalization or truncation

**What goes wrong:**
The ADIF parser in `app/adif/parser.py` normalizes all field names to UPPERCASE: `field_name = parts[0].upper()`. This means `APP_ollog_source` becomes `APP_OLLOG_SOURCE`. The serializer in `app/adif/serializer.py` outputs keys as-is from the dict. On import, a field named `APP_OLLOG_SOURCE` is stored in MongoDB `model_extra` as `APP_OLLOG_SOURCE`. On export, it is emitted as `<APP_OLLOG_SOURCE:N>value`.

This is correct per the ADIF spec (field names are case-insensitive). The pitfall is if the new token feature adds an `APP_OLLOG_TOKEN_NAME` or similar field to QSOs stamped via API token, and a downstream logger (e.g., WSJT-X, N1MM) reads that field as `APP_Ollog_Token_Name` — on re-import the field becomes `APP_OLLOG_TOKEN_NAME` and matches correctly.

The actual danger: if someone hand-crafts an ADIF file with mixed-case APP_ fields, expecting them to survive round-trip as mixed-case (like `APP_MyApp_foo`), they will be uppercased. This is a known behavior (parser line 72: `field_name = parts[0].upper()`), not a bug, but it can surprise operators who use the exported file with case-sensitive downstream tools.

A secondary risk: the ADIF 3.1.7 spec allows APP_ field names of arbitrary length. If an API token name (e.g., the user-supplied label) is injected as part of an APP_ field name (e.g., `APP_OLLOG_{TOKEN_NAME}`), a very long token name can create an oversized field name. The spec does not specify a max field name length, but MongoDB field names have a 16 MB document limit (not a per-key limit). However, downstream ADIF parsers may truncate or reject oversized field names.

**Why it happens:**
The temptation is to stamp QSOs logged via API token with the token's name for audit trail purposes, e.g., `APP_OLLOG_SOURCE=my-rig-token`. If the token name contains special chars (spaces, colons, angle brackets) and is embedded in a field name, the resulting ADIF is invalid.

**How to avoid:**
If stamping a token source field, use a fixed field name like `APP_OLLOG_SOURCE` with the token name as the value, not as part of the field name. Validate token names at creation to alphanumeric + hyphen/underscore only, max 32 chars. Keep the round-trip rule: field names always uppercase, values preserved verbatim.

**Warning signs:**
- Any code that does `f"APP_OLLOG_{token_name}"` as a field name key
- Token name validation missing from the POST /auth/tokens request schema
- Test that imports a token-stamped ADIF file and checks field names

**Phase to address:** Token model design plan (validation rules) + ADIF stamping plan if token-source stamping is in scope

---

### Pitfall 6: CSRF on token creation and revocation endpoints — cookie auth + state-changing POST

**What goes wrong:**
The existing cookie auth uses `HttpOnly` cookies. The token management UI (create token, revoke token) will use the same `get_current_user_cookie` dependency. A POST to `/auth/tokens` (create) or `DELETE /auth/tokens/{id}` (revoke) from a malicious site works if:
- The browser sends the `access_token` cookie automatically (CSRF)
- The `SameSite` attribute is not set to `Strict` or `Lax` on the cookie

The app currently sets the cookie in `app/auth/router.py` (the cookie login flow in the UI router). If `SameSite` is not explicitly set, the default in modern browsers is `Lax`, which blocks cross-site POSTs but allows top-level navigation GETs. `SameSite=Lax` does protect POST endpoints from CSRF in modern browsers. However, `SameSite=None` (required for cross-origin embedding) would not.

**Why it happens:**
The token management endpoints are the first endpoints in this app that are both cookie-authenticated AND perform sensitive state changes (create/revoke credentials). Previous cookie routes (log view, admin UI) are read-mostly and do not create security-sensitive resources. The new endpoints raise the stakes.

**How to avoid:**
Verify that the existing cookie is set with at minimum `SameSite=Lax`. Check the `set_cookie` call in the UI login router. For the token creation endpoint, add a `Referer` header check or a CSRF double-submit cookie if `SameSite` is not confirmed as `Strict`. Use HTMX for the UI and add `hx-headers='{"X-Requested-With": "XMLHttpRequest"}'` to the form — then verify this header server-side as a lightweight CSRF guard (not a substitute for SameSite, but defense-in-depth). Token revocation (DELETE) is safe from form-based CSRF since HTML forms cannot send DELETE — use DELETE not POST for revocation.

**Warning signs:**
- The login `set_cookie` call in the UI router does not include `samesite="lax"` or `samesite="strict"`
- Token create/revoke are both POST endpoints (DELETE is safer for revocation)
- No CSRF check of any kind on the token creation form

**Phase to address:** Token management UI plan — audit the login cookie attributes before building the create/revoke forms

---

### Pitfall 7: Timing attack via prefix lookup short-circuit — attacker can enumerate valid prefixes

**What goes wrong:**
The recommended token lookup pattern is: query MongoDB for `{"prefix": token[:8], "owner": ...}`, then verify the full hash. If no document is found for a given prefix, the response returns immediately (fast path). If a document is found, hash verification takes microseconds more. An attacker sending many tokens with the same first 8 chars can distinguish "prefix matched" from "prefix not found" by response timing — enabling a prefix enumeration attack.

**Why it happens:**
This is a subtle but real timing oracle. The "fast return on not found" is the natural code path. The gap is small (a MongoDB round-trip vs. a round-trip + hash verify) but measurable over many samples.

**How to avoid:**
After the prefix lookup, always run the hash verification path, even when no document was found — verify against a dummy hash. Use `hmac.compare_digest(candidate_hash, dummy_hash)` on the not-found branch to waste equivalent time. Alternatively, accept the theoretical risk: prefix enumeration only leaks "a token starting with X exists," not the token itself. At 8 chars of the character space, the risk is minimal for a single-operator app. Document the decision.

**Warning signs:**
- Token lookup code has an early `return None` on "not found" before any hash operation
- No dummy verification on the not-found branch

**Phase to address:** Token verification dependency plan — the dummy-verify pattern is a one-line addition, low cost, high security signal

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Reuse `password_hash.verify()` (Argon2) for token verification | Zero new code | 200–500 ms added to every API-key-authenticated request; event loop starvation | Never |
| Store token plaintext in DB "for admin convenience" | Easy token recovery | One DB dump exposes all tokens; breaks the "show once" security guarantee | Never |
| Use `auto_error=True` on `OAuth2PasswordBearer` in the combined auth dependency | No extra code | API key requests get 403 before the key is ever checked | Never |
| Make UDP path also accept API tokens | "Unified auth" aesthetic | UDP is a bare datagram with no headers; token auth is meaningless on this path; breaks the startup-pinned operator invariant | Never |
| Token name with no length/charset validation | Simpler create endpoint | Long or special-char token names break ADIF field stamping and Jinja2 rendering | Never in the token create schema |
| POST for token revocation instead of DELETE | Simpler HTML form | POST revocation is CSRF-vulnerable from forms; DELETE cannot be triggered by a plain HTML form | Acceptable only if HTMX handles revocation (not a plain HTML form) |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| `OAuth2PasswordBearer` + `APIKeyHeader` stacked | Using `auto_error=True` on Bearer scheme in a combined dependency | Set `auto_error=False` on both; try Bearer first, fall back to API key, raise 401 (not 403) if both absent |
| Beanie `ApiToken` document + plaintext | Accidentally including a `plain_token: str` field in the Pydantic model | Document schema must have no plaintext field; hash + prefix only; add a test that inspects the stored document |
| HTMX form + token creation response | HTMX `hx-swap="innerHTML"` retains the response in DOM history; the token value in the response is re-renderable | Use `hx-swap="outerHTML"` with a "token shown" confirmation state that replaces the creation form; never leave the raw token value in a stable DOM node |
| `pwdlib` Argon2 + API token path | `verify_password(token, stored_hash)` is called on the hot auth path | Use `hmac.compare_digest(hmac_sha256(token), stored_hash)` for tokens; reserve Argon2 for password verification only |
| MongoDB `model_extra` + ADIF APP_ fields | Adding a token-stamped APP_ field with a dynamic key name from token label | Use fixed field name `APP_OLLOG_SOURCE`, token label as value; never use token label as part of the key name |
| Cookie `SameSite` + token create form | Not setting `samesite` on the `set_cookie` call | Explicitly set `samesite="lax"` (or `"strict"`) in the login response that sets `access_token` cookie |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Argon2 on every token verify | P95 latency >400 ms on all API-key endpoints | HMAC-SHA256 with prefix-indexed lookup | Any non-trivial request rate; immediately apparent in load tests |
| No index on token prefix field | Full collection scan on every API request | `IndexModel([("prefix", ASCENDING), ("owner_id", ASCENDING)], unique=True)` in `ApiToken.Settings` | Breaks as soon as there are more than ~100 tokens |
| Synchronous `hmac` call without `run_in_executor` | Blocks asyncio loop for CPU-bound verify (minor for HMAC, severe for Argon2) | HMAC is fast enough to call inline; only move to executor if using Argon2 (don't) | Argon2: immediately; HMAC: never a real issue |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing token plaintext in DB | Full token exposure on any DB read (backup, dump, misconfigured replica) | Hash + prefix only; no plaintext field in `ApiToken` document |
| Logging token value in debug/info lines | Token in log files, aggregators, or error trackers | `NO_LOG_TOKEN` comment at generation; grep test that ensures no token value in log output |
| Returning token value in any endpoint other than the creation response | Token retrievable after creation (violates show-once contract) | GET /auth/tokens lists tokens by name + prefix only; never returns hash or reconstructed value |
| 403 (Forbidden) instead of 401 (Unauthorized) on missing API key | Client cannot distinguish "wrong key" from "not authorized to this resource" | `auto_error=False` + manual raise `HTTPException(401)` in combined dependency |
| Token with no expiry and no last-used tracking | Stolen token valid indefinitely; no audit trail | Add `expires_at: Optional[datetime]` and `last_used_at: Optional[datetime]` to `ApiToken`; update `last_used_at` on each verify (background task to avoid latency) |
| Token creation endpoint reachable without CSRF guard | Cross-site form can create tokens on behalf of logged-in operator | Verify `SameSite=Lax` on auth cookie; use `DELETE` not `POST` for revocation |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No "copy to clipboard" button on token creation page | Operator manually selects and copies; risk of partial selection or accidental navigation away | Render `<button onclick="navigator.clipboard.writeText(...)">Copy</button>` next to the token value in the creation response fragment |
| HTMX swap retains token in DOM after "copy" | Operator leaves page open; token value visible in page source | After copy, swap the token display fragment with "Token copied — this value is no longer shown" confirmation state |
| Token list shows truncated hash instead of prefix | Operator cannot identify which token is "rig-api" vs "logbook-sync" by prefix alone | Store a human-readable `name` (label) on the `ApiToken` document; list shows `name` + first 8 chars of plaintext prefix only |
| Revoke button requires a confirmation step but none is shown | Operator accidentally revokes production token | HTMX confirm dialog or two-step (confirm → DELETE) before revocation |
| No indication of which auth scheme was used in `/auth/me` | API consumers cannot debug whether their key was accepted as Bearer or X-API-Key | Return `auth_method: "bearer" | "api_key"` in the `/auth/me` response when the combined dependency is active |

---

## "Looks Done But Isn't" Checklist

- [ ] **Token hashing:** Verify that the `ApiToken` Beanie document has no `plain_token` or `token` string field — grep the model for any field storing the raw token value
- [ ] **HMAC not Argon2:** Verify that `password_hash.verify()` is NOT called anywhere in the token verification dependency — grep for `verify_password` in any new token auth code
- [ ] **Combined dependency 401 not 403:** `curl -X GET /api/qsos/ -H "X-API-Key: wrong"` returns 401, not 403; `curl` with no auth header returns 401, not 403
- [ ] **UDP regression:** After deploying token feature, UDP inserts still work with `UDP_OPERATOR` set — verify `test_udp_pipeline.py` passes unchanged
- [ ] **ADIF round-trip:** Token-stamped QSOs export and re-import cleanly — no APP_ field name issues; `test_adif_roundtrip.py` covers a token-stamped record
- [ ] **Token shown once:** After the creation POST, refreshing the page does not re-show the token — the HTMX response is not cached and re-swappable
- [ ] **Index on prefix:** `db.api_tokens.getIndexes()` shows a unique index on `(prefix, owner_id)` — not just on `prefix` alone (different operators could theoretically share a prefix)
- [ ] **SameSite on auth cookie:** Inspect the `Set-Cookie` response header on `/auth/ui/login` — confirm `SameSite=Lax` or `SameSite=Strict` is present
- [ ] **Token list no hashes:** GET /auth/tokens response body contains `name` and `prefix` fields only — no `hash`, `token_hash`, or reconstructable value
- [ ] **Operator isolation:** A token owned by operator W1AW cannot authenticate requests that modify operator KD9XYZ's QSOs — operator callsign comes from the resolved `ApiToken.owner` document, never from request body

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Argon2 used for tokens (P1) | HIGH — all tokens must be re-issued | Migrate: add HMAC hash field to documents, re-hash on next use (verify Argon2 first, then store HMAC hash, remove Argon2 hash), deprecate Argon2 field; invalidate all tokens after migration deadline |
| Plaintext stored in DB (P2) | CRITICAL — treat as full breach | Rotate all tokens immediately; audit DB access logs; notify affected operators; redesign schema |
| Wrong 403 on missing key (P3) | LOW | Change `auto_error` setting and re-raise with 401 in the dependency; one-line fix, redeploy |
| UDP regression (P4) | LOW | Revert any changes to `_handle_datagram` or `start_udp_listener`; UDP path should be untouched |
| ADIF APP_ field name broken (P5) | MEDIUM | Fix token name validation at creation; migrate existing malformed documents with a one-off script |
| CSRF on create/revoke (P6) | MEDIUM | Add `SameSite` to cookie; convert revocation to DELETE; deploy |
| Token prefix timing oracle (P7) | LOW | Add dummy-verify on not-found branch; no data migration needed |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Argon2 for token hash (P1) | Token model + hashing design plan | No call to `verify_password` in token auth code; HMAC verify confirmed by unit test |
| Plaintext in DB (P2) | Token model design plan | Inspect inserted `ApiToken` document in MongoDB; no plaintext field present |
| Wrong 403 / bad combined dependency (P3) | Auth dependency refactor plan | `curl` tests: no-auth → 401, bad key → 401, good key → 200; existing JWT tests still pass |
| UDP regression (P4) | UDP compatibility verification plan | `test_udp_pipeline.py` passes unchanged post-deploy |
| ADIF APP_ field issues (P5) | Token name validation plan + ADIF stamping plan | Round-trip test with token-stamped record; token name charset validated at create |
| CSRF on token create/revoke (P6) | Token management UI plan | Cookie `Set-Cookie` header has `SameSite=Lax`; revocation uses DELETE |
| Prefix timing oracle (P7) | Token verification dependency plan | Dummy-verify present on not-found branch; code review gate |

---

## Sources

- FastAPI `OAuth2PasswordBearer` returns 403 not 401 (confirmed bug): https://github.com/fastapi/fastapi/issues/10177 and https://github.com/fastapi/fastapi/issues/2026
- FastAPI multiple auth schemes discussion: https://github.com/fastapi/fastapi/discussions/9076 and https://github.com/fastapi/fastapi/discussions/9601
- FastAPI `auto_error=False` for optional auth: https://fastapi.tiangolo.com/reference/security/
- HMAC-SHA256 vs Argon2 for API tokens: https://mojoauth.com/compare-hashing-algorithms/hmac-sha256-vs-argon2 — HMAC appropriate for tokens, Argon2 appropriate for passwords
- OWASP password storage (hash algorithm guidance): https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- OWASP REST Security (token in header not URL): https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html
- ADIF 3.1.7 specification (APP_ field naming, case insensitivity): https://adif.org/317/ADIF_317.htm
- ADIF 3.1.5 annotated (most recent stable spec): https://adif.org/315/ADIF_315_annotated.htm
- pwdlib PyPI (Argon2 recommended parameters): https://pypi.org/project/pwdlib/
- Codebase direct reading: `app/auth/dependencies.py`, `app/auth/service.py`, `app/auth/models.py`, `app/auth/router.py`, `app/udp/server.py`, `app/adif/parser.py`, `app/adif/serializer.py`, `app/qso/service.py`, `app/qso/models.py`, `app/config.py`, `app/main.py`

---
*Pitfalls research for: adding named API token auth (X-API-Key) alongside JWT Bearer + cookie auth in a FastAPI ham radio logging app*
*Researched: 2026-04-09*
