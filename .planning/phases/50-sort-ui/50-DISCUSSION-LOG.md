# Phase 50: Sort UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-23
**Phase:** 50-sort-ui
**Areas discussed:** Clock icon in DATE header, Inactive sort indicator, Sort direction consistency

---

## Clock icon in DATE header

### DATE header layout

| Option | Description | Selected |
|--------|-------------|----------|
| Side by side inline | Two separate `<a>` elements in the DATE `<th>`: date sort link + clock sort link, each with its own chevron state | ✓ |
| Clock appended to date link | Tiny standalone clock `<a>` visually tight after the date text+chevron, no gap | |

**User's choice:** Side by side inline
**Notes:** The `<th>` becomes a flex container with two independent clickable elements. Each element shows its own sort state (hollow ↕ when not active, solid ↓/↑ when active).

---

### Clock icon chevron behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Clock + hollow chevron | Clock SVG + hollow ↕ when inactive; clock SVG + solid directional chevron when active. Consistent with all other sort columns. Satisfies UX-01 literally. | ✓ |
| Clock only, no extra chevron | Clock SVG is the trigger; turns accent color when active. No additional chevron. Cleaner but deviates from UX-01 spec. | |

**User's choice:** Clock + hollow chevron
**Notes:** Follows the same "element + chevron" pattern as all other sort columns.

---

## Inactive sort indicator

| Option | Description | Selected |
|--------|-------------|----------|
| Heroicons chevrons-up-down | Heroicons outline `chevrons-up-down` icon (↕), w-3 h-3, opacity-30. Most semantically correct "sortable" indicator. | ✓ |
| Faint filled chevron pair (custom SVG) | Same filled SVG as active chevrons, both up+down stacked, at low opacity. 100% consistent with active chevron approach. | |

**User's choice:** Heroicons chevrons-up-down
**Notes:** Standard ↕ sort indicator. Consistent with common data-table UI patterns.

---

## Sort direction consistency

| Option | Description | Selected |
|--------|-------------|----------|
| MODE only, leave CALL/BAND | Implement MODE ascending-first per spec; don't touch CALL/BAND. Minor inconsistency accepted. | ✓ |
| Fix all three to ascending-first | Update CALL, BAND, and MODE all to ascending-first for consistent UX. | |

**User's choice:** MODE only, leave CALL/BAND
**Notes:** CALL/BAND sort behavior is out of Phase 50 scope. MODE ascending-first is mandated by the success criteria.

---

## Claude's Discretion

- Exact clock SVG path (Heroicons `clock` outline, 20px viewBox preferred)
- Whether to use an explicit `<span>` wrapper for the two DATE sort links or rely on `<th>` flex context
- Dark mode opacity value for inactive indicator (25 vs 30)

## Deferred Ideas

- `_created_at` tooltip on QSO date cell (explicitly in REQUIREMENTS.md future requirements)
- CALL/BAND ascending-first sort direction (minor inconsistency, future cleanup if desired)
