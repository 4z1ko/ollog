# Phase 52: TIME_ON DB Migration - Research

**Researched:** 2026-04-27
**Domain:** MongoDB one-shot startup migration, pymongo async aggregation pipeline, pytest-asyncio integration tests
**Confidence:** HIGH

## Summary

Phase 52 is a narrow, backend-only phase with two deliverables: (1) an idempotent startup migration function `normalize_time_on()` that pads 4-digit `TIME_ON` values to 6 digits across all operator records in the `qsos` collection, and (2) an integration test that explicitly verifies both HHMM and HHMMSS inputs are accepted by `parse_adif_datetime()` in `app/qso/service.py`.

All implementation decisions are locked in CONTEXT.md. The codebase already contains an exact template (`backfill_created_at()` in `app/main.py:22–47`) and the target validation function (`parse_adif_datetime()` in `app/qso/service.py:29–44`). The MongoDB aggregation pipeline approach using a single `update_many` call is confirmed compatible with the installed stack: pymongo 4.16.0 async client on MongoDB 7.0.31. No new dependencies are required.

The test style is fully established: real MongoDB integration tests with function-scoped fixtures, `@pytest.mark.asyncio` on each async function (STRICT mode), and `pytest.mark.skipif` guards for MongoDB availability. No mocking pattern exists in this codebase.

**Primary recommendation:** Implement `normalize_time_on()` in `app/main.py` as a verbatim structural twin of `backfill_created_at()`, swapping the cursor+bulk_write body for a single `update_many` with aggregation pipeline. Write tests in `tests/test_migration.py` using the existing fixture pattern.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Single `update_many` with aggregation pipeline. Filter: `{"TIME_ON": {"$regex": r"^\d{4}$"}}`. Update: `[{"$set": {"TIME_ON": {"$concat": ["$TIME_ON", "00"]}}}]`. No cursor iteration, no Python loop.
- **D-02:** Function named `normalize_time_on()`, placed in `app/main.py`, called in `lifespan` immediately after `backfill_created_at()`.
- **D-03:** No `_operator` filter — admin-level startup migration across all operators.
- **D-04:** Logging style from `backfill_created_at`: log with two branches — modified count when updates occurred, "already up to date" when nothing to do.
- **D-05:** `parse_adif_datetime()` already accepts HHMM and HHMMSS — no code change to service.py. Write a test that explicitly asserts both formats pass, making DB-02 verifiably green.
- **D-06:** Integration tests hit real MongoDB (localhost:27017) — no mocking.
- **D-07:** New test file `tests/test_migration.py`.
- **D-08:** Three test cases: (1) 4-digit values padded to 6-digit on migration run, (2) second migration run is idempotent, (3) `parse_adif_datetime()` accepts both `"1430"` and `"143000"` without raising.

### Claude's Discretion

- Whether to call `QSO.get_pymongo_collection()` or use the Motor client directly — use whichever the existing `backfill_created_at` collection handle gives access to (follow what's simpler given the aggregation pipeline call).

### Deferred Ideas (OUT OF SCOPE)

None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DB-01 | Existing `TIME_ON` values stored as `HHMM` (4 digits) migrated to `HHMM00` (6 digits) at app startup; migration is idempotent | `update_many` with anchored regex `^\d{4}$` and `$concat` aggregation pipeline satisfies both the padding and idempotency requirements. Verified against pymongo 4.16.0 + MongoDB 7.0 `_Pipeline` type alias in `AsyncCollection.update_many`. |
| DB-02 | Server-side `TIME_ON` validation accepts both `HHMM` (4 digits) and `HHMMSS` (6 digits) | `parse_adif_datetime()` at `app/qso/service.py:36–43` already branches on `len(time_on) == 4` vs `== 6`. No code change needed — test coverage in `tests/test_migration.py` makes this verifiably green. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| TIME_ON padding migration | API / Backend (startup) | Database / Storage | Migration runs in FastAPI lifespan, executes pymongo write against MongoDB qsos collection. No frontend involvement. |
| TIME_ON format validation (DB-02) | API / Backend (service layer) | — | `parse_adif_datetime()` in service.py owns ADIF datetime parsing. Already correct — no tier change needed. |
| Test coverage | Test suite | — | Integration tests touch real MongoDB; no mocking. Test code isolated to `tests/test_migration.py`. |

## Standard Stack

### Core (already installed — no additions needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pymongo (async) | 4.16.0 [VERIFIED: `python3 -c "import pymongo; print(pymongo.version)"`] | `AsyncCollection.update_many` with aggregation pipeline | Native async MongoDB driver; `_Pipeline` type alias confirms aggregation pipeline support in `update_many` signature |
| MongoDB | 7.0.31 [VERIFIED: server ping response] | Target database | Aggregation pipeline in `update_many` requires MongoDB >= 4.2; 7.0 is fully compatible |
| beanie | >=2.1.0 [VERIFIED: pyproject.toml] | `QSO.get_pymongo_collection()` accessor | Returns `AsyncCollection` object used by existing migration |
| pytest-asyncio | 1.3.0 [VERIFIED: pytest --collect-only output] | Async test runner | STRICT mode confirmed — all async tests require `@pytest.mark.asyncio` |

**Installation:** No new packages required.

## Architecture Patterns

### System Architecture Diagram

```
App startup (lifespan)
        │
        ▼
  init_db()                     ← Beanie + MongoDB init
        │
        ▼
  _bootstrap_admin()            ← Admin seed
        │
        ▼
  backfill_created_at()         ← Existing idempotent migration
        │
        ▼
  normalize_time_on()           ← NEW: Phase 52 migration
  │
  ├── QSO.get_pymongo_collection()
  │         │
  │         ▼
  │   AsyncCollection.update_many(
  │     filter:  {TIME_ON: {$regex: "^\d{4}$"}},
  │     update:  [{$set: {TIME_ON: {$concat: ["$TIME_ON","00"]}}}]
  │   )
  │         │
  │         ├── result.modified_count > 0 → logger.info("... %d documents updated")
  │         └── result.modified_count == 0 → logger.info("... 0 documents — already up to date")
        │
        ▼
  watcher / UDP / backup startup
```

### Recommended Project Structure

No structural changes. Changes confined to:
```
app/
└── main.py          # add normalize_time_on() + lifespan call
tests/
└── test_migration.py  # new file
```

### Pattern 1: Idempotent Startup Migration (existing pattern)

**What:** Async function called once in `lifespan()` on app startup. Uses raw pymongo collection (not Beanie ORM) to execute bulk writes efficiently. Idempotency is enforced by the filter — documents that have already been migrated do not match the filter and are not touched.

**When to use:** One-shot data fixups where a field value needs normalisation across all existing records before the app begins serving traffic.

**Example — existing `backfill_created_at` (structural template):**
```python
# Source: app/main.py:22-47 [VERIFIED: Read tool]
async def backfill_created_at():
    from app.qso.models import QSO
    collection = QSO.get_pymongo_collection()
    cursor = collection.find({"_created_at": {"$exists": False}}, {"_id": 1})
    ops = []
    async for doc in cursor:
        ...
        ops.append(UpdateOne(...))
    if ops:
        result = await collection.bulk_write(ops, ordered=False)
        logger.info("_created_at backfill: %d documents updated", result.modified_count)
    else:
        logger.info("_created_at backfill: 0 documents — already up to date")
```

**Phase 52 variation — single `update_many` with aggregation pipeline (D-01):**
```python
# Source: CONTEXT.md D-01 + pymongo AsyncCollection.update_many signature [VERIFIED]
async def normalize_time_on():
    from app.qso.models import QSO
    collection = QSO.get_pymongo_collection()
    result = await collection.update_many(
        {"TIME_ON": {"$regex": r"^\d{4}$"}},
        [{"$set": {"TIME_ON": {"$concat": ["$TIME_ON", "00"]}}}],
    )
    if result.modified_count:
        logger.info("TIME_ON migration: %d documents updated", result.modified_count)
    else:
        logger.info("TIME_ON migration: 0 documents — already up to date")
```

Key differences from `backfill_created_at`:
- No cursor, no Python loop, no `UpdateOne` ops list — single network round-trip
- Update argument is a `list` (aggregation pipeline), not a dict — this is the `_Pipeline` type that `update_many` accepts [VERIFIED: `AsyncCollection.update_many` signature shows `Union[Mapping[str, Any], _Pipeline]`]
- `result` is `UpdateResult` — `.modified_count` attribute gives count of changed documents

### Pattern 2: Integration Test with Real MongoDB (existing pattern)

**What:** Function-scoped fixture creates a fresh test database, yields it, then drops it. Tests use `@pytest.mark.asyncio` and `pytest.mark.skipif` guard for MongoDB availability. STRICT asyncio mode is active — decorator is mandatory.

**When to use:** All tests in this codebase. No mocking pattern exists.

**Example — local fixture (matches existing style in `test_duplicate_detection.py`):**
```python
# Source: tests/test_duplicate_detection.py:51-63 [VERIFIED: Read tool]
@pytest_asyncio.fixture(scope="function")
async def migration_db():
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_migration_test"]
    await init_beanie(database=db, document_models=[QSO])
    yield db
    await client.drop_database("ollog_migration_test")
    await client.aclose()
```

**Asyncio STRICT mode — decorator required:**
```python
# Source: pytest --collect-only output showing "asyncio: mode=Mode.STRICT" [VERIFIED]
@mongo_required
@pytest.mark.asyncio
async def test_normalize_time_on_pads_4digit(migration_db):
    ...
```

### Anti-Patterns to Avoid

- **Cursor + Python loop for TIME_ON:** `backfill_created_at` uses this because the update value is derived from the ObjectId (cannot be expressed in MongoDB query language alone). `normalize_time_on` does not need this — the entire transformation (`$concat`) is expressible as an aggregation pipeline stage. Using a Python loop would be slower and more complex.
- **Unanchored regex:** `{"TIME_ON": {"$regex": r"\d{4}"}}` would match 6-digit values (they also contain 4+ digits). Must use `r"^\d{4}$"` anchored at both ends to match exactly-4-digit strings.
- **Dict update instead of pipeline:** `{"$set": {"TIME_ON": "00"}}` would overwrite the field with a literal string. The aggregation pipeline form (a list) is required to reference the existing field value via `$concat`.
- **Missing `@pytest.mark.asyncio`:** pytest-asyncio 1.3.0 in STRICT mode silently skips or errors on async test functions without the decorator. Every async test in this project has the decorator — follow the pattern.
- **Using `disabled` on form fields (Phase 53 concern):** Out of scope for Phase 52, but noted in STATE.md as critical pitfall for Phase 53.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Field value transformation in MongoDB update | Python loop reading and rewriting each doc | MongoDB aggregation pipeline in `update_many` | Single network round-trip; atomic per-document; no Python memory overhead for large collections |
| ADIF time string parsing | Custom string slicing | `parse_adif_datetime()` already in `app/qso/service.py:29–44` | Already handles HHMM/HHMMSS branching; adding a test is the correct action, not reimplementing |

**Key insight:** MongoDB's aggregation pipeline in `update_many` (available since MongoDB 4.2, confirmed on 7.0) lets the database engine perform the string concatenation without round-tripping data to Python. For a one-time migration this is a minor optimisation, but it also makes idempotency trivial — the anchored regex filter simply finds nothing on a second run.

## Runtime State Inventory

> Rename/refactor trigger: NO — this phase pads field values, it does not rename identifiers.
> Omitted per instructions (greenfield migration pattern, not a rename phase).

## Common Pitfalls

### Pitfall 1: Double-Padding Without Anchored Regex
**What goes wrong:** Filter `{"TIME_ON": {"$regex": r"\d{4}"}}` (no anchors) matches 6-digit strings like `"143000"` because they contain a 4-digit substring. Running the migration a second time would turn `"143000"` into `"14300000"`.
**Why it happens:** MongoDB `$regex` matches substrings by default, not full strings.
**How to avoid:** Use `r"^\d{4}$"` — caret anchors to start of string, dollar anchors to end. This matches only strings that are exactly 4 digits and nothing else. [VERIFIED: anchored regex behaviour is standard PCRE, confirmed by decision D-01 in CONTEXT.md]
**Warning signs:** Second migration run reports `modified_count > 0` — indicates the filter is not excluding already-padded values.

### Pitfall 2: Forgetting `await` on `update_many`
**What goes wrong:** Without `await`, `collection.update_many(...)` returns a coroutine object; the migration appears to succeed (no exception) but no documents are actually modified.
**Why it happens:** Motor/pymongo async methods return coroutines.
**How to avoid:** Always `result = await collection.update_many(...)`. The `if result.modified_count:` branch immediately after will catch this at runtime (result would be a coroutine, not an UpdateResult, so attribute access raises AttributeError).
**Warning signs:** Startup logs show "0 documents — already up to date" on a database known to have 4-digit TIME_ON values.

### Pitfall 3: Missing `@pytest.mark.asyncio` in STRICT Mode
**What goes wrong:** pytest-asyncio 1.3.0 in STRICT mode (confirmed active in this project) does not automatically discover async test functions — they must be marked explicitly. An unmarked async test is collected but not run as a coroutine, leading to confusing failures.
**Why it happens:** STRICT mode is the explicit-declaration policy; AUTO mode would auto-discover. This project uses STRICT.
**How to avoid:** Apply `@pytest.mark.asyncio` to every `async def test_*` function. See existing tests for confirmation.
**Warning signs:** `pytest --collect-only` shows the test as a `<Coroutine>` but it passes trivially without executing the async body.

### Pitfall 4: Lifespan Call Order
**What goes wrong:** If `normalize_time_on()` is inserted before `init_db()`, the Beanie models are not initialised and `QSO.get_pymongo_collection()` raises an error.
**Why it happens:** `get_pymongo_collection()` requires Beanie's internal registry to be populated, which happens during `init_beanie()` inside `init_db()`.
**How to avoid:** Insert the call at line 55 of `app/main.py` — immediately after `await backfill_created_at()`, before the watcher/UDP/backup block. This is the exact position specified in D-02 and confirmed by reading the lifespan function. [VERIFIED: `app/main.py:51-64` read]

## Code Examples

### normalize_time_on() — complete implementation

```python
# Source: CONTEXT.md D-01/D-02/D-04 + pymongo AsyncCollection.update_many [VERIFIED]
async def normalize_time_on():
    """Idempotent startup migration: pad 4-digit HHMM TIME_ON values to HHMM00.

    Uses an anchored regex filter (^\d{4}$) to match only exactly-4-digit strings,
    preventing double-padding on repeated runs. Aggregation pipeline $concat
    appends "00" server-side — no Python loop required.
    """
    from app.qso.models import QSO
    collection = QSO.get_pymongo_collection()
    result = await collection.update_many(
        {"TIME_ON": {"$regex": r"^\d{4}$"}},
        [{"$set": {"TIME_ON": {"$concat": ["$TIME_ON", "00"]}}}],
    )
    if result.modified_count:
        logger.info("TIME_ON migration: %d documents updated", result.modified_count)
    else:
        logger.info("TIME_ON migration: 0 documents — already up to date")
```

### Lifespan insertion point

```python
# Source: app/main.py:50-55 [VERIFIED: Read tool]
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _bootstrap_admin()
    await backfill_created_at()   # existing migration
    await normalize_time_on()     # NEW — Phase 52
    # Start change stream watcher ...
```

### test_migration.py — complete test file skeleton

```python
# Source: CONTEXT.md D-06/D-07/D-08 + tests/conftest.py and test_duplicate_detection.py patterns [VERIFIED]
"""Tests for startup migrations (Phase 52).

Requires live MongoDB at localhost:27017 — skipped if unavailable.
"""
import socket
import pytest
import pytest_asyncio
from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.qso.models import QSO
from app.qso.service import parse_adif_datetime
from app.main import normalize_time_on


def _mongo_available() -> bool:
    try:
        sock = socket.create_connection(("localhost", 27017), timeout=1)
        sock.close()
        return True
    except OSError:
        return False


mongo_required = pytest.mark.skipif(
    not _mongo_available(),
    reason="MongoDB not available at localhost:27017",
)


@pytest_asyncio.fixture(scope="function")
async def migration_db():
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_migration_test"]
    await init_beanie(database=db, document_models=[QSO])
    yield db
    await client.drop_database("ollog_migration_test")
    await client.aclose()


@mongo_required
@pytest.mark.asyncio
async def test_normalize_time_on_pads_4digit(migration_db):
    """D-08 case 1: 4-digit TIME_ON values are padded to 6-digit HHMM00."""
    # Insert QSOs with 4-digit TIME_ON
    collection = QSO.get_pymongo_collection()
    await collection.insert_many([
        {"_operator": "W1AW", "CALL": "K1A", "TIME_ON": "1430", "_deleted": False},
        {"_operator": "W1AW", "CALL": "K2B", "TIME_ON": "0900", "_deleted": False},
    ])
    await normalize_time_on()
    docs = await collection.find({"_operator": "W1AW"}).to_list(length=None)
    for doc in docs:
        assert len(doc["TIME_ON"]) == 6
        assert doc["TIME_ON"].endswith("00")


@mongo_required
@pytest.mark.asyncio
async def test_normalize_time_on_is_idempotent(migration_db):
    """D-08 case 2: Running migration twice produces no additional changes."""
    collection = QSO.get_pymongo_collection()
    await collection.insert_one(
        {"_operator": "W1AW", "CALL": "K1A", "TIME_ON": "1430", "_deleted": False}
    )
    await normalize_time_on()
    docs_after_first = await collection.find({"_operator": "W1AW"}).to_list(length=None)
    first_values = [d["TIME_ON"] for d in docs_after_first]

    await normalize_time_on()
    docs_after_second = await collection.find({"_operator": "W1AW"}).to_list(length=None)
    second_values = [d["TIME_ON"] for d in docs_after_second]

    assert first_values == second_values


@pytest.mark.asyncio
async def test_parse_adif_datetime_accepts_hhmm():
    """D-08 case 3a: parse_adif_datetime accepts 4-digit HHMM (DB-02)."""
    dt = parse_adif_datetime("20240115", "1430")
    assert dt.hour == 14
    assert dt.minute == 30


@pytest.mark.asyncio
async def test_parse_adif_datetime_accepts_hhmmss():
    """D-08 case 3b: parse_adif_datetime accepts 6-digit HHMMSS (DB-02)."""
    dt = parse_adif_datetime("20240115", "143000")
    assert dt.hour == 14
    assert dt.minute == 30
    assert dt.second == 0
```

Note: `test_parse_adif_datetime_accepts_hhmm` and `test_parse_adif_datetime_accepts_hhmmss` do NOT need `migration_db` — they call a pure function and require no MongoDB. The `@pytest.mark.asyncio` decorator is still needed because pytest-asyncio STRICT mode requires it on all async functions, even those that don't await anything.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Motor async driver (separate package) | pymongo `AsyncMongoClient` (built-in async since 4.9) | pymongo 4.9, 2024 | No `motor` dependency needed; `AsyncCollection.update_many` works with the same API |
| Aggregation pipeline in `update_many` required MongoDB 4.2+ | Fully supported in MongoDB 7.0 | MongoDB 4.2, 2019 | No version risk for this project |

**Deprecated/outdated:**
- `motor` package: This codebase does not use motor — it uses pymongo's built-in async support. `AsyncMongoClient` from `pymongo` is the correct import. [VERIFIED: `app/database.py:1`]

## Assumptions Log

> All claims below were verified in this session via Read tool or shell commands.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `QSO.get_pymongo_collection()` returns an `AsyncCollection` that supports `update_many` with aggregation pipeline | Code Examples | None — verified via `python3 -c "import beanie; help(beanie.Document.get_pymongo_collection)"` returning `AsyncCollection` and pymongo 4.16.0 signature confirmation |

**All other claims verified or cited. Assumptions log is effectively empty.**

## Open Questions

None. All decision points are locked in CONTEXT.md and all technical questions were resolved by reading the codebase directly.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| MongoDB | Integration tests, runtime migration | ✓ | 7.0.31 [VERIFIED: server ping] | — |
| pymongo AsyncMongoClient | Migration function, tests | ✓ | 4.16.0 [VERIFIED: import] | — |
| beanie | `QSO.get_pymongo_collection()` | ✓ | >=2.1.0 [VERIFIED: pyproject.toml] | — |
| pytest-asyncio | Async tests | ✓ | 1.3.0 [VERIFIED: pytest output] | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` (configfile detected by pytest) |
| Asyncio mode | STRICT — `@pytest.mark.asyncio` required on every async test |
| Quick run command | `uv run pytest tests/test_migration.py -x` |
| Full suite command | `uv run pytest tests/` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DB-01 | 4-digit TIME_ON values padded to 6-digit at startup | integration | `uv run pytest tests/test_migration.py::test_normalize_time_on_pads_4digit -x` | Wave 0 |
| DB-01 | Migration is idempotent (second run no-ops) | integration | `uv run pytest tests/test_migration.py::test_normalize_time_on_is_idempotent -x` | Wave 0 |
| DB-02 | Server accepts HHMM (4 digits) via parse_adif_datetime | unit | `uv run pytest tests/test_migration.py::test_parse_adif_datetime_accepts_hhmm -x` | Wave 0 |
| DB-02 | Server accepts HHMMSS (6 digits) via parse_adif_datetime | unit | `uv run pytest tests/test_migration.py::test_parse_adif_datetime_accepts_hhmmss -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_migration.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_migration.py` — covers DB-01 (pad + idempotency) and DB-02 (parse_adif_datetime acceptance)

*(Existing test infrastructure — conftest.py, pytest config in pyproject.toml — covers all shared needs. No framework install required.)*

## Security Domain

This phase performs no authentication, no input from external users, and no secrets handling. The migration runs at app startup with internal MongoDB access already established by `init_db()`. No ASVS categories apply.

## Project Constraints (from CLAUDE.md)

| Directive | Applies to Phase 52? | Notes |
|-----------|---------------------|-------|
| Stack: FastAPI + Beanie + pymongo + Jinja2 + HTMX + Tailwind | Partially | Phase 52 is backend-only; only FastAPI + Beanie + pymongo are relevant |
| `apscheduler<4` upper bound is load-bearing — do not touch pyproject.toml | Yes | No dependency changes in this phase — safe |
| Tests require MongoDB on localhost:27017; no mocking pattern | Yes | All integration tests use real MongoDB |
| `uv run pytest tests/` for running tests | Yes | Use `uv run pytest tests/test_migration.py -x` for per-task sampling |
| FOUC prevention inline script in base.html — do not move/defer | No | No template changes in Phase 52 |
| Tailwind: new `dark:` classes need `npm run build` + grep verification | No | No template changes in Phase 52 |
| `readonly` not `disabled` on form fields | No | Phase 53 concern — explicitly out of scope for Phase 52 |

## Sources

### Primary (HIGH confidence)

- `app/main.py:22-47` [VERIFIED: Read tool] — `backfill_created_at()` structural template
- `app/main.py:51-64` [VERIFIED: Read tool] — `lifespan()` function showing insertion point after `backfill_created_at()`
- `app/qso/service.py:29-44` [VERIFIED: Read tool] — `parse_adif_datetime()` branching on `len(time_on) == 4` vs `== 6`
- `app/qso/models.py` [VERIFIED: Read tool] — `QSO` Beanie document model confirming `get_pymongo_collection()` is a classmethod
- `tests/test_duplicate_detection.py` [VERIFIED: Read tool] — canonical test style: local fixture, `mongo_required` skip guard, `@pytest.mark.asyncio`
- `tests/conftest.py` [VERIFIED: Read tool] — shared fixture pattern, MongoDB availability guard
- pymongo 4.16.0 `AsyncCollection.update_many` signature [VERIFIED: `inspect.signature` call] — confirms `_Pipeline` (list) accepted as update argument
- MongoDB 7.0.31 [VERIFIED: server ping] — aggregation pipeline in update_many supported since 4.2
- pytest-asyncio 1.3.0 STRICT mode [VERIFIED: `uv run pytest --collect-only` output]

### Secondary (MEDIUM confidence)

None needed — all claims verified directly against codebase or installed packages.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all versions verified via pip import or pyproject.toml
- Architecture: HIGH — implementation verified by reading existing migration pattern in app/main.py
- Pitfalls: HIGH — derived from reading exact code paths and confirmed by CONTEXT.md decisions
- Test patterns: HIGH — verified by reading existing tests and running pytest --collect-only

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (stable stack — no fast-moving dependencies)
