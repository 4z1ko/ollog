---
phase: 16-udp-infrastructure
plan: 02
subsystem: udp
tags: [asyncio, udp, datagram-protocol, lifespan, docker, config]

# Dependency graph
requires:
  - phase: 16-01
    provides: service extraction prerequisite (parallel plan, no real dependency for skeleton)

provides:
  - app/udp/__init__.py (package marker)
  - app/udp/server.py with QSODatagramProtocol and start_udp_listener()
  - app/config.py: udp_enabled (bool, default False), udp_port (int, 2399), udp_bind_host (str, 127.0.0.1), udp_operator (str|None)
  - app/main.py: conditional UDP startup/shutdown in lifespan (before/after yield)
  - docker-compose.yml: 2399:2399/udp port mapping

affects:
  - phase-17 (QSO pipeline wires into QSODatagramProtocol._background_tasks)
  - operators (can now enable UDP_ENABLED=true and test socket with nc -u)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "asyncio.DatagramProtocol subclass with connection_made/datagram_received/error_received/connection_lost"
    - "asyncio.get_running_loop() (not deprecated get_event_loop()) for Python 3.14 compat"
    - "_background_tasks: set[asyncio.Task] strong reference pattern for GC safety (Phase 17 will use it)"
    - "transport.close() is synchronous — never await; placed before close_db() in lifespan shutdown"
    - "Docker UDP requires /udp suffix: '2399:2399/udp' — without it Docker maps TCP only"

key-files:
  created:
    - app/udp/__init__.py
    - app/udp/server.py
  modified:
    - app/config.py
    - app/main.py
    - docker-compose.yml

key-decisions:
  - "Default port 2399 — avoids WSJT-X (2237) and N1MM+ (12060) ecosystem conflicts"
  - "Default bind host 127.0.0.1 — loopback-only protects against LAN exposure by default"
  - "UDP_ENABLED=false default — existing deployments unaffected on upgrade"
  - "transport.close() before close_db() in lifespan shutdown — prevents DB use during shutdown"
  - "Docker comment documents UDP_BIND_HOST=0.0.0.0 requirement for host→container datagrams"

# One-liner
one_liner: "Created app/udp/ module with asyncio.DatagramProtocol skeleton, 4 config fields, FastAPI lifespan wiring, and Docker UDP port — operators can enable and smoke-test the socket before Phase 17 adds QSO processing."

# Self-Check
## Self-Check: PASSED
- UDP_ENABLED=false by default — settings.udp_enabled is False ✓
- UDP_PORT=2399 default ✓
- UDP_BIND_HOST=127.0.0.1 default ✓
- UDP_OPERATOR=None default ✓
- QSODatagramProtocol has _background_tasks set ✓
- start_udp_listener uses asyncio.get_running_loop() ✓
- Startup banner: logger.info("UDP listener bound to %s:%s", ...) in start_udp_listener ✓
- Receipt log: logger.info("UDP datagram received from %s:%s (%d bytes)", ...) in datagram_received ✓
- docker-compose.yml has "2399:2399/udp" ✓
- transport.close() in lifespan before close_db() ✓
- app/main.py imports clean: uv run python -c "from app.main import app" → OK ✓
