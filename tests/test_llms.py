"""Smoke tests for /llms.txt and /llms-full.txt endpoints (Phase 51).

No MongoDB required — FileResponse routes have zero database dependencies.
Requires static/llms.txt and static/llms-full.txt to exist on disk.
Run: uv run pytest tests/test_llms.py -x
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_llms_index():
    """LLMS-01: GET /llms.txt returns 200 with project title and contents section."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/llms.txt")
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text[:200]}"
    assert "# ollog" in resp.text, "H1 title '# ollog' missing from /llms.txt"
    # Section links to /llms-full.txt must be present
    assert "/llms-full.txt" in resp.text, "link to /llms-full.txt missing from index"


@pytest.mark.asyncio
async def test_llms_full():
    """LLMS-02: GET /llms-full.txt returns 200 with all three section headers."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/llms-full.txt")
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text[:200]}"
    assert "# ollog" in resp.text, "H1 title missing from /llms-full.txt"
    assert "## API Reference" in resp.text, "API Reference section header missing"
    assert "## ADIF Field Reference" in resp.text, "ADIF Field Reference section header missing"
    assert "## Getting Started" in resp.text, "Getting Started section header missing"


@pytest.mark.asyncio
async def test_llms_content_type():
    """LLMS-03: Both routes return Content-Type: text/plain; charset=utf-8."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        for path in ("/llms.txt", "/llms-full.txt"):
            resp = await ac.get(path)
            assert resp.status_code == 200, f"{path} returned {resp.status_code}"
            ct = resp.headers.get("content-type", "")
            assert "text/plain" in ct, f"{path} content-type missing text/plain: {ct!r}"
            assert "charset=utf-8" in ct, f"{path} content-type missing charset=utf-8: {ct!r}"


@pytest.mark.asyncio
async def test_llms_not_in_schema():
    """LLMS-03: Neither route appears in /openapi.json."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    paths = schema.get("paths", {})
    assert "/llms.txt" not in paths, "/llms.txt must carry include_in_schema=False"
    assert "/llms-full.txt" not in paths, "/llms-full.txt must carry include_in_schema=False"


@pytest.mark.asyncio
async def test_llms_full_api_reference():
    """CONTENT-01: /llms-full.txt includes API reference with curl examples for all 16 endpoints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/llms-full.txt")
    body = resp.text
    # Representative endpoints from each router — exhaustive 16 listed in RESEARCH.md
    assert "POST /auth/token" in body, "auth login endpoint missing"
    assert "GET /auth/me" in body, "/auth/me endpoint missing"
    assert "POST /api/qsos/" in body, "POST /api/qsos/ endpoint missing"
    assert "GET /api/qsos/" in body, "GET /api/qsos/ endpoint missing"
    assert "PATCH /api/qsos/" in body, "PATCH /api/qsos/ endpoint missing"
    assert "DELETE /api/qsos/" in body, "DELETE /api/qsos/ endpoint missing"
    assert "POST /api/adif/import" in body, "ADIF import endpoint missing"
    assert "GET /api/adif/export" in body, "ADIF export endpoint missing"
    assert "GET /api/profile/" in body, "profile GET endpoint missing"
    assert "PATCH /api/profile/" in body, "profile PATCH endpoint missing"
    assert "POST /api/tokens/" in body, "tokens POST endpoint missing"
    assert "GET /api/tokens/" in body, "tokens GET endpoint missing"
    assert "DELETE /api/tokens/" in body, "tokens DELETE endpoint missing"
    assert "GET /health" in body, "/health endpoint missing"
    assert "GET /api/whoami" in body, "/api/whoami endpoint missing"
    # At least one curl example must be present
    assert "curl" in body, "no curl examples found in API reference"


@pytest.mark.asyncio
async def test_llms_full_adif_reference():
    """CONTENT-02: /llms-full.txt includes ADIF field reference."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/llms-full.txt")
    body = resp.text
    # Required ADIF fields
    assert "CALL" in body, "ADIF CALL field missing"
    assert "QSO_DATE" in body, "ADIF QSO_DATE field missing"
    assert "TIME_ON" in body, "ADIF TIME_ON field missing"
    assert "BAND" in body, "ADIF BAND field missing"
    assert "MODE" in body, "ADIF MODE field missing"
    # Format conventions
    assert "YYYYMMDD" in body, "ADIF QSO_DATE format convention missing"
    assert "HHMM" in body, "ADIF TIME_ON format convention missing"
    # Auto-stamped fields documented
    assert "OPERATOR" in body, "ADIF OPERATOR auto-stamped field missing"
    assert "STATION_CALLSIGN" in body, "ADIF STATION_CALLSIGN auto-stamped field missing"


@pytest.mark.asyncio
async def test_llms_full_getting_started():
    """CONTENT-03: /llms-full.txt includes operator getting-started walkthrough."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/llms-full.txt")
    body = resp.text
    assert "## Getting Started" in body, "Getting Started section header missing"
    # Walkthrough must cover login, profile, logging a QSO, ADIF import/export
    assert "login" in body.lower(), "login step missing from getting-started"
    assert "profile" in body.lower(), "profile step missing from getting-started"
    assert "QSO" in body, "QSO step missing from getting-started"
    assert "import" in body.lower() or "export" in body.lower(), "ADIF import/export missing from walkthrough"
