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

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.auth.models import User
from app.udp.server import QSODatagramProtocol, _handle_datagram

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
async def test_handle_datagram_operator_field_resolves_user_override(udp_user: User) -> None:
    """An ADIF OPERATOR field can resolve the target user for collection routing."""
    adif_with_operator = (
        "<CALL:4>W1AW<BAND:3>20M<MODE:3>SSB"
        "<QSO_DATE:8>20260406<TIME_ON:4>1200"
        "<OPERATOR:5>W1XXX<EOR>"
    )
    override_user = User.model_construct(
        callsign="W1XXX",
        username="w1xxx",
        hashed_password="x",
        role="operator",
        enabled=True,
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
        patch("app.udp.operator_cache.operator_cache.resolve", new=AsyncMock(return_value=override_user)),
    ):
        await _handle_datagram(
            adif_with_operator.encode(),
            _ADDR,
            operator="VK2ABC",
            user=udp_user,
        )

    assert len(captured) == 1
    qso_kwargs = captured[0]
    assert qso_kwargs.get("operator_callsign") == "W1XXX"
    assert qso_kwargs.get("OPERATOR") == "W1XXX"


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


# ---------------------------------------------------------------------------
# Caplog tests: structured log assertions (OBS-01 through OBS-04)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_accepted_datagram_log(caplog, udp_user):
    """Accepted datagram produces INFO log with disposition=accepted, src, call."""
    mock_qso = MagicMock()
    mock_qso.insert = AsyncMock()
    mock_qso.id = "abc123"
    with caplog.at_level(logging.INFO, logger="app.udp.server"):
        with (
            patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=None)),
            patch("app.qso.models.QSO", return_value=mock_qso),
        ):
            await _handle_datagram(
                _SAMPLE_ADIF.encode(), _ADDR, operator="VK2ABC", user=udp_user,
            )
    assert "disposition=accepted" in caplog.text
    assert "src=127.0.0.1:9999" in caplog.text
    assert "call=W1AW" in caplog.text
    info_records = [r for r in caplog.records if r.levelno == logging.INFO and "disposition=accepted" in r.message]
    assert len(info_records) == 1


@pytest.mark.asyncio
async def test_rejected_missing_field_log(caplog, udp_user):
    """Datagram missing required field produces WARNING with disposition=rejected and reason."""
    adif_no_band = "<CALL:4>W1AW<MODE:3>SSB<QSO_DATE:8>20260406<TIME_ON:4>1200<EOR>"
    with caplog.at_level(logging.WARNING, logger="app.udp.server"):
        await _handle_datagram(
            adif_no_band.encode(), _ADDR, operator="VK2ABC", user=udp_user,
        )
    assert "disposition=rejected" in caplog.text
    assert "missing required field" in caplog.text
    assert "src=127.0.0.1:9999" in caplog.text
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING and r.name == "app.udp.server"]
    assert len(warning_records) == 1


@pytest.mark.asyncio
async def test_duplicate_datagram_log(caplog, udp_user):
    """Duplicate datagram produces INFO log with disposition=duplicate, src, call."""
    existing = MagicMock()
    existing.id = "dup123"
    with caplog.at_level(logging.INFO, logger="app.udp.server"):
        with (
            patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=existing)),
            patch("app.qso.models.QSO", MagicMock()),
        ):
            await _handle_datagram(
                _SAMPLE_ADIF.encode(), _ADDR, operator="VK2ABC", user=udp_user,
            )
    assert "disposition=duplicate" in caplog.text
    assert "call=W1AW" in caplog.text
    assert "src=127.0.0.1:9999" in caplog.text
    info_records = [r for r in caplog.records if r.levelno == logging.INFO and "disposition=duplicate" in r.message]
    assert len(info_records) == 1


@pytest.mark.asyncio
async def test_garbage_datagram_single_warning_no_crash(caplog, udp_user):
    """Binary garbage input produces exactly one WARNING and does not crash."""
    with caplog.at_level(logging.WARNING, logger="app.udp.server"):
        await _handle_datagram(
            b"\x00\xFF\xFE\xAB garbage bytes",
            _ADDR,
            operator="VK2ABC",
            user=udp_user,
        )
    warning_records = [
        r for r in caplog.records
        if r.levelno >= logging.WARNING and r.name == "app.udp.server"
    ]
    assert len(warning_records) == 1, f"Expected 1 WARNING, got {len(warning_records)}: {[r.message for r in warning_records]}"
    assert "disposition=rejected" in caplog.text


@pytest.mark.asyncio
async def test_error_received_logs_warning_and_continues(caplog):
    """QSODatagramProtocol.error_received() logs WARNING and protocol continues."""
    protocol = QSODatagramProtocol(operator="VK2ABC", user=None)
    with caplog.at_level(logging.WARNING, logger="app.udp.server"):
        protocol.error_received(OSError("ICMP unreachable"))
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING and r.name == "app.udp.server"]
    assert len(warning_records) == 1
    assert "ICMP unreachable" in caplog.text
    # Protocol has not stopped — transport is still None (never connected) which is fine;
    # the key assertion is that no exception was raised and no transport.close() was called
    assert protocol.transport is None
