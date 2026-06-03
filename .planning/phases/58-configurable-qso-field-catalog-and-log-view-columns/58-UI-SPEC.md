---
phase: 58
slug: configurable-qso-field-catalog-and-log-view-columns
status: approved
shadcn_initialized: false
preset: none
created: 2026-06-03
---

# Phase 58 — UI Design Contract

> Visual and interaction contract for making the Log View column configuration menu support all known QSO/ADIF display fields.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | not applicable |
| Component library | none |
| Icon library | inline Heroicons-style SVG already used in templates |
| Font | `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif` |

Use the existing ollog operator app component classes: `btn-ghost`, `btn-sm`, `table-wrap`, `data-table`, and existing light/dark Tailwind tokens. Do not introduce a new component library or a new visual motif.

---

## UI Scope

### In Scope

- Existing gear icon button remains the entry point for column configuration.
- The menu becomes a single bounded scrollable checklist of known QSO/ADIF display fields.
- Fresh browsers keep the current visible columns: Date / Time, Callsign, Band, Mode, Frequency, RST.
- Additional selected fields append after the default columns in catalog order.
- The Actions column remains always visible and is not part of the checklist.
- Current sortable headers keep their visual sort controls when visible.
- Non-sortable selected fields render plain headers.
- Existing Log View page structure, filter card, live badge, new-QSO badge, table wrapper, pagination, and inline row actions remain visually stable.

### Out of Scope

- Grouped menu sections.
- Search/filter inside the menu.
- Drag/reorder controls.
- User-defined column ordering.
- Dynamic discovery of fields from stored QSOs.
- New sortable ADIF field headers beyond existing sortable fields.
- Profile-backed column preferences.

---

## Interaction Contract

| Element | Contract |
|---------|----------|
| Gear button | Remains `btn-ghost btn-sm`, icon-only, with `aria-label="Configure table columns"`, `title="Configure table columns"`, and `aria-expanded` toggled on open/close. |
| Menu open/close | Click gear toggles menu; click inside menu does not close it; click outside closes it. Existing behavior should remain. |
| Checklist | One flat checklist. Each row is a label wrapping a checkbox and field label. No section headers and no explanatory text inside the app UI. |
| Menu bounds | Menu must have a fixed responsive width and a max height with vertical scrolling. It must fit in mobile and desktop viewports without covering the whole page. |
| Selection persistence | Continue using `localStorage` key `ollog.log.columns`. Invalid/stale keys are ignored. If no valid selected keys remain, defaults are restored. |
| Column visibility | Render all catalog columns in the table and use client-side `hidden` toggling for selected visibility, matching the current HTMX-friendly model. |
| Column order | Default columns appear first. Selected non-default fields append after defaults in catalog order. Deselected defaults are hidden, but when reselected they return to the default area. |
| Actions | Edit/Delete controls stay at the row end and remain visible even when all configurable fields are hidden or stale localStorage is present. |
| HTMX swaps | After HTMX table swaps, visibility is re-applied so selected columns persist through filtering, sorting, pagination, and SSE-triggered refresh. |

---

## Visual Contract

### Column Menu

- Placement: absolute, right aligned below the existing gear button.
- Width: wider than current `w-48`; target a compact but readable menu such as `w-72 max-w-[calc(100vw-2rem)]`.
- Height: bounded with vertical scrolling, such as `max-h-[min(28rem,calc(100vh-8rem))] overflow-y-auto`.
- Shape: `rounded-md`, not pill-shaped.
- Surface: light `bg-white`, dark `dark:bg-gray-900`.
- Border: `border border-gray-200 dark:border-gray-800`.
- Shadow: use existing `shadow-lg`.
- Padding: `p-2`.
- Checklist row: `flex items-center gap-2 px-2 py-1.5 text-sm rounded hover:bg-gray-50 dark:hover:bg-gray-800`.
- Checkbox: stable `w-4 h-4`, rounded border, indigo checked/focus state consistent with existing menu checkboxes.
- Labels: readable, humanized field names. Long labels should not overflow the menu; allow normal wrapping or truncate only if the full native field name remains understandable.

### Table

- Keep `table-wrap` and `data-table` styling.
- Header cells keep existing compact uppercase table style from `.data-table th`.
- Header text must not become hero-scale; use existing `text-xs font-semibold uppercase tracking-wider`.
- Sortable headers keep existing icon sizing and chevron opacity: active solid arrow, inactive hollow double-chevron with `opacity-30 dark:opacity-25`.
- Non-sortable selected headers render plain label text with no chevron placeholder.
- Row cells keep existing `.data-table td` spacing and `whitespace-nowrap`.
- Missing values render as visually empty cells, not placeholder punctuation.
- Date / Time and Callsign cells preserve current special formatting:
  - Date / Time: readable UTC timestamp.
  - Callsign: optional flag image before callsign.
  - RST default column: paired sent/received value.

### Responsive Behavior

- Horizontal overflow remains handled by `.table-wrap`.
- The menu must remain usable on narrow screens without extending outside the viewport.
- No page layout shift when opening the menu.
- No table resize flicker during hover, checkbox changes, or HTMX swaps.

---

## Spacing Scale

Declared values (must be multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps, checkbox edge spacing |
| sm | 8px | Checklist row horizontal gaps, menu padding |
| md | 16px | Header/action gaps, table cell minimum rhythm |
| lg | 24px | Existing card/filter spacing |
| xl | 32px | Existing page section spacing |
| 2xl | 48px | Existing empty-state vertical breathing room |
| 3xl | 64px | Not needed for this phase |

Exceptions: none.

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 14px | 400 | 1.25rem |
| Menu row label | 14px | 400 | 1.25rem |
| Table header | 12px | 600 | 1rem |
| Page heading | 20px | 700 | 1.75rem |

Do not add negative letter spacing. Do not scale font size with viewport width. Keep labels concise and field-like: `QSO Date`, `Time On`, `Station Callsign`, `Contest ID`, `LoTW QSL Rcvd`.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#f2f2f7` light / `#0f0f0f` dark | App canvas inherited from existing shell |
| Secondary (30%) | `#ffffff` light / `#1c1c1e`, `#111827` dark | Cards, table/menu surfaces |
| Accent (10%) | Indigo `#4f46e5`, `#6366f1`, `#818cf8` | Checkbox checked state, focus ring, existing sort/link hover states |
| Destructive | Rose `#e11d48` | Existing Delete action only |

Accent reserved for: checkbox checked/focus state, existing sort/link hover states, existing badges/buttons. Do not recolor the whole menu or table with a new palette.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Gear button accessible label | Configure table columns |
| Menu item labels | Human-readable field names derived from catalog labels |
| Empty state heading | No contacts found |
| Empty state body | Try adjusting your filters or log a new QSO |
| Error state | Not introduced in this phase |
| Destructive confirmation | Existing delete confirmation remains unchanged |

No visible instructional copy should be added to explain how the menu works. The control should be familiar enough as a checklist.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not required |
| third-party | none | not applicable |

No external UI registry, icon package, component package, or CSS framework change is allowed for this phase.

---

## Implementation Guardrails

- New Tailwind classes must appear as literal strings in scanned template files.
- If new Tailwind classes are added, run the CSS build and verify generated output contains the new classes.
- Preserve the FOUC-prevention behavior in `templates/base.html`; this phase should not touch it.
- Preserve `color-scheme` dark/light behavior and existing dark-mode classes.
- Keep the menu and table as operational UI, not a marketing/hero layout.
- Do not put a card inside another card.

---

## UI Verification Checklist

- [x] Dimension 1 Copywriting: PASS — copy is limited, functional, and consistent with current Log View.
- [x] Dimension 2 Visuals: PASS — menu/table contract reuses existing components and avoids a visual redesign.
- [x] Dimension 3 Color: PASS — accent remains restrained and existing palette is preserved.
- [x] Dimension 4 Typography: PASS — compact table/menu typography is locked.
- [x] Dimension 5 Spacing: PASS — menu/list/table spacing uses existing 4px-derived Tailwind scale.
- [x] Dimension 6 Registry Safety: PASS — no registry or component package use.

**Approval:** approved 2026-06-03
