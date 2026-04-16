"""Unit tests for watch_qsos watcher hardening (Phase 44).

Tests LIVE-01a (exception isolation), LIVE-01b (app.state strong reference),
LIVE-01c (null qso_date_utc does not kill watcher).

No live MongoDB connection required -- change stream is fully mocked.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.feed.manager import ConnectionManager, watch_qsos


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_collection(changes: list[dict]):
    """Build a mock AsyncCollection whose watch() yields the given change dicts."""
    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)

    async def _anext_impl(_self=None):
        if changes:
            return changes.pop(0)
        # Simulate an idle change stream — block until the task is cancelled.
        # Raising StopAsyncIteration here would cause watch_qsos to loop tight
        # (no actual yield) so task.cancel() would never be delivered.
        await asyncio.get_running_loop().create_future()

    mock_stream.__aiter__ = MagicMock(return_value=mock_stream)
    mock_stream.__anext__ = _anext_impl

    mock_collection = MagicMock()
    mock_collection.watch = AsyncMock(return_value=mock_stream)
    return mock_collection


# ---------------------------------------------------------------------------
# LIVE-01a: Exception isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_watcher_survives_render_exception():
    """LIVE-01a: render exception on change 1 does not kill watcher; change 2 broadcasts."""
    mgr = ConnectionManager()
    q = await mgr.connect()

    call_count = 0

    def _render_side_effect(ctx):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ValueError("simulated Jinja2 render error")
        return "<tr>ok</tr>"

    mock_template = MagicMock()
    mock_template.render.side_effect = _render_side_effect

    mock_templates = MagicMock()
    mock_templates.get_template.return_value = mock_template

    change1 = {"fullDocument": {"CALL": "W1AW", "BAND": "20M", "MODE": "FT8",
                                 "FREQ": "", "_operator": "VK2ABC", "qso_date_utc": None}}
    change2 = {"fullDocument": {"CALL": "VK2QQ", "BAND": "40M", "MODE": "SSB",
                                 "FREQ": "7.150", "_operator": "VK2ABC", "qso_date_utc": None}}

    collection = _make_mock_collection([change1, change2])

    task = asyncio.create_task(watch_qsos(collection, mgr, mock_templates))
    await asyncio.sleep(0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert call_count == 2, "render() must be called for both changes"
    assert q.get_nowait() == "<tr>ok</tr>", "second change must broadcast successfully"


# ---------------------------------------------------------------------------
# LIVE-01b: Strong reference in app.state
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_watcher_task_stored_in_app_state():
    """LIVE-01b: lifespan sets app.state.watcher_task unconditionally (not a local variable).

    httpx.ASGITransport (0.28+) does not trigger ASGI lifespan events, so we
    invoke the lifespan context manager directly with all external calls mocked.
    This tests the real behaviour (attribute is set) without requiring MongoDB.
    """
    import app.main as _main
    from app.main import app

    with (
        patch.object(_main, "init_db", new=AsyncMock()),
        patch.object(_main, "_bootstrap_admin", new=AsyncMock()),
        patch.object(_main, "get_client", return_value=None),
        patch.object(_main, "close_db", new=AsyncMock()),
        patch("app.main.settings") as mock_settings,
    ):
        mock_settings.udp_enabled = False
        mock_settings.backup_schedule = None

        async with _main.lifespan(app):
            assert hasattr(app.state, "watcher_task"), \
                "app.state.watcher_task must exist after startup (even when client is None)"
            # client is None in this mock — watcher_task stays None
            assert app.state.watcher_task is None


# ---------------------------------------------------------------------------
# LIVE-01c: Null qso_date_utc
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_watcher_null_date_does_not_kill():
    """LIVE-01c: qso_date_utc=None in a change doc does not propagate an exception."""
    mgr = ConnectionManager()
    q = await mgr.connect()

    mock_template = MagicMock()
    mock_template.render.return_value = "<tr>null-date-ok</tr>"
    mock_templates = MagicMock()
    mock_templates.get_template.return_value = mock_template

    change = {"fullDocument": {"CALL": "W1AW", "BAND": "20M", "MODE": "SSB",
                                "FREQ": "", "_operator": "VK2ABC", "qso_date_utc": None}}
    collection = _make_mock_collection([change])

    task = asyncio.create_task(watch_qsos(collection, mgr, mock_templates))
    await asyncio.sleep(0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert q.get_nowait() == "<tr>null-date-ok</tr>"
