# Phase 45: Sound Preference Model — Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `notify_sound: bool` to the `User` Beanie model, propagate it through `ProfileUpdateRequest` and `ProfileResponse` schemas, wire it as a `Form()` parameter in the `profile_update` POST handler, and display a "Sound Notifications" checkbox in the Profile Settings page.

Phase 45 is the data-model and toggle UI foundation only. No audio code, no JS constants, and no `log.html` changes — those belong to Phase 46 (Sound Playback Wiring).

</domain>

<decisions>
## Implementation Decisions

### Field Type
- **D-01:** `notify_sound: bool = False` — not `Optional[bool]`. Existing MongoDB user documents without the field read as `False` via Pydantic default. No database migration needed.

### Form Submission Ordering
- **D-02:** The hidden input (`<input type="hidden" name="notify_sound" value="false">`) appears **before** the checkbox (`<input type="checkbox" name="notify_sound" value="true">`) in the DOM. Starlette's `Form()` returns the last submitted value for a duplicated field name, so the checkbox "overrides" the hidden input when checked. When unchecked, only the hidden input submits — returning `"false"`.
- **D-03:** This ordering is load-bearing. Reversing it (checkbox before hidden) would cause `Form()` to always return `"false"`.

### Form Handler Wiring
- **D-04:** `raw["notify_sound"] = (notify_sound == "true")` is set **unconditionally** in `profile_update()` — it is NOT inside the `if value is not None:` gate used by the other optional profile fields. The hidden input guarantees `notify_sound` is always submitted as a non-None string.

### Phase Boundary (No JS)
- **D-05:** No JavaScript is introduced in Phase 45. The `NOTIFY_SOUND` JS constant injection into `log.html` and all Web Audio API code belong to Phase 46.

### Claude's Discretion
- Tailwind classes for checkbox dark mode: `dark:bg-gray-800`, `dark:border-gray-600`, `dark:checked:bg-indigo-600`
- Checkbox placed in `sm:col-span-2` full-width row after TX Power field — matches "My Rig" / "My Antenna" layout
- Copy: label "Sound Notifications", span "Play a tone when a new QSO arrives", hint "Requires at least one page interaction (browser autoplay policy)"

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture Decisions (PRE-DECIDED — must follow)
- `.planning/STATE.md` §v2.4 Architecture Decisions — `notify_sound` field type, hidden-input-before-checkbox ordering, unconditional bool conversion. All pre-decided and load-bearing.

### Project Requirements
- `.planning/REQUIREMENTS.md` — SND-03 (off by default), SND-04 (profile toggle), SND-05 (persisted per-operator) are the acceptance criteria for this phase.

### UI Contract
- `.planning/phases/45-sound-preference-model/45-UI-SPEC.md` — Authoritative HTML structure, Tailwind classes, copy contract, and interaction state machine for the checkbox section.

### Research
- `.planning/phases/45-sound-preference-model/45-RESEARCH.md` — Pitfall 1: hidden-input technique for unchecked checkboxes, and full data-flow diagram.

### Files Modified
- `app/auth/models.py` — `User.notify_sound: bool = False` field
- `app/profile/schemas.py` — `notify_sound: bool = False` in `ProfileUpdateRequest` and `ProfileResponse`
- `app/qso/ui_router.py` — `notify_sound` Form param + unconditional bool conversion in `profile_update()`
- `templates/log/profile.html` — checkbox + hidden input section

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/profile/service.py` `update_profile()` — passes `updates` dict to `user.update({"$set": ...})`; `notify_sound` is added to this dict via `ProfileUpdateRequest(**raw)` then `model_dump(exclude_unset=False)`
- `app/auth/dependencies.py` `get_current_user_cookie` — returns full `User` document including `notify_sound`; used by both `profile_page()` and `profile_update()`

### Established Patterns
- `bool = False` field on User: same Beanie optional-field-with-default pattern used for `enabled: bool = True` and other non-nullable fields
- `Annotated[Optional[str], Form()]` with explicit bool conversion in `profile_update()` handler — matching `tx_pwr` (str → float) conversion pattern
- `{{ 'checked' if profile.notify_sound else '' }}` — Jinja2 conditional attribute pattern used elsewhere in the template

### Integration Points
- `profile_update()` in `app/qso/ui_router.py`: add `notify_sound` Form param + set `raw["notify_sound"]` unconditionally before `ProfileUpdateRequest(**raw)`
- `templates/log/profile.html`: insert `<div class="sm:col-span-2">` block after TX Power `</div>`, before closing grid `</div>`

</code_context>

<specifics>
## Specific Ideas

No external references. All decisions were pre-decided in STATE.md v2.4 Architecture Decisions before this phase was planned.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. Audio playback code (Web Audio API, NOTIFY_SOUND constant, autoplay gate) is Phase 46 by design.

</deferred>

---

*Phase: 45-sound-preference-model*
*Context gathered: 2026-04-20*
