# Phase 49: Service Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 49-service-layer
**Areas discussed:** Invalid sort fallback

---

## Invalid Sort Fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Silent fallback | Silently substitute default sort with no logging | |
| Log + fallback | Log a WARNING with rejected field, then fall back | ✓ |

**User's choice:** Log + fallback

---

### Follow-up: Log message content

| Option | Description | Selected |
|--------|-------------|----------|
| Field name only | "Invalid sort field '%s', falling back to default" | |
| Field + operator | Include operator callsign in message | ✓ |
| You decide | Leave wording to planner, enforce WARNING level | |

**User's choice:** Field + operator — include both the rejected field name and the operator callsign in the WARNING log message.

---

## Claude's Discretion

- `created_at` key name in view dict — user skipped this area; planner decides (recommended: `"created_at"` for clean Jinja2 access)
- `created_at` format in view dict — raw datetime object, consistent with `qso_date_utc`

## Deferred Ideas

None.
