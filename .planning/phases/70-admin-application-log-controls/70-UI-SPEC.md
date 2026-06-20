---
phase: 70
slug: admin-application-log-controls
status: approved
shadcn_initialized: false
preset: existing-admin-ui
created: 2026-06-20
---

# Phase 70 — UI Design Contract

> Visual and interaction contract for adding Recent Logs pause/start and clear controls to the existing admin Application Logs page.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | existing admin FastAPI/Jinja/HTMX/Tailwind UI |
| Component library | none |
| Icon library | inline SVG already used in admin templates; do not introduce a new icon dependency |
| Font | system font stack from `static/css/input.css` |

Design posture: this is an operational admin tool. Keep the UI compact, scannable, and consistent with existing admin cards/tables. Do not redesign the Application Logs page, sidebar, filters, table, or settings layout.

---

## Layout Contract

### Recent Logs Header

The Recent Logs card header is the only approved placement for the new controls.

Required structure:
- Left side: existing `Recent Logs` title.
- Right side: a compact control group containing live status badge, Pause/Start button, and Clear Log Messages button.
- Controls must wrap cleanly on narrow screens without overlapping the title or table.
- Keep the table itself and pagination footer visually unchanged except where a clear action refreshes table content.

Recommended hierarchy:
1. Status badge: `LIVE`, `PAUSED`, or `OFFLINE`.
2. Pause/Start button: secondary/ghost weight.
3. Clear Log Messages button: danger-outline weight.

### Modal Placement

Add a modal placeholder near the bottom of `templates/admin/logs.html`, matching the existing admin modal pattern:
- `#admin-clear-application-logs-modal` or similarly specific ID.
- Modal fragment uses existing `modal-backdrop`, `modal-box`, `modal-title`, `modal-body`, and `modal-actions` classes.

---

## Spacing Scale

Declared values, matching current Tailwind/admin components:

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Badge/icon internal spacing |
| sm | 8px | Button gaps inside the header control group |
| md | 16px | Header group wrapping gap, modal action gap |
| lg | 24px | Existing card header horizontal padding |
| xl | 32px | No new use in this phase |

Exceptions: none. Do not introduce custom spacing values unless an existing component already uses them.

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 14px | 400 | 1.25rem |
| Label/Button | 12-14px | 500-600 | 1-1.25rem |
| Card title | 14px | 600 | 1.25rem |
| Modal title | existing `.modal-title` | existing | existing |

Rules:
- No viewport-scaled font sizes.
- No negative letter spacing.
- Button labels must fit on mobile. Prefer concise text: `Pause`, `Start`, `Clear Log Messages`.
- Badge text remains uppercase and short: `LIVE`, `PAUSED`, `OFFLINE`.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | existing admin surface colors | Page/card/table backgrounds |
| Secondary (30%) | existing gray/indigo admin controls | Ghost buttons, borders, table chrome |
| Accent (10%) | existing indigo/blue badge styles | `LIVE` status and neutral control focus |
| Warning/paused | existing gray or amber badge style | `PAUSED` status only |
| Destructive | existing rose palette | Clear Log Messages button and modal confirmation |

Accent reserved for:
- LIVE badge.
- Focus states already provided by `.btn`, `.btn-ghost`, `.btn-primary`.

Destructive contract:
- Clear Log Messages must be visibly destructive but not louder than primary page actions.
- Use a danger-outline treatment for the header button. If a reusable class does not exist, compose literal Tailwind classes in the template or add a small component class in `static/css/input.css` and rebuild `static/css/output.css`.
- The modal confirm button may use the existing filled `.btn-danger` pattern because it is the final destructive confirmation.

Palette guard:
- Do not introduce a new dominant color theme.
- Keep the existing admin palette; this phase should read as a small operational control addition.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Pause button, running state | `Pause` |
| Resume button, paused state | `Start` |
| Live badge, running state | `LIVE` |
| Live badge, paused state | `PAUSED` |
| Clear header button | `Clear Log Messages` |
| Confirmation title | `Clear Application Logs` |
| Destructive confirmation | `Clear all application log messages from the database. QSO records, users, and log settings are not affected.` |
| Confirm button | `Clear Log Messages` |
| Cancel button | `Cancel` |
| Success/audit row message | `Application logs cleared` |

Error/success handling:
- If clear succeeds and the audit row is saved, table should show the new audit row with deleted count metadata or context.
- If clear succeeds and the audit row cannot be saved, show a concise success status with a note that the audit message could not be written.
- Avoid wording like "clear displayed logs" or "clear filtered logs"; the action clears all application log records.

---

## Interaction Contract

### Pause/Start

- Pause is local to the current browser tab/session.
- Pause suppresses automatic SSE row insertion and near-live polling refreshes.
- Pause does not suppress intentional admin actions:
  - Applying filters still refreshes the table.
  - Reset link still works.
  - Previous/Next pagination still works.
- Start immediately refreshes/reconciles recent rows via the existing HTMX table refresh path.
- Start then reenables SSE row insertion and polling refreshes.
- Existing expanded metadata/error `<details>` state should continue to be preserved during polling refreshes where practical.

### Clear

- Header Clear button opens a confirmation modal; it must not delete records directly.
- Cancel/close removes the modal without table changes.
- Confirm clears all application log records, preserves `ApplicationLogSettings`, and refreshes the Recent Logs table.
- Clear should not change active filters, pagination controls, minimum level, or retention settings.
- After successful clear, live feed should remain in the same running/paused state the admin had before confirming.

### Accessibility

- Pause/Start button must use a real `<button>` with updated text and `aria-pressed` or equivalent state.
- Clear modal must use `role="dialog"` and `aria-modal="true"` with a labelled title.
- Controls must be keyboard focusable and use existing visible focus rings.
- Modal cancel and confirm buttons must be reachable in normal tab order.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not required |
| third-party | none | not allowed |

No UI registry, frontend package, or JavaScript framework additions are approved for this phase.

---

## Verification Expectations

- Source check that the Recent Logs header contains the status badge plus Pause/Start and Clear controls.
- Source/unit test for pause gating both SSE insert and polling fallback while allowing explicit HTMX filter/pagination refresh.
- Route/service tests for confirmation modal, clear execution, settings preservation, and table refresh/empty/audit behavior.
- Tailwind build/verify if new classes are added to templates or `static/css/input.css`.
- Browser/manual or template-level check that the header controls wrap cleanly on mobile width.

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-06-20
