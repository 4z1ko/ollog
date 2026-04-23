---
plan: 50-01
phase: 50-sort-ui
status: complete
completed: 2026-04-23
key-files:
  created: []
  modified:
    - templates/log/log_table.html
    - static/css/output.css
---

## What Was Built

All sort header changes in the log table template, completing Phase 50 (final phase of v2.5):

- **MODE sort header** — new clickable `<th>` with ascending-first toggle (`MODE` → `-MODE`). Inactive hollow double-chevron when not active sort column.
- **DATE header restructure** — wrapped in `<span class="inline-flex items-center gap-2">` containing two links: (1) date sort link for `qso_date_utc` (existing behavior, now with inactive indicator), (2) Heroicons clock outline icon link for `_created_at` sort (descending-first — newest entered first on first click).
- **CALL header** — added `{% else %}` branch with hollow double-chevron inactive indicator.
- **BAND header** — added `{% else %}` branch with hollow double-chevron inactive indicator.
- **CSS rebuild** — `static/css/output.css` rebuilt with `dark\:opacity-25` class (opacity 25% in dark mode for inactive indicators).

All 5 sortable elements (DATE text, clock icon, CALL, BAND, MODE) show: solid directional chevron when active, hollow double-chevron at `opacity-30 dark:opacity-25` when inactive. All sort clicks preserve active filter parameters in the URL.

## Verification

- `npm run verify` exits 0 — dark classes and color-scheme present
- `dark:opacity-25` class compiled as `.dark\:opacity-25:is(.dark *){opacity:.25}` in output.css
- Template contains exactly 5 occurrences of `opacity-30 dark:opacity-25`
- LINE 1 sentinel (`sort == '-_created_at'`) preserved — no regression
- MODE ascending-first toggle confirmed (`{% if sort == 'MODE' %}-MODE{% else %}MODE{% endif %}`)
- Human visual verification: approved

## Self-Check: PASSED

All must_haves satisfied:
- Clicking MODE sorts ascending first, then descending ✓
- Clock icon visible in DATE header, sorts by `_created_at` descending first ✓
- All inactive sortable columns show faint hollow double-chevron ✓
- Active sort column shows solid directional chevron ✓
- Filters preserved through all sort clicks ✓
