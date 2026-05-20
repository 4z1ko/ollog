---
phase: 54
plan: "01"
subsystem: qso-service, templates, tests
tags:
  - backend
  - service
  - tests
  - templates
  - htmx-fragments
dependency_graph:
  requires: []
  provides:
    - "app/qso/service.py:clear_operator_log"
    - "templates/log/clear_log_modal.html"
    - "templates/log/clear_log_success.html"
    - "tests/test_clear_log.py (6 tests)"
  affects:
    - "app/qso/service.py"
tech_stack:
  added: []
  patterns:
    - "Beanie find().delete_many() bulk delete with operator-isolation filter"
    - "HTMX outerHTML swap fragment pattern (outer div id matches swap target)"
    - "Wave 0 test-first: 5 integration tests RED, 1 service unit test GREEN"
key_files:
  created:
    - tests/test_clear_log.py
    - templates/log/clear_log_modal.html
    - templates/log/clear_log_success.html
  modified:
    - app/qso/service.py
decisions:
  - "clear_operator_log uses permanent delete (delete_many), not soft-delete toggle — per CLR-03"
  - "Filter includes both _operator and _deleted=False to prevent count drift (RESEARCH Pitfall 3 + A1)"
  - "result is not None guard handles Beanie DeleteMany | DeleteResult | None return shape"
  - "Cancel button uses inline JS onclick to avoid server round-trip for dismiss"
  - "Templates are pure HTML fragments (no extends/block) — HTMX outerHTML swap targets"
metrics:
  duration_minutes: 12
  completed_date: "2026-05-06"
  tasks_completed: 3
  files_modified: 4
requirements:
  - CLR-02
  - CLR-03
  - CLR-04
  - CLR-05
---

# Phase 54 Plan 01: Wave 0 — Service + Templates + Test Scaffolding Summary

**One-liner:** Bulk-delete service function `clear_operator_log(operator: str) -> int` with HTMX modal/success fragments and full 6-test scaffolding covering CLR-01–05.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wave 0 — Create failing test scaffolding | 74d95cf | tests/test_clear_log.py |
| 2 | Add clear_operator_log() async service function | b172581 | app/qso/service.py |
| 3 | Create modal + success HTMX fragment templates | 3c2cf27 | templates/log/clear_log_modal.html, templates/log/clear_log_success.html |

## Service Function Shipped

```python
# app/qso/service.py (appended at end of file)
async def clear_operator_log(operator: str) -> int:
    """Permanently delete all active (non-soft-deleted) QSOs for an operator.
    Returns the count of deleted documents.
    """
    result = await QSO.find(
        {"_operator": operator, "_deleted": False}
    ).delete_many()
    return result.deleted_count if result is not None else 0
```

Filter `{"_operator": operator, "_deleted": False}` enforces operator isolation (T-54-01) and excludes already-soft-deleted documents from the count so the modal count matches actual deletions.

## Template Contract

Both templates use `<div id="clear-log-modal">` as outer wrapper so HTMX `hx-swap="outerHTML"` correctly replaces the target element on the profile page.

| Template | Purpose | Outer id |
|----------|---------|----------|
| `templates/log/clear_log_modal.html` | Confirmation modal with count, password input, error slot | `clear-log-modal` |
| `templates/log/clear_log_success.html` | Success fragment showing deleted count | `clear-log-modal` |

Key attributes on modal:
- `role="dialog"`, `aria-modal="true"`, `aria-labelledby="clear-log-modal-title"` on `.modal-box`
- `hx-post="/log/profile/clear"` `hx-target="#clear-log-modal"` `hx-swap="outerHTML"` on form
- `autocomplete="current-password"` and `required` on password input
- Cancel button uses `onclick="document.getElementById('clear-log-modal').innerHTML = ''"` (no server round-trip)
- Both `count == 0` and `count > 0` branches present in modal and success templates

## Test Status

| Test | Requirement | Status |
|------|-------------|--------|
| test_clear_operator_log_service | (unit) | GREEN — passes immediately |
| test_danger_zone_visible | CLR-01 | RED — profile.html not yet modified |
| test_modal_shows_count | CLR-02 | RED — GET /log/profile/clear/modal not wired |
| test_clear_correct_password | CLR-03 | RED — POST /log/profile/clear not wired |
| test_success_fragment_count | CLR-04 | RED — POST /log/profile/clear not wired |
| test_wrong_password_no_delete | CLR-05 | RED — POST /log/profile/clear not wired |

The 5 integration tests are intentionally RED — this is the documented Wave 0 gap-creation pattern. Plan 02 closes all 5 by wiring two routes in `app/qso/ui_router.py` and adding the Danger Zone card to `templates/log/profile.html`.

## Deviations from Plan

None — plan executed exactly as written.

The `.env` file required by the worktree (not present in worktree checkout) was copied from the main repo to enable test execution. This is an infrastructure concern, not a deviation from plan logic.

## Known Stubs

None. No data flows to UI rendering in this plan — templates are Jinja2 fragments with context variables injected by routes that don't exist yet (Plan 02). The templates themselves are complete and correct.

## Threat Surface Scan

No new network endpoints introduced by this plan. `clear_operator_log()` is a pure service function — no route wiring in this plan. The two templates are static Jinja2 fragments.

T-54-01 mitigation (operator isolation filter) is present: filter `{"_operator": operator, "_deleted": False}` is a dict literal with `operator` sourced exclusively from the authenticated `user.callsign` (enforced in Plan 02 route handler via `get_current_user_cookie`).

## Self-Check: PASSED

File existence:
- tests/test_clear_log.py: FOUND
- app/qso/service.py (clear_operator_log): FOUND
- templates/log/clear_log_modal.html: FOUND
- templates/log/clear_log_success.html: FOUND

Commits:
- 74d95cf: FOUND (test scaffolding)
- b172581: FOUND (service function)
- 3c2cf27: FOUND (templates)
