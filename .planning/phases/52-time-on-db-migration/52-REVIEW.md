---
phase: 52-time-on-db-migration
reviewed: 2026-04-28T07:11:29Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - tests/test_migration.py
  - app/main.py
  - tests/test_watcher.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 52: Code Review Report

**Reviewed:** 2026-04-28T07:11:29Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Reviewed `app/main.py` (lifespan startup and migration functions) and the two new test files covering the Phase 52 TIME_ON migration and watcher hardening. The `normalize_time_on()` migration function is correct: the anchored `^\d{4}$` regex prevents double-padding, the aggregation pipeline update is server-side and efficient, and the idempotency design is sound.

Two warnings were found: one is a pre-existing dead-code bug in the lifespan shutdown path (`backup_task` is never assigned), and one is a test fixture isolation risk (shared Beanie collection state). Two informational items cover minor quality concerns.

## Warnings

### WR-01: `backup_task` is declared but never assigned — shutdown cancel branch is dead code

**File:** `app/main.py:113-141`

**Issue:** `backup_task` is initialised to `None` at line 113 and never reassigned anywhere in the lifespan function. The `backup_scheduler` object (an APScheduler instance) is correctly created and shut down via `backup_scheduler.shutdown()`, but the parallel `backup_task` cancel branch (lines 138-143) can never execute. If a future developer adds a background asyncio task for backup and stores it in `backup_task`, the shutdown logic would work; but as written the variable is misleading dead code that also diverges the shutdown intent from the implementation.

```python
# Current (lines 113-143):
backup_task = None          # assigned once, never changed
backup_scheduler = None
if settings.backup_schedule:
    ...
    backup_scheduler = make_scheduler(...)   # backup_task still None
    backup_scheduler.start()
...
# shutdown:
if backup_task is not None:    # always False — dead branch
    backup_task.cancel()
    try:
        await backup_task
    except asyncio.CancelledError:
        pass
```

**Fix:** Remove the dead `backup_task` variable and its shutdown block entirely, since the scheduler is shut down correctly via `backup_scheduler.shutdown(wait=False)`. If a future phase introduces a raw asyncio backup task, restore it then.

```python
# Remove lines 113, 138-143 entirely.
# Remaining shutdown for backup (lines 144-145) is correct and sufficient:
if backup_scheduler is not None and backup_scheduler.running:
    backup_scheduler.shutdown(wait=False)
```

---

### WR-02: `migration_db` fixture may collide with `test_db` fixture when both run in the same process

**File:** `tests/test_migration.py:49-59`

**Issue:** The `migration_db` fixture initialises Beanie against `ollog_migration_test` using `init_beanie(database=db, document_models=[QSO])`. Beanie stores collection bindings globally on the document class. If the shared `test_db` fixture (from `tests/conftest.py`) runs in the same pytest session against `ollog_test`, the second `init_beanie` call will silently rebind the `QSO` collection to a different database object. Subsequent operations in the interleaved test run will hit whichever database was bound last. The test files use `scope="function"` which gives test-level teardown, but Beanie's internal `_database` reference on the document class is a process-global side effect that is not reset between fixture teardowns.

This is a latent ordering/isolation risk rather than a deterministic failure, but it can produce spurious `assert len(docs) == 2` failures if tests from `test_migration.py` and other test files run in the same session with MongoDB available.

**Fix:** Align with the project's existing guard pattern used in `tests/conftest.py`: run migration tests in isolation (e.g. `pytest tests/test_migration.py`), or add a module-level marker to serialise them. The CLAUDE.md already documents running single test files. Alternatively, add a comment to the fixture documenting the Beanie global-state caveat so future maintainers are aware.

```python
@pytest_asyncio.fixture(scope="function")
async def migration_db():
    # NOTE: init_beanie() rebinds QSO collection globally. Run migration tests
    # in isolation (`pytest tests/test_migration.py`) to avoid cross-fixture
    # Beanie state collisions.
    client = AsyncMongoClient(...)
    ...
```

---

## Info

### IN-01: `normalize_time_on` comment references "Phase 52 (D-02)" but the lifespan comment says "D-02" while the docstring says "DB-01"

**File:** `app/main.py:50-66` and `app/main.py:74`

**Issue:** The docstring for `normalize_time_on()` (line 50) is silent about its phase/ticket reference. The inline lifespan comment at line 74 reads `# Phase 52 (D-02): pad 4-digit TIME_ON to 6-digit`, but the test file (line 7) refers to both `DB-01` and `DB-02`. The test docstrings use `DB-01` for `normalize_time_on()` and `DB-02` for `parse_adif_datetime()`. The `D-02` vs `DB-02` discrepancy is a minor consistency issue that could cause confusion when cross-referencing the phase plan.

**Fix:** Align the lifespan comment to use `DB-01` (matching the test naming convention):

```python
await normalize_time_on()     # Phase 52 (DB-01): pad 4-digit TIME_ON to 6-digit
```

---

### IN-02: `test_watcher_task_stored_in_app_state` patches `normalize_time_on` but not `backfill_created_at` — both must be mocked

**File:** `tests/test_watcher.py:103-119`

**Issue:** The test patches `_main.normalize_time_on` (added in Phase 52) alongside the other lifespan dependencies. This is correct and the test already works for its stated purpose. However, the comment in the test (line 99) says "all external calls mocked" — `backfill_created_at` is also patched (line 106), so the test is complete. This is an observation, not a gap. Worth noting that the test will need updating if future phases add new lifespan startup calls, which is a normal maintenance burden.

No code change required. The test correctly accounts for `normalize_time_on`.

---

_Reviewed: 2026-04-28T07:11:29Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
