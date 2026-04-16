# Phase 43: Stats UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 43-stats-ui
**Areas discussed:** Nav link position

---

## Nav link position

| Option | Description | Selected |
|--------|-------------|----------|
| After Log View | Groups Stats with 'viewing your log' actions before import/export | ✓ |
| After Export | Groups Stats with data manipulation tools (import, export, analyze) | |
| After Profile | Near settings and info links at the bottom | |

**User's choice:** After Log View — new sidebar order: Log QSO → Log View → Stats → Import → Export → Profile → About

---

## Claude's Discretion

- Chart grid layout — 2-column (Band + Mode) top row, DXCC full-width below
- Page width — `max-w-5xl mx-auto`
- Summary metrics placement — Total QSOs in compact header; unique entity count inline with DXCC chart title
- Dark mode hook — `CustomEvent('themechange')` dispatch from `toggleTheme()`, listened in `stats.html`
- Chart color palettes — indigo/violet/emerald/amber family, dark/light variants

## Deferred Ideas

None.
