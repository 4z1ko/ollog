"""QSO entry UI router — browser-based QSO logging for operators.

Serves HTML pages and HTMX partial responses for the QSO entry form.
All protected routes require cookie-based JWT auth.
Auth failures (401/403) are caught by the app-level exception handler
in main.py and redirected to /log/login.

Mounted at /log by app/main.py.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.dependencies import get_current_operator_callsign_cookie
from app.auth.models import User
from app.auth.service import create_access_token, verify_password
from app.qso.models import QSO
from app.qso.service import build_qso_dict, find_duplicate, parse_adif_datetime

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
