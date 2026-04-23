---
phase: 49-service-layer
reviewed: 2026-04-23T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - tests/test_view_dict.py
  - tests/test_service_sort.py
  - tests/test_sse_sentinel.py
  - app/qso/service.py
  - app/qso/ui_router.py
  - templates/log/log_table.html
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 49: Code Review Report

**Reviewed:** 2026-04-23T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Six files were reviewed covering the new service-layer additions for phase 49: the `get_qso_page()` sort allowlist, SSE sentinel rendering, `_qso_to_view_dict()` helper, and companion tests. The architecture is sound — operator isolation is correctly enforced, the sort allowlist uses a `frozenset` (immutable, O(1) lookup), and the sentinel logic in `log_table.html` matches the test expectations exactly.

One critical issue was found: the `callsign_filter` value passed directly into a MongoDB `$regex` query without escaping, allowing any authenticated operator to inject arbitrary regex patterns. Three warnings cover a logic gap in `parse_adif_datetime` for malformed TIME_ON values, a silent data-loss risk in the inline-edit PATCH handler, and a misleading mismatch between the sort-field name stored in the index (`_created_at`) and the name used in `_ALLOWED_SORT_FIELDS` (`-_created_at` / `_created_at`). Two info items flag a missing `secure` flag on the auth cookie and a bare `except Exception` block used for ObjectId parsing.

---

## Critical Issues

### CR-01: Unescaped user input in MongoDB `$regex` — ReDoS and data probing risk

**File:** `app/qso/service.py:222`

**Issue:** The `callsign_filter` string is taken directly from the query parameter and placed verbatim into a MongoDB `$regex` operator. An authenticated operator can supply a pathological pattern (e.g., `(a+)+$`) to cause catastrophic backtracking in MongoDB's regex engine (ReDoS), or a crafted pattern to probe callsigns belonging to other operators — operator isolation only filters on `_operator`, but a deliberately permissive regex on `CALL` can still be used to infer the shape of other documents if the operator has somehow obtained cross-collection read access, or to degrade shared server performance.

```python
# Current — dangerous
if callsign_filter:
    query["CALL"] = {"$regex": callsign_filter, "$options": "i"}
```

**Fix:** Escape the input with `re.escape()` before constructing the query, so user-supplied text is treated as a literal substring match. This preserves the "search by partial callsign" UX while eliminating injection:

```python
import re

if callsign_filter:
    query["CALL"] = {"$regex": re.escape(callsign_filter), "$options": "i"}
```

---

## Warnings

### WR-01: `parse_adif_datetime` silently misparses TIME_ON values that are neither 4 nor 6 characters

**File:** `app/qso/service.py:34-37`

**Issue:** The function branches on `len(time_on) == 4` to pick between `%H%M` and `%H%M%S`. Any other length (e.g., `"120"`, `"1200000"`, an empty string from a lenient ADIF parser) falls to the `else` branch and is parsed as `%H%M%S`, which raises a `ValueError` with a cryptic message. Worse, a 5-character value like `"12345"` is silently passed to `strptime("%H%M%S", "12345")`, which raises `ValueError` rather than returning a sensible error, causing the record to be counted as an error without explaining why the time was malformed. The docstring says "HHMM (4 chars) or HHMMSS (6 chars)" but the code never validates this constraint.

```python
# Current
if len(time_on) == 4:
    time_part = datetime.strptime(time_on, "%H%M").time()
else:
    time_part = datetime.strptime(time_on, "%H%M%S").time()
```

**Fix:** Add an explicit length guard so the error message is actionable:

```python
if len(time_on) == 4:
    time_part = datetime.strptime(time_on, "%H%M").time()
elif len(time_on) == 6:
    time_part = datetime.strptime(time_on, "%H%M%S").time()
else:
    raise ValueError(
        f"TIME_ON must be HHMM (4 chars) or HHMMSS (6 chars), got {len(time_on)!r} chars: {time_on!r}"
    )
```

### WR-02: Silent no-op when `update_dict` is empty in `qso_update` PATCH handler — user gets stale row with no feedback

**File:** `app/qso/ui_router.py:445-451`

**Issue:** If every submitted field is empty or None (e.g., user clears all inputs and submits), `update_dict` is empty after stripping protected fields. The handler skips `qso.update()` and re-fetches and returns the unchanged row with HTTP 200. The user sees the same row and receives no indication that their edit was rejected — this is a silent no-op that could be mistaken for a save. While not a data-corruption bug, it creates a misleading UX and can mask bugs in form wiring.

```python
# Current
if update_dict:
    await qso.update({"$set": update_dict})

# Refetch to get the updated document
updated = await QSO.get(oid)
```

**Fix:** Return a meaningful 400 error partial or HTMX-compatible feedback when `update_dict` is empty rather than silently returning the unchanged row:

```python
if not update_dict:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No valid fields to update",
    )
await qso.update({"$set": update_dict})
```

Alternatively, return an HTML error partial (HTTP 200 with error content) consistent with the project's HTMX-first pattern.

### WR-03: `_ALLOWED_SORT_FIELDS` uses `_created_at` / `-_created_at` but MongoDB sort key is `_created_at` (the alias) — test asserts the Python-attribute name, not the sort key Beanie resolves

**File:** `app/qso/service.py:18-24` and `tests/test_service_sort.py:176-190`

**Issue:** The `created_at` field on `QSO` is stored under the MongoDB alias `_created_at` (via `Field(alias="_created_at")`). Beanie's `.sort()` accepts either the Python attribute name or the MongoDB field name, but `get_qso_page()` passes the raw `sort_by` string directly to `.sort()`. The allowed values `"_created_at"` and `"-_created_at"` use the MongoDB alias prefix which Beanie may or may not recognise depending on version and `populate_by_name` settings — in Beanie 1.x, sorting by `"_created_at"` (the alias) works correctly when using raw `.sort(str)` with a leading minus. However the test at line 182 asserts the constant contains `"-_created_at"` (with underscore prefix), which differs from the Python attribute `"created_at"`. This is correct for the current Beanie raw `.sort()` path, but if `.sort()` is ever changed to use Python attribute names the sort silently falls back and the mismatch is invisible. A comment documenting this deliberate choice (alias vs attribute name) would prevent a future regression.

**Fix:** Add a comment in the constant and in `get_qso_page()` clarifying that the underscore-prefixed names are MongoDB field aliases, not Python attribute names:

```python
_ALLOWED_SORT_FIELDS: frozenset[str] = frozenset({
    "-qso_date_utc", "qso_date_utc",
    "-CALL", "CALL",
    "-BAND", "BAND",
    "-MODE", "MODE",
    # MongoDB alias "_created_at" (not the Python attribute "created_at")
    "-_created_at", "_created_at",
})
```

---

## Info

### IN-01: Auth cookie missing `secure=True` flag

**File:** `app/qso/ui_router.py:92-97`

**Issue:** The `access_token` cookie is set with `httponly=True` and `samesite="lax"` but does not set `secure=True`. In a production deployment over HTTPS this means the cookie will be transmitted over plain HTTP connections if the browser ever contacts the server over HTTP (e.g., on a LAN where TLS is not enforced). For a self-hosted ham radio logbook on a trusted LAN this is lower risk, but it is worth flagging.

```python
# Current
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    samesite="lax",
)
```

**Fix:** Add `secure=True`, or conditionally apply it based on an environment variable:

```python
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    samesite="lax",
    secure=True,  # or: secure=settings.cookie_secure
)
```

### IN-02: Bare `except Exception` swallows all ObjectId parse errors — consider narrowing

**File:** `app/qso/ui_router.py:334-337`, `358-361`, `393-396`, `538-540`, `750-753`

**Issue:** All five QSO ID parse blocks use `except Exception` to catch `PydanticObjectId(qso_id)` failures. The only realistic exception here is `bson.errors.InvalidId` (or a Pydantic wrapper of it). Using `except Exception` would also catch `MemoryError`, `KeyboardInterrupt` propagated as `Exception`, and similar unrelated failures. This is a minor code quality issue in a low-risk path, but it is inconsistent with the project's otherwise precise error handling.

**Fix:** Narrow the catch to the specific exception type:

```python
from bson.errors import InvalidId

try:
    oid = PydanticObjectId(qso_id)
except (InvalidId, ValueError):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")
```

---

_Reviewed: 2026-04-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
