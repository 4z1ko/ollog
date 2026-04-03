"""QSO service layer — ADIF datetime parsing, QSO document construction, paginated queries."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.qso.models import QSO


def parse_adif_datetime(qso_date: str, time_on: str) -> datetime:
    """Parse ADIF QSO_DATE (YYYYMMDD) and TIME_ON (HHMM or HHMMSS) into a UTC-aware datetime.

    ADIF spec: QSO_DATE is always YYYYMMDD; TIME_ON is HHMM (4 chars) or HHMMSS (6 chars).
    All times are UTC per ADIF convention.
    """
    date_part = datetime.strptime(qso_date, "%Y%m%d").date()
    if len(time_on) == 4:
        time_part = datetime.strptime(time_on, "%H%M").time()
    else:
        time_part = datetime.strptime(time_on, "%H%M%S").time()
    return datetime.combine(date_part, time_part, tzinfo=timezone.utc)


def build_qso_dict(body_dict: dict, operator: str) -> dict:
    """Build a QSO document dict from a merged ADIF field dict and operator callsign.

    Normalises BAND and MODE to uppercase (compound index consistency).
    Parses QSO_DATE + TIME_ON into qso_date_utc.
    Injects operator_callsign and is_deleted (Beanie serialises these to _operator/_deleted).
    Keeps QSO_DATE and TIME_ON in the dict for ADIF round-trip fidelity (Phase 4 export).
    """
    result = dict(body_dict)

    # Normalise BAND and MODE to uppercase
    if "BAND" in result and result["BAND"] is not None:
        result["BAND"] = result["BAND"].upper()
    if "MODE" in result and result["MODE"] is not None:
        result["MODE"] = result["MODE"].upper()

    # Parse ADIF date/time into UTC-aware datetime
    result["qso_date_utc"] = parse_adif_datetime(result["QSO_DATE"], result["TIME_ON"])

    # Inject operator callsign (Beanie serialises to _operator via serialization_alias)
    result["operator_callsign"] = operator

    # Set soft-delete flag (Beanie serialises to _deleted via serialization_alias)
    result["is_deleted"] = False

    return result


async def find_duplicate(
    operator: str,
    call: str,
    band: str,
    mode: str,
    qso_date_utc: datetime,
) -> QSO | None:
    """Find an existing non-deleted QSO matching CALL, BAND, MODE within +/-2 min.

    Returns the duplicate QSO if found, None otherwise.
    Only checks within the same operator's QSOs (operator isolation).
    """
    window_start = qso_date_utc - timedelta(minutes=2)
    window_end = qso_date_utc + timedelta(minutes=2)

    return await QSO.find_one({
        "_operator": operator,
        "CALL": call,
        "BAND": band,
        "MODE": mode,
        "_deleted": False,
        "qso_date_utc": {"$gte": window_start, "$lte": window_end},
    })


async def get_qso_page(
    operator: str,
    page: int = 1,
    page_size: int = 50,
    callsign_filter: Optional[str] = None,
    band_filter: Optional[str] = None,
    mode_filter: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sort_by: str = "-qso_date_utc",
) -> tuple[list[QSO], int]:
    """Fetch a paginated, filtered page of active QSOs for an operator.

    Uses raw MongoDB field names (_operator, _deleted) for correct index hits.
    Does NOT use find_active() — that method returns a list, not a query builder.

    Returns (items, total) where total is the unfiltered count for pagination UI.
    """
    query: dict = {"_operator": operator, "_deleted": False}

    if callsign_filter:
        query["CALL"] = {"$regex": callsign_filter, "$options": "i"}
    if band_filter:
        query["BAND"] = band_filter
    if mode_filter:
        query["MODE"] = mode_filter
    if date_from or date_to:
        date_query: dict = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        query["qso_date_utc"] = date_query

    base = QSO.find(query)
    total = await base.count()
    items = await QSO.find(query).sort(sort_by).skip((page - 1) * page_size).limit(page_size).to_list()
    return items, total
