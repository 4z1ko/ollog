"""QSO REST API router — POST, GET (list + by-id), PATCH, DELETE endpoints.

All endpoints require Bearer JWT auth via get_current_operator_callsign.
Callsign is NEVER accepted from request body — always injected from JWT.

Extra ADIF fields beyond required set are accepted and stored (extra="allow")
so Phase 4 batch import can POST ADIF field dicts directly through this endpoint.
"""
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.auth.dependencies import get_current_user_jwt_or_apikey
from app.auth.models import User
from app.internal_logs.service import app_logger
from app.qso.collections import get_user_qso_collection
from app.qso.models import QSO
from app.qso.service import (
    build_qso_dict,
    find_duplicate,
    get_qso_by_id,
    get_qso_page,
    insert_qso_dict,
    parse_adif_datetime,
    qso_from_mongo_doc,
    row_hash_for_updated_qso,
    soft_delete_qso,
    update_qso_fields,
)
from app.qso.custom_fields import apply_custom_field_normalization

router = APIRouter(prefix="/api/qsos", tags=["qsos"])


class QSOResponse(BaseModel):
    """Response model for a single QSO. Declares stable fields; extra ADIF fields are silently dropped."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str
    CALL: str
    BAND: Optional[str] = None
    MODE: Optional[str] = None
    qso_date_utc: Optional[str] = None
    operator_callsign: Optional[str] = Field(None, alias="_operator")
    is_deleted: Optional[bool] = Field(None, alias="_deleted")
    FREQ: Optional[str] = None
    RST_SENT: Optional[str] = None
    RST_RCVD: Optional[str] = None


class QSOListResponse(BaseModel):
    """Paginated list of QSOs."""

    items: list[QSOResponse]
    total: int
    page: int
    page_size: int


class DuplicateQSOError(BaseModel):
    """Response schema for 409 Conflict when a duplicate QSO is detected."""

    duplicate: bool
    existing_id: str
    existing_call: str
    existing_band: str
    existing_mode: str
    existing_date: Optional[str] = None


class QSOCreateRequest(BaseModel):
    """Request model for QSO creation. extra='allow' captures arbitrary ADIF fields.

    OPERATOR and STATION_CALLSIGN are auto-stamped from the authenticated user's
    profile — do not include them in the request body. OPERATOR identifies the
    person at the key; STATION_CALLSIGN identifies the station's licensed callsign.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    CALL: str = Field(description="Callsign of the contacted station (e.g. W1AW)")
    QSO_DATE: str = Field(description="UTC date of QSO in YYYYMMDD format (e.g. 20240115)")
    TIME_ON: str = Field(description="UTC start time in HHMM or HHMMSS format (e.g. 1430 or 143045)")
    BAND: str = Field(description="Amateur band designator (e.g. 40m, 20m, 2m)")
    MODE: str = Field(description="Operating mode per ADIF spec (e.g. SSB, CW, FT8, FM)")
    FREQ: Optional[str] = Field(None, description="Frequency in MHz (e.g. 14.225)")
    RST_SENT: Optional[str] = Field(None, description="RST signal report sent to contacted station")
    RST_RCVD: Optional[str] = Field(None, description="RST signal report received from contacted station")


def _qso_to_dict(qso: QSO) -> dict:
    """Serialise a QSO document to a fully JSON-serialisable response dict.

    model_dump(by_alias=True) may return PydanticObjectId and datetime objects
    that FastAPI cannot serialise directly. This function converts them to
    standard Python types (str and ISO string respectively).
    """
    d = qso.model_dump(by_alias=True)
    # Convert _id (PydanticObjectId) to string "id" key for API consumers
    d["id"] = str(qso.id)
    # Remove the raw _id key to avoid duplicate / non-serialisable values
    d.pop("_id", None)
    d.pop("_created_at", None)      # D-06: internal field, not for API consumers
    # Convert qso_date_utc datetime to ISO string
    if d.get("qso_date_utc") is not None:
        dt = d["qso_date_utc"]
        if hasattr(dt, "isoformat"):
            d["qso_date_utc"] = dt.isoformat()
    return d


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=QSOResponse,
    responses={
        409: {
            "model": DuplicateQSOError,
            "description": "Duplicate QSO detected within +/-2 min window. Use force=true to override.",
        }
    },
)
async def create_qso(
    body: QSOCreateRequest,
    force: bool = Query(False, description="Override duplicate detection and force insert"),
    user: User = Depends(get_current_user_jwt_or_apikey),
) -> dict:
    """Create a new QSO for the authenticated operator.

    Callsign is injected from JWT — not accepted from request body.
    BAND and MODE are uppercased on ingest for compound index consistency.
    Extra ADIF fields beyond the declared set are accepted and stored.
    Profile fields (OPERATOR, STATION_CALLSIGN, etc.) are auto-stamped from the User document.
    """
    operator = user.callsign
    collection = get_user_qso_collection(user)
    # Merge declared fields and extra ADIF fields
    merged: dict = {**body.model_dump(exclude_unset=False), **(body.model_extra or {})}
    await app_logger.info(
        "HTTP API QSO received",
        source="app.qso.router",
        event_type="qso_http_received",
        transport="HTTP",
        metadata={
            "operator": operator,
            "call": merged.get("CALL"),
            "band": merged.get("BAND"),
            "mode": merged.get("MODE"),
            "force": force,
        },
    )
    qso_dict = build_qso_dict(merged, operator, profile=user)

    # Duplicate detection — skip only when force=True
    if not force:
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
                "HTTP API QSO duplicate detected",
                source="app.qso.router",
                event_type="qso_duplicate",
                transport="HTTP",
                qso_id=str(dup.id),
                metadata={
                    "operator": operator,
                    "call": qso_dict["CALL"],
                    "band": qso_dict["BAND"],
                    "mode": qso_dict["MODE"],
                    "existing_id": str(dup.id),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "duplicate": True,
                    "existing_id": str(dup.id),
                    "existing_call": dup.CALL,
                    "existing_band": dup.BAND,
                    "existing_mode": dup.MODE,
                    "existing_date": dup.qso_date_utc.isoformat() if dup.qso_date_utc else None,
                },
            )

    insert_result = await insert_qso_dict(qso_dict, collection=collection)
    if insert_result.status == "duplicate":
        existing = insert_result.existing
        await app_logger.info(
            "HTTP API QSO duplicate detected",
            source="app.qso.router",
            event_type="qso_duplicate",
            transport="HTTP",
            qso_id=str(existing.id) if existing else None,
            metadata={
                "operator": operator,
                "call": qso_dict["CALL"],
                "band": qso_dict["BAND"],
                "mode": qso_dict["MODE"],
                "existing_id": str(existing.id) if existing else "",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "duplicate": True,
                "existing_id": str(existing.id) if existing else "",
                "existing_call": existing.CALL if existing else qso_dict["CALL"],
                "existing_band": existing.BAND if existing else qso_dict["BAND"],
                "existing_mode": existing.MODE if existing else qso_dict["MODE"],
                "existing_date": existing.qso_date_utc.isoformat()
                if existing and existing.qso_date_utc else None,
            },
        )
    qso = insert_result.qso
    await app_logger.info(
        "HTTP API QSO inserted",
        source="app.qso.router",
        event_type="qso_inserted",
        transport="HTTP",
        qso_id=str(qso.id),
        metadata={
            "operator": operator,
            "call": qso_dict["CALL"],
            "band": qso_dict["BAND"],
            "mode": qso_dict["MODE"],
            "force": force,
        },
    )
    return _qso_to_dict(qso)


@router.get("/", status_code=status.HTTP_200_OK, response_model=QSOListResponse)
async def list_qsos(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    call: Optional[str] = Query(None),
    band: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYYMMDD"),
    date_to: Optional[str] = Query(None, description="YYYYMMDD"),
    sort: str = Query("-qso_date_utc"),
    user: User = Depends(get_current_user_jwt_or_apikey),
) -> dict:
    """List the authenticated operator's active QSOs with pagination and optional filters."""
    operator = user.callsign
    collection = get_user_qso_collection(user)
    dt_from = None
    dt_to = None
    if date_from:
        dt_from = parse_adif_datetime(date_from, "0000")
    if date_to:
        # End-of-day for date_to: use 2359 (23:59) so the full day is included
        dt_to = parse_adif_datetime(date_to, "2359")

    items, total = await get_qso_page(
        operator=operator,
        page=page,
        page_size=page_size,
        callsign_filter=call,
        band_filter=band,
        mode_filter=mode,
        date_from=dt_from,
        date_to=dt_to,
        sort_by=sort,
        collection=collection,
    )
    return {
        "items": [_qso_to_dict(q) for q in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{qso_id}", status_code=status.HTTP_200_OK, response_model=QSOResponse)
async def get_qso(
    qso_id: str,
    user: User = Depends(get_current_user_jwt_or_apikey),
) -> dict:
    """Fetch a single QSO by ID. Returns 404 if not found, not owned, or soft-deleted."""
    try:
        oid = ObjectId(qso_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    collection = get_user_qso_collection(user)
    qso = await get_qso_by_id(oid, collection)
    if qso is None or qso.operator_callsign != user.callsign or qso.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")
    return _qso_to_dict(qso)


@router.patch("/{qso_id}", status_code=status.HTTP_200_OK, response_model=QSOResponse)
async def patch_qso(
    qso_id: str,
    body: Dict[str, Any],
    user: User = Depends(get_current_user_jwt_or_apikey),
) -> dict:
    """Partially update a QSO using raw $set for ADIF field compatibility.

    Protected fields (_operator, _deleted, _id) are stripped before update.
    BAND and MODE are uppercased if present. qso_date_utc is recalculated
    if QSO_DATE or TIME_ON changes.
    """
    try:
        oid = ObjectId(qso_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    collection = get_user_qso_collection(user)
    qso = await get_qso_by_id(oid, collection)
    if qso is None or qso.operator_callsign != user.callsign or qso.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    # Strip protected / immutable fields
    for protected in ("_operator", "operator_callsign", "_deleted", "is_deleted", "_id",
                      "_created_at", "created_at", "rowHash", "row_hash"):
        body.pop(protected, None)

    # Normalise BAND/MODE to uppercase
    if "BAND" in body and body["BAND"] is not None:
        body["BAND"] = body["BAND"].upper()
    if "MODE" in body and body["MODE"] is not None:
        body["MODE"] = body["MODE"].upper()

    body = apply_custom_field_normalization(body, user)

    # Recalculate qso_date_utc if either ADIF time field changed
    if "QSO_DATE" in body or "TIME_ON" in body:
        new_date = body.get("QSO_DATE") or qso.model_dump(by_alias=False).get("QSO_DATE")
        new_time = body.get("TIME_ON") or qso.model_dump(by_alias=False).get("TIME_ON")
        if new_date and new_time:
            body["qso_date_utc"] = parse_adif_datetime(new_date, new_time)

    if body:
        body["rowHash"] = row_hash_for_updated_qso(qso, body)
        try:
            updated_qso = await update_qso_fields(qso, body, collection)
        except Exception as exc:
            if "row_hash_unique_idx" not in str(exc) and "rowHash" not in str(exc):
                await app_logger.error(
                    "HTTP API QSO update failed",
                    source="app.qso.router",
                    event_type="qso_update_failed",
                    transport="HTTP",
                    qso_id=str(qso.id),
                    metadata={"operator": user.callsign, "updated_fields": sorted(body)},
                    exc=exc,
                )
                raise
            existing = await get_qso_by_id(qso.id, collection)
            duplicate = await collection.find_one({"rowHash": body["rowHash"]})
            if duplicate is not None:
                existing = qso_from_mongo_doc(duplicate)
            await app_logger.info(
                "HTTP API QSO update duplicate detected",
                source="app.qso.router",
                event_type="qso_update_duplicate",
                transport="HTTP",
                qso_id=str(existing.id) if existing else str(qso.id),
                metadata={"operator": user.callsign, "updated_fields": sorted(body)},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "duplicate": True,
                    "existing_id": str(existing.id) if existing else "",
                    "existing_call": existing.CALL if existing else body.get("CALL", qso.CALL),
                    "existing_band": existing.BAND if existing else body.get("BAND", qso.BAND),
                    "existing_mode": existing.MODE if existing else body.get("MODE", qso.MODE),
                    "existing_date": existing.qso_date_utc.isoformat()
                    if existing and existing.qso_date_utc else None,
                },
            )
        await app_logger.info(
            "HTTP API QSO updated",
            source="app.qso.router",
            event_type="qso_updated",
            transport="HTTP",
            qso_id=str(updated_qso.id),
            metadata={"operator": user.callsign, "updated_fields": sorted(body)},
        )

    updated = await get_qso_by_id(oid, collection)
    return _qso_to_dict(updated)


@router.delete("/{qso_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_qso(
    qso_id: str,
    user: User = Depends(get_current_user_jwt_or_apikey),
) -> None:
    """Soft-delete a QSO by ID.

    The record is marked as deleted in MongoDB — it is NOT physically removed.
    Soft-deleted QSOs are excluded from all list, get, and export operations.
    To permanently remove data, direct database access is required.

    Returns 204 No Content on success. Returns 404 if not found, not owned,
    or already deleted.
    """
    try:
        oid = ObjectId(qso_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    collection = get_user_qso_collection(user)
    qso = await get_qso_by_id(oid, collection)
    if qso is None or qso.operator_callsign != user.callsign or qso.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    await soft_delete_qso(qso, collection)
    await app_logger.info(
        "HTTP API QSO soft deleted",
        source="app.qso.router",
        event_type="qso_deleted",
        transport="HTTP",
        qso_id=str(qso.id),
        metadata={"operator": user.callsign, "call": qso.CALL},
    )
