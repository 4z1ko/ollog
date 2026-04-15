# Phase 42: Stats Aggregation Backend - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-15
**Phase:** 42-stats-aggregation-backend
**Areas discussed:** DXCC Entity Labels

---

## DXCC Entity Labels

### Question 1: Entity name for chart labels

| Option | Description | Selected |
|--------|-------------|----------|
| pycountry full name | e.g. 'Germany', 'Japan', 'United States'. Already imported in ui_router.py. Familiar to operators. | ✓ |
| ISO alpha-2 code | e.g. 'DE', 'JP', 'US'. Short but unfamiliar on chart slices. | |
| ITU prefix name | Raw ITU table name — verbose for chart labels. | |

**User's choice:** pycountry full name
**Notes:** pycountry is already a project dependency and the natural fit.

---

### Question 2: Unresolvable callsigns (lookup_prefix returns None)

| Option | Description | Selected |
|--------|-------------|----------|
| Bucket as 'Unknown' | All unresolvable QSOs grouped under a single 'Unknown' label. Total QSO count stays consistent. | ✓ |
| Exclude silently | Omit from DXCC chart — counts may not add up to total QSOs. | |
| You decide | Leave to Claude based on existing callsign module conventions. | |

**User's choice:** Bucket as 'Unknown'
**Notes:** Operator can see all QSOs accounted for in the chart.

---

## Claude's Discretion

- Module placement (new `app/stats/` module vs extending qso service)
- Aggregation pipeline architecture (1 vs 3 pipelines)
- Template data shape key names

## Deferred Ideas

None.
