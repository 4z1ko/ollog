---
phase: 54-operator-clear-log
reviewed: 2026-05-06T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - app/qso/service.py
  - app/qso/ui_router.py
  - templates/log/clear_log_modal.html
  - templates/log/clear_log_success.html
  - templates/log/profile.html
  - tests/test_clear_log.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 54: Code Review Report

**Reviewed:** 2026-05-06T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

The clear-log feature (service function, UI router endpoints, modal templates, and tests) is
well-structured. Operator isolation is correct — `clear_operator_log` scopes the delete to
`_operator == operator` and the test explicitly verifies a second operator's QSOs are
untouched. Password re-verification before the destructive action is correct. HTMX status-200
contract is upheld throughout.

Two warnings require attention before shipping:

1. A duplicate-`id` HTML bug in the modal swap chain that can cause the success fragment to
   land inside the outer placeholder instead of replacing it, leaving a stale interactive
   modal target in the DOM.
2. Soft-deleted QSOs are never removed by "Clear Log", meaning the operation is not a true
   full log wipe for operators who have individually deleted QSOs — the count displayed and
   reported will not reflect those records, which may surprise users.

## Warnings

### WR-01: Duplicate `id="clear-log-modal"` creates unreliable HTMX swap target

**File:** `templates/log/profile.html:237` and `templates/log/clear_log_modal.html:1`

**Issue:** The profile page placeholder is `<div id="clear-log-modal"></div>` (profile.html:244).
The "Clear my log" button targets it with `hx-swap="innerHTML"` (profile.html:237), which
injects the modal fragment verbatim — including its own `<div id="clear-log-modal">` wrapper
(clear_log_modal.html:1). After injection there are **two elements** sharing `id="clear-log-modal"`
in the document: the outer placeholder and the injected inner wrapper.

The form inside the modal uses `hx-target="#clear-log-modal"` with `hx-swap="outerHTML"`.
HTMX resolves `#clear-log-modal` via `document.querySelector`, which returns the **first**
matching element — the outer placeholder. The success swap therefore replaces the outer
placeholder, which is the correct behaviour in Chrome/Firefox today. However, duplicate IDs
are invalid HTML (HTML spec §3.2.6), and the HTMX resolution order is not guaranteed across
browsers or HTMX versions. If the inner element is resolved instead, the success fragment
lands inside the outer div (which still carries `id="clear-log-modal"`), the outer placeholder
stays in the DOM, and a subsequent "Clear my log" click will open another modal over the
success banner.

**Fix — change the button swap to `outerHTML` and give the page placeholder a different
sentinel ID:**

In `templates/log/profile.html`, change the button attributes to:
```html
<button class="btn-danger"
        aria-label="Clear my log — opens confirmation modal"
        hx-get="/log/profile/clear/modal"
        hx-target="#clear-log-modal-placeholder"
        hx-swap="outerHTML">Clear my log</button>
```

And rename the placeholder:
```html
<div id="clear-log-modal-placeholder"></div>
```

In `templates/log/clear_log_modal.html` change the outer wrapper id to match what will be
the swap target for form responses (so HTMX outerHTML can still find the element):
```html
<div id="clear-log-modal-placeholder">
  ...
  <form hx-post="/log/profile/clear"
        hx-target="#clear-log-modal-placeholder"
        hx-swap="outerHTML">
```

In `templates/log/clear_log_success.html` update the wrapper id:
```html
<div id="clear-log-modal-placeholder">
  ...
</div>
```

This eliminates the duplicate-ID condition entirely. The placeholder always has a unique id;
the modal content (once loaded) uses that same id so the form's `outerHTML` swap continues
to work correctly, and there is never more than one element with the id at any point.

---

### WR-02: `clear_operator_log` silently skips soft-deleted QSOs, leaving orphaned records

**File:** `app/qso/service.py:261`

**Issue:** `clear_operator_log` deletes only documents where `_deleted: False`:
```python
result = await QSO.find(
    {"_operator": operator, "_deleted": False}
).delete_many()
```

Individual QSO deletions (via `DELETE /log/qsos/{qso_id}`) use soft-delete: they set
`_deleted: True` but leave the document in MongoDB. An operator who has soft-deleted some
QSOs then presses "Clear Log" will receive a count and a success banner reflecting only the
active QSOs. Their soft-deleted records remain in the database indefinitely with no UI path
to remove them.

This is an internal data hygiene concern (no data is exposed to other operators), but it
diverges from the user-visible promise "permanently delete all QSOs from your log." It also
means the database is never fully cleared for these operators, which is relevant if storage
or ADIF export behaviour is ever changed to include soft-deleted records.

**Fix — include soft-deleted records in the clear:**
```python
async def clear_operator_log(operator: str) -> int:
    """Permanently delete ALL QSOs (active and soft-deleted) for an operator."""
    result = await QSO.find(
        {"_operator": operator}
    ).delete_many()
    return result.deleted_count if result is not None else 0
```

If the intent is deliberately to leave soft-deleted records untouched, update the docstring
and the profile page copy to say "Permanently delete all *active* QSOs" so the behaviour
is explicit and the count shown in the modal matches exactly what will be removed.

---

## Info

### IN-01: `_seed_qsos` test helper is not decorated as an async helper — misleading call site

**File:** `tests/test_clear_log.py:55`

**Issue:** `_seed_qsos` is a bare `async def` function, not a fixture. All callers
`await _seed_qsos(...)` without issue, but the function is defined at module scope with no
`@pytest_asyncio.fixture` or `@pytest.fixture` decorator. This is correct and functional,
but the naming convention (`_seed_qsos`) and its inline import (`from datetime import ...`
inside the loop body rather than at function top or module level) may confuse future
contributors who expect helper functions to follow the project's import-at-top pattern.

**Fix:** Move the import to the module level (alongside the other imports at the top of the
test file):
```python
from datetime import datetime, timezone
```
Remove the redundant inline import inside `_seed_qsos`. No functional change; aligns with
module-level import convention in every other test file in the suite.

---

_Reviewed: 2026-05-06T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
