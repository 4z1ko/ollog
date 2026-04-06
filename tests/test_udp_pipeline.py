"""Unit tests for the UDP QSO processing pipeline (_handle_datagram).

All tests are async, use pytest-asyncio, and mock MongoDB interactions so
no live database connection is required.

Patch targets use the module where names are resolved at call time because
_handle_datagram uses lazy imports inside the function body:
  - app.qso.service.find_duplicate  (resolved in app.qso.service namespace)
  - app.qso.models.QSO              (resolved in app.qso.models namespace)
  - app.adif.parser.parse_adi       (resolved in app.adif.parser namespace)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.auth.models import User
from app.udp.server import _handle_datagram

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SAMPLE_ADIF = (
    "<CALL:4>W1AW<BAND:3>20M<MODE:3>SSB"
    "<QSO_DATE:8>20260406<TIME_ON:4>1200<EOR>"
)
_ADDR = ("127.0.0.1", 9999)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def udp_user() -> User:
    """User constructed without DB (model_construct skips validation hooks)."""
    return User.model_construct(
        callsign="VK2ABC",
        username="vk2abc",
        hashed_password="x",
        role="operator",
        enabled=True,
        station_callsign="VK2ABC/P",
        my_gridsquare="QF56",
        my_rig=None,
        my_antenna=None,
        tx_pwr=None,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_datagram_inserts_qso(udp_user: User) -> None:
    """Valid datagram with operator configured results in QSO.insert() called."""
    mock_qso_instance = MagicMock()
    mock_qso_instance.insert = AsyncMock()
    mock_qso_instance.id = "abc123"

    mock_qso_class = MagicMock(return_value=mock_qso_instance)

    with (
        patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=None)),
        patch("app.qso.models.QSO", mock_qso_class),
    ):
        await _handle_datagram(
            _SAMPLE_ADIF.encode(),
            _ADDR,
            operator="VK2ABC",
            user=udp_user,
        )

    mock_qso_instance.insert.assert_awaited_once()
    _, kwargs = mock_qso_class.call_args
    assert kwargs.get("operator_callsign") == "VK2ABC" or (
        # build_qso_dict may pass as positional dict — check positional args too
        mock_qso_class.call_args[0]
        and mock_qso_class.call_args[0][0].get("operator_callsign") == "VK2ABC"
    )


@pytest.mark.asyncio
async def test_handle_datagram_profile_stamping(udp_user: User) -> None:
    """Profile fields are auto-stamped when user is provided."""
    captured: list[dict] = []

    def _capture_qso_dict(**kwargs: object) -> MagicMock:
        captured.append(kwargs)
        m = MagicMock()
        m.insert = AsyncMock()
        m.id = "stamp123"
        return m

    with (
        patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=None)),
        patch("app.qso.models.QSO", side_effect=_capture_qso_dict),
    ):
        await _handle_datagram(
            _SAMPLE_ADIF.encode(),
            _ADDR,
            operator="VK2ABC",
            user=udp_user,
        )

    assert len(captured) == 1
    qso_kwargs = captured[0]
    assert qso_kwargs.get("OPERATOR") == "VK2ABC"
    assert qso_kwargs.get("STATION_CALLSIGN") == "VK2ABC/P"
    assert qso_kwargs.get("MY_GRIDSQUARE") == "QF56"


@pytest.mark.asyncio
async def test_handle_datagram_missing_field_rejected(udp_user: User) -> None:
    """Datagram missing a required field (BAND) is rejected — QSO.insert not called."""
    adif_no_band = (
        "<CALL:4>W1AW<MODE:3>SSB"
        "<QSO_DATE:8>20260406<TIME_ON:4>1200<EOR>"
    )
    mock_qso_instance = MagicMock()
    mock_qso_instance.insert = AsyncMock()
    mock_qso_class = MagicMock(return_value=mock_qso_instance)

    with (
        patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=None)),
        patch("app.qso.models.QSO", mock_qso_class),
    ):
        await _handle_datagram(
            adif_no_band.encode(),
            _ADDR,
            operator="VK2ABC",
            user=udp_user,
        )

    mock_qso_instance.insert.assert_not_awaited()
    mock_qso_class.assert_not_called()


@pytest.mark.asyncio
async def test_handle_datagram_duplicate_skipped(udp_user: User) -> None:
    """Duplicate datagram (find_duplicate returns existing QSO) is skipped."""
    existing_qso = MagicMock()
    existing_qso.id = "dup123"

    mock_qso_instance = MagicMock()
    mock_qso_instance.insert = AsyncMock()
    mock_qso_class = MagicMock(return_value=mock_qso_instance)

    with (
        patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=existing_qso)),
        patch("app.qso.models.QSO", mock_qso_class),
    ):
        await _handle_datagram(
            _SAMPLE_ADIF.encode(),
            _ADDR,
            operator="VK2ABC",
            user=udp_user,
        )

    mock_qso_instance.insert.assert_not_awaited()
    mock_qso_class.assert_not_called()


@pytest.mark.asyncio
async def test_handle_datagram_operator_from_config_not_datagram(udp_user: User) -> None:
    """Operator attribution comes from config parameter, not ADIF datagram content."""
    # Datagram contains a different OPERATOR field value
    adif_with_operator = (
        "<CALL:4>W1AW<BAND:3>20M<MODE:3>SSB"
        "<QSO_DATE:8>20260406<TIME_ON:4>1200"
        "<OPERATOR:5>W1XXX<EOR>"
    )
    captured: list[dict] = []

    def _capture_qso_dict(**kwargs: object) -> MagicMock:
        captured.append(kwargs)
        m = MagicMock()
        m.insert = AsyncMock()
        m.id = "op123"
        return m

    with (
        patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=None)),
        patch("app.qso.models.QSO", side_effect=_capture_qso_dict),
    ):
        await _handle_datagram(
            adif_with_operator.encode(),
            _ADDR,
            operator="VK2ABC",
            user=udp_user,
        )

    assert len(captured) == 1
    qso_kwargs = captured[0]
    # operator_callsign must come from config ("VK2ABC"), not from ADIF ("W1XXX")
    assert qso_kwargs.get("operator_callsign") == "VK2ABC"
    # OPERATOR field is overwritten by profile stamping to profile.callsign
    assert qso_kwargs.get("OPERATOR") == "VK2ABC"


@pytest.mark.asyncio
async def test_handle_datagram_no_operator_configured() -> None:
    """When operator is None, datagram is discarded without calling QSO.insert."""
    mock_qso_instance = MagicMock()
    mock_qso_instance.insert = AsyncMock()
    mock_qso_class = MagicMock(return_value=mock_qso_instance)

    with (
        patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=None)),
        patch("app.qso.models.QSO", mock_qso_class),
    ):
        await _handle_datagram(
            _SAMPLE_ADIF.encode(),
            _ADDR,
            operator=None,
            user=None,
        )

    mock_qso_instance.insert.assert_not_awaited()
    mock_qso_class.assert_not_called()


@pytest.mark.asyncio
async def test_handle_datagram_no_records() -> None:
    """Datagram with no EOR tag yields no records — QSO.insert not called."""
    headeronly = b"some header text without any EOR tag"

    mock_qso_instance = MagicMock()
    mock_qso_instance.insert = AsyncMock()
    mock_qso_class = MagicMock(return_value=mock_qso_instance)

    with (
        patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=None)),
        patch("app.qso.models.QSO", mock_qso_class),
    ):
        await _handle_datagram(
            headeronly,
            _ADDR,
            operator="VK2ABC",
            user=None,
        )

    mock_qso_instance.insert.assert_not_awaited()
    mock_qso_class.assert_not_called()


@pytest.mark.asyncio
async def test_handle_datagram_exception_does_not_raise() -> None:
    """Unhandled exception inside _handle_datagram is caught — nothing propagates."""
    with patch("app.adif.parser.parse_adi", side_effect=RuntimeError("boom")):
        # Must not raise — exception is caught internally by the try/except block
        await _handle_datagram(
            _SAMPLE_ADIF.encode(),
            _ADDR,
            operator="VK2ABC",
            user=None,
        )
