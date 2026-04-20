# Requirements — v2.5 QSO Sorting & Entry Timestamp

## Active Requirements

### Entry Timestamp

- [ ] **TS-01**: QSO records are automatically stamped with `_created_at` (UTC datetime) when first inserted — applies to REST API, UI, UDP, and ADIF import paths with no service-layer changes required
- [ ] **TS-02**: `_created_at` is stripped from all PATCH/update handlers so it is never overwritten after initial insert
- [ ] **TS-03**: MongoDB compound index on `(_operator, _created_at DESC)` is created at app startup for efficient sort queries

### Column Sorting

- [ ] **SORT-01**: Operator can sort the log table by MODE (alphabetic asc/desc) via the MODE column header click
- [ ] **SORT-02**: Operator can sort the log table by entry timestamp (`_created_at`) via a clock icon appended to the DATE column header — no new visible data column and no extra `<td>` in QSO rows
- [ ] **SORT-03**: SSE auto-refresh fires on `-_created_at` sort (newest-entered first) in addition to the existing `-qso_date_utc` default sort
- [ ] **SORT-04**: `get_qso_page()` validates the sort parameter against an `_ALLOWED_SORT_FIELDS` allowlist before passing to MongoDB — arbitrary field names are rejected with a fallback to the default sort

### Sort UX

- [ ] **UX-01**: Sortable columns that are not currently the active sort show a faint double-chevron (hollow) icon indicating they are clickable
- [ ] **UX-02**: The active sort column shows a solid chevron in the current sort direction (asc/desc)

## Future Requirements

- FREQ sort — stored as string in `model_extra`; lexicographic order would be semantically wrong. Requires storing as numeric or a separate sort-key field.
- RST sort — no operational value for ham operators; deferred indefinitely
- Multi-column sort — not needed for personal/club logbook use case
- `_created_at` tooltip on hover — show entry timestamp as tooltip on the QSO date cell

## Out of Scope

- **FREQ column sort** — FREQ is stored as a string; lexicographic sort would place "14.225" before "7.1", which is wrong. Excluded to avoid misleading sort results.
- **RST_SENT / RST_RCVD sort** — no operational value for ham operators; omitted from sortable columns
- **Three-state sort cycle (asc/desc/reset)** — not needed; the existing Clear button already resets to default sort
- **`_created_at` visible as a table column** — intentionally invisible per milestone spec; only sortable via dedicated icon

## Traceability

| REQ-ID  | Phase    | Plans |
|---------|----------|-------|
| TS-01   | Phase 48 | TBD   |
| TS-02   | Phase 48 | TBD   |
| TS-03   | Phase 48 | TBD   |
| SORT-04 | Phase 49 | TBD   |
| SORT-03 | Phase 49 | TBD   |
| SORT-01 | Phase 50 | TBD   |
| SORT-02 | Phase 50 | TBD   |
| UX-01   | Phase 50 | TBD   |
| UX-02   | Phase 50 | TBD   |
