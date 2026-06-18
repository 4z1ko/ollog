"""Async TCP client for one ACLog bridge."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Protocol

from beanie import PydanticObjectId

from app.aclog.identity import match_aclog_operator_identity
from app.aclog.parser import (
    aclog_enterevent_to_adif,
    aclog_full_record_to_adif,
    aclog_full_records_from_message,
    aclog_records_match,
    iter_cmd_messages,
    is_aclog_full_record_response,
    merge_aclog_records,
    parse_cmd,
    update_state_from_message,
)
from app.auth.models import User
from app.internal_logs.service import app_logger
from app.qso.custom_fields import custom_fields_for_user
from app.qso.service import ingest_qso_record

logger = logging.getLogger(__name__)

ACLOG_FULL_RECORD_DELAY_SECONDS = 0.25
ACLOG_FULL_RECORD_RECENT_COUNT = 5


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


@dataclass(frozen=True)
class _PendingACLogEvent:
    record: dict[str, str]


class _ACLogWriter(Protocol):
    def write(self, data: bytes) -> None:
        ...

    async def drain(self) -> None:
        ...


async def run_aclog_bridge(config: ACLogBridgeRuntimeConfig) -> None:
    """Keep one ACLog TCP connection alive and ingest ENTEREVENT messages."""
    while True:
        try:
            logger.info("ACLog bridge connecting: %s", config.label)
            await app_logger.info(
                "ACLog bridge connecting",
                source="app.aclog.client",
                event_type="bridge_connecting",
                transport="bridge",
                bridge_name=config.name,
                remote_software="ACLog",
                metadata={"bridge_id": config.bridge_id, "host": config.host, "port": config.port},
            )
            reader, writer = await asyncio.open_connection(config.host, config.port)
            logger.info("ACLog bridge connected: %s", config.label)
            await app_logger.info(
                "ACLog bridge connected",
                source="app.aclog.client",
                event_type="bridge_connected",
                transport="bridge",
                bridge_name=config.name,
                remote_software="ACLog",
                metadata={"bridge_id": config.bridge_id, "host": config.host, "port": config.port},
            )
            state: dict[str, str] = {}
            pending: _PendingACLogEvent | None = None
            await _initialize_connection(writer)

            try:
                while True:
                    raw = await reader.readline()
                    if not raw:
                        if pending is not None:
                            _log_aclog_skip(
                                config,
                                pending.record,
                                "missing",
                                "ACLog disconnected before full record identity was available",
                            )
                            pending = None
                        logger.warning("ACLog bridge disconnected: %s", config.label)
                        await app_logger.warn(
                            "ACLog bridge disconnected",
                            source="app.aclog.client",
                            event_type="bridge_disconnected",
                            transport="bridge",
                            bridge_name=config.name,
                            remote_software="ACLog",
                            metadata={"bridge_id": config.bridge_id},
                        )
                        break

                    raw_message = raw.decode("utf-8", errors="replace").strip()
                    for message in iter_cmd_messages(raw_message):
                        pending = await _handle_message(
                            config,
                            message,
                            state,
                            writer=writer,
                            pending=pending,
                        )
            finally:
                writer.close()
                await writer.wait_closed()

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("ACLog bridge error %s: %s", config.label, exc)
            await app_logger.warn(
                "ACLog bridge error; reconnect will be attempted",
                source="app.aclog.client",
                event_type="bridge_reconnect_scheduled",
                transport="bridge",
                bridge_name=config.name,
                remote_software="ACLog",
                metadata={
                    "bridge_id": config.bridge_id,
                    "reconnect_seconds": config.reconnect_seconds,
                },
                exc=exc,
            )

        await asyncio.sleep(max(1, config.reconnect_seconds))


async def _initialize_connection(writer: asyncio.StreamWriter) -> None:
    """Ask ACLog for live textbox updates and current band/mode/frequency."""
    for command in [
        "<CMD><SETUPDATESTATE><VALUE>TRUE</VALUE></CMD>\r\n",
        "<CMD><READBMF></CMD>\r\n",
        "<CMD><GETUSERSETTINGS></CMD>\r\n",
        "<CMD><GETOTHERFIELDTITLES></CMD>\r\n",
    ]:
        writer.write(command.encode("utf-8"))
    await writer.drain()


async def _handle_message(
    config: ACLogBridgeRuntimeConfig,
    message: str,
    state: dict[str, str],
    *,
    writer: _ACLogWriter | None = None,
    pending: _PendingACLogEvent | None = None,
) -> _PendingACLogEvent | None:
    command, fields = parse_cmd(message)
    update_state_from_message(command, fields, state)

    if command == "ENTEREVENT":
        if pending is not None:
            _log_aclog_skip(
                config,
                pending.record,
                "missing",
                "new ACLog event arrived before previous full record identity was available",
            )

        record = aclog_enterevent_to_adif(fields, state=state)
        if writer is None:
            await _ingest_aclog_record(
                config,
                record,
                setup_station_call=state.get("ACLOG_SETUP_CALL"),
            )
            return None

        await _request_full_record(writer)
        return _PendingACLogEvent(record=record)

    if pending is None:
        return None

    if not is_aclog_full_record_response(command, fields):
        return pending

    _, full_records = aclog_full_records_from_message(message)
    if not full_records:
        full_records = [aclog_full_record_to_adif(fields)]

    full_record = next(
        (
            candidate
            for candidate in full_records
            if candidate and aclog_records_match(pending.record, candidate)
        ),
        None,
    )
    if full_record is None:
        _log_aclog_skip(
            config,
            pending.record,
            "missing",
            "no matching full ACLog record with operator identity",
        )
        return None

    record = merge_aclog_records(pending.record, full=full_record, state=state)
    await _ingest_aclog_record(
        config,
        record,
        setup_station_call=state.get("ACLOG_SETUP_CALL"),
    )
    return None


async def _request_full_record(writer: _ACLogWriter) -> None:
    await asyncio.sleep(ACLOG_FULL_RECORD_DELAY_SECONDS)
    writer.write(
        f"<CMD><LIST><INCLUDEALL><VALUE>{ACLOG_FULL_RECORD_RECENT_COUNT}</VALUE></CMD>\r\n".encode(
            "utf-8"
        )
    )
    await writer.drain()


async def _ingest_aclog_record(
    config: ACLogBridgeRuntimeConfig,
    record: dict[str, str],
    *,
    setup_station_call: str | None = None,
) -> None:
    user = await User.get(config.user_id)
    if user is None or not user.enabled:
        logger.warning("ACLog bridge %s skipped QSO: user unavailable", config.label)
        await app_logger.warn(
            "ACLog bridge skipped QSO because user is unavailable",
            source="app.aclog.client",
            event_type="bridge_qso_skipped",
            transport="bridge",
            bridge_name=config.name,
            remote_software="ACLog",
            metadata={"bridge_id": config.bridge_id, "reason": "user_unavailable"},
        )
        return

    identity = match_aclog_operator_identity(
        record,
        user,
        setup_station_call=setup_station_call,
    )
    if not identity.matched:
        detail = (
            "missing ACLog station/operator identity"
            if identity.disposition == "missing"
            else f"expected={identity.expected} {identity.field}={identity.value}"
        )
        _log_aclog_skip(config, record, identity.disposition, detail)
        return

    record = _map_other_slots_to_custom_fields(record, user)
    from app.qso.collections import get_user_qso_collection

    result = await ingest_qso_record(
        record=record,
        operator=user.callsign,
        profile=user,
        source=f"aclog:{config.bridge_id}",
        collection=get_user_qso_collection(user),
    )
    logger.info(
        "ACLog bridge %s call=%s identity_field=%s identity_value=%s disposition=%s",
        config.label,
        record.get("CALL", "?"),
        identity.field,
        identity.value,
        result["status"],
    )
    await app_logger.info(
        "ACLog bridge QSO processed",
        source="app.aclog.client",
        event_type="bridge_qso_processed",
        transport="bridge",
        qso_id=result.get("id") or result.get("existing_id"),
        bridge_name=config.name,
        remote_software="ACLog",
        metadata={
            "bridge_id": config.bridge_id,
            "call": record.get("CALL"),
            "identity_field": identity.field,
            "identity_value": identity.value,
            "status": result["status"],
        },
    )


def _log_aclog_skip(
    config: ACLogBridgeRuntimeConfig,
    record: dict[str, str],
    disposition: str,
    detail: str,
) -> None:
    logger.info(
        "ACLog bridge %s call=%s skipped=%s reason=%s",
        config.label,
        record.get("CALL", "?"),
        disposition,
        detail,
    )
    asyncio.create_task(
        app_logger.warn(
            "ACLog bridge skipped QSO",
            source="app.aclog.client",
            event_type="bridge_qso_skipped",
            transport="bridge",
            bridge_name=config.name,
            remote_software="ACLog",
            metadata={
                "bridge_id": config.bridge_id,
                "call": record.get("CALL"),
                "disposition": disposition,
                "reason": detail,
            },
        )
    )


def _map_other_slots_to_custom_fields(record: dict[str, str], user: User) -> dict[str, str]:
    mapped = dict(record)
    for field in custom_fields_for_user(user):
        slot_key = f"OTHER_{field.slot}"
        if slot_key in mapped and field.adif_name != slot_key:
            mapped[field.adif_name] = mapped.pop(slot_key)
    return mapped
