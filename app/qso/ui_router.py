"""QSO entry UI router — browser-based QSO logging for operators.

Serves HTML pages and HTMX partial responses for the QSO entry form and log view.
All protected routes require cookie-based JWT auth.
Auth failures (401/403) are caught by the app-level exception handler
in main.py and redirected to /log/login.

Mounted at /log by app/main.py.
"""
import math
from datetime import datetime, timezone
from typing import Annotated, Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.adif.router import _qso_to_adif_dict, process_import
from app.adif.serializer import serialize_adi
from app.auth.dependencies import get_current_operator_callsign_cookie
from app.auth.models import User
from app.auth.service import create_access_token, verify_password
from app.qso.models import QSO
from app.qso.service import build_qso_dict, find_duplicate, get_qso_page, parse_adif_datetime

templates = Jinja2Templates(directory="templates")

ui_router = APIRouter(prefix="/log", tags=["log-ui"])


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

@ui_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render the operator login form."""
    return templates.TemplateResponse(
        request,
        "log/login.html",
        {"error": None},
    )


@ui_router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    """Process operator login form submission.

    Any enabled user (operator or admin) can log in here — no role restriction.
    On success: set HttpOnly JWT cookie and redirect to /log/.
    On failure: re-render login page with error message.
    """
    error = "Invalid credentials"

    user = await User.find_one({"username": username})
    if user is None or not user.enabled:
        return templates.TemplateResponse(
            request,
            "log/login.html",
            {"error": error},
            status_code=401,
        )

    if not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request,
            "log/login.html",
            {"error": error},
            status_code=401,
        )

    token = create_access_token(
        data={"sub": user.username, "callsign": user.callsign, "role": user.role}
    )

    response = RedirectResponse(url="/log/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
    )
    return response


@ui_router.get("/logout")
async def logout():
    """Clear the auth cookie and redirect to the login page."""
    response = RedirectResponse(url="/log/login", status_code=302)
    response.delete_cookie(key="access_token")
    return response


# ---------------------------------------------------------------------------
# QSO entry form
# ---------------------------------------------------------------------------

@ui_router.get("/", response_class=HTMLResponse)
async def form_page(
    request: Request,
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    """Render the main QSO entry form page."""
    return templates.TemplateResponse(
        request,
        "log/form.html",
        {"callsign": callsign},
    )


@ui_router.post("/qsos", response_class=HTMLResponse)
async def submit_qso(
    request: Request,
    CALL: Annotated[str, Form()],
    QSO_DATE: Annotated[str, Form()],
    TIME_ON: Annotated[str, Form()],
    BAND: Annotated[str, Form()],
    MODE: Annotated[str, Form()],
    FREQ: Annotated[str | None, Form()] = None,
    RST_SENT: Annotated[str | None, Form()] = None,
    RST_RCVD: Annotated[str | None, Form()] = None,
    force: bool = Query(False),
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    """Handle HTMX QSO form submission.

    Always returns HTTP 200 with an HTML partial — HTMX 2.x won't swap on 4xx.
    Duplicate found and not forced → return warning partial with "Save Anyway" button.
    No duplicate or force=True → insert QSO and return success partial.
    """
    form_data = {
        "CALL": CALL,
        "QSO_DATE": QSO_DATE,
        "TIME_ON": TIME_ON,
        "BAND": BAND,
        "MODE": MODE,
        "FREQ": FREQ,
        "RST_SENT": RST_SENT,
        "RST_RCVD": RST_RCVD,
    }

    qso_dict = build_qso_dict(
        {k: v for k, v in form_data.items() if v is not None},
        operator=callsign,
    )

    if not force:
        dup = await find_duplicate(
            operator=callsign,
            call=qso_dict["CALL"],
            band=qso_dict["BAND"],
            mode=qso_dict["MODE"],
            qso_date_utc=qso_dict["qso_date_utc"],
        )
        if dup is not None:
            # Return duplicate warning — HTTP 200 so HTMX swaps the content
            dup_dict = {
                "CALL": dup.CALL,
                "BAND": dup.BAND,
                "MODE": dup.MODE,
                "qso_date_utc": dup.qso_date_utc.isoformat() if dup.qso_date_utc else "",
            }
            return templates.TemplateResponse(
                request,
                "log/qso_result.html",
                {
                    "duplicate": dup_dict,
                    "success": None,
                    "qso": None,
                    # Pass original form values for "Save Anyway" hidden inputs
                    "form": form_data,
                },
            )

    # No duplicate or force=True: insert the QSO
    qso = QSO(**qso_dict)
    await qso.insert()

    qso_display = {
        "CALL": qso.CALL,
        "BAND": qso.BAND,
        "MODE": qso.MODE,
        "qso_date_utc": qso.qso_date_utc.isoformat() if qso.qso_date_utc else "",
    }

    return templates.TemplateResponse(
        request,
        "log/qso_result.html",
        {
            "duplicate": None,
            "success": True,
            "qso": qso_display,
            "form": None,
        },
    )


# ---------------------------------------------------------------------------
# Log view — paginated list with filtering, sorting, inline edit, soft-delete
# ---------------------------------------------------------------------------

def _qso_to_view_dict(qso: QSO) -> dict:
    """Convert a QSO Beanie document to a plain dict for Jinja2 templates.

    Extra fields (FREQ, RST_SENT, RST_RCVD, QSO_DATE, TIME_ON) live in
    model_extra on Beanie documents — extracting them here avoids Jinja2
    attribute-access issues with Pydantic model_extra.
    """
    d: dict = {
        "id": str(qso.id),
        "CALL": qso.CALL,
        "BAND": qso.BAND or "",
        "MODE": qso.MODE or "",
        "qso_date_utc": qso.qso_date_utc,
    }
    # Pull extra ADIF fields from model_extra (set via extra="allow")
    extra = qso.model_extra or {}
    d["FREQ"] = extra.get("FREQ", "")
    d["RST_SENT"] = extra.get("RST_SENT", "")
    d["RST_RCVD"] = extra.get("RST_RCVD", "")
    d["QSO_DATE"] = extra.get("QSO_DATE", "")
    d["TIME_ON"] = extra.get("TIME_ON", "")
    return d


@ui_router.get("/view", response_class=HTMLResponse)
async def log_view(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    call: Optional[str] = Query(None),
    band: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort: str = Query("-qso_date_utc"),
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    """Render the paginated QSO log view.

    Supports filtering by callsign, band, mode, and date range.
    Supports sorting by qso_date_utc, CALL, or BAND (prefix '-' for descending).
    HTMX requests (HX-Request header) return only the table partial.
    Full page requests return the complete log.html page.
    """
    # Parse optional date range strings (YYYYMMDD) to UTC-aware datetimes
    date_from_dt: Optional[datetime] = None
    date_to_dt: Optional[datetime] = None
    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, "%Y%m%d").replace(tzinfo=timezone.utc)
        except ValueError:
            date_from_dt = None
    if date_to:
        try:
            # End of day: use start of next day minus 1 second, or just midnight
            date_to_dt = datetime.strptime(date_to, "%Y%m%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
        except ValueError:
            date_to_dt = None

    qsos_raw, total = await get_qso_page(
        operator=callsign,
        page=page,
        page_size=page_size,
        callsign_filter=call or None,
        band_filter=band or None,
        mode_filter=mode or None,
        date_from=date_from_dt,
        date_to=date_to_dt,
        sort_by=sort,
    )

    qsos = [_qso_to_view_dict(q) for q in qsos_raw]
    total_pages = max(1, math.ceil(total / page_size))

    ctx = {
        "qsos": qsos,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "filters": {
            "call": call or "",
            "band": band or "",
            "mode": mode or "",
            "date_from": date_from or "",
            "date_to": date_to or "",
        },
        "sort": sort,
        "callsign": callsign,
    }

    # HTMX partial swap: return only the table, not the full page
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "log/log_table.html", ctx)

    return templates.TemplateResponse(request, "log/log.html", ctx)


@ui_router.get("/qsos/{qso_id}/edit", response_class=HTMLResponse)
async def qso_edit_row(
    request: Request,
    qso_id: str,
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    """Return the editable row partial for a QSO (HTMX outerHTML swap)."""
    try:
        oid = PydanticObjectId(qso_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    qso = await QSO.get(oid)
    if qso is None or qso.operator_callsign != callsign or qso.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    return templates.TemplateResponse(
        request,
        "log/qso_row_edit.html",
        {"qso": _qso_to_view_dict(qso)},
    )


@ui_router.get("/qsos/{qso_id}", response_class=HTMLResponse)
async def qso_view_row(
    request: Request,
    qso_id: str,
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    """Return the view-mode row partial for a QSO (used by Cancel button)."""
    try:
        oid = PydanticObjectId(qso_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    qso = await QSO.get(oid)
    if qso is None or qso.operator_callsign != callsign or qso.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    return templates.TemplateResponse(
        request,
        "log/qso_row.html",
        {"qso": _qso_to_view_dict(qso)},
    )


@ui_router.patch("/qsos/{qso_id}", response_class=HTMLResponse)
async def qso_update(
    request: Request,
    qso_id: str,
    CALL: Annotated[Optional[str], Form()] = None,
    QSO_DATE: Annotated[Optional[str], Form()] = None,
    TIME_ON: Annotated[Optional[str], Form()] = None,
    BAND: Annotated[Optional[str], Form()] = None,
    FREQ: Annotated[Optional[str], Form()] = None,
    MODE: Annotated[Optional[str], Form()] = None,
    RST_SENT: Annotated[Optional[str], Form()] = None,
    RST_RCVD: Annotated[Optional[str], Form()] = None,
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    """PATCH a QSO with form-encoded data from the inline edit row.

    Accepts all ADIF fields as optional form inputs (hx-include="closest tr" sends all).
    Recalculates qso_date_utc if QSO_DATE or TIME_ON changed.
    Returns the updated view-mode row partial.
    """
    try:
        oid = PydanticObjectId(qso_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    qso = await QSO.get(oid)
    if qso is None or qso.operator_callsign != callsign or qso.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    update_dict: dict = {}

    if CALL and CALL.strip():
        update_dict["CALL"] = CALL.strip().upper()
    if BAND and BAND.strip():
        update_dict["BAND"] = BAND.strip().upper()
    if MODE and MODE.strip():
        update_dict["MODE"] = MODE.strip().upper()
    if FREQ is not None and FREQ.strip():
        update_dict["FREQ"] = FREQ.strip()
    if RST_SENT is not None and RST_SENT.strip():
        update_dict["RST_SENT"] = RST_SENT.strip()
    if RST_RCVD is not None and RST_RCVD.strip():
        update_dict["RST_RCVD"] = RST_RCVD.strip()

    # Recalculate qso_date_utc if date or time changed
    date_changed = QSO_DATE and QSO_DATE.strip()
    time_changed = TIME_ON and TIME_ON.strip()
    if date_changed or time_changed:
        extra = qso.model_extra or {}
        existing_date = extra.get("QSO_DATE", "")
        existing_time = extra.get("TIME_ON", "")

        new_date = QSO_DATE.strip() if date_changed else existing_date
        new_time = TIME_ON.strip() if time_changed else existing_time

        if new_date and new_time:
            try:
                new_dt = parse_adif_datetime(new_date, new_time)
                update_dict["qso_date_utc"] = new_dt
            except ValueError:
                pass  # Keep existing datetime if parse fails

        if date_changed and new_date:
            update_dict["QSO_DATE"] = QSO_DATE.strip()
        if time_changed and new_time:
            update_dict["TIME_ON"] = TIME_ON.strip()

    # Strip any protected fields that might have snuck in via hx-include
    for protected in ("_operator", "_deleted", "operator_callsign", "is_deleted", "_id"):
        update_dict.pop(protected, None)

    if update_dict:
        await qso.update({"$set": update_dict})

    # Refetch to get the updated document
    updated = await QSO.get(oid)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    return templates.TemplateResponse(
        request,
        "log/qso_row.html",
        {"qso": _qso_to_view_dict(updated)},
    )


# ---------------------------------------------------------------------------
# ADIF import UI
# ---------------------------------------------------------------------------

@ui_router.get("/import", response_class=HTMLResponse)
async def import_page(
    request: Request,
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    """Render the ADIF import upload form."""
    return templates.TemplateResponse(
        request,
        "log/import.html",
        {"callsign": callsign},
    )


@ui_router.post("/import", response_class=HTMLResponse)
async def import_submit(
    request: Request,
    file: UploadFile,
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    """Process an uploaded ADIF file and return the import report partial.

    Always returns HTTP 200 — HTMX 2.x does not swap on 4xx.
    The report partial shows accepted, duplicate, and error counts/tables.
    """
    raw = await file.read()
    try:
        report = await process_import(raw, callsign)
    except HTTPException as exc:
        # Size limit exceeded — render a simple error message in the target div
        return HTMLResponse(
            content=f'<div class="error-msg">{exc.detail}</div>',
            status_code=200,
        )
    return templates.TemplateResponse(
        request,
        "log/import_report.html",
        {"report": report},
    )


@ui_router.get("/export")
async def export_logbook(
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    """Stream the operator's logbook as a .adi file download.

    Cookie-auth mirror of GET /api/adif/export (which uses Bearer auth).
    Identical filtering and serialization — only the auth dependency differs.
    """
    qsos = await QSO.find({"_operator": callsign, "_deleted": False}).to_list()

    _adif_header = "<ADIF_VER:5>3.1.4\n<PROGRAMID:5>ollog\n<EOH>\n\n"

    async def _generate():
        yield _adif_header
        for qso in qsos:
            yield serialize_adi([_qso_to_adif_dict(qso)])

    filename = f"{callsign}_logbook.adi"
    return StreamingResponse(
        _generate(),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@ui_router.delete("/qsos/{qso_id}", response_class=HTMLResponse)
async def qso_delete(
    request: Request,
    qso_id: str,
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    """Soft-delete a QSO. Returns empty 200 — HTMX outerHTML swap removes the row."""
    try:
        oid = PydanticObjectId(qso_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    qso = await QSO.get(oid)
    if qso is None or qso.operator_callsign != callsign or qso.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    await qso.update({"$set": {"_deleted": True}})
    return Response(content="", status_code=200)
