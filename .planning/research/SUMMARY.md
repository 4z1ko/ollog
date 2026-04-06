# Research Summary: v1.4 UDP Interface

**Project:** ollog — ham radio logbook (FastAPI + Beanie + MongoDB)
**Milestone:** v1.4 UDP ADIF Listener
**Domain:** asyncio UDP socket integration, ham radio logging protocol conventions
**Researched:** 2026-04-05
**Confidence:** HIGH (stack, architecture, pitfalls from codebase inspection + official docs); MEDIUM (auth design, wire format conventions from community sources)

---

## Executive Summary

ollog's v1.4 milestone adds a UDP listener that accepts ADIF-formatted QSO records from ham radio logging software running on the same machine or LAN. The implementation requires no new production dependencies: Python's stdlib `asyncio.DatagramProtocol` is the correct tool, the existing `parse_adi()` / `build_qso_dict()` / `find_duplicate()` / `QSO.insert()` stack is fully reusable, and the lifespan pattern for background tasks is already established in `app/main.py`. The entire feature is approximately 150 lines of new code across two new files (`app/udp/__init__.py`, `app/udp/server.py`) and targeted changes to three existing files (`app/config.py`, `app/main.py`, `docker-compose.yml`).

The most consequential design decision is authentication. The ham radio logging ecosystem (N1MM+, WSJT-X, VarAC, and all bridge scripts) sends UDP datagrams with no authentication. JWTs are wrong for UDP: they expire, they require a refresh mechanism that UDP cannot provide, and no logging software knows how to include them. The recommended auth model for v1.4 is: bind to `127.0.0.1` by default (loopback-only, no LAN exposure), configure a single `UDP_OPERATOR` callsign in `.env` that maps all incoming datagrams to one user, and let the operator set `UDP_BIND_HOST=0.0.0.0` plus IP allowlist env vars if LAN access is needed. This matches how every other ham radio UDP integration works. The `APP_OLLOG_APIKEY` pre-shared key approach (embedding a key in the ADIF datagram) is viable as a v1.5 differentiator once the basic listener is working, but adds scope without solving the core use case.

The wire format decision is equally important: raw ADIF ADI text as the entire UDP payload is the simplest, most broadly compatible format and the right choice for v1.4 table stakes. WSJT-X type 12 (binary header + ADIF payload) and N1MM+ XML are medium-complexity differentiators worth considering for v1.5 after the listener infrastructure is proven. One pre-implementation clarification is needed: the default UDP port. Port 2237 conflicts with WSJT-X itself; port 12060 conflicts with N1MM+. A dedicated port or explicit operator configuration is the safer posture.

---

## Key Findings

### Recommended Stack

No new production dependencies are needed. The stdlib `asyncio.DatagramProtocol` + `loop.create_datagram_endpoint()` is the correct and complete solution. The pattern is identical to the existing change-stream watcher task already running in `app/main.py`'s lifespan. `uvloop` (which provides the actual event loop) is already installed at v0.22.1 and supports `create_datagram_endpoint()` transparently.

Docker Compose requires an explicit `/udp` suffix on any UDP port mapping. Without it, Docker maps TCP only and UDP datagrams are silently dropped at the host with no error on either side. This is the single most common silent misconfiguration for this feature.

**Core technologies:**
- `asyncio.DatagramProtocol` (stdlib): UDP receive loop — zero new deps, runs on uvicorn's event loop, callback model fits receive-only design perfectly
- `asyncio.get_running_loop()` (stdlib, Python 3.10+): correct way to acquire the running loop inside a protocol callback — `get_event_loop()` is deprecated on Python 3.14 (which this project runs per `.venv/lib/python3.14`)
- `asyncio.create_task()` (stdlib): dispatches async QSO insertion from the sync `datagram_received()` callback — the mandatory pattern for this sync/async boundary
- `pydantic-settings` (already present): add `udp_enabled: bool`, `udp_host: str`, `udp_port: int`, `udp_operator: str` to `Settings`
- Docker Compose `"<port>:<port>/udp"` syntax: required for UDP port forwarding

**Not needed:** `asyncio-dgram`, `aiohttp`, Motor directly, a separate worker process, or any new PyPI package.

### Expected Features

**Must have (table stakes):**
- Raw ADIF ADI text reception over UDP — `parse_adi()` already handles this format; the listener is the only new piece
- Single operator attribution via `UDP_OPERATOR` config — operator identity must come from configuration, never from the datagram
- Loopback-bind default (`127.0.0.1`) — matches ham radio ecosystem convention; protects against LAN exposure out of the box
- `UDP_ENABLED=false` default — existing deployments are unaffected on upgrade
- Configurable UDP port via `UDP_PORT` env var — operators must be able to avoid conflicts with WSJT-X (2237) and N1MM+ (12060)
- Required-field validation (CALL, BAND, MODE, QSO_DATE, TIME_ON) before insert — same fields as REST API
- Duplicate detection reusing existing `find_duplicate()` — prevents double-logging from FT8 auto-loggers
- Logging of accepted/rejected/duplicate datagrams to stdout — ham radio operators expect visible log output to diagnose listener health
- SSE feed integration (automatic, no code changes) — `QSO.insert()` triggers the existing change stream watcher

**Should have (differentiators for v1.5+):**
- WSJT-X type 12 "Logged ADIF" support — 12-byte binary header + raw ADIF string payload; dominant FT8/FT4 logger; medium complexity; `parse_adi()` usable after header extraction
- N1MM+ XML `<contactinfo>` support — dominant contest logger; sends XML not ADIF; requires field mapping (band MHz to ADIF string, timestamp format conversion); medium complexity
- `APP_OLLOG_APIKEY` pre-shared key auth in ADIF `APP_` field — enables multi-operator UDP without IP-only trust; ties each datagram to a specific user account; persistent (unlike JWT)
- API key management endpoints (`POST /api/udp-keys/`, `DELETE /api/udp-keys/{id}`) and admin UI section
- Per-source-IP rate limiting (simple in-memory token bucket in `datagram_received()`)
- `/health` endpoint `udp_listener` field with last-datagram timestamp

**Defer (v2+):**
- WSJT-X type 5 binary "QSO Logged" — requires full Qt binary deserialization of every field; much harder than type 12; no advantage over type 12 for new integrations
- TCP alongside UDP — zero ecosystem demand; logging software does not send QSOs over TCP
- ACK/NACK response datagrams — breaks fire-and-forget model; creates UDP amplification risk
- Auto-detection of datagram format by heuristic — adds fragility; use separate ports per format instead

### Architecture Approach

The UDP listener lives in a new `app/udp/` module following the established `app/qso/`, `app/auth/`, `app/feed/` pattern. A `QSODatagramProtocol` class handles the asyncio protocol lifecycle. All async work (parsing, validation, DB insert) is dispatched from the synchronous `datagram_received()` callback via `asyncio.create_task()` with a `_background_tasks` set providing strong references to prevent premature garbage collection. The operator `User` document is resolved once at startup (during lifespan) and cached, avoiding a MongoDB round-trip per datagram. UDP-inserted QSOs flow into the same `qsos` collection as REST API QSOs, so the SSE change-stream feed picks them up automatically with zero code changes.

**Major components:**
1. `app/udp/__init__.py` — empty package marker
2. `app/udp/server.py` — `QSODatagramProtocol` (protocol callbacks), `start_udp_listener()` / `stop_udp_listener()` (lifespan hooks), `_handle_datagram()` (async parse + validate + insert pipeline), `_background_tasks` set
3. `app/config.py` additions — `udp_enabled`, `udp_host`, `udp_port`, `udp_operator` settings
4. `app/main.py` lifespan additions — startup and shutdown hooks guarded by `settings.udp_enabled`
5. `docker-compose.yml` — `/udp` port mapping entry

**Unchanged (reused as-is):** `app/adif/parser.py`, `app/qso/service.py`, `app/qso/models.py`, `app/feed/manager.py`, `app/auth/service.py`

**Prerequisite refactor:** `process_import()` in `app/adif/router.py` raises `HTTPException` and cannot be called from a UDP task context. A shared `insert_qso_from_adif(record, operator, profile)` function must be extracted into `app/qso/service.py` or `app/adif/service.py` before the UDP handler is built. Both the HTTP import endpoint and the UDP handler call this shared function.

### Critical Pitfalls

1. **`datagram_received()` is synchronous — no `await` allowed.** Making it `async def` causes the event loop to call it synchronously and discard the returned coroutine, so QSOs silently never get inserted. All Beanie calls must be dispatched via `asyncio.create_task(_handle_datagram(data, addr))`. Use a `_background_tasks` set with `task.add_done_callback(_background_tasks.discard)` to prevent garbage collection before the task completes.

2. **`_operator` must come from configuration, never from the datagram.** The REST API always overwrites `_operator` from the JWT. UDP has no JWT, so `_operator` must come from `UDP_OPERATOR` in `.env`. If the datagram's ADIF `OPERATOR` field were used instead, any machine on the LAN could forge QSOs into another operator's log by spoofing that field.

3. **Docker requires `/udp` suffix.** `"2237:2237"` in `docker-compose.yml` forwards TCP only. UDP datagrams are silently dropped with no error on either end. Use `"2237:2237/udp"`. Test UDP delivery from the host with `nc -u` before declaring the phase done.

4. **JWT is wrong for UDP.** JWT tokens expire (60-minute default in `app/config.py`). A contest or overnight FT8 session silently stops logging mid-session with no visible error on the sending software. UDP is connectionless — there is no refresh mechanism. Use IP allowlist + `UDP_OPERATOR` config instead.

5. **`process_import()` raises `HTTPException` and is not reusable from UDP context.** Confirmed by direct reading of `app/adif/router.py`. Calling it from an async task would raise `HTTPException`, which gets caught by the general exception handler and silently swallowed. Extract the shared insertion logic before writing the UDP handler.

6. **`asyncio.get_event_loop()` is deprecated on Python 3.14.** This project runs Python 3.14 (confirmed from `.venv/lib/python3.14`). Use `asyncio.get_running_loop()` inside `datagram_received()`. It is always correct there because `datagram_received()` is called from the running loop.

7. **Transport must be explicitly closed on shutdown.** If `transport.close()` is not called in the lifespan shutdown path, the UDP port is not released and a restart fails with `EADDRINUSE`. Store the transport returned by `create_datagram_endpoint()` and close it before `close_db()`, following the existing `watcher_task.cancel()` pattern.

---

## Implications for Roadmap

Based on research, the feature decomposes cleanly into three implementation phases plus two optional v1.5+ phases.

### Phase 1: UDP Infrastructure

**Rationale:** Establishes the socket binding, config, Docker port mapping, and lifespan wiring before any QSO processing logic exists. A no-op listener that logs raw datagram receipts validates the entire environment stack — asyncio, Docker UDP forwarding, port configuration — before any business logic is written on top.

**Delivers:** A running UDP listener that logs "datagram received from 127.0.0.1:XXXXX" to stdout. No QSO processing. Proves the environment works.

**Addresses:** `UDP_ENABLED`, `UDP_HOST`, `UDP_PORT` config; Docker `/udp` port mapping; lifespan startup/shutdown hooks; loopback-bind default

**Avoids:** Docker silent TCP-only pitfall (verify with `nc -u` before Phase 2); port conflict with WSJT-X/N1MM+ (decide default port before coding)

**Files to create/modify:** `app/udp/__init__.py` (new), `app/udp/server.py` (skeleton protocol class), `app/config.py`, `app/main.py`, `docker-compose.yml`

**Research flag:** Standard patterns — no deeper research needed.

---

### Phase 2: QSO Processing Pipeline

**Rationale:** With socket infrastructure proven, wire in the full QSO handling pipeline. This is the highest-risk phase: it crosses the sync/async boundary, requires the `process_import()` refactor as a prerequisite, and implements the operator isolation logic that must be correct from the first inserted record.

**Delivers:** End-to-end QSO insertion from a raw ADIF UDP datagram. A datagram sent from `nc -u` appears in the ollog log and triggers the SSE feed.

**Addresses:** ADIF decode + parse, required-field validation, operator User document caching, `build_qso_dict()` with profile, `find_duplicate()` dedup, `QSO.insert()`, SSE automatic pickup

**Avoids:**
- AS-1 sync/async boundary: `datagram_received` is `def`, all awaits inside `_handle_datagram()`
- OL-1 operator identity: cache User document at startup, pass to `build_qso_dict()` as `profile=`
- OL-3 operator isolation: `_operator` always from `settings.udp_operator`, never from datagram
- OL-4 HTTPException coupling: extract shared insertion logic from `process_import()` as prerequisite
- OL-2 missing fields: wrap `build_qso_dict()` in `try/except (ValueError, KeyError)`
- AS-2 deprecated `get_event_loop()`: use `asyncio.get_running_loop()`

**Prerequisite:** Extract `insert_qso_from_adif()` from `app/adif/router.py` before writing `_handle_datagram()`.

**Research flag:** Standard patterns — the async task dispatch and Beanie insert patterns are well-understood. Operator isolation logic needs careful code review, not additional research.

---

### Phase 3: Error Handling, Logging, and Observability

**Rationale:** Operators need enough visibility to know the listener is working and enough robustness to avoid silent failures or log floods. Short phase but required before v1.4 is shippable.

**Delivers:** Structured log lines for accepted/rejected/duplicate datagrams; `error_received()` implementation; top-level exception guard in `_handle_datagram()`; startup banner ("UDP listener bound to 127.0.0.1:2237"); `udp_listener` state in `/health` response with last-datagram timestamp.

**Addresses:** Operator diagnostics, `error_received()` (prevents silent death on ICMP error), exception guard (prevents silent task failure swallowing)

**Avoids:**
- AS-4 Windows OSError silent death: implement `error_received(exc)` with WARNING log
- AS-3 unclosed transport: confirm `transport.close()` is called before `close_db()` in lifespan shutdown
- Port scanner noise on `0.0.0.0`: log malformed datagrams at DEBUG, not INFO/WARNING

**Research flag:** Standard patterns — logging and health endpoint patterns are already established in the codebase.

---

### Phase 4 (Optional, v1.5+): WSJT-X Type 12 Support

**Rationale:** WSJT-X is the dominant FT8/FT4 logger. Type 12 carries a complete ADIF string after a 12-byte binary header readable with `struct.unpack`. After header extraction, the ADIF string passes directly to `parse_adi()`. This is the highest-value compatibility addition for the least implementation complexity among the differentiators.

**Delivers:** Native WSJT-X UDP log-forwarding without a bridge script. Operators configure WSJT-X's "UDP Server" to point at ollog's port.

**Avoids:** Format auto-detection (configure via explicit `UDP_FORMAT` env var or per-port instead); type 5 binary decoding (skip entirely — type 12 is strictly better)

**Research flag:** Binary header format is documented in FEATURES.md with HIGH confidence. May want a quick verification pass against current WSJT-X source before coding.

---

### Phase 5 (Optional, v1.5+): APP_OLLOG_APIKEY Auth and Key Management

**Rationale:** Single-operator loopback use needs no auth beyond IP trust. Multi-operator or LAN-exposed deployments need per-user datagram attribution. The `APP_OLLOG_APIKEY` pre-shared key embedded in ADIF `APP_` fields enables this without expiry (unlike JWT) and without breaking ADIF compatibility (other loggers ignore `APP_` fields verbatim).

**Delivers:** Per-user API keys, key generation/revocation endpoints, multi-operator UDP support without per-IP user assignment.

**Avoids:** JWT in datagrams (expires, no refresh, incompatible with logging software); HMAC datagram signing (no ecosystem precedent, unimplementable in logging software)

**Research flag:** Original design — no ecosystem precedent to validate against. Schema for `api_keys` collection and key management UI are new design work requiring a design session.

---

### Phase Ordering Rationale

- Infrastructure before logic: Phase 1 proves Docker UDP and asyncio binding before any business logic compounds on top of a broken foundation.
- Prerequisite refactor surfaces early: `process_import()` extraction is called out as a pre-Phase 2 task rather than a Phase 2 subtask, so it doesn't become a surprise blocker mid-phase.
- Operator isolation is built in, not retrofitted: `_operator` attribution is a Phase 2 concern from the first inserted QSO. Retrofitting isolation after the fact risks data integrity issues in a multi-operator deployment.
- WSJT-X and auth are independent parallel tracks: Phases 4 and 5 do not depend on each other and can be sequenced in either order based on operator demand.

### Research Flags

Phases needing deeper research during planning:
- **Phase 4 (WSJT-X type 12):** Verify current binary header format against WSJT-X source. Documented in FEATURES.md with HIGH confidence, but implementation details (Qt string encoding edge cases) warrant a focused verification pass.
- **Phase 5 (API key auth):** `api_keys` collection schema, key hashing approach, admin UI placement, and multi-operator UDP config model are open design questions. Needs a design session before planning.

Phases with standard patterns (no research-phase needed):
- **Phase 1 (infrastructure):** `asyncio.DatagramProtocol` + Docker UDP syntax are fully documented at HIGH confidence.
- **Phase 2 (QSO pipeline):** All service functions are proven; async dispatch pattern is established. This is assembly, not research.
- **Phase 3 (error handling):** Logging and health endpoint patterns already exist in the codebase.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | stdlib asyncio (official Python docs); Docker UDP syntax (official Docker docs); uvloop already installed; no new dependency decisions to validate |
| Architecture | HIGH | Based on direct codebase inspection; lifespan pattern proven in `app/main.py`; SSE change-stream confirmed to watch the collection, not a specific code path |
| Pitfalls | HIGH | asyncio pitfalls from CPython official docs + issue tracker; ollog-specific pitfalls from direct reading of `app/adif/router.py`, `app/qso/service.py`, `app/auth/service.py` |
| Wire format (raw ADIF, N1MM+ XML, WSJT-X type 12) | HIGH | N1MM+ and WSJT-X formats confirmed against official docs and multiple independent implementations; raw ADIF convention confirmed from VarAC, Log4OM, Cloudlog |
| Auth design | MEDIUM | Loopback-default + `UDP_OPERATOR` config is HIGH confidence as correct for single-operator use; `APP_OLLOG_APIKEY` approach is original ollog design with no ecosystem precedent to validate against |

**Overall confidence:** HIGH for v1.4 table stakes (raw ADIF, loopback, single operator). MEDIUM for the auth design if multi-operator UDP is in scope.

### Gaps to Address

- **Default UDP port:** 2237 (WSJT-X default) and 12060 (N1MM+ default) are both ecosystem-occupied ports. A dedicated port (e.g., 2399) or leaving the port unconfigured with `UDP_ENABLED=false` as the gate should be decided before roadmap is written.

- **Single-operator vs. multi-operator scope for v1.4:** The simplest correct v1.4 is single-operator (`UDP_OPERATOR` config, all datagrams attributed to that user). Multi-operator requires Phase 5 (`APP_OLLOG_APIKEY`). This scope decision drives whether Phase 5 is v1.4 or v1.5.

- **`build_qso_dict()` profile stamping decision:** The ADIF import path calls `build_qso_dict()` with `profile=None`. The REST API calls it with the full `User` document. UDP could go either way. Decide before Phase 2: profile stamping requires the cached `User` object at startup; no stamping simplifies operator resolution but loses station metadata on UDP-submitted QSOs.

- **`process_import()` extraction timing:** This is a prerequisite for Phase 2, not part of it. The roadmap should include it explicitly as a pre-Phase 2 task or fold it into Phase 1 as a codebase preparation step.

---

## Sources

### Primary (HIGH confidence)
- Python asyncio Transports and Protocols (docs.python.org/3) — `DatagramProtocol`, `datagram_received`, `create_datagram_endpoint`, `get_running_loop`
- Python asyncio Event Loop (docs.python.org/3) — deprecation of `get_event_loop()` in Python 3.10+, active on Python 3.14
- FastAPI Lifespan Events (fastapi.tiangolo.com) — `@asynccontextmanager` lifespan, `create_task` pattern
- Docker port publishing docs (docs.docker.com) — `/udp` suffix requirement for UDP forwarding
- N1MM+ External UDP Broadcasts (n1mmwp.hamdocs.com) — XML format, port 12060, no auth
- WSJT-X User Guide 2.7.0 (wsjt.sourceforge.io) — binary protocol, port 2237, no auth
- WSJT-X NetworkMessage.hpp (GitHub mirror, roelandjansen/wsjt-x) — type 12 binary header format
- ADIF 3.1.6 specification (adif.org) — confirmed: no UDP transport specification exists
- Codebase direct inspection: `app/main.py`, `app/adif/parser.py`, `app/adif/router.py`, `app/qso/service.py`, `app/qso/router.py`, `app/auth/service.py`, `app/feed/manager.py`, `app/config.py`, `docker-compose.yml`

### Secondary (MEDIUM confidence)
- wsjtx-go library (pkg.go.dev/github.com/k0swe/wsjtx-go) — corroborates WSJT-X type 12 binary format
- VarAC integration docs (varac-hamradio.com) — raw ADIF-over-UDP convention, port 12060
- Log4OM UDP ADIF forum (forum.log4om.com) — raw ADIF-over-UDP convention
- Cloudlog Aurora UDP (aurora.cloudlog.org) — raw ADIF-over-UDP reception
- n1kdo/n1mm_view (GitHub) — Python N1MM+ XML UDP receiver implementation
- CPython issue #81409 — UDP `SO_REUSEADDR` silent multi-bind risk on Linux
- CPython issue #88906 — `DatagramProtocol` stops after `OSError` on Windows
- CPython issue #93453 — `get_event_loop()` deprecation timeline

### Tertiary (LOW confidence)
- Port 2237 as informal ham radio UDP ecosystem convention — community-derived; treat configurable port as the correct posture rather than relying on any specific default being unoccupied on a given operator's machine

---

*Research completed: 2026-04-05*
*Ready for roadmap: yes*
