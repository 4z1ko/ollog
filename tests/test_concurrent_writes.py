"""Integration tests for concurrent write safety across multiple operators.

These tests exercise MongoDB directly via Beanie model operations to isolate
database-level behaviour from HTTP routing concerns.

Run:
    python -m pytest tests/test_concurrent_writes.py -v
Requires: MongoDB reachable at localhost:27017.
"""
import asyncio
from datetime import datetime, timezone

import pytest

from app.qso.models import QSO


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_qso(operator: str, call: str, **kwargs) -> QSO:
    """Return an unsaved QSO document with sensible defaults."""
    return QSO(
        **{
            "_operator": operator,
            "CALL": call,
            "BAND": kwargs.get("BAND", "20M"),
            "MODE": kwargs.get("MODE", "SSB"),
            "qso_date_utc": kwargs.get(
                "qso_date_utc",
                datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
            ),
        }
    )


# ---------------------------------------------------------------------------
# Test 1 — two operators, same contact details, both succeed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_two_operators_same_contact_both_succeed(test_db):
    """Two operators logging an identical contact (same CALL/BAND/MODE/time)
    must both succeed — they differ only in _operator so they are not
    duplicates of each other.
    """
    shared_time = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    qso_a = _make_qso("AA1AA", "W1AW", qso_date_utc=shared_time)
    qso_b = _make_qso("BB2BB", "W1AW", qso_date_utc=shared_time)

    # Both inserts must succeed without DuplicateKeyError
    await qso_a.insert()
    await qso_b.insert()

    docs = await QSO.find({"_deleted": False}).to_list()
    assert len(docs) == 2, f"Expected 2 documents, got {len(docs)}"

    operators = {d.operator_callsign for d in docs}
    assert operators == {"AA1AA", "BB2BB"}


# ---------------------------------------------------------------------------
# Test 2 — 20 concurrent inserts produce no lost writes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_concurrent_inserts_no_lost_writes(test_db):
    """asyncio.gather() across 20 inserts (10 per operator) must produce
    exactly 20 documents in the collection — no write is lost.
    """
    shared_time = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    tasks = []
    for i in range(10):
        tasks.append(_make_qso("AA1AA", f"W{i}TEST", qso_date_utc=shared_time).insert())
        tasks.append(_make_qso("BB2BB", f"W{i}TEST", qso_date_utc=shared_time).insert())

    await asyncio.gather(*tasks)

    total = await QSO.count()
    assert total == 20, f"Expected 20 documents, got {total}"

    aa_count = await QSO.find({"_operator": "AA1AA"}).count()
    bb_count = await QSO.find({"_operator": "BB2BB"}).count()
    assert aa_count == 10, f"Expected 10 for AA1AA, got {aa_count}"
    assert bb_count == 10, f"Expected 10 for BB2BB, got {bb_count}"


# ---------------------------------------------------------------------------
# Test 3 — correct attribution under concurrency
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_concurrent_inserts_correct_attribution(test_db):
    """No cross-contamination of _operator values when inserting concurrently.

    Each operator's QSOs must carry only their own callsign; CALL values
    assigned to AA1AA must not appear under BB2BB and vice-versa.
    """
    shared_time = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    tasks_aa = [
        _make_qso("AA1AA", f"W{i}A", qso_date_utc=shared_time).insert()
        for i in range(1, 6)
    ]
    tasks_bb = [
        _make_qso("BB2BB", f"W{i}B", qso_date_utc=shared_time).insert()
        for i in range(1, 6)
    ]

    await asyncio.gather(*tasks_aa, *tasks_bb)

    aa_qsos = await QSO.find({"_operator": "AA1AA"}).to_list()
    bb_qsos = await QSO.find({"_operator": "BB2BB"}).to_list()

    aa_calls = sorted(q.CALL for q in aa_qsos)
    bb_calls = sorted(q.CALL for q in bb_qsos)

    assert aa_calls == ["W1A", "W2A", "W3A", "W4A", "W5A"], (
        f"AA1AA call mismatch: {aa_calls}"
    )
    assert bb_calls == ["W1B", "W2B", "W3B", "W4B", "W5B"], (
        f"BB2BB call mismatch: {bb_calls}"
    )

    # No cross-contamination: AA calls must not appear under BB and vice-versa
    aa_call_set = set(aa_calls)
    bb_call_set = set(bb_calls)
    assert aa_call_set.isdisjoint(bb_call_set), (
        f"Cross-contamination detected: {aa_call_set & bb_call_set}"
    )


# ---------------------------------------------------------------------------
# Test 4 — same-operator duplicate race documented
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_same_operator_duplicate_race_documented(test_db):
    """This test proves the known race window — two identical QSOs from the
    same operator can both insert if concurrent.

    The app-level find_duplicate() does not protect against sub-millisecond
    races. This is accepted per design decision in 03-02: the compound unique
    index was removed to support soft-delete re-insertion and force=true use
    cases. The race window is sub-millisecond and acceptable for the target
    use case (manual, human-paced contest logging).
    """
    shared_time = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    qso1 = _make_qso("AA1AA", "W1AW", qso_date_utc=shared_time)
    qso2 = _make_qso("AA1AA", "W1AW", qso_date_utc=shared_time)

    # Both must succeed — no unique index blocks them
    await asyncio.gather(qso1.insert(), qso2.insert())

    count = await QSO.count()
    assert count == 2, (
        f"Expected 2 documents (race window accepted), got {count}"
    )
