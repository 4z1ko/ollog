---
phase: 55-admin-clear-operator-log
reviewed: 2026-05-07T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - tests/test_admin_clear_log.py
  - templates/admin/clear_log_modal.html
  - templates/admin/clear_log_success.html
  - app/admin/ui_router.py
  - templates/admin/users_table.html
  - templates/admin/users.html
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 55: Code Review Report

**Reviewed:** 2026-05-07T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the admin "clear operator log" feature: two new router endpoints (modal GET, confirm POST, cancel GET), two new templates, one updated users table partial, and the acceptance test suite. The security-critical path — admin password re-verification before destructive action — is correctly implemented and mirrors the existing pattern in `restore_confirm`. No authentication bypasses or injection vectors were found.

Two warnings relate to behavioral gaps: an HTMX swap mismatch that will silently break the modal interaction, and missing test coverage for a non-admin (operator) attempting to reach the clear-log endpoint. Two info items cover a test comment inaccuracy and a minor accessibility gap.

## Warnings

### WR-01: HTMX swap mode mismatch — modal never opens

**File:** `templates/admin/users_table.html:83`
**Issue:** The "Clear log" button fires `hx-get` with `hx-target="#admin-clear-log-modal"` and `hx-swap="innerHTML"`. However, the modal endpoint returns a fragment whose outermost element **is** `<div id="admin-clear-log-modal">`. With `innerHTML` swap the outer `<div id="admin-clear-log-modal">` wrapper in `users.html` keeps its id, and the inner content is replaced — which works for the initial open. But the form inside `clear_log_modal.html` submits with `hx-swap="outerHTML"`, and the cancel button also uses `hx-swap="outerHTML"`. When the confirm POST or cancel GET returns a fragment with `id="admin-clear-log-modal"`, HTMX is targeting the `#admin-clear-log-modal` element and swapping its `outerHTML`, replacing the whole element. On a re-open after a previous clear or cancel the element still exists, so the second open works. However, on the **first** open, the target `#admin-clear-log-modal` is the empty `<div id="admin-clear-log-modal"></div>` in `users.html` line 126. `hx-swap="innerHTML"` replaces the contents with the full fragment including its own `<div id="admin-clear-log-modal">` wrapper — producing a **nested duplicate id**, which is invalid HTML and will cause HTMX to mis-target subsequent swaps.

The consistent pattern used elsewhere (e.g., `restore_page` cancel: `hx-target="#restore-modal"`, `hx-swap="outerHTML"`) is `outerHTML` throughout, so that the entire placeholder element is replaced by the response fragment.

**Fix:** Change the trigger button in `users_table.html` to use `outerHTML`:
```html
<button
  hx-get="/admin/ui/users/{{ user.username }}/clear-log/modal"
  hx-target="#admin-clear-log-modal"
  hx-swap="outerHTML"
  ...
>
```
This makes the full round-trip consistent: open (outerHTML), submit (outerHTML), cancel (outerHTML).

---

### WR-02: No authorization check — operator can invoke clear-log against another operator's log

**File:** `app/admin/ui_router.py:444`
**Issue:** `admin_clear_log_confirm` is protected by `require_admin_cookie`, which enforces `role == "admin"`. This is correct. However, there is no corresponding test that a non-admin (operator) JWT cookie is rejected. The existing test fixture `operator` creates a user with `role="operator"` but never attempts to call the endpoint with that user's cookie. If `require_admin_cookie` has a bug or the dependency is ever accidentally swapped for a weaker one, there is no regression test to catch it.

This is not a bug in the current code — the dependency is sound — but the absence of an explicit rejection test is a gap in the safety net for a destructive, irreversible operation.

**Fix:** Add a test to `tests/test_admin_clear_log.py`:
```python
@pytest.mark.asyncio
async def test_clear_log_requires_admin(http_client, admin, operator):
    """Non-admin cookie must be rejected (403) for both modal and confirm endpoints."""
    op_token = create_access_token(
        {"sub": operator.username, "callsign": operator.callsign, "role": operator.role}
    )
    headers = {"Cookie": f"admin_token={op_token}"}

    resp = await http_client.get(
        f"/admin/ui/users/{operator.username}/clear-log/modal",
        headers=headers,
    )
    assert resp.status_code in (401, 403)

    resp = await http_client.post(
        f"/admin/ui/users/{operator.username}/clear-log",
        headers=headers,
        data={"password": "oppass"},
    )
    assert resp.status_code in (401, 403)
```

---

## Info

### IN-01: Test comment references wrong requirement number

**File:** `tests/test_admin_clear_log.py:162`
**Issue:** `test_clear_zero_qsos` is docstring-annotated `"""ACLR-05 zero-QSO path: ..."""`. ACLR-05 is already used for `test_wrong_password_no_delete` (line 146). This is a copy-paste error in the docstring — not a code defect, but it makes tracing test coverage against requirements ambiguous.

**Fix:** Assign a distinct requirement label, e.g. `ACLR-06`, or append a sub-label:
```python
"""ACLR-06: Operator with no QSOs clears without error (zero-QSO path)."""
```

---

### IN-02: Cancel button lacks explicit `type="button"` in modal form context

**File:** `templates/admin/clear_log_modal.html:29`
**Issue:** The cancel button inside the `<form>` element has `type="button"`, which is correct — it will not submit the form. This is already done properly. However, for parity with the project's other modal patterns (e.g., `password_modal.html`) it should also carry an explicit `formnovalidate` attribute so that browsers with aggressive form-validation behavior do not attempt to validate required fields when the cancel button is activated via keyboard. Currently the `<input name="password" required>` field could trigger browser validation on some paths before HTMX intercepts the click.

**Fix:**
```html
<button type="button" formnovalidate class="btn btn-secondary"
        hx-get="/admin/ui/users/{{ username }}/clear-log/cancel"
        hx-target="#admin-clear-log-modal"
        hx-swap="outerHTML">
  Keep log
</button>
```

---

_Reviewed: 2026-05-07T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
