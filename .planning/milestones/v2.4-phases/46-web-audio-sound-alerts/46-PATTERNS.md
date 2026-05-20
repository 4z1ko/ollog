# Phase 46: Sound Playback Wiring — Pattern Map

**Mapped:** 2026-04-17
**Files analyzed:** 3 (2 modified, 1 new)
**Analogs found:** 3 / 3

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `templates/log/log.html` | template (client event handler) | event-driven | `templates/log/log.html` itself (lines 115–159) | exact — editing the existing IIFE `<script>` block |
| `app/qso/ui_router.py` | route handler | request-response | `app/qso/ui_router.py` — `profile_page()` / `submit_qso()` (lines 112–123, 125–212) | exact — same file, same dependency swap pattern already applied to adjacent handlers |
| `tests/test_log_view_notify_sound.py` | test | request-response | `tests/test_profile_api.py` (entire file) | role-match — same stack (httpx ASGITransport, pytest-asyncio, Beanie init, cookie-via-header fixture) |

---

## Pattern Assignments

### `templates/log/log.html` (template, event-driven)

**Analog:** `templates/log/log.html` lines 115–159 (the existing IIFE `<script>`)

This file is being modified, not replaced. The existing IIFE is the integration surface. All audio code must live inside it.

**Existing IIFE state variables** (lines 116–118 — copy this style for new state):
```javascript
(function () {
    var indicator = document.getElementById('live-indicator');
    var eventsFlowing = false;
```
Copy this `var` declaration style (no `let`/`const` inside the IIFE — the project uses `var` throughout the existing block). New Phase 46 state variables append immediately after `var eventsFlowing = false;`:
```javascript
    var AudioCtxClass = window.AudioContext || window.webkitAudioContext;
    var audioCtx = null;
    var userInteracted = false;
```

**Existing SSE event guard pattern** (lines 123–127 — the `new_qso` guard that all new audio code hooks into):
```javascript
    document.body.addEventListener('htmx:sseMessage', function (e) {
      if (!e.target || e.target.id !== 'log-table') return;
      if (!e.detail || e.detail.type !== 'new_qso') return;
```
The audio `playTone()` call is inserted **before** line 137 (`if (!document.getElementById('auto-refresh-ok')) return;`) so that tone fires independently of the HTMX auto-refresh guards. See RESEARCH.md Open Question 1.

**Existing auto-refresh guard block** (lines 137–139 — do NOT insert tone after this point):
```javascript
      if (!document.getElementById('auto-refresh-ok')) return;
      if (document.querySelector('#log-table input')) return;
      htmx.ajax('GET', '/log/view', { target: '#log-table', swap: 'innerHTML' });
```

**JS constant injection pattern** — `const NOTIFY_SOUND` must be declared inside the same `<script>` block, before the IIFE opening parenthesis, on its own line. The FOUC-prevention IIFE in `templates/base.html` lines 17–33 is the project-established model for inline JS constants injected via Jinja2:
```html
<script>
  const NOTIFY_SOUND = "{{ 'true' if notify_sound else 'false' }}";
  (function () {
    // ... existing IIFE contents unchanged ...
  })();
</script>
```
The explicit Jinja2 conditional `'true' if notify_sound else 'false'` is mandatory — Python booleans serialize as `True`/`False`, not `true`/`false` (see RESEARCH.md Pitfall 3).

**Complete new additions to the IIFE** — to be inserted in three locations:

1. After `var eventsFlowing = false;` (new state):
```javascript
    var AudioCtxClass = window.AudioContext || window.webkitAudioContext;
    var audioCtx = null;
    var userInteracted = false;

    function onFirstInteraction() {
      if (userInteracted) return;
      userInteracted = true;
      if (AudioCtxClass) {
        audioCtx = new AudioCtxClass();
      }
    }

    document.addEventListener('click', onFirstInteraction);
    document.addEventListener('keydown', onFirstInteraction);

    async function playTone(ctx) {
      if (ctx.state === 'suspended') {
        await ctx.resume();
      }
      var now = ctx.currentTime;
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(440, now);

      gain.gain.setValueAtTime(0, now);
      gain.gain.linearRampToValueAtTime(0.3, now + 0.01);
      gain.gain.linearRampToValueAtTime(0.3, now + 0.08);
      gain.gain.linearRampToValueAtTime(0, now + 0.11);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.12);
    }
```

2. Inside `htmx:sseMessage` handler, after the `eventsFlowing` block (lines 128–136) and **before** line 137 (`if (!document.getElementById...`):
```javascript
      if (NOTIFY_SOUND === 'true' && userInteracted && audioCtx) {
        playTone(audioCtx);
      }
```

---

### `app/qso/ui_router.py` (route handler, request-response)

**Analog:** `app/qso/ui_router.py` — `submit_qso()` handler (lines 125–212) and `profile_page()` handler (lines 567–577).

`submit_qso()` is the canonical model for `user: User = Depends(get_current_user_cookie)` + `callsign = user.callsign` extraction within the same file. `profile_page()` is the canonical model for the minimal form of `get_current_user_cookie` injection into a view.

**Existing import block** (lines 26–27 — both dependencies and User already imported, no changes needed):
```python
from app.auth.dependencies import get_current_operator_callsign_cookie, get_current_user_cookie
from app.auth.models import User
```

**Dependency swap pattern — before** (`log_view()` line 259, current):
```python
@ui_router.get("/view", response_class=HTMLResponse)
async def log_view(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    call: Optional[str] = Query(None),
    band: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort: str = Query("-qso_date_utc"),
    callsign: str = Depends(get_current_operator_callsign_cookie),   # REMOVE
):
```

**Dependency swap pattern — after** (copy from `submit_qso()` lines 137–146):
```python
    user: User = Depends(get_current_user_cookie),   # ADD
):
    callsign = user.callsign                          # ADD as first line of handler body
```

**Context dict injection pattern** — copy from `profile_page()` lines 573–576. The `notify_sound` key appends to the existing `ctx` dict (lines 300–315):
```python
    ctx = {
        "qsos": qsos,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "filters": { ... },
        "sort": sort,
        "callsign": callsign,
        "notify_sound": user.notify_sound,    # ADD
    }
```

**HTMX partial path** (lines 317–321 — unchanged, ctx passes through; `log_table.html` ignores the `notify_sound` key):
```python
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "log/log_table.html", ctx)

    return templates.TemplateResponse(request, "log/log.html", ctx)
```

---

### `tests/test_log_view_notify_sound.py` (test, request-response)

**Analog:** `tests/test_profile_api.py` (entire file — same fixture structure, same Beanie init pattern, same httpx ASGITransport + AsyncClient pattern)

**Imports pattern** (copy from `test_profile_api.py` lines 1–13):
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

**Test DB fixture pattern** (copy from `test_profile_api.py` lines 20–29 — use a distinct DB name to avoid collision):
```python
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

**Operator fixture pattern** (copy from `test_profile_api.py` lines 32–39):
```python
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

**Cookie auth pattern** — the new test calls a cookie-authenticated UI route (`GET /log/view`). The project uses HttpOnly cookies for UI routes; the test must send a `Cookie` header (not `Authorization`). Token is created with `create_access_token({"sub": operator.username, "callsign": operator.callsign, "role": operator.role})` to match `get_current_user_cookie`'s `payload.get("sub")` lookup. Send as:
```python
headers={"Cookie": f"access_token={token}"}
```
This mirrors how `get_current_user_cookie` reads `access_token: str | None = Cookie(default=None)` (see `app/auth/dependencies.py` lines 71–73).

**Core test pattern** (copy structure from `test_profile_api.py` `test_notify_sound_default_false` at line 206 — assert rendered HTML content):
```python
@pytest.mark.asyncio
async def test_notify_sound_false_injected(client, operator, log_view_db):
    """SND-01: log_view() injects NOTIFY_SOUND='false' when user.notify_sound is False."""
    token = create_access_token(
        {"sub": operator.username, "callsign": operator.callsign, "role": operator.role}
    )
    resp = await client.get(
        "/log/view",
        headers={"Cookie": f"access_token={token}"},
    )
    assert resp.status_code == 200
    assert 'const NOTIFY_SOUND = "false"' in resp.text


@pytest.mark.asyncio
async def test_notify_sound_true_injected(client, operator, log_view_db):
    """SND-01: log_view() injects NOTIFY_SOUND='true' when user.notify_sound is True."""
    operator.notify_sound = True
    await operator.save()

    token = create_access_token(
        {"sub": operator.username, "callsign": operator.callsign, "role": operator.role}
    )
    resp = await client.get(
        "/log/view",
        headers={"Cookie": f"access_token={token}"},
    )
    assert resp.status_code == 200
    assert 'const NOTIFY_SOUND = "true"' in resp.text
```

**httpx AsyncClient fixture** (copy from `test_profile_api.py` lines 48–52):
```python
@pytest_asyncio.fixture(scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

---

## Shared Patterns

### Cookie Authentication for UI Routes
**Source:** `app/auth/dependencies.py` lines 71–101 (`get_current_user_cookie`)
**Source:** `app/qso/ui_router.py` lines 567–577 (`profile_page()`)
**Apply to:** `log_view()` in `ui_router.py` (the dependency swap), and the new test file (cookie header construction)
```python
# Dependency (already imported at line 26 of ui_router.py)
user: User = Depends(get_current_user_cookie)
# Extract callsign from the full User document
callsign = user.callsign
```

### Jinja2 Boolean-to-JS-String Constant Injection
**Source:** `templates/base.html` lines 16–33 (FOUC-prevention IIFE — established pattern for inline Jinja2 constants in `<script>` blocks)
**Apply to:** `templates/log/log.html` `<script>` block
```html
const NOTIFY_SOUND = "{{ 'true' if notify_sound else 'false' }}";
```
The explicit conditional is mandatory — Python `True`/`False` must not reach the JS side.

### Test Database Fixture (function-scoped, isolated)
**Source:** `tests/test_profile_api.py` lines 20–29
**Apply to:** `tests/test_log_view_notify_sound.py`
Use a unique DB name (`ollog_log_view_test`) to avoid cross-test contamination. Always `drop_database` + `aclose()` in fixture teardown.

### IIFE `var` Style for Page-Level JS State
**Source:** `templates/log/log.html` lines 116–118
**Apply to:** New audio state variables in the same IIFE
Use `var` (not `let`/`const`) for IIFE-scoped mutable state — consistent with existing `var indicator` and `var eventsFlowing` declarations in the same block.

---

## No Analog Found

All three files have existing analogs. No entries.

---

## Metadata

**Analog search scope:** `templates/log/`, `app/qso/`, `app/auth/`, `tests/`
**Files read:** `templates/log/log.html`, `app/qso/ui_router.py`, `app/auth/dependencies.py`, `app/auth/models.py`, `templates/base_app.html`, `templates/base.html`, `tests/test_profile_api.py`, `tests/conftest.py`, `tests/test_auth.py`
**Pattern extraction date:** 2026-04-17
