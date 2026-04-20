# Domain Pitfalls — v2.5 QSO Sorting & Entry Timestamp

**Domain:** Adding `_created_at` timestamp + column sorting to existing FastAPI/Beanie/HTMX/MongoDB logbook
**Researched:** 2026-04-20
**Confidence:** HIGH — all findings verified against live codebase and Beanie docs

---

## Critical Pitfalls

### Pitfall 1: `default_factory` Fires on Every Instantiation, Including Updates — Double-Stamping

**What goes wrong:**
`_created_at: datetime = Field(default_factory=datetime.utcnow)` on the `QSO` Beanie document fires the factory every time a `QSO(...)` object is constructed, not only on `.insert()`. The `qso_update` handler in `ui_router.py` (and `patch_qso` in `router.py`) fetch the existing document with `await QSO.get(oid)`, then call `await qso.update({"$set": update_dict})`. This path never touches `_created_at`. However, if any code path ever calls `QSO(**qso_dict)` on an existing document dict (e.g., rebuilding from a stored dict), the factory overwrites the original timestamp.

The immediate risk: if `build_qso_dict()` is extended to include `_created_at` in the returned dict and `import_qsos_from_bytes` passes that dict to `QSO(**qso_dict)`, the import path will always receive an import-time stamp, not a QSO date stamp. This is correct for imports — but only if the field is not also included in `build_qso_dict` where a caller might strip it or leave it out, causing the factory to fire a second time on re-insertion.

**Root cause:**
Pydantic/Beanie `default_factory` is a *construction* hook, not an *insert* hook. It is re-evaluated every time the Python object is constructed.

**How to avoid:**
Use the Beanie `@before_event(Insert)` hook pattern instead of `default_factory`:

```python
from beanie import Document, Insert, before_event
from datetime import datetime, timezone

class QSO(Document):
    _created_at: Optional[datetime] = None

    @before_event(Insert)
    def set_created_at(self):
        self._created_at = datetime.now(timezone.utc)
```

OR: use `default_factory` but set it on the field with `Optional[datetime] = Field(default=None)` and set it explicitly only in `build_qso_dict()`. The rule is: one place sets it, never set it in `build_qso_dict()`, never touch it in the update path.

The simpler, safer pattern for this codebase (which uses raw `$set` dicts rather than Beanie save/replace): add `_created_at` to `build_qso_dict()` explicitly (`result["_created_at"] = datetime.now(timezone.utc)`), and ensure the update handlers in `qso_update` (ui_router) and `patch_qso` (router) include `_created_at` in the list of protected fields that get stripped from `update_dict`:

```python
for protected in ("_operator", "_deleted", "operator_callsign", "is_deleted", "_id", "_created_at"):
    update_dict.pop(protected, None)
```

**Warning signs:**
- `_created_at` on an updated QSO is newer than the QSO was inserted (the update path accidentally re-stamped it).
- Two QSOs inserted at the same time appear to have different `_created_at` values that match their respective edit times, not insert times.

**Phase to address:** Model + service layer phase (first implementation phase).

---

### Pitfall 2: Sorting `model_extra` Fields (FREQ, QSO_DATE, TIME_ON) — String Comparison, Not Numeric

**What goes wrong:**
`FREQ` is stored as a string (e.g., `"14.225"`, `"7.1"`, `"144.200"`). MongoDB's `sort()` on a string field uses lexicographic order. Lexicographic sort of `"14.225"` vs `"7.1"` places `"14.225"` before `"7.1"` because `"1" < "7"`. A user sorting by frequency ascending will see `14 MHz` entries before `7 MHz` entries — which is wrong.

`QSO_DATE` and `TIME_ON` are stored as ADIF strings (`"20260420"` and `"1430"`). String sort is correct for these two fields because the ADIF date/time format is lexicographically monotone (YYYYMMDD sorts correctly as a string). However, this is a coincidence of the format, not a guarantee — mixing 4-char (`HHMM`) and 6-char (`HHMMSS`) `TIME_ON` values can cause unexpected ordering.

**Root cause:**
`model_config = ConfigDict(extra="allow")` stores all non-declared ADIF fields verbatim in `model_extra`. These fields are not typed; MongoDB stores them as whatever type was inserted (string). Beanie's `.sort("-FREQ")` passes the field name directly to PyMongo, which sorts by whatever the stored type is.

**How to avoid:**
Do not expose `FREQ`, `QSO_DATE`, or `TIME_ON` as sort options in `get_qso_page()`. The correct sort for date/time is `qso_date_utc` (a declared `datetime` field, sorts correctly). The correct sort for frequency is also `qso_date_utc` or band — frequency sorting is rarely useful in a ham logbook context and adds complexity without user value.

If FREQ sorting is added in the future, the fix requires a migration that converts the string `FREQ` field to a float in MongoDB, or a computed `FREQ_MHZ: Optional[float]` declared field. Do not add FREQ as a sort target in v2.5.

**Warning signs:**
- Sort-by-frequency produces results in unexpected order (14 MHz before 7 MHz).
- Users report that "sort by date" and "sort by time" give different orderings for QSOs logged on the same UTC date with mixed TIME_ON formats.

**Phase to address:** Service layer sort allowlist phase. Exclude `FREQ`, `QSO_DATE`, `TIME_ON` from the sort allowlist.

---

### Pitfall 3: Sort Field Injection — No Allowlist in `get_qso_page()`

**What goes wrong:**
`get_qso_page()` passes `sort_by` directly to `.sort(sort_by)` with no validation:

```python
items = await QSO.find(query).sort(sort_by).skip(...).limit(...)
```

The `sort` query param in `log_view()` is also unvalidated. An operator can pass `sort=_operator` or `sort=-_id` or `sort=nonexistent_field` via the URL and the query will execute against MongoDB. While operator isolation prevents cross-operator data leakage, arbitrary sort fields expose MongoDB field structure and cause unpredictable ordering.

**Root cause:**
The current implementation (pre-v2.5) accepts any string. This was acceptable when the only sort was `qso_date_utc`, `CALL`, and `BAND`, but adding `_created_at` as a valid option requires a proper allowlist to prevent `_deleted`, `_operator`, or invented field names from being used as sort keys.

**How to avoid:**
Add a module-level allowlist set in `service.py` and validate at the top of `get_qso_page()`:

```python
_ALLOWED_SORT_FIELDS = {
    "qso_date_utc", "-qso_date_utc",
    "CALL", "-CALL",
    "BAND", "-BAND",
    "MODE", "-MODE",
    "_created_at", "-_created_at",
}

async def get_qso_page(..., sort_by: str = "-qso_date_utc") -> ...:
    if sort_by not in _ALLOWED_SORT_FIELDS:
        sort_by = "-qso_date_utc"  # fallback to default
    ...
```

**Warning signs:**
- Any user can craft a URL with `?sort=_deleted` or `?sort=_operator` and get a valid response (though not exploitable, it is a leak of internal field names).
- Adding new sort fields in a future phase requires updating the allowlist — without the allowlist, no such audit point exists.

**Phase to address:** First phase (service allowlist). Must be in place before the template exposes new sort icons.

---

### Pitfall 4: `_created_at` as Hidden Sort Column — Table Semantic Validity and `<th>` Placement

**What goes wrong:**
The requirement is: "timestamp sort icon in the table header allows sorting by `_created_at` even though the column is hidden." There is no `<td>` data column for `_created_at` in each `<tr>`, but the `<th>` for the sort icon must exist. An extra `<th>` in the `<thead>` without a corresponding `<td>` in every `<tbody>` row creates an HTML table with mismatched column counts. While browsers render this without visible error, it breaks screen readers, automated scraping, and `table-layout: fixed` styles if ever applied.

**Root cause:**
Attempting to add a sort control to a column that has no visible data requires choosing between: (a) an out-of-band sort button (outside the table entirely), (b) an empty `<td>` in every row (extra space in each row), or (c) accepting the semantic mismatch (fragile).

**How to avoid:**
The cleanest solution is (b): add an empty `<td></td>` in every `qso_row.html` and `qso_row_edit.html` at the same column position as the `<th>` sort icon. The cell is visually empty and has zero width via CSS (`width: 0; padding: 0;`). This preserves correct column count semantics.

An alternative is placing the `_created_at` sort icon outside the `<table>` entirely — e.g., as a sort control above the table header row. This avoids the semantic issue and is better UX since the column is conceptually "hidden."

Do not add a `<th>` without a matching `<td>` count in every row.

**Warning signs:**
- Developer tools accessibility audit flags "table header has no corresponding data cells."
- The `Actions` column shifts horizontally when the `_created_at` `<th>` is present on some renders and absent on others.

**Phase to address:** Template implementation phase (log_table.html, qso_row.html, qso_row_edit.html changes together in one commit).

---

### Pitfall 5: Auto-Refresh Sentinel Condition Must Include New `_created_at` Sort Value

**What goes wrong:**
The SSE auto-refresh sentinel in `log_table.html` suppresses live refresh whenever the sort is not the default:

```jinja
{% if page == 1 and sort == '-qso_date_utc' and not filters.call and ... %}
<span id="auto-refresh-ok" hidden></span>
{% endif %}
```

When `_created_at` sort is added, users can be on page 1 with no filters but with `sort='-_created_at'`. The sentinel will be absent, so every new QSO inserts only the badge counter instead of triggering a table refresh. This is technically correct (the table is sorted by entry time, not QSO date, so auto-refresh is appropriate). However: if the intent is to also suppress auto-refresh when sorted by `_created_at`, the condition remains correct. If the intent is to allow auto-refresh when sorted by `_created_at` (since new entries will naturally appear at the top), the condition must be extended:

```jinja
{% if page == 1 and sort in ('-qso_date_utc', '-_created_at') and not filters.call and ... %}
```

**Root cause:**
The sentinel condition hardcodes the default sort value as the only allowed auto-refresh case. Adding `_created_at` as a valid sort target requires a deliberate decision about whether it should also enable auto-refresh.

**How to avoid:**
Decide explicitly during implementation: auto-refresh triggers for `-qso_date_utc` only (default sort only), or for all descending sorts where new items naturally appear at the top. Document the decision as a comment in the template.

**Warning signs:**
- Users sorting by entry time (`_created_at` descending) get badge counter increments instead of live table refresh — unexpected behavior if they expect new entries to appear automatically.

**Phase to address:** Template phase. The condition change is one line; the decision must be made before writing the line.

---

## Moderate Pitfalls

### Pitfall 6: HTMX Sort Header Clicks Lose Filter Params — URL Construction Must Thread All Active Filters

**What goes wrong:**
Each sort header `<a>` in `log_table.html` constructs the `hx-get` URL by hand:

```jinja
hx-get="/log/view?sort=...&call={{ filters.call or '' }}&band=..."
```

If a new filter param is added to `log_view()` in the future (e.g., a "worked before" toggle), the sort header URL construction must be updated in every `<th>` element individually. The current template already handles all five existing filter params. Adding the `_created_at` sort icon as a sixth `<th>` requires adding the same five filter params to its URL. Forgetting even one drops that filter when the user clicks the sort icon.

**Root cause:**
Manual URL construction in Jinja2 templates is not DRY — every sort link duplicates the full parameter list. Changing any filter param name requires touching every sort header.

**How to avoid:**
In v2.5, use the existing pattern (all five params appear in every sort URL). If this pattern is ever refactored, a Jinja2 macro or URL builder helper would centralize it. For now, the risk is low — five params is manageable. The key discipline is: add the `_created_at` sort `<th>` using the exact same URL template as the existing sort headers — copy-paste the full URL fragment and change only the `sort=` value.

**Warning signs:**
- Clicking the entry-time sort icon while a band filter is active clears the band filter (it was omitted from the sort URL).
- Integration test: apply a filter, then click each sort header, confirm filter params are preserved in the updated URL.

**Phase to address:** Template phase. Test by applying a filter and cycling through all sort icons.

---

### Pitfall 7: Beanie Aliased Fields — `_created_at` Must Use the Same Alias Pattern as `_operator` and `_deleted`

**What goes wrong:**
The existing QSO model uses `Field(alias="_operator", serialization_alias="_operator")` because MongoDB requires the leading-underscore field name, but Python attribute names cannot start with underscore (without a name-mangling side effect in Python classes). If `_created_at` is added as a plain field name (e.g., `created_at: Optional[datetime]`), the MongoDB document will have the key `created_at`, not `_created_at`. This mismatches the naming convention for system fields and breaks any code or MongoDB query that expects `_created_at`.

Conversely, if `created_at` (without underscore) is used as the Python attribute, adding `Field(alias="_created_at", serialization_alias="_created_at")` correctly stores the field as `_created_at` in MongoDB. Beanie `.sort("-_created_at")` string sort uses the MongoDB field name, so this is the correct approach.

**Root cause:**
The existing alias pattern for `_operator` and `_deleted` is the established convention for internal/system fields in this codebase. Deviating from it for `_created_at` creates an inconsistency and breaks the expected field naming.

**How to avoid:**
Follow the established pattern exactly:

```python
created_at: Optional[datetime] = Field(
    default=None,
    alias="_created_at",
    serialization_alias="_created_at"
)
```

with `populate_by_name=True` already set in `model_config`. Access as `qso.created_at` in Python; stored as `_created_at` in MongoDB. The sort string `"-_created_at"` in `get_qso_page()` uses the MongoDB alias name, which Beanie passes directly to PyMongo.

Add `"_created_at"` to the protected fields list in both update handlers:
- `ui_router.py` `qso_update()` protected list
- `router.py` `patch_qso()` protected list

**Warning signs:**
- `qso._created_at` attribute access raises `AttributeError` — the Python attribute name is `created_at` (no underscore), not `_created_at`.
- MongoDB documents have `created_at` field (no underscore) instead of `_created_at`.
- Sorting by `"-_created_at"` returns results in insertion order (because the field is actually stored as `created_at` without underscore, so the sort field `_created_at` does not exist and MongoDB uses natural order).

**Phase to address:** Model phase. Verify with a quick `mongosh` query after first insert.

---

### Pitfall 8: ADIF Import Gets Import-Time Timestamp, Not QSO-Date Timestamp — Intentional But Easy to Confuse

**What goes wrong:**
When `import_qsos_from_bytes()` inserts QSOs via `QSO(**qso_dict)` and `_created_at` is set at construction time (whether by `default_factory` or by explicit set in `build_qso_dict()`), all imported QSOs receive the timestamp of the import operation. A logbook imported on 2026-04-20 will have `_created_at = 2026-04-20T...` for QSOs that were originally made in 2020. Sorting by `_created_at` descending then shows the most recently *imported* QSOs, not the most recently *worked* QSOs.

This is the correct behavior for the stated requirement ("entry timestamp — system field auto-set on QSO insert"). But it creates confusion when:
1. Users sort by entry time and see their entire imported logbook at the top.
2. A user re-imports a file after clearing duplicates — the re-imported QSOs all get new `_created_at` timestamps.
3. The SSE feed's auto-refresh sentinel, which uses `_created_at` sort, triggers a full table refresh for every bulk-imported QSO (if import-time inserts fire change stream events, which they do).

**Root cause:**
`_created_at` is a database insertion timestamp (MongoDB `$currentDate` equivalent), not an ADIF QSO date field. The distinction must be documented and users must understand that "entry time" means "when this record entered this database," not "when the QSO was made."

**How to avoid:**
- In the log table UI, label the `_created_at` sort icon as "Entry order" or "Logged order," not "Time logged" or "QSO time" (which suggests QSO date).
- This is a UX documentation issue, not a code issue. The implementation is correct.
- If import-heavy usage causes SSE refresh storms during bulk import, the debounce on `htmx.ajax` (from v2.4 pitfall research) becomes critical. Ensure it is in place.

**Phase to address:** Template phase (label the icon correctly). Architecture decision phase (acknowledge the semantic in comments).

---

### Pitfall 9: `_qso_to_view_dict()` Does Not Expose `_created_at` — Template Gets None

**What goes wrong:**
`_qso_to_view_dict()` in `ui_router.py` constructs the dict that Jinja2 templates receive. It currently populates `id`, `CALL`, `BAND`, `MODE`, `qso_date_utc`, plus `model_extra` fields (`FREQ`, `RST_SENT`, `RST_RCVD`, `QSO_DATE`, `TIME_ON`). It does not include `created_at` (the Python attribute for `_created_at`).

If the `_created_at` sort icon is added to the template and a tooltip or data attribute wants to show the entry timestamp, `qso.created_at` must be explicitly added to the view dict. Without this, the template gets `None` (key missing) or a Jinja2 `UndefinedError`.

The sort itself does not require `_created_at` in the view dict — sorting happens in `get_qso_page()` before the dicts are built. But any template that references `qso.created_at` or `qso['created_at']` will fail.

**Root cause:**
`model_extra` is the grab-bag for arbitrary ADIF fields. `created_at` is a declared field but NOT in `model_extra` — it is accessed as `qso.created_at` (the Python attribute). Extra fields must be pulled from `model_extra`; declared fields must be pulled directly from the Beanie document attributes.

**How to avoid:**
Explicitly add `created_at` to `_qso_to_view_dict()`:

```python
d["created_at"] = qso.created_at  # alias for _created_at
```

Only needed if any template renders it. For the v2.5 requirement (invisible column, sort-only), this is optional. Add it anyway for completeness and future use.

**Phase to address:** Service/template integration phase.

---

### Pitfall 10: Existing QSOs Have No `_created_at` — `None` Sort Behavior in MongoDB

**What goes wrong:**
All existing QSO documents in MongoDB have no `_created_at` field. When sorted by `"_created_at"` ascending, MongoDB places documents with a `null` or missing field *before* documents with a value (nulls sort first in ascending order, last in descending). Sorting by `"-_created_at"` descending places the oldest (null) records at the end, which is acceptable for the default use case (users want newest entries first). But sorting ascending puts all pre-migration records at the top, which is confusing.

**Root cause:**
MongoDB sort behavior for missing fields: `null` values sort before any non-null value in ascending order. Documents missing the field entirely behave the same as `null`.

**How to avoid:**
Accept this behavior as correct for the descending case (which is the primary use case). For ascending sort, consider filtering out null `_created_at` documents or document the known limitation.

No migration is required for v2.5. Beanie reads the missing field as `None` (the Python default), which is correct.

**Warning signs:**
- Sort by `_created_at` ascending shows all imported/pre-v2.5 QSOs first, then QSOs inserted after the feature was deployed.
- This is expected behavior, not a bug.

**Phase to address:** No action required. Document as known behavior in comments.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| URL construction per sort header (no DRY macro) | Simple to understand, easy to debug | Every new filter param requires updating every sort URL | Acceptable for v2.5 (5 params). Refactor to Jinja2 macro if filter count exceeds 7. |
| No index on `_created_at` | Zero index setup | Sort-by-entry-time scans all documents | Acceptable until logbook > 10,000 QSOs. Add `IndexModel([("_operator", ASC), ("_created_at", DESC)])` in same commit as field addition. |
| Sort allowlist as a Python set (not enum) | Simple to add values | No documentation of valid values, no IDE autocomplete | Acceptable for v2.5. Add a comment listing all valid sort strings. |
| `_created_at` labeled "entry order" in UI only | No migration, no renaming | Users may confuse with QSO date if tooltip is absent | Never omit the tooltip or label — UX debt if label is absent. |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Beanie `default_factory` | Set on field declaration — fires on every construction | Set explicitly in `build_qso_dict()` or use `@before_event(Insert)` |
| `qso.update({"$set": ...})` | Forget to add `_created_at` to protected fields strip list | Add `"_created_at"` to the protected fields list in both update handlers |
| `model_extra` vs declared fields | Pull `created_at` from `model_extra` (it isn't there) | Access as `qso.created_at` (declared field) |
| Beanie `.sort("-_created_at")` | Use Python attribute name `"-created_at"` | Use MongoDB alias name `"-_created_at"` (with underscore) |
| `_qso_to_view_dict()` | Forget to include `created_at` in the view dict | Add explicitly; it is not in `model_extra` |
| HTMX sort URL | Omit one filter param from new sort icon URL | Copy the full URL template from an existing sort icon, change only the sort value |

---

## "Looks Done But Isn't" Checklist

- [ ] **`_created_at` double-stamp prevention:** Verify `_created_at` is in the protected fields strip list in `qso_update()` (ui_router.py) AND `patch_qso()` (router.py). Run a test: insert QSO, edit CALL, confirm `_created_at` is unchanged in MongoDB after edit.
- [ ] **Sort allowlist active:** Confirm `get_qso_page()` returns `sort_by="-qso_date_utc"` results when called with `sort_by="nonexistent_field"`. Confirm `sort_by="_deleted"` falls back to default.
- [ ] **FREQ excluded from sort options:** Confirm `FREQ` and `QSO_DATE` are not in the sort allowlist and not exposed as sort icons in the template.
- [ ] **Column count semantic validity:** Every `<tr>` in `<tbody>` has the same number of `<td>` elements as `<th>` elements in `<thead>`. Run HTML validation or count manually.
- [ ] **Filter params preserved on sort click:** Apply a band filter + mode filter, then click each sort header. Confirm the URL retains `band=` and `mode=` params. Confirm the table shows filtered results after sort.
- [ ] **Auto-refresh sentinel decision documented:** The template comment explicitly states which sort values enable the sentinel. The decision (default sort only, or all descending sorts) is stated in the comment.
- [ ] **Index added for `_created_at`:** `Settings.indexes` in `QSO` model includes a compound index on `(_operator ASC, _created_at DESC)`.
- [ ] **`_created_at` in view dict:** `_qso_to_view_dict()` returns `created_at` key (even if `None` for pre-migration documents) so templates can safely reference it without `UndefinedError`.
- [ ] **Import path gets insert-time stamp:** After importing a test ADIF file, confirm all imported QSOs have `_created_at` close to the import time (not `None`, not the ADIF QSO_DATE value).
- [ ] **UDP path gets insert-time stamp:** After sending a test UDP datagram, confirm the inserted QSO has `_created_at` set (not `None`).

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| `_created_at` stamped on update | MEDIUM | MongoDB update: `db.qsos.updateMany({_created_at: {$gt: ISODate("2026-04-21")}}, [{$set: {_created_at: "$_id.getTimestamp()"}}])` — MongoDB ObjectIds encode insert time, can recover approximate `_created_at` from `_id` |
| Field stored as `created_at` (no underscore) | LOW | Rename field in MongoDB: `db.qsos.updateMany({created_at: {$exists: true}}, [{$rename: {created_at: "_created_at"}}])` |
| Filter param dropped by sort icon | LOW | Purely a template fix — no data impact, user navigates back, re-applies filter |
| Sort allowlist missing (injection) | LOW | Code-only fix, no data impact — no operator can see another operator's data regardless |
| No index on `_created_at` (performance) | LOW | Add index online via `db.qsos.createIndex({_operator: 1, _created_at: -1})` — MongoDB builds indexes in background without downtime |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Double-stamp on update | Model + service layer | Edit a QSO after insert; confirm `_created_at` is unchanged in DB |
| FREQ string sort | Sort allowlist phase | Confirm `FREQ` not in `_ALLOWED_SORT_FIELDS` |
| Sort field injection | Sort allowlist phase | Call `get_qso_page(sort_by="_deleted")`, confirm fallback to default |
| `<th>` without `<td>` mismatch | Template phase | HTML validation; count `<th>` vs `<td>` in rendered output |
| Auto-refresh sentinel missing new sort | Template phase | Sort by `_created_at`, trigger new QSO, confirm expected refresh/badge behavior |
| Filter params lost on sort click | Template phase | Apply filter, click each sort icon, confirm filter preserved |
| Alias mismatch (`created_at` vs `_created_at`) | Model phase | Inspect MongoDB doc after insert; field must be `_created_at` |
| `_created_at` missing from view dict | Template integration | Access `{{ qso.created_at }}` in template; no `UndefinedError` |
| Import gets insert-time stamp | Service phase | Import test file; all records have `_created_at` near import time, not `None` |
| Missing `_created_at` index | Model phase | Check `Settings.indexes` before merging model change |

---

## Sources

- Beanie `@before_event(Insert)` pattern — verified against Beanie docs via Context7 (/beanieodm/beanie)
- Beanie `.sort()` string syntax — verified: string sort uses MongoDB field name (alias), not Python attribute name
- MongoDB sort behavior for null/missing fields — MongoDB documentation, behavior confirmed in current docs
- Existing codebase alias pattern: `operator_callsign = Field(alias="_operator", serialization_alias="_operator")` — `app/qso/models.py`
- `model_extra` access pattern for ADIF fields — `_qso_to_view_dict()` in `app/qso/ui_router.py`
- Protected fields strip list — `qso_update()` in `app/qso/ui_router.py` and `patch_qso()` in `app/qso/router.py`
- Auto-refresh sentinel condition — `templates/log/log_table.html` line 1
- HTMX sort URL construction pattern — `templates/log/log_table.html` existing sort headers

---
*Pitfalls research for: v2.5 QSO Sorting & Entry Timestamp*
*Researched: 2026-04-20*
