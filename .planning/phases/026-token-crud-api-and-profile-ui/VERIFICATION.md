---
phase: 026-token-crud-api-and-profile-ui
verified: 2026-04-10T16:02:10Z
status: passed
score: 4/4 must-haves verified
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "After dismissing the creation banner, the plaintext token cannot be recovered — dismiss button now clears #token-result"
  gaps_remaining: []
  regressions: []
---

# Phase 26: Token CRUD API and Profile UI — Verification Report

**Phase Goal:** Operators can create named API tokens, see them listed in Profile Settings, and revoke them — with the plaintext token shown exactly once at creation.
**Verified:** 2026-04-10T16:02:10Z
**Status:** passed
**Re-verification:** Yes — after gap closure

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator can submit a token creation form with a required name and optional expiry; response shows full plaintext token in a "will not be shown again" banner | VERIFIED | `profile.html` lines 151-183: form with `name` (required) and `expires_at` (date input, optional) posting `hx-post="/log/tokens/create"` to `#token-result`. `token_created.html` lines 4-6 render the token in an `alert-warning` banner with "Copy your token now — it will not be shown again". `tokens_create()` in `ui_router.py` generates, hashes, and persists the token, passing `full_token` to the template. |
| 2 | After closing/dismissing the banner, the plaintext token cannot be recovered — the profile page shows only token prefix, label, creation date, and expiry | VERIFIED | GAP CLOSED. `token_created.html` line 16: dismiss button now carries `onclick="document.getElementById('token-result').innerHTML=''"`. This clears `#token-result` immediately on click, removing the full token from the DOM. Separately, `GET /log/tokens` (triggered by `hx-trigger="load"` on `#token-list`) queries `tokens_list.html` which never has access to `full_token` — it only renders `token.token_prefix`, `token.name`, `token.created_at`, and `token.expires_at`. `GET /api/tokens` returns `list[TokenResponse]` which has no `full_token` field. |
| 3 | Active token list displays label, creation date, expiry ("Never" if none), and the first 8 chars of the token | VERIFIED | `tokens_list.html` lines 15-28: columns Token Prefix (`{{ token.token_prefix }}...`), Label (`{{ token.name }}`), Created (`{{ token.created_at.strftime('%Y-%m-%d') }}`), Expires (`{{ token.expires_at.strftime('%Y-%m-%d') if token.expires_at else 'Never' }}`). `token_prefix` is the first 8 characters of the token body (`_PREFIX_LEN = 8` in `service.py`). |
| 4 | Operator can revoke any individual token; the token is immediately disabled | VERIFIED | `tokens_list.html` lines 30-35: Revoke button with `hx-delete="/log/tokens/{{ token.id }}"`, `hx-target="#token-row-{{ token.id }}"`, `hx-swap="outerHTML"`, and `hx-confirm`. `tokens_revoke()` in `ui_router.py` calls `token.set({ApiToken.enabled: False})` (soft-disable). Ownership enforced: `token.user_id != user.id` check prevents revoking another user's token. `token_is_active()` in `service.py` checks both `.enabled` and `.expires_at`. |

**Score:** 4/4 truths verified

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/tokens/models.py` | ApiToken with `expires_at` field | VERIFIED | `expires_at: Optional[datetime] = None` present. `token_prefix`, `hashed_token`, `enabled`, `user_id`, `name`, `created_at` all present. |
| `app/tokens/service.py` | `token_is_active()` helper | VERIFIED | Checks `token.enabled` first; then checks `token.expires_at <= datetime.now(tz=timezone.utc)` if set. |
| `app/tokens/router.py` | REST CRUD: POST 201, GET 200, DELETE 204 | VERIFIED | All three routes present. POST returns `TokenCreateResponse` with `full_token`. GET returns `list[TokenResponse]` (no `full_token` field). DELETE sets `enabled=False` and returns 204. All queries filter by `ApiToken.user_id == user.id`. |
| `app/qso/ui_router.py` | HTMX routes: POST `/log/tokens/create`, GET `/log/tokens`, DELETE `/log/tokens/{id}` | VERIFIED | All three routes at lines 634, 659, 713. All return HTTP 200. |
| `templates/log/token_created.html` | Show-once reveal banner with working dismiss | VERIFIED | Banner renders with "will not be shown again" text and copy-to-clipboard button. Dismiss button at line 16 carries `onclick="document.getElementById('token-result').innerHTML=''"` — clears `#token-result` immediately on click. Also fires `hx-get="/log/tokens" hx-target="#token-list"` to refresh the token list. Both concerns handled. |
| `templates/log/tokens_list.html` | Token list table with revoke buttons | VERIFIED | Table with all required columns. Revoke button uses `hx-delete`, `hx-confirm`, and `hx-swap="outerHTML"` to remove the row from the DOM after revocation. |
| `templates/log/profile.html` | Token creation form + lazy-loaded list | VERIFIED | Form with `name` (required) and `expires_at` (optional date) at lines 151-183. `#token-result` div at line 186. `#token-list` div at lines 196-201 with `hx-trigger="load"` for lazy loading. |
| `tests/test_token_api.py` | Integration tests covering all paths | VERIFIED | 9 tests: create returns `full_token`, create with expiry, invalid name 422, empty list, list after create (no `full_token` in list items), revoke 204, cross-user revoke 404, unauthenticated 401/403. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `templates/log/profile.html` | `/log/tokens/create` | `hx-post` on creation form | WIRED | Line 151: `hx-post="/log/tokens/create"` targeting `#token-result` |
| `templates/log/profile.html` | `/log/tokens` | `hx-trigger="load"` on token list div | WIRED | Lines 197-198: `hx-get="/log/tokens" hx-trigger="load"` |
| `templates/log/token_created.html` | `#token-result` cleared on dismiss | `onclick` on close button | WIRED | Line 16: `onclick="document.getElementById('token-result').innerHTML=''"` clears the banner div immediately |
| `templates/log/token_created.html` | `/log/tokens` list refresh on dismiss | `hx-get` on close button | WIRED | Lines 13-16: `hx-get="/log/tokens" hx-target="#token-list"` also fires on dismiss, keeping the list current |
| `app/tokens/router.py` | `ApiToken.user_id == user.id` | user_id filter on every query | WIRED | GET: `ApiToken.user_id == user.id` filter. DELETE: `token.user_id != user.id` ownership check at line 154. |

---

## Technical Constraints Verification

| Constraint | Status | Evidence |
|------------|--------|----------|
| POST `/api/tokens` returns `full_token` in 201 response | PASS | `TokenCreateResponse` extends `TokenResponse` with `full_token: str`. `status_code=201`. |
| GET `/api/tokens` returns list WITHOUT `full_token` | PASS | `TokenResponse` schema has no `full_token` field. GET route returns `list[TokenResponse]`. |
| Dismiss clears `#token-result` from the DOM | PASS | `onclick="document.getElementById('token-result').innerHTML=''"` on close button in `token_created.html` line 16. |
| GET `/log/tokens` partial never exposes `full_token` | PASS | `tokens_list.html` only renders `token_prefix`, `name`, `created_at`, `expires_at` — no access to `full_token`. |
| All `/log/tokens/*` UI routes return HTTP 200 | PASS | `tokens_list()` always returns template. `tokens_create()` always returns template. `tokens_revoke()` returns `Response(content="", status_code=200)` on all paths. |
| Revoke uses `enabled=False` soft-disable | PASS | Both `router.py` and `ui_router.py` call `token.set({ApiToken.enabled: False})`. |
| `token_is_active()` checks both `.enabled` and `.expires_at` | PASS | Checks `not token.enabled` first; then `expires_at is not None and expires_at <= datetime.now(tz=timezone.utc)`. |

---

## Anti-Patterns Found

None. The previously identified blocker (dismiss button leaving `#token-result` populated) is resolved.

---

## Human Verification Required

None. All checks completed programmatically.

---

## Re-verification Summary

The sole gap from the initial verification is closed. The dismiss button in `templates/log/token_created.html` now carries `onclick="document.getElementById('token-result').innerHTML=''"` which clears the banner div the moment the operator clicks "I've copied it — close". The HTMX call (`hx-get="/log/tokens" hx-target="#token-list"`) still fires in parallel to keep the token list current. No regressions were found in the three passing criteria from the initial verification.

All four success criteria now pass. The phase goal is achieved: operators can create named tokens (shown exactly once), view them in a list (prefix only, no full token), and revoke individual tokens immediately.

---

_Verified: 2026-04-10T16:02:10Z_
_Verifier: Claude (gsd-verifier)_
