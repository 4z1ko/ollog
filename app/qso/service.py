"""QSO service layer — ADIF datetime parsing, QSO document construction, paginated queries."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Optional

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.hashing import canonical_document_hash
from app.internal_logs.service import app_logger
from app.qso.models import QSO
from app.qso.custom_fields import apply_custom_field_normalization

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


def _transport_for_source(source: str) -> str:
    source_lower = source.lower()
    if source_lower.startswith("udp"):
        return "UDP"
    if source_lower.startswith("tcp"):
        return "TCP"
    if "bridge" in source_lower or "aclog" in source_lower:
        return "bridge"
    if "http" in source_lower or "api" in source_lower:
        return "HTTP"
    return "system"


def _qso_log_metadata(record: dict[str, Any], operator: str) -> dict[str, Any]:
    return {
        "operator": operator,
        "call": record.get("CALL"),
        "band": record.get("BAND"),
        "mode": record.get("MODE"),
        "qso_date": record.get("QSO_DATE"),
        "time_on": record.get("TIME_ON"),
    }


def _mongo_sort(sort_by: str) -> list[tuple[str, int]]:
    if sort_by.startswith("-"):
        return [(sort_by[1:], -1)]
    return [(sort_by, 1)]


@dataclass(frozen=True)
class QSOInsertResult:
    status: str
    qso: QSO | None = None
    existing: QSO | None = None


def qso_from_mongo_doc(doc: dict[str, Any] | None) -> QSO | None:
    """Hydrate a raw MongoDB document into the existing QSO view/model shape."""
    if doc is None:
        return None

    declared = {
        "id": doc.get("_id"),
        "operator_callsign": doc.get("_operator"),
        "CALL": doc.get("CALL"),
        "BAND": doc.get("BAND"),
        "MODE": doc.get("MODE"),
        "qso_date_utc": doc.get("qso_date_utc"),
        "is_deleted": doc.get("_deleted", False),
        "created_at": doc.get(
            "_created_at",
            QSO.model_fields["created_at"].default_factory(),
        ),
        "row_hash": doc.get("rowHash", ""),
    }
    extra = {
        key: value
        for key, value in doc.items()
        if key not in {
            "_id",
            "_operator",
            "CALL",
            "BAND",
            "MODE",
            "qso_date_utc",
            "_deleted",
            "_created_at",
            "rowHash",
        }
    }
    return QSO.model_construct(**declared, **extra)


def qso_to_mongo_doc(qso: QSO) -> dict[str, Any]:
    """Serialize a QSO shape into a raw MongoDB document."""
    doc = qso.model_dump(by_alias=True)
    if doc.get("_id") is None:
        doc["_id"] = ObjectId()
    return doc


def qso_from_input_dict(qso_dict: dict[str, Any]) -> QSO:
    """Build a QSO object without invoking Beanie's initialized collection hooks."""
    extras = {
        key: value
        for key, value in qso_dict.items()
        if key
        not in {
            "_id",
            "id",
            "_operator",
            "operator_callsign",
            "CALL",
            "BAND",
            "MODE",
            "qso_date_utc",
            "_deleted",
            "is_deleted",
            "_created_at",
            "created_at",
            "rowHash",
            "row_hash",
        }
    }
    qso = QSO.model_construct(
        id=qso_dict.get("_id") or qso_dict.get("id") or ObjectId(),
        operator_callsign=qso_dict.get("operator_callsign") or qso_dict.get("_operator"),
        CALL=qso_dict.get("CALL"),
        BAND=qso_dict.get("BAND"),
        MODE=qso_dict.get("MODE"),
        qso_date_utc=qso_dict.get("qso_date_utc"),
        is_deleted=qso_dict.get("is_deleted", qso_dict.get("_deleted", False)),
        created_at=qso_dict.get(
            "created_at",
            qso_dict.get("_created_at", QSO.model_fields["created_at"].default_factory()),
        ),
        row_hash=qso_dict.get("row_hash", qso_dict.get("rowHash", "")),
        **extras,
    )
    qso.refresh_row_hash()
    return qso


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
    result = apply_custom_field_normalization(result, profile)

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


async def insert_qso_dict(qso_dict: dict, collection: Any | None = None) -> QSOInsertResult:
    """Insert a QSO dict, returning explicit status for exact rowHash duplicates."""
    if collection is None:
        from app.qso.models import QSO as QSOModel

        qso = QSOModel(**qso_dict)
        try:
            await qso.insert()
        except DuplicateKeyError as exc:
            if "row_hash_unique_idx" not in str(exc) and "rowHash" not in str(exc):
                raise
            existing = await QSOModel.find_one({"rowHash": qso.row_hash})
            return QSOInsertResult(status="duplicate", existing=existing)
        from app.feed.manager import broadcast_qso

        await broadcast_qso(qso)
        return QSOInsertResult(status="inserted", qso=qso)

    qso = qso_from_input_dict(qso_dict)
    doc = qso_to_mongo_doc(qso)
    try:
        await collection.insert_one(doc)
    except DuplicateKeyError as exc:
        if "row_hash_unique_idx" not in str(exc) and "rowHash" not in str(exc):
            raise
        existing = qso_from_mongo_doc(await collection.find_one({"rowHash": qso.row_hash}))
        return QSOInsertResult(status="duplicate", existing=existing)
    from app.feed.manager import broadcast_qso

    await broadcast_qso(qso)
    return QSOInsertResult(status="inserted", qso=qso)


def row_hash_for_updated_qso(qso: QSO, updates: dict) -> str:
    """Compute the rowHash that a QSO would have after applying `$set` updates."""
    merged = qso.model_dump(by_alias=True)
    merged.update(updates)
    return canonical_document_hash(merged)


async def find_duplicate(
    operator: str,
    call: str,
    band: str,
    mode: str,
    qso_date_utc: datetime,
    collection: Any | None = None,
) -> QSO | None:
    """Find an existing non-deleted QSO matching CALL, BAND, MODE within +/-2 min.

    Returns the duplicate QSO if found, None otherwise.
    Only checks within the same operator's QSOs (operator isolation).
    """
    window_start = qso_date_utc - timedelta(minutes=2)
    window_end = qso_date_utc + timedelta(minutes=2)

    query = {
        "_operator": operator,
        "CALL": call,
        "BAND": band,
        "MODE": mode,
        "_deleted": False,
        "qso_date_utc": {"$gte": window_start, "$lte": window_end},
    }
    if collection is None:
        return await QSO.find_one(query)
    return qso_from_mongo_doc(await collection.find_one(query))


async def ingest_qso_record(
    record: dict,
    operator: str,
    profile: Optional[User] = None,
    source: str = "unknown",
    collection: Any | None = None,
) -> dict:
    """Validate, duplicate-check, and insert one ADIF-style QSO record.

    Returns a small status dict instead of raising for expected validation
    outcomes so background ingestion sources can log and continue.
    """
    missing = _REQUIRED_FIELDS - set(record)
    if missing:
        reason = f"missing required field: {sorted(missing)[0]}"
        await app_logger.warn(
            "QSO rejected during validation",
            source="app.qso.service",
            event_type="qso_validation_rejected",
            transport=_transport_for_source(source),
            metadata={
                **_qso_log_metadata(record, operator),
                "ingest_source": source,
                "reason": reason,
            },
        )
        return {
            "status": "rejected",
            "reason": reason,
        }

    try:
        qso_dict = build_qso_dict(record, operator, profile=profile)
    except (ValueError, KeyError) as exc:
        await app_logger.warn(
            "QSO rejected during validation",
            source="app.qso.service",
            event_type="qso_validation_rejected",
            transport=_transport_for_source(source),
            metadata={
                **_qso_log_metadata(record, operator),
                "ingest_source": source,
                "reason": str(exc),
            },
        )
        return {"status": "rejected", "reason": str(exc)}

    dup = await find_duplicate(
        operator=operator,
        call=qso_dict["CALL"],
        band=qso_dict["BAND"],
        mode=qso_dict["MODE"],
        qso_date_utc=qso_dict["qso_date_utc"],
        collection=collection,
    )
    if dup is not None:
        await app_logger.info(
            "QSO duplicate detected",
            source="app.qso.service",
            event_type="qso_duplicate",
            transport=_transport_for_source(source),
            qso_id=str(dup.id),
            metadata={
                **_qso_log_metadata(qso_dict, operator),
                "ingest_source": source,
                "existing_id": str(dup.id),
            },
        )
        return {"status": "duplicate", "existing_id": str(dup.id)}

    try:
        insert_result = await insert_qso_dict(qso_dict, collection=collection)
    except Exception as exc:
        await app_logger.error(
            "QSO insert failed",
            source="app.qso.service",
            event_type="qso_insert_failed",
            transport=_transport_for_source(source),
            metadata={
                **_qso_log_metadata(qso_dict, operator),
                "ingest_source": source,
            },
            exc=exc,
        )
        raise
    if insert_result.status == "duplicate":
        existing_id = str(insert_result.existing.id) if insert_result.existing else ""
        await app_logger.info(
            "QSO duplicate detected",
            source="app.qso.service",
            event_type="qso_duplicate",
            transport=_transport_for_source(source),
            qso_id=existing_id or None,
            metadata={
                **_qso_log_metadata(qso_dict, operator),
                "ingest_source": source,
                "existing_id": existing_id,
            },
        )
        return {
            "status": "duplicate",
            "existing_id": existing_id,
        }
    qso = insert_result.qso
    await app_logger.info(
        "QSO inserted",
        source="app.qso.service",
        event_type="qso_inserted",
        transport=_transport_for_source(source),
        qso_id=str(qso.id),
        metadata={
            **_qso_log_metadata(qso_dict, operator),
            "ingest_source": source,
        },
    )
    return {"status": "accepted", "id": str(qso.id), "source": source}


async def import_qsos_from_bytes(
    raw: bytes,
    operator: str,
    collection: Any | None = None,
    transport: str = "HTTP",
) -> dict:
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
            collection=collection,
        )
        if dup is not None:
            duplicates.append({
                "record_index": idx,
                "call": qso_dict["CALL"],
                "existing_id": str(dup.id),
                "record": record,
            })
            continue

        # Insert accepted record
        insert_result = await insert_qso_dict(qso_dict, collection=collection)
        if insert_result.status == "duplicate":
            duplicates.append({
                "record_index": idx,
                "call": qso_dict["CALL"],
                "existing_id": str(insert_result.existing.id) if insert_result.existing else "",
                "record": record,
            })
            continue

        qso = insert_result.qso
        accepted.append({
            "record_index": idx,
            "call": qso_dict["CALL"],
            "id": str(qso.id),
        })

    report = {
        "total_records": len(records),
        "accepted": accepted,
        "duplicates": duplicates,
        "errors": errors,
    }
    await app_logger.info(
        "QSO ADIF import completed",
        source="app.qso.service",
        event_type="qso_import_completed",
        transport=transport,
        metadata={
            "operator": operator,
            "total_records": report["total_records"],
            "accepted_count": len(accepted),
            "duplicate_count": len(duplicates),
            "error_count": len(errors),
        },
    )
    return report


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
    collection: Any | None = None,
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

    if collection is None:
        base = QSO.find(query)
        total = await base.count()
        items = await QSO.find(query).sort(sort_by).skip((page - 1) * page_size).limit(page_size).to_list()
        return items, total

    total = await collection.count_documents(query)
    docs = await (
        collection.find(query)
        .sort(_mongo_sort(sort_by))
        .skip((page - 1) * page_size)
        .limit(page_size)
        .to_list(length=page_size)
    )
    items = [qso for doc in docs if (qso := qso_from_mongo_doc(doc)) is not None]
    return items, total


async def get_qso_by_id(qso_id: Any, collection: Any) -> QSO | None:
    """Fetch one QSO from a raw per-user collection by ObjectId."""
    return qso_from_mongo_doc(await collection.find_one({"_id": qso_id}))


async def update_qso_fields(qso: QSO, updates: dict[str, Any], collection: Any) -> QSO:
    """Apply a raw $set update to a QSO in a per-user collection."""
    set_doc = dict(updates)
    set_doc["rowHash"] = row_hash_for_updated_qso(qso, set_doc)
    await collection.update_one({"_id": qso.id}, {"$set": set_doc})
    updated = await get_qso_by_id(qso.id, collection)
    if updated is None:
        raise RuntimeError("QSO disappeared during update")
    return updated


async def soft_delete_qso(qso: QSO, collection: Any) -> None:
    """Soft-delete a QSO in a per-user collection and refresh rowHash."""
    row_hash = row_hash_for_updated_qso(qso, {"_deleted": True})
    await collection.update_one(
        {"_id": qso.id},
        {"$set": {"_deleted": True, "rowHash": row_hash}},
    )


async def clear_operator_log(operator: str, collection: Any | None = None) -> int:
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
    query = {"_operator": operator, "_deleted": False}
    if collection is None:
        result = await QSO.find(query).delete_many()
    else:
        result = await collection.delete_many(query)
    return result.deleted_count if result is not None else 0
