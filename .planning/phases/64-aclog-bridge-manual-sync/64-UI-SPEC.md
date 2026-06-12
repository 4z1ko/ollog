---
phase: 64
slug: aclog-bridge-manual-sync
status: approved
shadcn_initialized: false
preset: none
created: 2026-06-12
---

# Phase 64 — UI Design Contract

> Visual and interaction contract for the ACLog Bridge Manual Sync UI changes.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | not applicable |
| Component library | none |
| Icon library | Existing inline Heroicons-style SVGs in templates |
| Font | Existing system stack from `static/css/input.css` |

**Contract:** Reuse the current profile/settings card, grid, button, form, and alert patterns. Do not introduce shadcn, new icon packages, new layout systems, or broad visual redesign.

---

## Interaction Contract

### ACLog Bridge Rows

- Add the Sync action only inside the saved bridge loop: `{% for bridge in profile.aclog_bridges %}`.
- Do not render Sync for the blank `new-0` bridge row.
- Keep the existing editable fields in each saved row: Name, Host, Port, Enabled, Remove.
- Add Sync as an additional row action, visually grouped with Remove.
- The saved bridge row grid may widen the action area, but must preserve the existing field order and form bindings.
- Sync must not submit `profile-form`; it must use its own HTMX POST action for that bridge.

### Sync Button

- Label: `Sync`.
- Style: use existing `btn-secondary` plus fixed-height row-action sizing, matching the Remove button height (`h-10`).
- Include an inline SVG icon if consistent with nearby buttons; use a refresh/sync style icon from the same inline Heroicons visual family.
- Add an `aria-label` that includes the bridge name or host, for example `Sync ACLog bridge Shack PC`.
- Use HTMX:
  - `hx-post="/log/profile/aclog/{{ bridge.id }}/sync"` or equivalent route chosen by the planner.
  - `hx-target="#profile-result"`.
  - `hx-swap="innerHTML"`.
  - The button may use `hx-disabled-elt="this"` if available in the current HTMX version/pattern, or an equivalent non-invasive disabled state.

### Report Placement

- Render all sync results into existing `<div id="profile-result"></div>` near the top of the Profile Settings page.
- Do not add per-row result containers.
- Do not add persistent sync history.

---

## Spacing Scale

Declared values reuse existing Tailwind utilities and must stay on the current 4px scale:

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps and compact text spacing |
| sm | 8px | Row action gaps (`gap-2`) |
| md | 16px | Existing grid gaps (`gap-3`/`gap-4`) |
| lg | 24px | Existing card body/header padding |
| xl | 32px | Existing section spacing |

Exceptions: none.

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | existing `text-sm` | 400 | Tailwind default |
| Label | existing `form-label` | 600 | Tailwind default |
| Button | existing `btn` / `btn-sm` | 500 | Tailwind default |
| Report heading | `text-sm` | 600 | Tailwind default |
| Report detail | `text-xs` or `text-sm` | 400 | Tailwind default |

**Contract:** Do not add display-scale headings or new uppercase/tracking treatments. Match the current compact operational UI.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | existing canvas/surface tokens | Page and cards |
| Secondary (30%) | existing gray card borders and text | Inputs, row chrome, secondary text |
| Accent (10%) | existing indigo/emerald/amber alert/button tokens | Sync button and report status |
| Destructive | existing rose tokens | Remove bridge and destructive actions only |

Accent reserved for: Sync button, success report count, warning/error report states. Do not recolor the full Profile Settings page.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Sync button | `Sync` |
| Success report heading | `ACLog sync complete` |
| Main report line | `Missing QSOs imported: {count}` |
| Skipped count | `Already present: {count}` |
| Error count | `Errors: {count}` |
| Rejected examples label | `Examples:` |
| Timeout/offline error | `ACLog sync failed: {reason}` plus a short actionable note such as `Confirm ACLog is running and the API port is reachable.` |
| Missing bridge error | `ACLog bridge not found. Save the bridge, then try again.` |

**Contract:** Keep report copy concise. No explanatory in-app tutorial text, no marketing language, and no modal.

---

## Report Layout

- Success report should use existing success/alert styling where practical.
- Failure report should use existing error/alert styling where practical.
- Report should be compact:
  - heading line,
  - three count lines or inline count chips,
  - optional short rejected examples list when errors exist.
- Rejected examples must be bounded to the first few records; do not render a long table.
- The report must not push the ACLog Bridges card into a new layout mode beyond normal vertical page flow.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not required |
| third-party | none | not allowed |

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-06-12
