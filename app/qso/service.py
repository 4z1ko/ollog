"""QSO service layer — ADIF datetime parsing, QSO document construction, paginated queries."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

from app.qso.models import QSO

if TYPE_CHECKING:
    from app.auth.models import User

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = {"CALL", "QSO_DATE", "TIME_ON", "BAND", "MODE"}
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_DEFAULT_SORT = "-qso_date_utc"
_ALLOWED_SORT_FIELDS: frozenset[str] = frozenset({
    "-qso_date_utc", "qso_date_utc",
    "-CALL", "CALL",
    "-BAND", "BAND",
    "-MODE", "MODE",
    # MongoDB alias "_created_at" (not the Python attribute "created_at")
    "-_created_at", "_created_at",
})


def parse_adif_datetime(qso_date: str, time_on: str) -> datetime:
    """Parse ADIF QSO_DATE (YYYYMMDD) and TIME_ON (HHMM or HHMMSS) into a UTC-aware datetime.

    ADIF spec: QSO_DATE is always YYYYMMDD; TIME_ON is HHMM (4 chars) or HHMMSS (6 chars).
    All times are UTC per ADIF convention.
    """
    date_part = datetime.strptime(qso_date, "%Y%m%d").date()
    if len(time_on) == 4:
        time_part = datetime.strptime(time_on, "%H%M").time()
    elif len(time_on) == 6:
        time_part = datetime.strptime(time_on, "%H%M%S").time()
    else:
        raise ValueError(
            f"TIME_ON must be HHMM (4 chars) or HHMMSS (6 chars), got {len(time_on)!r} chars: {time_on!r}"
        )
    return datetime.combine(date_part, time_part, tzinfo=timezone.utc)


def build_qso_dict(body_dict: dict, operator: str, profile: Optional[User] = None) -> dict:
    """Build a QSO document dict from a merged ADIF field dict and operator callsign.

    Normalises BAND and MODE to uppercase (compound index consistency).
    Parses QSO_DATE + TIME_ON into qso_date_utc.
    Injects operator_callsign and is_deleted (Beanie serialises these to _operator/_deleted).
    Keeps QSO_DATE and TIME_ON in the dict for ADIF round-trip fidelity (Phase 4 export).

    When profile is provided, auto-stamps OPERATOR and optional profile fields (STAMP-01/02).
    When profile is None (ADIF import path), no profile-derived fields are injected (STAMP-03).
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

    # Auto-stamp profile-derived ADIF fields when a profile is provided (STAMP-01/02/03)
    if profile is not None:
        result["OPERATOR"] = profile.callsign
        if profile.station_callsign:
            result["STATION_CALLSIGN"] = profile.station_callsign
        if profile.my_gridsquare:
            result["MY_GRIDSQUARE"] = profile.my_gridsquare
        if profile.my_rig:
            result["MY_RIG"] = profile.my_rig
        if profile.my_antenna:
            result["MY_ANTENNA"] = profile.my_antenna
        if profile.tx_pwr is not None:
            result["TX_PWR"] = str(profile.tx_pwr)

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


async def ingest_qso_record(
    record: dict,
    operator: str,
    profile: Optional[User] = None,
    source: str = "unknown",
) -> dict:
    """Validate, duplicate-check, and insert one ADIF-style QSO record.

    Returns a small status dict instead of raising for expected validation
    outcomes so background ingestion sources can log and continue.
    """
    from app.qso.models import QSO as QSOModel

    missing = _REQUIRED_FIELDS - set(record)
    if missing:
        return {
            "status": "rejected",
            "reason": f"missing required field: {sorted(missing)[0]}",
        }

    try:
        qso_dict = build_qso_dict(record, operator, profile=profile)
    except (ValueError, KeyError) as exc:
        return {"status": "rejected", "reason": str(exc)}

    dup = await find_duplicate(
        operator=operator,
        call=qso_dict["CALL"],
        band=qso_dict["BAND"],
        mode=qso_dict["MODE"],
        qso_date_utc=qso_dict["qso_date_utc"],
    )
    if dup is not None:
        return {"status": "duplicate", "existing_id": str(dup.id)}

    qso = QSOModel(**qso_dict)
    await qso.insert()
    return {"status": "accepted", "id": str(qso.id), "source": source}


async def import_qsos_from_bytes(raw: bytes, operator: str) -> dict:
    """Core ADIF import logic — raises ValueError, never HTTPException.

    Callable from HTTP routes (via thin wrapper) AND async background tasks
    (UDP handler, CLI tools) where no HTTP context is available.

    Args:
        raw: Raw bytes of the uploaded ADIF file.
        operator: Callsign of the authenticated operator.

    Returns:
        Report dict with keys: total_records, accepted, duplicates, errors.

    Raises:
        ValueError: If raw exceeds 10 MB limit.
    """
    from app.adif.parser import parse_adi  # avoid circular import at module load

    if len(raw) > _MAX_BYTES:
        raise ValueError("File exceeds 10 MB limit")

    text = raw.decode("utf-8", errors="replace")
    records, parse_errors = parse_adi(text)

    accepted: list[dict] = []
    duplicates: list[dict] = []
    errors: list[dict] = list(parse_errors)

    for idx, record in enumerate(records):
        # Required field check
        if not (_REQUIRED_FIELDS <= set(record)):
            missing = sorted(_REQUIRED_FIELDS - set(record))
            errors.append({
                "record_index": idx,
                "call": record.get("CALL", "?"),
                "error": f"Missing required field(s): {', '.join(missing)}",
            })
            continue

        # Build QSO dict (validates/normalises fields)
        try:
            qso_dict = build_qso_dict(record, operator)
        except (ValueError, KeyError) as exc:
            errors.append({
                "record_index": idx,
                "call": record.get("CALL", "?"),
                "error": str(exc),
            })
            continue

        # Duplicate detection — same +/-2 min window as live QSO entry
        dup = await find_duplicate(
            operator=operator,
            call=qso_dict["CALL"],
            band=qso_dict["BAND"],
            mode=qso_dict["MODE"],
            qso_date_utc=qso_dict["qso_date_utc"],
        )
        if dup is not None:
            duplicates.append({
                "record_index": idx,
                "call": qso_dict["CALL"],
                "existing_id": str(dup.id),
            })
            continue

        # Insert accepted record
        qso = QSO(**qso_dict)
        await qso.insert()
        accepted.append({
            "record_index": idx,
            "call": qso_dict["CALL"],
            "id": str(qso.id),
        })

    return {
        "total_records": len(records),
        "accepted": accepted,
        "duplicates": duplicates,
        "errors": errors,
    }


async def get_qso_page(
    operator: str,
    page: int = 1,
    page_size: int = 50,
    callsign_filter: Optional[str] = None,
    band_filter: Optional[str] = None,
    mode_filter: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sort_by: str = _DEFAULT_SORT,
) -> tuple[list[QSO], int]:
    """Fetch a paginated, filtered page of active QSOs for an operator.

    Uses raw MongoDB field names (_operator, _deleted) for correct index hits.
    Does NOT use find_active() — that method returns a list, not a query builder.

    Returns (items, total) where total is the unfiltered count for pagination UI.
    """
    if sort_by not in _ALLOWED_SORT_FIELDS:
        logger.warning(
            "Invalid sort field '%s' for operator '%s', falling back to default",
            sort_by,
            operator,
        )
        sort_by = _DEFAULT_SORT
    query: dict = {"_operator": operator, "_deleted": False}

    if callsign_filter:
        query["CALL"] = {"$regex": re.escape(callsign_filter), "$options": "i"}
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


async def clear_operator_log(operator: str) -> int:
    """Permanently delete all active (non-soft-deleted) QSOs for an operator.

    Returns the count of deleted documents. Permanent delete (not soft-delete)
    per CLR-03 requirements — sets do not toggle `_deleted`; documents are
    removed entirely from MongoDB.

    Args:
        operator: The operator callsign (from JWT cookie / current user).

    Returns:
        Number of QSO documents removed. Zero is a valid, non-error return value
        (operator may legitimately have an empty log).
    """
    result = await QSO.find(
        {"_operator": operator, "_deleted": False}
    ).delete_many()
    return result.deleted_count if result is not None else 0
