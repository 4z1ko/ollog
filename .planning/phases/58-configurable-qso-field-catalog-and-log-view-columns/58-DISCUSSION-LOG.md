# Phase 58: Configurable QSO Field Catalog and Log View Columns - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-03
**Phase:** 58-configurable-qso-field-catalog-and-log-view-columns
**Areas discussed:** Field catalog boundaries, menu shape for many fields, column order behavior, value formatting rules, sorting with optional columns

---

## Field Catalog Boundaries

| Option | Description | Selected |
|--------|-------------|----------|
| Only known ADIF/common fields | Use a curated known catalog of QSO/ADIF fields. | ✓ |
| Dynamically discovered fields | Scan current QSOs and expose any stored field name. | |
| Both known and discovered fields | Combine a known catalog with discovered extras. | |

**User's choice:** Only known ADIF/common fields.
**Notes:** This avoids unpredictable menus and keeps the phase scoped to a stable supported display catalog.

---

## Menu Shape for Many Fields

| Option | Description | Selected |
|--------|-------------|----------|
| One scrollable checklist | Keep the current gear-menu checklist pattern with bounded scrolling. | ✓ |
| Grouped sections | Organize fields by category, such as Core, Station, Award, App. | |
| Search/filter in menu | Add a text filter to find field names quickly. | |

**User's choice:** One scrollable checklist.
**Notes:** Preserve the compact current configuration menu; do not add grouping or search in this phase.

---

## Column Order Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed catalog order | Selected columns render in catalog order. | |
| Selected fields append after defaults | Defaults stay first; extra selected fields appear after them. | ✓ |
| User-selected order | Preserve click/selection order or add reorder controls. | |

**User's choice:** Selected fields append after defaults.
**Notes:** The current default columns remain the baseline and extra fields extend the table rather than rearranging it.

---

## Value Formatting Rules

| Option | Description | Selected |
|--------|-------------|----------|
| Raw ADIF values | Render stored values directly. | |
| Humanized display values | Use readable display formatting where conventions exist. | ✓ |
| Special formatting only for defaults | Keep special handling only for current default columns. | |

**User's choice:** Humanized display values.
**Notes:** Preserve existing user-facing formatting, including readable UTC date/time, callsign flag enrichment, and paired RST display for the default RST column.

---

## Sorting with Optional Columns

| Option | Description | Selected |
|--------|-------------|----------|
| Only current sortable fields | Keep sort controls on Date / Time, entry timestamp, Callsign, Band, and Mode. | ✓ |
| Make selected ADIF fields sortable | Add sort controls for additional selected fields. | |
| Expand sorting for a small allowlist | Add a few additional sortable ADIF fields. | |

**User's choice:** Only current sortable fields keep sort controls.
**Notes:** Broad sortable-field expansion is deferred to avoid turning the phase into a sorting/indexing project.

---

## the agent's Discretion

- Exact known-field catalog contents.
- Exact field labels, provided they are human-readable and stable.
- Exact implementation structure for catalog, extraction, and stale localStorage handling.

## Deferred Ideas

- Dynamic field discovery from the operator's current QSO data.
- Column drag/reorder or custom selected ordering.
- Search/filter inside the column menu.
- Sort controls for every selected ADIF/common field.
