---
phase: 027-x-api-key-rest-authentication
verified: 2026-04-10T17:52:39Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 27: X-API-Key REST Authentication — Verification Report

**Phase Goal:** All QSO REST API endpoints accept `X-API-Key: <token>` as a valid alternative to JWT Bearer, with identical operator isolation and correct HTTP 401 responses for invalid or missing credentials.
**Verified:** 2026-04-10T17:52:39Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A `curl` request to any QSO endpoint with `X-API-Key: <valid-token>` succeeds and returns the authenticated operator's data — no JWT needed | VERIFIED | All 5 QSO endpoints wired to dual-auth deps; `_resolve_user_from_api_key` validates and returns `User`; 5 integration tests in `test_qso_api_key.py` cover POST, GET/, GET/{id}, PATCH, DELETE each using `X-API-Key` only |
| 2 | The operator identity resolved from an API key is identical to the identity resolved from a JWT for the same operator — no cross-operator data access is possible | VERIFIED | `get_current_user_jwt_or_apikey` returns the same `User` document regardless of auth path; callsign is derived from `user.callsign` in both paths; `test_api_key_operator_isolation` confirms two-operator data separation at the API layer; `test_operator_isolation.py` CALLSIGN_DEPS set updated to include both new deps |
| 3 | A request with a missing, invalid, or expired credential (both JWT and API key absent or wrong) returns HTTP 401 — never HTTP 403 | VERIFIED | `get_current_user_jwt_or_apikey` raises `HTTP_401_UNAUTHORIZED` exclusively (code lines 178-205); `_resolve_user_from_api_key` returns `None` on any failure without raising; tests 7, 8, 9, 10 in `test_qso_api_key.py` cover invalid key, missing creds, expired key, disabled key — all asserting `status_code == 401` |
| 4 | Admin and profile endpoints continue to require JWT; they do not accept `X-API-Key` authentication | VERIFIED | `app/admin/router.py` uses `require_admin` → `get_current_user` → `oauth2_scheme` (auto_error=True, Bearer only); `app/profile/router.py` uses `get_current_user` (JWT-only); `app/tokens/router.py` uses `get_current_user` (JWT-only); `app/auth/router.py` uses `get_current_user` (JWT-only); test 12 in `test_qso_api_key.py` confirms admin endpoint rejects API key with 401 or 403 |

**Score:** 4/4 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/auth/dependencies.py` | `get_current_user_jwt_or_apikey`, `get_current_operator_callsign_jwt_or_apikey`, `_resolve_user_from_api_key` | VERIFIED | All three functions present and substantive (lines 128-216); `_oauth2_scheme_optional` and `_apikey_scheme` both `auto_error=False` (lines 17-18); existing `oauth2_scheme` unchanged with default `auto_error=True` (line 12) |
| `app/qso/router.py` | 5 QSO endpoints wired to dual-auth deps | VERIFIED | `create_qso` uses `get_current_user_jwt_or_apikey` (line 117); `list_qsos`, `get_qso`, `patch_qso`, `delete_qso` all use `get_current_operator_callsign_jwt_or_apikey` (lines 168, 203, 221, 265) |
| `tests/test_qso_api_key.py` | Integration tests for API key auth | VERIFIED | 12 substantive integration tests covering all 5 CRUD endpoints, operator isolation, invalid/missing/expired/disabled key scenarios, JWT regression, and admin rejection |
| `tests/test_operator_isolation.py` | CALLSIGN_DEPS updated to include new deps | VERIFIED | `CALLSIGN_DEPS` set at line 36 includes both `get_current_operator_callsign_jwt_or_apikey` and `get_current_user_jwt_or_apikey`; both are imported at lines 23-26 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/qso/router.py` | `get_current_user_jwt_or_apikey` | `Depends()` on `create_qso` | WIRED | `user: User = Depends(get_current_user_jwt_or_apikey)` at line 117 |
| `app/qso/router.py` | `get_current_operator_callsign_jwt_or_apikey` | `Depends()` on list/get/patch/delete | WIRED | All 4 remaining endpoints use `operator: str = Depends(get_current_operator_callsign_jwt_or_apikey)` at lines 168, 203, 221, 265 |
| `get_current_user_jwt_or_apikey` | `_resolve_user_from_api_key` | Direct call on API key path | WIRED | `user = await _resolve_user_from_api_key(api_key)` at line 200 |
| `_resolve_user_from_api_key` | `token_is_active()` and `verify_api_token()` | Called in sequence per candidate | WIRED | `token_is_active(candidate)` at line 151; `verify_api_token(api_key, candidate.hashed_token)` at line 153; both imported from `app.tokens.service` at line 10 |
| `_resolve_user_from_api_key` | `ApiToken` (Beanie find by prefix) | `ApiToken.find(ApiToken.token_prefix == prefix)` | WIRED | Lines 148; `ApiToken` imported from `app.tokens.models` at line 9 |
| Admin router | `require_admin` → `get_current_user` (JWT-only) | `oauth2_scheme` with `auto_error=True` | WIRED | `app/admin/router.py` imports and uses only `require_admin`; no dual-auth deps present |

---

### Technical Constraints Check

| Constraint | Status | Evidence |
|------------|--------|---------|
| `_oauth2_scheme_optional` has `auto_error=False` | PASS | Line 17: `OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)` |
| `_apikey_scheme` has `auto_error=False` | PASS | Line 18: `APIKeyHeader(name="X-API-Key", auto_error=False)` |
| Existing `oauth2_scheme` still `auto_error=True` (default) | PASS | Line 12: `OAuth2PasswordBearer(tokenUrl="/auth/token")` — no `auto_error` kwarg, defaults to True |
| Token prefix guard: `startswith("ollog_")` and `len >= 14` before DB call | PASS | Lines 142-143: `if not api_key.startswith("ollog_") or len(api_key) < 14: return None` |
| HTTP 401 (not 403) for all failure modes | PASS | Lines 178-205: `credentials_exception` uses `HTTP_401_UNAUTHORIZED` exclusively |
| `create_qso` uses `get_current_user_jwt_or_apikey` (returns `User`) | PASS | Line 117: `user: User = Depends(get_current_user_jwt_or_apikey)` |
| Other 4 endpoints use `get_current_operator_callsign_jwt_or_apikey` (returns `str`) | PASS | Lines 168, 203, 221, 265 confirmed |
| Admin endpoints NOT changed — still JWT-only via `require_admin` | PASS | `app/admin/router.py` only imports `require_admin`; all 4 admin routes use `require_admin` |
| `token_is_active()` AND `verify_api_token()` both called in lookup | PASS | Lines 151-153: active check first (cheap), then HMAC verify |

---

### Anti-Patterns Found

No blockers or stubs detected.

- `app/qso/router.py` docstring at line 3 still says "Bearer JWT auth via get_current_operator_callsign" — this is a stale comment that predates Phase 27 and does not affect behavior. It is informational only.

---

### Human Verification Required

None. All success criteria are verifiable programmatically via code inspection. The integration tests in `test_qso_api_key.py` cover the full live-path scenarios that would otherwise require manual curl testing.

---

## Summary

Phase 27 fully achieves its goal. The dual-auth dependency chain is implemented correctly with no stubs or orphaned artifacts:

- `_resolve_user_from_api_key` performs a real DB lookup with prefix extraction, active/expiry checks, and constant-time HMAC verification — not a placeholder.
- All 5 QSO endpoints are wired to the correct dual-auth dependencies (`create_qso` → User-returning dep; remaining 4 → callsign-returning dep).
- HTTP 401 is raised exclusively on all failure paths; HTTP 403 is never raised by the dual-auth code.
- Admin, profile, auth, and token management routes are untouched — they continue to use JWT-only dependencies.
- `test_operator_isolation.py` CALLSIGN_DEPS set is current, including both new dual-auth functions so the route introspection audit does not flag any QSO endpoint as missing a callsign dep.

---

_Verified: 2026-04-10T17:52:39Z_
_Verifier: Claude (gsd-verifier)_
