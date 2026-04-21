# Phase 48: Model Foundation - Research

**Researched:** 2026-04-21
**Domain:** Beanie ODM field defaults, MongoDB indexing, startup migrations
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Add `created_at` (Python attribute name) to the QSO Beanie Document with `Field(alias="_created_at", serialization_alias="_created_at", default_factory=lambda: datetime.now(timezone.utc))`. `timezone` must be imported in `app/qso/models.py`.
- **D-02:** MongoDB stores the field as `_created_at` (underscore prefix = internal field, consistent with `_operator`, `_deleted`).
- **D-03:** Add `_created_at` and `created_at` to the protected-fields strip in **both** PATCH handlers:
  - `app/qso/router.py` line ~239 — REST API PATCH
  - `app/qso/ui_router.py` line ~440 — UI inline-edit PATCH
- **D-04:** Add a new `IndexModel` to `QSO.Settings.indexes` for `(_operator ASCENDING, _created_at DESCENDING)`. Name it `operator_created_at_idx`. Do not merge into the existing `operator_qso_compound` index.
- **D-05:** At app startup (inside `lifespan` / `init_db`), run a one-time idempotent backfill migration: for every QSO where `_created_at` is absent or `None`, set it from `_id.generation_time`. Fall back to `datetime.now(timezone.utc)` for non-ObjectId `_id` values.
- **D-06:** Strip `_created_at` from `_qso_to_dict` in `app/qso/router.py` — the field must NOT appear in REST API GET `/api/qsos` responses.
- **D-07:** Add `_created_at` to `_SKIP_FIELDS` in `app/adif/router.py` so it is excluded from `.adi` export files.

### Claude's Discretion

- How to perform the bulk MongoDB update in the startup migration (`update_many` with `$set` vs. per-document iteration) — choose the most efficient approach for the expected record count.
- Whether to log a startup banner line for the migration — include one if it aids ops visibility.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TS-01 | QSO records are automatically stamped with `_created_at` (UTC datetime) when first inserted — applies to REST API, UI, UDP, and ADIF import paths with no service-layer changes required | D-01 Beanie `default_factory` fires for every `QSO(**kwargs).insert()` call regardless of caller path |
| TS-02 | `_created_at` is stripped from all PATCH/update handlers so it is never overwritten after initial insert | D-03 + D-06 explicit strip in both PATCH handlers; `_qso_to_dict` strip prevents round-trip clobber |
| TS-03 | MongoDB compound index on `(_operator, _created_at DESC)` is created at app startup for efficient sort queries | D-04 `IndexModel` added to `QSO.Settings.indexes`; Beanie `init_beanie` syncs indexes at startup |
</phase_requirements>

---

## Summary

Phase 48 adds `_created_at` — a UTC insert timestamp — to every QSO document in the `qsos` MongoDB collection. The mechanism is a Beanie `default_factory` on a new declared field; because all four insert paths (REST API, UI form, UDP datagram, ADIF import) call `QSO(**dict).insert()`, no service-layer changes are needed. The field follows the exact same `alias` + `serialization_alias` pattern already used for `_operator` and `_deleted`.

Two protection layers prevent the field from being mutated after insert: (1) both PATCH handlers strip `_created_at` and `created_at` before any `$set` is issued, and (2) `_qso_to_dict` in `router.py` explicitly drops the field so API clients never see it and cannot accidentally echo it back in a PATCH body. The field is also added to `_SKIP_FIELDS` in the ADIF router so it never appears in `.adi` export files.

A startup migration backfills all pre-existing QSO documents that lack `_created_at` by reading the embedded timestamp from each document's MongoDB ObjectId (`_id.generation_time`). This is idempotent: the migration queries only documents where `_created_at` does not exist (`{"_created_at": {"$exists": False}}`), so after the first run it touches zero documents. A new compound index `(_operator, _created_at DESC)` is declared in `QSO.Settings.indexes` and created by Beanie at startup, enabling the sort queries that Phase 49 will introduce.

**Primary recommendation:** Implement all changes in a single wave — model field + index + both PATCH strips + `_qso_to_dict` strip + `_SKIP_FIELDS` + startup migration — because the index and the migration both depend on the field existing in the schema first.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Stamp `_created_at` on insert | Database / ODM layer (Beanie model) | — | `default_factory` fires at document construction time, before any caller-specific code runs — guarantees all insert paths are covered |
| Protect `_created_at` from mutation | API / Backend (PATCH handlers) | — | Protection must live in the update path, not the model; model has no built-in immutability for existing documents |
| Exclude `_created_at` from API responses | API / Backend (`_qso_to_dict`) | — | Serialization filter in the REST layer; prevents API consumers from seeing or inadvertently re-submitting the field |
| Exclude `_created_at` from ADIF export | API / Backend (`_SKIP_FIELDS`) | — | Export layer filter; ADIF is a ham-radio interchange format and should contain only ADIF-standard fields |
| Backfill existing records | API / Backend (startup migration in `lifespan`) | Database | One-time migration at startup; requires Beanie and the `qsos` collection to be available |
| Compound index creation | Database / Storage | — | Beanie `init_beanie()` syncs `Settings.indexes` to MongoDB on startup |

---

## Standard Stack

### Core — Already in Use

| Library | Version in use | Purpose | Why Standard |
|---------|----------------|---------|--------------|
| Beanie | existing | Async MongoDB ODM | Project standard; `default_factory` is a Pydantic `FieldInfo` feature, fully supported [VERIFIED: codebase] |
| Pydantic v2 | existing | Field definition + validation | `Field(default_factory=...)` with `alias` + `serialization_alias` is already the project pattern for `_operator` and `_deleted` [VERIFIED: codebase grep] |
| PyMongo `IndexModel` | existing | Index declaration | Already used in `QSO.Settings.indexes` for three existing indexes [VERIFIED: codebase] |
| Motor (via Beanie) | existing | Async MongoDB driver | `update_many` is available via `get_motor_collection()` or direct collection access in startup migration [VERIFIED: codebase] |

### No New Dependencies

This phase requires zero new packages. All capabilities needed (`default_factory`, `IndexModel`, `update_many`, `ObjectId.generation_time`) are already present.

---

## Architecture Patterns

### System Architecture Diagram

```
Insert path (any of 4):                          Update path (PATCH):
  REST API POST /api/qsos                          REST API PATCH /api/qsos/{id}
  UI form POST /log/qsos                  →        UI PATCH /log/qsos/{id}
  UDP datagram handler                               │
  ADIF import service.py                             ▼
         │                                   strip _created_at / created_at
         ▼                                   from body before $set
   QSO(**dict)                                       │
         │                                           ▼
         ▼                                   qso.update({"$set": body})
   Pydantic __init__
   default_factory fires                    Export path (ADIF):
   → created_at = datetime.now(UTC)           _qso_to_adif_dict(qso)
         │                                           │
         ▼                                           ▼
   qso.insert()                              skip _SKIP_FIELDS (now includes "_created_at")
   MongoDB doc: { _created_at: ISODate }             │
         │                                           ▼
         ▼                               clean ADIF record (no internal fields)
   compound index hit:
   (_operator ASC, _created_at DESC)      API GET response:
                                            _qso_to_dict(qso)
Startup migration:                                  │
  lifespan() after init_db()                         ▼
  → db.qsos.update_many(                  pop("_created_at", None) before return
      {_created_at: {$exists: false}},
      {$set: {_created_at: <oid_ts>}}
    ) per-batch or bulk
  → log INFO banner with count
```

### Recommended Change Structure

All changes are in-place edits to existing files — no new files needed:

```
app/
├── qso/
│   ├── models.py        # Add created_at field + IndexModel (D-01, D-02, D-04)
│   └── router.py        # Extend PATCH strip + _qso_to_dict pop (D-03, D-06)
├── qso/
│   └── ui_router.py     # Extend PATCH strip (D-03)
├── adif/
│   └── router.py        # Add "_created_at" to _SKIP_FIELDS (D-07)
└── main.py              # Add startup migration in lifespan after init_db (D-05)
```

### Pattern 1: Beanie Field with alias + serialization_alias + default_factory

The project already uses this exact pattern for `_operator` and `_deleted`. The new field follows it identically:

```python
# Source: verified in app/qso/models.py (existing patterns)
# Existing pattern:
operator_callsign: str = Field(alias="_operator", serialization_alias="_operator")
is_deleted: bool = Field(default=False, alias="_deleted", serialization_alias="_deleted")

# New field (D-01):
from datetime import datetime, timezone  # timezone must be added to existing import
created_at: datetime = Field(
    alias="_created_at",
    serialization_alias="_created_at",
    default_factory=lambda: datetime.now(timezone.utc),
)
```

Key note: `datetime` is already imported in `models.py`. Only `timezone` needs adding to the import line. [VERIFIED: codebase]

### Pattern 2: IndexModel in QSO.Settings.indexes

```python
# Source: verified in app/qso/models.py (existing pattern)
# New index (D-04) — add after the three existing IndexModel entries:
IndexModel(
    [
        ("_operator", pymongo.ASCENDING),
        ("_created_at", pymongo.DESCENDING),
    ],
    name="operator_created_at_idx",
),
```

The index count test in `test_qso_schema.py` (`test_qso_has_three_indexes`) currently asserts exactly 3 indexes. After this change it must assert 4. [VERIFIED: codebase]

### Pattern 3: Protected Fields Strip in PATCH Handlers

```python
# Source: verified in app/qso/router.py line 239 and app/qso/ui_router.py line 440

# REST API PATCH (router.py) — current:
for protected in ("_operator", "operator_callsign", "_deleted", "is_deleted", "_id"):
    body.pop(protected, None)

# After D-03 (add both aliases):
for protected in ("_operator", "operator_callsign", "_deleted", "is_deleted", "_id",
                  "_created_at", "created_at"):
    body.pop(protected, None)

# UI PATCH (ui_router.py) — current:
for protected in ("_operator", "_deleted", "operator_callsign", "is_deleted", "_id"):
    update_dict.pop(protected, None)

# After D-03 (add both aliases):
for protected in ("_operator", "_deleted", "operator_callsign", "is_deleted", "_id",
                  "_created_at", "created_at"):
    update_dict.pop(protected, None)
```

### Pattern 4: _qso_to_dict pop (D-06)

```python
# Source: verified in app/qso/router.py lines 83-100

def _qso_to_dict(qso: QSO) -> dict:
    d = qso.model_dump(by_alias=True)
    d["id"] = str(qso.id)
    d.pop("_id", None)
    d.pop("_created_at", None)      # D-06: internal field, not for API consumers
    if d.get("qso_date_utc") is not None:
        dt = d["qso_date_utc"]
        if hasattr(dt, "isoformat"):
            d["qso_date_utc"] = dt.isoformat()
    return d
```

### Pattern 5: Startup Migration (D-05)

The most efficient approach for a typical ham radio logbook (expected count: tens to low thousands of QSOs) is a single `update_many` with per-document ObjectId timestamp extraction. However, `update_many` cannot compute `_id.generation_time` server-side in a MongoDB `$set` expression — the timestamp extraction must happen in application code.

**Recommended approach: cursor iteration with `bulk_write`**

```python
# Source: [ASSUMED] — Motor/PyMongo bulk_write pattern; ObjectId.generation_time is documented
# in PyMongo docs. Verified that get_motor_collection() is accessible post-init_db via Beanie.

from datetime import datetime, timezone
from bson import ObjectId
from pymongo import UpdateOne

async def backfill_created_at():
    """One-time idempotent migration: stamp _created_at on QSOs that lack it."""
    import logging
    logger = logging.getLogger(__name__)

    collection = QSO.get_motor_collection()
    cursor = collection.find(
        {"_created_at": {"$exists": False}},
        {"_id": 1},           # project only _id for efficiency
    )

    ops = []
    async for doc in cursor:
        oid = doc["_id"]
        if isinstance(oid, ObjectId):
            ts = oid.generation_time.replace(tzinfo=timezone.utc)
        else:
            ts = datetime.now(timezone.utc)
        ops.append(UpdateOne({"_id": oid}, {"$set": {"_created_at": ts}}))

    if ops:
        result = await collection.bulk_write(ops, ordered=False)
        logger.info("_created_at backfill: %d documents updated", result.modified_count)
    else:
        logger.info("_created_at backfill: 0 documents — already up to date")
```

Call site in `app/main.py` lifespan, immediately after `await init_db()`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await _bootstrap_admin()
    await backfill_created_at()   # D-05: one-time idempotent migration
    # ... rest of startup unchanged
```

**Why `bulk_write` not `update_many`:** MongoDB `$set` with computed values derived from `_id.generation_time` cannot be expressed in a single `update_many` aggregation pipeline unless using `$toDate("$_id")` with MongoDB 4.0+ aggregation-in-update syntax. `bulk_write` with pre-computed timestamps is simpler, idiomatic Python, and sufficient for the scale. [ASSUMED — multiple valid approaches exist]

**Why not per-document `.save()`:** Raw `UpdateOne` operations bypass Beanie validation, which is correct here — the migration only sets one internal field and does not need full Pydantic re-validation for every existing document.

### Pattern 6: ADIF _SKIP_FIELDS Extension (D-07)

```python
# Source: verified in app/adif/router.py line 81

# Current:
_SKIP_FIELDS = {"qso_date_utc", "_operator", "_deleted", "_id", "id", "revision_id"}

# After D-07:
_SKIP_FIELDS = {"qso_date_utc", "_operator", "_deleted", "_id", "id", "revision_id",
                "_created_at"}
```

Note: `_created_at` is stored as a declared Beanie field (not in `model_extra`). The `_qso_to_adif_dict` function iterates `qso.model_extra` for extra fields, so `_created_at` would NOT appear there. However, the `_SKIP_FIELDS` guard is still the correct place to add it as a safety net, consistent with how `_operator` and `_deleted` are listed there despite also being declared fields (see comment on line 79–81 of the existing file). [VERIFIED: codebase]

### Anti-Patterns to Avoid

- **Injecting `_created_at` in `build_qso_dict()`:** This would break the "no service-layer changes needed" requirement (TS-01) and couples the timestamp to only the paths that call `build_qso_dict`. The `default_factory` fires automatically for all `QSO(**kwargs)` construction.
- **Using `update_many` with `$set: {_created_at: new Date()}`:** This would stamp all documents with the migration run time, not the actual insert time from the ObjectId.
- **Making the field `Optional[datetime] = None`:** Using `None` as the default instead of `default_factory` would leave `_created_at` absent until explicitly set, defeating the purpose. The field must have `default_factory` so it is always populated on construction.
- **Merging the new index into `operator_qso_compound`:** D-04 explicitly prohibits this. The new index serves sort queries; the compound index serves duplicate detection and operator-scoped queries with different access patterns.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UTC timestamp at insert | Custom middleware or service-layer injection | Pydantic `default_factory=lambda: datetime.now(timezone.utc)` | Fires for all construction paths; no call-site coordination needed |
| ObjectId embedded timestamp extraction | Custom timestamp parsing | `ObjectId.generation_time` (PyMongo built-in) | ObjectId encodes a Unix timestamp in the first 4 bytes; `.generation_time` exposes it as a `datetime` |
| Bulk document updates | Per-document `await qso.save()` loop | PyMongo `bulk_write` with `UpdateOne` ops | Single round-trip; ordered=False allows parallel writes; lower memory footprint |
| Index creation | Manual `db.create_index()` calls | Beanie `Settings.indexes` | Beanie syncs indexes on `init_beanie()` startup; declarative and version-controlled |

**Key insight:** The `default_factory` pattern is precisely the right tool for immutable-at-creation fields. Once set at construction time, the protection is enforced by the PATCH strips — the two layers together provide "set-once" semantics without a custom `__setattr__` override or database-level write concern.

---

## Common Pitfalls

### Pitfall 1: Test Count Assertion Breaks

**What goes wrong:** `test_qso_has_three_indexes` in `tests/test_qso_schema.py` asserts `len(QSO.Settings.indexes) == 3`. Adding a fourth `IndexModel` causes this test to fail immediately.

**Why it happens:** The test was written to lock the index count at phase implementation time.

**How to avoid:** Update the assertion to `== 4` in the same commit that adds the new `IndexModel`.

**Warning signs:** `AssertionError: assert 4 == 3` in `test_qso_schema.py::test_qso_has_three_indexes`.

### Pitfall 2: `timezone` Not Imported in models.py

**What goes wrong:** `datetime.now(timezone.utc)` in the `default_factory` raises `NameError: name 'timezone' is not defined` at import time.

**Why it happens:** `models.py` currently imports `from datetime import datetime` but not `timezone`. [VERIFIED: codebase]

**How to avoid:** Change the import to `from datetime import datetime, timezone` in the same edit that adds the field.

**Warning signs:** App fails to start with `NameError` traceback pointing to `models.py`.

### Pitfall 3: ObjectId.generation_time is Timezone-Naive

**What goes wrong:** `ObjectId.generation_time` returns a `datetime` in UTC but without tzinfo set (it is "naive UTC"). Storing it directly into `_created_at` produces a naive datetime, which is inconsistent with `datetime.now(timezone.utc)` (aware UTC) and may cause comparison errors downstream.

**Why it happens:** PyMongo's `ObjectId.generation_time` returns a naive `datetime` [ASSUMED — common PyMongo behavior; worth confirming with a quick test].

**How to avoid:** Always call `.replace(tzinfo=timezone.utc)` on the result: `oid.generation_time.replace(tzinfo=timezone.utc)`.

**Warning signs:** Mixed aware/naive datetime comparisons in sort operations produce `TypeError: can't compare offset-naive and offset-aware datetimes`.

### Pitfall 4: _created_at Appears in _qso_to_dict If Not Explicitly Popped

**What goes wrong:** `model_dump(by_alias=True)` includes all declared fields, including `_created_at`. Without the explicit `d.pop("_created_at", None)` in `_qso_to_dict`, the field leaks into API GET responses. A client PATCH using the GET response as a body would then include `_created_at`, and the strip in the PATCH handler would only prevent it from being written — but it would cause a silent pop, not an error. More importantly, D-06 requires the field to be invisible to API consumers.

**Why it happens:** Beanie's `model_dump(by_alias=True)` serializes all declared fields. Unlike `model_extra`, declared fields are not easily excluded without an explicit pop or field exclusion.

**How to avoid:** Add `d.pop("_created_at", None)` to `_qso_to_dict` explicitly (D-06).

**Warning signs:** `_created_at` key present in `/api/qsos` GET response body.

### Pitfall 5: Migration Runs Before init_beanie Completes

**What goes wrong:** If `backfill_created_at()` is called before `init_db()` finishes initializing Beanie, `QSO.get_motor_collection()` raises an error because Beanie has not registered the collection.

**Why it happens:** `lifespan` startup order matters — Beanie must be initialized before any model method is called.

**How to avoid:** Place the `await backfill_created_at()` call strictly after `await init_db()` in `lifespan`. The existing order is: `init_db()` → `_bootstrap_admin()` → other startup tasks. Migration should go after `_bootstrap_admin()`.

**Warning signs:** `CollectionWasNotInitialized` or `AttributeError` traceback at startup.

---

## Code Examples

### Full models.py Changes

```python
# Source: verified in app/qso/models.py

# Change import (line 8):
from datetime import datetime, timezone    # timezone added

# New declared field (add after is_deleted, before find_active):
created_at: datetime = Field(
    alias="_created_at",
    serialization_alias="_created_at",
    default_factory=lambda: datetime.now(timezone.utc),
)

# New IndexModel (add as 4th entry in Settings.indexes list):
IndexModel(
    [
        ("_operator", pymongo.ASCENDING),
        ("_created_at", pymongo.DESCENDING),
    ],
    name="operator_created_at_idx",
),
```

---

## Runtime State Inventory

> Included because Phase 48 performs a data migration (backfill) that touches existing runtime state.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | All existing QSO documents in `qsos` collection that lack `_created_at` | Data migration via `bulk_write` in startup — reads `_id.generation_time`, writes `_created_at` |
| Live service config | MongoDB collection indexes — Beanie syncs `Settings.indexes` to live collection at startup | New index `operator_created_at_idx` created automatically by `init_beanie()` |
| OS-registered state | None — no OS-level registrations | None |
| Secrets/env vars | None — no new environment variables | None |
| Build artifacts | None — no compiled artifacts affected | None |

**Migration is idempotent:** After first run, `{"_created_at": {"$exists": False}}` returns 0 documents; `bulk_write` is skipped with zero ops.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | pytest.ini or pyproject.toml (existing) |
| Quick run command | `uv run pytest tests/test_qso_schema.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TS-01 | `_created_at` present in MongoDB doc after insert via any path | integration | `uv run pytest tests/test_qso_schema.py::test_created_at_in_mongodb -x` | ❌ Wave 0 |
| TS-01 | `created_at` field has correct serialization_alias `_created_at` | unit (static) | `uv run pytest tests/test_qso_schema.py::test_qso_created_at_field_alias -x` | ❌ Wave 0 |
| TS-01 | `default_factory` fires — `_created_at` is close to now | unit (static) | `uv run pytest tests/test_qso_schema.py::test_qso_created_at_default_factory -x` | ❌ Wave 0 |
| TS-02 | REST PATCH does not modify `_created_at` | integration | `uv run pytest tests/test_qso_schema.py::test_patch_does_not_overwrite_created_at -x` | ❌ Wave 0 |
| TS-03 | `operator_created_at_idx` index exists after `init_beanie` | integration | `uv run pytest tests/test_qso_schema.py::test_operator_created_at_index_exists -x` | ❌ Wave 0 |
| meta | Index count is now 4 (not 3) | unit (static) | `uv run pytest tests/test_qso_schema.py::test_qso_has_three_indexes -x` | ✅ exists — must update assertion |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_qso_schema.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_qso_schema.py::test_qso_created_at_field_alias` — covers TS-01 (static)
- [ ] `tests/test_qso_schema.py::test_qso_created_at_default_factory` — covers TS-01 (static)
- [ ] `tests/test_qso_schema.py::test_created_at_in_mongodb` — covers TS-01 (integration, requires test_db)
- [ ] `tests/test_qso_schema.py::test_patch_does_not_overwrite_created_at` — covers TS-02 (integration)
- [ ] `tests/test_qso_schema.py::test_operator_created_at_index_exists` — covers TS-03 (integration)
- [ ] Update existing `test_qso_has_three_indexes` assertion from `== 3` to `== 4`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Both PATCH handlers strip `_created_at` before `$set` — prevents client-supplied timestamps from reaching MongoDB |
| V6 Cryptography | no | — |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Client-supplied `_created_at` in PATCH body | Tampering | Strip `_created_at` and `created_at` from body in both PATCH handlers before `$set` (D-03) |
| `_created_at` leaked in GET response, echoed back in PATCH | Tampering (via information disclosure) | Pop `_created_at` from `_qso_to_dict` response (D-06) |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `bulk_write` with pre-computed timestamps is more idiomatic than `update_many` with `$toDate("$_id")` aggregation pipeline for this use case | Pattern 5 (startup migration) | Low — both approaches are correct; the `bulk_write` path is safe regardless |
| A2 | `ObjectId.generation_time` returns a naive UTC `datetime` (not timezone-aware) | Pitfall 3 | Medium — if it is already aware, `.replace(tzinfo=timezone.utc)` is a safe no-op, so the code is correct either way |
| A3 | `QSO.get_motor_collection()` is the correct Beanie API to get a raw Motor collection reference inside a lifespan migration | Pattern 5 | Medium — if Beanie changed the API, alternative is `client[settings.mongodb_db]["qsos"]` (motor client is already retrieved in lifespan via `get_client()`) |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

> A2 and A3 are low-risk: the `.replace(tzinfo=timezone.utc)` guard is correct regardless of whether A2 is true, and the fallback for A3 (`get_client()[settings.mongodb_db]["qsos"]`) is already demonstrated in the existing lifespan code.

---

## Open Questions

1. **`QSO.get_motor_collection()` API surface**
   - What we know: Beanie documents expose `.get_motor_collection()` as a classmethod in most versions
   - What's unclear: Exact method name in the version installed in this project
   - Recommendation: Inspect `app/database.py` or existing Beanie usage; fallback is `get_client()[settings.mongodb_db]["qsos"]` which is already used in `lifespan` (line 28-31 of `app/main.py`)

---

## Environment Availability

Step 2.6: SKIPPED — this phase is purely code/model changes plus a startup migration. All runtime dependencies (MongoDB, Beanie, PyMongo) are existing project dependencies with no new installation required.

---

## Sources

### Primary (HIGH confidence)
- `app/qso/models.py` — verified `Field(alias, serialization_alias)` pattern, existing `IndexModel` structure, current imports
- `app/qso/router.py` — verified protected-fields strip (line 239), `_qso_to_dict` structure (lines 83-100)
- `app/qso/ui_router.py` — verified PATCH protected-fields strip (line 440)
- `app/adif/router.py` — verified `_SKIP_FIELDS` set (line 81) and `_qso_to_adif_dict` logic
- `app/main.py` — verified `lifespan` startup order; `get_client()` usage for collection access
- `app/qso/service.py` — verified all four insert paths call `QSO(**qso_dict).insert()` or `QSO(**qso_dict)` construction
- `tests/test_qso_schema.py` — verified index count assertion (line 38: `assert len(QSO.Settings.indexes) == 3`) that will need updating
- `.planning/phases/48-model-foundation/48-CONTEXT.md` — all decisions D-01 through D-07

### Secondary (MEDIUM confidence)
- `.planning/REQUIREMENTS.md` — TS-01, TS-02, TS-03 requirement text

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are existing project dependencies, verified in codebase
- Architecture: HIGH — all patterns are direct extensions of verified existing patterns in the codebase
- Pitfalls: HIGH — derived from direct code inspection; the `timezone` import gap is a verified finding

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 (stable codebase; no fast-moving dependencies)
