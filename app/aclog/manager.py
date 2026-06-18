"""Background manager for all configured per-user ACLog bridges."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.aclog.client import ACLogBridgeRuntimeConfig, run_aclog_bridge
from app.auth.models import User
from app.internal_logs.service import app_logger

logger = logging.getLogger(__name__)


@dataclass
class _ManagedBridge:
    signature: tuple[str, int, str, bool]
    task: asyncio.Task


class ACLogBridgeManager:
    def __init__(self, scan_seconds: int, reconnect_seconds: int) -> None:
        self.scan_seconds = max(1, scan_seconds)
        self.reconnect_seconds = max(1, reconnect_seconds)
        self._bridges: dict[str, _ManagedBridge] = {}
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        for managed in self._bridges.values():
            managed.task.cancel()
        for managed in self._bridges.values():
            try:
                await managed.task
            except asyncio.CancelledError:
                pass
        self._bridges.clear()

    async def _run(self) -> None:
        while True:
            try:
                await self.reconcile()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("ACLog bridge reconciliation failed")
                await app_logger.error(
                    "ACLog bridge reconciliation failed",
                    source="app.aclog.manager",
                    event_type="bridge_reconcile_failed",
                    transport="bridge",
                    remote_software="ACLog",
                    exc=exc,
                )
            await asyncio.sleep(self.scan_seconds)

    async def reconcile(self) -> None:
        users = await User.find_all().to_list()
        desired: dict[str, tuple[ACLogBridgeRuntimeConfig, tuple[str, int, str, bool]]] = {}

        for user in users:
            if not user.enabled:
                continue
            for bridge in user.aclog_bridges:
                key = f"{user.id}:{bridge.id}"
                signature = (bridge.host, bridge.port, bridge.name, bridge.enabled)
                if bridge.enabled:
                    desired[key] = (
                        ACLogBridgeRuntimeConfig(
                            user_id=user.id,
                            bridge_id=bridge.id,
                            name=bridge.name,
                            host=bridge.host,
                            port=bridge.port,
                            reconnect_seconds=self.reconnect_seconds,
                        ),
                        signature,
                    )

        for key in set(self._bridges) - set(desired):
            await self._stop_bridge(key)

        for key, (config, signature) in desired.items():
            existing = self._bridges.get(key)
            if existing is not None and not existing.task.done() and existing.signature == signature:
                continue
            if existing is not None:
                await self._stop_bridge(key)
            task = asyncio.create_task(run_aclog_bridge(config))
            self._bridges[key] = _ManagedBridge(signature=signature, task=task)
            logger.info("ACLog bridge started: %s", config.label)
            await app_logger.info(
                "ACLog bridge task started",
                source="app.aclog.manager",
                event_type="bridge_task_started",
                transport="bridge",
                bridge_name=config.name,
                remote_software="ACLog",
                metadata={"bridge_id": config.bridge_id, "host": config.host, "port": config.port},
            )

    async def _stop_bridge(self, key: str) -> None:
        managed = self._bridges.pop(key, None)
        if managed is None:
            return
        managed.task.cancel()
        try:
            await managed.task
        except asyncio.CancelledError:
            pass
        logger.info("ACLog bridge stopped: %s", key)
        await app_logger.info(
            "ACLog bridge task stopped",
            source="app.aclog.manager",
            event_type="bridge_task_stopped",
            transport="bridge",
            remote_software="ACLog",
            metadata={"bridge_key": key},
        )
