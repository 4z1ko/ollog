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
    from app.qso.models import QSO
    from app.qso.service import _REQUIRED_FIELDS, build_qso_dict, find_duplicate

    if operator is None:
        logger.warning(
            "UDP_OPERATOR not configured — datagram from %s discarded", addr
        )
        return

    try:
        text = data.decode("utf-8", errors="replace")
        records, parse_errors = parse_adi(text)

        if parse_errors:
            logger.warning(
                "UDP datagram from %s had parse errors: %s", addr, parse_errors
            )

        if not records:
            logger.warning(
                "UDP datagram from %s: no ADIF records found", addr
            )
            return

        if len(records) > 1:
            logger.warning(
                "UDP datagram from %s: %d records found, processing first only",
                addr,
                len(records),
            )

        record = records[0]

        missing = _REQUIRED_FIELDS - set(record)
        if missing:
            logger.warning(
                "UDP datagram from %s rejected — missing required field(s): %s",
                addr,
                sorted(missing),
            )
            return

        qso_dict = build_qso_dict(record, operator, profile=user)

        dup = await find_duplicate(
            operator=operator,
            call=qso_dict["CALL"],
            band=qso_dict["BAND"],
            mode=qso_dict["MODE"],
            qso_date_utc=qso_dict["qso_date_utc"],
        )
        if dup is not None:
            logger.info(
                "UDP datagram from %s: duplicate of existing QSO %s — skipped",
                addr,
                dup.id,
            )
            return

        qso = QSO(**qso_dict)
        await qso.insert()
        logger.info(
            "UDP QSO inserted: id=%s call=%s band=%s mode=%s operator=%s",
            qso.id,
            qso_dict["CALL"],
            qso_dict["BAND"],
            qso_dict["MODE"],
            operator,
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
