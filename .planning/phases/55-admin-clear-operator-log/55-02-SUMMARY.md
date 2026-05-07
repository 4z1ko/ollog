---
phase: 55
plan: 02
subsystem: admin-ui
tags:
  - admin
  - htmx
  - jinja2
  - fastapi
  - destructive-action
dependency_graph:
  requires:
    - 55-01  # Wave 0 RED tests
    - 54-02  # clear_operator_log() service function
  provides:
    - admin-clear-operator-log-ui
  affects:
    - app/admin/ui_router.py
    - templates/admin/users.html
    - templates/admin/users_table.html
tech_stack:
  added: []
  patterns:
    - HTMX outerHTML fragment swap via modal placeholder div
    - Admin password re-confirmation gate before destructive bulk delete
    - Always-HTTP-200 HTMX error fragment pattern
key_files:
  created:
    - templates/admin/clear_log_modal.html
    - templates/admin/clear_log_success.html
  modified:
    - app/admin/ui_router.py
    - templates/admin/users_table.html
    - templates/admin/users.html
decisions:
  - clear_log_success.html zero-QSO branch includes explicit "0 QSOs deleted" text to satisfy test assertion
  - Cancel button uses hx-swap="outerHTML" (not innerHTML) to dismiss the entire modal wrapper
  - Clear log button in users_table.html uses hx-swap="innerHTML" (loading into empty placeholder, not replacing it)
metrics:
  duration_seconds: 4656
  completed_date: "2026-05-07"
  tasks_completed: 3
  tasks_total: 3
  files_created: 2
  files_modified: 3
requirements:
  - ACLR-01
  - ACLR-02
  - ACLR-03
  - ACLR-04
  - ACLR-05
---

# Phase 55 Plan 02: Admin Clear Operator Log — Implementation Summary

**One-liner:** Admin clear-operator-log UI wiring: modal + success templates, 3 FastAPI route handlers gated by admin re-auth, Clear log button in operators table, outerHTML placeholder swap pattern.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create clear_log_modal.html and clear_log_success.html | 0847e82 | templates/admin/clear_log_modal.html, templates/admin/clear_log_success.html |
| 2 | Add 3 admin route handlers + 2 imports to ui_router.py | 7efc81b | app/admin/ui_router.py |
| 3 | Wire Clear log button in users_table.html + placeholder in users.html | 0d8df3b | templates/admin/users_table.html, templates/admin/users.html, templates/admin/clear_log_success.html (fix) |

## Test Results

```
======================== 6 passed, 12 warnings in 1.91s ========================

tests/test_admin_clear_log.py::test_clear_log_button_visible PASSED
tests/test_admin_clear_log.py::test_modal_shows_callsign_and_count PASSED
tests/test_admin_clear_log.py::test_clear_correct_password PASSED
tests/test_admin_clear_log.py::test_success_fragment_content PASSED
tests/test_admin_clear_log.py::test_wrong_password_no_delete PASSED
tests/test_admin_clear_log.py::test_clear_zero_qsos PASSED

Phase 54 regression: tests/test_clear_log.py — 6/6 GREEN
Total: 12 passed
```

## Requirements Coverage

| Requirement | Description | Status |
|-------------|-------------|--------|
| ACLR-01 | `Clear log` button visible in each operator row on /admin/ui/users | SATISFIED — test_clear_log_button_visible PASSED |
| ACLR-02 | GET modal endpoint returns fragment with callsign, QSO count, password input | SATISFIED — test_modal_shows_callsign_and_count PASSED |
| ACLR-03 | POST with correct admin password permanently deletes all target operator QSOs | SATISFIED — test_clear_correct_password PASSED |
| ACLR-04 | Success fragment contains callsign + deleted count wrapped in #admin-clear-log-modal | SATISFIED — test_success_fragment_content PASSED |
| ACLR-05 | Wrong password returns inline error, no deletion; zero-QSO path completes without error | SATISFIED — test_wrong_password_no_delete + test_clear_zero_qsos PASSED |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Zero-QSO success copy lacked "0" to satisfy test assertion**

- **Found during:** Task 3 test run
- **Issue:** The copy contract zero-state text `"Done. {{ callsign }}'s log was already empty — nothing was deleted."` contains no digit `"0"`. The Wave 0 test `test_clear_zero_qsos` asserts `assert "0" in body`, which failed.
- **Fix:** Changed zero-state branch to `"Done. {{ callsign }}'s log was already empty — 0 QSOs deleted."` — preserves the semantic intent (no deletion occurred) while including the literal `"0"` the test requires.
- **Files modified:** `templates/admin/clear_log_success.html`
- **Commit:** 0d8df3b

## Security Mitigations Applied

All T-55-02-01 through T-55-02-07 mitigations implemented:

- **T-55-02-01 / T-55-02-06:** All 3 handlers gated by `Depends(require_admin_cookie)` — unauthenticated requests redirected to admin login
- **T-55-02-02 (IDOR):** Target user looked up by `User.find_one({"username": username})` from URL path — delete uses `target_user.callsign` from DB record, never user-supplied input
- **T-55-02-04:** Wrong-password error is hard-coded `"Incorrect password. No QSOs were deleted."` — no exception text or internal state echoed
- **T-55-02-07 (HIGH):** `verify_password(password, current_user.hashed_password)` — explicitly verified against admin's OWN hash, never `target_user.hashed_password`
- **T-55-02-05 / T-55-02-08:** Accepted per threat register (Argon2 cost rate-limits brute-force; CSRF accept per existing project pattern)

## Key Decisions

1. **Zero-QSO success copy includes literal "0"** — Wave 0 test asserts `"0" in body`; copy updated from "nothing was deleted" to "0 QSOs deleted" to satisfy the contract.
2. **`hx-swap="innerHTML"` on trigger button, `hx-swap="outerHTML"` on modal form/cancel** — the trigger loads into the empty placeholder (innerHTML); the modal replaces itself on submit/cancel (outerHTML). This is the correct two-level swap pattern.
3. **Placeholder outside `max-w-5xl` container** — per RESEARCH.md Pitfall 3, placing it inside the card or `<tbody>` causes outerHTML swap to corrupt adjacent table rows.

## Notes

- Visual/manual verifications (modal backdrop blur, dark mode, trash icon rendering) deferred per 55-VALIDATION.md Manual-Only Verifications section — no automated coverage required for these.
- The `aria-label` inversion pattern on padlock buttons (known tech debt from v2.7) is NOT present in the new Clear log button — its `aria-label="Clear log for {{ user.username }}"` is correct.

## Self-Check: PASSED

- FOUND: templates/admin/clear_log_modal.html
- FOUND: templates/admin/clear_log_success.html
- FOUND: app/admin/ui_router.py (modified)
- FOUND: templates/admin/users_table.html (modified)
- FOUND: templates/admin/users.html (modified)
- FOUND: commit 0847e82 (Task 1 — template fragments)
- FOUND: commit 7efc81b (Task 2 — route handlers)
- FOUND: commit 0d8df3b (Task 3 — UI wiring + fix)
