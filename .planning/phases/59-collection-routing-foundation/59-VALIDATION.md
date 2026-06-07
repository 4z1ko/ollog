# Phase 59 Validation Strategy

**Date:** 2026-06-07
**Phase:** 59 - Collection Routing Foundation

## Scope Under Test

Phase 59 verifies the shared routing foundation only:

- username-to-collection-name derivation
- safe rejection of unsafe username values
- raw async MongoDB collection access for a `User` or username
- idempotent per-user QSO index setup
- continued availability of the `QSO` model as a validation/serialization shape

Migration, REST/UI workflow rewiring, stats, admin, live feed, and backup/restore integration are out of scope for this phase.

## Nyquist Sample Points

1. **Happy path naming**
   - `john_doe` maps exactly to `john_doe_qsos`.
   - alphanumeric and underscore usernames remain unchanged before suffixing.

2. **Unsafe naming**
   - empty usernames are rejected.
   - usernames containing MongoDB-dangerous or filesystem-like separators are rejected.
   - names that would create reserved MongoDB collection namespaces are rejected.

3. **Collection access**
   - helper reads the database name from settings and the client from `app.database.get_client()`.
   - uninitialized database client raises a clear runtime error.
   - `User.username` is the canonical runtime source when a user object is supplied.

4. **Index setup**
   - helper calls `create_indexes(...)` with the expected `IndexModel` definitions.
   - `rowHash` index is unique and sparse.
   - index setup can be called repeatedly without custom state.

5. **Compatibility**
   - `QSO.Settings.name` may remain `qsos` in this phase.
   - `_operator`, `_deleted`, `_created_at`, and `rowHash` field semantics stay unchanged.

## Verification Commands

```bash
.venv/bin/python -m pytest tests/test_qso_collections.py tests/test_qso_schema.py
.venv/bin/python -m ruff check app/qso/collections.py tests/test_qso_collections.py
```

If the virtual environment is unavailable, use the repository's established test runner while preserving the same focused test targets.

## Acceptance

Phase 59 is acceptable when the focused tests pass, the helper behavior is deterministic, and all code that needs a per-user QSO collection has one obvious module to import in later phases.

