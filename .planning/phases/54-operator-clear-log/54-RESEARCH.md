# Phase 54: Operator Clear Log — Research

**Researched:** 2026-05-06
**Domain:** FastAPI + Beanie bulk delete, HTMX modal pattern, cookie-auth password verification
**Confidence:** HIGH

---

## Summary

Phase 54 is a focused feature with no new dependencies and no new CSS classes needed. Every
building block exists in the project: the password-verification function, the cookie-auth
dependency, the modal component classes, the Beanie bulk-delete API, and the HTMX swap
pattern for modals. The primary work is wiring these pieces together in `app/qso/ui_router.py`
and `templates/log/profile.html`.

The clearest precedent is the admin restore flow (`app/admin/ui_router.py` + `templates/admin/restore/`).
That flow does two-step HTMX: a GET loads a modal fragment into a dedicated target div, and a
POST from inside the modal replaces that div with either a success or error fragment. Phase 54
replicates this pattern verbatim, adapted for the operator context.

**Primary recommendation:** Two new routes in `app/qso/ui_router.py` (`GET /log/profile/clear/modal`
and `POST /log/profile/clear`) + one new `<div id="clear-log-modal">` in `profile.html` +
one new `clear_operator_log()` function in `app/qso/service.py`. No new files outside the
existing module hierarchy are required.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| QSO count query | API / Backend | — | Must be operator-scoped; browser must not supply count |
| Password verification | API / Backend | — | Argon2 compare must run server-side |
| Bulk permanent delete | API / Backend (DB) | — | `delete_many` on MongoDB; irreversible, so must be atomic |
| Modal HTML fragment | Frontend Server (SSR) | — | Server injects count into modal body at render time |
| Danger Zone card | Browser / Client | — | Static HTML addition to profile.html |
| Cancel button | Browser / Client | — | Inline JS clears modal div; no round-trip needed |

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLR-01 | "Danger Zone" section with "Clear my log" button visible on `/log/profile` | Add card to `profile.html`; no backend change |
| CLR-02 | Clicking button opens modal showing exact QSO count and password field | `GET /log/profile/clear/modal` queries count and returns modal fragment |
| CLR-03 | Correct password → all operator QSOs permanently deleted | `clear_operator_log()` uses `QSO.find().delete_many()` returning `deleted_count` |
| CLR-04 | Success: modal closes, inline success message shows count deleted | Success fragment replaces `#clear-log-modal` via `hx-swap="outerHTML"` |
| CLR-05 | Wrong password → inline error inside modal, no deletion | `verify_password()` false branch returns modal HTML with error populated |
</phase_requirements>

---

## Standard Stack

### Core (all already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pwdlib[argon2] | installed | `verify_password(plain, hashed)` | Already in `app/auth/service.py` — exact function used for admin restore |
| beanie | installed | `QSO.find({}).count()` and `QSO.find({}).delete_many()` | Project ODM; bulk ops confirmed available [VERIFIED: runtime inspection] |
| htmx | 2.x | Partial DOM swap for modal loading and replacement | Project standard; HTMX 2.x requires HTTP 200 for body swap |
| Jinja2 | installed | Server-renders modal with QSO count injected | Project templating layer |
| Tailwind CSS | v3 | All component classes already compiled | No new classes needed per UI-SPEC |

### No new dependencies needed
This phase adds zero entries to `pyproject.toml` or `package.json`.

---

## Architecture Patterns

### System Architecture Diagram

```
Browser                   FastAPI (port 8000)             MongoDB
  |                            |                              |
  | GET /log/profile            |                              |
  |--------------------------->|                              |
  |  profile.html + empty       |                              |
  |  #clear-log-modal div       |                              |
  |<---------------------------|                              |
  |                            |                              |
  | [click "Clear my log"]     |                              |
  | hx-get /log/profile/clear/modal                           |
  |--------------------------->|                              |
  |                            | QSO.find(_operator=X,        |
  |                            |   _deleted=False).count()   |
  |                            |----------------------------->|
  |                            |<-- count N ------------------|
  |                            | render modal fragment        |
  |                            | (count injected)             |
  | modal HTML (HTTP 200)      |                              |
  |<---------------------------|                              |
  | [modal visible in DOM]     |                              |
  |                            |                              |
  | POST /log/profile/clear    |                              |
  | password=<input>           |                              |
  |--------------------------->|                              |
  |                            | verify_password(plain, hash) |
  |                            | [if wrong]                   |
  |                            | return modal+error (HTTP 200)|
  |<---------------------------|                              |
  |                            | [if correct]                 |
  |                            | QSO.find(_operator=X,        |
  |                            |   _deleted=False).delete_many|
  |                            |----------------------------->|
  |                            |<-- DeleteResult.deleted_count|
  |                            | return success frag (HTTP 200)|
  | success fragment replaces  |                              |
  | #clear-log-modal outerHTML |                              |
  |<---------------------------|                              |
```

### Recommended File Changes
```
app/qso/
├── service.py          # + clear_operator_log(operator) -> int
└── ui_router.py        # + GET /log/profile/clear/modal
                        # + POST /log/profile/clear

templates/log/
├── profile.html        # + Danger Zone card + #clear-log-modal target div
├── clear_log_modal.html     # NEW: modal fragment (count, password, error slot)
├── clear_log_success.html   # NEW: success alert fragment
└── (no other new files)
```

### Pattern 1: Beanie Count + Bulk Delete

**What:** Query active (non-deleted) QSOs for an operator, get count, then delete them all.
**When to use:** Both count (for modal display) and delete (on confirmation) use the same filter.

```python
# Source: verified via runtime inspection of beanie.odm.interfaces.find.FindMany

async def clear_operator_log(operator: str) -> int:
    """Permanently delete all active QSOs for an operator.

    Returns the count of deleted documents.
    Permanent (not soft-delete) per CLR-03 requirements.
    """
    result = await QSO.find(
        {"_operator": operator, "_deleted": False}
    ).delete_many()
    return result.deleted_count if result is not None else 0
```

Count-only query (for modal, without deleting):
```python
# Source: existing pattern in app/qso/service.py line 242 (get_qso_page uses .count())
count = await QSO.find({"_operator": operator, "_deleted": False}).count()
```

**Important:** `delete_many()` returns `pymongo.results.DeleteResult | None`. The `.deleted_count`
attribute is safe to access when `acknowledged=True` (the default for non-unacknowledged writes).
[VERIFIED: runtime inspection of `pymongo.results.DeleteResult`]

### Pattern 2: HTMX Two-Step Modal (GET then POST)

**What:** A GET loads the modal fragment into a target div; a POST from inside the modal
replaces that div with success or re-renders with error.

**Reference implementation:** `templates/admin/restore/password_modal.html` + `ui_router.py`
`POST /restore/confirm`. Phase 54 mirrors this exactly. [VERIFIED: codebase]

Key HTMX attributes:
- Trigger button in Danger Zone card: `hx-get="/log/profile/clear/modal"` `hx-target="#clear-log-modal"` `hx-swap="innerHTML"`
- Form inside modal: `hx-post="/log/profile/clear"` `hx-target="#clear-log-modal"` `hx-swap="outerHTML"`
- Cancel button: `type="button"` `onclick="document.getElementById('clear-log-modal').innerHTML = ''"` — no server round-trip [VERIFIED: UI-SPEC]

### Pattern 3: Cookie-Auth Password Re-Verification

**What:** The authenticated user's password is re-verified as a second factor for destructive operations.
**Reference implementation:** `app/admin/ui_router.py` `POST /restore/confirm`:

```python
# Source: app/admin/ui_router.py lines 369-375 [VERIFIED: codebase]
# Current user already hydrated by Depends(require_admin_cookie)
if not verify_password(password, current_user.hashed_password):
    return templates.TemplateResponse(
        request,
        "admin/restore/password_error.html",
        {"error": "Incorrect password", "temp_path": temp_path},
        status_code=200,
    )
```

For Phase 54, operator route equivalent:
```python
# user is already hydrated by Depends(get_current_user_cookie)
if not verify_password(password, user.hashed_password):
    return templates.TemplateResponse(
        request,
        "log/clear_log_modal.html",
        {"count": count, "error": "Incorrect password — no QSOs were deleted."},
        status_code=200,
    )
```

The `verify_password` import: `from app.auth.service import verify_password` — already imported
in `ui_router.py` at line 28. [VERIFIED: codebase]

### Pattern 4: HTTP 200 Required for HTMX Error Fragments

**What:** All error and success HTML fragments must return `status_code=200`.
**Why:** HTMX 2.x silently drops response body on 4xx. [VERIFIED: STATE.md "Critical Build Rules"]

This applies to both the wrong-password modal re-render and the success fragment.

### Pattern 5: QSO Count Context in Modal GET

The modal GET route must query the count server-side (never trust a client-supplied number).
The count is injected into the Jinja2 template context for display in `.modal-body` and
on the submit button label.

```python
# GET /log/profile/clear/modal
@ui_router.get("/profile/clear/modal", response_class=HTMLResponse)
async def clear_log_modal(
    request: Request,
    user: User = Depends(get_current_user_cookie),
):
    count = await QSO.find({"_operator": user.callsign, "_deleted": False}).count()
    return templates.TemplateResponse(
        request,
        "log/clear_log_modal.html",
        {"count": count, "error": None},
    )
```

### Anti-Patterns to Avoid
- **Client-supplied QSO count:** Never accept count from the form body. Always re-query server-side.
- **Hard-deleting via `qso.delete()` in a loop:** Use `QSO.find({...}).delete_many()` — one round-trip, not N.
- **Soft-delete for clear log:** Requirements say permanent delete. Do NOT set `_deleted: True`. Remove documents entirely.
- **4xx responses for HTMX error fragments:** HTMX 2.x drops body on 4xx — always return HTTP 200.
- **Deleting soft-deleted QSOs:** The filter `{"_operator": operator, "_deleted": False}` excludes
  already-soft-deleted records; `deleted_count` will correctly reflect only active records removed.
  Whether to also delete soft-deleted records is [ASSUMED] to be out of scope — the requirements
  say "all of the operator's QSOs" but the existing model treats `_deleted: True` records as invisible
  to the operator. Safest interpretation: only delete `_deleted: False` records (what the operator sees).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing comparison | Custom bcrypt/sha256 compare | `verify_password()` from `app/auth/service` | Argon2 is constant-time via pwdlib; already in scope |
| Bulk delete with count | Python loop over `qso.delete()` | `QSO.find({...}).delete_many()` | Single MongoDB round-trip; returns `DeleteResult.deleted_count` |
| Modal overlay with blur | Custom JS modal library | `.modal-backdrop` + `.modal-box` CSS classes | Already in `input.css`; identical to restore modal |
| Count before delete | Separate aggregation pipeline | `.count()` on the same Beanie query | Beanie wraps `countDocuments` — simple and indexed |

---

## Common Pitfalls

### Pitfall 1: Count Race (count differs between modal load and confirm)
**What goes wrong:** Modal shows "5 QSOs" but 2 more arrive via UDP between GET and POST.
**Why it happens:** Count is fetched at GET time; delete fires at POST time.
**How to avoid:** Return `deleted_count` from `delete_many()` as the authoritative number in
the success message. The UI-SPEC already specifies "Done. {N} QSO(s) deleted" using the
actual delete result, not the modal's displayed count.
**Warning signs:** Success message count differs from modal count — this is expected and correct.

### Pitfall 2: `delete_many()` Returns None
**What goes wrong:** `result.deleted_count` raises `AttributeError: 'NoneType'`.
**Why it happens:** Beanie's `delete_many()` return type is `DeleteMany | DeleteResult | None`.
For unacknowledged writes it can be None.
**How to avoid:** Default MongoDB write concern is acknowledged. Guard with:
`return result.deleted_count if result is not None else 0`

### Pitfall 3: Wrong Filter Includes Already-Soft-Deleted Records
**What goes wrong:** `deleted_count` is higher than the visible QSO count — confuses operators.
**Why it happens:** `QSO.find({"_operator": operator})` without `"_deleted": False` hits
all records including those already soft-deleted.
**How to avoid:** Always include `"_deleted": False` in the filter for both count and delete.

### Pitfall 4: Route Path Conflict with Profile Page
**What goes wrong:** `GET /log/profile/clear/modal` might shadow or conflict with profile page routing.
**Why it happens:** FastAPI routes are matched in registration order.
**How to avoid:** Register `GET /log/profile/clear/modal` and `POST /log/profile/clear` AFTER
the existing `GET /log/profile` and `POST /log/profile` routes — or use distinct path segments
(which `/profile/clear/modal` already provides).

### Pitfall 5: `#clear-log-modal` Target Placement
**What goes wrong:** HTMX swaps inside a profile card instead of the dedicated modal target.
**Why it happens:** If `#clear-log-modal` is inside a card, the `outerHTML` swap removes the card.
**How to avoid:** `<div id="clear-log-modal"></div>` must be a sibling of the profile card
container (after the closing `</div>` of `max-w-3xl mx-auto space-y-6`), not nested inside it.
The UI-SPEC explicitly documents this: "A dedicated `<div id="clear-log-modal"></div>` target
lives outside the profile card container". [VERIFIED: UI-SPEC]

### Pitfall 6: Missing `role="dialog"` on Modal
**What goes wrong:** Screen readers don't announce the modal as a dialog.
**Why it happens:** Generic `<div>` doesn't convey modal semantics.
**How to avoid:** UI-SPEC requires `role="dialog"`, `aria-modal="true"`, `aria-labelledby="clear-log-modal-title"`.
[VERIFIED: UI-SPEC]

---

## Code Examples

### Service function — clear_operator_log

```python
# Pattern source: existing QSO.find().count() in service.py + beanie delete_many() API
# [VERIFIED: runtime inspection of beanie.odm.interfaces.find.FindMany]

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

### Route — GET modal (count injection)

```python
# Pattern: mirrors admin restore GET /restore (which returns modal or bare div)
# [VERIFIED: app/admin/ui_router.py lines 265-279]

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

### Route — POST confirm (password verify + delete)

```python
# Pattern: mirrors admin restore POST /restore/confirm
# [VERIFIED: app/admin/ui_router.py lines 338-406]

@ui_router.post("/profile/clear", response_class=HTMLResponse)
async def clear_log_confirm(
    request: Request,
    user: User = Depends(get_current_user_cookie),
    password: Annotated[str, Form()] = "",
):
    """Verify password and permanently delete all operator QSOs.

    Returns HTTP 200 always — HTMX 2.x won't swap on 4xx.
    Wrong password: return modal with error (modal stays open).
    Correct password: return success fragment (modal replaced).
    """
    # Wrong password — re-render modal with error populated
    if not verify_password(password, user.hashed_password):
        count = await QSO.find({"_operator": user.callsign, "_deleted": False}).count()
        return templates.TemplateResponse(
            request,
            "log/clear_log_modal.html",
            {"count": count, "error": "Incorrect password — no QSOs were deleted."},
            status_code=200,
        )

    # Correct password — delete and return success fragment
    from app.qso.service import clear_operator_log
    deleted = await clear_operator_log(user.callsign)

    return templates.TemplateResponse(
        request,
        "log/clear_log_success.html",
        {"deleted": deleted},
        status_code=200,
    )
```

### Template — clear_log_modal.html structure

```html
<!-- Source: mirrors templates/admin/restore/password_modal.html structure -->
<!-- [VERIFIED: codebase + UI-SPEC] -->
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

### Template — clear_log_success.html

```html
<!-- Source: mirrors templates/admin/restore/restore_success.html structure -->
<!-- [VERIFIED: codebase + UI-SPEC] -->
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

### Template — Danger Zone card addition to profile.html

```html
<!-- Add after the closing </div> of the Active Tokens card, before </div> of max-w-3xl container -->
<!-- [VERIFIED: UI-SPEC layout section] -->

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

<!-- Modal target: must be OUTSIDE the card container -->
<div id="clear-log-modal"></div>
```

---

## Environment Availability

Step 2.6: SKIPPED — this phase is code-only. No external tools, CLIs, databases, or services
beyond the already-running MongoDB instance (required for all phases) are needed.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio + httpx ASGITransport |
| Config file | `pyproject.toml` (pytest settings) |
| Quick run command | `uv run pytest tests/test_clear_log.py -x` |
| Full suite command | `uv run pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLR-01 | Danger Zone card visible on `/log/profile` | integration | `uv run pytest tests/test_clear_log.py::test_danger_zone_visible -x` | Wave 0 |
| CLR-02 | Modal GET returns fragment with correct count | integration | `uv run pytest tests/test_clear_log.py::test_modal_shows_count -x` | Wave 0 |
| CLR-03 | Correct password deletes all active QSOs | integration | `uv run pytest tests/test_clear_log.py::test_clear_correct_password -x` | Wave 0 |
| CLR-04 | Success fragment shows deleted count | integration | `uv run pytest tests/test_clear_log.py::test_success_fragment_count -x` | Wave 0 |
| CLR-05 | Wrong password returns error, no deletion | integration | `uv run pytest tests/test_clear_log.py::test_wrong_password_no_delete -x` | Wave 0 |

Additional unit test (no MongoDB):
| — | `clear_operator_log()` function | unit | `uv run pytest tests/test_clear_log.py::test_clear_operator_log_service -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_clear_log.py -x`
- **Per wave merge:** `uv run pytest tests/`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_clear_log.py` — covers CLR-01 through CLR-05

### Test Fixture Pattern (to match existing style)

```python
# Source: matches test_profile_api.py and test_auth.py fixture patterns [VERIFIED: codebase]

@pytest_asyncio.fixture(scope="function")
async def clear_log_db():
    client = AsyncMongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
    db = client["ollog_clearlog_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_clearlog_test")
    await client.aclose()
```

The test file should use `httpx.AsyncClient` with `ASGITransport(app=app)` and set the
`access_token` cookie directly (mirroring `test_log_view_notify_sound.py` pattern for cookie-auth
UI route tests).

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `verify_password()` Argon2 re-verification before deletion |
| V3 Session Management | yes | `Depends(get_current_user_cookie)` — existing HttpOnly cookie auth |
| V4 Access Control | yes | Operator isolation: delete filter includes `_operator == user.callsign` |
| V5 Input Validation | yes | `password` form field — only used for `verify_password()`, not in DB query |
| V6 Cryptography | no | No new crypto; `verify_password()` delegates to pwdlib Argon2 |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-operator log clear (IDOR) | Tampering | Filter always uses `user.callsign` from authenticated cookie, never from form input |
| Replay attack (resubmit correct password) | Repudiation | After successful clear, all QSOs gone — replay is idempotent (count=0), acceptable |
| Brute-force password at `/log/profile/clear` | Elevation of Privilege | Argon2 is slow by design; no additional rate limiting added [ASSUMED no project rate-limiting requirement] |
| Path traversal or SQL injection | Tampering | No file paths involved; Beanie uses parameterized BSON queries, not string interpolation |

**No new security surface beyond what the restore confirm endpoint already establishes.**

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Soft-delete only (`_deleted: True`) | Permanent delete for clear log | Phase 54 (new) | First permanent-delete path in the operator UI; consistent with REQUIREMENTS.md "Out of Scope: Soft-delete / archive" |
| N/A | `QSO.find({}).delete_many()` | Phase 54 (new) | First use of bulk delete in the service layer |

**No deprecated APIs involved.** `delete_many()` is current Beanie API. [VERIFIED: beanie runtime]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Clear log should only delete `_deleted: False` records (visible QSOs), not already-soft-deleted ones | Anti-Patterns, Code Examples | Soft-deleted records would not be removed; operator might expect "total wipe" |
| A2 | No rate limiting is required on the `/log/profile/clear` endpoint for this phase | Security Domain | Brute force of password via rapid POST is theoretically possible; mitigated by Argon2 cost |
| A3 | The `clear-log-modal` div should be placed AFTER the closing tag of the `max-w-3xl` container | Template examples | If wrong, modal overlay z-index/stacking could be affected |

---

## Open Questions

1. **Soft-deleted QSO inclusion**
   - What we know: filter `{"_deleted": False}` is what the operator sees; `{"_deleted": True}` records are invisible in the UI
   - What's unclear: should "clear my log" also delete `_deleted: True` records (a full purge)?
   - Recommendation: Delete only `_deleted: False`. The UI displays a count N; deleting exactly N is the least surprising behavior. Soft-deleted records are already invisible and inconsequential.

2. **SSE watcher behavior after clear**
   - What we know: the SSE change stream fires on MongoDB delete operations
   - What's unclear: will a bulk delete trigger the SSE watcher and cause the log table to refresh?
   - Recommendation: This is fine behavior (the log will be empty). No special handling needed.

---

## Sources

### Primary (HIGH confidence)
- `app/auth/service.py` — `verify_password()` function signature confirmed [VERIFIED: codebase]
- `app/admin/ui_router.py` — restore confirm pattern (password verify + action + fragment return) [VERIFIED: codebase]
- `templates/admin/restore/password_modal.html` — modal component usage [VERIFIED: codebase]
- `static/css/input.css` — all component classes confirmed present: `.modal-backdrop`, `.modal-box`, `.modal-title`, `.modal-body`, `.modal-actions`, `.form-group`, `.form-control`, `.btn-danger`, `.btn-secondary`, `.alert-success`, `.alert-error` [VERIFIED: codebase]
- `app/qso/ui_router.py` — existing profile page route structure and cookie-auth patterns [VERIFIED: codebase]
- `app/qso/models.py` — QSO document structure, `_operator`/`_deleted` fields [VERIFIED: codebase]
- beanie `FindMany.delete_many()` — returns `DeleteMany` awaitable → `DeleteResult | None`, `.deleted_count` attribute [VERIFIED: runtime inspection]
- `.planning/phases/54-operator-clear-log/54-UI-SPEC.md` — component inventory, interaction flow, copywriting contract [VERIFIED: file]
- `STATE.md` — Critical Build Rules including "HTMX error fragments return HTTP 200" and "Password verify pattern" [VERIFIED: file]

### Secondary (MEDIUM confidence)
- REQUIREMENTS.md scope note: "Soft-delete / archive (recoverable): User explicitly chose permanent delete" [CITED: .planning/REQUIREMENTS.md]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, no new dependencies
- Architecture: HIGH — exact precedent exists in restore flow
- Pitfalls: HIGH — most from verified code inspection, one assumed (A1)
- Test patterns: HIGH — direct match to existing test files in repo

**Research date:** 2026-05-06
**Valid until:** 2026-06-06 (stable internal APIs; no external dependencies)
