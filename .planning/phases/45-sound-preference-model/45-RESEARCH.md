# Phase 45: Sound Preference Model - Research

**Researched:** 2026-04-17
**Domain:** Beanie/Pydantic model extension, HTML checkbox form handling, FastAPI Form parameter handling
**Confidence:** HIGH

## Summary

Phase 45 is a narrow, well-defined data-model and form-UI change. It adds a single `notify_sound: bool = False` field to the existing `User` Beanie document, propagates it through `ProfileUpdateRequest` and `ProfileResponse` schemas, adds a hidden-input + checkbox pair to the profile form template, and handles the new form parameter in the `profile_update` POST handler.

Every architecture decision for this phase has already been pre-decided and recorded in `.planning/STATE.md` under "v2.4 Architecture Decisions." The codebase patterns for adding a new optional boolean field to an existing profile form are already established by the `tx_pwr`, `my_gridsquare`, and other profile fields added in Phase 7/10. No new libraries, no new dependencies, and no database migration are required.

The only non-trivial implementation detail is the hidden-input technique for unchecked checkboxes: an `<input type="hidden" name="notify_sound" value="false">` must appear before the `<input type="checkbox" name="notify_sound" value="true">` in the HTML. When the checkbox is checked, the browser sends `notify_sound=true` (the checkbox value overrides the hidden input). When unchecked, only the hidden input is submitted, sending `notify_sound=false`. Without the hidden input, an unchecked checkbox sends nothing, and the form handler receives `None` — the preference is silently ignored.

**Primary recommendation:** Follow the established Beanie optional-field-with-default pattern exactly. Add `notify_sound: bool = False` to `User`, extend both schemas, wire the Form parameter in `profile_update`, and add the hidden+checkbox pair to `profile.html`. One plan is sufficient for the entire phase.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SND-03 | Sound notifications are off by default | `notify_sound: bool = False` default on User model; Beanie reads missing field as `False` via Pydantic default — no migration needed [VERIFIED: codebase inspection] |
| SND-04 | Profile Settings page has a "Sound notifications" on/off toggle | Hidden input + checkbox pattern in profile.html; handled by `profile_update` POST Form param [VERIFIED: codebase inspection] |
| SND-05 | Sound preference persisted per-operator in MongoDB, survives reload and session restart | Stored via `update_profile()` service → `user.update({"$set": ...})`; read back by `get_current_user_cookie` dependency on every page load [VERIFIED: codebase inspection] |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Persist notify_sound to MongoDB | API / Backend | — | Beanie `$set` update in profile service; field lives on User document in `users` collection |
| Read notify_sound back on profile page load | API / Backend | — | `get_current_user_cookie` dependency fetches full User document; `profile_page` passes it to template |
| Display checkbox in correct checked/unchecked state | Frontend (Jinja2 template) | — | Template reads `profile.notify_sound` and conditionally adds `checked` attribute |
| Submit preference change | Frontend (HTML form POST) | — | Hidden input + checkbox; `hx-post="/log/profile"` sends to profile_update |
| Accept + validate form value | API / Backend | — | `profile_update` receives `notify_sound` as `Annotated[str, Form()]`; convert to bool before passing to `ProfileUpdateRequest` |

## Standard Stack

### Core (already in project — no new installs)
| Component | Version | Purpose | Notes |
|-----------|---------|---------|-------|
| Beanie | pinned in pyproject.toml | Async MongoDB ODM; `Document` with `update({"$set": ...})` | [VERIFIED: codebase] |
| Pydantic v2 | pinned | Schema validation; `bool` field with `= False` default | [VERIFIED: codebase] |
| FastAPI | pinned | `Form()` dependency for profile POST handler | [VERIFIED: codebase] |
| Jinja2 | pinned | Template rendering; conditional `checked` attribute | [VERIFIED: codebase] |
| HTMX | CDN in base.html | `hx-post` form submission; result swapped into `#profile-result` | [VERIFIED: codebase] |

**No new packages.** CLAUDE.md and STATE.md both explicitly state: "No new Python packages" and "No new JS dependencies" for v2.4.

## Architecture Patterns

### System Architecture Diagram

```
Browser: profile.html form
  POST /log/profile (hx-post, form-encoded)
    notify_sound=false   ← hidden input (always sent)
    notify_sound=true    ← checkbox (overrides hidden when checked)
        |
        v
  profile_update() in app/qso/ui_router.py
    Annotated[str, Form()] = "false" | "true"
    convert to bool → ProfileUpdateRequest(notify_sound=True/False)
        |
        v
  update_profile() in app/profile/service.py
    user.update({"$set": {"notify_sound": True/False}})
        |
        v
  MongoDB users collection
    {notify_sound: true} or {notify_sound: false}
        |
        v
  Next GET /log/profile
    get_current_user_cookie() → User document (notify_sound from DB)
    profile_page() → template context {"profile": user}
    profile.html → checked="{{ 'checked' if profile.notify_sound else '' }}"
```

### Recommended File Changes
```
app/auth/models.py           # Add: notify_sound: bool = False
app/profile/schemas.py       # Add: notify_sound: bool = False to both ProfileUpdateRequest and ProfileResponse
app/qso/ui_router.py         # Add: notify_sound Form param to profile_update(); conversion logic
templates/log/profile.html   # Add: hidden input + checkbox in form
tests/test_profile_api.py    # Add: test_notify_sound_default, test_notify_sound_toggle
```

### Pattern 1: Beanie Optional Field with Default (established pattern)

**What:** Add a new optional field to a Beanie Document with a Python-side default. Existing MongoDB documents lacking the field return the default value when read — no schema migration needed.

**When to use:** Any time a new preference field is added to User. This is the same pattern used for `station_callsign`, `tx_pwr`, etc. (all added in Phase 7 with `Optional[X] = None` defaults).

**Example:**
```python
# Source: app/auth/models.py (verified in codebase)
# EXISTING pattern — new field follows same convention:
notify_sound: bool = False   # SND-03: sound off by default; existing users read as False
```

Pydantic v2 + Beanie: when MongoDB returns a document without `notify_sound` (all pre-Phase-45 users), Pydantic applies the field default `False`. No migration needed. [VERIFIED: codebase inspection of existing optional fields]

### Pattern 2: ProfileUpdateRequest + ProfileResponse Extension

**What:** Both schema classes in `app/profile/schemas.py` must receive the new field. `ProfileUpdateRequest` uses it for PATCH validation; `ProfileResponse` exposes it in the REST API GET response.

```python
# Source: app/profile/schemas.py (verified in codebase)
class ProfileUpdateRequest(BaseModel):
    # ... existing fields ...
    notify_sound: bool = False   # new

class ProfileResponse(BaseModel):
    # ... existing fields ...
    notify_sound: bool = False   # new
```

Note: `notify_sound` is NOT `Optional[bool]` — it always has a value. The default `False` ensures the field is always present in responses.

### Pattern 3: Form Handler Parameter (established pattern from existing profile_update)

**What:** The `profile_update` POST handler in `app/qso/ui_router.py` already accepts all profile fields as `Annotated[Optional[str], Form()]`. The new `notify_sound` field arrives as a string `"true"` or `"false"` (not a Python bool) because HTML forms always submit string values.

**Conversion logic:**
```python
# Source: app/qso/ui_router.py pattern (verified in codebase)
notify_sound: Annotated[Optional[str], Form()] = None,

# In the handler body — add to the raw dict construction:
raw["notify_sound"] = (notify_sound == "true")  # convert string to bool
```

The hidden-input technique guarantees `notify_sound` is never `None` in a real browser submission (the hidden input always fires). However, the Form parameter default should still be `None` to handle edge cases (e.g., direct API calls that omit the field).

### Pattern 4: Hidden Input + Checkbox (load-bearing HTML pattern)

**What:** HTML unchecked checkboxes send no value. A hidden input with the same `name` provides the fallback `false` value.

**Why load-bearing:** Without the hidden input, unchecking the checkbox and saving sends no `notify_sound` field to the server. The `profile_update` handler receives `None`, and if the code does `raw["notify_sound"] = (notify_sound == "true")` it correctly evaluates to `False`. However, if the code uses `if notify_sound is not None:` gating (like other fields do), the unchecked state would be silently ignored and the preference would not be saved. The hidden input is the clean, correct solution that avoids requiring special-case logic.

**Correct HTML order (order is load-bearing):**
```html
<!-- Source: STATE.md v2.4 Architecture Decisions (pre-decided) -->
<!-- hidden input MUST come BEFORE the checkbox -->
<input type="hidden" name="notify_sound" value="false">
<input type="checkbox" name="notify_sound" value="true"
       {{ 'checked' if profile.notify_sound else '' }}>
```

Browser behavior: when checkbox is checked, browser sends `notify_sound=false&notify_sound=true` — FastAPI's `Form()` resolves multi-value fields by taking the last value, which is `true`. When unchecked, only `notify_sound=false` is sent.

**Alternative:** Some browsers take the first value, not the last, for multi-value same-name fields. Verify: FastAPI uses Starlette's `FormData` which wraps Python's `multipart` parsing. For same-name fields, `request.form.getlist("notify_sound")` returns all values; `Form()` as a scalar takes the first. This means the hidden+checkbox order may need to be **checkbox AFTER hidden** so the FIRST value (hidden=false) is the fallback and the checkbox value overrides when present.

Wait — this requires careful verification. See "Common Pitfalls" section.

### Anti-Patterns to Avoid
- **`Optional[bool]` for notify_sound:** Use `bool = False` not `Optional[bool] = None`. A three-state boolean (true/false/null) complicates template logic and REST API consumers.
- **Checking `if notify_sound is not None:` before setting:** The existing `profile_update` handler gates each field on `if value is not None`. For `notify_sound`, we must NOT gate it this way — the converted bool value (even `False`) must always be included in `raw`. Otherwise unchecking and saving is silently ignored.
- **Initiating AudioContext in this phase:** Phase 45 is model-only. The `NOTIFY_SOUND` JS constant injection and Web Audio API wiring belong to Phase 46. Do not add any JavaScript to `log.html` in this phase.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Boolean field with DB default | Custom migration script | Pydantic field default | Beanie returns Python default for missing MongoDB fields — zero-migration pattern already used in this codebase |
| Form checkbox boolean | Custom JS to inject hidden field | HTML hidden-input-before-checkbox | Standard HTML pattern; no JS needed |
| Profile form submission | Custom fetch/XHR | HTMX `hx-post` | Already wired in profile.html; just add the new field to the existing form |

## Common Pitfalls

### Pitfall 1: FastAPI Form() Multi-Value Field Resolution Order

**What goes wrong:** The HTML hidden-input + checkbox pattern sends the same field name twice. When checkbox is unchecked: `notify_sound=false` (hidden only). When checked: behavior depends on which value FastAPI's `Form()` picks from a multi-value submission.

**Root cause:** Starlette's `FormData.get(key)` returns the FIRST value for a repeated key. This is the opposite of what was described in the STATE.md architecture decision ("hidden input provides the false fallback"). If the hidden input comes first and the checkbox second, `Form()` returns `"false"` even when the checkbox is checked.

**Verified behavior:** [ASSUMED — needs verification at implementation time] Starlette `ImmutableMultiDict.get()` returns the first occurrence. For `notify_sound=false&notify_sound=true`, `Form()` returns `"false"`. This means the checkbox value (second) is ignored.

**How to avoid:** Two options:
1. Put the CHECKBOX first, hidden input second. Then when checkbox is unchecked: only `notify_sound=false` from hidden. When checked: `notify_sound=true&notify_sound=false` → Form() returns `"true"` (first value, from checkbox). This reversal works correctly.
2. Use `Form()` with `list` type: `notify_sound: Annotated[list[str], Form()] = []` and take the last value. Less clean.

**Recommendation:** Put checkbox FIRST, hidden input SECOND. This is the reliable pattern regardless of `get()` semantics:
- Checkbox checked: form sends `notify_sound=true` then `notify_sound=false`; Form() takes first → `"true"` ✓
- Checkbox unchecked: form sends only `notify_sound=false`; Form() takes it → `"false"` ✓

**Note:** The STATE.md architecture decision says "hidden input precedes checkbox" and describes it as load-bearing. This refers to the fallback-providing role of the hidden input — but the correct ordering for Starlette's `get()` is checkbox first, then hidden. **Clarify at implementation time by testing both orderings.** The behavioral contract (unchecked → false, checked → true) is what matters.

**Warning signs:** Checking the checkbox, saving, reloading profile, and seeing the checkbox unchecked — this means the value was saved as `False` due to wrong ordering.

### Pitfall 2: Gating notify_sound with `if value is not None`

**What goes wrong:** The existing `profile_update` handler builds `raw` by gating each field: `if value is not None: raw[field] = value`. If `notify_sound` is gated the same way, and the hidden input correctly sends `"false"`, then `"false" is not None` → `True` → `raw["notify_sound"] = False` ← this actually works. But if the conversion `(notify_sound == "true")` produces `False`, gating on `if False:` silently drops the update.

**How to avoid:** Separate the gating from the conversion. Add `notify_sound` to `raw` unconditionally after conversion:
```python
raw["notify_sound"] = (notify_sound == "true")
```
Do not wrap this in `if notify_sound is not None:`.

### Pitfall 3: Tailwind `checked` pseudo-class in dark mode

**What goes wrong:** New checkbox styling may require `dark:` variants. Tailwind's JIT purger requires complete literal class strings to appear in scanned templates.

**How to avoid:** Use the existing form input styling patterns. For the checkbox itself, add any new `dark:` classes as complete literal strings. Run `npm run build` after template changes and run `npm run verify` to confirm classes appear in `output.css`. This is a documented CLAUDE.md requirement.

### Pitfall 4: ProfileResponse missing notify_sound

**What goes wrong:** The REST API PATCH endpoint returns `ProfileResponse`. If `notify_sound` is added to the `User` model and `ProfileUpdateRequest` but not `ProfileResponse`, the REST API response omits it. Existing `test_get_profile_empty` will fail because it checks for null on a known field list.

**How to avoid:** Add `notify_sound: bool = False` to `ProfileResponse` as well. Update `test_get_profile_empty` to expect `notify_sound: False` in the response.

## Code Examples

### User model field addition
```python
# app/auth/models.py
# Source: verified codebase pattern (existing optional fields use same convention)
class User(Document):
    # ... existing fields ...
    notify_sound: bool = False  # SND-03: off by default; missing field reads as False (no migration)
```

### ProfileUpdateRequest + ProfileResponse
```python
# app/profile/schemas.py
class ProfileUpdateRequest(BaseModel):
    # ... existing fields ...
    notify_sound: bool = False

class ProfileResponse(BaseModel):
    # ... existing fields ...
    notify_sound: bool = False
```

### profile_update handler extension
```python
# app/qso/ui_router.py — profile_update() signature addition
async def profile_update(
    request: Request,
    user: User = Depends(get_current_user_cookie),
    # ... existing Form params ...
    notify_sound: Annotated[Optional[str], Form()] = None,
):
    # In the raw dict construction — add OUTSIDE the existing loop, unconditionally:
    raw["notify_sound"] = (notify_sound == "true")
    # ... rest of handler unchanged ...
```

### Template HTML
```html
<!-- templates/log/profile.html — inside the form grid, new section -->
<!-- Sound Notifications toggle -->
<div class="sm:col-span-2">
  <label class="form-label">Sound Notifications</label>
  <div class="flex items-center gap-3 mt-1">
    <!-- Checkbox FIRST so Form() receives checkbox value before hidden fallback -->
    <input type="checkbox"
           name="notify_sound"
           value="true"
           {{ 'checked' if profile.notify_sound else '' }}
           class="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 dark:border-gray-600">
    <!-- Hidden input SECOND — provides "false" fallback when checkbox unchecked -->
    <input type="hidden" name="notify_sound" value="false">
    <span class="text-sm text-gray-700 dark:text-gray-300">
      Play a tone when a new QSO arrives via SSE
    </span>
  </div>
  <p class="form-hint">Requires at least one page interaction (browser autoplay policy)</p>
</div>
```

### Test additions
```python
# tests/test_profile_api.py — new test functions
@pytest.mark.asyncio
async def test_notify_sound_default_false(client, operator, operator_token):
    """SND-03: notify_sound is False for a new operator."""
    resp = await client.get("/api/profile/", headers={"Authorization": f"Bearer {operator_token}"})
    assert resp.status_code == 200
    assert resp.json()["notify_sound"] == False

@pytest.mark.asyncio
async def test_notify_sound_patch_true(client, operator, operator_token):
    """SND-05: patching notify_sound=True persists and is readable."""
    headers = {"Authorization": f"Bearer {operator_token}"}
    resp = await client.patch("/api/profile/", json={"notify_sound": True}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["notify_sound"] == True
    # Verify persistence
    get_resp = await client.get("/api/profile/", headers=headers)
    assert get_resp.json()["notify_sound"] == True

@pytest.mark.asyncio
async def test_notify_sound_patch_false(client, operator, operator_token):
    """SND-05: patching notify_sound=False (after True) persists correctly."""
    headers = {"Authorization": f"Bearer {operator_token}"}
    await client.patch("/api/profile/", json={"notify_sound": True}, headers=headers)
    resp = await client.patch("/api/profile/", json={"notify_sound": False}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["notify_sound"] == False
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| localStorage for UI prefs | Server-side MongoDB field | Decided in v2.4 planning | Preference survives different browsers/devices; correct for shared station computer |
| Optional[bool] = None | bool = False | v2.4 design | Simpler template logic; avoids three-state boolean; cleaner REST API |

**Explicitly out of scope (REQUIREMENTS.md):**
- `localStorage sound preference` — server-side is the correct approach for shared station computers

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Starlette `FormData.get()` returns the FIRST occurrence of a repeated field name, meaning checkbox-first ordering is required | Common Pitfalls (Pitfall 1) | If it returns the LAST value instead, hidden-first ordering works. Risk: wrong checkbox ordering causes save to always store opposite of intent. Verify with a quick test at implementation time. |

## Open Questions

1. **Hidden input vs. checkbox order for Starlette Form()**
   - What we know: STATE.md says "hidden input precedes checkbox" as load-bearing. Starlette `ImmutableMultiDict.get()` behavior on repeated keys needs confirmation.
   - What's unclear: Whether Starlette returns first or last value for `Form()` scalar on a repeated key.
   - Recommendation: At implementation time, test both orderings with a simple print of the raw form value. The test `test_notify_sound_patch_false` (via the REST API using JSON) cannot cover this HTML form edge case — add a UI-level smoke test or verify manually in the browser.

## Environment Availability

Step 2.6: SKIPPED — no new external dependencies. This phase modifies Python source files and a Jinja2 template only. MongoDB is already running for the test suite.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | pyproject.toml (likely) or pytest.ini |
| Quick run command | `uv run pytest tests/test_profile_api.py -x` |
| Full suite command | `uv run pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SND-03 | notify_sound defaults to False for new operator | unit/integration | `uv run pytest tests/test_profile_api.py::test_notify_sound_default_false -x` | ❌ Wave 0 |
| SND-04 | Profile page shows toggle | manual | Browser inspection — not automatable via API test | — |
| SND-05 | Preference persists: True saved → True on reload | integration | `uv run pytest tests/test_profile_api.py::test_notify_sound_patch_true -x` | ❌ Wave 0 |
| SND-05 | Preference persists: False saved → False on reload | integration | `uv run pytest tests/test_profile_api.py::test_notify_sound_patch_false -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_profile_api.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_profile_api.py` — add `test_notify_sound_default_false`, `test_notify_sound_patch_true`, `test_notify_sound_patch_false` (file exists, add new test functions)
- [ ] Update `test_get_profile_empty` to assert `notify_sound == False` in the null-fields check (or leave it since the test only asserts listed fields are null, and `notify_sound: bool` is never null)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Profile update already behind `get_current_user_cookie` |
| V3 Session Management | no | No session changes |
| V4 Access Control | yes | `notify_sound` is scoped to the authenticated user's own record — operator isolation is maintained by the existing `update_profile(user, updates)` pattern which updates `user.id`'s document |
| V5 Input Validation | yes | `bool = False` in Pydantic schema; `(notify_sound == "true")` string→bool conversion is explicit and safe |
| V6 Cryptography | no | No cryptographic operations |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Operator A modifying operator B's notify_sound | Tampering | `update_profile(user, updates)` takes the `user` object from `get_current_user_cookie` — the update target is always the authenticated user's document |
| Form field injection (extra unexpected fields) | Tampering | `ProfileUpdateRequest(**raw)` with Pydantic; only declared fields are accepted; extra fields raise ValidationError |

## Sources

### Primary (HIGH confidence)
- Codebase: `app/auth/models.py` — verified existing User document fields and Beanie Document pattern
- Codebase: `app/profile/schemas.py` — verified ProfileUpdateRequest and ProfileResponse structure
- Codebase: `app/profile/service.py` — verified `update_profile()` using `user.update({"$set": ...})`
- Codebase: `app/qso/ui_router.py` — verified `profile_update()` Form parameter pattern
- Codebase: `templates/log/profile.html` — verified existing form structure and component classes
- `.planning/STATE.md` — v2.4 Architecture Decisions (pre-decided, authoritative)
- `.planning/REQUIREMENTS.md` — SND-03/04/05 requirements

### Secondary (MEDIUM confidence)
- HTML spec / established practice: hidden-input + checkbox technique for boolean form fields

### Tertiary (LOW confidence)
- Starlette `FormData.get()` first-vs-last behavior for repeated keys — [ASSUMED, see A1]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all existing
- Architecture: HIGH — pre-decided in STATE.md; codebase patterns confirmed
- Pitfalls: MEDIUM — Starlette Form multi-value behavior is assumed (A1), rest verified

**Research date:** 2026-04-17
**Valid until:** 2026-05-17 (stable dependencies, no fast-moving ecosystem)
