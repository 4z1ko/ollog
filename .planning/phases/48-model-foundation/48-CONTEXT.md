# Phase 48: Model Foundation - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Stamp `_created_at` (UTC datetime) on every QSO document at insert time via Beanie model `default_factory`, protect the field from being overwritten on subsequent PATCH edits, add a startup migration to backfill existing records from their ObjectId timestamp, and create the compound index `(_operator, _created_at DESC)`.

No code changes are required in any of the four insert callers (REST API, UI form, UDP datagram, ADIF import) — the model-level `default_factory` covers all paths automatically.

</domain>

<decisions>
## Implementation Decisions

### Field Definition

- **D-01:** Add `created_at` (Python attribute name) to the QSO Beanie Document with `Field(alias="_created_at", serialization_alias="_created_at", default_factory=lambda: datetime.now(timezone.utc))` — follows the existing `operator_callsign`/`is_deleted` naming convention. `timezone` must be imported in `app/qso/models.py`.
- **D-02:** MongoDB stores the field as `_created_at` (underscore prefix = internal field, consistent with `_operator`, `_deleted`).

### PATCH Protection

- **D-03:** Add `_created_at` and `created_at` to the protected-fields strip in **both** PATCH handlers:
  - `app/qso/router.py:239` — REST API PATCH
  - `app/qso/ui_router.py:440` — UI inline-edit PATCH
  Neither handler should ever set `_created_at` via `$set` on update.

### Index

- **D-04:** Add a new `IndexModel` to `QSO.Settings.indexes` for `(_operator ASCENDING, _created_at DESCENDING)` — do not merge into the existing `operator_qso_compound` index. Name it `operator_created_at_idx`.

### Backfill for Existing Records

- **D-05:** At app startup (inside `lifespan` / `init_db`), run a one-time migration:
  - For every QSO document where `_created_at` is absent or `None`, set `_created_at` from `_id.generation_time` (the timestamp embedded in the MongoDB ObjectId).
  - If a document's `_id` is not a standard ObjectId (e.g., test-inserted custom `_id`), fall back to `datetime.now(timezone.utc)` as a placeholder.
  - Migration is idempotent — documents that already have `_created_at` are skipped. After first run it is a zero-op.

### API and Export Visibility

- **D-06:** Explicitly strip `_created_at` from `_qso_to_dict` in `app/qso/router.py` — `_created_at` does NOT appear in REST API GET `/api/qsos` responses. It is a housekeeping-only internal field.
- **D-07:** Add `_created_at` to `_SKIP_FIELDS` in `app/adif/router.py` — `_created_at` is excluded from ADIF `.adi` export files. ADIF files remain clean and importable by external logbook software.

### Claude's Discretion

- How to perform the bulk MongoDB update in the startup migration (e.g., `update_many` with `$set` vs. per-document iteration) — choose the most efficient approach for the expected record count.
- Whether to log a startup banner line for the migration (analogous to the UDP banner) — include one if it aids ops visibility.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### QSO Model and Insert Paths
- `app/qso/models.py` — QSO Beanie Document, existing field alias pattern, Settings.indexes definition
- `app/qso/service.py` — `build_qso_dict()` and all four insert paths; `datetime`/`timezone` import patterns

### Update Handlers (PATCH Protection)
- `app/qso/router.py` — REST API PATCH handler (line ~239), `_qso_to_dict` (line ~83), protected fields strip
- `app/qso/ui_router.py` — UI inline-edit PATCH handler (line ~440), protected fields strip

### ADIF Export Skip List
- `app/adif/router.py` — `_SKIP_FIELDS` set (line ~81)

### Requirements
- `.planning/REQUIREMENTS.md` — TS-01 (stamp on insert), TS-02 (protected from update), TS-03 (compound index)

### App Startup / Lifespan
- `app/main.py` — `lifespan` function and `init_db()` call site; where to wire the startup migration

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Field(alias="...", serialization_alias="...")` pattern: established in `app/qso/models.py` for `_operator` and `_deleted` — use identical pattern for `_created_at`
- `IndexModel` list in `QSO.Settings.indexes`: three existing index models to follow as a template for the new compound index
- `datetime` already imported in `app/qso/models.py`; `timezone` needs adding

### Established Patterns
- Internal fields use underscore prefix in MongoDB (`_operator`, `_deleted`, `_created_at`) with camelCase/snake_case Python attribute names (`operator_callsign`, `is_deleted`, `created_at`)
- Protected fields strip is a manual `for protected in (...): body.pop(protected, None)` loop — extend the tuple in both PATCH handlers
- `_SKIP_FIELDS` in ADIF router is a plain Python set — add `"_created_at"` to it

### Integration Points
- `app/main.py` `lifespan` is the correct hook for the startup migration — it runs after `init_db()` so Beanie and the collection are available
- Both PATCH handlers (`router.py` and `ui_router.py`) currently share the same strip pattern but are NOT refactored into a shared helper — patch both in place

</code_context>

<specifics>
## Specific Ideas

- Startup migration logs a banner line to confirm migration ran and how many documents were updated (e.g., `INFO: _created_at backfill: 142 documents updated`).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 48-model-foundation*
*Context gathered: 2026-04-20*
