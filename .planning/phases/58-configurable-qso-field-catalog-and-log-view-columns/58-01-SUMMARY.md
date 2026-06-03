---
phase: 58
plan: 58-01
status: complete
completed: 2026-06-03
---

# Phase 58 Plan 01 Summary

## Objective

Enable the Log View configuration menu to select from a curated known QSO/ADIF field catalog while preserving the current default columns, sort behavior, HTMX/SSE refresh behavior, and always-visible Actions column.

## Implemented

- Added `app/qso/fields.py` as the shared server-side field catalog and value extraction layer.
- Preserved default visible columns exactly: `date`, `call`, `band`, `mode`, `freq`, `rst`.
- Added known/common fields such as operator, station callsign, raw ADIF date/time fields, receive band/frequency, RST sent/received, power, comments, notes, QTH/grid, contest exchange fields, park/summit/reference fields, country/zone/state/county fields, and QSL status fields.
- Excluded internal/security-sensitive fields including `_id`, `_operator`, `_deleted`, `_created_at`, `rowHash`, and `APP_OLLOG_TOKEN`.
- Updated `_qso_to_view_dict()` to include human-readable `fields` values for every catalog key.
- Updated Log View menu, table headers, view rows, and edit rows to render from the shared catalog.
- Kept existing sort controls limited to Date/Time, entry timestamp, Callsign, Band, and Mode.
- Kept `ollog.log.columns` localStorage persistence and added normalization for stale/duplicate/invalid stored values.
- Rebuilt `static/css/output.css` for the bounded scrollable menu classes.

## Verification

- `.venv/bin/python -m pytest tests/test_view_dict.py tests/test_service_sort.py` — 7 passed, 3 skipped.
- `.venv/bin/python -m pytest tests/test_sse_sentinel.py` — 4 skipped because MongoDB was not available.
- `.venv/bin/python -m ruff check app/qso/fields.py app/qso/ui_router.py tests/test_view_dict.py` — passed.
- `npm run build` — passed.
- Jinja smoke render for `templates/log/log_table.html` — passed.

## Notes

- `uv` is not on PATH in this environment, so verification used the local `.venv/bin/python` runner.
- `tests/test_service_sort.py` and `tests/test_sse_sentinel.py` contain Mongo-backed cases that skip when local MongoDB is unavailable; the non-Mongo sort allowlist and catalog/value tests passed.
