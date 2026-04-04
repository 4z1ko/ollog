"""Operator isolation audit and integration tests.

Tests:
  1. Route introspection: every QSO-related endpoint injects callsign from JWT.
  2. Cross-operator data isolation at the service/query layer.

Run:
    python -m pytest tests/test_operator_isolation.py -v
Requires (integration tests): MongoDB reachable at localhost:27017.
"""
import inspect
import socket
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from beanie import init_beanie
from fastapi.routing import APIRoute
from pymongo import AsyncMongoClient

from app.auth.dependencies import (
    get_current_operator_callsign,
    get_current_operator_callsign_cookie,
)
from app.main import app
from app.qso.models import QSO
from app.qso.service import find_duplicate, get_qso_page

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CALLSIGN_DEPS = {
    "get_current_operator_callsign",
    "get_current_operator_callsign_cookie",
}

QSO_PATH_PREFIXES = (
    "/api/qsos",
    "/log/qsos",
    "/log/view",
    "/log/import",
    "/log/export",
    "/api/adif",
)

# These paths do NOT need callsign injection — they handle login/logout
EXCLUDE_PATHS = {"/log/login", "/log/logout"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_dep_names(endpoint) -> set[str]:
    """Collect names of all callables injected via Depends() into an endpoint."""
    sig = inspect.signature(endpoint)
    dep_names: set[str] = set()
    for param in sig.parameters.values():
        default = param.default
        if hasattr(default, "dependency"):
            # FastAPI Depends() wrapper — recurse into the dependency itself
            dep = default.dependency
            if hasattr(dep, "__name__"):
                dep_names.add(dep.__name__)
            # Also inspect the dependency's own signature for chained Depends
            inner_dep_names = _collect_dep_names(dep)
            dep_names.update(inner_dep_names)
        elif callable(default) and hasattr(default, "__name__"):
            dep_names.add(default.__name__)
    return dep_names


def _mongo_available() -> bool:
    """Return True if MongoDB is reachable at localhost:27017."""
    try:
        s = socket.create_connection(("localhost", 27017), timeout=1)
        s.close()
        return True
    except OSError:
        return False


mongo_required = pytest.mark.skipif(
    not _mongo_available(),
    reason="MongoDB not available at localhost:27017",
)


# ---------------------------------------------------------------------------
# Local async fixture (independent of conftest.py's test_db)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def isolation_test_db():
    """Function-scoped test database for operator isolation tests.

    Skips if MongoDB is not reachable. Drops ollog_test and closes
    the connection on teardown.
    """
    if not _mongo_available():
        pytest.skip("MongoDB not available at localhost:27017")

    from app.auth.models import User

    client = AsyncMongoClient(
        "mongodb://localhost:27017/?directConnection=true",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_test"]
    await init_beanie(database=db, document_models=[QSO, User])
    yield db
    await client.drop_database("ollog_test")
    await client.aclose()


# ---------------------------------------------------------------------------
# Task 1: Route introspection audit
# ---------------------------------------------------------------------------

def test_all_qso_routes_inject_callsign_from_jwt():
    """Every QSO-related APIRoute must have a callsign dependency from JWT.

    Introspects app.routes at import time — no database required.
    Catches any future endpoint that forgets get_current_operator_callsign
    or get_current_operator_callsign_cookie.
    """
    flagged_routes: list[str] = []
    matched_routes: list[str] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        # Only check paths under QSO prefixes
        if not any(route.path.startswith(prefix) for prefix in QSO_PATH_PREFIXES):
            continue

        # Skip login/logout — they intentionally have no callsign injection
        if route.path in EXCLUDE_PATHS:
            continue

        matched_routes.append(route.path)

        dep_names = _collect_dep_names(route.endpoint)

        if not (dep_names & CALLSIGN_DEPS):
            flagged_routes.append(
                f"  MISSING callsign dep on {sorted(route.methods)} {route.path!r}"
                f" (found deps: {sorted(dep_names)})"
            )

    # Guard: ensure we actually matched routes (test doesn't silently pass)
    assert len(matched_routes) >= 8, (
        f"Expected at least 8 QSO-related routes, only matched {len(matched_routes)}: "
        f"{matched_routes}"
    )

    assert not flagged_routes, (
        "The following QSO-related routes are missing a callsign dependency:\n"
        + "\n".join(flagged_routes)
    )


# ---------------------------------------------------------------------------
# Task 2: Cross-operator data isolation integration tests
# ---------------------------------------------------------------------------

def _make_qso_doc(operator: str, call: str, **kwargs) -> QSO:
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
            "QSO_DATE": kwargs.get("QSO_DATE", "20240601"),
            "TIME_ON": kwargs.get("TIME_ON", "1200"),
        }
    )


@pytest.mark.asyncio
async def test_operator_cannot_see_other_operators_qsos(isolation_test_db):
    """QSO.find_active() must return only the queried operator's QSOs.

    Insert 3 QSOs for AA1AA and 3 for BB2BB; confirm each operator sees
    exactly their own records and none from the other.
    """
    aa_calls = ["W1AW", "W2AW", "W3AW"]
    bb_calls = ["K1TTT", "K2TTT", "K3TTT"]

    for i, call in enumerate(aa_calls):
        dt = datetime(2024, 6, 1, 12, i, 0, tzinfo=timezone.utc)
        await _make_qso_doc("AA1AA", call, qso_date_utc=dt).insert()

    for i, call in enumerate(bb_calls):
        dt = datetime(2024, 6, 2, 14, i, 0, tzinfo=timezone.utc)
        await _make_qso_doc("BB2BB", call, qso_date_utc=dt).insert()

    aa_results = await QSO.find_active("AA1AA")
    bb_results = await QSO.find_active("BB2BB")

    assert len(aa_results) == 3, (
        f"AA1AA expected 3 QSOs, got {len(aa_results)}"
    )
    assert len(bb_results) == 3, (
        f"BB2BB expected 3 QSOs, got {len(bb_results)}"
    )

    for qso in aa_results:
        assert qso.operator_callsign == "AA1AA", (
            f"AA1AA result has wrong operator: {qso.operator_callsign}"
        )
        assert qso.CALL in aa_calls, (
            f"AA1AA result contains unexpected CALL: {qso.CALL}"
        )

    for qso in bb_results:
        assert qso.operator_callsign == "BB2BB", (
            f"BB2BB result has wrong operator: {qso.operator_callsign}"
        )
        assert qso.CALL in bb_calls, (
            f"BB2BB result contains unexpected CALL: {qso.CALL}"
        )

    # Confirm no cross-contamination
    aa_call_set = {q.CALL for q in aa_results}
    bb_call_set = {q.CALL for q in bb_results}
    assert aa_call_set.isdisjoint(bb_call_set), (
        f"Cross-operator CALL contamination detected: {aa_call_set & bb_call_set}"
    )


@pytest.mark.asyncio
async def test_get_qso_page_returns_only_own_qsos(isolation_test_db):
    """get_qso_page() must return only QSOs belonging to the queried operator.

    Insert 5 QSOs for AA1AA and 5 for BB2BB; paginated query for each
    operator returns exactly 5 items, all with the correct operator callsign.
    """
    for i in range(5):
        dt = datetime(2024, 7, 1, 10, i, 0, tzinfo=timezone.utc)
        await _make_qso_doc("AA1AA", f"W{i+1}TEST", qso_date_utc=dt).insert()

    for i in range(5):
        dt = datetime(2024, 7, 2, 11, i, 0, tzinfo=timezone.utc)
        await _make_qso_doc("BB2BB", f"K{i+1}TEST", qso_date_utc=dt).insert()

    aa_items, aa_total = await get_qso_page("AA1AA", page_size=50)
    bb_items, bb_total = await get_qso_page("BB2BB", page_size=50)

    assert len(aa_items) == 5, (
        f"AA1AA page expected 5 items, got {len(aa_items)}"
    )
    assert aa_total == 5, f"AA1AA total expected 5, got {aa_total}"

    assert len(bb_items) == 5, (
        f"BB2BB page expected 5 items, got {len(bb_items)}"
    )
    assert bb_total == 5, f"BB2BB total expected 5, got {bb_total}"

    for qso in aa_items:
        assert qso.operator_callsign == "AA1AA", (
            f"AA1AA page item has wrong operator: {qso.operator_callsign}"
        )

    for qso in bb_items:
        assert qso.operator_callsign == "BB2BB", (
            f"BB2BB page item has wrong operator: {qso.operator_callsign}"
        )


@pytest.mark.asyncio
async def test_find_duplicate_scoped_to_operator(isolation_test_db):
    """find_duplicate() must only match within the queried operator's QSOs.

    AA1AA logs W1AW. BB2BB's duplicate check for the same contact returns None.
    AA1AA's own duplicate check returns the existing QSO.
    """
    ts = datetime(2024, 8, 15, 18, 30, 0, tzinfo=timezone.utc)

    # Insert a QSO for AA1AA
    await _make_qso_doc(
        "AA1AA", "W1AW",
        BAND="20M", MODE="SSB",
        qso_date_utc=ts,
    ).insert()

    # BB2BB checks for duplicates — must NOT see AA1AA's QSO
    dup_for_bb = await find_duplicate(
        operator="BB2BB",
        call="W1AW",
        band="20M",
        mode="SSB",
        qso_date_utc=ts,
    )
    assert dup_for_bb is None, (
        f"BB2BB should not find AA1AA's QSO as a duplicate, got: {dup_for_bb}"
    )

    # AA1AA checks for duplicates — MUST find their own QSO
    dup_for_aa = await find_duplicate(
        operator="AA1AA",
        call="W1AW",
        band="20M",
        mode="SSB",
        qso_date_utc=ts,
    )
    assert dup_for_aa is not None, (
        "AA1AA should find their own QSO as a duplicate, got None"
    )
    assert dup_for_aa.operator_callsign == "AA1AA"
    assert dup_for_aa.CALL == "W1AW"


@pytest.mark.asyncio
async def test_soft_deleted_qso_not_visible_to_any_operator(isolation_test_db):
    """Soft-deleted QSOs must not appear in find_active() or get_qso_page().

    Insert a QSO for AA1AA, soft-delete it, then confirm it is excluded from
    both find_active() and the paginated log view.
    """
    ts = datetime(2024, 9, 20, 8, 0, 0, tzinfo=timezone.utc)
    qso = _make_qso_doc("AA1AA", "VK2TDX", qso_date_utc=ts)
    await qso.insert()

    # Confirm it's visible before deletion
    before = await QSO.find_active("AA1AA")
    assert len(before) == 1, f"Expected 1 active QSO before delete, got {len(before)}"

    # Soft-delete via MongoDB $set (mirrors how routes delete)
    await qso.update({"$set": {"_deleted": True}})

    # find_active() must not return the deleted QSO
    after_active = await QSO.find_active("AA1AA")
    assert len(after_active) == 0, (
        f"Expected 0 active QSOs after soft-delete, got {len(after_active)}"
    )

    # get_qso_page() must not return the deleted QSO
    page_items, page_total = await get_qso_page("AA1AA", page_size=50)
    assert len(page_items) == 0, (
        f"Expected 0 items in page after soft-delete, got {len(page_items)}"
    )
    assert page_total == 0, (
        f"Expected total=0 after soft-delete, got {page_total}"
    )
