"""Manual ACLog bridge synchronization helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.aclog.parser import aclog_full_records_from_message, iter_cmd_messages
from app.auth.models import ACLogBridge, User
from app.qso.collections import get_user_qso_collection
from app.qso.service import ingest_qso_record

ACLOG_SYNC_COMMAND = "<CMD><LIST><INCLUDEALL></CMD>\r\n"
ACLOG_SYNC_TIMEOUT_SECONDS = 15.0
ACLOG_SYNC_EXAMPLE_LIMIT = 5


@dataclass
class ACLogSyncReport:
    bridge_name: str
    host: str
    port: int
    received: int = 0
    imported: int = 0
    skipped: int = 0
    errors: int = 0
    examples: list[dict[str, str]] = field(default_factory=list)
    failure_reason: str | None = None

    @property
    def failed(self) -> bool:
        return self.failure_reason is not None


async def sync_aclog_bridge(
    user: User,
    bridge: ACLogBridge,
    *,
    timeout: float = ACLOG_SYNC_TIMEOUT_SECONDS,
) -> ACLogSyncReport:
    """Fetch all ACLog records from one saved bridge and import missing QSOs."""
    report = ACLogSyncReport(
        bridge_name=bridge.name or bridge.host,
        host=bridge.host,
        port=bridge.port,
    )
    writer: Any | None = None

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(bridge.host, bridge.port),
            timeout=timeout,
        )
        writer.write(ACLOG_SYNC_COMMAND.encode("utf-8"))
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        raw = await _read_cmd_response(reader, timeout)
    except (OSError, asyncio.TimeoutError) as exc:
        report.failure_reason = str(exc) or exc.__class__.__name__
        return report
    finally:
        if writer is not None:
            writer.close()
            wait_closed = getattr(writer, "wait_closed", None)
            if wait_closed is not None:
                try:
                    await wait_closed()
                except OSError:
                    pass

    records: list[dict[str, str]] = []
    payload = raw.decode("utf-8", errors="replace")
    for message in iter_cmd_messages(payload):
        _, parsed = aclog_full_records_from_message(message)
        records.extend(parsed)

    report.received = len(records)
    collection = get_user_qso_collection(user)

    from app.aclog.client import _map_other_slots_to_custom_fields

    for index, record in enumerate(records):
        mapped = _map_other_slots_to_custom_fields(record, user)
        try:
            result = await ingest_qso_record(
                record=mapped,
                operator=user.callsign,
                profile=user,
                source=f"aclog-sync:{bridge.id}",
                collection=collection,
            )
        except Exception as exc:
            report.errors += 1
            _append_example(report, index, mapped, str(exc))
            continue

        status = result.get("status")
        if status == "accepted":
            report.imported += 1
        elif status == "duplicate":
            report.skipped += 1
        else:
            report.errors += 1
            _append_example(report, index, mapped, result.get("reason", "rejected"))

    return report


async def _read_cmd_response(reader: Any, timeout: float) -> bytes:
    """Read one complete ACLog <CMD> response without waiting for socket EOF."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    payload = b""

    while b"</CMD>" not in payload.upper():
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise asyncio.TimeoutError
        line = await asyncio.wait_for(reader.readline(), timeout=remaining)
        if not line:
            break
        payload += line

    return payload


def _append_example(
    report: ACLogSyncReport,
    index: int,
    record: dict[str, str],
    reason: str,
) -> None:
    if len(report.examples) >= ACLOG_SYNC_EXAMPLE_LIMIT:
        return
    report.examples.append(
        {
            "index": str(index + 1),
            "call": record.get("CALL") or "?",
            "reason": reason,
        }
    )
