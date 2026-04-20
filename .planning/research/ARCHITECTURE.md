# Architecture Research

**Domain:** QSO sorting + entry timestamp integration — v2.5 milestone
**Researched:** 2026-04-20
**Confidence:** HIGH (derived from direct reading of all relevant source files)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Insert Paths (4)                          │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  REST API    │   UI Form    │  UDP Server  │  ADIF Import   │
│  router.py   │  ui_router   │  server.py   │  service.py    │
│              │  .py         │              │  (via qso/svc) │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬─────────┘
       │              │              │              │
       └──────────────┴──────────────┴──────────────┘
                              │
                    build_qso_dict()
                    app/qso/service.py      <- single stamp point
                              │
                    QSO(**qso_dict).insert()
                              │
                    app/qso/models.py       <- default_factory stamps _created_at here
                              │
                    MongoDB qsos collection
                              │
               ┌──────────────┴──────────────────┐
               │                                 │
      get_qso_page()                   SSE change stream
      (filtered, sorted, paginated)    app/feed/manager.py
               │
      _qso_to_view_dict()
      (render-time enrichment)
               │
      log_table.html / qso_row.html
```

### Component Responsibilities

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| `app/qso/models.py` | QSO Beanie Document, MongoDB indexes | Declares typed fields; extra ADIF via `model_extra` |
| `app/qso/service.py::build_qso_dict()` | Constructs QSO dict, stamps operator + profile | All 4 insert paths call this; does NOT set `_created_at` |
| `app/qso/service.py::get_qso_page()` | Paginated, filtered, sorted reads | Beanie `.sort(sort_by)` accepts `"-field"` prefix for descending |
| `app/qso/ui_router.py::_qso_to_view_dict()` | Render-time enrichment; builds template dict | Sole place that exposes `created_at` to templates |
| `app/qso/ui_router.py::log_view()` | Assembles Jinja2 context, controls `sort` param | Passes `sort` and all filter state to both template layers |
| `templates/log/log_table.html` | Sort headers, row loop, pagination, auto-refresh sentinel | HTMX partial; `sort` value in context drives icon state |
| `templates/log/log.html` | Outer page; `#log-table` SSE swap target; JS badge/tone/indicator | Must not be touched for sort/timestamp changes |

---

## Integration: `_created_at` Field

### The Single Correct Layer

`_created_at` belongs in `app/qso/models.py` as a Beanie Document field with `default_factory`. This is the only location that ensures all four insert paths stamp the field without any caller changes.

The `default_factory` runs at `QSO()` construction time — before `.insert()` is called. Every insert path already ends with `QSO(**qso_dict)` followed by `.insert()`, so the stamp is automatic.

### Required Model Change

`app/qso/models.py` — add to the `QSO` class:

```python
from datetime import datetime, timezone

created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
    alias="_created_at",
    serialization_alias="_created_at",
)
```

The `alias`/`serialization_alias` pattern matches the existing `operator_callsign`/`is_deleted` precedent exactly. `populate_by_name=True` is already on the model config, so both `created_at` (Python attribute) and `"_created_at"` (MongoDB alias) work for construction.

Optional but recommended — add an index for efficient sort:

```python
IndexModel(
    [("_operator", pymongo.ASCENDING), ("_created_at", pymongo.DESCENDING)],
    name="operator_created_at_idx",
),
```

Without this, sorting by `_created_at` does a per-operator collection scan. For small logbooks this is acceptable.

### Required View Dict Change

`app/qso/ui_router.py::_qso_to_view_dict()` — add one line to the returned dict:

```python
d["created_at"] = qso.created_at  # datetime; for sort icon and optional tooltip
```

`created_at` is a declared Beanie field (not in `model_extra`), so `qso.created_at` is accessible directly. The template receives a `datetime` object and can use Jinja2's `strftime` or `isoformat` filter as needed.

### What Does NOT Change for Stamping

| File | Reason |
|------|--------|
| `app/qso/service.py::build_qso_dict()` | Dict constructor only; model default is the stamp layer |
| `app/qso/router.py` | `QSO(**qso_dict)` picks up `default_factory` automatically |
| `app/udp/server.py` | Same — `QSO(**qso_dict).insert()` path unchanged |
| `app/adif/router.py` | Same |
| `app/qso/service.py::import_qsos_from_bytes()` | `QSO(**qso_dict)` already present |

---

## Integration: Expanded Sort Options

### Sort Mechanism

`get_qso_page()` passes `sort_by` directly to `QSO.find(query).sort(sort_by)`. Beanie's `.sort()` accepts the MongoDB field name as a string; a leading `-` means descending. This works for both declared fields (`CALL`, `BAND`, `qso_date_utc`) and `model_extra` fields (`FREQ`, `RST_SENT`), because MongoDB stores them all as flat document keys.

### Allowlist Required

`get_qso_page()` currently accepts any `sort_by` string from query params — a minor injection risk. An explicit allowlist guard must be added:

```python
_ALLOWED_SORT_FIELDS = {
    "qso_date_utc", "-qso_date_utc",
    "CALL", "-CALL",
    "BAND", "-BAND",
    "MODE", "-MODE",
    "FREQ", "-FREQ",
    "RST_SENT", "-RST_SENT",
    "_created_at", "-_created_at",
}

if sort_by not in _ALLOWED_SORT_FIELDS:
    sort_by = "-qso_date_utc"
```

This is the only change needed in `get_qso_page()`. The function signature does not change. The `log_view()` and `list_qsos()` callers both already pass `sort_by=sort`.

### Sort Field Reference

| UI sort value | MongoDB field | Field type | Index? |
|---------------|--------------|------------|--------|
| `qso_date_utc` / `-qso_date_utc` | `qso_date_utc` | declared | compound index |
| `CALL` / `-CALL` | `CALL` | declared | compound index |
| `BAND` / `-BAND` | `BAND` | declared | compound index |
| `MODE` / `-MODE` | `MODE` | declared | no dedicated sort index |
| `FREQ` / `-FREQ` | `FREQ` | model_extra | no index |
| `RST_SENT` / `-RST_SENT` | `RST_SENT` | model_extra | no index |
| `_created_at` / `-_created_at` | `_created_at` | declared (new) | add index (recommended) |

MODE has no dedicated sort index but is in the compound index (`operator_qso_compound`). MongoDB can use this index for a sort on MODE filtered by operator, though it is less efficient than a leading-sort field. FREQ and RST_SENT sorts will scan — acceptable for small logs.

### Template Changes

`templates/log/log_table.html` — add sort headers for MODE and `_created_at`. The pattern is already established by DATE, CALL, and BAND headers. Each new header is:

1. An `<a>` element with `hx-get="/log/view?sort={% if sort == '-FIELD' %}FIELD{% else %}-FIELD{% endif %}&...filters..."`
2. Two `{% if sort == '-FIELD' %}` / `{% elif sort == 'FIELD' %}` branches showing the appropriate chevron SVG

The `_created_at` header is special: it has no corresponding `<td>` cell in `qso_row.html` (the column is hidden). The header needs a distinguishable icon (e.g., a clock) so operators can find it visually. The HTMX wiring is identical to other headers.

The `#auto-refresh-ok` sentinel condition in `log_table.html` is already correct: it fires only when `sort == '-qso_date_utc'`. Adding `_created_at` sort does not require updating this condition — any non-default sort correctly suppresses auto-refresh, which is the intended behavior.

---

## Data Flow

### Insert Path (all four routes)

```
[UI Form | REST body | UDP datagram | ADIF bytes]
    |
    v
build_qso_dict(record, operator, profile=user)
    returns: { CALL, BAND, MODE, qso_date_utc, operator_callsign, is_deleted, ... }
    does NOT include _created_at
    |
    v
QSO(**qso_dict)
    Beanie constructs Document
    default_factory sets created_at = datetime.now(utc)
    |
    v
await qso.insert()
    MongoDB document: { _operator, CALL, BAND, ..., _created_at, _deleted }
```

### Read / Sort Path

```
GET /log/view?sort=-_created_at&page=1
    |
    v
log_view() in ui_router.py
    passes sort_by="-_created_at" to get_qso_page()
    |
    v
get_qso_page()
    validates sort_by against allowlist
    QSO.find(query).sort("-_created_at").skip(0).limit(50)
    |
    v
list of QSO Beanie documents
    |
    v
_qso_to_view_dict(qso) for each result
    adds created_at to view dict
    |
    v
Jinja2 context -> log_table.html
    #auto-refresh-ok absent (non-default sort, correctly suppresses SSE reload)
    sort header for _created_at shows active chevron
    rows rendered normally (no _created_at cell visible)
```

### HTMX Sort Click Flow

```
User clicks sort header
    hx-get="/log/view?sort=-_created_at&call=&band=..."
    hx-target="#log-table"
    hx-swap="innerHTML"
    hx-push-url="true"
    |
    v
Server renders log_table.html partial
    #auto-refresh-ok absent (non-default sort)
    |
    v
HTMX swaps #log-table innerHTML
    SSE connection on #log-table container survives (SSE attrs on outer div, not in partial)
    badge and sound logic continue to work (fired before auto-refresh guard in htmx:sseMessage)
```

---

## Build Order

The dependency chain flows model → service → view dict → template. This order is strict because:
- The template depends on `sort` values being valid (enforced by service allowlist)
- The template depends on `created_at` being in the view dict (added by `_qso_to_view_dict`)
- Both of those depend on the model field existing

### Step 1: Model (foundational — nothing else can be tested without this)

`app/qso/models.py`
- Add `created_at` field with `alias="_created_at"` and `default_factory`
- Add optional `operator_created_at_idx` index

Verify: existing tests still pass. New QSO inserts should carry `_created_at` in MongoDB.

### Step 2: Service (depends on model field existing for allowlist to include it)

`app/qso/service.py`
- Add `_ALLOWED_SORT_FIELDS` set
- Add allowlist guard at top of `get_qso_page()`

Verify: `get_qso_page()` with `sort_by="-_created_at"` returns results sorted by creation time. Invalid sort values fall back to default.

### Step 3: View Dict (depends on model field existing)

`app/qso/ui_router.py::_qso_to_view_dict()`
- Add `d["created_at"] = qso.created_at`

No change to `log_view()`, `submit_qso()`, or any other handler. This is a one-line addition.

### Step 4: Template (depends on allowlist + view dict)

`templates/log/log_table.html`
- Add MODE sort header (same pattern as CALL/BAND)
- Add `_created_at` sort header with clock icon (no corresponding data cell)
- Optionally add FREQ and RST_SENT sort headers

`log.html` does not need changes.

---

## Files Changed vs Unchanged

| File | Status | Scope of Change |
|------|--------|-----------------|
| `app/qso/models.py` | **REQUIRED** | Add `created_at` field + optional index |
| `app/qso/service.py` | **REQUIRED** | Add sort allowlist guard in `get_qso_page()` |
| `app/qso/ui_router.py` | **REQUIRED** | Add `created_at` to `_qso_to_view_dict()` — one line |
| `templates/log/log_table.html` | **REQUIRED** | Add sort headers for MODE and `_created_at` |
| `app/qso/router.py` | unchanged | `QSO(**dict)` picks up model default automatically |
| `app/udp/server.py` | unchanged | Same reason |
| `app/adif/router.py` | unchanged | Same reason |
| `app/adif/service.py` (import) | unchanged | `QSO(**qso_dict)` already in place |
| `app/qso/service.py::build_qso_dict()` | unchanged | Timestamp is model layer responsibility |
| `templates/log/log.html` | unchanged | Filter form already threads `sort` via hidden input; JS is unaffected |

---

## Anti-Patterns

### Anti-Pattern 1: Setting `_created_at` inside `build_qso_dict()`

**What people do:** Add `result["created_at"] = datetime.now(timezone.utc)` inside `build_qso_dict()`.

**Why it's wrong:** `build_qso_dict()` is also called in potential update paths. Any future PATCH operation that goes through this function would silently overwrite `_created_at`. The model `default_factory` only runs at `QSO()` construction; it is never called by `.update({"$set": ...})`.

**Do this instead:** Declare on the model with `default_factory`. Factory runs only at construction; updates never touch it.

### Anti-Pattern 2: Open-ended `sort_by` string passed to MongoDB

**What people do:** Pass the raw `?sort=` query param directly to `get_qso_page()` without validation.

**Why it's wrong:** Allows sorting by any MongoDB field name, including internal fields (`_operator`, `_id`) or non-existent fields. Not a severe security risk given operator isolation, but causes unpredictable behavior and is a minor injection vector.

**Do this instead:** Allowlist in `get_qso_page()`. Fall back to `-qso_date_utc` for any unknown value.

### Anti-Pattern 3: Putting the `_created_at` sort header inside `qso_row.html`

**What people do:** Add a visible `_created_at` cell to the row partial to make the column visible, then add a sort header for it.

**Why it's wrong:** The feature spec explicitly calls `_created_at` hidden — it is a system field, not operator-facing data. Showing it clutters the table and exposes implementation details. The sort header without a data cell is the correct pattern (the feature description says "dedicated icon in the table header allows sorting by `_created_at` even though the column is hidden").

**Do this instead:** Add only the `<th>` header with a clock icon. No `<td>` in `qso_row.html`. Optionally expose the value as a tooltip on an existing visible cell (e.g., the date cell).

---

## Architectural Patterns Observed

### Pattern: Beanie `default_factory` for system timestamps

**What:** Declare the field on the Document model. Factory runs at `QSO()` construction, before `.insert()`.

**When to use:** Any system-generated field that must be set at creation time and is invisible to insert callers. Zero changes to service or router layers.

**Trade-off:** Timestamp is Python wall-clock time, not MongoDB server time. For self-hosted single-node deployments, acceptable. For distributed deployments with multiple app servers, clock skew is a risk — use MongoDB `$currentDate` instead.

### Pattern: Template-level sort state via string comparison

**What:** `ctx["sort"]` is a plain string. Template uses `{% if sort == '-FIELD' %}` to render active chevrons. Router echoes the sort value back from query params without transformation.

**When to use:** Sort state is reflected in the URL (via `hx-push-url="true"`). URL and template stay in sync automatically. Browser back/forward navigation works correctly.

**Trade-off:** Adding a sortable column requires touching both the service allowlist and the template header section. These are the only two places that must stay in sync — a small, acceptable cost.

### Pattern: `_qso_to_view_dict()` as the sole template data gate

**What:** All template rendering goes through `_qso_to_view_dict()` in `ui_router.py`. This function extracts `model_extra` fields, adds render-time enrichment (flags), and now will add `created_at`. Templates never access `qso.model_extra` directly.

**When to use:** Any time a Beanie document field needs to be surfaced in a template. Add it here once; all template render paths get it automatically.

**Trade-off:** `_qso_to_view_dict()` is called in 4 places in `ui_router.py` (log_view list, qso_edit_row, qso_view_row, qso_update). All get the same enrichment. No special-casing needed.

---

## Sources

- Direct reading of `app/qso/models.py`, `app/qso/service.py`, `app/qso/ui_router.py`, `app/qso/router.py`, `app/udp/server.py`, `templates/log/log_table.html`, `templates/log/log.html` (2026-04-20)
- `.planning/PROJECT.md` — v2.5 milestone requirements and Key Decisions log

---
*Architecture research for: v2.5 QSO Sorting & Entry Timestamp integration*
*Researched: 2026-04-20*
