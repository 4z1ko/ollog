# Phase 26: Token CRUD API and Profile UI - Research

**Researched:** 2026-04-09
**Domain:** FastAPI REST endpoints, Beanie document updates, HTMX 2.0.4 partial swaps, Jinja2 templates, "show-once" plaintext token UX
**Confidence:** HIGH

---

## Summary

Phase 26 builds on Phase 25's `ApiToken` document and service layer to deliver four
operator-facing capabilities: create a named token (with optional expiry), view the
active token list, see the plaintext token exactly once after creation, and revoke any
individual token.

The implementation spans two layers: a JSON REST API (`app/tokens/router.py`) that
handles the stateless CRUD operations, and HTMX/Jinja2 UI additions to the existing
profile page (`app/qso/ui_router.py` + `templates/log/profile.html`). No new
dependencies are required — everything uses the already-installed stack.

**Critical gap to fix first:** The `ApiToken` model in Phase 25 does NOT include an
`expires_at: Optional[datetime]` field. Phase 26 must add this field to
`app/tokens/models.py` before implementing the API or UI. Without it, the optional
expiry requirement (TOK-01, TOK-03) cannot be satisfied.

**Primary recommendation:** Add `expires_at` to the model first, then implement a
`/api/tokens` REST router, then add HTMX-driven UI sections to the profile page — one
section for the creation form (POST, returns token reveal banner), one section for the
token list (GET, loads on page render), and a per-row revoke button (DELETE on each
token row).

---

## Standard Stack

No new dependencies — all libraries are already installed.

### Core (already in project)

| Library | Version | Purpose | Role in Phase 26 |
|---------|---------|---------|-----------------|
| `fastapi` | current | API router, `Depends`, `Form`, `Request` | Token CRUD endpoints |
| `beanie` | 2.1.0 | ODM queries, `.find()`, `.set()`, `.delete()` | Fetch, update, delete ApiToken docs |
| `pymongo` | 4.16.0 | `PydanticObjectId` for token ID path params | Parse ObjectId from URL |
| `pydantic` | v2 | Request/response schemas | `TokenCreateRequest`, `TokenResponse` |
| `jinja2` | current | Template rendering | Profile page additions, token reveal banner |
| `htmx` | 2.0.4 | `hx-post`, `hx-delete`, `hx-get`, `hx-swap` | Form submission, list refresh, revoke |

### No New Dependencies Required

All four requirements (create, show-once, list, revoke) are implementable with the
existing stack. `secrets`, `hmac`, `hashlib` for crypto are already used in
`app/tokens/service.py`.

---

## Architecture Patterns

### File Structure for Phase 26

```
app/
└── tokens/
    ├── __init__.py        # exists
    ├── models.py          # ADD: expires_at: Optional[datetime] = None
    ├── service.py         # exists — no changes needed
    └── router.py          # NEW: /api/tokens CRUD endpoints

templates/log/
├── profile.html           # MODIFY: add two new sections below existing form
├── profile_result.html    # no changes needed
├── tokens_list.html       # NEW: partial for the active token table
└── token_created.html     # NEW: partial for the "copy your token" reveal banner

tests/
└── test_token_api.py      # NEW: integration tests for the token CRUD API
```

`app/main.py` gets one new line: `app.include_router(token_router)`.

### Pattern 1: Beanie `find` with user_id filter

All token queries MUST filter by `user_id` — operators must never see each other's tokens.

```python
# Source: app/tokens/models.py + existing Beanie query patterns from project
tokens = await ApiToken.find(
    ApiToken.user_id == user.id,
    ApiToken.enabled == True,
).to_list()
```

`user.id` is a `PydanticObjectId` on the `User` Beanie document. Compare against
`ApiToken.user_id` (same type). This pattern matches how QSO queries filter by
`operator_callsign`.

### Pattern 2: Token creation — generate, hash, respond once

```python
# Source: app/tokens/service.py (generate_api_token, hash_api_token)
full_token, token_prefix = generate_api_token()
hashed = hash_api_token(full_token)
doc = ApiToken(
    user_id=user.id,
    name=validated_name,
    token_prefix=token_prefix,
    hashed_token=hashed,
    expires_at=expires_at_dt,  # None if not provided
)
await doc.insert()
# Return full_token in response — this is the ONLY time it is available
```

The REST endpoint returns `full_token` in the JSON response body. The UI endpoint
passes it to a Jinja2 template for the "shown once" banner. After this response,
`full_token` is gone — only `hashed_token` and `token_prefix` are stored.

### Pattern 3: Token revoke — soft-disable via `enabled = False`

Do NOT delete documents — set `enabled = False`. This preserves audit trail and
prevents prefix reuse confusion. The existing `qso_delete` pattern uses a similar
soft-delete approach with `_deleted: True`.

```python
# Source: admin/ui_router.py toggle_user pattern (await user.set({User.enabled: new_enabled}))
token = await ApiToken.get(token_oid)
if token is None or token.user_id != user.id:
    raise HTTPException(status_code=404, detail="Token not found")
await token.set({ApiToken.enabled: False})
```

**Security requirement:** Verify `token.user_id == user.id` before any mutation.
Operators must not be able to revoke other operators' tokens by guessing IDs.

### Pattern 4: HTMX "show once" banner

The creation form uses `hx-post` → the HTMX response is the token reveal banner partial
(`token_created.html`). This partial contains the `full_token` in a styled
`<code>` block plus a "I've copied this — dismiss" button. Dismissing replaces the
banner with the token list partial via a second HTMX request (`hx-get="/log/tokens"`).

```html
<!-- In profile.html — creation form -->
<form hx-post="/log/tokens/create"
      hx-target="#token-result"
      hx-swap="innerHTML">
  ...
</form>
<div id="token-result">
  <!-- token_created.html banner swapped in here after POST -->
</div>

<!-- token_created.html partial -->
<div class="alert-warning">
  <strong>Copy your token now — it will not be shown again:</strong>
  <code class="...">{{ full_token }}</code>
  <button hx-get="/log/tokens"
          hx-target="#token-list"
          hx-swap="innerHTML">I've copied it — dismiss</button>
</div>
```

### Pattern 5: Token list as separate HTMX-loadable partial

The token list (`tokens_list.html`) is loaded on profile page render via `hx-get`
triggered automatically with `hx-trigger="load"`. This means:
1. The initial profile page GET does NOT need to query tokens (keeps the route simple)
2. The list refreshes automatically after a revoke (`hx-target="#token-list"` on the revoke button)

```html
<!-- In profile.html — token list section -->
<div id="token-list"
     hx-get="/log/tokens"
     hx-trigger="load"
     hx-swap="innerHTML">
  <!-- Loading state (replaced by HTMX on page load) -->
</div>
```

### Pattern 6: HTMX delete pattern for revoke

Follow the existing `qso_row.html` / `qso_delete` pattern exactly:
- `hx-delete="/log/tokens/{token_id}"`
- `hx-target="#token-row-{token_id}"`
- `hx-swap="outerHTML"` (removes the row)
- `hx-confirm="Revoke token '{label}'? Active sessions using this token will be rejected immediately."`

The UI endpoint returns `Response(content="", status_code=200)` on success (same as
`qso_delete`). An empty response + `outerHTML` swap removes the row.

### Pattern 7: Cookie auth for all UI endpoints

All `/log/tokens/*` UI routes MUST use `get_current_user_cookie` (not `get_current_user`).
The `get_current_user` dependency reads from `Authorization: Bearer` header — which
does NOT exist in browser-originated HTMX requests. This is the existing split in
`app/auth/dependencies.py`:
- `get_current_user` → Bearer token → REST API use
- `get_current_user_cookie` → HttpOnly cookie → UI route use

### Pattern 8: API endpoints use Bearer auth

The REST API at `/api/tokens` uses `get_current_user` (Bearer JWT). This is consistent
with all other `/api/*` routes in the project.

### Recommended Router Layout

```python
# app/tokens/router.py
router = APIRouter(prefix="/api/tokens", tags=["tokens"])

@router.post("/", status_code=201)           # create token — returns full_token once
@router.get("/", status_code=200)            # list active tokens (prefix, label, dates)
@router.delete("/{token_id}", status_code=204)  # revoke token
```

```python
# In app/qso/ui_router.py (where all /log/* UI lives)
@ui_router.post("/tokens/create", response_class=HTMLResponse)  # HTMX create
@ui_router.get("/tokens", response_class=HTMLResponse)          # HTMX list partial
@ui_router.delete("/tokens/{token_id}", response_class=HTMLResponse)  # HTMX revoke
```

The UI routes are added to the EXISTING `ui_router` in `app/qso/ui_router.py`.
Do NOT create a separate `tokens/ui_router.py` — the existing profile page and
its `/log/*` namespace already live there.

### Anti-Patterns to Avoid

- **Returning full_token from a GET endpoint:** The token reveal is a one-time response
  to the POST. A subsequent GET must never return `full_token` — only `token_prefix`,
  `name`, `created_at`, and `expires_at`.
- **Fetching all tokens without user_id filter:** Every token query must include
  `ApiToken.user_id == user.id`. No exceptions.
- **Using hard-delete for revoke:** Set `enabled = False`. Hard-delete breaks the
  audit trail and can cause prefix collision confusion.
- **Using `get_current_user` (Bearer) in UI routes:** Use `get_current_user_cookie`
  for all `/log/*` endpoints. HTMX requests from the browser carry no Authorization
  header.
- **Raising 4xx from HTMX endpoints:** HTMX 2.x does not swap on non-2xx responses.
  UI endpoints must return HTTP 200 with an error partial on validation failure (same
  convention as `submit_qso` and `profile_update`).
- **Storing `expires_at` as a naive datetime:** Use `datetime.now(tz=timezone.utc)` and
  `datetime(..., tzinfo=timezone.utc)` consistently. The model uses timezone-aware
  datetimes (`created_at` uses `datetime.now(tz=timezone.utc)`).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ObjectId parsing from URL path | String-to-OID conversion | `PydanticObjectId(token_id)` + catch `Exception` | Follows existing `qso_edit_row` pattern |
| Constant-time token verification | Custom compare loop | `hmac.compare_digest` in `verify_api_token()` | Already exists in `app/tokens/service.py` |
| Date input parsing | Custom date string parsing | `datetime.fromisoformat(date_str)` or `date` type with Pydantic | Pydantic parses ISO 8601 dates automatically in schemas |
| "Copy to clipboard" button | Custom JS implementation | Plain `navigator.clipboard.writeText()` inline onclick | One line of JS, no library needed |

**Key insight:** All crypto is already in `app/tokens/service.py`. Phase 26 is plumbing
(wire existing pieces together) and UI (HTMX partials). No new algorithms.

---

## Critical Gap: `expires_at` Field Missing

**What:** `ApiToken` in `app/tokens/models.py` does NOT have an `expires_at` field.
The Phase 25 plan explicitly excluded it. Phase 26 requirements specify optional expiry
(TOK-01, TOK-03).

**Fix required (first task of Phase 26):**
```python
# Add to ApiToken in app/tokens/models.py
expires_at: Optional[datetime] = None
```

This is a non-breaking additive change — existing documents without the field will
deserialize with `expires_at=None` (Beanie/Pydantic v2 default behavior for `Optional`
fields with a `None` default).

**No migration needed** — MongoDB is schemaless; existing documents get `None` for the
new field automatically on deserialization.

---

## Common Pitfalls

### Pitfall 1: Expiry check missing from token verification (Phase 27 dependency)

**What goes wrong:** Phase 26 stores `expires_at` but Phase 27 (X-API-Key auth) must
check `expires_at` during verification. The Phase 26 revoke endpoint sets
`enabled = False`. Expired-but-not-revoked tokens must also be rejected.
**Why it happens:** Phase 26 stores expiry but Phase 27 does the auth check.
**How to avoid:** Phase 26's API layer should implement a helper
`token_is_active(token: ApiToken) -> bool` that checks BOTH `enabled == True` AND
`(expires_at is None or expires_at > datetime.now(tz=timezone.utc))`. Even if Phase 26
doesn't use it, Phase 27 will import it.
**Warning signs:** TOK-04 says "token immediately stops being accepted" — revoke sets
`enabled = False`. For expiry, Phase 27 must also check `expires_at`.

### Pitfall 2: HTMX partial returns 422 on validation error

**What goes wrong:** FastAPI raises `HTTPException(422)` for Pydantic validation errors.
HTMX 2.x ignores non-2xx responses and does not swap content.
**Why it happens:** Forgetting the "always return 200" convention from HTMX endpoints.
**How to avoid:** Wrap form processing in `try/except ValidationError` (or use
`ValueError` for `validate_token_name`). Return HTTP 200 with an error partial into
`#token-result`.
**Warning signs:** Form submission appears to do nothing — no error shown, no success.

### Pitfall 3: Token prefix misidentified

**What goes wrong:** The `token_prefix` is the first 8 chars of the URL-safe BODY, not
of the full token string (which starts with `"ollog_"`). Full token is `"ollog_{body}"`,
prefix is `body[:8]` which is `full_token[6:14]`.
**Why it happens:** Confusing "prefix" with "first 8 chars of the full string".
**How to avoid:** Use `generate_api_token()` which already returns the correct prefix
as the second element of the tuple. Never recompute the prefix manually.
**Warning signs:** Token lookup fails because stored prefix doesn't match lookup.

### Pitfall 4: profile.html callsign variable scope

**What goes wrong:** `templates/log/profile.html` receives `{"callsign": user.callsign, "profile": user}`.
Adding token UI to this page means the token HTMX endpoints also need a `user` context.
**Why it happens:** The profile route already fetches the full `User` object — token list
endpoints can use the `user.id` from the same dependency injection.
**How to avoid:** Token list/create/revoke endpoints use `user: User = Depends(get_current_user_cookie)`
directly (not just callsign). The `User` object provides `.id` (PydanticObjectId) for
all token queries.

### Pitfall 5: Date input format mismatch

**What goes wrong:** HTML `<input type="date">` submits values as `YYYY-MM-DD` strings.
The existing date inputs in this app use `YYYYMMDD` format (for QSO date/time). Using
the wrong format breaks parsing.
**Why it happens:** Mixing the QSO date format convention with the expiry date input.
**How to avoid:** Use `<input type="date">` for `expires_at` — it natively provides
date pickers in browsers and submits `YYYY-MM-DD`. Parse with
`datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)` in the route.

### Pitfall 6: `user.id` vs `user.username` for ownership

**What goes wrong:** Filtering tokens by `user.username` string instead of
`user.id` (PydanticObjectId). The `ApiToken.user_id` field is typed as `PydanticObjectId`.
**Why it happens:** Comparing the wrong field.
**How to avoid:** Always filter: `ApiToken.user_id == user.id`. The `user.id` field
is the MongoDB `_id` as `PydanticObjectId`, set automatically by Beanie on insert.

---

## Code Examples

Verified patterns from the existing codebase:

### Create token — full flow
```python
# Source: app/tokens/service.py + app/qso/ui_router.py patterns
from datetime import datetime, timezone
from app.tokens.service import generate_api_token, hash_api_token, validate_token_name
from app.tokens.models import ApiToken

full_token, token_prefix = generate_api_token()
hashed = hash_api_token(full_token)
doc = ApiToken(
    user_id=user.id,
    name=validate_token_name(name_str),
    token_prefix=token_prefix,
    hashed_token=hashed,
    expires_at=None,  # or a parsed datetime
)
await doc.insert()
# full_token is now gone from server memory — pass to template response ONCE
```

### List active tokens for a user
```python
# Source: Beanie query pattern from app/tokens/models.py + test_tokens.py
tokens = await ApiToken.find(
    ApiToken.user_id == user.id,
    ApiToken.enabled == True,
).sort(-ApiToken.created_at).to_list()
```

### Revoke a token
```python
# Source: app/admin/ui_router.py toggle_user pattern
from beanie import PydanticObjectId

try:
    oid = PydanticObjectId(token_id)
except Exception:
    raise HTTPException(status_code=404, detail="Token not found")

token = await ApiToken.get(oid)
if token is None or token.user_id != user.id or not token.enabled:
    raise HTTPException(status_code=404, detail="Token not found")

await token.set({ApiToken.enabled: False})
```

### HTMX revoke button row
```html
<!-- Source: templates/log/qso_row.html hx-delete pattern -->
<tr id="token-row-{{ token.id }}">
  <td class="font-mono text-xs">{{ token.token_prefix }}...</td>
  <td>{{ token.name }}</td>
  <td>{{ token.created_at.strftime('%Y-%m-%d') }}</td>
  <td>{{ token.expires_at.strftime('%Y-%m-%d') if token.expires_at else 'Never' }}</td>
  <td>
    <button class="btn-danger btn-sm"
            hx-delete="/log/tokens/{{ token.id }}"
            hx-target="#token-row-{{ token.id }}"
            hx-swap="outerHTML"
            hx-confirm="Revoke '{{ token.name }}'? This cannot be undone.">
      Revoke
    </button>
  </td>
</tr>
```

### HTMX 200 always convention for UI endpoints
```python
# Source: app/qso/ui_router.py submit_qso and profile_update patterns
try:
    name = validate_token_name(name_raw.strip())
except ValueError as exc:
    return templates.TemplateResponse(
        request,
        "log/token_created.html",
        {"error": str(exc), "full_token": None},
    )
# ... proceed with insert ...
return templates.TemplateResponse(
    request,
    "log/token_created.html",
    {"error": None, "full_token": full_token, "token_id": str(doc.id)},
)
```

### Register new router in main.py
```python
# Source: app/main.py — follow existing pattern
from app.tokens.router import router as token_router  # noqa: E402
app.include_router(token_router)
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Beanie `update({"$set": ...})` | `await doc.set({Model.field: value})` | Beanie 2.x typed set method; both work, `.set()` is preferred |
| `datetime.utcnow()` | `datetime.now(tz=timezone.utc)` | Python 3.12+ deprecation; project already uses aware datetimes |

**Deprecated/outdated:**
- `datetime.utcnow()`: deprecated in Python 3.12, raises `DeprecationWarning`. Already
  avoided in `app/tokens/models.py` (uses `datetime.now(tz=timezone.utc)`). Phase 26
  must continue this pattern everywhere.

---

## Open Questions

1. **Should `token_is_active()` helper live in `service.py` or `router.py`?**
   - What we know: Phase 27 (X-API-Key auth middleware) will need to check both
     `enabled` and `expires_at`. Phase 26 only needs `enabled == True` for listing.
   - What's unclear: Whether the planner should create the helper in Phase 26 for
     Phase 27 to use, or leave it to Phase 27.
   - Recommendation: Include it in `service.py` in Phase 26 since the data is there.
     A two-line function with no downstream risk.

2. **Empty token list state: empty table or friendly message?**
   - What we know: The project uses a styled "no results" card for QSO log view
     (`log_table.html` lines 5-19). Same pattern applies to token list.
   - What's unclear: Nothing — use the same empty-state card pattern.
   - Recommendation: `tokens_list.html` renders an empty-state card when
     `tokens | length == 0`, matching `log_table.html`.

3. **REST API: should `DELETE /api/tokens/{id}` return 204 (No Content) or 200?**
   - What we know: The existing REST API uses `204` for `qso_delete` (soft-delete).
     HTTP semantics prefer 204 for successful deletes with no body.
   - Recommendation: 204 No Content for `DELETE /api/tokens/{id}`. The UI endpoint
     (different route) returns 200 with empty body (HTMX convention).

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection:
  - `app/tokens/models.py` — confirmed field list, missing `expires_at`
  - `app/tokens/service.py` — confirmed `generate_api_token()` tuple return, `hash_api_token`, `verify_api_token`, `validate_token_name`
  - `app/qso/ui_router.py` — confirmed all profile routes live here, confirmed HTMX 200-always pattern, hx-delete pattern
  - `app/auth/dependencies.py` — confirmed `get_current_user` (Bearer) vs `get_current_user_cookie` split
  - `app/admin/ui_router.py` — confirmed `await doc.set({Model.field: value})` revoke/toggle pattern
  - `templates/log/profile.html` — confirmed page structure, `#profile-result` target div
  - `templates/log/qso_row.html` — confirmed `hx-delete` + `hx-confirm` + `hx-swap="outerHTML"` pattern
  - `static/css/input.css` — confirmed CSS classes: `btn-danger`, `btn-sm`, `card`, `card-header`, `card-body`, `form-input`, `form-label`, `alert-success`, `alert-warning`, `alert-error`, `badge-green`, `badge-gray`, `table-wrap`, `data-table`
  - `app/database.py` — confirmed `ApiToken` is registered in `init_beanie`
  - `app/main.py` — confirmed router registration pattern

### Secondary (MEDIUM confidence)
- HTMX 2.0.4 documentation: non-2xx responses are not swapped (confirmed by existing code comments in `submit_qso` and `profile_update`)

---

## Metadata

**Confidence breakdown:**
- Model gap (`expires_at` missing): HIGH — directly verified from source
- Standard stack: HIGH — all libraries confirmed installed and in use
- Architecture patterns: HIGH — derived from existing code in the same codebase
- HTMX interaction patterns: HIGH — copied from working `qso_row.html` / `profile_update` patterns
- CSS classes: HIGH — read directly from `static/css/input.css`
- Pitfalls: HIGH — all derived from observed code patterns, not speculation

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable codebase — 30 days)
