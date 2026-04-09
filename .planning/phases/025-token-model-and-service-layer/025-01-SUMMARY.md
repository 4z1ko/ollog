---
phase: 025-token-model-and-service-layer
plan: "01"
subsystem: tokens
tags: [api-tokens, hmac, beanie, mongodb, pydantic]
dependency_graph:
  requires: [app/config.py, app/database.py, app/auth/models.py]
  provides: [app/tokens/models.py, app/tokens/service.py]
  affects: [app/database.py, app/config.py]
tech_stack:
  added: []
  patterns: [HMAC-SHA256 token hashing, constant-time comparison via hmac.compare_digest, prefix-based DB lookup]
key_files:
  created:
    - app/tokens/__init__.py
    - app/tokens/models.py
    - app/tokens/service.py
    - tests/test_tokens.py
  modified:
    - app/config.py
    - app/database.py
decisions:
  - "hashed_token field name used (not token_hash) to match plan's template and field name in service"
  - "generate_api_token() returns tuple[str, str] — (full_token, token_prefix) — rather than just the token string, so callers always have the prefix without recomputing it"
  - "client.close() changed to await client.aclose() in fixture (Rule 1 fix) to match conftest.py pattern and eliminate RuntimeWarning"
metrics:
  duration: "14 minutes"
  completed: "2026-04-09"
  tasks_completed: 2
  files_created: 4
  files_modified: 2
---

# Phase 25 Plan 01: Token Model and Service Layer Summary

HMAC-SHA256 API token foundation with ApiToken Beanie document, compound index on (token_prefix, user_id), and four pure-stdlib service helpers.

## What Was Built

### app/tokens/__init__.py
Empty package marker. Makes `app.tokens` importable.

### app/tokens/models.py
`ApiToken` Beanie document with 7 fields:
- `user_id: PydanticObjectId` — FK to User collection (no Link[], plain ObjectId)
- `name: str` — human-readable token label
- `token_prefix: str` — first 8 chars of the URL-safe body, for fast pre-hash DB lookup
- `hashed_token: str` — HMAC-SHA256 hex of full token
- `created_at: datetime` — defaults to `datetime.now(tz=timezone.utc)` (no utcnow())
- `last_used_at: Optional[datetime] = None`
- `enabled: bool = True`

Compound index on `(token_prefix, user_id)` named `prefix_user_idx` in `Settings.indexes`.

### app/tokens/service.py
Four public functions, stdlib only:

- `generate_api_token() -> tuple[str, str]` — returns `(full_token, token_prefix)` where full_token is `"ollog_" + secrets.token_urlsafe(32)` (49 chars total, 256-bit entropy) and token_prefix is `body[:8]`
- `hash_api_token(token: str) -> str` — HMAC-SHA256 hex using `settings.api_token_secret.get_secret_value()`
- `verify_api_token(token: str, hashed: str) -> bool` — constant-time via `hmac.compare_digest`
- `validate_token_name(name: str) -> str` — regex `^[a-zA-Z0-9_-]{1,80}$`, raises `ValueError` on rejection

### app/config.py
Added `api_token_secret: SecretStr` (required, no default) after the existing `secret_key` field. `SecretStr` imported from `pydantic`.

### app/database.py
`ApiToken` imported from `app.tokens.models` and appended to `document_models` list in `init_db()`.

### tests/test_tokens.py
11 tests: 10 static (no MongoDB required) + 1 integration test.

Static tests cover:
- Collection name (`api_tokens`)
- Compound index existence and key membership
- `enabled` field default
- Token format (prefix, lengths, alignment)
- Token uniqueness
- Hash returns 64-char hex
- Hash + verify roundtrip (True)
- Verify with wrong token (False)
- Name validation: 4 valid cases
- Name validation: 4 invalid cases

Integration test: insert `ApiToken` with dummy values, find by `token_prefix`, assert fields match.

## Commits

| Hash | Message |
|------|---------|
| b3eab3e | feat(025-01): add ApiToken model, config secret, and database registration |
| d9f9da3 | feat(025-01): add token service helpers and test suite |

## Test Results

```
11 passed in 0.38s
```

All 11 tests pass. Pre-existing failures in `test_operator_isolation.py` and `test_qso_schema.py` (3 tests) confirmed to predate this plan by reverting and re-running — no regressions introduced.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed client.close() awaitable in integration test fixture**
- **Found during:** Task 2 — test run produced `RuntimeWarning: coroutine 'AsyncMongoClient.close' was never awaited`
- **Issue:** `AsyncMongoClient.close()` is a coroutine in newer pymongo; calling without `await` leaves it unawaited
- **Fix:** Changed `client.close()` to `await client.aclose()` to match the `conftest.py` pattern
- **Files modified:** tests/test_tokens.py
- **Commit:** d9f9da3

No other deviations — plan executed as written.

## Self-Check: PASSED

All 6 key files exist on disk. Both task commits (b3eab3e, d9f9da3) confirmed in git log.
