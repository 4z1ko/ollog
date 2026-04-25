---
phase: 51-llms-txt-endpoints-and-content
reviewed: 2026-04-24T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - app/main.py
  - static/llms-full.txt
  - static/llms.txt
  - tests/test_llms.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 51: Code Review Report

**Reviewed:** 2026-04-24
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 51 adds two static-file endpoints (`/llms.txt`, `/llms-full.txt`) and a test suite
covering them. The implementation is clean and minimal: two `FileResponse` routes in
`app/main.py`, two hand-authored plain-text files, and seven `pytest-asyncio` smoke tests.

The main concerns are: (1) a dead code variable (`backup_task`) in the lifespan
function that silently prevents APScheduler backup jobs from being cancelled on shutdown;
(2) inaccurate documentation in `llms-full.txt` where the `/health` error response body
does not match what the code actually returns; and (3) the test suite will silently skip
or error without `asyncio_mode = "auto"` configured, because no `@pytest.mark.asyncio`
mode is set in `pyproject.toml`.

---

## Warnings

### WR-01: Dead variable — backup_task is set to None and never assigned, making the shutdown cancel path unreachable

**File:** `app/main.py:93-123`

**Issue:** `backup_task` is declared at line 93 (`backup_task = None`) but is never
reassigned anywhere in the lifespan function. The APScheduler integration uses
`backup_scheduler` (correctly assigned on line 102 and shut down on line 124), but the
`if backup_task is not None: backup_task.cancel()` block at lines 118-122 is dead code.
This appears to be a leftover from an earlier design (asyncio task-based scheduler) that
was replaced by APScheduler but the cancel guard was not removed. While APScheduler is
correctly shut down via `backup_scheduler.shutdown()`, the dead variable causes confusion
and the dead cancel block could mask a future regression if someone assigns `backup_task`
without adding a corresponding scheduler shutdown call.

**Fix:** Remove the dead `backup_task` variable and its shutdown block entirely:

```python
# Remove these three blocks:
backup_task = None          # line 93 — delete

if backup_task is not None:           # lines 118-122 — delete
    backup_task.cancel()
    try:
        await backup_task
    except asyncio.CancelledError:
        pass
```

After removal, the only backup shutdown path is the correct `backup_scheduler.shutdown()` on line 124.

---

### WR-02: Inaccurate /health error response documented in llms-full.txt

**File:** `static/llms-full.txt:399`

**Issue:** The `/health` section documents the error response body as:
```
{"status": "error", "detail": "<message>"}
```
But the actual implementation in `app/main.py` lines 225 and 232 returns:
```python
{"status": "error", "mongodb": "disconnected"}
```
The documented key is `detail`; the real key is `mongodb`. An LLM reading this reference
to build a health-check client would check the wrong field. This is a content correctness
bug, not just a style issue.

**Fix:** Update line 399 of `static/llms-full.txt`:

```diff
-  {"status": "error", "detail": "<message>"}  — MongoDB unreachable
+  {"status": "error", "mongodb": "disconnected"}  — MongoDB unreachable
```

---

### WR-03: pytest-asyncio mode not configured — tests may fail or require per-test decoration depending on version

**File:** `tests/test_llms.py:14`

**Issue:** All seven tests use `@pytest.mark.asyncio` but `pyproject.toml` has no
`[tool.pytest.ini_options]` section and no `asyncio_mode` setting. With
`pytest-asyncio >= 0.21`, the default mode changed to `strict`, which requires either
the `@pytest.mark.asyncio` decorator on every test (present here) or a module-level
`pytestmark`. However, the test file also imports `from app.main import app` which
triggers the full FastAPI lifespan on module load, which includes database I/O — this can
cause import-time errors in environments without MongoDB.

More critically: the existing `conftest.py` uses `@pytest_asyncio.fixture` but the
`pyproject.toml` has no `asyncio_mode = "auto"` setting. If pytest-asyncio strict mode
requires matching event loop scope declarations and the scope is mismatched, tests can
fail with `ScopeMismatch` errors.

**Fix:** Add an `asyncio_mode` declaration to `pyproject.toml` to make the configuration
explicit and avoid version-dependent behaviour:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

This makes all `async def test_*` functions automatically treated as asyncio tests
without requiring the decorator on each one, and aligns with the `conftest.py` style.

---

## Info

### IN-01: `GET /api/qsos/{qso_id}` not listed in the test_llms_full_api_reference test despite being in llms-full.txt

**File:** `tests/test_llms.py:62-84`

**Issue:** `test_llms_full_api_reference` checks for 15 endpoints by string presence in
the body. `GET /api/qsos/{qso_id}` (single-QSO fetch) is documented in `llms-full.txt`
at line 159 but is not in the test's assertion list. This means the test passes even if
that section is accidentally deleted. Not a bug in itself (the content is correct), but
the test coverage gap is worth noting.

**Fix:** Add an assertion for the single-QSO fetch endpoint:

```python
assert "GET /api/qsos/" in body, "GET /api/qsos/ endpoint missing"
# Add:
assert "GET /api/qsos/{qso_id}" in body, "GET /api/qsos/{qso_id} endpoint missing"
```

---

### IN-02: FileResponse uses a relative path — works in practice but is fragile under uvicorn cwd changes

**File:** `app/main.py:190,199`

**Issue:** Both `FileResponse` calls use relative paths (`"static/llms.txt"`,
`"static/llms-full.txt"`). This works because uvicorn is launched from the project root
and Python's cwd matches. However if the process cwd ever differs (e.g., systemd service
with a `WorkingDirectory` mismatch, or a test runner that changes cwd), the
`FileResponse` will 500 with a `FileNotFoundError`. The `StaticFiles` mount on line 179
uses the same relative `"static"` pattern, so this is a project-wide convention, not
just these routes.

**Fix:** This is low-priority given the project convention is consistent. If hardening is
desired, use `pathlib` relative to `__file__`:

```python
from pathlib import Path
_BASE = Path(__file__).parent.parent  # project root

@app.get("/llms.txt", include_in_schema=False)
async def llms_index():
    return FileResponse(
        path=str(_BASE / "static" / "llms.txt"),
        media_type="text/plain; charset=utf-8",
    )
```

---

_Reviewed: 2026-04-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
