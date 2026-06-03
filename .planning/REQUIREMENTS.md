# Requirements: ollog v3.0 Configurable QSO Log Fields

**Defined:** 2026-06-03
**Core Value:** Operators can tailor the Log View table to the fields they actually use without losing ollog's ADIF-native, live-updating workflow.

## v1 Requirements

### Field Catalog

- [ ] **FIELDS-01:** The Log View configuration menu lists every selectable QSO field from the supported display catalog, including core fields, profile-stamped fields, common ADIF fields, app-specific fields, and safe internal display fields.
- [ ] **FIELDS-02:** A fresh browser uses the current default visible columns: Date / Time, Callsign, Band, Mode, Frequency, and RST.
- [ ] **FIELDS-03:** The field catalog has stable field keys, human-readable labels, and display extractors so headers and row cells are generated from the same source.
- [ ] **FIELDS-04:** The catalog excludes non-display implementation fields that should never appear in the UI, including `_deleted`, raw MongoDB IDs, and authentication/security fields.

### Column Selection

- [ ] **COLUMNS-01:** Operators can select or deselect any configurable field from the existing column configuration menu.
- [ ] **COLUMNS-02:** The Actions column remains visible and functional regardless of selected QSO fields.
- [ ] **COLUMNS-03:** Selected columns persist across full page loads and HTMX table partial swaps.
- [ ] **COLUMNS-04:** Invalid, stale, or removed persisted field keys are ignored and the menu falls back to the default column set when no valid selection remains.
- [ ] **COLUMNS-05:** The configuration menu remains usable with the larger field list by using a bounded, scrollable panel that works in light and dark themes on desktop and mobile.

### Table Rendering

- [ ] **TABLE-01:** The table header renders selected field labels from the catalog in the selected order.
- [ ] **TABLE-02:** Each QSO row renders selected values from ADIF-native fields, profile-stamped fields, app-specific fields, and safe internal display values without losing arbitrary ADIF extras.
- [ ] **TABLE-03:** Missing or unknown field values render as blank cells without raising Jinja2 or JavaScript errors.
- [ ] **TABLE-04:** Existing sortable fields continue to show sort controls when visible; non-sortable selected fields render plain headers.
- [ ] **TABLE-05:** Existing sort, filter, pagination, inline edit, delete, SSE auto-refresh, LIVE indicator, new-QSO badge, and sound-notification behavior continue to work with configurable columns.

### Verification

- [ ] **VERIFY-01:** Tests cover field catalog construction, excluded-field behavior, and default/persisted column normalization.
- [ ] **VERIFY-02:** Tests cover row value extraction for declared fields, extra ADIF fields, profile-stamped fields, missing values, and safe internal display fields.
- [ ] **VERIFY-03:** Template or integration tests cover HTMX partial refresh compatibility and preservation of row action controls.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIELDS-01 | Phase 58 | Planned |
| FIELDS-02 | Phase 58 | Planned |
| FIELDS-03 | Phase 58 | Planned |
| FIELDS-04 | Phase 58 | Planned |
| COLUMNS-01 | Phase 58 | Planned |
| COLUMNS-02 | Phase 58 | Planned |
| COLUMNS-03 | Phase 58 | Planned |
| COLUMNS-04 | Phase 58 | Planned |
| COLUMNS-05 | Phase 58 | Planned |
| TABLE-01 | Phase 58 | Planned |
| TABLE-02 | Phase 58 | Planned |
| TABLE-03 | Phase 58 | Planned |
| TABLE-04 | Phase 58 | Planned |
| TABLE-05 | Phase 58 | Planned |
| VERIFY-01 | Phase 58 | Planned |
| VERIFY-02 | Phase 58 | Planned |
| VERIFY-03 | Phase 58 | Planned |
