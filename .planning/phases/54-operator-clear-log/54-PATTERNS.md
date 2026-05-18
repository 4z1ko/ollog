# Phase 54: Operator Clear Log — Pattern Map

**Mapped:** 2026-05-06
**Files analyzed:** 5 new/modified files
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/qso/service.py` | service | CRUD (bulk delete) | `app/qso/service.py` lines 200–244 (`get_qso_page` count pattern) | self-extension — exact ODM pattern |
| `app/qso/ui_router.py` | controller | request-response (HTMX fragment) | `app/admin/ui_router.py` lines 265–406 (restore GET + POST /restore/confirm) | exact — same two-step modal pattern |
| `templates/log/profile.html` | component | request-response (SSR) | `templates/log/profile.html` lines 161–224 (API Tokens card + outer container) | self-extension — exact card pattern |
| `templates/log/clear_log_modal.html` | component | request-response (HTMX fragment) | `templates/admin/restore/password_modal.html` (all 37 lines) | exact — same modal structure |
| `templates/log/clear_log_success.html` | component | request-response (HTMX fragment) | `templates/admin/restore/restore_success.html` (all 8 lines) | exact — same alert fragment pattern |
| `tests/test_clear_log.py` | test | request-response (ASGI integration) | `tests/test_log_view_notify_sound.py` (all 74 lines) | exact — cookie-auth UI route test pattern |

---

## Pattern Assignments

### `app/qso/service.py` — new `clear_operator_log()` function (service, CRUD)

**Analog:** `app/qso/service.py` lines 200–244 (`get_qso_page`) and lines 92–114 (`find_duplicate`)

**Imports pattern** — no new imports needed; `QSO` already imported at line 9:
```python
# app/qso/service.py lines 1-14
from __future__ import annotations
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional
from app.qso.models import QSO
if TYPE_CHECKING:
    from app.auth.models import User
logger = logging.getLogger(__name__)
```

**Core bulk-delete pattern** — mirrors the `.count()` call at line 242 but uses `.delete_many()`:
```python
# app/qso/service.py line 241-242 (count analog)
base = QSO.find(query)
total = await base.count()
```
New function to add at end of file:
```python
async def clear_operator_log(operator: str) -> int:
    """Permanently delete all active (non-soft-deleted) QSOs for an operator.

    Returns the count of deleted documents.
    Permanent delete (not soft-delete) per CLR-03 requirements.
    """
    result = await QSO.find(
        {"_operator": operator, "_deleted": False}
    ).delete_many()
    return result.deleted_count if result is not None else 0
```

**Filter pattern** — copy `{"_operator": operator, "_deleted": False}` from `find_duplicate` line 107:
```python
# app/qso/service.py lines 107-113
return await QSO.find_one({
    "_operator": operator,
    "CALL": call,
    "BAND": band,
    "MODE": mode,
    "_deleted": False,
    "qso_date_utc": {"$gte": window_start, "$lte": window_end},
})
```

---

### `app/qso/ui_router.py` — two new routes (controller, request-response)

**Analog:** `app/admin/ui_router.py` lines 265–406 (restore page + confirm)

**Imports pattern** — `verify_password` is already imported at line 28 of `app/qso/ui_router.py`; `Annotated`, `Form`, `Depends`, `Request`, `HTMLResponse` already present:
```python
# app/qso/ui_router.py lines 10-38 (existing — nothing to add)
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from app.auth.dependencies import get_current_operator_callsign_cookie, get_current_user_cookie
from app.auth.models import User
from app.auth.service import create_access_token, verify_password
from app.qso.models import QSO
from app.qso.service import build_qso_dict, find_duplicate, get_qso_page, parse_adif_datetime
```
After adding `clear_operator_log` to service, extend the `from app.qso.service import ...` line to include it.

**GET modal route pattern** — mirrors `app/admin/ui_router.py` lines 265–279:
```python
# app/admin/ui_router.py lines 265-279
@ui_router.get("/restore", response_class=HTMLResponse)
async def restore_page(
    request: Request,
    hx_request: Annotated[str | None, Header()] = None,
    _user: User = Depends(require_admin_cookie),
):
    if hx_request:
        return HTMLResponse(content='<div id="restore-modal"></div>')
    return templates.TemplateResponse(request, "admin/restore.html", {})
```
Phase 54 equivalent (count injection added, no HX-Request branch needed):
```python
@ui_router.get("/profile/clear/modal", response_class=HTMLResponse)
async def clear_log_modal(
    request: Request,
    user: User = Depends(get_current_user_cookie),
):
    """Return the confirmation modal fragment with current QSO count."""
    count = await QSO.find({"_operator": user.callsign, "_deleted": False}).count()
    return templates.TemplateResponse(
        request,
        "log/clear_log_modal.html",
        {"count": count, "error": None},
    )
```

**POST confirm route pattern** — mirrors `app/admin/ui_router.py` lines 338–406:
```python
# app/admin/ui_router.py lines 338-375 (password-verify branch)
@ui_router.post("/restore/confirm", response_class=HTMLResponse)
async def restore_confirm(
    request: Request,
    password: Annotated[str, Form()],
    temp_path: Annotated[str, Form()],
    current_user: User = Depends(require_admin_cookie),
):
    # Password check — current_user already hydrated by require_admin_cookie
    if not verify_password(password, current_user.hashed_password):
        return templates.TemplateResponse(
            request,
            "admin/restore/password_error.html",
            {"error": "Incorrect password", "temp_path": temp_path},
            status_code=200,
        )
    # ... action ...
    return templates.TemplateResponse(
        request,
        "admin/restore/restore_success.html",
        {"backup_path": auto_backup_path.name},
        status_code=200,
    )
```
Phase 54 equivalent:
```python
@ui_router.post("/profile/clear", response_class=HTMLResponse)
async def clear_log_confirm(
    request: Request,
    user: User = Depends(get_current_user_cookie),
    password: Annotated[str, Form()] = "",
):
    """Verify password and permanently delete all operator QSOs.

    Returns HTTP 200 always — HTMX 2.x won't swap on 4xx.
    """
    if not verify_password(password, user.hashed_password):
        count = await QSO.find({"_operator": user.callsign, "_deleted": False}).count()
        return templates.TemplateResponse(
            request,
            "log/clear_log_modal.html",
            {"count": count, "error": "Incorrect password — no QSOs were deleted."},
            status_code=200,
        )
    from app.qso.service import clear_operator_log
    deleted = await clear_operator_log(user.callsign)
    return templates.TemplateResponse(
        request,
        "log/clear_log_success.html",
        {"deleted": deleted},
        status_code=200,
    )
```

**Route registration order** — register both new routes AFTER the existing `GET /profile` and `POST /profile` handlers (currently at lines 575–654 of `ui_router.py`) to avoid path conflicts.

---

### `templates/log/profile.html` — Danger Zone card addition (component, SSR)

**Analog:** `templates/log/profile.html` lines 161–224 (API Tokens cards + closing container div)

**Addition location** — insert after line 223 (`</div>` closing the Active Tokens card) and before line 224 (`</div>` closing `max-w-3xl mx-auto space-y-6`):
```html
<!-- templates/log/profile.html lines 209-224 (existing — shows insertion context) -->
  <!-- API Tokens: active token list (lazy-loaded) -->
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">Active Tokens</h2>
    </div>
    <div class="card-body">
      <div id="token-list"
           hx-get="/log/tokens"
           hx-trigger="load"
           hx-swap="innerHTML">
        <p class="text-sm text-gray-500">Loading tokens...</p>
      </div>
    </div>
  </div>

</div>  ← INSERT BEFORE THIS LINE (closes max-w-3xl container)
{% endblock %}
```

**Card pattern** — copy card structure from the existing API Tokens card (lines 161–169):
```html
<!-- templates/log/profile.html lines 161-169 (card header pattern) -->
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">API Tokens</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
        Create tokens for REST API and UDP ADIF callers. ...
      </p>
    </div>
    <div class="card-body">
```

**New Danger Zone block + modal target:**
```html
  <!-- Danger Zone -->
  <div class="card">
    <div class="card-header">
      <h2 class="card-title">Danger Zone</h2>
    </div>
    <div class="card-body">
      <p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Permanently delete all QSOs from your log. This cannot be undone.
      </p>
      <button class="btn-danger"
              aria-label="Clear my log — opens confirmation modal"
              hx-get="/log/profile/clear/modal"
              hx-target="#clear-log-modal"
              hx-swap="innerHTML">
        Clear my log
      </button>
    </div>
  </div>

</div><!-- end max-w-3xl mx-auto space-y-6 -->

<!-- Modal target: OUTSIDE the card container — outerHTML swap must not disturb cards -->
<div id="clear-log-modal"></div>
```

---

### `templates/log/clear_log_modal.html` — NEW modal fragment (component, HTMX fragment)

**Analog:** `templates/admin/restore/password_modal.html` (all 37 lines) and `templates/admin/restore/password_error.html` (all 39 lines)

**Structural pattern** — outer wrapper `id` matches HTMX target; modal-backdrop + modal-box inside:
```html
<!-- templates/admin/restore/password_modal.html lines 1-37 (full file) -->
<div id="restore-modal">
  <div class="modal-backdrop"></div>
  <div class="modal-box">
    <h3 class="modal-title">Confirm Restore</h3>
    <p class="modal-body">Enter your admin password to restore the database. ...</p>
    <form
      hx-post="/admin/ui/restore/confirm"
      hx-target="#restore-modal"
      hx-swap="outerHTML"
    >
      <input type="hidden" name="temp_path" value="{{ temp_path }}">
      <div id="password-error-target"></div>
      <div class="form-group">
        <label for="restore-password">Password</label>
        <input id="restore-password" type="password" name="password" required
               autocomplete="current-password" class="form-control"
               placeholder="Your admin password">
      </div>
      <div class="modal-actions">
        <button type="submit" class="btn btn-danger">Restore</button>
        <button type="button" class="btn btn-secondary"
                hx-get="/admin/ui/restore" hx-target="#restore-modal" hx-swap="outerHTML">
          Cancel
        </button>
      </div>
    </form>
  </div>
</div>
```

**Error inline pattern** — from `templates/admin/restore/password_error.html` lines 12–14:
```html
<div id="password-error-target">
  <div class="alert alert-error" role="alert">{{ error }}</div>
</div>
```

**Key differences from admin analog:**
- Outer id: `clear-log-modal` (not `restore-modal`)
- Form action: `hx-post="/log/profile/clear"` `hx-target="#clear-log-modal"` `hx-swap="outerHTML"`
- No hidden `temp_path` field
- Count injected via `{{ count }}` in modal body and submit button label
- Cancel uses inline JS (`onclick="document.getElementById('clear-log-modal').innerHTML = ''"`) instead of server round-trip
- Modal needs `role="dialog"` `aria-modal="true"` `aria-labelledby="clear-log-modal-title"` on `.modal-box`

**Full new template:**
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

---

### `templates/log/clear_log_success.html` — NEW success fragment (component, HTMX fragment)

**Analog:** `templates/admin/restore/restore_success.html` (all 8 lines)

**Pattern:**
```html
<!-- templates/admin/restore/restore_success.html lines 1-8 (full file) -->
<div class="alert alert-success" role="alert">
  <strong>Restore complete.</strong>
  Database restored successfully.
  {% if backup_path %}
  An automatic backup was saved as <code>{{ backup_path }}</code> before the restore.
  {% endif %}
</div>
```

**Key differences:** Must be wrapped in `<div id="clear-log-modal">` so the `outerHTML` swap replaces the target element cleanly; uses `{{ deleted }}` count; no `<strong>` prefix label needed.

**Full new template:**
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

---

### `tests/test_clear_log.py` — NEW test file (test, request-response)

**Analog:** `tests/test_log_view_notify_sound.py` (all 74 lines) — cookie-auth UI route test pattern

**Fixture pattern** — copy DB fixture from `tests/test_log_view_notify_sound.py` lines 15–24:
```python
# tests/test_log_view_notify_sound.py lines 15-24
@pytest_asyncio.fixture(scope="function")
async def log_view_db():
    client = AsyncMongoClient(
        "mongodb://localhost:27017", serverSelectionTimeoutMS=2000, directConnection=True
    )
    db = client["ollog_log_view_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_log_view_test")
    await client.aclose()
```

**Operator fixture pattern** — copy from `tests/test_log_view_notify_sound.py` lines 27–35:
```python
# tests/test_log_view_notify_sound.py lines 27-35
@pytest_asyncio.fixture(scope="function")
async def operator(log_view_db):
    user = User(
        username="testop",
        hashed_password=hash_password("testpass"),
        callsign="W1AW",
    )
    await user.insert()
    return user
```

**ASGI client pattern** — copy from `tests/test_log_view_notify_sound.py` lines 38–42:
```python
# tests/test_log_view_notify_sound.py lines 38-42
@pytest_asyncio.fixture(scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

**Cookie-auth test pattern** — copy from `tests/test_log_view_notify_sound.py` lines 45–56:
```python
# tests/test_log_view_notify_sound.py lines 45-56
@pytest.mark.asyncio
async def test_notify_sound_false_injected(client, operator, log_view_db):
    token = create_access_token(
        {"sub": operator.username, "callsign": operator.callsign, "role": operator.role}
    )
    resp = await client.get(
        "/log/view",
        headers={"Cookie": f"access_token={token}"},
    )
    assert resp.status_code == 200
```

**Imports block** — copy from `tests/test_log_view_notify_sound.py` lines 1–12:
```python
import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient
from app.auth.models import User
from app.auth.service import create_access_token, hash_password
from app.main import app
from app.qso.models import QSO
```

---

## Shared Patterns

### Authentication (cookie-based)
**Source:** `app/qso/ui_router.py` line 26
**Apply to:** Both new routes in `ui_router.py`
```python
user: User = Depends(get_current_user_cookie)
```
Use `get_current_user_cookie` (not `get_current_operator_callsign_cookie`) because the full `User` document is needed to access `user.hashed_password` for verification and `user.callsign` for the delete filter.

### HTTP 200 for all HTMX fragments
**Source:** `app/qso/ui_router.py` lines 139–145 (submit_qso docstring) and `app/admin/ui_router.py` lines 292–293
**Apply to:** Both POST response branches (wrong password modal re-render + success fragment)
```python
# app/qso/ui_router.py lines 139-145
"""
Always returns HTTP 200 with an HTML partial — HTMX 2.x won't swap on 4xx.
"""
```
```python
# app/admin/ui_router.py lines 292-293
"""
Returns HTTP 200 always — HTMX 2.x ignores body on 4xx responses.
"""
```

### Password re-verification pattern
**Source:** `app/admin/ui_router.py` lines 369–375
**Apply to:** `POST /log/profile/clear` handler
```python
# app/admin/ui_router.py lines 369-375
if not verify_password(password, current_user.hashed_password):
    return templates.TemplateResponse(
        request,
        "admin/restore/password_error.html",
        {"error": "Incorrect password", "temp_path": temp_path},
        status_code=200,
    )
```

### Operator isolation in DB filter
**Source:** `app/qso/service.py` line 225
**Apply to:** Both count query and delete filter in `clear_operator_log()` and route handlers
```python
# app/qso/service.py line 225
query: dict = {"_operator": operator, "_deleted": False}
```

### `TemplateResponse` call signature
**Source:** `app/qso/ui_router.py` lines 47–51 (first route in file)
**Apply to:** All new `TemplateResponse` calls
```python
# Positional: request first, then template path string, then context dict
return templates.TemplateResponse(
    request,
    "log/clear_log_modal.html",
    {"count": count, "error": None},
)
```

---

## No Analog Found

All five files have close analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `app/admin/`, `app/qso/`, `app/auth/`, `templates/admin/restore/`, `templates/log/`, `tests/`
**Files scanned:** 11 source files read directly
**Pattern extraction date:** 2026-05-06
