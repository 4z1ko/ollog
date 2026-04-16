# Phase 42: Stats Aggregation Backend - Pattern Map

**Mapped:** 2026-04-15
**Files analyzed:** 5 new files + 1 modified file
**Analogs found:** 5 / 5 (+ 1 modification with exact pattern)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/stats/__init__.py` | config | — | `app/profile/__init__.py` | exact (empty module init) |
| `app/stats/service.py` | service | batch / transform | `app/qso/service.py` | role-match + data-flow-match |
| `app/stats/router.py` | route | request-response | `app/qso/ui_router.py` lines 550–560 (`about_page`) | exact |
| `templates/log/stats.html` | template | — | `templates/log/about.html` | exact (stub extending `base_app.html`) |
| `tests/test_stats.py` | test | — | `tests/test_operator_isolation.py` | exact (isolation_test_db fixture + pytest-asyncio pattern) |
| `app/main.py` (modified) | config | — | `app/main.py` lines 110–113 (`qso_ui_router` registration block) | exact |

---

## Pattern Assignments

### `app/stats/__init__.py` (module init)

**Analog:** `app/profile/__init__.py`

Empty file — no content required. All domain module `__init__.py` files in this project are empty.

---

### `app/stats/service.py` (service, batch/transform)

**Analog:** `app/qso/service.py`

**Imports pattern** (`app/qso/service.py` lines 1–11):
```python
"""QSO service layer — ..."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

from app.qso.models import QSO
```

For `app/stats/service.py`, adapt as:
```python
"""Stats service layer — band/mode/DXCC aggregation for operator stats page."""
from __future__ import annotations

import pycountry
from app.callsign.prefixes import lookup_prefix
from app.qso.models import QSO
```

**Motor aggregation access pattern** (`app/qso/service.py` lines 90–97 as structural reference; confirmed pattern from STATE.md):
```python
# The pattern established for any Motor aggregation in this codebase:
collection = QSO.get_motor_collection()          # Motor AsyncCollection
cursor = collection.aggregate(pipeline)          # returns async cursor
results = await cursor.to_list(length=None)      # await full materialisation
```

**Operator isolation + soft-delete guard** (`app/qso/service.py` lines 88–96 and lines 200–201):
```python
# Every query must begin with this exact match dict — no exceptions:
query: dict = {"_operator": operator, "_deleted": False}

# For aggregation pipelines, this becomes the FIRST $match stage:
match_stage = {"$match": {"_operator": callsign, "_deleted": False}}
```

**Service function signature convention** (`app/qso/service.py` lines 183–192):
```python
async def get_qso_page(
    operator: str,
    page: int = 1,
    ...
) -> tuple[list[QSO], int]:
    """Fetch a paginated, filtered page of active QSOs for an operator.
    ...
    """
```

For stats, mirror as:
```python
async def get_stats(callsign: str) -> dict:
    """Compute band counts, mode counts, DXCC entity counts for one operator.

    Returns same dict shape for empty and non-empty logs (STATS-07).
    All pipelines begin with $match guard (STATS-06).
    """
```

**pycountry + lookup_prefix usage pattern** (`app/qso/ui_router.py` lines 23–24 and lines 241–244):
```python
import pycountry
from app.callsign.prefixes import lookup_prefix

# Inside a function body (never at module level):
iso = lookup_prefix(qso.CALL) if qso.CALL else None
country_obj = pycountry.countries.get(alpha_2=iso) if iso else None
d["flag_country"] = country_obj.name if country_obj else (iso if iso else None)
```

**Empty-state return convention** — the service must always return the complete dict shape. Based on the pattern of `get_qso_page` which always returns `([], 0)` for empty results rather than `None`:
```python
# STATS-07: return complete shape for empty log, never raise or return None
if total_qsos == 0:
    return {
        "band_counts": {},
        "mode_counts": {},
        "entity_counts": [],
        "unique_entity_count": 0,
        "total_qsos": 0,
    }
```

---

### `app/stats/router.py` (route, request-response)

**Analog:** `app/qso/ui_router.py` — specifically the `about_page` handler (lines 550–560) and `form_page` handler (lines 112–122)

**Router declaration pattern** (`app/qso/ui_router.py` line 38):
```python
ui_router = APIRouter(prefix="/log", tags=["log-ui"])
```

For stats, mirror as:
```python
stats_router = APIRouter(prefix="/log", tags=["stats-ui"])
```

**Imports pattern** (`app/qso/ui_router.py` lines 1–36, trimmed to what stats needs):
```python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.auth.dependencies import get_current_operator_callsign_cookie

templates = Jinja2Templates(directory="templates")
```

**Cookie-auth TemplateResponse pattern** (`app/qso/ui_router.py` lines 550–560):
```python
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
```

For stats, mirror as (note prefix `/log` on router + endpoint `/stats` = full path `/log/stats`):
```python
@stats_router.get("/stats", response_class=HTMLResponse)
async def stats_page(
    request: Request,
    callsign: str = Depends(get_current_operator_callsign_cookie),
):
    """Render the operator stats page."""
    data = await get_stats(callsign)
    return templates.TemplateResponse(
        request,
        "log/stats.html",
        {**data, "callsign": callsign},
    )
```

**Template context dict spreading pattern** (`app/qso/ui_router.py` lines 300–315):
```python
ctx = {
    "qsos": qsos,
    "total": total,
    ...
    "callsign": callsign,
}
return templates.TemplateResponse(request, "log/log.html", ctx)
```

The `{**data, "callsign": callsign}` form is idiomatic when the service returns a full context dict that only needs `callsign` appended.

---

### `templates/log/stats.html` (template stub)

**Analog:** `templates/log/about.html` lines 1–4 (extends + block declarations)

**Template extends + block pattern** (`templates/log/about.html` lines 1–4):
```html
{% extends "base_app.html" %}
{% block title %}ollog — About{% endblock %}
{% block active_page %}about{% endblock %}

{% block content %}
...
{% endblock %}
```

For the Phase 42 stub, copy this shell exactly, substituting the page name and adding a minimal content block that consumes `total_qsos` to confirm the data dict flows through:
```html
{# Phase 42 stub — charts and full stats UI added in Phase 43 #}
{% extends "base_app.html" %}
{% block title %}ollog — Stats{% endblock %}
{% block active_page %}stats{% endblock %}

{% block content %}
<div>Stats coming soon. Total QSOs: {{ total_qsos }}</div>
{% endblock %}
```

---

### `tests/test_stats.py` (test)

**Analog:** `tests/test_operator_isolation.py`

**Test file header + imports pattern** (`tests/test_operator_isolation.py` lines 1–31):
```python
"""Operator isolation audit and integration tests.
...
"""
import inspect
import socket
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from beanie import init_beanie
from fastapi.routing import APIRoute
from pymongo import AsyncMongoClient

from app.main import app
from app.qso.models import QSO
from app.qso.service import find_duplicate, get_qso_page
```

For test_stats.py, adapt imports to bring in `get_stats` and `User`:
```python
"""Integration tests for Phase 42 stats aggregation backend.

Tests STATS-06 (operator isolation) and STATS-07 (empty-state shape).
"""
import socket
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.auth.models import User
from app.auth.service import create_access_token, hash_password
from app.main import app
from app.qso.models import QSO
from app.stats.service import get_stats
```

**`isolation_test_db` fixture pattern** — includes BOTH `QSO` and `User` models (`tests/test_operator_isolation.py` lines 102–122):
```python
@pytest_asyncio.fixture(scope="function")
async def isolation_test_db():
    if not _mongo_available():
        pytest.skip("MongoDB not available at localhost:27017")

    from app.auth.models import User

    client = AsyncMongoClient(
        "mongodb://localhost:27017/?directConnection=true",
        serverSelectionTimeoutMS=2000,
    )
    db = client["ollog_test"]
    await init_beanie(database=db, document_models=[QSO, User])
    yield db
    await client.drop_database("ollog_test")
    await client.aclose()
```

Stats tests use this same pattern because `get_stats()` needs Beanie to be initialised with `QSO`. The fixture must include `User` only if route-level auth tests are added (cookie tests need user creation).

**_make_qso_doc helper pattern** (`tests/test_operator_isolation.py` lines 177–193):
```python
def _make_qso_doc(operator: str, call: str, **kwargs) -> QSO:
    """Return an unsaved QSO document with sensible defaults."""
    return QSO(
        **{
            "_operator": operator,
            "CALL": call,
            "BAND": kwargs.get("BAND", "20M"),
            "MODE": kwargs.get("MODE", "SSB"),
            "qso_date_utc": kwargs.get(
                "qso_date_utc",
                datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
            ),
            "QSO_DATE": kwargs.get("QSO_DATE", "20240601"),
            "TIME_ON": kwargs.get("TIME_ON", "1200"),
        }
    )
```

Copy this helper directly into `test_stats.py` — it is exactly what is needed to seed QSOs for the stats tests.

**pytest.mark.asyncio + integration test pattern** (`tests/test_operator_isolation.py` lines 195–243):
```python
@pytest.mark.asyncio
async def test_operator_cannot_see_other_operators_qsos(isolation_test_db):
    # insert data for AA1AA and BB2BB
    # query each operator
    # assert counts and no cross-contamination
```

**HTTP integration test using httpx.ASGITransport** (`tests/test_profile_api.py` lines 20–53):
```python
@pytest_asyncio.fixture(scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_get_profile_no_auth(client):
    resp = await client.get("/api/profile/")
    assert resp.status_code == 401
```

Use this pattern for the route-level auth test (`test_stats_route_requires_auth`): make a GET to `/log/stats` without a cookie and assert the redirect to `/log/login` (status 302) or 401.

---

### `app/main.py` (modification — router registration)

**Analog:** `app/main.py` lines 110–113 (the `qso_ui_router` registration block)

**Exact lines to copy and adapt** (`app/main.py` lines 110–113):
```python
# QSO UI router (browser-based, cookie auth, Jinja2 templates)
from app.qso.ui_router import ui_router as qso_ui_router  # noqa: E402

app.include_router(qso_ui_router, include_in_schema=False)
```

For stats, insert immediately after the token router block (lines 131–133), following the same pattern:
```python
# Stats UI router (browser-based, cookie auth, Jinja2 templates)
from app.stats.router import stats_router  # noqa: E402

app.include_router(stats_router, include_in_schema=False)
```

Key: `include_in_schema=False` is required — this is a UI route, not a REST API endpoint. All UI routers in `app/main.py` use this flag.

---

## Shared Patterns

### Authentication (Cookie)
**Source:** `app/auth/dependencies.py` lines 104–108
**Apply to:** `app/stats/router.py` (all route handlers)
```python
async def get_current_operator_callsign_cookie(
    user: User = Depends(get_current_user_cookie),
) -> str:
    """Cookie-auth version of callsign injection for UI routes under /log/."""
    return user.callsign
```
Import as: `from app.auth.dependencies import get_current_operator_callsign_cookie`
Use as: `callsign: str = Depends(get_current_operator_callsign_cookie)` in every route handler parameter list.

### Operator Isolation Guard
**Source:** `app/qso/service.py` lines 200–201; `app/qso/models.py` lines 39, confirmed by `app/qso/service.py` lines 88–96
**Apply to:** `app/stats/service.py` — every MongoDB pipeline
```python
# This exact pattern must be the FIRST stage of every aggregation pipeline:
{"$match": {"_operator": callsign, "_deleted": False}}
```
Both keys are required. `_operator` enforces operator isolation; `_deleted` excludes soft-deleted QSOs. Omitting either is a data leak or data inflation bug.

### Template Response Pattern
**Source:** `app/qso/ui_router.py` lines 116–121
**Apply to:** `app/stats/router.py`
```python
return templates.TemplateResponse(
    request,
    "log/<page>.html",
    {"callsign": callsign, ...context_dict},
)
```
The `request` object is always the first positional argument (FastAPI/Starlette convention used throughout this project). `templates` is a module-level `Jinja2Templates(directory="templates")` singleton.

### Module-Level Singleton Avoidance
**Source:** `app/qso/ui_router.py` line 36; confirmed by RESEARCH.md Pitfall 5
**Apply to:** `app/stats/service.py`
```python
# CORRECT: call inside async function body
async def get_stats(callsign: str) -> dict:
    collection = QSO.get_motor_collection()  # inside async def — Beanie is initialised
    ...

# WRONG: module level
collection = QSO.get_motor_collection()  # Beanie not yet init'd at import time
```

### Test MongoDB Fixture
**Source:** `tests/test_operator_isolation.py` lines 102–122
**Apply to:** `tests/test_stats.py`

The `isolation_test_db` fixture (not the `test_db` fixture from `conftest.py`) is the correct model for stats tests because it includes both `QSO` and `User` models in `init_beanie`. The base `test_db` fixture only includes `QSO`, which is insufficient if the test needs to create users for cookie auth flows.

---

## No Analog Found

All files in this phase have close analogs in the codebase. No files need to rely on RESEARCH.md patterns exclusively.

---

## Metadata

**Analog search scope:** `app/` (all modules), `tests/`, `templates/log/`
**Files scanned:** 10 source files read directly
**Key discovery:** The stats service is a pure aggregation-and-transform module — it has no Beanie CRUD operations itself (only Motor `.aggregate()` calls). The `app/qso/service.py` analog covers the structural conventions; the Motor aggregation pattern is confirmed via STATE.md and the `watch_qsos` pipeline in `app/feed/manager.py` (lines 31–35) demonstrates the Motor collection access idiom in async context.
**Pattern extraction date:** 2026-04-15
