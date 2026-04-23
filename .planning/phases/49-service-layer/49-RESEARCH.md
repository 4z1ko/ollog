# Phase 49: Service Layer - Research

**Researched:** 2026-04-23
**Domain:** FastAPI service layer, Beanie ODM, Jinja2 template context, SSE sentinel (server-side HTML)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** When `get_qso_page()` receives a `sort_by` value not in `_ALLOWED_SORT_FIELDS`, log a `WARNING` and fall back to the default sort (`-qso_date_utc`). Do NOT pass the unrecognized field to MongoDB.
- **D-02:** The WARNING log message must include both the rejected field name AND the operator callsign: e.g., `"Invalid sort field '%s' for operator '%s', falling back to default"`.
- **D-03:** `_ALLOWED_SORT_FIELDS` should be declared as a module-level constant (frozenset or set) in `app/qso/service.py`. It must include all 10 currently sortable values: `-qso_date_utc`, `qso_date_utc`, `-CALL`, `CALL`, `-BAND`, `BAND`, `-MODE`, `MODE`, `-_created_at`, `_created_at`.

### Claude's Discretion
- **`created_at` key in view dict:** Use `"created_at"` (no leading underscore) for the `_qso_to_view_dict()` key. Consistent with Phase 50 template access.
- **`created_at` format in view dict:** Raw `datetime` object is acceptable — Phase 50 will format it as needed.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SORT-03 | SSE auto-refresh fires on `-_created_at` sort (newest-entered first) in addition to the existing `-qso_date_utc` default sort | Template sentinel condition at line 1 of `log_table.html` — extend `or sort == '-_created_at'` |
| SORT-04 | `get_qso_page()` validates the sort parameter against an `_ALLOWED_SORT_FIELDS` allowlist before passing to MongoDB — arbitrary field names are rejected with a fallback to the default sort | Guard block after function signature in `service.py` line 183; `_REQUIRED_FIELDS` frozenset is the direct pattern analog |
</phase_requirements>

---

## Summary

Phase 49 is a pure service/backend phase with three discrete edits across three files. All changes are small in-place extensions to existing patterns with no new files, no schema changes, and no new routes.

The scope is: (1) add `_ALLOWED_SORT_FIELDS` frozenset to `service.py` and a guard block inside `get_qso_page()`, (2) add `"created_at"` to the view dict in `_qso_to_view_dict()` in `ui_router.py`, and (3) extend the SSE auto-refresh sentinel condition in `log_table.html`.

All three patterns have exact analogs in the codebase: `_REQUIRED_FIELDS` frozenset, the existing dict-building pattern in `_qso_to_view_dict()`, and the existing `{% if page == 1 and sort == ... %}` sentinel expression.

**Primary recommendation:** Treat this as three atomic edits — one per file. The logging setup gap (see Pitfall 1) must be resolved as part of the service.py edit. All changes together should fit in a single plan with three tasks.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sort parameter validation | API / Backend (service layer) | — | `get_qso_page()` is the sole gateway before MongoDB query; validation at this layer prevents arbitrary field injection regardless of call site |
| `created_at` exposure in template context | Frontend Server (SSR) | — | `_qso_to_view_dict()` is the SSR adapter — it bridges Beanie model attributes to Jinja2 template dicts |
| SSE auto-refresh sentinel condition | Frontend Server (SSR) | — | Server-rendered `#auto-refresh-ok` span controls whether browser SSE listener fires; decision logic lives in the template, driven by context vars from the route |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `logging` stdlib | stdlib | WARNING log for rejected sort fields | Already used throughout `app/` — `logging.getLogger(__name__)` is the project standard |
| Beanie ODM | 2.1.0 [VERIFIED: uv run python -c "import beanie; print(beanie.__version__)"] | `.sort(str)` accepts string sort expr | `.sort("-field_name")` confirmed in Beanie docs [CITED: github.com/beanieodm/beanie/blob/main/docs/tutorial/find.md] |
| Python `frozenset` / `set` | stdlib | `_ALLOWED_SORT_FIELDS` constant | Project already uses `_REQUIRED_FIELDS = {"CALL", ...}` as a module-level set in `service.py` |
| Jinja2 | bundled with FastAPI/Starlette | Template `{% if ... or ... %}` condition | Existing sentinel uses `and`/`not` — `or` extension is trivial |

### No New Dependencies
This phase adds zero new packages. Every capability needed is available via existing imports or the Python stdlib.

---

## Architecture Patterns

### System Architecture Diagram

```
HTTP Request (?sort=arbitrary_field)
      |
      v
log_view() [ui_router.py]
      |
      v -- sort param passed as sort_by arg
get_qso_page() [service.py]
      |
      +-- sort_by NOT IN _ALLOWED_SORT_FIELDS?
      |       YES --> logger.warning(...) --> sort_by = "-qso_date_utc"  (fallback)
      |       NO  --> use sort_by as-is
      |
      v
QSO.find(query).sort(sort_by)... [Beanie -> MongoDB]
      |
      v
list[QSO] returned to log_view()
      |
      v
_qso_to_view_dict(qso) [ui_router.py]
      |   adds: "created_at": qso.created_at  <-- Phase 49 addition
      v
ctx dict passed to template
      |
      v
log_table.html [Jinja2]
      |
      +-- {% if page==1 and (sort=='-qso_date_utc' or sort=='-_created_at') and not filters.* %}
      |       YES --> render <span id="auto-refresh-ok" hidden></span>
      |       NO  --> omit sentinel (SSE refresh disabled)
      v
HTML response to browser
```

### Recommended Project Structure

No structural changes. All edits are in-place to existing files:
```
app/qso/
├── service.py       # add _ALLOWED_SORT_FIELDS + guard block in get_qso_page()
└── ui_router.py     # add "created_at" to _qso_to_view_dict()

templates/log/
└── log_table.html   # extend SSE sentinel condition at line 1
```

### Pattern 1: Module-Level Frozenset Constant

**What:** Declare allowed values as a module-level frozenset constant before the function that uses it.
**When to use:** Input allowlist validation at the service layer.
**Example:**
```python
# Source: app/qso/service.py line 12 (existing _REQUIRED_FIELDS analog)
_REQUIRED_FIELDS = {"CALL", "QSO_DATE", "TIME_ON", "BAND", "MODE"}

# Phase 49 — add before get_qso_page():
_ALLOWED_SORT_FIELDS: frozenset[str] = frozenset({
    "-qso_date_utc", "qso_date_utc",
    "-CALL", "CALL",
    "-BAND", "BAND",
    "-MODE", "MODE",
    "-_created_at", "_created_at",
})
```

### Pattern 2: Guard Block with Fallback and Warning Log

**What:** At the top of `get_qso_page()`, check `sort_by` against the frozenset and reset to default if not found.
**When to use:** Any service function accepting a user-supplied sort/filter parameter that gets passed to MongoDB.
**Example:**
```python
# Source: project pattern — similar to REQUIRED_FIELDS check in import_qsos_from_bytes()
_DEFAULT_SORT = "-qso_date_utc"

async def get_qso_page(
    operator: str,
    ...
    sort_by: str = "-qso_date_utc",
) -> tuple[list[QSO], int]:
    if sort_by not in _ALLOWED_SORT_FIELDS:
        logger.warning(
            "Invalid sort field '%s' for operator '%s', falling back to default",
            sort_by,
            operator,
        )
        sort_by = _DEFAULT_SORT
    ...
```

### Pattern 3: View Dict Addition in _qso_to_view_dict()

**What:** Add `"created_at"` key to the dict returned by `_qso_to_view_dict()`.
**When to use:** Any new QSO attribute that Jinja2 templates need to access.
**Example:**
```python
# Source: app/qso/ui_router.py line 219, existing dict pattern
def _qso_to_view_dict(qso: QSO) -> dict:
    d: dict = {
        "id": str(qso.id),
        "CALL": qso.CALL,
        "BAND": qso.BAND or "",
        "MODE": qso.MODE or "",
        "qso_date_utc": qso.qso_date_utc,
        "created_at": qso.created_at,    # ADD — raw datetime, Phase 50 formats it
    }
    ...
```

### Pattern 4: SSE Sentinel Condition Extension

**What:** Extend the Jinja2 `{% if %}` on line 1 of `log_table.html` to also match `-_created_at`.
**When to use:** Any new sort mode that should enable SSE live refresh (newest-first sorts).
**Example:**
```html
{# Source: templates/log/log_table.html line 1 (current) #}
{% if page == 1 and sort == '-qso_date_utc' and not filters.call and not filters.band and not filters.mode and not filters.date_from and not filters.date_to %}

{# Phase 49 — extend sort condition: #}
{% if page == 1 and (sort == '-qso_date_utc' or sort == '-_created_at') and not filters.call and not filters.band and not filters.mode and not filters.date_from and not filters.date_to %}
```

### Anti-Patterns to Avoid

- **Putting the guard block in the call site (`log_view()`):** The decision says guard happens inside `get_qso_page()`, not at the call site. `get_qso_page()` is called from 4 different handlers; central validation prevents drift.
- **Using `sort_by = sort_by if sort_by in _ALLOWED_SORT_FIELDS else _DEFAULT_SORT` without logging:** The decision mandates a WARNING log with both the rejected value AND the operator callsign. Do not silently fall back.
- **Exposing `_created_at` (with underscore) in the view dict key:** The discretion area specifies `"created_at"` (no leading underscore) for Jinja2 template access in Phase 50. Using the MongoDB alias name in templates creates friction.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sort string allowlist | Custom regex or prefix-stripping parser | `frozenset.__contains__` (`in` operator) | Direct set membership is O(1), readable, and already the project pattern (`_REQUIRED_FIELDS`) |
| Logging | Custom print/warn wrapper | `import logging; logger = logging.getLogger(__name__)` | Project-standard across `app/udp/`, `app/auth/`, `app/main.py`, etc. |

---

## Common Pitfalls

### Pitfall 1: `logger` Not Yet Defined in `service.py`
**What goes wrong:** CONTEXT.md states "logger = logging.getLogger(__name__) — already set up in app/qso/service.py". The actual file (`service.py` lines 1–14 [VERIFIED: file read]) has NO `import logging` and NO `logger` assignment.
**Why it happens:** CONTEXT.md was written based on intent, not the current file state.
**How to avoid:** The plan MUST include adding `import logging` and `logger = logging.getLogger(__name__)` to `service.py` as part of the same task that adds the guard block. Without this, the `logger.warning(...)` call will raise `NameError`.
**Warning signs:** `NameError: name 'logger' is not defined` at runtime when an invalid sort field is passed.

### Pitfall 2: Beanie `.sort()` Receives Unvalidated User Input
**What goes wrong:** If the guard block is omitted or bypassed, `QSO.find(query).sort("_deleted")` or `QSO.find(query).sort("hashed_password")` executes — MongoDB sorts by that field and returns results in a potentially revealing order, even though `_deleted=False` filters the returned documents.
**Why it happens:** Beanie's `.sort(str)` accepts any string without validation [VERIFIED: Beanie docs — no allowlist built into the ODM].
**How to avoid:** `_ALLOWED_SORT_FIELDS` guard runs BEFORE `.sort()` is called.

### Pitfall 3: `qso.created_at` May Be `None` for Pre-Phase-48 Documents
**What goes wrong:** The backfill in Phase 48 runs at startup and stamps all existing documents. But in test environments that bypass app startup (direct Beanie calls), `created_at` may be `None` on constructed QSO objects.
**Why it happens:** `default_factory` fires at model construction, but test fixtures that use `QSO.model_construct()` may not trigger it.
**How to avoid:** In `_qso_to_view_dict()`, use `qso.created_at` directly — the model's `default_factory` ensures non-None in production. Tests for the view dict should construct via `QSO(...)` not `QSO.model_construct(...)` if `created_at` is needed.

### Pitfall 4: SSE Sentinel Parenthesization
**What goes wrong:** Adding `or sort == '-_created_at'` without parentheses around the sort conditions changes operator precedence — `and` binds tighter than `or`, so `A and B or C and D` is `(A and B) or (C and D)`, not `(A or B) and C and D`.
**Why it happens:** Jinja2 follows Python operator precedence.
**How to avoid:** Wrap the disjunction in parentheses: `(sort == '-qso_date_utc' or sort == '-_created_at')`. The pattern in Pattern 4 above is correct.

---

## Code Examples

### Guard Block — Complete Diff Context

```python
# Source: app/qso/service.py (verified 2026-04-23 — lines 1-14 have NO logger currently)

# ADD at top of file (after existing imports):
import logging

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = {"CALL", "QSO_DATE", "TIME_ON", "BAND", "MODE"}  # existing
_MAX_BYTES = 10 * 1024 * 1024  # existing

_DEFAULT_SORT = "-qso_date_utc"
_ALLOWED_SORT_FIELDS: frozenset[str] = frozenset({
    "-qso_date_utc", "qso_date_utc",
    "-CALL", "CALL",
    "-BAND", "BAND",
    "-MODE", "MODE",
    "-_created_at", "_created_at",
})


# Inside get_qso_page() — add as FIRST statement in function body:
async def get_qso_page(
    operator: str,
    page: int = 1,
    page_size: int = 50,
    callsign_filter: Optional[str] = None,
    band_filter: Optional[str] = None,
    mode_filter: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sort_by: str = "-qso_date_utc",
) -> tuple[list[QSO], int]:
    if sort_by not in _ALLOWED_SORT_FIELDS:
        logger.warning(
            "Invalid sort field '%s' for operator '%s', falling back to default",
            sort_by,
            operator,
        )
        sort_by = _DEFAULT_SORT
    # ... rest of existing function unchanged ...
```

### View Dict Addition

```python
# Source: app/qso/ui_router.py — _qso_to_view_dict() at line 219
# ADD "created_at" immediately after "qso_date_utc":

def _qso_to_view_dict(qso: QSO) -> dict:
    d: dict = {
        "id": str(qso.id),
        "CALL": qso.CALL,
        "BAND": qso.BAND or "",
        "MODE": qso.MODE or "",
        "qso_date_utc": qso.qso_date_utc,
        "created_at": qso.created_at,   # ADD
    }
    # Pull extra ADIF fields from model_extra (set via extra="allow")
    extra = qso.model_extra or {}
    d["FREQ"] = extra.get("FREQ", "")
    d["RST_SENT"] = extra.get("RST_SENT", "")
    d["RST_RCVD"] = extra.get("RST_RCVD", "")
    d["QSO_DATE"] = extra.get("QSO_DATE", "")
    d["TIME_ON"] = extra.get("TIME_ON", "")
    # ... flag enrichment unchanged ...
```

### Sentinel Extension

```html
{# Source: templates/log/log_table.html line 1 #}
{# BEFORE: #}
{% if page == 1 and sort == '-qso_date_utc' and not filters.call and not filters.band and not filters.mode and not filters.date_from and not filters.date_to %}

{# AFTER: #}
{% if page == 1 and (sort == '-qso_date_utc' or sort == '-_created_at') and not filters.call and not filters.band and not filters.mode and not filters.date_from and not filters.date_to %}
<span id="auto-refresh-ok" hidden></span>
{% endif %}
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (9.0.2) |
| Config file | `pyproject.toml` (inferred from project structure) |
| Quick run command | `uv run pytest tests/test_qso_schema.py tests/test_operator_isolation.py -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SORT-04 | Invalid sort field is rejected and falls back to default | unit (service) | `uv run pytest tests/test_service_sort.py -x` | ❌ Wave 0 |
| SORT-04 | All 10 allowed sort values are accepted without fallback | unit (service) | `uv run pytest tests/test_service_sort.py -x` | ❌ Wave 0 |
| SORT-04 | WARNING log is emitted with field name and operator callsign | unit (service) | `uv run pytest tests/test_service_sort.py -x` | ❌ Wave 0 |
| SORT-03 | `#auto-refresh-ok` sentinel is rendered when `sort='-_created_at'` | integration (HTTP) | `uv run pytest tests/test_sse_sentinel.py -x` | ❌ Wave 0 |
| SORT-03 | `#auto-refresh-ok` sentinel is rendered when `sort='-qso_date_utc'` (regression) | integration (HTTP) | `uv run pytest tests/test_sse_sentinel.py -x` | ❌ Wave 0 |
| SORT-03 | `#auto-refresh-ok` sentinel NOT rendered when `sort='CALL'` | integration (HTTP) | `uv run pytest tests/test_sse_sentinel.py -x` | ❌ Wave 0 |
| (view dict) | `created_at` is present in `_qso_to_view_dict()` output, no UndefinedError | unit (router) | `uv run pytest tests/test_view_dict.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_service_sort.py tests/test_sse_sentinel.py tests/test_view_dict.py -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_service_sort.py` — covers SORT-04 (allowlist guard, WARNING log, fallback, all 10 valid values accepted)
- [ ] `tests/test_sse_sentinel.py` — covers SORT-03 (sentinel rendered for both newest-first sorts, absent for others); follows `test_log_view_notify_sound.py` fixture pattern (httpx ASGITransport + JWT cookie)
- [ ] `tests/test_view_dict.py` — covers `_qso_to_view_dict()` `created_at` key presence (unit test, no MongoDB required, construct via `QSO(...)` not `model_construct()`)

**Existing test infrastructure coverage:** `test_operator_isolation.py` already tests `get_qso_page()` — extend or add alongside it. `test_log_view_notify_sound.py` provides the exact fixture pattern (ASGITransport + JWT cookie + init_beanie) for sentinel tests.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `_ALLOWED_SORT_FIELDS` frozenset — the entire point of SORT-04 |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| MongoDB field enumeration via sort parameter | Information Disclosure | `_ALLOWED_SORT_FIELDS` allowlist rejects unknown fields before `.sort()` call |
| Sensitive field ordering (`_deleted`, `hashed_password`) via sort | Tampering / Info Disclosure | Same allowlist; `_deleted` and `hashed_password` are not in the allowed set |

---

## Environment Availability

Step 2.6: SKIPPED (no external dependencies — this is a code-only change to Python and Jinja2 files within the existing project).

---

## Open Questions (RESOLVED)

1. **Logger not in `service.py` — is import logging needed elsewhere?**
   RESOLVED: Yes, `import logging` and `logger = logging.getLogger(__name__)` must be added to `service.py` in the same task as the guard block. It's a 2-line addition. The CONTEXT.md claim that the logger was "already set up" was incorrect — verified by file read that `service.py` lines 1-14 have neither import.

2. **`_DEFAULT_SORT` as named constant vs. inline string?**
   RESOLVED: Define `_DEFAULT_SORT = "-qso_date_utc"` alongside `_ALLOWED_SORT_FIELDS`. Use it in both the function signature default and the guard assignment. This avoids duplicating the string literal and is Claude's discretion.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `qso.created_at` is non-None for all production documents after Phase 48 backfill runs at startup | Code Examples (view dict) | `created_at` would be `None` in template context for old QSOs not yet backfilled; Phase 50 tooltip would display nothing rather than error |

**Note:** A1 is low-risk — the backfill is idempotent and runs at every startup. The model's `default_factory` also ensures new inserts always have a value.

---

## Sources

### Primary (HIGH confidence)
- `/Users/royco/ollog/app/qso/service.py` — read directly; confirmed no logger, no allowlist, `.sort(sort_by)` passes raw string to Beanie [VERIFIED]
- `/Users/royco/ollog/app/qso/ui_router.py` — read directly; confirmed `_qso_to_view_dict()` dict structure, `created_at` absent [VERIFIED]
- `/Users/royco/ollog/templates/log/log_table.html` — read directly; confirmed sentinel at line 1, current condition [VERIFIED]
- `/Users/royco/ollog/app/qso/models.py` — read directly; confirmed `created_at` field with `alias="_created_at"`, `default_factory` [VERIFIED]
- Beanie 2.1.0 installed — `.sort(str)` accepts string sort expressions [VERIFIED: `uv run python -c "import beanie; print(beanie.__version__)"`]
- Beanie docs sort syntax [CITED: github.com/beanieodm/beanie/blob/main/docs/tutorial/find.md]

### Secondary (MEDIUM confidence)
- `/Users/royco/ollog/tests/test_log_view_notify_sound.py` — confirmed fixture pattern for HTTP integration tests against `app/main.py` ASGI app [VERIFIED by file read]
- `/Users/royco/ollog/tests/test_operator_isolation.py` — confirmed `get_qso_page()` test pattern [VERIFIED by file read]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified in running codebase
- Architecture: HIGH — all three edit points read directly from source; exact line numbers confirmed
- Pitfalls: HIGH — Pitfall 1 (missing logger) verified directly against source file; Pitfall 4 (parenthesization) is a deterministic Python/Jinja2 precedence rule

**Research date:** 2026-04-23
**Valid until:** 2026-05-23 (stable project, no fast-moving dependencies)
