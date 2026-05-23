"""Async TCP client for one ACLog bridge."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from beanie import PydanticObjectId

from app.aclog.parser import aclog_enterevent_to_adif, parse_cmd
from app.auth.models import User
from app.qso.service import ingest_qso_record

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ACLogBridgeRuntimeConfig:
    user_id: PydanticObjectId
    bridge_id: str
    name: str
    host: str
    port: int
    reconnect_seconds: int

    @property
    def label(self) -> str:
        name = self.name or self.bridge_id
        return f"{name} ({self.host}:{self.port})"


async def run_aclog_bridge(config: ACLogBridgeRuntimeConfig) -> None:
    """Keep one ACLog TCP connection alive and ingest ENTEREVENT messages."""
    while True:
        try:
            logger.info("ACLog bridge connecting: %s", config.label)
            reader, writer = await asyncio.open_connection(config.host, config.port)
            logger.info("ACLog bridge connected: %s", config.label)

            try:
                while True:
                    raw = await reader.readline()
                    if not raw:
                        logger.warning("ACLog bridge disconnected: %s", config.label)
                        break

                    message = raw.decode("utf-8", errors="replace").strip()
                    if message:
                        await _handle_message(config, message)
            finally:
                writer.close()
                await writer.wait_closed()

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("ACLog bridge error %s: %s", config.label, exc)

        await asyncio.sleep(max(1, config.reconnect_seconds))


async def _handle_message(config: ACLogBridgeRuntimeConfig, message: str) -> None:
    command, fields = parse_cmd(message)
    if command != "ENTEREVENT":
        return

    user = await User.get(config.user_id)
    if user is None or not user.enabled:
        logger.warning("ACLog bridge %s skipped QSO: user unavailable", config.label)
        return

    record = aclog_enterevent_to_adif(fields)
    result = await ingest_qso_record(
        record=record,
        operator=user.callsign,
        profile=user,
        source=f"aclog:{config.bridge_id}",
    )
    logger.info(
        "ACLog bridge %s call=%s disposition=%s",
        config.label,
        record.get("CALL", "?"),
        result["status"],
    )
