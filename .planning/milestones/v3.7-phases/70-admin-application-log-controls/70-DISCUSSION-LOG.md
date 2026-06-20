# Phase 70: Admin Application Log Controls - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-20
**Phase:** 70-admin-application-log-controls
**Areas discussed:** Pause/Start Behavior, Clear Result Behavior, Button Placement and Visual State, Clear Scope Wording

---

## Pause/Start Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Fetch missed | Immediately refresh/reconcile recent rows so the admin catches up without a page refresh. | ✓ |
| Continue forward | Only show new records from the next SSE or polling event after resume. | |
| You decide | Let implementation choose the simplest behavior that still feels reliable. | |

**User's choice:** Fetch missed.
**Notes:** The user wants Start/Resume to catch up immediately.

| Option | Description | Selected |
|--------|-------------|----------|
| Filters still refresh | Pause only stops live feed/polling; intentional filter/pagination actions still update the table. | ✓ |
| Freeze everything | Pause locks the table until Start/Resume. | |
| You decide | Choose the behavior that best matches existing HTMX patterns. | |

**User's choice:** Filters still refresh.
**Notes:** Pause should be scoped to automatic live updates, not deliberate admin table actions.

---

## Clear Result Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Show audit message | Clear records, then create/show a fresh "Application logs cleared" log entry with deleted count. | ✓ |
| Stay empty | Clear records and leave the table empty until some future app event logs naturally. | |
| Toast/status only | Show a temporary UI success message, but do not create a new log row for the clear action. | |

**User's choice:** Show audit message.
**Notes:** The admin should see evidence that clear happened, including the deleted count.

| Option | Description | Selected |
|--------|-------------|----------|
| Still succeed | Clearing logs is the main action; show a UI success message with a note that audit logging could not be written. | ✓ |
| Treat as failure | If the audit message cannot be saved, report the whole clear as failed. | |
| You decide | Choose during implementation based on current logger failure-isolation behavior. | |

**User's choice:** Still succeed.
**Notes:** Audit logging failure should not roll back or fail a successful clear.

---

## Button Placement and Visual State

| Option | Description | Selected |
|--------|-------------|----------|
| Recent Logs header | Put Pause/Start and Clear in the card header next to the LIVE/PAUSED badge. | ✓ |
| Below filters | Put the controls between Filters and Recent Logs. | |
| Inside table footer | Put controls near pagination. | |

**User's choice:** Recent Logs header.
**Notes:** Controls belong with the table they affect and next to the live status.

| Option | Description | Selected |
|--------|-------------|----------|
| Danger outline | Visible red/danger styling, but not visually louder than primary page actions. | ✓ |
| Danger filled | Strong red filled button to emphasize destructive action. | |
| Neutral until modal | Normal/ghost button, with danger styling only inside the confirmation modal. | |

**User's choice:** Danger outline.
**Notes:** Clear should be visibly destructive without dominating the page.

---

## Clear Scope Wording

| Option | Description | Selected |
|--------|-------------|----------|
| All application logs | "Clear all application log messages from the database. QSO records, users, and log settings are not affected." | ✓ |
| Database table records | "Clear all records in the application logs database table/collection." | |
| Recent Logs records | "Clear all messages shown in Recent Logs." | |

**User's choice:** All application logs.
**Notes:** The wording should make the database-wide scope clear while reassuring that QSO records, users, and log settings are untouched.

## the agent's Discretion

- Exact icon choice, button microcopy, and success/error fragment text can follow existing admin UI patterns.

## Deferred Ideas

- Export/download filtered application logs.
- Clear logs by active filter or date range.
- Password-confirmed clear for higher-friction destructive behavior.
- Global live-feed pause across all browser sessions.
