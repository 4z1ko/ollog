# Phase 62: Cross-Feature Integration and Verification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-08
**Phase:** 62-cross-feature-integration-and-verification
**Areas discussed:** Live Feed Strategy, Backup/Restore Scope, Admin/Stats Routing, Verification Depth

---

## Live Feed Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Watch all user collections | Start one Mongo change stream per known user QSO collection. Closest to current watcher behavior but more moving parts. | |
| Broadcast from write paths | Publish SSE events directly after successful app-created QSO writes. Simpler and avoids dynamic change streams. | ✓ |
| Hybrid | Broadcast from write paths and keep a small watcher fallback or refresh mechanism. | |

**User's choice:** Broadcast from write paths
**Notes:** Planner should preserve live updates for supported app write paths. Manual DB inserts, restore operations, and migration/backfill events do not need live feed broadcasts in Phase 62.

---

## Backup/Restore Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Pattern include | Backup and restore collections matching `*_qsos` plus fixed app collections. | |
| Enumerate users | Backup only collections derived from current users in `users`. | |
| All collections | Backup the entire configured MongoDB database as-is. | ✓ |

**User's choice:** 3
**Notes:** The current backup model is full database backup/restore. Phase 62 should preserve that disaster-recovery contract and add tests proving dynamic QSO collections are included.

---

## Admin/Stats Routing

| Option | Description | Selected |
|--------|-------------|----------|
| Direct feature wiring | Stats and admin routes call collection helpers directly. | |
| Shared service helpers | Add small helper APIs so routes stay thin without a broad repository layer. | ✓ |
| Repository layer | Create a broad QSO repository abstraction for future reads/writes. | |

**User's choice:** 2
**Notes:** Use small shared helpers, not a full repository abstraction.

---

## Verification Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Representative coverage | Focused tests for each feature path plus a few isolation checks. | |
| Broad live-Mongo isolation suite | Exercise every major feature path with two users and real per-user collections. | |
| Layered | Unit/fake-collection tests for helpers, route tests where practical, and a smaller live-Mongo suite for highest-risk paths. | ✓ |

**User's choice:** 3
**Notes:** Layered verification gives confidence without making every test require MongoDB availability.

## the agent's Discretion

- Exact helper names and module placement.
- Exact feed broadcast helper location and integration mechanics.
- Final minimum test set, provided it covers INT-01..05 and VERIFY-03..04.

## Deferred Ideas

None.
