"""Integration tests for Profile API (GET and PATCH /api/profile)."""

import pytest
import pytest_asyncio
from beanie import init_beanie
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient

from app.auth.models import User
from app.auth.service import create_access_token, hash_password
from app.main import app
from app.qso.models import QSO


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def profile_db():
    client = AsyncMongoClient(
        "mongodb://localhost:27017", serverSelectionTimeoutMS=2000, directConnection=True
    )
    db = client["ollog_profile_test"]
    await init_beanie(database=db, document_models=[User, QSO])
    yield db
    await client.drop_database("ollog_profile_test")
    await client.aclose()


@pytest_asyncio.fixture(scope="function")
async def operator(profile_db):
    user = User(
        username="testop",
        hashed_password=hash_password("testpass"),
        callsign="W1AW",
    )
    await user.insert()
    return user


@pytest_asyncio.fixture(scope="function")
async def operator_token(operator):
    return create_access_token({"sub": operator.username})


@pytest_asyncio.fixture(scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_profile_empty(client, operator, operator_token):
    """GET /api/profile for operator with no profile fields set returns 200 with null optional fields."""
    resp = await client.get(
        "/api/profile/",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["callsign"] == "W1AW"
    # All optional fields should be null
    for field in [
        "station_callsign", "name", "email", "qth", "state", "country",
        "my_gridsquare", "latitude", "longitude", "my_rig", "my_antenna", "tx_pwr",
    ]:
        assert data[field] is None, f"Expected {field} to be null, got {data[field]!r}"
    assert data["notify_sound"] is False


@pytest.mark.asyncio
async def test_patch_profile_basic(client, operator, operator_token):
    """PATCH /api/profile with name and qth updates the fields and persists them."""
    headers = {"Authorization": f"Bearer {operator_token}"}

    resp = await client.patch(
        "/api/profile/",
        json={"name": "Test Op", "qth": "Boston"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Op"
    assert data["qth"] == "Boston"

    # Verify persistence via GET
    get_resp = await client.get("/api/profile/", headers=headers)
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["name"] == "Test Op"
    assert get_data["qth"] == "Boston"


@pytest.mark.asyncio
async def test_patch_profile_grid_computes_latlon(client, operator, operator_token):
    """PATCH with my_gridsquare auto-computes latitude and longitude from grid center."""
    headers = {"Authorization": f"Bearer {operator_token}"}

    resp = await client.patch(
        "/api/profile/",
        json={"my_gridsquare": "FN31pr"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["my_gridsquare"] == "FN31PR"
    assert data["latitude"] is not None
    assert data["longitude"] is not None
    assert isinstance(data["latitude"], float)
    assert isinstance(data["longitude"], float)
    # FN31pr center is approximately 41.7N, -72.4W
    assert data["latitude"] == pytest.approx(41.7, abs=1.0)
    assert data["longitude"] == pytest.approx(-72.4, abs=1.0)


@pytest.mark.asyncio
async def test_patch_profile_clear_grid_clears_latlon(client, operator, operator_token):
    """PATCH my_gridsquare to null clears latitude and longitude."""
    headers = {"Authorization": f"Bearer {operator_token}"}

    # First set a grid
    await client.patch(
        "/api/profile/",
        json={"my_gridsquare": "FN31pr"},
        headers=headers,
    )

    # Then clear it
    resp = await client.patch(
        "/api/profile/",
        json={"my_gridsquare": None},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["my_gridsquare"] is None
    assert data["latitude"] is None
    assert data["longitude"] is None


@pytest.mark.asyncio
async def test_patch_profile_partial_update(client, operator, operator_token):
    """Two sequential PATCHes each only update their own fields — no field erasure."""
    headers = {"Authorization": f"Bearer {operator_token}"}

    await client.patch("/api/profile/", json={"name": "First"}, headers=headers)
    await client.patch("/api/profile/", json={"qth": "NYC"}, headers=headers)

    get_resp = await client.get("/api/profile/", headers=headers)
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["name"] == "First"
    assert data["qth"] == "NYC"


@pytest.mark.asyncio
async def test_get_profile_no_auth(client):
    """GET /api/profile without Authorization header returns 401."""
    resp = await client.get("/api/profile/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_operator_isolation(client, operator, operator_token, profile_db):
    """Each operator only sees their own profile — JWT scoping enforced."""
    # Create a second operator
    user2 = User(
        username="testop2",
        hashed_password=hash_password("testpass2"),
        callsign="K1ABC",
    )
    await user2.insert()
    token2 = create_access_token({"sub": "testop2"})

    # Second operator's GET should return their own callsign, not W1AW
    resp = await client.get(
        "/api/profile/",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["callsign"] == "K1ABC"
    assert data["callsign"] != "W1AW"


@pytest.mark.asyncio
async def test_patch_invalid_grid_rejected(client, operator, operator_token):
    """PATCH with an invalid my_gridsquare value returns 422 (schema validation error)."""
    resp = await client.patch(
        "/api/profile/",
        json={"my_gridsquare": "99ZZ"},
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_notify_sound_default_false(client, operator, operator_token):
    """SND-03: notify_sound is False for a new operator."""
    resp = await client.get(
        "/api/profile/",
        headers={"Authorization": f"Bearer {operator_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["notify_sound"] is False


@pytest.mark.asyncio
async def test_notify_sound_patch_true(client, operator, operator_token):
    """SND-05: patching notify_sound=True persists and is readable."""
    headers = {"Authorization": f"Bearer {operator_token}"}
    resp = await client.patch(
        "/api/profile/",
        json={"notify_sound": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["notify_sound"] is True
    # Verify persistence via GET
    get_resp = await client.get("/api/profile/", headers=headers)
    assert get_resp.json()["notify_sound"] is True


@pytest.mark.asyncio
async def test_notify_sound_patch_false(client, operator, operator_token):
    """SND-05: patching notify_sound=False after True persists correctly."""
    headers = {"Authorization": f"Bearer {operator_token}"}
    await client.patch(
        "/api/profile/",
        json={"notify_sound": True},
        headers=headers,
    )
    resp = await client.patch(
        "/api/profile/",
        json={"notify_sound": False},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["notify_sound"] is False
