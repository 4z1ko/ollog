---
plan: 45-01
phase: 45-sound-preference-model
status: complete
self_check: PASSED
tasks_completed: 2
tasks_total: 2
key_files:
  created: []
  modified:
    - app/auth/models.py
    - app/profile/schemas.py
    - app/qso/ui_router.py
    - tests/test_profile_api.py
    - templates/log/profile.html
    - static/css/output.css
commits:
  - 08d7e87
  - fc96a78
deviations: none
---

## What Was Built

Added the `notify_sound` boolean preference to the User model and wired it end-to-end through the profile stack. Existing MongoDB documents without the field read as `False` (Pydantic default, no migration required).

## Key Decisions

- **`bool = False` not `Optional[bool] = None`** — The field always has a value; `False` is a valid preference state, not "unknown". This matches the SND-03 requirement for "off by default".
- **Unconditional `raw["notify_sound"]` assignment** — The checkbox+hidden-input pattern guarantees the field is always submitted. The conversion `(notify_sound == "true")` maps any non-`"true"` string (including `"false"`) to `False`, blocking tampering with arbitrary values (T-45-01).
- **Checkbox before hidden input** — Starlette's `Form()` takes the first submitted value for a given name. When checked, browser sends `"true"` then `"false"`; `Form()` captures `"true"`. When unchecked, only `"false"` is sent.

## Verification

- `uv run pytest tests/test_profile_api.py -x -v` — 11/11 passed (3 new: default False, patch True, patch False-after-True)
- `npm run build && npm run verify` — Tailwind rebuilt, dark classes confirmed
- `dark\:bg-gray-800`, `dark\:checked\:bg-indigo-600`, `dark\:border-gray-600` all present in `output.css`

## Self-Check

- [x] `app/auth/models.py` contains `notify_sound: bool = False`
- [x] `app/profile/schemas.py` ProfileUpdateRequest contains `notify_sound: bool = False`
- [x] `app/profile/schemas.py` ProfileResponse contains `notify_sound: bool = False`
- [x] `app/qso/ui_router.py` signature contains `notify_sound: Annotated[Optional[str], Form()] = None`
- [x] `app/qso/ui_router.py` contains `raw["notify_sound"] = (notify_sound == "true")` outside any `if` gate
- [x] `templates/log/profile.html` contains Sound Notifications checkbox (2× `name="notify_sound"`)
- [x] `templates/log/profile.html` checkbox appears before hidden input
- [x] All 11 profile tests pass with no regressions
