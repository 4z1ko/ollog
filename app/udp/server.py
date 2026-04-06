"""UDP listener for ADIF QSO ingestion.

Accepts raw ADIF ADI text datagrams over UDP. Lifecycle-managed via the
FastAPI lifespan in app/main.py.

Phase 16: skeleton only — logs datagram receipt, no QSO processing.
Phase 17 will add full parse → validate → insert pipeline.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


class QSODatagramProtocol(asyncio.DatagramProtocol):
    """asyncio UDP protocol for receiving ADIF QSO datagrams.

    datagram_received() is synchronous — async QSO processing (Phase 17)
    must be dispatched via asyncio.create_task(_handle_datagram(...)).
    The _background_tasks set holds strong references to in-flight tasks
    to prevent premature garbage collection (Python 3.12+ requirement).
    """

    def __init__(self) -> None:
        self.transport: asyncio.DatagramTransport | None = None
        self._background_tasks: set[asyncio.Task] = set()

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:  # type: ignore[override]
        self.transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        logger.info(
            "UDP datagram received from %s:%s (%d bytes)",
            addr[0],
            addr[1],
            len(data),
        )
        # Phase 17: dispatch async processing here via create_task

    def error_received(self, exc: Exception) -> None:
        logger.warning("UDP transport error: %s", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        logger.info("UDP transport closed")


async def start_udp_listener(
    host: str,
    port: int,
) -> tuple[asyncio.DatagramTransport, QSODatagramProtocol]:
    """Bind a UDP socket and return the (transport, protocol) pair.

    Uses asyncio.get_running_loop() — compatible with Python 3.14
    (get_event_loop() is deprecated in coroutine context since 3.10).

    Call transport.close() (synchronously, not awaited) to release the socket.
    """
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        QSODatagramProtocol,
        local_addr=(host, port),
    )
    logger.info("UDP listener bound to %s:%s", host, port)
    return transport, protocol  # type: ignore[return-value]
