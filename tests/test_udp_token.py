"""Tests for per-datagram operator identity resolution via APP_OLLOG_TOKEN.

Covers UDP-01 (valid token overrides UDP_OPERATOR), UDP-02 (invalid/revoked
token is rejected with no fallthrough to UDP_OPERATOR), and UDP-03 (no token
uses UDP_OPERATOR unchanged — existing behaviour preserved).

Patch target: app.udp.token_cache.token_cache
  _handle_datagram uses a lazy import to the module singleton, so patching the
  singleton directly (not the class) is the correct approach — see test_udp_pipeline.py
  for the same pattern with QSO and find_duplicate.
"""
from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.auth.models import User
from app.udp.server import _handle_datagram

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SAMPLE_ADIF_BASE = (
    "<CALL:4>W1AW<BAND:3>20M<MODE:3>SSB"
    "<QSO_DATE:8>20260406<TIME_ON:4>1200<EOR>"
)

_SAMPLE_ADIF_WITH_TOKEN = (
    "<CALL:4>W1AW<BAND:3>20M<MODE:3>SSB"
    "<QSO_DATE:8>20260406<TIME_ON:4>1200"
    "<APP_OLLOG_TOKEN:20>ollog_testtoken12345<EOR>"
)

_ADDR = ("127.0.0.1", 9999)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def token_user() -> User:
    """User returned by token_cache.resolve() — the token owner."""
    return User.model_construct(
        callsign="VK3XYZ",
        username="vk3xyz",
        hashed_password="x",
        role="operator",
        enabled=True,
        station_callsign="VK3XYZ/P",
        my_gridsquare="QF22",
        my_rig=None,
        my_antenna=None,
        tx_pwr=None,
    )


@pytest.fixture
def fallback_user() -> User:
    """User representing the UDP_OPERATOR fallback."""
    return User.model_construct(
        callsign="VK2ABC",
        username="vk2abc",
        hashed_password="x",
        role="operator",
        enabled=True,
        station_callsign=None,
        my_gridsquare=None,
        my_rig=None,
        my_antenna=None,
        tx_pwr=None,
    )


# ---------------------------------------------------------------------------
# Tests — UDP-01: valid token overrides UDP_OPERATOR
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_token_overrides_udp_operator(token_user: User, fallback_user: User) -> None:
    """UDP-01: valid APP_OLLOG_TOKEN causes QSO to be logged under the token owner's callsign.

    The token_cache.resolve() returns token_user (VK3XYZ), not the fallback UDP_OPERATOR.
    operator_callsign in the inserted QSO must be VK3XYZ, not VK2ABC.
    """
    captured: list[dict] = []

    def _capture_qso_dict(**kwargs: object) -> MagicMock:
        captured.append(kwargs)
        m = MagicMock()
        m.insert = AsyncMock()
        m.id = "token_qso_001"
        return m

    with patch("app.udp.token_cache.token_cache") as mock_cache:
        mock_cache.resolve = AsyncMock(return_value=token_user)
        with (
            patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=None)),
            patch("app.qso.models.QSO", side_effect=_capture_qso_dict),
        ):
            await _handle_datagram(
                _SAMPLE_ADIF_WITH_TOKEN.encode(),
                _ADDR,
                operator="VK2ABC",   # UDP_OPERATOR fallback — should be overridden
                user=fallback_user,
            )

    assert len(captured) == 1, "Expected exactly one QSO to be constructed"
    qso_kwargs = captured[0]
    # Operator must come from token_user, not from the UDP_OPERATOR "VK2ABC"
    assert qso_kwargs.get("operator_callsign") == "VK3XYZ"
    # APP_OLLOG_TOKEN must NOT appear in the QSO document
    assert "APP_OLLOG_TOKEN" not in qso_kwargs


# ---------------------------------------------------------------------------
# Tests — UDP-02: invalid/revoked token is rejected, no fallthrough
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_token_rejected_no_fallthrough(fallback_user: User) -> None:
    """UDP-02: invalid APP_OLLOG_TOKEN rejects the datagram — QSO.insert is NOT called."""
    mock_qso_insert = AsyncMock()
    mock_qso_class = MagicMock(return_value=MagicMock(insert=mock_qso_insert, id="never"))

    with patch("app.udp.token_cache.token_cache") as mock_cache:
        mock_cache.resolve = AsyncMock(return_value=None)   # invalid/revoked
        with (
            patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=None)),
            patch("app.qso.models.QSO", mock_qso_class),
        ):
            await _handle_datagram(
                _SAMPLE_ADIF_WITH_TOKEN.encode(),
                _ADDR,
                operator="VK2ABC",
                user=fallback_user,
            )

    # Must NOT fall through to UDP_OPERATOR — insert must never be called
    mock_qso_insert.assert_not_awaited()
    mock_qso_class.assert_not_called()


# ---------------------------------------------------------------------------
# Tests — UDP-03: no token uses UDP_OPERATOR unchanged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_token_uses_udp_operator(fallback_user: User) -> None:
    """UDP-03: datagram without APP_OLLOG_TOKEN uses UDP_OPERATOR unchanged.

    token_cache.resolve() must NOT be called when the field is absent.
    The QSO operator_callsign must equal the UDP_OPERATOR fallback callsign.
    """
    captured: list[dict] = []

    def _capture_qso_dict(**kwargs: object) -> MagicMock:
        captured.append(kwargs)
        m = MagicMock()
        m.insert = AsyncMock()
        m.id = "fallback_qso_001"
        return m

    with patch("app.udp.token_cache.token_cache") as mock_cache:
        mock_cache.resolve = AsyncMock()  # should not be called
        with (
            patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=None)),
            patch("app.qso.models.QSO", side_effect=_capture_qso_dict),
        ):
            await _handle_datagram(
                _SAMPLE_ADIF_BASE.encode(),   # no APP_OLLOG_TOKEN field
                _ADDR,
                operator="VK2ABC",
                user=fallback_user,
            )

    # resolve() must NOT have been called for a no-token datagram
    mock_cache.resolve.assert_not_called()

    assert len(captured) == 1, "Expected exactly one QSO constructed for no-token datagram"
    qso_kwargs = captured[0]
    assert qso_kwargs.get("operator_callsign") == "VK2ABC"


# ---------------------------------------------------------------------------
# Tests — Token field never reaches QSO document
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_not_stored_in_qso_document(token_user: User, fallback_user: User) -> None:
    """APP_OLLOG_TOKEN is consumed (pop'd) before build_qso_dict — never stored in MongoDB."""
    captured_kwargs: dict = {}

    def _capture(**kwargs: object) -> MagicMock:
        captured_kwargs.update(kwargs)
        m = MagicMock()
        m.insert = AsyncMock()
        m.id = "no_token_leak_001"
        return m

    with patch("app.udp.token_cache.token_cache") as mock_cache:
        mock_cache.resolve = AsyncMock(return_value=token_user)
        with (
            patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=None)),
            patch("app.qso.models.QSO", side_effect=_capture),
        ):
            await _handle_datagram(
                _SAMPLE_ADIF_WITH_TOKEN.encode(),
                _ADDR,
                operator="VK2ABC",
                user=fallback_user,
            )

    # Check all QSO kwarg keys — neither the original nor any case variant must appear
    for key in captured_kwargs:
        assert key.upper() != "APP_OLLOG_TOKEN", (
            f"APP_OLLOG_TOKEN leaked into QSO document as key={key!r}"
        )


# ---------------------------------------------------------------------------
# Tests — Rejection log format (structured key=value pairs)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_token_rejected_log_format(
    caplog: pytest.LogCaptureFixture, fallback_user: User
) -> None:
    """UDP-02: rejected datagram produces exactly one WARNING with structured log format.

    Checks that disposition=rejected, reason=invalid-token, and src=127.0.0.1:9999
    all appear in the warning record from the app.udp.server logger.
    """
    with patch("app.udp.token_cache.token_cache") as mock_cache:
        mock_cache.resolve = AsyncMock(return_value=None)
        with caplog.at_level(logging.WARNING, logger="app.udp.server"):
            with (
                patch("app.qso.service.find_duplicate", new=AsyncMock(return_value=None)),
                patch("app.qso.models.QSO", MagicMock()),
            ):
                await _handle_datagram(
                    _SAMPLE_ADIF_WITH_TOKEN.encode(),
                    _ADDR,
                    operator="VK2ABC",
                    user=fallback_user,
                )

    warning_records = [
        r
        for r in caplog.records
        if r.levelno == logging.WARNING and r.name == "app.udp.server"
    ]
    assert len(warning_records) == 1, (
        f"Expected exactly 1 WARNING from app.udp.server, got {len(warning_records)}: "
        f"{[r.message for r in warning_records]}"
    )
    msg = warning_records[0].message
    assert "disposition=rejected" in msg
    assert "reason=invalid-token" in msg
    assert "src=127.0.0.1:9999" in msg
