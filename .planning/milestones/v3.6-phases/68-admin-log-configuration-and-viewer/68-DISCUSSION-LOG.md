# Phase 68: Admin Log Configuration and Viewer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-19
**Phase:** 68-admin-log-configuration-and-viewer
**Areas discussed:** Reconcile Scope, Pagination Controls, Live Update Behavior, Log Detail Display

---

## Reconcile Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Reconcile gaps | Verify existing work, add only missing acceptance-criteria polish, and avoid duplicate implementation. | Yes |
| Full phase pass | Treat Phase 68 as a normal implementation phase even if it touches code already added. | |
| Verify only | Do not add polish unless something is clearly broken. | |

**User's choice:** Reconcile gaps
**Notes:** Phase 67 already shipped admin log viewer/configuration work, so Phase 68 should validate that work and close only remaining gaps.

---

## Pagination Controls

| Option | Description | Selected |
|--------|-------------|----------|
| Simple Previous/Next | Compact controls that match the operational recent-logs use case and use existing backend pagination. | Yes |
| Numbered pages | More precise navigation, but more UI surface. | |
| Backend-only | Keep API pagination but no visible UI controls. | |

**User's choice:** Simple Previous/Next
**Notes:** Current backend supports pagination, but the visible table only shows count text. Add compact controls.

---

## Live Update Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Insert immediately | Keeps the page truly live and matches the current implementation. | Yes |
| Show refresh prompt | Avoids table movement while reading, but makes live updates less direct. | |
| Insert only on first page | Keeps recent logs live while older pages stay stable. | |

**User's choice:** Insert immediately
**Notes:** Preserve existing live behavior, including client-side filtering of incoming SSE records.

---

## Log Detail Display

| Option | Description | Selected |
|--------|-------------|----------|
| Format collapsed JSON | Keep details collapsed, but render readable pretty JSON instead of raw Python-style dict text. | Yes |
| Keep raw dictionaries | Lowest effort, current behavior. | |
| Add context chips | Show event/QSO/bridge/correlation as chips plus formatted collapsed metadata/error details. | |

**User's choice:** Format collapsed JSON
**Notes:** Improve readability without broad UI redesign.

---

## the agent's Discretion

- Choose precise implementation details for Previous/Next controls.
- Keep existing admin styling and HTMX/SSE patterns.
- Add focused tests where behavior changes.

## Deferred Ideas

- Numbered pagination.
- Broader context-chip redesign for log row details.
