# Phase 55: Admin Clear Operator Log - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 6 (3 new, 3 modified)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/admin/ui_router.py` (modify) | controller | request-response | `app/admin/ui_router.py` lines 338–406 (restore_confirm) | exact |
| `templates/admin/users_table.html` (modify) | component | request-response | `templates/admin/users_table.html` lines 44–80 (toggle/reset buttons) | exact |
| `templates/admin/users.html` (modify) | component | request-response | `templates/log/profile.html` (modal placeholder outside table) | role-match |
| `templates/admin/clear_log_modal.html` (new) | component | request-response | `templates/log/clear_log_modal.html` | exact |
| `templates/admin/clear_log_success.html` (new) | component | request-response | `templates/log/clear_log_success.html` | exact |
| `tests/test_admin_clear_log.py` (new) | test | request-response | `tests/test_clear_log.py` | exact |

---

## Pattern Assignments

### `app/admin/ui_router.py` — 3 new route handlers appended at end of file

**Primary analog:** `app/admin/ui_router.py` lines 338–407 (restore_confirm pattern)
**Secondary analog:** `app/qso/ui_router.py` lines 774–823 (Phase 54 clear log handlers)

**Import additions** — add at top of file alongside existing imports (lines 10–21):
```python
# These two lines must be ADDED to the existing imports block.
# verify_password IS already imported (line 18). QSO and clear_operator_log are NOT.
from app.qso.models import QSO
from app.qso.service import clear_operator_log
```

**GET modal handler pattern** (modeled on ui_router.py lines 265–279 + 774–791):
```python
@ui_router.get("/users/{username}/clear-log/modal", response_class=HTMLResponse)
async def admin_clear_log_modal(
    username: str,
    request: Request,
    current_user: User = Depends(require_admin_cookie),
):
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

**POST confirm handler pattern** (modeled on ui_router.py lines 338–406):
```python
@ui_router.post("/users/{username}/clear-log", response_class=HTMLResponse)
async def admin_clear_log_confirm(
    username: str,
    request: Request,
    password: Annotated[str, Form()],
    current_user: User = Depends(require_admin_cookie),
):
    target_user = await User.find_one({"username": username})
    if target_user is None:
        return HTMLResponse(content='<div id="admin-clear-log-modal"></div>', status_code=200)

    if not verify_password(password, current_user.hashed_password):  # admin's OWN password
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

**Cancel handler pattern** (modeled on ui_router.py lines 265–279, HX-Request branch):
```python
@ui_router.get("/users/{username}/clear-log/cancel", response_class=HTMLResponse)
async def admin_clear_log_cancel(
    username: str,
    _user: User = Depends(require_admin_cookie),
):
    return HTMLResponse(content='<div id="admin-clear-log-modal"></div>')
```

**Critical routing rule:** Append all three handlers at the END of the file (after line 407), after the existing restore handlers. FastAPI matches routes in registration order; appending avoids any path-param conflict with `/users/{username}/toggle` and `/users/{username}/reset-password`.

---

### `templates/admin/users_table.html` — add "Clear log" button inside actions div

**Analog:** `templates/admin/users_table.html` lines 44–80 (existing row action buttons)

**Insertion point:** Inside the existing `<div class="flex flex-wrap items-center gap-2">` at line 44, after the reset-password form closing `</form>` at line 79.

**Button pattern** (copy `btn-danger btn-sm` from Disable button at lines 45–63):
```html
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
          d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.021-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
  </svg>
  Clear log
</button>
```

**HTMX swap note:** Button uses `hx-swap="innerHTML"` (not `outerHTML`) because it targets the placeholder div. The modal fragment itself uses `hx-swap="outerHTML"` on the form submit to replace the placeholder with the full modal div.

---

### `templates/admin/users.html` — add modal placeholder div

**Analog:** Existing page structure at lines 102–124; placement mirrors Phase 54 pattern in `templates/log/profile.html`.

**Insertion point:** After the closing `</div>` of `max-w-5xl mx-auto space-y-6` (line 124), before `{% endblock %}` (line 125).

**Required addition:**
```html
</div>  {# closes max-w-5xl mx-auto space-y-6 #}

<div id="admin-clear-log-modal"></div>

{% endblock %}
```

**Critical placement rule:** The `<div id="admin-clear-log-modal"></div>` MUST be placed OUTSIDE the `max-w-5xl mx-auto space-y-6` container and OUTSIDE the `.card.overflow-hidden` table card. `hx-swap="outerHTML"` replaces this div entirely — if it were inside the container or `<tbody>`, the swap would corrupt adjacent DOM elements or be stripped by the browser's HTML parser.

---

### `templates/admin/clear_log_modal.html` (new)

**Analog:** `templates/log/clear_log_modal.html` (exact — same modal pattern, different copy and target IDs)
**Secondary analog:** `templates/admin/restore/password_modal.html` (admin modal CSS class usage)

**Analog file** (`templates/log/clear_log_modal.html`, full content):
```html
<div id="clear-log-modal">
  <div class="modal-backdrop"></div>
  <div class="modal-box" role="dialog" aria-modal="true" aria-labelledby="clear-log-modal-title">
    <h3 id="clear-log-modal-title" class="modal-title">Clear My Log</h3>
    <p class="modal-body">
      {% if count == 0 %}
        Your log is empty (0 QSOs). Submitting your password will complete without deleting anything.
      {% else %}
        This will permanently delete <strong>{{ count }} QSO(s)</strong> from your log.
        This cannot be undone.
      {% endif %}
    </p>
    {% if error %}
    <div class="alert alert-error" role="alert">{{ error }}</div>
    {% endif %}
    <form hx-post="/log/profile/clear" hx-target="#clear-log-modal" hx-swap="outerHTML">
      <div class="form-group">
        <label for="clear-log-password" class="form-label">Your password</label>
        <input id="clear-log-password" type="password" name="password" required
               autocomplete="current-password" class="form-control"
               placeholder="Enter your password to confirm">
      </div>
      <div class="modal-actions">
        <button type="submit" class="btn-danger">
          {% if count == 0 %}Confirm (0 QSOs){% else %}Delete {{ count }} QSOs{% endif %}
        </button>
        <button type="button" class="btn-secondary"
                onclick="document.getElementById('clear-log-modal').innerHTML = ''">
          Keep my log
        </button>
      </div>
    </form>
  </div>
</div>
```

**Phase 55 adaptation deltas:**
- `id="clear-log-modal"` → `id="admin-clear-log-modal"`
- `aria-labelledby` → `id="admin-clear-log-modal-title"`
- Title: "Clear My Log" → "Clear Operator Log"
- Body copy: references `{{ callsign }}` (the target operator) not "your log"
- `hx-post="/log/profile/clear"` → `hx-post="/admin/ui/users/{{ username }}/clear-log"`
- `hx-target="#clear-log-modal"` → `hx-target="#admin-clear-log-modal"`
- Cancel: replace `onclick=...` JS with `hx-get="/admin/ui/users/{{ username }}/clear-log/cancel"` + `hx-target="#admin-clear-log-modal"` + `hx-swap="outerHTML"` (admin pattern uses server-side cancel, not inline JS)
- Cancel button copy: "Keep my log" → "Keep log"
- Template variables: `count`, `error` (same) + `username` and `callsign` (new, for URL building and display)

---

### `templates/admin/clear_log_success.html` (new)

**Analog:** `templates/log/clear_log_success.html` (same pattern — success alert with deleted count)
**Secondary analog:** `templates/admin/restore/restore_success.html` (admin alert CSS class usage)

**Analog file** (`templates/log/clear_log_success.html`, full content):
```html
<div id="clear-log-modal">
  <div class="alert alert-success" role="alert">
    {% if deleted == 0 %}
      Done. Your log was already empty — nothing was deleted.
    {% else %}
      Done. {{ deleted }} QSO(s) deleted from your log.
    {% endif %}
  </div>
</div>
```

**Phase 55 adaptation deltas:**
- `id="clear-log-modal"` → `id="admin-clear-log-modal"` (matches placeholder ID for `outerHTML` swap)
- Body copy: references `{{ callsign }}` (target operator) instead of "your log"
  - Zero-QSO: "Operator {{ callsign }}'s log was already empty — nothing was deleted."
  - Nonzero: "Done. {{ deleted }} QSO(s) deleted from {{ callsign }}'s log."
- Template variables: `deleted` (same) + `callsign` (new)

---

### `tests/test_admin_clear_log.py` (new)

**Analog:** `tests/test_clear_log.py` (exact structure — same fixture pattern, same test shape)

**DB fixture pattern** (`tests/test_clear_log.py` lines 18–27):
```python
@pytest_asyncio.fixture(scope="function")
async def clear_log_db():
    client = AsyncMongoClient(
        "mongodb://localhost:27017", serverSelectionTimeoutMS=2000, directConnection=True
    )
    db = client["ollog_clearlog_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_clearlog_test")
    await client.aclose()
```

**Phase 55 adaptation:** Use database name `"ollog_admin_clearlog_test"` (distinct from `"ollog_clearlog_test"` used by Phase 54 — prevents fixture interference if both files run in the same pytest session).

**Admin cookie helper** (replaces `_auth_cookie` from `test_clear_log.py` lines 48–52):
```python
def _admin_cookie(admin: User) -> dict:
    token = create_access_token(
        {"sub": admin.username, "callsign": admin.callsign, "role": admin.role}
    )
    return {"Cookie": f"admin_token={token}"}
    # CRITICAL: cookie name is "admin_token" NOT "access_token"
    # require_admin_cookie reads Cookie(alias="admin_token") in app/auth/dependencies.py
```

**Operator cookie helper** (needed for seeding fixture that uses the operator app):
```python
def _operator_cookie(user: User) -> dict:
    token = create_access_token(
        {"sub": user.username, "callsign": user.callsign, "role": user.role}
    )
    return {"Cookie": f"access_token={token}"}
```

**QSO seeding helper** (copy from `test_clear_log.py` lines 55–69):
```python
async def _seed_qsos(operator_callsign: str, n: int) -> None:
    from datetime import datetime, timezone
    for i in range(n):
        qso = QSO(
            CALL=f"K{i}TEST",
            BAND="20m",
            MODE="FT8",
            QSO_DATE="20260507",
            TIME_ON="120000",
            qso_date_utc=datetime.now(timezone.utc),
            _operator=operator_callsign,
            _deleted=False,
        )
        await qso.insert()
```

**Admin fixture:**
```python
@pytest_asyncio.fixture(scope="function")
async def admin(admin_clear_log_db):
    user = User(
        username="adminuser",
        hashed_password=hash_password("adminpass"),
        callsign="W1ADM",
        role="admin",
        enabled=True,
    )
    await user.insert()
    return user
```

**Operator fixture:**
```python
@pytest_asyncio.fixture(scope="function")
async def operator(admin_clear_log_db):
    user = User(
        username="testop",
        hashed_password=hash_password("oppass"),
        callsign="W1AW",
        role="operator",
        enabled=True,
    )
    await user.insert()
    return user
```

**Test method pattern** (copy from `test_clear_log.py` lines 72–148 with admin cookie swap):
```python
@pytest.mark.asyncio
async def test_clear_correct_password(http_client, admin, operator, admin_clear_log_db):
    """ACLR-03: Correct admin password permanently deletes all target operator QSOs."""
    await _seed_qsos(operator.callsign, 5)
    resp = await http_client.post(
        f"/admin/ui/users/{operator.username}/clear-log",
        headers=_admin_cookie(admin),
        data={"password": "adminpass"},
    )
    assert resp.status_code == 200
    post_count = await QSO.find({"_operator": operator.callsign, "_deleted": False}).count()
    assert post_count == 0
```

**Test inventory** (mirrors Phase 54 test file structure):
- `test_clear_log_button_visible` — ACLR-01: button appears in `/admin/ui/users` page (uses admin cookie)
- `test_modal_shows_callsign_and_count` — ACLR-02: GET modal returns fragment with callsign, count, password field
- `test_clear_correct_password` — ACLR-03: correct password deletes all target operator QSOs
- `test_success_fragment_content` — ACLR-04: success fragment contains callsign and deleted count, uses `id="admin-clear-log-modal"`
- `test_wrong_password_no_delete` — ACLR-05: wrong password returns inline error, QSO count unchanged, `id="admin-clear-log-modal"` still in response
- `test_clear_zero_qsos` — ACLR-05 zero-QSO path: operator with no QSOs clears without error

---

## Shared Patterns

### Admin Cookie Authentication
**Source:** `app/admin/ui_router.py` lines 16, 23 and every protected route
**Apply to:** All three new route handlers
```python
from app.auth.dependencies import require_admin_cookie
# ...
_user: User = Depends(require_admin_cookie)   # read-only guard (no user data needed)
current_user: User = Depends(require_admin_cookie)  # when hashed_password is needed
```

### Password Verification Gate
**Source:** `app/admin/ui_router.py` lines 369–375 (restore_confirm)
**Apply to:** POST `/users/{username}/clear-log` handler
```python
# Password check — current_user already hydrated by require_admin_cookie
if not verify_password(password, current_user.hashed_password):
    return templates.TemplateResponse(
        request,
        "admin/clear_log_modal.html",
        {"username": username, "callsign": target_user.callsign, "count": count,
         "error": "Incorrect password. No QSOs were deleted."},
        status_code=200,  # MUST be 200 — HTMX 2.x drops body on 4xx
    )
```

### HTTP 200 for All HTMX Responses
**Source:** `app/admin/ui_router.py` lines 372–375 (restore password error), lines 393–396 (restore success)
**Apply to:** All branches of all three new handlers
```python
# All HTMX fragment responses — including error branches — MUST use status_code=200
# HTMX 2.x silently discards the response body for 4xx/5xx
status_code=200
```

### Path-Param Username Lookup Pattern
**Source:** `app/admin/ui_router.py` lines 163–170 (toggle_user) and lines 208–215 (reset_password)
**Apply to:** Both GET modal and POST confirm handlers
```python
user = await User.find_one({"username": username})
if user is None:
    users = await User.find_all().to_list()
    return templates.TemplateResponse(...)
```
**Phase 55 variant:** On not-found, return empty modal div at HTTP 200 instead of re-rendering the table (since the response target is `#admin-clear-log-modal`, not `#users-table-body`).

### HTMX outerHTML Modal Swap
**Source:** `templates/admin/restore/password_modal.html` lines 7–9
**Apply to:** `templates/admin/clear_log_modal.html` form
```html
<form
  hx-post="/admin/ui/users/{{ username }}/clear-log"
  hx-target="#admin-clear-log-modal"
  hx-swap="outerHTML"
>
```

### Server-Side Cancel (Admin Pattern)
**Source:** `templates/admin/restore/password_modal.html` lines 28–35 (cancel button) + `app/admin/ui_router.py` lines 265–279 (HX-Request branch)
**Apply to:** Cancel button in `templates/admin/clear_log_modal.html`
```html
<button
  type="button"
  class="btn-secondary"
  hx-get="/admin/ui/users/{{ username }}/clear-log/cancel"
  hx-target="#admin-clear-log-modal"
  hx-swap="outerHTML"
>Keep log</button>
```
**Note:** Phase 55 uses a DEDICATED cancel endpoint (not HX-Request detection on the modal endpoint) — simpler and avoids the dual-path logic in the restore handler.

---

## No Analog Found

All files have close analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `app/admin/`, `app/qso/`, `templates/admin/`, `templates/log/`, `tests/`
**Files scanned:** 12 (ui_router.py x2, users.html, users_table.html, password_modal.html, password_error.html, restore_success.html, clear_log_modal.html, clear_log_success.html, service.py, dependencies.py, test_clear_log.py)
**Pattern extraction date:** 2026-05-07
