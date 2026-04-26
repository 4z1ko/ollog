# Phase 52: TIME_ON DB Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-26
**Phase:** 52-time-on-db-migration
**Areas discussed:** Migration mechanism, DB-02 disposition, Test coverage, Test file location, Logging format, Regex scope

---

## Migration mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| update_many + aggregation pipeline | Single MongoDB call with regex filter and $concat update; no cursor iteration | ✓ |
| Cursor + bulk_write | Match existing backfill_created_at pattern: cursor.find(), build UpdateOne ops, bulk_write | |
| You decide | Let Claude choose whichever fits the implementation | |

**User's choice:** update_many + aggregation pipeline
**Notes:** STATE.md research explicitly recommended this approach. Anchored regex `^\d{4}$` prevents double-padding.

---

## DB-02 disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Test confirming both formats accepted | Write pytest test asserting HHMM and HHMMSS both succeed via service layer | ✓ |
| Code comment only | Add comment noting DB-02 is satisfied by existing parse_adif_datetime branches | |
| Nothing — already covered | parse_adif_datetime tests cover it implicitly; no additional work | |

**User's choice:** Test confirming both formats accepted
**Notes:** Makes DB-02 verifiably green rather than assumed. Test goes in tests/test_migration.py.

---

## Test coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Integration test hitting real MongoDB | Consistent with existing test suite; insert HHMM docs, run migration, assert HHMM00 + idempotency | ✓ |
| Unit test with mock collection | AsyncMock patch; isolated but departs from codebase pattern | |
| No test for migration function | Rely on DB-02 tests and startup log | |

**User's choice:** Integration test hitting real MongoDB
**Notes:** Must test both padding correctness and idempotency (run twice, no double-padding).

---

## Test file location

| Option | Description | Selected |
|--------|-------------|----------|
| New tests/test_migration.py | Keeps startup migration tests grouped; clean separation from QSO CRUD tests | ✓ |
| Add to tests/test_qso.py | TIME_ON is a QSO field; but test_qso.py is already substantial | |

**User's choice:** New tests/test_migration.py

---

## Logging format

| Option | Description | Selected |
|--------|-------------|----------|
| Follow backfill_created_at style | Two-branch log: "N documents updated" or "0 documents — already up to date" | ✓ |
| Single line regardless of count | Always log modified_count; simpler, no branch | |

**User's choice:** Follow backfill_created_at style

---

## Regex scope

| Option | Description | Selected |
|--------|-------------|----------|
| All operators — no _operator filter | Admin-level startup migration; HHMM00 is correct for every operator | ✓ |
| Per-operator batching | Iterate operators, run update_many per operator; more complex, no real benefit | |

**User's choice:** All operators — no _operator filter

---

## Claude's Discretion

- Exact pymongo async API calls for aggregation pipeline update_many
- Whether to use get_pymongo_collection() or Motor client directly

## Deferred Ideas

None.
