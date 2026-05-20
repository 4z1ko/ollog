---
phase: 45-sound-preference-model
reviewed: 2026-04-17T12:25:53Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - app/auth/models.py
  - app/profile/schemas.py
  - app/qso/ui_router.py
  - tests/test_profile_api.py
  - templates/log/profile.html
  - static/css/output.css
findings:
  critical: 1
  warning: 1
  info: 1
  total: 3
status: issues_found
---

# Phase 45: Code Review Report

**Reviewed:** 2026-04-17T12:25:53Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 45 adds a `notify_sound: bool = False` field to the User model, propagates it through `ProfileUpdateRequest` / `ProfileResponse` schemas, wires a Form parameter in the HTMX profile update handler, renders a checkbox in the profile template using the checkbox-before-hidden-input pattern, and adds three JSON-body integration tests against the REST API.

The model-level change, schema propagation, and `profile_update` handler logic are all clean. The coercion `notify_sound == "true"` is safe and correct. Jinja2 auto-escaping is active for `.html` files in this FastAPI setup — no XSS risk was found.

One critical bug exists: the HTML element ordering in the checkbox-before-hidden pattern is wrong for Starlette's multidict, making it impossible to enable sound notifications via the UI. The three new tests exclusively exercise the JSON REST path and do not detect this bug — they constitute a warning-level test coverage gap. One info-level item exists: a missing `for` attribute on the checkbox label.

## Critical Issues

### CR-01: checkbox-before-hidden-input ordering breaks Starlette multidict — sound can never be enabled

**File:** `templates/log/profile.html:132-139`

**Issue:** The template places the checkbox input (`value="true"`) at line 132 and the hidden fallback input (`value="false"`) at line 139. When the checkbox is checked the browser encodes both fields in DOM order: `notify_sound=true&notify_sound=false`. Starlette's `ImmutableMultiDict.get(key)` returns the **last** matching entry (confirmed with Starlette 1.0.0: `FormData([('k','true'),('k','false')]).get('k') == 'false'`). FastAPI's `Form()` dependency calls `form.get()`, so the server always receives `"false"`, regardless of checkbox state. The coercion on line 623 of `ui_router.py` (`notify_sound == "true"`) therefore always evaluates `False` — the preference can never be persisted as `True` through the UI form.

**Fix:** Reverse the element order — place the hidden input **before** the checkbox so Starlette returns the last (checkbox) value when the box is checked, and the hidden value when it is unchecked:

```html
<!-- Sound Notifications (SND-04) -->
<div class="sm:col-span-2">
  <label class="form-label">Sound Notifications</label>
  <div class="flex items-center gap-3 mt-1">
    <!-- hidden BEFORE checkbox — Starlette multidict.get() returns last value -->
    <input type="hidden" name="notify_sound" value="false">
    <input type="checkbox"
           id="notify_sound"
           name="notify_sound"
           value="true"
           {{ 'checked' if profile.notify_sound else '' }}
           class="w-4 h-4 rounded border-gray-300 dark:border-gray-600
                  text-indigo-600 focus:ring-indigo-500
                  dark:bg-gray-800 dark:checked:bg-indigo-600">
    <span class="text-sm text-gray-700 dark:text-gray-300">
      Play a tone when a new QSO arrives
    </span>
  </div>
  <p class="form-hint">Requires at least one page interaction (browser autoplay policy)</p>
</div>
```

When unchecked only the hidden `false` is submitted; `get()` returns `"false"`. When checked both are submitted in order `false, true`; `get()` returns `"true"`. The coercion `notify_sound == "true"` then works correctly.

## Warnings

### WR-01: New tests cover only the JSON REST path — UI form coercion path has zero test coverage

**File:** `tests/test_profile_api.py:206-247`

**Issue:** `test_notify_sound_default_false`, `test_notify_sound_patch_true`, and `test_notify_sound_patch_false` all send `json={"notify_sound": True/False}` to `PATCH /api/profile/`. They exercise `ProfileUpdateRequest` Pydantic validation and the service layer, but they do not touch `POST /log/profile` (the HTMX handler in `ui_router.py`). The entire form-encoding branch — including the `Optional[str]` Form parameter, the `notify_sound == "true"` string coercion, and the multidict ordering — is untested. The critical CR-01 bug above would have been caught by a test that posts form-encoded data with the checkbox value.

**Fix:** Add a test that posts to `POST /log/profile` with a session cookie and form-encoded body, verifying both the `checked` (value `true`) and `unchecked` (value `false`) submissions persist correctly via a subsequent `GET /api/profile/` check:

```python
@pytest.mark.asyncio
async def test_ui_profile_notify_sound_enable(client, operator, login_cookie):
    """POST /log/profile with form data sets notify_sound=True."""
    resp = await client.post(
        "/log/profile",
        data={"notify_sound": "true"},   # simulates hidden=false,checkbox=true order
        cookies={"access_token": login_cookie},
    )
    assert resp.status_code == 200
    profile = await User.get(operator.id)
    assert profile.notify_sound is True
```

## Info

### IN-01: Checkbox input has no associated `<label for>` — reduces accessibility

**File:** `templates/log/profile.html:131-145`

**Issue:** The checkbox at line 132 has no `id` attribute, and the `<label class="form-label">` at line 131 has no `for` attribute. The visible label ("Play a tone...") at line 140 is a bare `<span>`, not a `<label>`. Clicking the label text does not toggle the checkbox, and screen readers cannot programmatically associate the label with the control.

**Fix:** Add `id="notify_sound"` to the checkbox and change the description span to a `<label for="notify_sound">` element:

```html
<input type="checkbox"
       id="notify_sound"
       name="notify_sound"
       value="true" ...>
<label for="notify_sound" class="text-sm text-gray-700 dark:text-gray-300">
  Play a tone when a new QSO arrives
</label>
```

---

_Reviewed: 2026-04-17T12:25:53Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
