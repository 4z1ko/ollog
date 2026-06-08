"""UDP listener for ADIF QSO ingestion.

Accepts raw ADIF ADI text datagrams over UDP. Lifecycle-managed via the
FastAPI lifespan in app/main.py.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.auth.models import User

logger = logging.getLogger(__name__)


async def _handle_datagram(
    data: bytes,
    addr: tuple[str, int],
    operator: str | None,
    user: "User | None",
) -> None:
    """Parse a raw ADIF datagram and insert it as a QSO into MongoDB.

    Lazy imports are used inside the function body to avoid circular imports
    at module load time (matches pattern from import_qsos_from_bytes).

    Validation rules:
    - operator must be configured (from settings.udp_operator)
    - ADIF text must parse to at least one record
    - Record must contain all _REQUIRED_FIELDS
    - Duplicate detection: same CALL/BAND/MODE within +/-2 min is skipped

    Profile auto-stamping is applied when user is not None (build_qso_dict
    with profile=user). This is identical to the POST /api/qsos/ path.
    """
    from app.adif.parser import parse_adi
    from app.qso.service import ingest_qso_record

    try:
        text = data.decode("utf-8", errors="replace")
        records, parse_errors = parse_adi(text)

        if parse_errors or not records:
            logger.warning(
                "UDP datagram src=%s:%s disposition=rejected reason=parse-failure",
                addr[0], addr[1],
            )
            return

        if len(records) > 1:
            logger.warning(
                "UDP datagram src=%s:%s: %d records found, processing first only",
                addr[0], addr[1], len(records),
            )

        record = records[0]

        _APP_TOKEN_FIELD = "APP_OLLOG_TOKEN"
        token_value = record.pop(_APP_TOKEN_FIELD, None)   # consume — must not reach QSO doc
        if token_value is not None:
            from app.udp.token_cache import token_cache
            resolved_user = await token_cache.resolve(token_value)
            if resolved_user is None:
                logger.warning(
                    "UDP datagram src=%s:%s disposition=rejected reason=invalid-token",
                    addr[0], addr[1],
                )
                return
            # Override operator and user — both must come from resolved_user
            operator = resolved_user.callsign
            user = resolved_user

        # --- Multi-operator routing: OPERATOR field overrides UDP_OPERATOR ---
        _OPERATOR_FIELD = "OPERATOR"
        op_field_value = record.pop(_OPERATOR_FIELD, None)  # consume — must not reach QSO doc
        if op_field_value is not None:
            from app.udp.operator_cache import operator_cache

            resolved_op_user = await operator_cache.resolve(op_field_value)
            if resolved_op_user is None:
                logger.warning(
                    "UDP datagram src=%s:%s disposition=rejected reason=unknown-operator callsign=%s",
                    addr[0],
                    addr[1],
                    op_field_value,
                )
                return
            operator = resolved_op_user.callsign
            user = resolved_op_user

        if operator is None or user is None:
            logger.warning(
                "UDP datagram src=%s:%s disposition=rejected reason=no-user-resolved",
                addr[0],
                addr[1],
            )
            return

        from app.database import get_client
        from app.qso.collections import get_user_qso_collection

        collection = get_user_qso_collection(user) if get_client() is not None else None

        result = await ingest_qso_record(
            record=record,
            operator=operator,
            profile=user,
            source="udp",
            collection=collection,
        )

        if result["status"] == "rejected":
            logger.warning(
                'UDP datagram src=%s:%s disposition=rejected reason="%s"',
                addr[0], addr[1], result.get("reason", "unknown"),
            )
            return

        if result["status"] == "duplicate":
            logger.info(
                "UDP datagram src=%s:%s call=%s disposition=duplicate",
                addr[0], addr[1], record.get("CALL", "?"),
            )
            return

        logger.info(
            "UDP datagram src=%s:%s call=%s disposition=accepted id=%s",
            addr[0], addr[1], record.get("CALL", "?"), result.get("id"),
        )

    except Exception:
        logger.exception("UDP datagram from %s: unhandled exception", addr)


class QSODatagramProtocol(asyncio.DatagramProtocol):
    """asyncio UDP protocol for receiving ADIF QSO datagrams.

    datagram_received() is synchronous — async QSO processing is dispatched
    via asyncio.create_task(_handle_datagram(...)). The _background_tasks set
    holds strong references to in-flight tasks to prevent premature garbage
    collection (Python 3.12+ requirement).
    """

    def __init__(
        self,
        operator: str | None = None,
        user: "User | None" = None,
    ) -> None:
        self.transport: asyncio.DatagramTransport | None = None
        self._background_tasks: set[asyncio.Task] = set()
        self._operator = operator
        self._user = user

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:  # type: ignore[override]
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        logger.info(
            "UDP datagram received from %s:%s (%d bytes)",
            addr[0],
            addr[1],
            len(data),
        )
        task = asyncio.create_task(
            _handle_datagram(data, addr, self._operator, self._user)
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def error_received(self, exc: Exception) -> None:
        logger.warning("UDP transport error: %s", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        logger.info("UDP transport closed")


async def start_udp_listener(
    host: str,
    port: int,
    operator: str | None = None,
    user: "User | None" = None,
) -> tuple[asyncio.DatagramTransport, QSODatagramProtocol]:
    """Bind a UDP socket and return the (transport, protocol) pair.

    Uses asyncio.get_running_loop() — compatible with Python 3.14
    (get_event_loop() is deprecated in coroutine context since 3.10).

    The operator callsign and user profile are passed to QSODatagramProtocol
    for per-datagram QSO attribution and profile auto-stamping.

    Call transport.close() (synchronously, not awaited) to release the socket.
    """
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: QSODatagramProtocol(operator=operator, user=user),
        local_addr=(host, port),
    )
    logger.info("UDP listener bound to %s:%s", host, port)
    return transport, protocol  # type: ignore[return-value]
