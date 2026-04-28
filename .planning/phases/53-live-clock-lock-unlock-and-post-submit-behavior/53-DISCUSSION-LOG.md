# Phase 53: Live Clock, Lock/Unlock, and Post-Submit Behavior - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-28
**Phase:** 53-live-clock-lock-unlock-and-post-submit-behavior
**Areas discussed:** Reset toggle UI, Padlock placement, Locked field styling, Post-submit focus

---

## Reset Toggle UI

### Widget type

| Option | Description | Selected |
|--------|-------------|----------|
| Radio buttons | Two labeled choices side-by-side; always visible and explicit | |
| Checkbox | Single checkbox: "Reset to live UTC after submit" | |
| Toggle switch | On/off switch, styled with pure Tailwind utility classes | ✓ |

**User's choice:** Toggle switch

### Toggle position

| Option | Description | Selected |
|--------|-------------|----------|
| Inline with submit row | Same flex row as "Log QSO" + "Clear" buttons | ✓ |
| Row above submit | Dedicated row spanning full form width | |
| Below date/time fields | Near the fields it controls | |

**User's choice:** Inline with submit row

### Toggle implementation

| Option | Description | Selected |
|--------|-------------|----------|
| Pure Tailwind utility classes | Hidden checkbox + styled label in form.html | ✓ |
| New .toggle CSS component in input.css | Reusable class, requires npm run build | |

**User's choice:** Pure Tailwind utility classes

### Toggle default state

| Option | Description | Selected |
|--------|-------------|----------|
| Reset to live UTC (ON) | Safe default for first-time operators | ✓ |
| Keep current date/time (OFF) | Operator must explicitly enable auto-reset | |

**User's choice:** Reset to live UTC (ON)

---

## Padlock Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Inline suffix inside input wrapper | Password show/hide style; input gets padding-right | ✓ |
| Appended button after input | Standalone button outside input, flex row | |
| Icon next to label | Padlock in label area above the input | |

**User's choice:** Inline suffix inside input wrapper

---

## Locked Field Styling

| Option | Description | Selected |
|--------|-------------|----------|
| Subtle background change | Muted bg + cursor-not-allowed when locked; normal form-input when unlocked | ✓ |
| Icon only — no background change | Same styling locked vs unlocked | |

**User's choice:** Subtle background change (muted bg + cursor-not-allowed)

---

## Post-Submit Focus

| Option | Description | Selected |
|--------|-------------|----------|
| CALL field | Always focus CALL after submit, both modes | ✓ |
| No focus change | Leave focus wherever it is in "Keep current" mode | |

**User's choice:** Always focus CALL field

---

## Claude's Discretion

- Exact Tailwind utility classes for toggle pill and thumb
- `initDateTime()` function name and exact structure
- Heroicons SVG `<path>` data for lock-closed and lock-open (outline, w-4 h-4)
- Padlock wrapper — relative div or flex row

## Deferred Ideas

None.
