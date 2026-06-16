"""Tests for the HTMX operator profile settings form."""

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient
from pymongo.errors import ServerSelectionTimeoutError
from starlette.requests import Request

from app import database
from app.aclog.sync import ACLogSyncReport
from app.auth.models import ACLogBridge, User
from app.auth.service import create_access_token, hash_password
from app.config import settings
from app.main import app
from app.qso.ui_router import profile_update
from app.qso.models import QSO


def _default_custom_field_form() -> dict[str, list[str]]:
    return {
        "custom_field_slot": [str(slot) for slot in range(1, 9)],
        "custom_field_label": [f"Other {slot}" for slot in range(1, 9)],
        "custom_field_adif_name": [f"OTHER_{slot}" for slot in range(1, 9)],
        "custom_field_fill_behavior": ["none" for _ in range(1, 9)],
    }


@pytest_asyncio.fixture(scope="function")
async def profile_ui_db(monkeypatch):
    client = AsyncMongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=2000,
        directConnection=True,
    )
    db_name = "ollog_profile_ui_test"
    try:
        await client.admin.command("ping")
    except ServerSelectionTimeoutError as exc:
        await client.aclose()
        pytest.skip(f"MongoDB not available for profile UI tests: {exc}")

    db = client[db_name]
    monkeypatch.setattr(database, "_client", client)
    monkeypatch.setattr(settings, "mongodb_db", db_name)
    await init_beanie(database=db, document_models=[User, QSO])
    try:
        yield db
    finally:
        await client.drop_database(db_name)
        await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def operator(profile_ui_db):
    user = User(
        username="profileop",
        hashed_password=hash_password("testpass"),
        callsign="W1AW",
    )
    await user.insert()
    return user


@pytest_asyncio.fixture(scope="function")
async def http_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _auth_cookie(user: User) -> dict:
    token = create_access_token(
        {"sub": user.username, "callsign": user.callsign, "role": user.role}
    )
    return {"Cookie": f"access_token={token}"}


@pytest.mark.asyncio
async def test_profile_update_invalid_tx_pwr_does_not_raise_without_mongo():
    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/log/profile",
        "headers": [],
    })
    user = User.model_construct(
        username="profileop",
        hashed_password=hash_password("testpass"),
        callsign="W1AW",
    )

    resp = await profile_update(request, user=user, tx_pwr="100W")

    assert resp.status_code == 200
    assert "TX power must be a number" in resp.body.decode()


@pytest.mark.asyncio
async def test_profile_update_full_form_builds_profile_updates(monkeypatch):
    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/log/profile",
        "headers": [],
    })
    user = User.model_construct(
        username="profileop",
        hashed_password=hash_password("testpass"),
        callsign="W1AW",
    )
    captured: dict = {}

    async def fake_update_profile(received_user: User, updates: dict) -> User:
        captured["user"] = received_user
        captured["updates"] = updates
        return received_user

    monkeypatch.setattr("app.qso.ui_router.update_profile", fake_update_profile)

    resp = await profile_update(
        request,
        user=user,
        station_callsign="K1ABC",
        name="Test Operator",
        my_gridsquare="fn31pr",
        tx_pwr="100",
        notify_sound="true",
        aclog_bridge_id=["new-0"],
        aclog_bridge_name=["Shack PC"],
        aclog_bridge_host=["127.0.0.1"],
        aclog_bridge_port=["1100"],
        aclog_bridge_enabled=["new-0"],
        **_default_custom_field_form(),
    )

    assert resp.status_code == 200
    assert "Profile updated successfully" in resp.body.decode()
    assert captured["user"] is user
    updates = captured["updates"]
    assert updates["station_callsign"] == "K1ABC"
    assert updates["name"] == "Test Operator"
    assert updates["my_gridsquare"] == "FN31PR"
    assert updates["tx_pwr"] == 100
    assert updates["notify_sound"] is True
    assert len(updates["aclog_bridges"]) == 1
    bridge = updates["aclog_bridges"][0]
    assert bridge["id"] != "new-0"
    assert bridge["name"] == "Shack PC"
    assert bridge["host"] == "127.0.0.1"
    assert bridge["port"] == 1100
    assert bridge["enabled"] is True
    assert len(updates["custom_qso_fields"]) == 8
    assert updates["custom_qso_fields"][0]["adif_name"] == "OTHER_1"


@pytest.mark.asyncio
async def test_profile_update_service_value_error_returns_htmx_error(monkeypatch):
    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/log/profile",
        "headers": [],
    })
    user = User.model_construct(
        username="profileop",
        hashed_password=hash_password("testpass"),
        callsign="W1AW",
    )

    async def fake_update_profile(received_user: User, updates: dict) -> User:
        raise ValueError("Duplicate custom ADIF field name: OTHER_1")

    monkeypatch.setattr("app.qso.ui_router.update_profile", fake_update_profile)

    resp = await profile_update(
        request,
        user=user,
        station_callsign="K1ABC",
        **_default_custom_field_form(),
    )

    assert resp.status_code == 200
    assert "Duplicate custom ADIF field name: OTHER_1" in resp.body.decode()


@pytest.mark.asyncio
async def test_profile_update_saves_operator_profile(http_client, operator, profile_ui_db):
    resp = await http_client.post(
        "/log/profile",
        headers=_auth_cookie(operator),
        data={
            "station_callsign": "K1ABC",
            "name": "Test Operator",
            "my_gridsquare": "FN31pr",
            "tx_pwr": "100",
            "notify_sound": "true",
        },
    )

    assert resp.status_code == 200
    assert "Profile updated successfully" in resp.text

    refreshed = await User.get(operator.id)
    assert refreshed is not None
    assert refreshed.station_callsign == "K1ABC"
    assert refreshed.name == "Test Operator"
    assert refreshed.my_gridsquare == "FN31PR"
    assert refreshed.tx_pwr == 100
    assert refreshed.notify_sound is True


@pytest.mark.asyncio
async def test_profile_update_invalid_tx_pwr_returns_htmx_error(
    http_client,
    operator,
    profile_ui_db,
):
    resp = await http_client.post(
        "/log/profile",
        headers=_auth_cookie(operator),
        data={"tx_pwr": "100W"},
    )

    assert resp.status_code == 200
    assert "TX power must be a number" in resp.text


@pytest.mark.asyncio
async def test_profile_page_renders_sync_only_for_saved_aclog_bridges(
    http_client,
    operator,
    profile_ui_db,
):
    operator.aclog_bridges = [
        ACLogBridge(
            id="bridge-1",
            name="Shack PC",
            host="127.0.0.1",
            port=1100,
            enabled=True,
        )
    ]
    await operator.save()

    resp = await http_client.get("/log/profile", headers=_auth_cookie(operator))

    assert resp.status_code == 200
    assert "Sync" in resp.text
    assert 'hx-post="/log/profile/aclog/bridge-1/sync"' in resp.text
    assert 'hx-target="#profile-result"' in resp.text
    assert "/log/profile/aclog/new-0/sync" not in resp.text


@pytest.mark.asyncio
async def test_profile_aclog_sync_unknown_bridge_returns_htmx_error(
    http_client,
    operator,
    profile_ui_db,
):
    resp = await http_client.post(
        "/log/profile/aclog/missing/sync",
        headers=_auth_cookie(operator),
    )

    assert resp.status_code == 200
    assert "ACLog bridge not found" in resp.text


@pytest.mark.asyncio
async def test_profile_aclog_sync_saved_bridge_renders_report(
    monkeypatch,
    http_client,
    operator,
    profile_ui_db,
):
    operator.aclog_bridges = [
        ACLogBridge(
            id="bridge-1",
            name="Shack PC",
            host="127.0.0.1",
            port=1100,
            enabled=True,
        )
    ]
    await operator.save()
    captured: dict[str, object] = {}

    async def fake_sync_aclog_bridge(user: User, bridge: ACLogBridge) -> ACLogSyncReport:
        captured["user"] = user
        captured["bridge"] = bridge
        return ACLogSyncReport(
            bridge_name=bridge.name,
            host=bridge.host,
            port=bridge.port,
            received=3,
            imported=1,
            skipped=2,
            skipped_missing_operator=1,
            skipped_unmatched_operator=1,
            errors=0,
        )

    monkeypatch.setattr("app.qso.ui_router.sync_aclog_bridge", fake_sync_aclog_bridge)

    resp = await http_client.post(
        "/log/profile/aclog/bridge-1/sync",
        headers=_auth_cookie(operator),
    )

    assert resp.status_code == 200
    assert "ACLog sync complete" in resp.text
    assert "Missing QSOs imported: 1" in resp.text
    assert "Already present: 2" in resp.text
    assert "Missing operator: 1" in resp.text
    assert "Unmatched operator: 1" in resp.text
    assert captured["bridge"].id == "bridge-1"
