# Phase 13: OpenAPI Schema Cleanup - Research

**Researched:** 2026-04-04
**Domain:** FastAPI OpenAPI schema annotation — response models, error responses, route exclusion, custom content types
**Confidence:** HIGH

---

## Summary

This phase is pure annotation work: no new dependencies, no runtime behavior changes. Every requirement maps to a specific FastAPI decorator parameter that already exists in the version the project uses (`fastapi>=0.135.0`). The four techniques in play are `response_model` on the decorator, `responses={N: {"model": ...}}` for error status codes, `include_in_schema=False` to hide browser-only routes, and `responses={200: {"content": {"text/plain": {}}}}` combined with `response_class=StreamingResponse` to document the ADIF export endpoint. No library installs are needed.

The tricky constraint is that the QSO endpoints currently return untyped `dict` from `_qso_to_dict()` and `_qso_to_view_dict()`. The phase decision is that **runtime serialization does NOT change** — only the OpenAPI annotation changes. This means using `response_model=QSOResponse` on the decorator while the function still returns a plain dict. FastAPI's response model validation runs at response time, not at function return type; as long as the dict shape matches the model, it works. A concrete `QSOResponse` Pydantic model must be defined that mirrors what `_qso_to_dict()` already returns.

The ADIF import endpoint returns a dict from `process_import()`. A concrete `ADIFImportReport` Pydantic model must be defined and used as `response_model`. The export endpoint uses `StreamingResponse` and cannot use `response_model` at all — the documentation comes entirely from the `responses` decorator parameter.

**Primary recommendation:** Work file by file in dependency order — define models first (qso/schemas.py or inline in router), then annotate decorators, then exclude UI routers last since they are the most mechanical step.

---

## Standard Stack

### Core (already installed — no new installs needed)

| Library | Version in project | Purpose | Why Standard |
|---------|-------------------|---------|--------------|
| fastapi | >=0.135.0 | Decorator parameters: `response_model`, `responses`, `include_in_schema`, `openapi_extra` | All annotation features are first-party FastAPI |
| pydantic | >=2.0 | `BaseModel` for typed response schemas; `Field(description=...)` for field annotations | FastAPI's schema generation reads Pydantic model JSON Schema |

**Installation:** None required.

---

## Architecture Patterns

### Pattern 1: Typed response model on QSO endpoints

**What:** Add a `QSOResponse` Pydantic model that mirrors the dict shape returned by `_qso_to_dict()`. Attach it as `response_model=QSOResponse` on each QSO decorator. The function body continues to return a plain dict — FastAPI validates and serializes via the model at response time.

**When to use:** Any endpoint that returns `-> dict` but has a known stable shape.

```python
# Source: https://fastapi.tiangolo.com/tutorial/response-model/
from pydantic import BaseModel
from typing import Optional

class QSOResponse(BaseModel):
    id: str
    CALL: str
    BAND: Optional[str] = None
    MODE: Optional[str] = None
    qso_date_utc: Optional[str] = None  # ISO string, not datetime
    # ... plus any other fields _qso_to_dict() emits

@router.post("/", status_code=201, response_model=QSOResponse)
async def create_qso(...) -> dict:
    ...
    return _qso_to_dict(qso)  # unchanged
```

**Critical detail:** `_qso_to_dict()` converts `qso_date_utc` to an ISO string. The `QSOResponse` model should declare it as `Optional[str]`, not `Optional[datetime]`, to match what the function actually returns without triggering Pydantic coercion errors.

**For `list_qsos`:** The response model is a wrapper:
```python
class QSOListResponse(BaseModel):
    items: list[QSOResponse]
    total: int
    page: int
    page_size: int

@router.get("/", response_model=QSOListResponse)
```

### Pattern 2: Declaring additional error responses (409)

**What:** Use the `responses` dict parameter on the decorator to declare non-2xx response schemas. FastAPI generates a `$ref` to the model's JSON Schema in the OpenAPI components.

**When to use:** Any endpoint that raises `HTTPException` with a non-default status code (409, 404, etc.) and you want Swagger to show the error schema.

```python
# Source: https://fastapi.tiangolo.com/advanced/additional-responses/
from pydantic import BaseModel

class DuplicateQSOError(BaseModel):
    duplicate: bool
    existing_id: str
    existing_call: str
    existing_band: str
    existing_mode: str
    existing_date: Optional[str] = None

@router.post(
    "/",
    status_code=201,
    response_model=QSOResponse,
    responses={
        409: {
            "model": DuplicateQSOError,
            "description": "Duplicate QSO detected within ±2 min window. Use force=true to override.",
        }
    },
)
async def create_qso(
    body: QSOCreateRequest,
    force: bool = Query(False, description="Override duplicate detection and force insert"),
    ...
) -> dict:
```

**Note on `force` query param description:** The `description=` argument on `Query()` already adds documentation to the parameter in Swagger. The phase requirement is to add this description — it belongs on the `Query()` call, not in `responses`.

### Pattern 3: Excluding HTMX routes from OpenAPI schema

**What:** Add `include_in_schema=False` to every route decorator in the UI routers. Can be applied at the `APIRouter` constructor level (applies to all routes in that router) or per-route.

**Router-level exclusion (preferred — single change covers all routes):**

```python
# Source: https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/
# In app/main.py or in the router file itself:
app.include_router(qso_ui_router, include_in_schema=False)
app.include_router(ui_router, include_in_schema=False)  # admin UI
```

OR at the APIRouter constructor:
```python
ui_router = APIRouter(prefix="/log", tags=["log-ui"], include_in_schema=False)
```

**Important:** Setting `include_in_schema=False` at `app.include_router()` call in `main.py` is the cleanest approach — it requires no changes to the ui_router files themselves and makes the intent explicit at mount time.

Routers to exclude:
- `app/qso/ui_router.py` — prefix `/log`, all routes are HTMX/cookie-auth
- `app/admin/ui_router.py` — prefix `/admin/ui`, all routes are HTMX/cookie-auth
- `app/feed/router.py` — prefix `/feed`, SSE endpoint uses cookie auth (not Bearer)

### Pattern 4: Documenting StreamingResponse (ADIF export)

**What:** `StreamingResponse` cannot use `response_model` (FastAPI would try to validate the generator). Use the `responses` parameter to declare the 200 response content type and description, combined with `response_class=StreamingResponse`.

```python
# Source: https://fastapi.tiangolo.com/advanced/additional-responses/
# Verified in: https://github.com/fastapi/fastapi/discussions/3881
from fastapi.responses import StreamingResponse

@router.get(
    "/export",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/plain": {}},
            "description": "ADIF (.adi) file download for the operator's full logbook.",
        }
    },
)
async def export_adif(...):
    ...
    return StreamingResponse(...)  # unchanged
```

### Pattern 5: ADIFImportReport response model

**What:** Define a Pydantic model for the import report dict returned by `process_import()`. Annotate the import endpoint with `response_model=ADIFImportReport`.

```python
from pydantic import BaseModel

class ADIFRecordAccepted(BaseModel):
    record_index: int
    call: str
    id: str

class ADIFRecordDuplicate(BaseModel):
    record_index: int
    call: str
    existing_id: str

class ADIFRecordError(BaseModel):
    record_index: int
    call: str
    error: str

class ADIFImportReport(BaseModel):
    total_records: int
    accepted: list[ADIFRecordAccepted]
    duplicates: list[ADIFRecordDuplicate]
    errors: list[ADIFRecordError]

@router.post("/import", response_model=ADIFImportReport)
async def import_adif(...):
```

**Critical detail:** The `errors` list in `process_import()` can include items from `parse_errors` (returned by `parse_adi()`) which may not have `record_index`. Verify the shape of parse errors matches `ADIFRecordError` before committing to the model. If parse errors have a different shape, use `list[dict]` or a union type for `errors`.

### Pattern 6: Field descriptions for ADIF request fields

**What:** Add `Field(description=...)` to each field in `QSOCreateRequest` to document ADIF format conventions in Swagger.

```python
# Source: Pydantic v2 docs — Field is standard
from pydantic import BaseModel, Field

class QSOCreateRequest(BaseModel):
    CALL: str = Field(description="Callsign of the contacted station (e.g., W1AW)")
    QSO_DATE: str = Field(description="UTC date of QSO in YYYYMMDD format (e.g., 20240115)")
    TIME_ON: str = Field(description="UTC start time in HHMM or HHMMSS format (e.g., 1430 or 143045)")
    BAND: str = Field(description="Amateur band using ADIF designators (e.g., 40m, 20m, 2m)")
    MODE: str = Field(description="Operating mode (e.g., SSB, CW, FT8, FM)")
    FREQ: Optional[str] = Field(None, description="Frequency in MHz (e.g., 14.225)")
    RST_SENT: Optional[str] = Field(None, description="RST signal report sent to contacted station")
    RST_RCVD: Optional[str] = Field(None, description="RST signal report received from contacted station")
```

**Format convention notes from phase requirements:**
- `QSO_DATE`: YYYYMMDD
- `TIME_ON`: HHMM or HHMMSS
- `BAND`: ADIF band designators (40m, 20m, etc.)
- `OPERATOR` vs `STATION_CALLSIGN`: OPERATOR is the person operating, STATION_CALLSIGN is the station's call (auto-stamped from profile — not in this request model but should be documented in endpoint description)

### Pattern 7: DELETE soft-delete description

**What:** Expand the `delete_qso` docstring (which FastAPI uses as the Swagger description) to explicitly document soft-delete semantics.

```python
@router.delete("/{qso_id}", status_code=204)
async def delete_qso(...) -> None:
    """Soft-delete a QSO by ID.

    Marks the record deleted=True in MongoDB — the document is NOT removed.
    Soft-deleted QSOs are excluded from all list and get endpoints.
    Returns 204 No Content on success. Returns 404 if not found, not owned,
    or already deleted.
    """
```

### Anti-Patterns to Avoid

- **Changing `_qso_to_dict()` or `_qso_to_view_dict()`:** The phase decision explicitly locks runtime serialization unchanged — only decorator annotations change.
- **Using `response_model` on the export endpoint:** `StreamingResponse` generators cannot be validated by Pydantic. Use `responses=` parameter instead.
- **Per-route `include_in_schema=False` on UI routers:** Requires touching every decorator. Use `app.include_router(..., include_in_schema=False)` in `main.py` instead.
- **Defining `QSOResponse` with `datetime` for `qso_date_utc`:** The serializer converts it to an ISO string before returning. Model must match what the function actually returns (`Optional[str]`).
- **Trusting that the `errors` list in `ADIFImportReport` is uniform:** Parse errors from `parse_adi()` may have a different structure than per-record errors. Inspect `parser.py` output shape before finalizing the model.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Hiding HTMX routes | Per-route decorating with `include_in_schema=False` | `app.include_router(..., include_in_schema=False)` | One change in main.py vs. touching every route |
| Error schema docs | Inline JSON in docstring | `responses={409: {"model": ErrorModel}}` | FastAPI generates proper `$ref` components |
| StreamingResponse docs | `openapi_extra` override of full responses block | `responses={200: {"content": {"text/plain": {}}}}` + `response_class=StreamingResponse` | Simpler, standard, documented approach |

**Key insight:** Every requirement in this phase has a first-party FastAPI solution. No custom middleware, schema overrides, or schema-generation hooks are needed.

---

## Common Pitfalls

### Pitfall 1: response_model validation fails at runtime because dict shape doesn't match model

**What goes wrong:** Adding `response_model=QSOResponse` but the dict returned by `_qso_to_dict()` has a field the model doesn't declare, or misses a required field.
**Why it happens:** `_qso_to_dict()` uses `model_dump(by_alias=True)` which can emit extra fields from `model_extra` (arbitrary ADIF fields stored via `extra="allow"`).
**How to avoid:** Either use `response_model_exclude_unset=True` on the decorator, OR define `QSOResponse` with `model_config = ConfigDict(extra="ignore")` so extra fields are silently dropped during serialization. The `extra="ignore"` approach is cleaner.
**Warning signs:** HTTP 500 during tests, `ValueError` from Pydantic in response serialization.

### Pitfall 2: include_in_schema=False at APIRouter level vs. app.include_router level

**What goes wrong:** Setting `include_in_schema=False` on the `APIRouter()` constructor in the ui_router file doesn't always propagate if the router is included with `include_in_schema=True` (the default) at mount time.
**Why it happens:** `app.include_router()` call parameters take precedence in some FastAPI versions.
**How to avoid:** Set `include_in_schema=False` in the `app.include_router(...)` call in `main.py`. This is authoritative and version-stable.
**Warning signs:** HTMX routes still appearing in `/openapi.json` after applying `include_in_schema=False` only to the router constructor.

### Pitfall 3: Feed router also uses cookie auth — may need exclusion

**What goes wrong:** The `/feed/station` SSE endpoint uses `get_current_operator_callsign_cookie` (cookie auth, not Bearer). If it appears in Swagger, it shows as a Bearer-auth endpoint but won't work from Swagger UI.
**Why it happens:** Phase description mentions `/log/*` and `/admin/ui/*` but the feed router at `/feed` also uses cookie auth.
**How to avoid:** Confirm with phase requirements — OAPI-02 specifies "HTMX browser routes (`/log/*`, `/admin/ui/*`)" only. The feed router may be intentionally left in or out — verify explicitly. If left in, it will appear with incorrect auth documentation.

### Pitfall 4: ADIFImportReport errors field shape mismatch

**What goes wrong:** `parse_adi()` returns parse errors that may not have `record_index` or may have a different `call` key value. If `ADIFImportReport.errors` is `list[ADIFRecordError]`, Pydantic will reject parse error dicts that don't match.
**Why it happens:** The `errors` list in `process_import()` is initialized from `list(parse_errors)` which comes directly from the parser — a different code path than per-record errors.
**How to avoid:** Read `app/adif/parser.py` before writing `ADIFRecordError`. Use `list[dict]` for errors if the shape is not uniform, or use a union type.
**Warning signs:** HTTP 500 on import endpoint after adding `response_model`.

### Pitfall 5: `force` query param description needs to be on Query(), not in responses

**What goes wrong:** Confusing where the `force=true` documentation lives. OAPI-03 says "force=true query parameter with description" — this description goes on `Query(False, description="...")` not in the `responses` dict.
**Why it happens:** The requirement bundles 409 response and force param in the same acceptance criterion.
**How to avoid:** Separate the two: `responses={409: {...}}` for the error schema, `force: bool = Query(False, description="Override duplicate detection and force insert")` for the query param.

---

## Code Examples

Verified patterns from official sources:

### Declare a typed list response

```python
# Source: https://fastapi.tiangolo.com/tutorial/response-model/
@router.get("/", response_model=QSOListResponse)
async def list_qsos(...) -> dict:
    # ... existing logic unchanged ...
    return {
        "items": [_qso_to_dict(q) for q in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
```

### Declare 409 conflict response

```python
# Source: https://fastapi.tiangolo.com/advanced/additional-responses/
@router.post(
    "/",
    status_code=201,
    response_model=QSOResponse,
    responses={
        409: {
            "model": DuplicateQSOError,
            "description": "Duplicate QSO detected within ±2 min window. Use force=true to override.",
        }
    },
)
```

### Exclude router from schema at mount time

```python
# Source: https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/
# In app/main.py — single change excludes all routes under the router
app.include_router(qso_ui_router, include_in_schema=False)
app.include_router(ui_router, include_in_schema=False)   # admin UI
```

### Document StreamingResponse with text/plain

```python
# Source: https://github.com/fastapi/fastapi/discussions/3881
# Source: https://fastapi.tiangolo.com/advanced/additional-responses/
@router.get(
    "/export",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/plain": {}},
            "description": "ADIF (.adi) file download for the operator's full logbook.",
        }
    },
)
async def export_adif(...):
    return StreamingResponse(...)   # unchanged
```

### Field descriptions in Pydantic v2

```python
# Source: Pydantic v2 — Field() is standard; Field(description=) emits JSON Schema description
from pydantic import Field

class QSOCreateRequest(BaseModel):
    QSO_DATE: str = Field(description="UTC date in YYYYMMDD format")
    TIME_ON: str = Field(description="UTC start time in HHMM or HHMMSS format")
    BAND: str = Field(description="ADIF band designator, e.g. 40m, 20m, 2m")
```

---

## What Needs Inspection Before Planning Tasks

These items require reading actual code before the planner can finalize task boundaries:

### 1. Shape of parse errors from `parse_adi()`
- Read `app/adif/parser.py` to confirm the exact dict structure of parse errors
- Determines whether `ADIFImportReport.errors` can be `list[ADIFRecordError]` or must be `list[dict]`

### 2. Full field list emitted by `_qso_to_dict()`
- The function is in `app/qso/router.py` (already read)
- It emits: `id`, `CALL`, `BAND`, `MODE`, `qso_date_utc` (as ISO string), plus all `model_extra` fields
- `model_extra` fields vary per record (arbitrary ADIF fields) — `QSOResponse` must handle this
- **Recommended approach:** Declare `QSOResponse` with only the stable declared fields and `model_config = ConfigDict(extra="ignore")` so extra ADIF fields don't cause validation errors

### 3. Whether the feed SSE router needs exclusion
- OAPI-02 requirement explicitly lists `/log/*` and `/admin/ui/*`
- `/feed/station` uses cookie auth (`get_current_operator_callsign_cookie`) — same pattern as excluded routes
- Planner should clarify: exclude feed router or leave it?

---

## File Map: What Changes Where

| File | Changes Needed |
|------|---------------|
| `app/qso/router.py` | Add `QSOResponse`, `QSOListResponse`, `DuplicateQSOError` models; annotate all 5 decorators with `response_model` and/or `responses`; add `Field(description=...)` to `QSOCreateRequest`; expand `delete_qso` docstring |
| `app/adif/router.py` | Add `ADIFImportReport` model (and sub-models); annotate import decorator with `response_model`; annotate export decorator with `response_class=StreamingResponse` and `responses` |
| `app/main.py` | Add `include_in_schema=False` to `app.include_router()` calls for `qso_ui_router` and `ui_router` (admin UI) |
| `app/adif/parser.py` | READ ONLY — verify parse error dict shape for `ADIFImportReport` |

No changes needed to:
- `app/qso/models.py` — Beanie document model, not a response schema
- `app/qso/ui_router.py` — excluded via `main.py` include_router call
- `app/admin/ui_router.py` — excluded via `main.py` include_router call
- `app/profile/router.py` — already has `response_model=ProfileResponse` on both endpoints
- `app/auth/router.py` — no response model annotation needed (simple dicts)

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `-> dict` return with no annotation | `response_model=SomeModel` on decorator, function still returns dict | FastAPI validates output against model at response time; no runtime change to serialization logic |
| Hiding routes via middleware | `include_in_schema=False` on decorator or `include_router()` | First-party, zero overhead, cleanest approach |
| Custom OpenAPI schema hook for StreamingResponse | `responses={200: {"content": {"text/plain": {}}}}` + `response_class` | Supported natively since FastAPI 0.95+; no workarounds needed |

---

## Open Questions

1. **Feed router exclusion (OAPI-02 scope)**
   - What we know: OAPI-02 lists `/log/*` and `/admin/ui/*` explicitly
   - What's unclear: Whether `/feed/station` (SSE, cookie auth) should also be excluded
   - Recommendation: Planner should treat it as in-scope for exclusion given it uses cookie auth; if not, it will appear in Swagger with Bearer auth shown but unusable from Swagger UI

2. **ADIFImportReport errors field shape**
   - What we know: `errors` is built from both parse errors and per-record validation errors
   - What's unclear: Whether parse errors from `parse_adi()` have `record_index` and `call` keys
   - Recommendation: Read `app/adif/parser.py` in first planning task; if shapes differ, use `list[dict]` for errors or a union type

3. **model_extra in QSOResponse**
   - What we know: `_qso_to_dict()` emits all model_extra fields (arbitrary ADIF) in the response dict
   - What's unclear: Whether QSOResponse should expose these as `model_config = ConfigDict(extra="allow")` or silently drop them with `extra="ignore"`
   - Recommendation: Use `extra="ignore"` — the schema purpose is to document the stable declared fields; extra ADIF passthrough is an implementation detail, not part of the typed contract

---

## Sources

### Primary (HIGH confidence)
- [FastAPI — Additional Responses in OpenAPI](https://fastapi.tiangolo.com/advanced/additional-responses/) — `responses` dict parameter, error model declaration, text/plain content type pattern
- [FastAPI — Path Operation Advanced Configuration](https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/) — `include_in_schema`, `openapi_extra`
- [FastAPI — Response Model](https://fastapi.tiangolo.com/tutorial/response-model/) — `response_model` decorator parameter

### Secondary (MEDIUM confidence)
- [FastAPI GitHub Discussion #3881](https://github.com/fastapi/fastapi/discussions/3881) — Documenting StreamingResponse pattern; `response_class=StreamingResponse` + `responses` approach confirmed by multiple community members

### Codebase (HIGH confidence — read directly)
- `app/qso/router.py` — all QSO endpoints, `QSOCreateRequest`, `_qso_to_dict()` shape
- `app/adif/router.py` — import/export endpoints, `process_import()` return shape
- `app/qso/ui_router.py` — HTMX routes to exclude at `/log`
- `app/admin/ui_router.py` — HTMX routes to exclude at `/admin/ui`
- `app/feed/router.py` — SSE route using cookie auth
- `app/main.py` — `app.include_router()` call sites
- `app/profile/router.py` — example of already-annotated endpoints with `response_model`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all annotation features are first-party FastAPI, no new dependencies
- Architecture patterns: HIGH — `response_model`, `responses`, `include_in_schema` all verified against official docs
- Pitfalls: HIGH — based on direct code inspection (model_extra, _qso_to_dict shape, parse_errors source)
- ADIFImportReport errors sub-shape: MEDIUM — `parser.py` not yet read; shape assumed from `process_import()` code

**Research date:** 2026-04-04
**Valid until:** 2026-07-04 (stable FastAPI APIs; `include_in_schema`, `response_model`, `responses` have been stable since FastAPI 0.95+)
