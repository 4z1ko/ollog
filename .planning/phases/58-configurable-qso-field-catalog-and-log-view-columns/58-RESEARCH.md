# Phase 58: Configurable QSO Field Catalog and Log View Columns - Research

**Researched:** 2026-06-03
**Status:** Ready for planning

## Research Question

What does the planner need to know to replace the Log View's hard-coded column menu/table cells with a supported QSO/ADIF field catalog while preserving the current HTMX, SSE, sorting, and localStorage behavior?

## Sources

- Official ADIF site: https://adif.org/ - lists ADIF V 3.1.7 as the current HTML specification and provides the always-current redirect at `https://adif.org/adif`.
- Official ADIF 3.1.7 specification: https://adif.org/317/ADIF_317.htm - authoritative field/source reference for known ADIF fields.
- `docs/reference/adif-field-reference.md` - ollog's current documented core, auto-stamped, app-specific, and example extra fields.
- `templates/log/log.html` - current gear menu, `ollog.log.columns` persistence, and HTMX/SSE JavaScript.
- `templates/log/log_table.html` and `templates/log/qso_row.html` - current hard-coded header/cell rendering.
- `app/qso/ui_router.py` - `_qso_to_view_dict()` and `log_view()` context construction.
- `app/qso/models.py` and `app/adif/router.py` - QSO field storage/export behavior.

## Findings

### ADIF Field Source

- ADIF field names are standardized externally, but ollog should not try to scrape or dynamically discover the entire spec at runtime. A curated known catalog is the right implementation for this phase.
- The official site currently points to ADIF 3.1.7, updated 2026-03-22. Use this as the external source of truth when choosing known fields, but keep the app catalog as static Python data.
- ollog already documents a smaller supported/common subset: core fields (`QSO_DATE`, `TIME_ON`, `CALL`, `BAND`, `MODE`, `RST_SENT`, `RST_RCVD`), auto-stamped fields (`OPERATOR`, `STATION_CALLSIGN`), app-specific `APP_OLLOG_TOKEN`, and examples such as `FREQ`, `TX_PWR`, `COMMENT`, `QTH`, `GRIDSQUARE`, `CONTEST_ID`, `SRX`, and `STX`.

### Recommended Catalog Shape

Use a server-side field catalog with stable keys, labels, ADIF/source field names, default visibility, sort metadata, and value rendering metadata.

Suggested field groups in one flat catalog:

- Existing defaults: `date`, `call`, `band`, `mode`, `freq`, `rst`
- Current non-defaults: `operator`, `station`
- Time/detail fields: `qso_date`, `time_on`, `time_off`, `created_at`
- Contact and station fields: `name`, `qth`, `gridsquare`, `country`, `dxcc`, `cqz`, `ituz`, `state`, `cnty`
- Signal/radio fields: `rst_sent`, `rst_rcvd`, `freq_rx`, `band_rx`, `tx_pwr`, `rx_pwr`, `sat_name`, `sat_mode`, `prop_mode`
- Award/activation fields: `pota_ref`, `my_pota_ref`, `sota_ref`, `my_sota_ref`, `wwff_ref`, `my_wwff_ref`, `iota`, `my_gridsquare`
- Contest/exchange fields: `contest_id`, `srx`, `srx_string`, `stx`, `stx_string`, `check`, `class`, `section`
- Notes/QSL fields: `comment`, `notes`, `qsl_rcvd`, `qsl_sent`, `eqsl_qsl_rcvd`, `eqsl_qsl_sent`, `lotw_qsl_rcvd`, `lotw_qsl_sent`, `qsl_via`
- App fields: `app_ollog_token` display can exist in the catalog if considered useful, but it should likely default hidden. If shown, it must never expose authentication token values from active UDP ingestion paths. Since UDP consumes token fields before QSO creation, normal records should be blank.

The planner should keep the exact catalog list adjustable, but must avoid unsafe fields:
`id`, `_id`, `revision_id`, `_operator` as a raw implementation key, `_deleted`, `_created_at` as raw internal spelling, `rowHash`, and anything credential-like.

### Rendering Strategy

Current rendering is split:

- `log.html`: hard-coded menu and client-side column toggle logic.
- `log_table.html`: hard-coded headers and sort links.
- `qso_row.html`: hard-coded cells and actions.
- `_qso_to_view_dict()`: extracts a limited set of extras from `model_extra`.

For Phase 58, the cleanest direction is:

1. Add a catalog/value layer in Python near the log-view route, likely in a small module such as `app/qso/fields.py` or adjacent helpers in `app/qso/ui_router.py`.
2. Have `_qso_to_view_dict()` expose a `fields` mapping keyed by catalog key, with already-humanized string/html-safe display values.
3. Pass `field_catalog`, `default_column_keys`, and `configurable_column_keys` into both full page and partial table render contexts.
4. Generate menu labels from the catalog in `log.html`.
5. Generate table headers and row cells from catalog keys in `log_table.html` and `qso_row.html`.
6. Keep the Actions column outside the field loop.

This avoids trying to teach Jinja templates how to look through declared fields, aliases, `model_extra`, and synthetic display fields independently.

### LocalStorage and Order

The existing key `ollog.log.columns` should stay. The current JS stores an array of selected column keys and re-applies visibility after HTMX settles.

Needed changes:

- Server emits `DEFAULT_COLUMNS` and `CONFIGURABLE_COLUMNS` as JSON from the catalog, instead of hard-coded JS arrays.
- JS normalizes persisted keys against `CONFIGURABLE_COLUMNS`.
- If no valid persisted keys remain, fall back to defaults.
- When rendering visible order, defaults stay first and extra selected fields append after defaults in catalog order.

Implementation note: because the table partial is server-rendered and localStorage is client-side, the server cannot know selected columns during normal HTMX swaps unless the selection is sent in the URL/body. The current implementation works by rendering all possible columns and hiding unselected ones client-side. Preserve that model for this phase. It keeps pagination/filter/sort URLs unchanged and prevents localStorage from becoming a backend concern.

### Sorting

Do not expand sortable fields in this phase.

Sortable catalog entries should map only to existing sort targets:

- Date / Time -> `qso_date_utc` / `-qso_date_utc`
- Entry timestamp icon -> `_created_at` / `-_created_at`
- Callsign -> `CALL` / `-CALL`
- Band -> `BAND` / `-BAND`
- Mode -> `MODE` / `-MODE`

Other selected headers should render as plain text. `app/qso/service.py` already has a strict sort allowlist; preserving it avoids security and index scope creep.

### UI Menu

Use one bounded scrollable checklist. The existing menu width (`w-48`) will likely be too tight for long labels, so planner should include a UI task to widen and bound it, for example a responsive width plus max height with overflow-y auto.

Avoid:

- Grouped sections
- Search/filter input
- Drag/reorder controls
- Extra explanatory text inside the app UI

Do include:

- Stable checkbox dimensions
- Light/dark hover and border states using literal Tailwind classes
- A max height based on viewport, so the panel does not exceed mobile screens

### Tests and Verification

Recommended focused tests:

- Unit tests for field catalog:
  - default keys exactly preserve `date`, `call`, `band`, `mode`, `freq`, `rst`
  - known keys are unique
  - unsafe internal keys are absent
  - sortable metadata exists only for current sortable fields
- Unit tests for value extraction:
  - declared fields: `CALL`, `BAND`, `MODE`
  - extra ADIF fields from `model_extra`: `FREQ`, `TX_PWR`, `COMMENT`, `CONTEST_ID`
  - profile/app fields: `OPERATOR`, `STATION_CALLSIGN`, `APP_OLLOG_TOKEN`
  - missing values render as empty strings
  - date/time and RST displays are humanized
- Template/integration tests:
  - `GET /log/view` includes the expanded menu with known fields
  - table still contains Actions column outside configurable cells
  - HTMX partial response includes catalog-generated headers/cells
  - `id="auto-refresh-ok"` behavior remains unchanged for default and `_created_at` sorts

Existing tests to extend:

- `tests/test_view_dict.py`
- `tests/test_sse_sentinel.py`
- `tests/test_service_sort.py`

## Validation Architecture

The phase should be validated by combining unit-level catalog/value tests with one or two HTML response assertions. Full browser validation is useful but not necessary for the first safety gate because the current behavior is plain localStorage plus `hidden` class toggling.

Minimum validation:

1. Run the field/value unit tests.
2. Run existing sort and SSE sentinel tests.
3. Render `/log/view` and assert:
   - expanded known-field checklist exists
   - default fields remain present
   - Actions column remains present
   - at least one additional known ADIF field appears as a configurable column

## Planning Recommendations

- One implementation plan is enough.
- Plan should start with a Python catalog/value extraction task, then template rendering, then JavaScript normalization/menu bounds, then tests.
- Keep localStorage client-side; do not add profile persistence.
- Do not modify database schema.
- Do not expand service sort allowlist.
- If Tailwind classes change, run the existing CSS build command and verify output contains any new literal classes.

## Research Complete

Phase 58 can be planned from this research plus `58-CONTEXT.md`.
