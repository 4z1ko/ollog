# Phase 3: QSO Entry & Log View - Research

**Researched:** 2026-04-03
**Domain:** FastAPI REST API + Beanie ODM QSO CRUD, HTMX form UI, duplicate detection, paginated log view
**Confidence:** HIGH

## Summary

Phase 3 builds on a well-established codebase: Beanie with `extra='allow'` for ADIF field passthrough, JWT callsign injection, and an HTMX 2.0.4 + Jinja2 UI pattern proven in Phase 2 admin screens. All four plans (API, duplicate detection, web form, log view) can be implemented with patterns already present in the project.

The primary complexity lies in three areas: (1) a PATCH update for QSO documents that have both declared fields and arbitrary ADIF `model_extra` fields requires using `$set` with a raw dict rather than Beanie's typed `set()`, (2) the duplicate detection window query uses a raw MongoDB dict against `qso_date_utc` with `$gte/$lte` and `timedelta`, and (3) the HTMX duplicate-warning UI pattern requires a two-step flow — server returns a 409-class partial with a warning banner that the user must confirm before resubmitting.

The API design must preserve ADIF field names verbatim in the request body so Phase 4 import can reuse the same endpoint. Using `Dict[str, str]` or a `BaseModel` with `model_config = ConfigDict(extra="allow")` as the POST body is the correct approach.

**Primary recommendation:** Use raw `{"$set": update_dict}` for all PATCH operations on QSO documents; use `find().skip().limit().sort().count()` chain for pagination; use 422-with-warning-body for duplicate detection returned as HTMX partial.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.135.0 (already installed) | API + UI routes | Already in project |
| Beanie | >=2.1.0 (already installed) | MongoDB ODM | Already in project |
| pymongo AsyncMongoClient | >=4.16.0 (already installed) | Async driver | Already in project |
| Jinja2Templates | via fastapi[standard] | Server-side HTML | Already established |
| HTMX | 2.0.4 (CDN in base.html) | Hypermedia UI | Already in base.html |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pydantic BaseModel | v2 (via fastapi) | Request/response schemas | POST/PATCH body shapes |
| datetime + timedelta | stdlib | UTC timestamps, dup window | Everywhere datetime is used |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Raw `$set` dict for PATCH | Beanie `set({QSO.field: val})` | Typed set() cannot handle arbitrary model_extra ADIF keys — must use raw dict |
| `Dict[str, str]` POST body | Pydantic model with extra=allow | Dict is simpler for full ADIF passthrough; Pydantic model gives better validation |
| `hx-confirm` for delete | Custom JS modal | hx-confirm is native browser confirm() — simpler, no JS needed |

**Installation:** No new packages required. All dependencies present.

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── qso/
│   ├── __init__.py
│   ├── models.py         # QSO Beanie Document (existing)
│   ├── router.py         # REST API: POST/GET/PATCH/DELETE /api/qsos/
│   ├── ui_router.py      # UI: /log/* routes (form, log view, edit row partials)
│   └── service.py        # duplicate detection, QSO build logic
templates/
├── log/
│   ├── log.html          # full log page (extends base.html)
│   ├── log_table.html    # paginated table partial (HTMX swap target)
│   ├── qso_row.html      # single row view partial
│   ├── qso_row_edit.html # single row edit partial
│   └── form.html         # QSO entry form partial
└── base.html             # existing, no changes needed
```

---

### Pattern 1: QSO POST API Body — ADIF Field Passthrough

**What:** Accept all ADIF fields verbatim in POST body as-is so Phase 4 import can reuse this endpoint.

**When to use:** `POST /api/qsos/`

**Design decision:** Use a thin Pydantic model with `extra="allow"` for required field validation, then pass `model_extra` through for arbitrary ADIF fields. Alternatively, accept `Dict[str, Any]` and validate required keys manually.

```python
# Source: FastAPI docs + project pattern
from pydantic import BaseModel, ConfigDict
from typing import Any

class QSOCreateRequest(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    CALL: str
    QSO_DATE: str       # YYYYMMDD string, validated to datetime
    TIME_ON: str        # HHMM or HHMMSS string
    BAND: str
    FREQ: Optional[str] = None
    MODE: str
    RST_SENT: Optional[str] = None
    RST_RCVD: Optional[str] = None
    # All other ADIF fields captured in model_extra

@router.post("/api/qsos/", status_code=201)
async def create_qso(
    body: QSOCreateRequest,
    operator: str = Depends(get_current_operator_callsign),
):
    # Parse QSO_DATE + TIME_ON → qso_date_utc datetime
    # Check duplicate window
    # Build QSO document from body.model_dump() + body.model_extra
    # Insert
```

**ADIF date/time parsing:**
- `QSO_DATE`: `YYYYMMDD` string → `datetime.strptime(v, "%Y%m%d")`
- `TIME_ON`: `HHMM` or `HHMMSS` → `datetime.strptime(v, "%H%M")` or `"%H%M%S"`
- Combine into UTC-aware datetime: `datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)`
- Store as `qso_date_utc` field on QSO document

---

### Pattern 2: PATCH QSO — Partial Update with Arbitrary ADIF Fields

**What:** Accept a dict of fields to update; use raw `$set` because Beanie's typed `set()` cannot handle `model_extra` keys.

**When to use:** `PATCH /api/qsos/{qso_id}`

```python
# Source: Beanie docs (raw MongoDB syntax) + FastAPI partial update pattern
from typing import Any

@router.patch("/api/qsos/{qso_id}")
async def update_qso(
    qso_id: str,
    body: Dict[str, Any],
    operator: str = Depends(get_current_operator_callsign),
):
    qso = await QSO.get(qso_id)
    if qso is None or qso.operator_callsign != operator:
        raise HTTPException(404)
    if qso.is_deleted:
        raise HTTPException(404)

    # Never allow operator_callsign or _operator to be patched
    body.pop("_operator", None)
    body.pop("operator_callsign", None)
    body.pop("_deleted", None)
    body.pop("is_deleted", None)

    # Re-parse qso_date_utc if QSO_DATE or TIME_ON changed
    # Use raw $set — works for both declared fields and model_extra ADIF keys
    await qso.update({"$set": body})
    return await QSO.get(qso_id)
```

**Critical:** `await bar.set({QSO.CALL: "W1AW"})` only works for declared Pydantic fields. For dynamic ADIF keys from `model_extra`, use `await qso.update({"$set": {"COMMENT": "new value"}})`.

---

### Pattern 3: Soft Delete

**What:** Set `_deleted: true` in MongoDB via `is_deleted=True`.

```python
# Source: existing QSO model + beanie update pattern
@router.delete("/api/qsos/{qso_id}", status_code=204)
async def soft_delete_qso(
    qso_id: str,
    operator: str = Depends(get_current_operator_callsign),
):
    qso = await QSO.get(qso_id)
    if qso is None or qso.operator_callsign != operator:
        raise HTTPException(404)
    await qso.update({"$set": {"_deleted": True}})
```

Note: `is_deleted` is the Python attribute; `_deleted` is the MongoDB field name (via `serialization_alias`). The raw `$set` must use the MongoDB field name `_deleted`.

---

### Pattern 4: Paginated Log Query

**What:** Find active QSOs with filters, count total, return page.

```python
# Source: beanie-odm.dev/tutorial/finding-documents/ + query API docs
from beanie.operators import In

async def get_qso_page(
    operator: str,
    page: int = 1,
    page_size: int = 50,
    callsign_filter: str | None = None,
    band_filter: str | None = None,
    mode_filter: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort_by: str = "-qso_date_utc",
) -> tuple[list[QSO], int]:
    query = {"_operator": operator, "_deleted": False}

    if callsign_filter:
        query["CALL"] = {"$regex": callsign_filter, "$options": "i"}
    if band_filter:
        query["BAND"] = band_filter
    if mode_filter:
        query["MODE"] = mode_filter
    if date_from or date_to:
        query["qso_date_utc"] = {}
        if date_from:
            query["qso_date_utc"]["$gte"] = date_from
        if date_to:
            query["qso_date_utc"]["$lte"] = date_to

    base = QSO.find(query)
    total = await base.count()
    items = await base.sort(sort_by).skip((page - 1) * page_size).limit(page_size).to_list()
    return items, total
```

**Sort field mapping:** Sort parameter from UI/API must map to actual MongoDB field names:
- `date_asc` → `+qso_date_utc`
- `date_desc` → `-qso_date_utc`
- `call_asc` → `+CALL`
- `call_desc` → `-CALL`
- `band_asc` → `+BAND`

---

### Pattern 5: Duplicate Detection

**What:** Before inserting, query for a QSO with same CALL, BAND, MODE within ±2 minutes.

**When to use:** Inside `create_qso` before insert.

```python
# Source: pymongo datetime range query docs + project utils
from datetime import timedelta

async def find_duplicate(
    operator: str,
    call: str,
    band: str,
    mode: str,
    qso_date_utc: datetime,
) -> QSO | None:
    window_start = qso_date_utc - timedelta(minutes=2)
    window_end = qso_date_utc + timedelta(minutes=2)

    return await QSO.find_one({
        "_operator": operator,
        "CALL": call,
        "BAND": band,
        "MODE": mode,
        "_deleted": False,
        "qso_date_utc": {"$gte": window_start, "$lte": window_end},
    })
```

**API duplicate response:** Return HTTP 409 with body `{"duplicate": true, "existing_id": "..."}` — client may force-save by sending `?force=true` query param on re-submit. This avoids a two-step flow on the REST API.

**UI duplicate warning:** Server returns 409 HTML partial with a warning banner. HTMX shows it inline above the form. User clicks "Save anyway" button which re-POSTs with `?force=true`.

---

### Pattern 6: HTMX OOB for Duplicate Warning

**What:** Server returns warning HTML alongside form reset (OOB swap) when duplicate detected.

```html
<!-- Server response for duplicate (returned as HTML partial) -->
<div id="qso-form-warning" hx-swap-oob="true">
  <div class="warning-msg">
    Possible duplicate: VK2XYZ on 20M/CW was logged 1 minute ago.
    <form hx-post="/log/qsos?force=true" hx-target="#qso-result">
      <!-- hidden fields from original form -->
      <button type="submit">Save Anyway</button>
      <button type="button" onclick="document.getElementById('qso-form-warning').innerHTML=''">Cancel</button>
    </form>
  </div>
</div>
<!-- Primary swap target: empty (no change to form) -->
<div></div>
```

**Alternative (simpler):** Return 422 status with warning message in the primary swap target. HTMX swaps in a warning div. No OOB needed — just return the warning where the result div is. User clicks "Save Anyway" which hits the same endpoint with `force=true`.

---

### Pattern 7: HTMX Edit Row

**What:** Inline edit of a QSO row in the log table.

```html
<!-- View row: hx-target is the row itself -->
<tr id="qso-{{ qso.id }}">
  <td>{{ qso.CALL }}</td>
  <td>{{ qso.qso_date_utc | utcformat }}</td>
  <td>{{ qso.BAND }}</td>
  <td>{{ qso.MODE }}</td>
  <td>
    <button hx-get="/log/qsos/{{ qso.id }}/edit"
            hx-target="#qso-{{ qso.id }}"
            hx-swap="outerHTML">Edit</button>
    <button hx-delete="/log/qsos/{{ qso.id }}"
            hx-target="#qso-{{ qso.id }}"
            hx-swap="outerHTML"
            hx-confirm="Delete this QSO?">Delete</button>
  </td>
</tr>

<!-- Edit row (returned by GET /log/qsos/{id}/edit) -->
<tr id="qso-{{ qso.id }}">
  <td><input name="CALL" value="{{ qso.CALL }}"></td>
  <td><input name="QSO_DATE" value="{{ qso.QSO_DATE }}"></td>
  <!-- ... more fields ... -->
  <td>
    <button hx-patch="/log/qsos/{{ qso.id }}"
            hx-target="#qso-{{ qso.id }}"
            hx-swap="outerHTML"
            hx-include="closest tr">Save</button>
    <button hx-get="/log/qsos/{{ qso.id }}"
            hx-target="#qso-{{ qso.id }}"
            hx-swap="outerHTML">Cancel</button>
  </td>
</tr>
```

**Key insight:** `hx-include="closest tr"` collects all inputs in the row. The form-in-tr HTML issue is bypassed because HTMX sends form data directly, not via an actual `<form>` element in the `<tr>`.

---

### Pattern 8: Cookie Auth for UI Routes

**What:** The UI log routes (under `/log/`) require cookie JWT auth, same as admin UI.

```python
# Source: existing app/auth/dependencies.py pattern

# Add to dependencies.py (or reuse existing):
async def get_current_operator_callsign_cookie(
    user: User = Depends(get_current_user_cookie),
) -> str:
    """Cookie-auth version of callsign injection for UI routes."""
    return user.callsign
```

**URL prefix decision:** `/log/` for UI routes, `/api/qsos/` for REST API routes. These are distinct namespaces so exception handler redirect logic (`/admin/ui/` → login) needs extension to cover `/log/`.

---

### Anti-Patterns to Avoid

- **Beanie typed `set()` for ADIF extra fields:** `await qso.set({QSO.CALL: ...})` only works for declared model fields. For `model_extra` ADIF keys use `await qso.update({"$set": {...}})` with the exact MongoDB field name.
- **Using `is_deleted` in raw `$set`:** The Python attribute is `is_deleted`, but MongoDB stores it as `_deleted`. In raw `{"$set": ...}` dicts, always use `_deleted` (the serialization alias).
- **Storing `operator_callsign` instead of `_operator` in raw queries:** Same alias issue — raw MongoDB queries use `_operator`, Python code uses `operator_callsign`.
- **Taking callsign from POST body:** `get_current_operator_callsign` (Bearer) or `get_current_operator_callsign_cookie` (cookie) are the only sources of truth.
- **Naive datetime storage:** Always attach `timezone.utc` before storing. After reading from MongoDB, call `from_mongo_dt()` to re-attach UTC tzinfo.
- **Using `find_active()` for everything:** `find_active()` returns a list (no sort/skip/limit). For paginated queries, use `QSO.find({"_operator": op, "_deleted": False})` query builder directly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pagination offset | Custom slice logic | `.skip(n).limit(n)` on Beanie FindMany | Correct, async, MongoDB pushdown |
| Total count | Python `len(all_results)` | `await query.count()` | Separate count query; no full load |
| Date range filter | Python-side filter loop | MongoDB `$gte/$lte` in query dict | Index-leveraged, runs in MongoDB |
| Delete confirmation UI | JS modal library | `hx-confirm` attribute | Native browser confirm(), no deps |
| Edit-in-place | Full page reload | HTMX edit-row pattern | Partial swap, no JS |
| Duplicate window check | Fetch all QSOs and scan | MongoDB range query with timedelta | Efficient, index-backed |

---

## Common Pitfalls

### Pitfall 1: Serialization Alias vs Python Attribute in Raw Dicts

**What goes wrong:** `await qso.update({"$set": {"is_deleted": True}})` stores the Python name, not the MongoDB alias. The document then has both `is_deleted` (new) and `_deleted` (existing).

**Why it happens:** Raw `$set` dicts bypass Pydantic serialization. Beanie's alias mapping only applies when Beanie does the serialization.

**How to avoid:** In raw `$set` dicts, always use MongoDB field names: `{"$set": {"_deleted": True}}` and `{"$set": {"_operator": callsign}}`.

**Warning signs:** After PATCH, fetching the document shows mismatched field names, or `find_active()` returns soft-deleted records.

---

### Pitfall 2: `find_active()` Returns List, Not Query Builder

**What goes wrong:** `QSO.find_active(operator)` calls `to_list()` internally and returns a `list[QSO]`. Calling `.sort()`, `.skip()`, `.limit()` on a list raises AttributeError.

**Why it happens:** `find_active()` is a convenience method for simple fetches, not the paginated query builder.

**How to avoid:** For paginated log view, use `QSO.find({"_operator": operator, "_deleted": False})` directly, then chain `.sort()`, `.skip()`, `.limit()`.

**Warning signs:** `AttributeError: 'list' object has no attribute 'sort'`.

---

### Pitfall 3: Naive Datetime in Duplicate Window Query

**What goes wrong:** PyMongo stores datetimes as UTC but may return them as naive (no tzinfo). Comparing a timezone-aware `window_start` against a naive stored datetime raises `TypeError: can't compare offset-naive and offset-aware datetimes`.

**Why it happens:** `from_mongo_dt()` is called when building Python objects, but not when building raw MongoDB query dicts. MongoDB itself doesn't care; the issue is in Python comparisons before the query is sent.

**How to avoid:** When building `window_start` and `window_end`, always use `datetime.now(tz=timezone.utc)` or ensure `qso_date_utc` is timezone-aware before arithmetic. Store and query only UTC-aware datetimes.

**Warning signs:** `TypeError` on `timedelta` arithmetic, or duplicate check silently fails because stored datetimes are naive.

---

### Pitfall 4: Phase 4 Import Compatibility — Keep POST Body as ADIF Passthrough

**What goes wrong:** Phase 4 import will need to batch-POST QSOs parsed from an ADIF file. If the POST body schema validates/rejects unknown ADIF fields, import will fail or require a different endpoint.

**Why it happens:** If `QSOCreateRequest` uses `model_config = ConfigDict(extra="forbid")`, any field not declared is rejected.

**How to avoid:** Use `extra="allow"` on the request model. Phase 4 will send ADIF field dicts directly through the same `/api/qsos/` endpoint. Document this constraint in the router's docstring.

---

### Pitfall 5: HTMX Partial Response Must Return Correct HTTP Status

**What goes wrong:** HTMX 2.x by default does NOT swap on 4xx/5xx responses. If the server returns 409 for duplicate, HTMX ignores the response body entirely and nothing is shown.

**Why it happens:** HTMX 2.0 changed behavior — non-2xx responses are not swapped unless `htmx.config.responseHandling` is configured, or the response includes `HX-Reswap` header.

**How to avoid:** Two options:
1. Return HTTP 200 with a warning body (preferred for simplicity) — server signals warning state via body content, not HTTP status.
2. Return 4xx with `HX-Reswap: innerHTML` and `HX-Retarget: #warning-div` response headers.

For the duplicate warning flow: return 200 with warning HTML — the form target gets the warning partial. User sees it and can confirm or cancel.

---

### Pitfall 6: conftest.py Constraint

**What goes wrong:** Plans that add fixtures to `tests/conftest.py` break isolation — the comment at line 6 explicitly says "Plans 01-03 and 01-04 must NOT modify it."

**Why it happens:** conftest.py is owned by plan 01-02.

**How to avoid:** Phase 3 tests must add their own fixtures in their own test files (local pytest fixtures), not in conftest.py. They can use a separate `qso_db` fixture (similar to `auth_db`) declared locally.

---

## Code Examples

Verified patterns from project codebase and official sources:

### Beanie Paginated Find with Raw Dict Filter
```python
# Source: beanie-odm.dev/tutorial/finding-documents/
query = {"_operator": operator, "_deleted": False}
total = await QSO.find(query).count()
items = await QSO.find(query).sort("-qso_date_utc").skip(offset).limit(page_size).to_list()
```

### Beanie Update with Raw $set (works for model_extra ADIF fields)
```python
# Source: beanie-odm.dev/tutorial/updating-&-deleting/
await qso.update({"$set": {"COMMENT": "new comment", "NOTES": "extra"}})
# Also for soft delete using MongoDB alias:
await qso.update({"$set": {"_deleted": True}})
```

### Duplicate Detection Window Query
```python
# Source: pymongo datetime docs + project utils pattern
from datetime import timedelta
window_start = qso_date_utc - timedelta(minutes=2)
window_end = qso_date_utc + timedelta(minutes=2)
dup = await QSO.find_one({
    "_operator": operator,
    "CALL": call,
    "BAND": band,
    "MODE": mode,
    "_deleted": False,
    "qso_date_utc": {"$gte": window_start, "$lte": window_end},
})
```

### ADIF QSO_DATE + TIME_ON → UTC datetime
```python
# Source: ADIF spec (adif.org) — QSO_DATE=YYYYMMDD, TIME_ON=HHMM or HHMMSS
from datetime import datetime, timezone

def parse_adif_datetime(qso_date: str, time_on: str) -> datetime:
    date_part = datetime.strptime(qso_date, "%Y%m%d").date()
    if len(time_on) == 4:
        time_part = datetime.strptime(time_on, "%H%M").time()
    else:
        time_part = datetime.strptime(time_on, "%H%M%S").time()
    return datetime.combine(date_part, time_part, tzinfo=timezone.utc)
```

### HTMX OOB Swap for Warning Banner
```html
<!-- Server returns this as the full response body (status 200) -->
<!-- Primary swap goes into #qso-result (the form's hx-target) -->
<div class="warning-msg" id="dup-warning">
  Duplicate: {{ dup.CALL }} on {{ dup.BAND }}/{{ dup.MODE }}
  logged {{ minutes_ago }} min ago.
  <button hx-post="/log/qsos?force=true"
          hx-include="#qso-form"
          hx-target="#qso-result">Save Anyway</button>
</div>
<!-- OOB: table prepend not needed for warnings; use primary target -->
```

### hx-confirm for Soft Delete (no JS required)
```html
<!-- Source: htmx.org/docs/ -->
<button hx-delete="/log/qsos/{{ qso.id }}"
        hx-target="#qso-{{ qso.id }}"
        hx-swap="outerHTML"
        hx-confirm="Delete this QSO? It can be recovered by an admin.">
  Delete
</button>
```

### FastAPI PATCH Endpoint — Partial Update Pattern
```python
# Source: fastapi.tiangolo.com/tutorial/body-updates/
@router.patch("/api/qsos/{qso_id}")
async def patch_qso(
    qso_id: str,
    body: Dict[str, Any],  # arbitrary ADIF fields
    operator: str = Depends(get_current_operator_callsign),
):
    qso = await QSO.get(qso_id)
    if qso is None or qso.operator_callsign != operator or qso.is_deleted:
        raise HTTPException(status_code=404, detail="QSO not found")

    # Strip immutable fields
    for protected in ("_operator", "operator_callsign", "_deleted", "is_deleted", "_id"):
        body.pop(protected, None)

    if body:
        await qso.update({"$set": body})
    return {"id": str(qso.id), "updated": list(body.keys())}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HTMX 1.x non-2xx response swap | HTMX 2.x requires `HX-Reswap` header or 2xx for swap | HTMX 2.0 (2024) | Must return 200 for duplicate warning HTML |
| Beanie 1.x `update_one` | Beanie 2.x `.update({"$set": ...})` on document | Beanie 2.x | Raw $set on instance works |
| `model.dict()` Pydantic v1 | `model.model_dump(exclude_unset=True)` Pydantic v2 | Pydantic v2 | `.dict()` deprecated |

---

## ADIF Field Reference for Phase 3

Standard ADIF values relevant to the required form fields:

**Required web form fields (QSO-01):** CALL, QSO_DATE, TIME_ON, BAND, FREQ, MODE, RST_SENT, RST_RCVD

**BAND enumeration (common values):** 160m, 80m, 60m, 40m, 30m, 20m, 17m, 15m, 12m, 10m, 6m, 2m, 70cm (lowercase per ADIF spec; most loggers also accept uppercase)

**MODE enumeration (common values):** CW, SSB, AM, FM, FT8, FT4, RTTY, PSK31, JS8, DSTAR, DIGITALVOICE

**QSO_DATE format:** YYYYMMDD (e.g., `20240115`)
**TIME_ON format:** HHMM or HHMMSS (e.g., `1430` or `143059`) — UTC always

**Source:** ADIF spec adif.org/316/ADIF_316.htm (released 2025)

---

## Open Questions

1. **Operator UI login endpoint for `/log/` routes**
   - What we know: Admin UI uses `/admin/ui/login`. Operator accounts exist in Phase 2.
   - What's unclear: Should operators log in via the same `/admin/ui/login` page (role check would need to allow "operator"), or a separate `/log/login` page?
   - Recommendation: Add a separate `/log/login` route for operator login. Admin login checks `role == "admin"` — operators cannot log in there. Keep them separate.

2. **Exception handler redirect for `/log/` routes**
   - What we know: Exception handler in main.py redirects 401/403 on `/admin/ui/*` to `/admin/ui/login`.
   - What's unclear: Phase 3 UI routes under `/log/` need the same redirect to `/log/login`.
   - Recommendation: Extend the exception handler condition to also cover `/log/` prefix → redirect to `/log/login`.

3. **QSO list response format for REST API vs UI**
   - What we know: REST API GET should return JSON; UI GET should return HTML partial.
   - What's unclear: Should the REST `GET /api/qsos/` return all ADIF extra fields or just declared fields?
   - Recommendation: Return full `model_dump(by_alias=True)` including `model_extra` for API responses. UI needs only display fields.

4. **ADIF BAND case sensitivity in MongoDB**
   - What we know: ADIF spec allows case-insensitive band enumeration. Prior decision: ADIF stored verbatim.
   - What's unclear: If a user submits "20M" via API and another submits "20m" via form, the compound unique index treats them as different values.
   - Recommendation: Normalize BAND and MODE to uppercase on ingest (both API and form). Document this normalization decision.

---

## Sources

### Primary (HIGH confidence)
- https://beanie-odm.dev/tutorial/finding-documents/ — find(), sort(), skip(), limit(), count() patterns
- https://beanie-odm.dev/tutorial/updating-&-deleting/ — set(), update(), delete() patterns with code examples
- https://beanie-odm.dev/api-documentation/query/ — count() and sort() method signatures
- https://htmx.org/attributes/hx-swap-oob/ — OOB swap syntax and examples
- https://htmx.org/headers/hx-trigger/ — HX-Trigger response header syntax
- https://htmx.org/examples/edit-row/ — edit row in-place pattern (official HTMX example)
- https://fastapi.tiangolo.com/tutorial/body-updates/ — PATCH partial update with exclude_unset

### Secondary (MEDIUM confidence)
- https://www.mongodb.com/docs/languages/python/pymongo-driver/current/data-formats/dates-and-times/ — datetime UTC handling in pymongo
- https://adif.org/316/ADIF_316.htm — current ADIF spec (2025) for band/mode enumerations and date/time formats
- https://htmx.org/docs/ — HTMX 2.x behavior changes (non-2xx swap behavior)

### Tertiary (LOW confidence)
- WebSearch results on ADIF BAND/MODE values — cross-verified with adif.org link above

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, patterns from official docs
- Architecture: HIGH — patterns verified against existing codebase and official HTMX/Beanie docs
- Pitfalls: HIGH — alias issue verified by reading existing QSO model code; HTMX 2.x swap issue from official docs
- ADIF field formats: HIGH — from current ADIF spec (2025 release)
- Open questions: MEDIUM — identified from codebase analysis, recommendations are reasonable but not verified against a running system

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (stable libraries; HTMX/Beanie unlikely to change breaking behavior)
