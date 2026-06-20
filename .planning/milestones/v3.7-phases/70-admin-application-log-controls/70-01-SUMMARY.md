---
phase: 70-admin-application-log-controls
plan: 70-01
subsystem: admin-ui
tags: [internal-logs, admin, htmx, sse, tests, docs]
requires:
  - phase: 67
    provides: MongoDB-backed internal logs, settings, retention, masking, and broadcast support
  - phase: 68
    provides: Admin Logs page with filters, pagination, live row rendering, and formatted details
  - phase: 69
    provides: Core application-flow instrumentation and live log behavior fixes
provides:
  - Current-browser Pause/Start control for admin Recent Logs live updates
  - Confirmation-gated Clear Log Messages action for application log records
  - Post-clear forced audit event with deleted count
  - Documentation and focused tests for pause/resume, clear scope, and safety guarantees
affects: [admin-log-viewer, internal-logs, docs, tests]
tech-stack:
  added: []
  patterns:
    - Client-side pause gates automatic SSE insertion and polling only
    - Explicit HTMX filter/pagination refreshes remain active while paused
    - Clear deletes application log records first, then attempts a forced audit event
    - Destructive admin modal reuses existing admin modal classes
key-files:
  created:
    - templates/admin/clear_application_logs_modal.html
    - templates/admin/clear_application_logs_result.html
    - .planning/phases/70-admin-application-log-controls/70-01-SUMMARY.md
  modified:
    - app/admin/ui_router.py
    - app/internal_logs/service.py
    - templates/admin/logs.html
    - static/css/input.css
    - static/css/output.css
    - docs/admin-guide/application-logs.md
    - tests/test_internal_logs.py
    - .planning/phases/70-admin-application-log-controls/70-01-PLAN.md
    - .planning/ROADMAP.md
    - .planning/STATE.md
requirements-completed:
  - LOGCTRL-01
  - LOGCTRL-02
  - LOGCTRL-03
  - LOGCTRL-04
  - LOGCTRL-05
  - LOGCTRL-06
  - LOGCTRL-07
  - LOGCTRL-08
duration: 60 min
completed: 2026-06-20
---

# Phase 70 Plan 70-01: Admin Application Log Controls Summary

**Admin Recent Logs controls for current-browser pause/start and confirmation-gated application log clearing**

## Accomplishments

- Added Pause/Start controls to the Recent Logs card header with a LIVE/PAUSED/OFFLINE badge.
- Pause now suppresses automatic SSE row insertion and near-live polling in the current browser tab only.
- Start immediately refreshes the log table and resumes automatic live updates.
- Existing filter, reset, and pagination HTMX actions remain available while paused.
- Added an admin-only Clear Log Messages modal using the locked safety wording.
- Added `clear_application_logs()` to delete only `ApplicationLog` records.
- Clear now deletes application log records first, then attempts a forced `application_logs_cleared` audit log with deleted count.
- If the audit row cannot be written, the clear still succeeds and the UI reports the note.
- Updated admin logging documentation with Pause/Start and Clear Log Messages behavior.
- Added focused tests for pause/start source behavior, modal copy, clear helper scope, clear route audit behavior, and audit-failure success behavior.

## Task Commits

1. **Tasks 70-01-01 through 70-01-04: Tests, backend clear path, UI controls/modal, docs, and verification** — `ef29a40`

## Deviations From Plan

- Combined implementation tasks into one feature commit rather than one commit per task because the tests, backend route, UI script, CSS class, and docs were tightly coupled and verified together.
- Restored generated MkDocs `site/` output after strict docs verification, preserving current repo practice of committing source docs rather than generated site churn.

## Verification

Passed:

- `uv run pytest tests/test_internal_logs.py` — 24 passed.
- `uv run python -m compileall app tests/test_internal_logs.py` — passed after approved escalation because sandboxed `uv` could not open `/Users/roy/.cache/uv`.
- `npm run build` — passed.
- `npm run verify` — passed; dark classes and `color-scheme` present.
- `uv run mkdocs build --strict` — passed after approved escalation for `uv` cache access.
- `git diff --check` — passed.

## Self-Check: PASSED

- All LOGCTRL-01 through LOGCTRL-08 requirements have implementation and test/doc coverage.
- Clear action is scoped to `ApplicationLog` and preserves settings/unrelated data.
- Pause/Start affects automatic live behavior in the current browser tab only.
- UI matches the approved Phase 70 UI-SPEC without adding dependencies or redesigning the page.
