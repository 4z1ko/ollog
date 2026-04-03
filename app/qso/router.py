"""QSO REST API router — POST, GET (list + by-id), PATCH, DELETE endpoints.

All endpoints require Bearer JWT auth via get_current_operator_callsign.
Callsign is NEVER accepted from request body — always injected from JWT.

Extra ADIF fields beyond required set are accepted and stored (extra="allow")
so Phase 4 batch import can POST ADIF field dicts directly through this endpoint.
"""
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict

from app.auth.dependencies import get_current_operator_callsign
from app.qso.models import QSO
from app.qso.service import build_qso_dict, get_qso_page, parse_adif_datetime

router = APIRouter(prefix="/api/qsos", tags=["qsos"])


class QSOCreateRequest(BaseModel):
    """Request model for QSO creation. extra='allow' captures arbitrary ADIF fields for Phase 4."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    CALL: str
    QSO_DATE: str
    TIME_ON: str
    BAND: str
    MODE: str
    FREQ: Optional[str] = None
    RST_SENT: Optional[str] = None
    RST_RCVD: Optional[str] = None


def _qso_to_dict(qso: QSO) -> dict:
    """Serialise a QSO document to a response dict with string id."""
    d = qso.model_dump(by_alias=True)
    d["id"] = str(qso.id)
    # Ensure qso_date_utc is serialised as ISO string if present
    if d.get("qso_date_utc") is not None:
        dt = d["qso_date_utc"]
        if hasattr(dt, "isoformat"):
            d["qso_date_utc"] = dt.isoformat()
    return d


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_qso(
    body: QSOCreateRequest,
    force: bool = Query(False),  # duplicate override — wired in 03-02, ignored here
    operator: str = Depends(get_current_operator_callsign),
) -> dict:
    """Create a new QSO for the authenticated operator.

    Callsign is injected from JWT — not accepted from request body.
    BAND and MODE are uppercased on ingest for compound index consistency.
    Extra ADIF fields beyond the declared set are accepted and stored.
    """
    # Merge declared fields and extra ADIF fields
    merged: dict = {**body.model_dump(exclude_unset=False), **(body.model_extra or {})}
    qso_dict = build_qso_dict(merged, operator)
    qso = QSO(**qso_dict)
    await qso.insert()
    return _qso_to_dict(qso)


@router.get("/", status_code=status.HTTP_200_OK)
async def list_qsos(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    call: Optional[str] = Query(None),
    band: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, description="YYYYMMDD"),
    date_to: Optional[str] = Query(None, description="YYYYMMDD"),
    sort: str = Query("-qso_date_utc"),
    operator: str = Depends(get_current_operator_callsign),
) -> dict:
    """List the authenticated operator's active QSOs with pagination and optional filters."""
    from datetime import timezone as tz

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
    )
    return {
        "items": [_qso_to_dict(q) for q in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{qso_id}", status_code=status.HTTP_200_OK)
async def get_qso(
    qso_id: str,
    operator: str = Depends(get_current_operator_callsign),
) -> dict:
    """Fetch a single QSO by ID. Returns 404 if not found, not owned, or soft-deleted."""
    try:
        oid = ObjectId(qso_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    qso = await QSO.get(oid)
    if qso is None or qso.operator_callsign != operator or qso.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")
    return _qso_to_dict(qso)


@router.patch("/{qso_id}", status_code=status.HTTP_200_OK)
async def patch_qso(
    qso_id: str,
    body: Dict[str, Any],
    operator: str = Depends(get_current_operator_callsign),
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

    qso = await QSO.get(oid)
    if qso is None or qso.operator_callsign != operator or qso.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    # Strip protected / immutable fields
    for protected in ("_operator", "operator_callsign", "_deleted", "is_deleted", "_id"):
        body.pop(protected, None)

    # Normalise BAND/MODE to uppercase
    if "BAND" in body and body["BAND"] is not None:
        body["BAND"] = body["BAND"].upper()
    if "MODE" in body and body["MODE"] is not None:
        body["MODE"] = body["MODE"].upper()

    # Recalculate qso_date_utc if either ADIF time field changed
    if "QSO_DATE" in body or "TIME_ON" in body:
        new_date = body.get("QSO_DATE") or qso.model_dump(by_alias=False).get("QSO_DATE")
        new_time = body.get("TIME_ON") or qso.model_dump(by_alias=False).get("TIME_ON")
        if new_date and new_time:
            body["qso_date_utc"] = parse_adif_datetime(new_date, new_time)

    if body:
        await qso.update({"$set": body})

    updated = await QSO.get(oid)
    return _qso_to_dict(updated)


@router.delete("/{qso_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_qso(
    qso_id: str,
    operator: str = Depends(get_current_operator_callsign),
) -> None:
    """Soft-delete a QSO by setting _deleted: true in MongoDB.

    Returns 204 No Content on success. Returns 404 if not found, not owned,
    or already deleted. Uses MongoDB alias _deleted (not Python attribute is_deleted).
    """
    try:
        oid = ObjectId(qso_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    qso = await QSO.get(oid)
    if qso is None or qso.operator_callsign != operator or qso.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    # Use MongoDB alias _deleted, not Python attribute is_deleted
    await qso.update({"$set": {"_deleted": True}})
