"""QSO entry UI router — browser-based QSO logging for operators.

Serves HTML pages and HTMX partial responses for the QSO entry form and log view.
All protected routes require cookie-based JWT auth.
Auth failures (401/403) are caught by the app-level exception handler
in main.py and redirected to /log/login.

Mounted at /log by app/main.py.
"""
import base64
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from pydantic import ValidationError

from app.adif.router import _qso_to_adif_dict
from app.qso.service import import_qsos_from_bytes
from app.callsign.prefixes import lookup_prefix
import pycountry
from app.adif.serializer import serialize_adi
from app.auth.dependencies import get_current_operator_callsign_cookie, get_current_user_cookie
from app.auth.models import User
from app.auth.service import create_access_token, verify_password
from app.profile.schemas import ProfileUpdateRequest
from app.profile.service import update_profile
from app.qso.fields import (
    build_field_values,
    get_configurable_column_keys_for_user,
    get_default_column_keys_for_user,
    get_field_catalog_for_user,
)
from app.qso.custom_fields import (
    custom_field_defaults,
    custom_fields_for_user,
    enabled_custom_fields_for_user,
)
from app.qso.models import QSO
from app.qso.service import (
    build_qso_dict,
    clear_operator_log,
    find_duplicate,
    get_qso_page,
    insert_qso_dict,
    parse_adif_datetime,
    row_hash_for_updated_qso,
)
from app.tokens.models import ApiToken
from app.tokens.service import generate_api_token, hash_api_token, validate_token_name

templates = Jinja2Templates(directory="templates")

ui_router = APIRouter(prefix="/log", tags=["log-ui"])


def _encode_import_record(record: dict) -> str:
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def _decode_import_record(token: str) -> dict:
    payload = base64.urlsafe_b64decode(token.encode("ascii"))
    record = json.loads(payload.decode("utf-8"))
    if not isinstance(record, dict):
        raise ValueError("Invalid duplicate record payload")
    return record


def _custom_qso_values_from_form(form, user: User, include_empty: bool = False) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in enabled_custom_fields_for_user(user):
        if field.adif_name not in form:
            continue
        value = str(form.get(field.adif_name, "")).strip()
        if not include_empty and not value:
            continue
        values[field.adif_name] = value.upper() if field.force_uppercase else value
    return values


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
    user: User = Depends(get_current_user_cookie),
):
    """Render the main QSO entry form page."""
    return templates.TemplateResponse(
        request,
        "log/form.html",
        {
            "callsign": user.callsign,
            "custom_fields": enabled_custom_fields_for_user(user),
            "custom_field_defaults": await custom_field_defaults(user),
        },
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
    user: User = Depends(get_current_user_cookie),
):
    """Handle HTMX QSO form submission.

    Always returns HTTP 200 with an HTML partial — HTMX 2.x won't swap on 4xx.
    Duplicate found and not forced → return warning partial with "Save Anyway" button.
    No duplicate or force=True → insert QSO and return success partial.
    Profile fields (OPERATOR, STATION_CALLSIGN, etc.) are auto-stamped from the User document.
    """
    callsign = user.callsign
    submitted_form = await request.form()
    custom_values = _custom_qso_values_from_form(submitted_form, user)

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
    form_data.update(custom_values)

    qso_dict = build_qso_dict(
        {k: v for k, v in form_data.items() if v is not None},
        operator=callsign,
        profile=user,
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
    insert_result = await insert_qso_dict(qso_dict)
    if insert_result.status == "duplicate":
        existing = insert_result.existing
        dup_dict = {
            "CALL": existing.CALL if existing else qso_dict["CALL"],
            "BAND": existing.BAND if existing else qso_dict["BAND"],
            "MODE": existing.MODE if existing else qso_dict["MODE"],
            "qso_date_utc": existing.qso_date_utc.isoformat()
            if existing and existing.qso_date_utc else "",
        }
        return templates.TemplateResponse(
            request,
            "log/qso_result.html",
            {
                "duplicate": dup_dict,
                "success": None,
                "qso": None,
                "form": form_data,
            },
        )

    qso = insert_result.qso

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


@ui_router.get("/custom-field-defaults")
async def get_custom_qso_field_defaults(
    call: str = Query(""),
    user: User = Depends(get_current_user_cookie),
) -> dict[str, str]:
    """Return CALL-dependent custom field defaults for the QSO entry form."""
    return await custom_field_defaults(user, call=call)


# ---------------------------------------------------------------------------
# Log view — paginated list with filtering, sorting, inline edit, soft-delete
# ---------------------------------------------------------------------------

def _qso_to_view_dict(qso: QSO, user: User | None = None) -> dict:
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
        "created_at": qso.created_at,
        "operator": qso.operator_callsign,
    }
    # Pull extra ADIF fields from model_extra (set via extra="allow")
    extra = qso.model_extra or {}
    d["FREQ"] = extra.get("FREQ", "")
    d["RST_SENT"] = extra.get("RST_SENT", "")
    d["RST_RCVD"] = extra.get("RST_RCVD", "")
    d["QSO_DATE"] = extra.get("QSO_DATE", "")
    d["TIME_ON"] = extra.get("TIME_ON", "")
    d["STATION_CALLSIGN"] = extra.get("STATION_CALLSIGN", "")
    d["fields"] = build_field_values(qso, user=user)
    # Flag enrichment — render-time lookup, not stored
    iso = lookup_prefix(qso.CALL) if qso.CALL else None
    d["flag_iso"] = iso.lower() if iso else None
    country_obj = pycountry.countries.get(alpha_2=iso) if iso else None
    d["flag_country"] = country_obj.name if country_obj else (iso if iso else None)
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
    user: User = Depends(get_current_user_cookie),
):
    """Render the paginated QSO log view.

    Supports filtering by callsign, band, mode, and date range.
    Supports sorting by qso_date_utc, CALL, or BAND (prefix '-' for descending).
    HTMX requests (HX-Request header) return only the table partial.
    Full page requests return the complete log.html page.
    """
    callsign = user.callsign
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

    qsos = [_qso_to_view_dict(q, user=user) for q in qsos_raw]
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
        "notify_sound": user.notify_sound,
        "field_catalog": get_field_catalog_for_user(user),
        "default_column_keys": get_default_column_keys_for_user(user),
        "configurable_column_keys": get_configurable_column_keys_for_user(user),
    }

    # HTMX partial swap: return only the table, not the full page
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, "log/log_table.html", ctx)

    return templates.TemplateResponse(request, "log/log.html", ctx)


@ui_router.get("/qsos/{qso_id}/edit", response_class=HTMLResponse)
async def qso_edit_row(
    request: Request,
    qso_id: str,
    user: User = Depends(get_current_user_cookie),
):
    """Return the editable row partial for a QSO (HTMX outerHTML swap)."""
    try:
        oid = PydanticObjectId(qso_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    qso = await QSO.get(oid)
    if qso is None or qso.operator_callsign != user.callsign or qso.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    return templates.TemplateResponse(
        request,
        "log/qso_row_edit.html",
        {
            "qso": _qso_to_view_dict(qso, user=user),
            "field_catalog": get_field_catalog_for_user(user),
        },
    )


@ui_router.get("/qsos/{qso_id}", response_class=HTMLResponse)
async def qso_view_row(
    request: Request,
    qso_id: str,
    user: User = Depends(get_current_user_cookie),
):
    """Return the view-mode row partial for a QSO (used by Cancel button)."""
    try:
        oid = PydanticObjectId(qso_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    qso = await QSO.get(oid)
    if qso is None or qso.operator_callsign != user.callsign or qso.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    return templates.TemplateResponse(
        request,
        "log/qso_row.html",
        {
            "qso": _qso_to_view_dict(qso, user=user),
            "field_catalog": get_field_catalog_for_user(user),
        },
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
    user: User = Depends(get_current_user_cookie),
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
    if qso is None or qso.operator_callsign != user.callsign or qso.is_deleted:
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

    submitted_form = await request.form()
    update_dict.update(_custom_qso_values_from_form(submitted_form, user, include_empty=True))

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
    for protected in ("_operator", "_deleted", "operator_callsign", "is_deleted", "_id",
                      "_created_at", "created_at", "rowHash", "row_hash"):
        update_dict.pop(protected, None)

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update",
        )
    update_dict["rowHash"] = row_hash_for_updated_qso(qso, update_dict)
    try:
        await qso.update({"$set": update_dict})
    except Exception as exc:
        if "row_hash_unique_idx" not in str(exc) and "rowHash" not in str(exc):
            raise
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="QSO already exists",
        )

    # Refetch to get the updated document
    updated = await QSO.get(oid)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QSO not found")

    return templates.TemplateResponse(
        request,
        "log/qso_row.html",
        {
            "qso": _qso_to_view_dict(updated, user=user),
            "field_catalog": get_field_catalog_for_user(user),
        },
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
        report = await import_qsos_from_bytes(raw, callsign)
    except ValueError as exc:
        # Size limit exceeded — render a simple error message in the target div
        return HTMLResponse(
            content=f'<div class="error-msg">{str(exc)}</div>',
            status_code=200,
        )
    for duplicate in report.get("duplicates", []):
        if "record" in duplicate:
            duplicate["import_token"] = _encode_import_record(duplicate["record"])
    return templates.TemplateResponse(
        request,
        "log/import_report.html",
        {"report": report},
    )


@ui_router.post("/import/duplicates", response_class=HTMLResponse)
async def import_selected_duplicates(
    request: Request,
    records: Annotated[list[str] | None, Form()] = None,
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    """Force-import selected duplicate ADIF records from the import review table."""
    accepted: list[dict] = []
    duplicates: list[dict] = []
    errors: list[dict] = []

    selected = records or []
    for idx, token in enumerate(selected):
        try:
            record = _decode_import_record(token)
            qso_dict = build_qso_dict(record, callsign)
            insert_result = await insert_qso_dict(qso_dict)
        except Exception as exc:
            errors.append({
                "record_index": idx,
                "call": "?",
                "error": str(exc),
            })
            continue

        if insert_result.status == "duplicate":
            duplicates.append({
                "record_index": idx,
                "call": qso_dict["CALL"],
                "existing_id": str(insert_result.existing.id) if insert_result.existing else "",
            })
            continue

        qso = insert_result.qso
        accepted.append({
            "record_index": idx,
            "call": qso_dict["CALL"],
            "id": str(qso.id),
        })

    report = {
        "total_records": len(selected),
        "accepted": accepted,
        "duplicates": duplicates,
        "errors": errors,
        "duplicate_review": True,
    }
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


# ---------------------------------------------------------------------------
# About page
# ---------------------------------------------------------------------------

@ui_router.get("/about", response_class=HTMLResponse)
async def about_page(
    request: Request,
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    """Render the About page."""
    return templates.TemplateResponse(
        request,
        "log/about.html",
        {"callsign": callsign},
    )


# ---------------------------------------------------------------------------
# Profile settings
# ---------------------------------------------------------------------------

@ui_router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    user: User = Depends(get_current_user_cookie),
):
    """Render the operator profile settings form, pre-populated with current values."""
    return templates.TemplateResponse(
        request,
        "log/profile.html",
        {
            "callsign": user.callsign,
            "profile": user,
            "custom_qso_fields": custom_fields_for_user(user),
        },
    )


@ui_router.post("/profile", response_class=HTMLResponse)
async def profile_update(
    request: Request,
    user: User = Depends(get_current_user_cookie),
    station_callsign: Annotated[Optional[str], Form()] = None,
    name: Annotated[Optional[str], Form()] = None,
    email: Annotated[Optional[str], Form()] = None,
    qth: Annotated[Optional[str], Form()] = None,
    state: Annotated[Optional[str], Form()] = None,
    country: Annotated[Optional[str], Form()] = None,
    my_gridsquare: Annotated[Optional[str], Form()] = None,
    my_rig: Annotated[Optional[str], Form()] = None,
    my_antenna: Annotated[Optional[str], Form()] = None,
    tx_pwr: Annotated[Optional[str], Form()] = None,
    notify_sound: Annotated[Optional[str], Form()] = None,
    aclog_bridge_id: Annotated[Optional[list[str]], Form()] = None,
    aclog_bridge_name: Annotated[Optional[list[str]], Form()] = None,
    aclog_bridge_host: Annotated[Optional[list[str]], Form()] = None,
    aclog_bridge_port: Annotated[Optional[list[str]], Form()] = None,
    aclog_bridge_enabled: Annotated[Optional[list[str]], Form()] = None,
    custom_field_slot: Annotated[Optional[list[str]], Form()] = None,
    custom_field_label: Annotated[Optional[list[str]], Form()] = None,
    custom_field_adif_name: Annotated[Optional[list[str]], Form()] = None,
    custom_field_enabled: Annotated[Optional[list[str]], Form()] = None,
    custom_field_fill_behavior: Annotated[Optional[list[str]], Form()] = None,
    custom_field_force_uppercase: Annotated[Optional[list[str]], Form()] = None,
):
    """Process profile settings form submission via HTMX.

    Always returns HTTP 200 — HTMX 2.x won't swap on 4xx.
    Validates via ProfileUpdateRequest, calls update_profile() directly.
    Returns a success or error partial into #profile-result.
    """
    # Collect form fields into dict, converting empty strings to None
    raw: dict = {}
    for field_name, value in [
        ("station_callsign", station_callsign),
        ("name", name),
        ("email", email),
        ("qth", qth),
        ("state", state),
        ("country", country),
        ("my_gridsquare", my_gridsquare),
        ("my_rig", my_rig),
        ("my_antenna", my_antenna),
        ("tx_pwr", tx_pwr),
    ]:
        if value is not None:
            stripped = value.strip()
            if field_name == "tx_pwr":
                raw[field_name] = float(stripped) if stripped else None
            else:
                raw[field_name] = stripped if stripped else None

    raw["notify_sound"] = (notify_sound == "true")
    try:
        raw["aclog_bridges"] = _parse_aclog_bridge_form(
            ids=aclog_bridge_id or [],
            names=aclog_bridge_name or [],
            hosts=aclog_bridge_host or [],
            ports=aclog_bridge_port or [],
            enabled_ids=set(aclog_bridge_enabled or []),
        )
        raw["custom_qso_fields"] = _parse_custom_qso_field_form(
            slots=custom_field_slot or [],
            labels=custom_field_label or [],
            adif_names=custom_field_adif_name or [],
            fill_behaviors=custom_field_fill_behavior or [],
            enabled_slots=set(custom_field_enabled or []),
            uppercase_slots=set(custom_field_force_uppercase or []),
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "log/profile_result.html",
            {"error": str(exc), "success": False},
        )

    try:
        validated = ProfileUpdateRequest(**raw)
    except ValidationError as exc:
        # Extract first human-readable error message
        first_error = exc.errors()[0]
        msg = first_error.get("msg", "Validation error")
        field = first_error.get("loc", [""])[0]
        error_text = f"{field}: {msg}" if field else msg
        return templates.TemplateResponse(
            request,
            "log/profile_result.html",
            {"error": error_text, "success": False},
        )

    updates = validated.model_dump(exclude_unset=True)
    await update_profile(user, updates)

    return templates.TemplateResponse(
        request,
        "log/profile_result.html",
        {"error": None, "success": True},
    )


def _parse_aclog_bridge_form(
    ids: list[str],
    names: list[str],
    hosts: list[str],
    ports: list[str],
    enabled_ids: set[str],
) -> list[dict]:
    bridges: list[dict] = []
    total = max(len(ids), len(names), len(hosts), len(ports), 0)

    for idx in range(total):
        row_id = ids[idx].strip() if idx < len(ids) else ""
        name = names[idx].strip() if idx < len(names) else ""
        host = hosts[idx].strip() if idx < len(hosts) else ""
        port_text = ports[idx].strip() if idx < len(ports) else ""

        if not name and not host:
            continue

        if not row_id or row_id.startswith("new-"):
            row_id = uuid.uuid4().hex

        try:
            port = int(port_text) if port_text else 1100
        except ValueError as exc:
            raise ValueError("ACLog bridge port must be a number") from exc

        bridges.append({
            "id": row_id,
            "name": name,
            "host": host,
            "port": port,
            "enabled": row_id in enabled_ids or ids[idx].strip() in enabled_ids,
        })

    return bridges


def _parse_custom_qso_field_form(
    slots: list[str],
    labels: list[str],
    adif_names: list[str],
    fill_behaviors: list[str],
    enabled_slots: set[str],
    uppercase_slots: set[str],
) -> list[dict]:
    fields: list[dict] = []
    total = max(len(slots), len(labels), len(adif_names), len(fill_behaviors), 0)

    for idx in range(total):
        slot_text = slots[idx].strip() if idx < len(slots) else str(idx + 1)
        try:
            slot = int(slot_text)
        except ValueError as exc:
            raise ValueError("Custom QSO field slot must be a number") from exc
        label = labels[idx].strip() if idx < len(labels) else f"Other {slot}"
        adif_name = adif_names[idx].strip() if idx < len(adif_names) else f"OTHER_{slot}"
        fill_behavior = (
            fill_behaviors[idx].strip()
            if idx < len(fill_behaviors) and fill_behaviors[idx].strip()
            else "none"
        )

        fields.append({
            "slot": slot,
            "label": label,
            "adif_name": adif_name,
            "enabled": str(slot) in enabled_slots,
            "fill_behavior": fill_behavior,
            "force_uppercase": str(slot) in uppercase_slots,
        })

    return fields


# ---------------------------------------------------------------------------
# API Token management UI (HTMX partials)
# ---------------------------------------------------------------------------


@ui_router.get("/tokens", response_class=HTMLResponse)
async def tokens_list(
    request: Request,
    user: User = Depends(get_current_user_cookie),
):
    """Return the token list partial.

    Loaded lazily via hx-trigger="load" on the profile page and refreshed
    after token creation or revocation.  Always returns HTTP 200.
    """
    tokens = (
        await ApiToken.find(
            ApiToken.user_id == user.id,
            ApiToken.enabled == True,  # noqa: E712
        )
        .sort(-ApiToken.created_at)
        .to_list()
    )
    return templates.TemplateResponse(
        request,
        "log/tokens_list.html",
        {"tokens": tokens},
    )


@ui_router.post("/tokens/create", response_class=HTMLResponse)
async def tokens_create(
    request: Request,
    user: User = Depends(get_current_user_cookie),
    name: Annotated[str, Form()] = "",
    expires_at: Annotated[Optional[str], Form()] = None,
):
    """Handle the token creation form submission.

    Always returns HTTP 200 — HTMX 2.x won't swap on 4xx.
    On success: returns token_created.html with full_token (show-once banner).
    On error: returns token_created.html with error message.
    """
    try:
        validate_token_name(name)
    except ValueError as exc:
        return templates.TemplateResponse(
            request,
            "log/token_created.html",
            {"error": str(exc), "full_token": None},
        )

    expires_at_dt = None
    if expires_at and expires_at.strip():
        try:
            expires_at_dt = datetime.strptime(expires_at.strip(), "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return templates.TemplateResponse(
                request,
                "log/token_created.html",
                {"error": "Invalid date format: use YYYY-MM-DD", "full_token": None},
            )

    full_token, token_prefix = generate_api_token()
    hashed_token = hash_api_token(full_token)

    doc = ApiToken(
        user_id=user.id,
        name=name,
        token_prefix=token_prefix,
        hashed_token=hashed_token,
        expires_at=expires_at_dt,
    )
    await doc.insert()
    from app.udp.token_cache import token_cache
    token_cache.notify_refresh()

    return templates.TemplateResponse(
        request,
        "log/token_created.html",
        {"error": None, "full_token": full_token, "token_id": str(doc.id)},
    )


@ui_router.delete("/tokens/{token_id}", response_class=HTMLResponse)
async def tokens_revoke(
    request: Request,
    token_id: str,
    user: User = Depends(get_current_user_cookie),
):
    """Revoke a token via HTMX delete.

    Returns empty 200 on success — hx-swap="outerHTML" removes the row from DOM.
    Returns empty 200 on any error (silent no-op for stale rows).
    """
    try:
        oid = PydanticObjectId(token_id)
    except Exception:
        return Response(content="", status_code=200)

    token = await ApiToken.get(oid)
    if token is None or token.user_id != user.id or not token.enabled:
        return Response(content="", status_code=200)

    await token.set({ApiToken.enabled: False})
    from app.udp.token_cache import token_cache
    token_cache.notify_refresh()
    return Response(content="", status_code=200)


# -------------------------------------------------------------------
# Phase 54: Operator clear log (Danger Zone)
# -------------------------------------------------------------------


@ui_router.get("/profile/clear/modal", response_class=HTMLResponse)
async def clear_log_modal(
    request: Request,
    user: User = Depends(get_current_user_cookie),
):
    """Return the clear-log confirmation modal fragment with current QSO count.

    The count is queried server-side — never trust a client-supplied number.
    Always returns HTTP 200 — HTMX 2.x will not swap on 4xx.
    """
    count = await QSO.find(
        {"_operator": user.callsign, "_deleted": False}
    ).count()
    return templates.TemplateResponse(
        request,
        "log/clear_log_modal.html",
        {"count": count, "error": None},
    )


@ui_router.post("/profile/clear", response_class=HTMLResponse)
async def clear_log_confirm(
    request: Request,
    user: User = Depends(get_current_user_cookie),
    password: Annotated[str, Form()] = "",
):
    """Verify operator password and permanently delete all their active QSOs.

    Always returns HTTP 200 — HTMX 2.x ignores body on 4xx responses.
    Wrong password → re-render the modal with an inline error (modal stays open).
    Correct password → delete and return the success fragment (modal replaced).
    """
    if not verify_password(password, user.hashed_password):
        count = await QSO.find(
            {"_operator": user.callsign, "_deleted": False}
        ).count()
        return templates.TemplateResponse(
            request,
            "log/clear_log_modal.html",
            {"count": count, "error": "Incorrect password — no QSOs were deleted."},
            status_code=200,
        )

    deleted = await clear_operator_log(user.callsign)
    return templates.TemplateResponse(
        request,
        "log/clear_log_success.html",
        {"deleted": deleted},
        status_code=200,
    )
