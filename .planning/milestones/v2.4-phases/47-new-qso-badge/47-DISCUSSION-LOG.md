# Phase 47: New QSO Badge — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 47-new-qso-badge
**Areas discussed:** Badge visual design

---

## Badge Visual Design

### Area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Badge visual design | What does the badge look like? Slim full-width info bar vs. compact pill/chip. No design spec exists. | ✓ |
| Edit mode behavior | When a QSO row edit form is open on page 2+, should new SSE events increment the badge counter? | |

### Badge style

| Option | Description | Selected |
|--------|-------------|----------|
| Slim info bar | Full-width row above the table. Hard to miss, easy to dismiss. | |
| Compact pill chip | Small pill badge left-aligned above the table. Subtle — less prominent but less disruptive. | ✓ |

**User's choice:** Compact pill chip

### Badge color

| Option | Description | Selected |
|--------|-------------|----------|
| Amber/yellow | Signals "attention needed" — distinct from LIVE green and filter blue. | |
| Indigo (brand color) | Matches the app's primary button color. Consistent design language. | ✓ |
| You decide | Claude's discretion. | |

**User's choice:** Indigo (brand color)

**Notes:** User opted not to discuss edit mode behavior — left to Claude's discretion (badge increments on all SSE events when not on page 1, matching the existing sentinel mechanism).

---

## Claude's Discretion

- Edit mode behavior: badge increments even during row edit (consistent with "not page 1" logic)
- Exact Tailwind class set for the indigo pill
- Transition/animation on badge appear
- Icon choice (upward arrow or similar)

## Deferred Ideas

None.
