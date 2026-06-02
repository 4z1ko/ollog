# Requirements: ollog v2.9 QSO Deduplication and ADIF Duplicate Review

**Defined:** 2026-06-02
**Core Value:** Exact duplicate QSOs are prevented at the document level while ADIF imports remain operator-controlled.

## v1 Requirements

### Deterministic Document Deduplication

- [x] **DEDUP-01**: Every QSO document gets a deterministic `rowHash` computed from business-relevant values.
- [x] **DEDUP-02**: Hashing sorts object keys recursively, preserves array order, normalizes date values, and excludes metadata/audit fields.
- [x] **DEDUP-03**: MongoDB enforces uniqueness with an idempotent unique index on `rowHash`.
- [x] **DEDUP-04**: Insert flows return explicit duplicate/already-existing results without overwriting existing documents.
- [x] **DEDUP-05**: Soft-delete changes update `rowHash` so deleted and active documents do not collide.
- [x] **DEDUP-06**: Existing QSO records can be safely backfilled without overwriting existing `rowHash` values or deleting duplicates.

### ADIF Duplicate Review

- [x] **ADIF-REVIEW-01**: ADIF import automatically inserts QSOs that do not already exist.
- [x] **ADIF-REVIEW-02**: Existing QSOs are listed at the end of the import process.
- [x] **ADIF-REVIEW-03**: Each existing QSO row has a checkbox so the operator can choose whether to force import it.
- [x] **ADIF-REVIEW-04**: Duplicate review import revalidates records server-side and does not silently overwrite existing documents.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEDUP-01 | Phase 57 | Complete |
| DEDUP-02 | Phase 57 | Complete |
| DEDUP-03 | Phase 57 | Complete |
| DEDUP-04 | Phase 57 | Complete |
| DEDUP-05 | Phase 57 | Complete |
| DEDUP-06 | Phase 57 | Complete |
| ADIF-REVIEW-01 | Phase 57 | Complete |
| ADIF-REVIEW-02 | Phase 57 | Complete |
| ADIF-REVIEW-03 | Phase 57 | Complete |
| ADIF-REVIEW-04 | Phase 57 | Complete |
