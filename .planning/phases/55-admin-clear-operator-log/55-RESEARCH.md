# Phase 55: Admin Clear Operator Log — Research

**Researched:** 2026-05-07
**Domain:** FastAPI admin UI routes, HTMX modal fragments, Beanie ODM, Jinja2 templates
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** "Clear log" button placed inline with existing row actions — same `flex flex-wrap items-center gap-2` div as Enable/Disable and Reset Password. No separate row or visual section needed.
- **D-02:** Button copy is "Clear log" — matches the feature name used in ROADMAP.md and requirements throughout.
- **D-03:** Button style follows existing row danger action convention: `btn-danger btn-sm` (same as the Disable button).

### Claude's Discretion

- **Cancel mechanism:** Use the admin restore pattern — a server-side cancel endpoint returns an empty `<div id="admin-clear-log-modal"></div>` to clear the modal without a page reload. Consistent with `templates/admin/restore/password_modal.html`.
- **Post-success feedback:** After successful deletion, replace the modal with an inline success fragment (same approach as Phase 54 `clear_log_success.html`) — no table reload. The users table does not display QSO counts, so a table refresh adds no value.
- **Duplicate-ID fix:** Use `id="admin-clear-log-modal"` for both the placeholder div and the fragment outer wrapper. The placeholder is OUTSIDE the table so `outerHTML` swap does not disturb table rows.
- **Username routing:** Pass the target operator username via URL path param — `GET /admin/ui/users/{username}/clear-log/modal` and `POST /admin/ui/users/{username}/clear-log` — consistent with existing `/toggle` and `/reset-password` route pattern.
- **Service reuse:** Call `clear_operator_log(target_user.callsign)` from `app/qso/service` — already ships from Phase 54. Admin auth uses the admin's own `user.hashed_password` (not the target operator's).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ACLR-01 | Admin can trigger "Clear log" for any operator from the admin operators management page (alongside existing enable/disable/reset-password actions) | `templates/admin/users_table.html` row actions div identified; button placement and styling confirmed |
| ACLR-02 | Confirmation modal opens showing target operator's callsign and QSO count, requiring admin to re-enter their own password | GET modal route pattern from admin restore confirmed; QSO count query from Phase 54 service confirmed |
| ACLR-03 | On successful admin password verification, all QSOs for the target operator are permanently deleted | `clear_operator_log(operator: str) -> int` in `app/qso/service.py` confirmed present and working |
| ACLR-04 | Admin sees inline success confirmation with operator callsign and QSO count deleted | Success fragment pattern from Phase 54 `clear_log_success.html` confirmed; admin adapts to show callsign |
| ACLR-05 | Incorrect admin password shows inline error — deletion does not proceed | Password verify gate pattern from admin restore confirmed; `verify_password()` already imported in admin router |

</phase_requirements>

---

## Summary

Phase 55 is a pure extension of established patterns — no new dependencies, no new CSS, no new architectural decisions. The admin `ui_router.py` already implements the exact two-step modal pattern (GET modal → POST confirm) via the restore feature. Phase 54 already delivers `clear_operator_log()` as a reusable service function. This phase wires those two together in the admin context with three new routes and two new template fragments.

The key structural difference from Phase 54 is that the admin clears a *target operator's* log (not their own), so the target username is passed via URL path param, and the admin's own `user.hashed_password` is used for re-authentication. The QSO query must use `target_user.callsign` (from DB lookup), not the admin's callsign.

The cancel mechanism diverges slightly from Phase 54: instead of inline JS clearing the modal, the admin pattern uses a dedicated cancel endpoint that returns an empty div — consistent with `templates/admin/restore/password_modal.html`. The UI-SPEC has already locked this choice.

**Primary recommendation:** Follow the admin restore pattern verbatim for route structure and template structure. The only divergences are: (1) the modal body shows the target operator's callsign and QSO count, (2) the target username is a URL path param, (3) the service call passes `target_user.callsign` not `current_user.callsign`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Admin password re-verification | API/Backend | — | `verify_password()` must run server-side; password never sent to client or stored beyond the request |
| QSO count query for modal | API/Backend | — | Count is live server-side data; never trust a client-supplied count |
| Bulk QSO deletion | API/Backend | Database/Storage | `clear_operator_log()` calls Beanie `.delete_many()` against MongoDB |
| Modal rendering | Frontend Server (SSR) | — | Jinja2 TemplateResponse renders fragment with count/callsign injected server-side |
| Modal display/dismiss | Browser/Client | — | HTMX `hx-swap="outerHTML"` replaces placeholder div; server-side cancel route clears it |
| Admin authentication | API/Backend | — | `require_admin_cookie` dependency reads `admin_token` HttpOnly cookie; enforced before handler body |

---

## Standard Stack

All libraries already present — zero new dependencies.

### Core (already in pyproject.toml)
| Library | Purpose | Usage in Phase |
|---------|---------|----------------|
| FastAPI | Route handlers | 3 new routes in `app/admin/ui_router.py` |
| Beanie (async MongoDB ODM) | Database access | `clear_operator_log()` bulk delete via `QSO.find().delete_many()` |
| Jinja2 (via FastAPI) | Template rendering | 2 new fragment templates + 1 template modification |
| HTMX (browser) | Partial DOM swaps | `hx-get`/`hx-post`/`hx-swap="outerHTML"` on modal and cancel |
| pwdlib[argon2] | Password verification | `verify_password(plain, user.hashed_password)` in POST confirm handler |
| PyJWT | Admin cookie auth | Decoded by `require_admin_cookie` dependency (already active for all admin routes) |

**Installation:** No new packages. [VERIFIED: codebase grep]

---

## Architecture Patterns

### System Architecture Diagram

```
Admin browser
    │
    │ 1. Click "Clear log" for operator X
    │    hx-get /admin/ui/users/X/clear-log/modal
    ▼
GET /admin/ui/users/{username}/clear-log/modal
    │  require_admin_cookie  ──→  admin_token cookie  ──→  User (admin)
    │  DB: User.find_one(username=X)  ──→  target_user
    │  DB: QSO.find(_operator=target_user.callsign).count()  ──→  count
    │  TemplateResponse(clear_log_modal.html, {username, callsign, count})
    │
    ▼  innerHTML swap into #admin-clear-log-modal
    │
Admin enters password, submits form
    │    hx-post /admin/ui/users/X/clear-log
    ▼
POST /admin/ui/users/{username}/clear-log
    │  require_admin_cookie  ──→  User (admin, has hashed_password)
    │  DB: User.find_one(username=X)  ──→  target_user
    │
    ├── verify_password(password, current_user.hashed_password) FAILS
    │       DB: re-count QSOs for modal re-render
    │       TemplateResponse(clear_log_modal.html, {error=...})  HTTP 200
    │       outerHTML swap  ──→  modal re-renders with error
    │
    └── verify_password PASSES
            clear_operator_log(target_user.callsign)  ──→  deleted_count
            TemplateResponse(clear_log_success.html, {callsign, deleted})  HTTP 200
            outerHTML swap  ──→  modal replaced by success alert

Cancel path:
    Admin clicks "Keep log"
    hx-get /admin/ui/users/X/clear-log/cancel
    ──→  HTMLResponse('<div id="admin-clear-log-modal"></div>')  HTTP 200
    outerHTML swap  ──→  modal cleared
```

### Recommended File Structure

```
app/admin/
└── ui_router.py          # 3 new route handlers appended at end of file

templates/admin/
├── users.html            # Add <div id="admin-clear-log-modal"></div> after table card
├── users_table.html      # Add "Clear log" btn-danger btn-sm to row actions div
├── clear_log_modal.html  # NEW — modal fragment (mirrors restore/password_modal.html)
└── clear_log_success.html  # NEW — success fragment (mirrors clear_log_success.html)

tests/
└── test_admin_clear_log.py  # NEW — 5 integration tests + 0 service unit tests
                              # (service unit test already in test_clear_log.py Phase 54)
```

### Pattern 1: Admin UI Route with Path-Param Username Lookup

All existing admin user-action routes use this pattern. The new routes follow it exactly.

```python
# Source: app/admin/ui_router.py lines 156–197 (toggle_user)
@ui_router.post("/users/{username}/toggle", response_class=HTMLResponse)
async def toggle_user(
    username: str,
    request: Request,
    _user: User = Depends(require_admin_cookie),
):
    user = await User.find_one({"username": username})
    if user is None:
        users = await User.find_all().to_list()
        return templates.TemplateResponse(
            request,
            "admin/users_table.html",
            {"users": users, "error": f"User '{username}' not found"},
            status_code=404,
        )
    # ... action ...
```

**Phase 55 adaptation:** The GET modal and POST confirm both look up `target_user` via `username` path param. On not-found, return the empty modal div at HTTP 200 (not 404) — HTMX cannot swap on 4xx.

### Pattern 2: Admin Modal with Password Confirm (Existing Restore Flow)

```python
# Source: app/admin/ui_router.py lines 338–406

# GET: return modal fragment
@ui_router.get("/restore", response_class=HTMLResponse)
async def restore_page(request, hx_request=None, _user=Depends(require_admin_cookie)):
    if hx_request:
        return HTMLResponse(content='<div id="restore-modal"></div>')
    return templates.TemplateResponse(request, "admin/restore.html", {})

# POST: verify password, then act
@ui_router.post("/restore/confirm", response_class=HTMLResponse)
async def restore_confirm(request, password, temp_path, current_user=Depends(require_admin_cookie)):
    if not verify_password(password, current_user.hashed_password):
        return templates.TemplateResponse(
            request,
            "admin/restore/password_error.html",
            {"error": "Incorrect password", "temp_path": temp_path},
            status_code=200,  # HTMX 2.x requires 200
        )
    # ... act ...
    return templates.TemplateResponse(
        request, "admin/restore/restore_success.html",
        {"backup_path": ...}, status_code=200,
    )
```

**Phase 55 adaptation:**
- GET: modal endpoint is `/users/{username}/clear-log/modal` — returns fragment, not full page
- POST: password from admin's own `current_user.hashed_password`, target QSOs from `target_user.callsign`
- Cancel: dedicated `/users/{username}/clear-log/cancel` endpoint returning empty div (not the restore page)

### Pattern 3: HTMX Modal Placeholder Outside Table

```html
<!-- Source: CONTEXT.md D-Cancel + users.html analysis -->
<!-- Placeholder div AFTER the table card closing div, BEFORE {% endblock %} -->
<!-- This ensures outerHTML swap does not disturb tbody rows -->

<!-- In templates/admin/users.html: -->
  </div>  <!-- closes .card.overflow-hidden table card -->
</div>    <!-- closes max-w-5xl container -->

<div id="admin-clear-log-modal"></div>  <!-- OUTSIDE the container -->
{% endblock %}
```

**Critical:** The modal target div must be outside `<div class="max-w-5xl mx-auto space-y-6">`. Placing it inside the container would cause `outerHTML` swap to remove adjacent cards.

### Anti-Patterns to Avoid

- **Passing callsign from form body:** Never read the target callsign from a form field or query param — always look up `target_user = await User.find_one({"username": username})` using the URL path param and call `target_user.callsign`.
- **Using target_user.hashed_password for verification:** The admin is verifying their OWN password (`current_user.hashed_password`), not the target operator's password. The dependency `Depends(require_admin_cookie)` returns the admin user; the target user is fetched separately via path param.
- **Returning 4xx for HTMX fragments:** All admin HTMX response branches (wrong password, success, not-found) MUST return `status_code=200`. HTMX 2.x silently drops body on 4xx. [VERIFIED: existing codebase comment in STATE.md and all existing HTMX handlers]
- **Placing modal target inside the `<tbody>`:** The `hx-swap="outerHTML"` on the success/error fragment replaces `#admin-clear-log-modal` and its content. If this div is inside a `<tbody>`, the swap corrupts the table structure.
- **Calling clear_operator_log before password check:** Service call MUST be gated behind `verify_password` — wrong-password branch must never delete.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bulk delete of operator QSOs | Custom MongoDB aggregate or loop | `clear_operator_log(operator)` from `app/qso/service` | Already ships from Phase 54; handles `_deleted=False` filter and returns count |
| Password verification | Custom hash comparison | `verify_password(plain, user.hashed_password)` from `app/auth/service` | pwdlib Argon2 — timing-safe, already imported in admin router |
| Admin cookie authentication | Custom cookie parsing | `require_admin_cookie` dependency | Reads `admin_token` cookie, verifies JWT, checks `role == "admin"`, raises 403 for non-admins |
| Modal CSS | New Tailwind classes | `.modal-backdrop`, `.modal-box`, `.modal-title`, `.modal-body`, `.modal-actions`, `.btn-danger`, `.btn-secondary`, `.alert-error`, `.alert-success` | All already compiled into `static/css/output.css` — UI-SPEC confirms no new CSS needed |

**Key insight:** Every component of this phase already exists in the codebase — the only work is combining them with the correct wiring.

---

## Common Pitfalls

### Pitfall 1: Wrong User for Password Verification

**What goes wrong:** Calling `verify_password(password, target_user.hashed_password)` instead of `verify_password(password, current_user.hashed_password)`. The feature requires the admin to confirm with *their own* password.

**Why it happens:** The handler fetches both `current_user` (admin, from dependency) and `target_user` (operator, from path param DB lookup). It is easy to reach for `target_user.hashed_password` because it's closer in the code.

**How to avoid:** `current_user` comes from `Depends(require_admin_cookie)`. Always verify against `current_user.hashed_password`.

**Warning signs:** Test `test_admin_clear_log_wrong_password` passes when it should fail — means it's accidentally using the operator's (unknown) password hash.

### Pitfall 2: QSO Count Queried Against Admin's Callsign

**What goes wrong:** The modal GET handler queries `QSO.find({"_operator": current_user.callsign}).count()` instead of `QSO.find({"_operator": target_user.callsign}).count()`.

**Why it happens:** In Phase 54, the operator clears their own log, so `user.callsign` was the correct subject. In Phase 55, the subject is the *target* operator.

**How to avoid:** The modal GET handler must perform two DB calls: (1) `User.find_one({"username": username})` to get `target_user`, (2) `QSO.find({"_operator": target_user.callsign, "_deleted": False}).count()`.

**Warning signs:** Modal shows the admin's own QSO count (0 if admin has no QSOs) rather than the operator's count.

### Pitfall 3: Modal Target Inside the Table

**What goes wrong:** `<div id="admin-clear-log-modal"></div>` placed inside `<tbody id="users-table-body">` or inside the `.card.overflow-hidden` container. On `outerHTML` swap, the modal div is replaced by the success/error fragment, which contains a non-`<tr>` element inside a `<tbody>`.

**Why it happens:** Placing it near the row buttons feels natural. But `hx-swap="outerHTML"` replaces the entire div with the fragment, and DOM parsers may strip non-`<tr>` children from `<tbody>`.

**How to avoid:** Place `<div id="admin-clear-log-modal"></div>` AFTER the closing `</div>` of the `.card.overflow-hidden` table block and AFTER the closing `</div>` of `max-w-5xl mx-auto space-y-6`, before `{% endblock %}`. This mirrors exactly what Phase 54 did with `templates/log/profile.html`.

**Warning signs:** Success fragment disappears immediately (DOM strips it), or table rows vanish after a successful delete.

### Pitfall 4: Cancel Route Has Wrong Path / Wrong Response

**What goes wrong:** Cancel button fires `hx-get` to a path that doesn't exist or returns a full page instead of an empty div.

**Why it happens:** The restore pattern uses `hx-get="/admin/ui/restore"` with HX-Request detection to differentiate full-page vs fragment. The clear-log cancel is a dedicated endpoint, so there's no HX-Request branch needed — it always returns the empty div.

**How to avoid:** Register a dedicated `GET /admin/ui/users/{username}/clear-log/cancel` that always returns `HTMLResponse('<div id="admin-clear-log-modal"></div>')` with `status_code=200`, regardless of whether it's an HTMX request.

### Pitfall 5: Route Registration Order Conflict

**What goes wrong:** Registering `/users/{username}/clear-log` before or interleaved with `/users/{username}/toggle` and `/users/{username}/reset-password` causes unexpected routing behaviour with FastAPI's path parameter matching.

**Why it happens:** FastAPI matches routes in registration order. A path like `/users/{username}/clear-log/modal` could conflict if a prior catch-all is registered.

**How to avoid:** Append the three new route handlers at the END of `app/admin/ui_router.py`, after the existing backup/restore handlers — consistent with how Phase 54 appended to `app/qso/ui_router.py`.

---

## Code Examples

### GET Modal Handler (verified pattern from codebase)

```python
# Source: app/admin/ui_router.py (restore_confirm pattern) + CONTEXT.md
@ui_router.get("/users/{username}/clear-log/modal", response_class=HTMLResponse)
async def admin_clear_log_modal(
    username: str,
    request: Request,
    current_user: User = Depends(require_admin_cookie),
):
    """Return confirmation modal fragment with target operator's QSO count.

    Always HTTP 200 — HTMX 2.x will not swap on 4xx.
    """
    target_user = await User.find_one({"username": username})
    if target_user is None:
        return HTMLResponse(content='<div id="admin-clear-log-modal"></div>', status_code=200)

    count = await QSO.find(
        {"_operator": target_user.callsign, "_deleted": False}
    ).count()
    return templates.TemplateResponse(
        request,
        "admin/clear_log_modal.html",
        {"username": username, "callsign": target_user.callsign, "count": count, "error": None},
    )
```

### POST Confirm Handler (verified pattern from codebase)

```python
# Source: app/admin/ui_router.py restore_confirm + CONTEXT.md
@ui_router.post("/users/{username}/clear-log", response_class=HTMLResponse)
async def admin_clear_log_confirm(
    username: str,
    request: Request,
    password: Annotated[str, Form()],
    current_user: User = Depends(require_admin_cookie),
):
    """Verify admin password and delete all target operator's QSOs.

    Always HTTP 200 — HTMX 2.x ignores body on 4xx.
    current_user is the admin; target_user is the operator being cleared.
    Password check uses current_user.hashed_password (admin's own password).
    """
    from app.qso.service import clear_operator_log  # already imported if Phase 54 is done

    target_user = await User.find_one({"username": username})
    if target_user is None:
        return HTMLResponse(content='<div id="admin-clear-log-modal"></div>', status_code=200)

    if not verify_password(password, current_user.hashed_password):
        count = await QSO.find(
            {"_operator": target_user.callsign, "_deleted": False}
        ).count()
        return templates.TemplateResponse(
            request,
            "admin/clear_log_modal.html",
            {
                "username": username,
                "callsign": target_user.callsign,
                "count": count,
                "error": "Incorrect password. No QSOs were deleted.",
            },
            status_code=200,
        )

    deleted = await clear_operator_log(target_user.callsign)
    return templates.TemplateResponse(
        request,
        "admin/clear_log_success.html",
        {"callsign": target_user.callsign, "deleted": deleted},
        status_code=200,
    )
```

### Cancel Handler (verified pattern: restore page HX-Request branch)

```python
# Source: app/admin/ui_router.py restore_page HX-Request branch (lines 265-279)
@ui_router.get("/users/{username}/clear-log/cancel", response_class=HTMLResponse)
async def admin_clear_log_cancel(
    username: str,
    _user: User = Depends(require_admin_cookie),
):
    """Clear the modal without a page reload."""
    return HTMLResponse(content='<div id="admin-clear-log-modal"></div>')
```

### Import Addition for clear_operator_log

```python
# Source: app/admin/ui_router.py — no QSO import exists yet in this file
# ADD at top of file alongside other imports:
from app.qso.models import QSO
from app.qso.service import clear_operator_log
```

**Note:** `app/admin/ui_router.py` does NOT currently import `QSO` or `clear_operator_log`. Both must be added. `verify_password` IS already imported (line 18). [VERIFIED: codebase read]

### Row Action Button (verified from users_table.html)

```html
<!-- Source: templates/admin/users_table.html — append inside the existing div -->
<!-- Existing: <div class="flex flex-wrap items-center gap-2"> -->
<button
  hx-get="/admin/ui/users/{{ user.username }}/clear-log/modal"
  hx-target="#admin-clear-log-modal"
  hx-swap="innerHTML"
  aria-label="Clear log for {{ user.username }}"
  class="btn-danger btn-sm"
>
  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5"
       stroke="currentColor" aria-hidden="true">
    <path stroke-linecap="round" stroke-linejoin="round"
          d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21..." />
  </svg>
  Clear log
</button>
```

**Note:** The row button uses `hx-swap="innerHTML"` (not `outerHTML`) because it targets the *placeholder* div — the modal fragment then uses `outerHTML` on the form submit to replace the placeholder with itself.

### Modal Placeholder in users.html (verified from page structure)

```html
<!-- Source: templates/admin/users.html — insert AFTER the card.overflow-hidden closing div -->
<!-- and AFTER the max-w-5xl container closing div, BEFORE {% endblock %} -->

</div>  <!-- closes max-w-5xl mx-auto space-y-6 -->

<div id="admin-clear-log-modal"></div>

{% endblock %}
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Page reload after admin action | HTMX partial swap (`outerHTML`) | Phase 55 follows established Phase 54 + admin restore pattern — no server-side redirect |
| 4xx status for error fragments | HTTP 200 always for HTMX | Critical project rule; enforced by existing handlers |
| Server-round-trip cancel | Dedicated cancel endpoint returning empty div | Admin modal pattern (restore); already decided in CONTEXT.md |

---

## Runtime State Inventory

> Phase 55 is a greenfield extension of admin UI — no rename/refactor/migration.

Not applicable. No stored data, live service config, OS-registered state, secrets, or build artifacts reference anything being renamed or changed. New routes and templates are additive only.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `clear_operator_log()` is already present in `app/qso/service.py` from Phase 54 | Standard Stack / Code Examples | If Phase 54 is not yet executed, this function must be added first (or in the same plan) before the admin handler can call it |
| A2 | `app/admin/ui_router.py` does NOT yet import `QSO` or `clear_operator_log` | Code Examples | If these are already imported (unlikely but possible), duplicate import lines would cause a minor style issue but not a runtime error |
| A3 | The `<div id="admin-clear-log-modal"></div>` placeholder does not yet exist in `templates/admin/users.html` | Architecture Patterns | If already present from some prior work, adding it again creates a duplicate ID (browser ignores second instance, HTMX targeting becomes unreliable) |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

A1 is the only material risk: verify Phase 54 is complete before planning Phase 55 execution. A2 and A3 are low-risk and can be confirmed with a quick grep during plan execution.

---

## Open Questions

1. **Is Phase 54 fully executed before Phase 55 plans run?**
   - What we know: STATE.md says "stopped_at: Phase 55 UI-SPEC approved" and "Phase 54: Executing". Phase 54 plans exist and are complete in planning. The `clear_operator_log()` function is present in `app/qso/service.py` (confirmed by direct file read).
   - What's unclear: Whether Phase 54 code was actually executed (tests passing, commits made). The STATE.md progress shows 100% plans completed but the function IS present in the file.
   - Recommendation: Plan 01 executor should verify `grep "async def clear_operator_log" app/qso/service.py` before proceeding. If absent, add the function in Wave 0 of Phase 55 Plan 01 (it's a 10-line addition).

---

## Environment Availability

Step 2.6: SKIPPED — Phase 55 is purely code/template/config changes with no new external dependencies beyond the project's existing stack (MongoDB, FastAPI, HTMX). All tools verified present in prior phases.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` (pytest config section) |
| Quick run command | `uv run pytest tests/test_admin_clear_log.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ACLR-01 | "Clear log" button appears in admin row actions on `/admin/ui/users` | integration | `uv run pytest tests/test_admin_clear_log.py::test_clear_log_button_visible -x` | ❌ Wave 0 |
| ACLR-02 | GET modal endpoint returns fragment with callsign, QSO count, password field | integration | `uv run pytest tests/test_admin_clear_log.py::test_modal_shows_callsign_and_count -x` | ❌ Wave 0 |
| ACLR-03 | Correct admin password permanently deletes all target operator QSOs | integration | `uv run pytest tests/test_admin_clear_log.py::test_clear_correct_password -x` | ❌ Wave 0 |
| ACLR-04 | Success fragment shows operator callsign and QSO count deleted | integration | `uv run pytest tests/test_admin_clear_log.py::test_success_fragment_content -x` | ❌ Wave 0 |
| ACLR-05 | Wrong admin password → inline error, no deletion, modal stays open | integration | `uv run pytest tests/test_admin_clear_log.py::test_wrong_password_no_delete -x` | ❌ Wave 0 |
| ACLR-05 (zero-QSO) | Zero-QSO operator clears without error | integration | `uv run pytest tests/test_admin_clear_log.py::test_clear_zero_qsos -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_admin_clear_log.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_admin_clear_log.py` — covers ACLR-01 through ACLR-05 plus zero-QSO path

**Test fixture pattern for admin cookie auth:**

Admin UI routes use `admin_token` cookie (not `access_token`). The cookie name difference from Phase 54 is load-bearing. The token is a standard JWT created with `create_access_token`. The fixture pattern:

```python
def _admin_cookie(admin: User) -> dict:
    token = create_access_token(
        {"sub": admin.username, "callsign": admin.callsign, "role": admin.role}
    )
    return {"Cookie": f"admin_token={token}"}
    # NOTE: cookie name is "admin_token" NOT "access_token"
    # require_admin_cookie reads Cookie(alias="admin_token") via get_current_admin_cookie
```

[VERIFIED: `app/auth/dependencies.py` `get_current_admin_cookie` reads `admin_token: str | None = Cookie(default=None)`]

The test database name should be `ollog_admin_clearlog_test` (distinct from `ollog_clearlog_test` used by Phase 54) to prevent fixture interference if both test files run in the same session.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `require_admin_cookie` + `verify_password` (Argon2) |
| V3 Session Management | yes | Existing HttpOnly `admin_token` cookie (not modified) |
| V4 Access Control | yes | `require_admin_cookie` enforces `role == "admin"` before any handler body |
| V5 Input Validation | yes | `username` path param used only for `User.find_one` lookup — no SQL, no eval; password form field not echoed |
| V6 Cryptography | no | No new crypto — `verify_password` calls existing pwdlib Argon2 |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Admin clears wrong operator's log (IDOR via path param) | Tampering | `target_user = await User.find_one({"username": username})` — username from URL, not from form body. Operator isolation enforced at `clear_operator_log(target_user.callsign)` level. |
| Unauthenticated access to clear-log endpoints | Spoofing | `require_admin_cookie` dependency raises 401/403 before handler body; existing exception handler redirects to admin login |
| Admin password brute-force | Denial of Service | Argon2 verify cost (~hundreds of ms per attempt); no additional throttle needed at this scope |
| Error fragment leaks system information | Information Disclosure | Error string is hard-coded: "Incorrect password. No QSOs were deleted." — no exception text or internal state echoed |
| Cross-admin escalation (admin A clears admin B's QSOs) | Elevation of Privilege | Admin role is required but not restricted to specific admin; any admin can clear any operator. This is by design per REQUIREMENTS.md (no per-admin scoping) |
| CSRF on POST /clear-log | Spoofing | SameSite=lax on admin_token cookie mitigates most CSRF; HTMX requests originate same-origin; no additional CSRF token required per existing project pattern |

---

## Sources

### Primary (HIGH confidence)
- `app/admin/ui_router.py` — full file read; route patterns, import list, password verify pattern confirmed [VERIFIED: codebase read]
- `app/auth/dependencies.py` — `require_admin_cookie`, `get_current_admin_cookie`, cookie name `admin_token` confirmed [VERIFIED: codebase read]
- `app/qso/service.py` — `clear_operator_log()` function confirmed present, signature and filter confirmed [VERIFIED: codebase read]
- `templates/admin/users_table.html` — row actions div structure confirmed [VERIFIED: codebase read]
- `templates/admin/users.html` — page structure, table card placement, modal target insertion point confirmed [VERIFIED: codebase read]
- `templates/admin/restore/password_modal.html` — exact modal structure to mirror [VERIFIED: codebase read]
- `.planning/phases/55-admin-clear-operator-log/55-CONTEXT.md` — all locked decisions [VERIFIED: file read]
- `.planning/phases/55-admin-clear-operator-log/55-UI-SPEC.md` — component inventory, HTMX interaction flow, copy [VERIFIED: file read]
- `.planning/phases/54-operator-clear-log/54-01-PLAN.md` — fragment ID contracts, status_code=200 rule [VERIFIED: file read]
- `.planning/phases/54-operator-clear-log/54-02-PLAN.md` — route handler pattern, password verify gate [VERIFIED: file read]

### Secondary (MEDIUM confidence)
- `tests/test_clear_log.py` — cookie auth fixture pattern (`access_token` vs `admin_token` distinction identified) [VERIFIED: codebase read]
- `.planning/STATE.md` — critical build rules for HTMX, Tailwind, password verify [VERIFIED: file read]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, no new dependencies
- Architecture: HIGH — exact patterns verified from existing codebase
- Pitfalls: HIGH — derived from actual code analysis and Phase 54 experience
- Test patterns: HIGH — admin cookie name `admin_token` verified from `dependencies.py`

**Research date:** 2026-05-07
**Valid until:** 2026-06-07 (stable stack — no time-sensitive library versions)
