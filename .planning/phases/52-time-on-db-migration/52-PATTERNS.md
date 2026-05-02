# Phase 52: TIME_ON DB Migration - Pattern Map

**Mapped:** 2026-04-27
**Files analyzed:** 2 (1 modified, 1 new)
**Analogs found:** 2 / 2

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/main.py` | utility (startup migration) | batch | `app/main.py` — `backfill_created_at()` (same file) | exact |
| `tests/test_migration.py` | test | batch + request-response | `tests/test_duplicate_detection.py` | exact |

## Pattern Assignments

---

### `app/main.py` — add `normalize_time_on()` and lifespan call

**Analog:** `app/main.py` — `backfill_created_at()` (lines 22–47)

**Imports pattern** (lines 1–8 of `app/main.py` — all already present, no new imports needed):
```python
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from bson import ObjectId
from pymongo import UpdateOne
from fastapi import Depends, FastAPI, HTTPException, Request
```

**Module-level logger** (line 19 — already present, shared by both migration functions):
```python
logger = logging.getLogger(__name__)
```

**Core migration pattern — `backfill_created_at` structural template** (lines 22–47):
```python
async def backfill_created_at():
    """One-time idempotent migration: stamp _created_at on QSOs that lack it."""
    from app.qso.models import QSO
    collection = QSO.get_pymongo_collection()
    cursor = collection.find(
        {"_created_at": {"$exists": False}},
        {"_id": 1},
    )
    ops = []
    async for doc in cursor:
        oid = doc["_id"]
        if isinstance(oid, ObjectId):
            ts = oid.generation_time.replace(tzinfo=timezone.utc)
        else:
            ts = datetime.now(timezone.utc)
        ops.append(UpdateOne({"_id": oid}, {"$set": {"_created_at": ts}}))

    if ops:
        result = await collection.bulk_write(ops, ordered=False)
        logger.info("_created_at backfill: %d documents updated", result.modified_count)
    else:
        logger.info("_created_at backfill: 0 documents — already up to date")
```

**Phase 52 variation — switch cursor+bulk_write body to single update_many with aggregation pipeline (D-01):**
- `backfill_created_at` uses cursor+bulk_write because the update value is derived from ObjectId (Python-side computation required).
- `normalize_time_on` does NOT need Python-side logic — the full transformation (`$concat`) is expressible as a MongoDB aggregation pipeline stage. Use `update_many` with a `list` (pipeline) as the update argument.
- Filter: `{"TIME_ON": {"$regex": r"^\d{4}$"}}` — anchored regex, matches only exactly-4-digit strings; 6-digit values already present will not match on a second run (idempotency).
- Update argument is a `list`, not a `dict` — this is the `_Pipeline` type accepted by `AsyncCollection.update_many` (verified: pymongo 4.16.0).

**Logging pattern to copy** (lines 43–47 of `app/main.py` — copy the two-branch style exactly):
```python
    if ops:
        result = await collection.bulk_write(ops, ordered=False)
        logger.info("_created_at backfill: %d documents updated", result.modified_count)
    else:
        logger.info("_created_at backfill: 0 documents — already up to date")
```
For `normalize_time_on`, replace the `if ops:` branch with `if result.modified_count:` (single `update_many` returns `UpdateResult` directly).

**Lifespan call site** (lines 50–54 of `app/main.py` — insertion point is line 55, immediately after `backfill_created_at()`):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _bootstrap_admin()
    await backfill_created_at()   # D-05: one-time idempotent migration
    # INSERT HERE: await normalize_time_on()
    # Start change stream watcher for live feed
    client = get_client()
```

**Key constraint:** `normalize_time_on()` must be called after `init_db()` — `QSO.get_pymongo_collection()` requires Beanie's internal registry to be populated, which happens during `init_beanie()` inside `init_db()`.

---

### `tests/test_migration.py` (new file)

**Analog:** `tests/test_duplicate_detection.py` (lines 1–44 for header, imports, guard; lines 51–63 for fixture structure)

**File header / module docstring pattern** (lines 1–12 of `test_duplicate_detection.py`):
```python
"""Tests for QSO duplicate detection (03-02).

All fixtures are local — this file does NOT modify tests/conftest.py.
Integration tests require a live MongoDB at localhost:27017 and are skipped
if unavailable.
...
"""
```

**Imports pattern** (lines 13–22 of `test_duplicate_detection.py` — copy, trim to what's needed):
```python
import socket
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient

from app.auth.models import User
from app.auth.service import hash_password
from app.qso.models import QSO
```
For `test_migration.py`, drop `AsyncGenerator`, `ASGITransport`, `AsyncClient`, `User`, `hash_password` — only `socket`, `pytest`, `pytest_asyncio`, `init_beanie`, `AsyncMongoClient`, `QSO` are needed, plus `from app.qso.service import parse_adif_datetime` and `from app.main import normalize_time_on`.

**MongoDB availability guard pattern** (lines 31–44 of `test_duplicate_detection.py` — copy verbatim):
```python
def _mongo_available() -> bool:
    """Quick synchronous check if MongoDB is reachable at localhost:27017."""
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
```

**Function-scoped fixture pattern** (lines 51–63 of `test_duplicate_detection.py`):
```python
@pytest_asyncio.fixture(scope="function")
async def qso_db():
    """Function-scoped test database with User and QSO registered."""
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_dupdet_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_dupdet_test")
    await client.aclose()
```
For `test_migration.py`, use a unique database name (`"ollog_migration_test"`), and `document_models=[QSO]` only (no `User` needed since there is no auth layer in this test).

**Async test decorator pattern** (lines 124–126 of `test_duplicate_detection.py` — STRICT mode requires both decorators on every `async def test_*`):
```python
@mongo_required
@pytest.mark.asyncio
async def test_duplicate_within_2min_window(qso_db):
```
Integration tests that need MongoDB get `@mongo_required` + `@pytest.mark.asyncio`. Pure-function tests (DB-02, `parse_adif_datetime`) get only `@pytest.mark.asyncio` — no `@mongo_required` since no database is involved.

**Raw collection access pattern** (from `test_duplicate_detection.py` line 129 + `app/main.py` line 29):
```python
from app.qso.models import QSO
collection = QSO.get_pymongo_collection()
```
Used in both `backfill_created_at` and in the test body to insert/query raw documents directly.

---

## Shared Patterns

### Module-Level Logger
**Source:** `app/main.py` line 19
**Apply to:** `normalize_time_on()` in `app/main.py` (already present — no new import needed)
```python
logger = logging.getLogger(__name__)
```

### Raw pymongo Collection Access
**Source:** `app/main.py` line 29; `app/qso/models.py` lines 37+
**Apply to:** `normalize_time_on()` body, `test_migration.py` test bodies
```python
from app.qso.models import QSO
collection = QSO.get_pymongo_collection()
```
`QSO.get_pymongo_collection()` is a Beanie classmethod that returns `AsyncCollection`. Requires `init_beanie()` to have been called first.

### Two-Branch Logging for Idempotent Migrations
**Source:** `app/main.py` lines 43–47
**Apply to:** `normalize_time_on()` logging section
```python
if result.modified_count:
    logger.info("...: %d documents updated", result.modified_count)
else:
    logger.info("...: 0 documents — already up to date")
```

### pytest-asyncio STRICT Mode — Mandatory Decorator
**Source:** `tests/test_duplicate_detection.py` lines 124–126 (and all async tests in the suite)
**Apply to:** Every `async def test_*` function in `tests/test_migration.py`
```python
@pytest.mark.asyncio
async def test_example():
    ...
```
pytest-asyncio 1.3.0 in STRICT mode (confirmed active) does NOT auto-discover async tests. The decorator is mandatory on every async test function, even those that do not `await` anything (e.g., the DB-02 `parse_adif_datetime` unit tests).

### Function-Scoped Test DB Fixture + Teardown
**Source:** `tests/test_duplicate_detection.py` lines 51–63; `tests/conftest.py` lines 11–30
**Apply to:** `migration_db` fixture in `tests/test_migration.py`
```python
@pytest_asyncio.fixture(scope="function")
async def migration_db():
    client = AsyncMongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
    db = client["ollog_migration_test"]
    await init_beanie(database=db, document_models=[QSO])
    yield db
    await client.drop_database("ollog_migration_test")
    await client.aclose()
```

---

## No Analog Found

None. Both deliverables have exact analogs in the codebase.

---

## Metadata

**Analog search scope:** `app/main.py`, `app/qso/service.py`, `app/qso/models.py`, `tests/test_duplicate_detection.py`, `tests/conftest.py`
**Files scanned:** 5
**Pattern extraction date:** 2026-04-27
