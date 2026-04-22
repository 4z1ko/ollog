---
phase: 48-model-foundation
reviewed: 2026-04-21T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - app/qso/models.py
  - app/qso/router.py
  - app/qso/ui_router.py
  - app/adif/router.py
  - app/main.py
  - tests/test_qso_schema.py
  - tests/test_watcher.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 48: Code Review Report

**Reviewed:** 2026-04-21T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Seven files reviewed spanning the QSO model, REST and UI routers, ADIF import/export, application lifespan, and test suite. The model and auth isolation patterns are solid — operator callsign is always injected from the JWT and never accepted from request bodies, and soft-delete filtering is consistently applied across all query paths.

Four warnings were found: an unguarded `None` dereference in the PATCH response path, a `float()` conversion that can raise an unhandled 500, a dead `backup_task` variable in the lifespan shutdown path, and an unvalidated sort-field parameter being passed directly to the database. Three info items were found: a contradictory test that will fail against a non-unique index, an HTTP spec deviation in Content-Disposition headers, and a dead import aliased in `feed/manager.py`.

No critical security vulnerabilities were found.

## Warnings

### WR-01: Unguarded `None` dereference in `patch_qso` after re-fetch

**File:** `app/qso/router.py:260-261`
**Issue:** After `await qso.update({"$set": body})`, the document is re-fetched with `QSO.get(oid)`. The return value is assigned to `updated` without a None-check, and then passed directly to `_qso_to_dict(updated)`. If the document is hard-deleted between the update and the re-fetch (e.g., by a concurrent admin operation), `updated` will be `None` and `_qso_to_dict` will raise an `AttributeError` — resulting in an unhandled 500.

**Fix:**
```python
updated = await QSO.get(oid)
if updated is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")
return _qso_to_dict(updated)
```

---

### WR-02: Unguarded `float()` conversion on user-supplied `tx_pwr` raises 500

**File:** `app/qso/ui_router.py:621-622`
**Issue:** The profile update handler converts the `tx_pwr` form field to `float` without a try/except. If the user submits any non-numeric value (e.g., `"abc"` or `"1.2.3"`), `float(stripped)` raises `ValueError` before the `ProfileUpdateRequest` Pydantic validation runs, resulting in an unhandled 500 that bypasses the HTMX-safe error-partial pattern used everywhere else in this router.

```python
if field_name == "tx_pwr":
    raw[field_name] = float(stripped) if stripped else None  # crashes on non-numeric input
```

**Fix:**
```python
if field_name == "tx_pwr":
    try:
        raw[field_name] = float(stripped) if stripped else None
    except ValueError:
        raw[field_name] = stripped  # let Pydantic reject it with a user-friendly message
```

Alternatively, keep `tx_pwr` as a string in `raw` and rely on Pydantic's coercion in `ProfileUpdateRequest` — then the `ValidationError` is already caught at line 630 and rendered as the error partial.

---

### WR-03: Dead `backup_task` variable — shutdown path never executes

**File:** `app/main.py:93,118-123`
**Issue:** `backup_task` is initialized to `None` at line 93 and is never assigned any value. The `APScheduler`-based path uses `backup_scheduler` (line 102), not `backup_task`. The shutdown block at lines 118-123 checks `if backup_task is not None` and then calls `backup_task.cancel()` — this block is unreachable dead code. The comment implies an asyncio `Task` was intended but was replaced by APScheduler without cleaning up the variable.

```python
backup_task = None          # set here
backup_scheduler = ...      # actually used
...
if backup_task is not None: # always False — dead code
    backup_task.cancel()
```

**Fix:** Remove the `backup_task` variable and its shutdown block entirely:
```python
# Remove lines 93, 118-123
if backup_scheduler is not None and backup_scheduler.running:
    backup_scheduler.shutdown(wait=False)
```

---

### WR-04: Unvalidated `sort` query parameter passed directly to database

**File:** `app/qso/router.py:168`, `app/qso/ui_router.py:258`, `app/qso/service.py:219`
**Issue:** The `sort` query parameter is a free-form string accepted from the request and passed verbatim to Beanie's `.sort()`, which forwards it to PyMongo. There is no allowlist validation. An attacker can supply arbitrary field names — including internal fields like `_operator` or `_deleted` — as the sort key. While this does not enable code execution, it leaks internal schema structure in error responses, can trigger unexpected sort behavior, and is inconsistent with the defensive posture applied elsewhere (e.g., operator isolation, protected-field stripping in PATCH).

**Fix:**
```python
_ALLOWED_SORT_FIELDS = {"qso_date_utc", "CALL", "BAND", "MODE", "_created_at"}

def _validate_sort(sort: str) -> str:
    field = sort.lstrip("-")
    if field not in _ALLOWED_SORT_FIELDS:
        raise HTTPException(status_code=400, detail=f"Invalid sort field: {field!r}")
    return sort
```
Apply this in `get_qso_page` or at the router level before calling the service.

---

## Info

### IN-01: Test `test_qso_duplicate_rejected` contradicts the non-unique index decision

**File:** `tests/test_qso_schema.py:209-217`
**Issue:** `test_qso_compound_index_definition` (line 42-54) explicitly asserts that `unique=True` was removed from the compound index (per 03-02 decision). However, `test_qso_duplicate_rejected` (line 210-217) expects `DuplicateKeyError` to be raised on a second insert with identical compound key fields. Since the index is non-unique, MongoDB will accept the second insert without error — the test's `pytest.raises(DuplicateKeyError)` assertion will fail when run against a live MongoDB instance.

**Fix:** Remove or rewrite the test to reflect the actual enforcement model — app-level `find_duplicate()` rather than DB-level uniqueness:
```python
@pytest.mark.asyncio
async def test_qso_duplicate_not_enforced_at_db_level(test_db, sample_qso_data):
    """DB does not reject duplicate inserts — enforcement is app-level (find_duplicate)."""
    qso1 = QSO(**sample_qso_data)
    await qso1.insert()
    qso2 = QSO(**sample_qso_data)
    # Should NOT raise — the compound index is non-unique by design (03-02)
    await qso2.insert()
    assert qso2.id != qso1.id
```

---

### IN-02: `Content-Disposition` filename is unquoted — HTTP spec deviation

**File:** `app/adif/router.py:148`, `app/qso/ui_router.py:522`
**Issue:** Both ADIF export routes construct the header as:
```python
"Content-Disposition": f"attachment; filename={filename}"
```
RFC 6266 requires the filename to be quoted if it contains special characters. Callsigns are alphanumeric and this is low risk in practice, but some HTTP clients may reject or misparse an unquoted filename token if a future callsign contains unexpected characters (e.g., `/` in portable callsigns like `W1AW/1`).

**Fix:**
```python
"Content-Disposition": f'attachment; filename="{filename}"'
```

---

### IN-03: `full_document="updateLookup"` in change stream is misleading

**File:** `app/feed/manager.py:36`
**Issue:** The change stream pipeline matches only `insert` operations (`operationType: "insert"`). The `full_document="updateLookup"` option is only meaningful for update/replace/delete events — it has no effect on insert events (inserts always include the full document in `fullDocument`). The option is harmless but signals intent incorrectly.

**Fix:**
```python
async with await collection.watch(pipeline) as stream:
```
Or document why `full_document` is retained:
```python
# full_document="updateLookup" retained for future update-event support
async with await collection.watch(pipeline, full_document="updateLookup") as stream:
```

---

_Reviewed: 2026-04-21T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
