"""ADIF import router — POST /api/adif/import endpoint.

Provides synchronous per-record ADIF import with:
- 10 MB file size guard
- Required field validation (CALL, QSO_DATE, TIME_ON, BAND, MODE)
- Parse error passthrough from parse_adi
- Duplicate detection via find_duplicate() (+/-2 min fuzzy window)
- Per-record error accumulation (no silent drops)
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.adif.parser import parse_adi
from app.auth.dependencies import get_current_operator_callsign
from app.qso.models import QSO
from app.qso.service import build_qso_dict, find_duplicate

router = APIRouter(prefix="/api/adif", tags=["adif"])

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


@router.post("/import")
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
