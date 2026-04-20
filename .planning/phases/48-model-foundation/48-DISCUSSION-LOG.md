# Phase 48: Model Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 48-model-foundation
**Areas discussed:** Backfill existing QSOs, API response exposure

---

## Backfill Existing QSOs

| Option | Description | Selected |
|--------|-------------|----------|
| Accept nulls | Phase 48 adds only the model field. Existing records stay as-is. Sort by _created_at pushes null records to end when sorting descending. | |
| Backfill from ObjectId timestamp | Add startup migration: set _created_at from _id.generation_time for all documents missing the field. | ✓ |
| Defer to Phase 49 | Phase 48 adds only model field; backfill handled in Phase 49 alongside the sort allowlist. | |

**User's choice:** Backfill from ObjectId timestamp

---

**Follow-up: When to run the migration?**

| Option | Description | Selected |
|--------|-------------|----------|
| App startup (inside lifespan/init_db) | Fire once at startup, skip records that already have _created_at. Zero-op after first run. | ✓ |
| Separate admin script | A standalone Python script run manually before deployment. | |

**User's choice:** App startup

---

**Follow-up: Fallback for non-ObjectId _id?**

| Option | Description | Selected |
|--------|-------------|----------|
| Skip it | Leave _created_at missing on records with non-ObjectId _id. | |
| Use datetime.now() | Stamp backfill time as a placeholder so every record has a value. | ✓ |

**User's choice:** Use datetime.now() as fallback

---

## API Response Exposure

**REST API GET /api/qsos**

| Option | Description | Selected |
|--------|-------------|----------|
| Include in REST API responses | Useful to external API consumers. _qso_to_dict handles datetime → ISO string. | |
| Exclude from REST API responses | Treat as purely internal housekeeping. Strip from _qso_to_dict. | ✓ |

**User's choice:** Exclude from REST API responses

---

**ADIF export**

| Option | Description | Selected |
|--------|-------------|----------|
| Exclude from ADIF export | Add to _SKIP_FIELDS in app/adif/router.py. ADIF files stay clean and ADIF-standard-compliant. | ✓ |
| Include in ADIF export | Emit <_created_at:N>... in exported ADIF. | |

**User's choice:** Exclude from ADIF export

---

## Claude's Discretion

- Bulk update strategy for startup migration (update_many vs. per-document iteration)
- Whether to log a startup banner for the migration

## Deferred Ideas

None.
