---
phase: 68
slug: admin-log-configuration-and-viewer
status: approved
shadcn_initialized: false
preset: none
created: 2026-06-19
---

# Phase 68 — UI Design Contract

> Visual and interaction contract for the admin application log viewer reconciliation phase.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | not applicable |
| Component library | none |
| Icon library | inline existing admin SVG icons only; do not introduce a new icon dependency |
| Font | existing system font stack from Tailwind/base CSS |

Phase 68 must reuse the existing admin visual language:

- Page shell from `templates/base_app.html`
- Admin sidebar/nav pattern from existing admin templates
- `card`, `card-header`, `card-title`, `card-body`
- `data-table`, `table-wrap`
- `form-label`, `form-input`, `form-select`
- `btn-primary`, `btn-ghost`
- Existing badge styles such as `badge-blue`

No new UI framework, component registry, or broad admin redesign is in scope.

---

## Spacing Scale

Declared values are inherited from Tailwind spacing and existing component classes.

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Inline log detail spacing and metadata line spacing |
| sm | 8px | Button gaps, compact pagination control gaps |
| md | 16px | Form grid gaps and table footer padding |
| lg | 24px | Card-to-card vertical rhythm |
| xl | 32px | Not required for Phase 68 changes |
| 2xl | 48px | Not required for Phase 68 changes |
| 3xl | 64px | Not required for Phase 68 changes |

Exceptions: none. Do not introduce custom one-off spacing values.

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 14px (`text-sm`) | 400 | 1.25rem |
| Label | 12px (`text-xs`) | 600 | 1rem |
| Page heading | 20px (`text-xl`) | 700 | 1.75rem |
| Card heading | 14px (`card-title`) | 600 | existing component default |
| Table metadata | 12px (`text-xs`) | 400 | 1rem |
| JSON detail text | 12px (`text-xs font-mono`) | 400 | 1rem |

Use monospace only for timestamps, source/module names, and formatted JSON details. Do not scale font sizes with viewport width.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | existing light/dark canvas (`bg-canvas-light`, `dark:bg-canvas-dark`) | Page background |
| Secondary (30%) | existing card/table surfaces (`bg-white`, `dark:bg-surface-dark`, `dark:bg-gray-900`) | Cards, table wrappers, collapsed detail blocks |
| Accent (10%) | existing indigo/blue component accents | Primary buttons, LIVE badge, level badges, focus rings |
| Destructive | existing rose/red text classes only | Error detail summary text and validation errors |

Accent reserved for: Save Settings, Apply Filters, level/live badges, focus rings. Do not add new bright palettes for pagination or JSON details.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | Save Settings |
| Filter CTA | Apply Filters |
| Pagination CTAs | Previous, Next |
| Pagination status | Showing {start}-{end} of {total} log records. |
| Empty state heading | No application logs match these filters. |
| Empty state body | No extra body copy; keep table empty state compact. |
| Live status | LIVE / OFFLINE |
| Metadata summary | metadata |
| Error summary | error |
| Error state | Use the existing settings error fragment copy from validation messages. |
| Destructive confirmation | Not applicable; Phase 68 has no destructive action. |

Copy must be operational and short. Do not add visible feature tutorials or marketing-style explanation inside the app.

---

## Interaction Contract

### Scope Reconciliation

- Treat the current admin Logs page as the baseline.
- Preserve existing settings, filters, SSE stream, admin auth, and docs unless a concrete acceptance gap is found.
- Phase 68 UI changes should be limited to visible pagination controls and readable collapsed detail formatting.

### Pagination

- Add simple Previous/Next controls in `templates/admin/logs_table.html`.
- Controls belong in the existing table footer area next to or below the count text.
- Use `btn-ghost` or a visually consistent compact button/link style.
- Preserve active filters while paging.
- Disable or visually de-emphasize Previous on page 1.
- Disable or visually de-emphasize Next when there are no more results.
- Do not add numbered pages.

### Live Updates

- Keep immediate insertion for matching SSE log events.
- Preserve current filter matching for level/source/search/date filters.
- Do not add a refresh prompt.
- New live rows should not resize table controls or shift page chrome outside normal row insertion.

### Log Details

- Metadata and error details remain collapsed by default using `<details>`.
- Render detail payloads as readable formatted JSON in a `<pre>` block.
- Use the existing compact mono style and scroll horizontally when long lines appear.
- Do not expose raw Python-style dict rendering.
- Do not redesign event/QSO/bridge/correlation context into a new chip system in this phase.

### Responsive Behavior

- Existing table horizontal scrolling is acceptable and should remain.
- Filters keep the current responsive grid behavior.
- Pagination controls should wrap cleanly on narrow screens without overlapping the count text.
- Button labels must remain readable and must not shrink with viewport width.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not required |
| third-party registries | none | not allowed for Phase 68 |

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS — copy is short, operational, and matches current admin page tone.
- [x] Dimension 2 Visuals: PASS — contract reuses existing admin cards, tables, controls, and dense operational layout.
- [x] Dimension 3 Color: PASS — no new palette; existing canvas/card/accent/destructive colors only.
- [x] Dimension 4 Typography: PASS — uses existing text sizes and monospace only for log-like data.
- [x] Dimension 5 Spacing: PASS — uses existing Tailwind/component spacing and avoids custom one-offs.
- [x] Dimension 6 Registry Safety: PASS — no external UI registry or component dependency.

**Approval:** approved 2026-06-19
