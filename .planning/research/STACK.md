# Technology Stack — v2.5 QSO Sorting & Entry Timestamp

**Project:** ollog v2.5
**Milestone:** QSO Sorting & Entry Timestamp
**Researched:** 2026-04-20
**Scope:** Additions and changes ONLY. Validated v2.4 stack is not re-listed.
**Confidence:** HIGH (all claims verified against official docs, Context7, or code audit)

---

## New Dependencies

**None required.** All v2.5 features are achievable with the existing Python + JS stack.
No new packages in `pyproject.toml` or CDN `<script>` tags are needed.

---

## Feature 1: `_created_at` Entry Timestamp Field

### Field Declaration Pattern

Add to `app/qso/models.py` — `QSO(Document)`:

```python
from datetime import datetime, timezone
from pydantic import Field

created_at: Optional[datetime] = Field(
    default_factory=lambda: datetime.now(tz=timezone.utc),
    alias="_created_at",
    serialization_alias="_created_at",
)
```

**Why `lambda: datetime.now(tz=timezone.utc)` not `datetime.utcnow`:**
`datetime.utcnow()` is deprecated in Python 3.12 (DeprecationWarning emitted at module
import if used as a `default_factory`). The `lambda` wrapper avoids capturing a stale
datetime at class-definition time and produces a timezone-aware UTC datetime consistently.

**Why `Optional[datetime]`:**
Matches the existing `qso_date_utc: Optional[datetime]` pattern on the same model.
Documents without `_created_at` (pre-v2.5 imports) read as `None` — no migration needed.
Beanie skips missing fields and applies `default_factory` only on insert, not on read.

**Why `alias="_created_at"` AND `serialization_alias="_created_at"`:**
This is the same two-alias pattern used for `operator_callsign`/`is_deleted` in the
existing model. `alias` controls how Beanie names the MongoDB field during both reads
and writes. `serialization_alias` is required for `model_dump(by_alias=True)` calls.
`populate_by_name=True` is already set via `model_config = ConfigDict(...)`.

### Datetime Storage Behaviour (MEDIUM confidence — pymongo docs verified)

pymongo stores `datetime` objects as BSON UTC milliseconds regardless of timezone info.
By default (without `tz_aware=True` in CodecOptions), pymongo **returns naive UTC
datetimes on read**. The existing `qso_date_utc` field is already stored and retrieved
this way — the codebase treats all datetimes as UTC-naive. The new `_created_at` field
must follow the same convention.

**Do NOT add `tz_aware=True` to `init_db()`** — it would change the type returned for all
existing datetime fields and could break the current `qso_date_utc` comparisons in
`find_duplicate()` (aware vs naive comparison raises `TypeError` in Python).

The only change is: store `_created_at` using `lambda: datetime.now(tz=timezone.utc)`.
pymongo strips the `+00:00` tzinfo at write time and stores UTC milliseconds. On read,
`_created_at` comes back as a naive UTC datetime — consistent with `qso_date_utc`.

### Index Change — `QSO.Settings.indexes`

Add one new `IndexModel` to the existing `indexes` list:

```python
IndexModel(
    [
        ("_operator", pymongo.ASCENDING),
        ("_created_at", pymongo.DESCENDING),
    ],
    name="operator_created_idx",
),
```

**Why this compound index, not a single-field index on `_created_at`:**

Every `get_qso_page()` query includes `{"_operator": operator, "_deleted": False}`. MongoDB
compound index rules: sort can use an index if all fields preceding the sort key in the
index have equality conditions in the query. `_operator` always has an equality condition.
The compound `(_operator, _created_at)` index supports both:
- Sort by `_created_at` (the v2.5 use case)
- The existing `operator_active_idx` handles `_deleted` filter; this index adds sort support

The existing `operator_qso_compound` index (`_operator, CALL, qso_date_utc, BAND, MODE`)
supports sort by `qso_date_utc` because `_operator` is the equality prefix. No changes
needed to existing indexes for date sort. For sorting by `CALL`, `BAND`, `MODE`, `FREQ`
these are in-memory sorts for the typical log size (hundreds to low thousands per operator),
which is acceptable. Adding individual indexes for every sortable column would over-index.

**Index creation:** Beanie calls `init_beanie()` at startup which runs `ensure_indexes()`.
New indexes are created idempotently — no migration script needed. Old documents without
`_created_at` will have no value for that field; MongoDB skips sparse fields in index
entries unless explicitly sparse-indexed. The non-sparse compound index will store `null`
for documents missing `_created_at` — they will sort last on descending sort, first on
ascending. This is acceptable for pre-migration documents.

### Insert Paths That Need `_created_at` Auto-Set

The field has `default_factory` so it is set automatically on `QSO(**qso_dict).insert()`.
No changes needed to `build_qso_dict()`, `import_qsos_from_bytes()`, or the UDP path.
The default fires on every `QSO(**kwargs)` construction, covering all four paths:

| Path | How `_created_at` is set |
|------|--------------------------|
| REST API POST `/api/qsos` | `QSO(**qso_dict).insert()` — default_factory fires |
| UI form submit | Same `QSO(**qso_dict).insert()` call in `submit_qso()` |
| UDP datagram | Same `QSO(**qso_dict).insert()` call in `udp/server.py` |
| ADIF import | Same `QSO(**qso_dict).insert()` call in `import_qsos_from_bytes()` |

**Important:** `build_qso_dict()` must NOT explicitly set `_created_at` — let the
Pydantic default_factory handle it. If the dict contains `_created_at`, it would
override the default (which is the desired behaviour for tests that need a fixed
timestamp, but must not happen in production paths).

### Exposing `_created_at` in the View Dict

`_qso_to_view_dict()` in `ui_router.py` must extract `_created_at` for sort-by display
in the table header (the timestamp icon), even though the column is hidden:

```python
d["_created_at"] = qso.created_at  # None for pre-v2.5 documents
```

The field is declared (not in `model_extra`), so access as `qso.created_at` is correct.
No `extra.get()` needed.

---

## Feature 2: Sortable Log Table Columns

### Sort Parameter Design

**Keep the existing `-fieldname` / `fieldname` convention** — it is already wired end-to-end
in `get_qso_page()` and the Beanie query builder. Do not change to a separate
`sort_field + sort_dir` pair — the existing combined string is simpler and Beanie's
`.sort(sort_by)` accepts it directly.

**Three-state sort cycle per column:**
```
default (no sort applied to this column)
  → click → descending ("-FIELD")
  → click → ascending ("FIELD")
  → click → back to default ("-qso_date_utc")
```

The "default" state is always `-qso_date_utc` (most recent first), not "no sort" — the
table must always have a sort. This means clicking a column header a third time resets to
the default sort, not to unsorted.

**Implementation in template**: Jinja2 handles the toggle logic. Each column header link
computes its `next_sort` value from the current `sort` variable:

```jinja2
{% if sort == "-BAND" %}
  {% set next_sort = "BAND" %}
{% elif sort == "BAND" %}
  {% set next_sort = "-qso_date_utc" %}
{% else %}
  {% set next_sort = "-BAND" %}
{% endif %}
```

This is identical to the existing Date/Time column logic but extended to three states.

### HTMX Sort Pattern (Confirmed — Existing Pattern Is Correct)

The existing `log_table.html` already implements the correct pattern:
- `hx-get="/log/view?sort=...&call=...&band=...&mode=...&date_from=...&date_to=..."`
- `hx-target="#log-table"`
- `hx-swap="innerHTML"`
- `hx-push-url="true"` (preserves sort state in browser URL; supports back button)

All filter params are carried forward in the URL string directly. This is the authoritative
HTMX pattern for server-side sorted tables. No `hx-vals`, `hx-include`, or hidden form
inputs are needed — the sort and filter state is fully encoded in the URL.

**`auto-refresh-ok` sentinel update needed:** The sentinel condition in `log_table.html`
line 1 currently checks `sort == '-qso_date_utc'`. This is correct and must remain — it
means the auto-SSE-refresh only fires when on the default sort. Sorting by any other column
suppresses auto-refresh (correct behaviour — user explicitly chose a non-default sort).
No change required to this logic.

### New Sortable Columns

| Column | Sort key | Notes |
|--------|----------|-------|
| Date / Time UTC | `-qso_date_utc` / `qso_date_utc` | Already implemented |
| Callsign | `-CALL` / `CALL` | Already implemented |
| Band | `-BAND` / `BAND` | Already implemented |
| Mode | `-MODE` / `MODE` | New |
| Freq | `-FREQ` / `FREQ` | New — FREQ is in `model_extra`; Beanie sort on extra fields works via raw field name string |
| RST | No sort needed | Not meaningful to sort by RST |
| Entry Timestamp | `-_created_at` / `_created_at` | New — hidden column, icon in header only |

**Beanie sorting on `model_extra` fields (FREQ):** Beanie's `.sort("-FREQ")` passes the
string to pymongo's cursor `.sort()` which works on any field name in the collection,
including those not declared as Pydantic fields. Verified: `get_qso_page()` already calls
`QSO.find(query).sort(sort_by)` where `sort_by` is an arbitrary string — no changes to
the service layer needed.

**Beanie sorting on aliased fields (`_created_at`):** The MongoDB field is stored as
`_created_at` (from `alias="_created_at"`). The Beanie sort string must use the
**MongoDB field name**, i.e. `"-_created_at"` not `"-created_at"`. This is consistent
with how `_operator` and `_deleted` are referenced in raw queries throughout the codebase
(e.g. `{"_operator": operator}` not `{"operator_callsign": operator}`).

### `get_qso_page()` Sort Allowlist

Add a server-side validation allowlist in `get_qso_page()` to prevent arbitrary field
injection via the `sort` query parameter:

```python
_SORTABLE_FIELDS = {
    "qso_date_utc", "-qso_date_utc",
    "CALL", "-CALL",
    "BAND", "-BAND",
    "MODE", "-MODE",
    "FREQ", "-FREQ",
    "_created_at", "-_created_at",
}

async def get_qso_page(..., sort_by: str = "-qso_date_utc") -> tuple[list[QSO], int]:
    if sort_by not in _SORTABLE_FIELDS:
        sort_by = "-qso_date_utc"
    ...
```

This prevents `sort=_deleted` or other field injection. The current code has no such guard.

---

## Feature 3: Sort Icons in Column Headers

### Icon Set — Heroicons (Already In Use)

The existing `log_table.html` already uses inline Heroicons SVG paths (chevron-down and
chevron-up for the two existing sort states). No new icon library or CDN dependency needed.

**Three-state icon convention:**

| State | Icon | Heroicons name | SVG path |
|-------|------|----------------|----------|
| No sort (column not active) | Double chevron (neutral) | `chevron-up-down` | See below |
| Sorted descending (active) | Chevron down | `chevron-down` | Already in codebase |
| Sorted ascending (active) | Chevron up | `chevron-up` | Already in codebase |

**`chevron-up-down` SVG path (20px solid — matches existing `w-3 h-3` icons):**

```html
<svg class="w-3 h-3 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
  <path fill-rule="evenodd"
    d="M10 3a.75.75 0 01.55.24l3.25 3.5a.75.75 0 11-1.1 1.02L10 4.852 7.3 7.76a.75.75 0 01-1.1-1.02l3.25-3.5A.75.75 0 0110 3zm-3.76 9.2a.75.75 0 011.06.04l2.7 2.908 2.7-2.908a.75.75 0 111.1 1.02l-3.25 3.5a.75.75 0 01-1.1 0l-3.25-3.5a.75.75 0 01.04-1.06z"
    clip-rule="evenodd"/>
</svg>
```

**Colour convention:**
- Active sort column icon: `currentColor` (inherits the link hover colour, typically
  indigo-400 on hover)
- Inactive column icon: add `text-gray-400 dark:text-gray-600` so it is subdued but visible

This matches the existing pattern where active sort headers show a coloured icon and
inactive columns show no icon (current) or a muted double-chevron (proposed).

**Entry timestamp icon (hidden column, header-only):** Add a compact clock icon or
double-arrow in the last position of the `<tr>` header row. The column has no visible
data — only the sortable icon appears. Label with `title="Sort by entry time"` tooltip
for discoverability. Use `w-4 h-4` at the header level to be slightly more prominent.

---

## Integration Points — What Changes vs What Stays

| Component | Change | Details |
|-----------|--------|---------|
| `app/qso/models.py` | Add field + index | `created_at` with `alias="_created_at"`, `default_factory`; new `operator_created_idx` IndexModel |
| `app/qso/service.py` | Add sort allowlist | `_SORTABLE_FIELDS` set; fallback to default in `get_qso_page()` |
| `app/qso/ui_router.py` | Extend `_qso_to_view_dict()` | Add `d["_created_at"] = qso.created_at` |
| `app/qso/router.py` | Verify `_created_at` not in `QSOResponse` | Should be excluded from REST API response (internal field) |
| `templates/log/log_table.html` | Extend sort headers | Add three-state Jinja2 logic + icons for MODE, FREQ, `_created_at`; update Date column to three-state |
| `app/adif/router.py` | No change | `_qso_to_adif_dict()` should not export `_created_at` (not an ADIF field) |

### `QSOResponse` exclusion

The `_created_at` field must be excluded from the REST API `QSOResponse` schema. It is
an internal system field (like `_operator` and `_deleted`). Verify `app/qso/schemas.py`
does not include it — if `QSOResponse` uses `extra='ignore'`, it will be silently dropped
at the serialization boundary without changes.

---

## What NOT to Add

| Item | Reason |
|------|---------|
| New Python package for datetime | stdlib `datetime.now(tz=timezone.utc)` is sufficient |
| `tz_aware=True` in `init_db()` | Changes return type for ALL datetime fields; breaks existing naive datetime comparisons |
| `sort_field` + `sort_dir` as separate query params | The existing combined `-fieldname` convention already works end-to-end; splitting adds complexity with no benefit |
| Per-column index for CALL, BAND, MODE, FREQ sort | Low cardinality / small dataset; in-memory sorts acceptable; over-indexing wastes MongoDB memory |
| `hx-vals` or `hx-include` for sort state | Not needed — sort state travels in the URL query string directly |
| Any JavaScript for sort toggle | Pure server-side Jinja2 toggle logic; zero JS needed for sorting |
| tablesort.js or similar client-side sort library | Server-side sort is the correct pattern for paginated tables; client sort only works on visible rows |
| `_created_at` in ADIF export | Not an ADIF field; must not pollute ADIF exports |

---

## Version Compatibility

All features use packages already pinned in the project:

| Package | Version | Relevant Capability |
|---------|---------|---------------------|
| Beanie | 2.1+ | `default_factory` fields, `IndexModel` in `Settings.indexes`, `.sort("-field")` string syntax |
| pymongo | 4.16+ | `AsyncMongoClient`, `IndexModel`, stores datetime as BSON UTC, returns naive UTC on read |
| HTMX | 2.0.4 | `hx-push-url`, `hx-get` with query string, `hx-swap="innerHTML"` |
| Tailwind CSS | v3 | `text-gray-400 dark:text-gray-600` for inactive icon colour |
| Heroicons | Inline SVG (no npm package) | `chevron-up-down` path confirmed on heroicons.com |
| Python | 3.12+ | `datetime.now(tz=timezone.utc)` — avoids DeprecationWarning from `utcnow()` |

---

## Sources

- Beanie index documentation (Context7 `/beanieodm/beanie`): `IndexModel` in `Settings.indexes`, `Indexed()` wrapper, `.sort("-field")` string syntax
- PyMongo datetime handling: https://www.mongodb.com/docs/languages/python/pymongo-driver/current/data-formats/dates-and-times/
- MongoDB compound index sort rules: https://www.mongodb.com/docs/manual/tutorial/sort-results-with-indexes/
- HTMX `hx-push-url` (Context7 `/bigskysoftware/htmx`): URL state preservation pattern
- HTMX `hx-include` (Context7 `/bigskysoftware/htmx`): confirmed not needed for URL-param sort
- Heroicons sort icons: https://heroicons.com/ — `chevron-up-down`, `chevron-up`, `chevron-down` (20px solid)
- Beanie datetime timezone discussion: https://github.com/BeanieODM/beanie/discussions/1146
- Python 3.12 `datetime.utcnow()` deprecation: https://github.com/dbt-labs/dbt-core/issues/9791
- HTMX sortable table pattern: https://vladkens.cc/htmx-table-sorting/
- Code audit: `app/qso/models.py`, `app/qso/service.py`, `app/qso/ui_router.py`,
  `app/database.py`, `templates/log/log_table.html`

---
*Stack research for: ollog v2.5 QSO Sorting & Entry Timestamp*
*Researched: 2026-04-20*
