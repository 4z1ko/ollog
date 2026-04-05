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

from app.adif.parser import parse_adi
from app.adif.serializer import serialize_adi
from app.auth.dependencies import get_current_operator_callsign
from app.qso.models import QSO
from app.qso.service import build_qso_dict, find_duplicate

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


_REQUIRED_FIELDS = {"CALL", "QSO_DATE", "TIME_ON", "BAND", "MODE"}
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


async def process_import(raw: bytes, operator: str) -> dict:
    """Core import logic shared between API and UI endpoints.

    Args:
        raw: Raw bytes of the uploaded ADIF file.
        operator: Callsign of the authenticated operator.

    Returns:
        Report dict with keys: total_records, accepted, duplicates, errors.
    """
    if len(raw) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 10 MB limit",
        )

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


@router.post("/import", response_model=ADIFImportReport)
async def import_adif(
    file: UploadFile,
    operator: str = Depends(get_current_operator_callsign),
):
    """Import an ADIF file and return a JSON import report.

    Accepts .adi or .adif files up to 10 MB.
    Returns a report with accepted, duplicate, and error lists.
    """
    raw = await file.read()
    return await process_import(raw, operator)


# ---------------------------------------------------------------------------
# ADIF export
# ---------------------------------------------------------------------------

# Fields that are internal to the application and must NOT appear in exported ADIF.
# operator_callsign and is_deleted are declared Beanie fields (not in model_extra)
# so they won't surface during model_extra iteration — but listed here as a safety net.
_SKIP_FIELDS = {"qso_date_utc", "_operator", "_deleted", "_id", "id", "revision_id"}


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
    operator: str = Depends(get_current_operator_callsign),
):
    """Stream the operator's logbook as a valid .adi file download.

    Filters: only the authenticated operator's non-deleted QSOs.
    Output: ADIF header + one serialized record per QSO.
    Memory: uses StreamingResponse with an async generator.
    """
    qsos = await QSO.find({"_operator": operator, "_deleted": False}).to_list()

    async def _generate():
        yield _ADIF_HEADER
        for qso in qsos:
            yield serialize_adi([_qso_to_adif_dict(qso)])

    filename = f"{operator}_logbook.adi"
    return StreamingResponse(
        _generate(),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
