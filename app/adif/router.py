"""ADIF import/export router — POST /api/adif/import and GET /api/adif/export.

Provides synchronous per-record ADIF import with:
- 10 MB file size guard
- Required field validation (CALL, QSO_DATE, TIME_ON, BAND, MODE)
- Parse error passthrough from parse_adi
- Duplicate detection via find_duplicate() (+/-2 min fuzzy window)
- Per-record error accumulation (no silent drops)

Provides streaming ADIF export with:
- StreamingResponse for memory efficiency
- Operator isolation + soft-delete filter
- ADIF field mapping via _qso_to_adif_dict helper
- Internal fields (qso_date_utc) excluded from output
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from app.adif.serializer import serialize_adi
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.qso.collections import get_user_qso_collection
from app.qso.models import QSO
from app.qso.service import import_qsos_from_bytes, qso_from_mongo_doc

router = APIRouter(prefix="/api/adif", tags=["adif"])


class ADIFRecordAccepted(BaseModel):
    record_index: int
    call: str
    id: str


class ADIFRecordDuplicate(BaseModel):
    record_index: int
    call: str
    existing_id: str


class ADIFRecordError(BaseModel):
    record_index: int
    call: Optional[str] = None
    error: str


class ADIFImportReport(BaseModel):
    total_records: int
    accepted: list[ADIFRecordAccepted]
    duplicates: list[ADIFRecordDuplicate]
    errors: list[ADIFRecordError]


@router.post("/import", response_model=ADIFImportReport)
async def import_adif(
    file: UploadFile,
    user: User = Depends(get_current_user),
):
    """Import an ADIF file and return a JSON import report.

    Accepts .adi or .adif files up to 10 MB.
    Returns a report with accepted, duplicate, and error lists.
    """
    raw = await file.read()
    try:
        return await import_qsos_from_bytes(
            raw,
            user.callsign,
            collection=get_user_qso_collection(user),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# ADIF export
# ---------------------------------------------------------------------------

# Fields that are internal to the application and must NOT appear in exported ADIF.
# operator_callsign and is_deleted are declared Beanie fields (not in model_extra)
# so they won't surface during model_extra iteration — but listed here as a safety net.
_SKIP_FIELDS = {"qso_date_utc", "_operator", "_deleted", "_id", "id", "revision_id",
                "_created_at"}


def _qso_to_adif_dict(qso: QSO) -> dict:
    """Convert a QSO document to a flat ADIF field dict for serialization.

    Declared ADIF fields (CALL, BAND, MODE) are added explicitly.
    Extra fields from model_extra are included verbatim — this preserves
    APP_ prefixed fields, USERDEF fields, and other non-declared ADIF fields
    (QSO_DATE, TIME_ON, FREQ, RST_SENT, RST_RCVD, etc.).

    Internal fields (qso_date_utc, _operator, _deleted, id) are excluded.
    All values are coerced to strings for serializer compatibility.
    """
    d: dict = {}

    # Declared ADIF fields on the model
    if qso.CALL is not None:
        d["CALL"] = str(qso.CALL)
    if qso.BAND is not None:
        d["BAND"] = str(qso.BAND)
    if qso.MODE is not None:
        d["MODE"] = str(qso.MODE)

    # Extra fields stored verbatim in MongoDB (QSO_DATE, TIME_ON, FREQ, APP_*, etc.)
    for key, val in (qso.model_extra or {}).items():
        if key in _SKIP_FIELDS:
            continue
        if val is None:
            continue
        d[key] = str(val)

    return d


_ADIF_HEADER = "<ADIF_VER:5>3.1.4\n<PROGRAMID:5>ollog\n<EOH>\n\n"


@router.get(
    "/export",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/plain": {}},
            "description": "ADIF (.adi) file download containing the operator's full logbook.",
        }
    },
)
async def export_adif(
    user: User = Depends(get_current_user),
):
    """Stream the operator's logbook as a valid .adi file download.

    Filters: only the authenticated operator's non-deleted QSOs.
    Output: ADIF header + one serialized record per QSO.
    Memory: uses StreamingResponse with an async generator.
    """
    collection = get_user_qso_collection(user)
    docs = await collection.find({"_operator": user.callsign, "_deleted": False}).to_list()
    qsos = [qso for doc in docs if (qso := qso_from_mongo_doc(doc)) is not None]

    async def _generate():
        yield _ADIF_HEADER
        for qso in qsos:
            yield serialize_adi([_qso_to_adif_dict(qso)])

    filename = f"{user.callsign}_logbook.adi"
    return StreamingResponse(
        _generate(),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
