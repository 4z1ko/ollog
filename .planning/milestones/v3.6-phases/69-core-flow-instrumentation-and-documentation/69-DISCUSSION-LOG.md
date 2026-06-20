# Phase 69: Core Flow Instrumentation and Documentation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-19
**Phase:** 69-core-flow-instrumentation-and-documentation
**Areas discussed:** Reconciliation depth, test strictness, documentation boundary

---

## Reconciliation Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Gap-fill only | Audit existing instrumentation against OBS-01–OBS-05, add missing events/tests/docs, avoid renaming or reshaping existing event names unless clearly wrong. | ✓ |
| Standardize existing events too | Normalize event names, source names, metadata keys, and transport labels where inconsistent. | |
| Strict minimum | Only add instrumentation where a requirement has no current evidence. | |

**User's choice:** Gap-fill only.
**Notes:** Phase 67 already added broad instrumentation, so Phase 69 should avoid unnecessary churn and focus on missing or weak coverage.

---

## Test Strictness

| Option | Description | Selected |
|--------|-------------|----------|
| Behavior-focused assertions | Verify important flows emit a log with right level/source/event type/transport and safe metadata without over-specifying every key. | |
| Exact event contracts | Assert precise event names and metadata shape for instrumented flows. | ✓ |
| Smoke coverage only | Check representative flows and rely on source review/docs for the rest. | |

**User's choice:** Exact event contracts.
**Notes:** This increases maintenance cost but gives clearer operational auditability for OBS-01 through OBS-05.

---

## Documentation Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Coverage-focused docs | Explain what flows are logged, how to filter/search them, and what fields admins can expect. | ✓ |
| Troubleshooting runbook | Add concrete admin scenarios and which filters/events to inspect. | |
| Minimal docs only | Only update existing docs enough to reflect final coverage and event categories. | |

**User's choice:** Coverage-focused docs.
**Notes:** The docs should provide operational clarity without becoming a full troubleshooting runbook.

---

## the agent's Discretion

- Planner may choose the exact gap audit and test fixture strategy.
- Planner should keep the phase scoped to OBS-01 through OBS-05.

## Deferred Ideas

- Full scenario troubleshooting runbook for admins.
- Broad event-name/metadata normalization unless required by a specific defect.
