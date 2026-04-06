# Pitfalls Research: UDP ADIF Ingestion

**Domain:** Adding a UDP listener to an existing FastAPI/asyncio ham radio logging app (ollog)
**Researched:** 2026-04-05
**Overall confidence:** HIGH for asyncio-specific pitfalls (official CPython docs + confirmed issues); HIGH for ollog-specific pitfalls (codebase confirmed); MEDIUM for auth trade-offs (industry practice + self-hosted context); MEDIUM for ham radio logging conventions (community evidence, no single authoritative standard).

---

## Summary

Adding UDP to ollog introduces five distinct failure surfaces: the asyncio sync/async protocol boundary (the single most dangerous one), authentication design (where the correct answer for self-hosted LAN use is different from the correct answer for public deployment), UDP transport lifecycle (unclosed transports, silent Windows failures), Docker networking (UDP is not TCP and compose treats it differently), and ollog-specific concerns about whether the existing QSO service layer is safe to call from a non-request async context.

The core insight about real-world ham radio logging is that **N1MM+, WSJT-X, and every major logging application send UDP broadcasts with zero authentication**. They rely entirely on network-level trust (loopback or LAN). This is the domain convention, not a bug. The implication for ollog: designing a JWT-in-datagram scheme is architecturally foreign to every tool operators will actually use. The right design is IP-allowlist at the bind/accept layer, not token auth in the datagram.

The asyncio DatagramProtocol boundary is the most technically dangerous pitfall: `datagram_received()` is a synchronous callback called by the event loop. Any `await` inside it is a syntax error. Any Beanie/Motor call must be dispatched with `asyncio.create_task()`. Forgetting this causes one of two failure modes: either a runtime error that kills the process, or a subtler problem where the coroutine is scheduled but exceptions are silently swallowed.

The duplicate detection, SSE feed, and operator isolation systems all work correctly from a UDP-inserted QSO — but only if the UDP handler calls the same `build_qso_dict()` / `find_duplicate()` / `QSO.insert()` path that the REST API calls, and only if it supplies a resolved `User` document (not just a callsign string) to `build_qso_dict()` for profile stamping.

---

## Authentication Pitfalls

### Pitfall A-1: JWT in Datagram Is Architecturally Foreign to the Ecosystem

**What goes wrong:**
The natural instinct is to require a `Authorization: Bearer <token>` field in every UDP datagram — mirroring the REST API auth pattern. This is technically feasible but operationally broken: N1MM+, WSJT-X, JS8Call, and every major ham radio logging application that emits UDP QSO broadcasts do so with **no authentication fields in the datagram at all**. They assume loopback or LAN trust. A UDP listener that requires a JWT token in every datagram is incompatible with every logging tool operators will actually use. They would need a custom middleware shim to inject tokens — which no one will build.

**Why it happens:**
Developers extending a JWT-authenticated REST API to UDP naturally ask "how do I put auth in the datagram?" The question assumes JWT is the right model for UDP. It is not.

**What the ecosystem actually does:**
N1MM+ broadcasts XML datagrams on port 12060 with no auth. WSJT-X broadcasts binary protocol messages on port 2237 with no auth. The receiving application is trusted because it is listening on the same machine or LAN. IP-level trust is the universal convention. (Source: N1MM+ External UDP Broadcasts documentation; WSJT-X community discussions confirming no auth in UDP messages.)

**Correct approach for ollog:**
Accept datagrams from a configurable IP allowlist (default: `127.0.0.1` only). Bind to `127.0.0.1` by default to refuse any non-loopback datagrams at the OS level. For LAN use, the operator explicitly opens the bind address to their LAN subnet. This is consistent with how every other ham radio UDP integration works.

**Confidence:** MEDIUM — no single normative document states "ham radio UDP has no auth"; derived from examining multiple software's documentation and community reports. The loopback-default approach is HIGH confidence as a defensive measure.

---

### Pitfall A-2: Token Replay via Captured Datagram

**What goes wrong:**
If a JWT token is embedded in UDP datagrams (despite the recommendation in A-1 above), the stateless nature of JWT means a captured datagram can be replayed indefinitely until the token expires. UDP has no connection state, so there is no sequence number or session that would detect a replay. An attacker on the LAN who captures one datagram can insert QSOs into any operator's log for up to `JWT_EXPIRE_MINUTES` (60 minutes by default in ollog's `config.py`).

**Mitigation if JWT-in-datagram is chosen anyway:**
Use the `jti` (JWT ID) claim: a unique UUID per token, stored server-side with a TTL matching the token expiry. Reject tokens whose `jti` has already been seen. This requires server-side state (a set of used JTIs in memory or Redis), which undermines the stateless advantage of JWT and adds infrastructure. For a self-hosted LAN app this overhead is not justified.

**Better mitigation:**
Do not embed tokens in datagrams. Use IP allowlist + loopback bind (see A-1). Replay on loopback is only possible from processes on the same machine — which is the same as having local shell access.

**Confidence:** HIGH — JWT replay via capture is a well-documented vulnerability; jti mitigation is in RFC 7519 and Auth0 documentation.

---

### Pitfall A-3: Long-Running Logger with Expired Token

**What goes wrong:**
If the design requires JWT tokens in datagrams, a logging program that started a contest session hours ago will have an expired token. `decode_access_token()` in `app/auth/service.py` raises `jwt.InvalidTokenError` on expiry. Datagrams with expired tokens are silently dropped. The operator has no feedback — QSOs appear to log in the software but never arrive in ollog. This is a particularly bad failure mode because it is invisible.

**Why this matters for ollog specifically:**
`jwt_expire_minutes` defaults to 60 in `app/config.py`. A 4-hour contest session will expire the token partway through without any user-visible error on the logging software side.

**Prevention:**
Again, the right answer is not to require JWT in datagrams (see A-1). If auth-in-datagram must be used, log a warning (not silently drop) and implement token refresh before the session starts.

**Confidence:** HIGH — confirmed by reading `app/auth/service.py` (`decode_access_token` raises on expiry) and `app/config.py` (60-minute default).

---

### Pitfall A-4: IP Allowlist Gives False Confidence Without Loopback Bind

**What goes wrong:**
Implementing IP allowlist checking in Python code (`if addr[0] not in allowed_ips: return`) while binding to `0.0.0.0` still means the OS receives the datagram, creates the socket buffer entry, and calls `datagram_received()` before the Python code rejects it. This approach works but wastes CPU on every rejected datagram and is bypassable by IP spoofing on the LAN.

**Prevention:**
Bind to `127.0.0.1` by default (loopback only) using `local_addr=('127.0.0.1', port)` in `loop.create_datagram_endpoint()`. When LAN access is needed, the operator sets `UDP_BIND_HOST=0.0.0.0` in their `.env`. Supplement with Python-level source IP check for defense-in-depth on the `0.0.0.0` case. This matches how N1MM+ and WSJT-X are configured: operators set the specific listener IP explicitly.

**Confidence:** HIGH — standard UDP bind behavior; confirmed by Docker networking section below.

---

## UDP Reliability Pitfalls

### Pitfall R-1: Datagram Drop Is Silent — No Retry, No Error

**What goes wrong:**
UDP datagrams can be silently dropped by the OS kernel (receive buffer overflow), network switches, or Docker's virtual network stack. There is no acknowledgement, no retransmission. If the ollog UDP receive buffer fills up (e.g., burst of QSOs during a contest pile-up), the OS drops datagrams without notification. The logging software believes the QSO was sent; it was not logged.

**For the self-hosted LAN use case:**
On loopback, datagram loss is extremely rare (the OS does not route the packet through any network stack). On LAN, it is uncommon but possible under load. In a contest environment with rapid QSO entry (> 500 QSOs/hour for competitive operators), brief bursts are plausible.

**Prevention:**
Design the UDP listener as fire-and-forget on the ollog side: log a warning when a datagram produces an error, but do not attempt acknowledgement (which would change the protocol away from what logging software expects). Increase the receive buffer size if needed: `socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)` before passing the socket to `create_datagram_endpoint()`. Document to operators that UDP does not guarantee delivery and that important QSOs should be verified in the log.

**Confidence:** MEDIUM — drop probability on loopback is effectively zero; on LAN it is a real concern under load but not normal conditions.

---

### Pitfall R-2: Datagram Size — ADIF QSOs Fit Comfortably, But Multi-QSO Batches May Not

**What goes wrong:**
IPv4 UDP maximum payload is 65,507 bytes. A single ADIF QSO record is typically 200–600 bytes (a minimal FT8 QSO: CALL + BAND + MODE + QSO_DATE + TIME_ON + RST fields ≈ 200 bytes; a verbose HF QSO with notes ≈ 600 bytes). Single-QSO datagrams are far below the limit.

However, some logging software (e.g., bulk re-send after a crash recovery) might send multiple QSO records in a single datagram, or include ADIF headers plus many records. ADIF files with dozens of QSOs can easily exceed 65 KB.

**Concrete risk for ollog:**
The existing `parse_adi()` parser handles multi-record ADIF (it iterates `<EOR>` boundaries). If a datagram contains multiple QSOs, each would be inserted. But if the datagram is truncated by the OS because the sender's socket tried to send > 65,507 bytes, the last record in the ADIF stream will be malformed (truncated after `<EOR>` and before the next field boundary). `parse_adi()` handles this gracefully (it stops at the last complete `<EOR>`), but the truncated QSO is silently lost.

**Prevention:**
In the UDP handler, after decoding the datagram, log `len(data)` at DEBUG level and emit a warning if it approaches the limit (e.g., > 60,000 bytes). Document that the UDP interface is intended for single-QSO-per-datagram sends.

**Confidence:** HIGH — UDP size limit is a known protocol constraint; ADIF record sizes are from community-confirmed examples (CQRLOG documentation and WSJT-X protocol notes).

---

### Pitfall R-3: No ACK Response — Do Not Add One

**What goes wrong:**
Adding a response datagram back to the sender ("OK: QSO accepted") seems useful for debugging. It is a mistake because: (1) it breaks fire-and-forget logging software that does not read from the UDP port; (2) it creates a UDP amplification vector — each small inbound datagram triggers a response, which can be spoofed to amplify traffic toward a third party; (3) it adds bidirectional state where none is needed; (4) logging software like N1MM+ that uses `SO_REUSEADDR` for port sharing may not be the entity reading responses.

**Prevention:**
The UDP listener is strictly receive-only. No response datagrams. Log incoming QSO results (accepted/duplicate/error) to the Python logger at INFO/WARNING level for operator review via server logs, not via network responses.

**Confidence:** HIGH — UDP amplification via reflective responses is well-documented in DDoS literature; ham radio UDP integrations universally omit response datagrams.

---

## asyncio Pitfalls

### Pitfall AS-1: Blocking or Awaiting Inside `datagram_received()` — The Most Dangerous Pitfall

**What goes wrong:**
`asyncio.DatagramProtocol.datagram_received(data, addr)` is a **synchronous callback** called directly by the event loop's I/O poller. It must return immediately. Two failure modes:

1. **`await` in `datagram_received()`**: Syntax error. The method signature is `def datagram_received(...)` not `async def`. Attempting to use `await` inside it either raises a `SyntaxError` or — if the developer makes it `async def` — causes the event loop to call it synchronously and ignore the coroutine return value, meaning the Beanie operations silently never execute.

2. **Blocking Beanie/Motor call**: Motor is built on asyncio. Calling `QSO.insert()` synchronously (as if it were a blocking function) from `datagram_received()` will raise a `RuntimeError: no running event loop` in some contexts, or more insidiously, attempt to create a new event loop and deadlock.

**The correct pattern:**
```python
def datagram_received(self, data: bytes, addr: tuple) -> None:
    loop = asyncio.get_event_loop()  # or asyncio.get_running_loop() in Python 3.10+
    loop.create_task(self._handle(data, addr))

async def _handle(self, data: bytes, addr: tuple) -> None:
    # All await calls go here
    records, errors = parse_adi(data.decode("utf-8", errors="replace"))
    for record in records:
        qso_dict = build_qso_dict(record, operator)
        await qso.insert()
```

**Exceptions from tasks are silently swallowed:**
A task created via `loop.create_task()` that raises an exception logs the exception to the asyncio logger but does not propagate it anywhere. The UDP handler appears to work (no crash), but QSOs are not inserted. This requires explicit exception handling inside `_handle()`:

```python
async def _handle(self, data: bytes, addr: tuple) -> None:
    try:
        ...
    except Exception as exc:
        logger.exception("UDP handler error: %s", exc)
```

**Confidence:** HIGH — confirmed from CPython asyncio-protocol.html documentation (DatagramProtocol callbacks are synchronous); confirmed from Python asyncio docs on task exception handling.

---

### Pitfall AS-2: `asyncio.get_event_loop()` Deprecated in Python 3.10+ When No Loop Is Running

**What goes wrong:**
`asyncio.get_event_loop()` called outside a running coroutine emits a `DeprecationWarning` in Python 3.10 and will raise `RuntimeError` in future Python versions. When `datagram_received()` is called by the event loop, a loop is running — so `asyncio.get_running_loop()` works correctly here. But if `get_event_loop()` is called during protocol `__init__` (outside the running loop context, e.g., during lifespan startup before the endpoint is created), it will either warn or fail depending on the Python version.

**Ollog is on Python 3.14** (confirmed from `.venv/lib/python3.14`). The deprecation is active. On Python 3.14, `asyncio.get_event_loop()` in a non-running context raises `DeprecationWarning` or worse.

**Prevention:**
Inside `datagram_received()`, use `asyncio.get_running_loop()`. This is always correct because `datagram_received()` is called from within the running event loop. Never store a reference to the loop at `__init__` time — acquire it at the point of use.

```python
def datagram_received(self, data, addr):
    loop = asyncio.get_running_loop()  # correct: always has a running loop here
    loop.create_task(self._handle(data, addr))
```

**Confidence:** HIGH — confirmed from CPython issue #93453 and deprecation timeline discussion; confirmed ollog uses Python 3.14 from venv path.

---

### Pitfall AS-3: Unclosed Transport Leaks the UDP Socket

**What goes wrong:**
`loop.create_datagram_endpoint()` returns a `(transport, protocol)` tuple. If the transport is not explicitly closed during application shutdown, the UDP socket remains open. This has two consequences: (1) the port is not released, so restarting the app will fail with `EADDRINUSE` on the UDP port; (2) there is a resource leak warning in Python's garbage collector.

**In the ollog lifespan pattern:**
The existing `main.py` lifespan already demonstrates the correct pattern for the change stream watcher task: store the task reference, cancel it in the shutdown path, await the `CancelledError`. The UDP transport needs the same treatment:

```python
# startup
transport, protocol = await loop.create_datagram_endpoint(...)
# stored in lifespan scope

# shutdown
transport.close()
```

The transport's `close()` method is synchronous — it schedules the socket close on the event loop. The protocol's `connection_lost()` callback is called after the socket is closed. No `await` needed, but `transport.close()` must be called before `close_db()`.

**Confirmation from ollog codebase:**
`main.py` already correctly stores and cancels the `watcher_task`. The UDP transport must be stored in the same lifespan scope and closed in the shutdown path.

**Confidence:** HIGH — standard asyncio resource management; confirmed by reading `app/main.py` lifespan pattern.

---

### Pitfall AS-4: Protocol Stops Receiving After OSError on Windows (Silent Death)

**What goes wrong:**
CPython bug #88906 (open as of Python 3.14): on Windows with `ProactorEventLoop`, when `DatagramProtocol.error_received()` is triggered by an `OSError`, the protocol stops calling all subsequent callbacks — `datagram_received()` is never called again. The process continues running with no crash, no log message, no indication that UDP has stopped working. This is a silent total failure.

**For ollog's use case:**
ollog is designed for Linux (Docker container, confirmed from `docker-compose.yml`). On Linux with `SelectorEventLoop`, this bug does not occur. However, if someone runs ollog directly on Windows for development, this bug will manifest the first time a malformed datagram triggers an `error_received()` call.

**Prevention:**
Implement `error_received(exc)` in the DatagramProtocol subclass to log the error and (on Windows) potentially restart the endpoint. For Linux production deployments, document that this is a Windows-only concern.

**Confidence:** HIGH — confirmed from CPython issue #88906 and related Python bug tracker issue #44743.

---

### Pitfall AS-5: `create_datagram_endpoint()` During Lifespan — Must Be Called From a Coroutine

**What goes wrong:**
`loop.create_datagram_endpoint()` is a coroutine method — it must be `await`-ed. It cannot be called from synchronous code. The ollog lifespan is an `async` context manager, so this is natural. But the pitfall is calling it before the event loop is fully running, or after the loop has started shutting down.

**In practice:**
The `lifespan` function in `main.py` is called by Uvicorn after the event loop starts. `create_datagram_endpoint()` is safe to `await` anywhere inside the lifespan body before the `yield`. The transport must be created before `yield` (startup) and closed after `yield` (shutdown).

**Edge case:** If `create_datagram_endpoint()` fails (port already in use), the exception propagates out of the lifespan startup and kills the application startup. This is correct behavior — fail fast on port conflict — but the error message from the OS (`[Errno 98] Address already in use`) should be caught and re-raised with a more descriptive message.

**Confidence:** HIGH — asyncio event loop documentation; confirmed from `main.py` lifespan structure.

---

## Operational Pitfalls

### Pitfall O-1: UDP Port Conflict — Different Error Behavior from TCP

**What goes wrong:**
If another process is already listening on the configured UDP port, `create_datagram_endpoint()` raises `OSError: [Errno 98] Address already in use`. Unlike TCP, there is no `SO_REUSEADDR` behavior that lets two processes share a UDP port under normal circumstances. (Note: asyncio sets `SO_REUSEADDR` by default on UDP sockets on Linux, which _does_ allow two processes to bind the same port — see CPython issue #81409. This can cause the second process to silently receive no datagrams if both are listening, which is worse than an error.)

**For ollog:**
The default UDP port choice matters. Port 2237 (WSJT-X's native port) should not be used as ollog's default — ollog is a secondary receiver, not WSJT-X itself. Port 12060 (N1MM+ default) is similarly occupied on contest computers. A dedicated high-numbered port (e.g., 2399 or a configurable `UDP_PORT` env var) is the right choice. Always make the port configurable.

**Warning signs:**
- UDP listener starts with no error but receives no datagrams.
- Two processes bound to the same UDP port on Linux (asyncio's default `SO_REUSEADDR` behavior can allow this).

**Prevention:**
Add a `UDP_PORT` setting to `app/config.py`. Choose a default port that does not conflict with WSJT-X (2237) or N1MM+ (12060). Log the bind address and port at startup: `"UDP listener bound to {host}:{port}"`.

**Confidence:** MEDIUM — port conflict behavior is platform-dependent; CPython issue #81409 confirms the silent multiple-bind risk on Linux.

---

### Pitfall O-2: Docker Compose — UDP Ports Require Explicit `/udp` Protocol Annotation

**What goes wrong:**
Docker Compose's `ports:` directive defaults to TCP. A port mapping `"2399:2399"` maps TCP only. UDP datagrams to the host on port 2399 are **not forwarded** to the container. The app starts, the UDP listener starts, the logging software sends datagrams, and nothing arrives. There is no error — the port just silently discards UDP traffic.

**Concrete fix required in `docker-compose.yml`:**
```yaml
ports:
  - "8000:8000"          # existing HTTP (TCP)
  - "2399:2399/udp"      # UDP listener — must specify /udp
```

Without `/udp`, the UDP port is never exposed from the container, regardless of what the Python code does.

**Confidence:** HIGH — confirmed from Docker documentation on port publishing; this is a very common and silent misconfiguration.

---

### Pitfall O-3: Malformed Datagram Noise From Port Scanners

**What goes wrong:**
Any open UDP port on a networked machine will receive random garbage from port scanners, misconfigured software, and network probes. On a VPS or any internet-exposed host, this is constant background noise. Each malformed datagram goes through `parse_adi()` (which handles malformed input gracefully), but if logged at INFO level, it floods the application logs. If logged at ERROR level, it creates alert fatigue.

**For ollog's self-hosted/LAN use case:**
If bound to `127.0.0.1` (loopback only), port scanner noise is impossible — no external traffic reaches loopback. If bound to `0.0.0.0` on a VPS, this is a real concern.

**Prevention:**
Log malformed datagrams at DEBUG level, not INFO or WARNING. Only log at INFO or above for successfully parsed or duplicate QSOs. Emit a single WARNING if a source IP sends more than N malformed datagrams in a time window (simple in-memory counter is sufficient for LAN use).

**Confidence:** MEDIUM — standard operational concern for any open UDP port; the loopback default prevents this entirely.

---

### Pitfall O-4: No Connection State — "Listener Connected" Is Meaningless

**What goes wrong:**
With TCP, the server can tell when a client connects and disconnects. With UDP, there is no concept of a connected logger. The admin UI or monitoring endpoint cannot report "WSJT-X is connected" — only "a datagram arrived from 127.0.0.1 at 14:32:07." If logging software crashes silently, ollog has no way to know.

**Impact on ollog:**
This is not a code bug — it is a documentation and expectation-setting issue. Operators accustomed to the REST API's visible session must understand that UDP is receive-and-forget. Health check endpoints should not report "UDP client connected" — they can only report "UDP listener is running."

**Prevention:**
In the health check response (`GET /health`), add a field like `"udp_listener": "running"` or `"udp_listener": "disabled"`. Track the timestamp of the last successfully processed datagram: `"udp_last_received": "2026-04-05T14:32:07Z"` or `null`. This gives operators a way to verify the listener is receiving traffic without implying a connection model that does not exist.

**Confidence:** HIGH — fundamental UDP property; operational recommendation is new for ollog.

---

## Security Pitfalls

### Pitfall S-1: UDP Amplification — Do Not Respond to Datagrams

**What goes wrong:**
If the UDP handler sends response datagrams back to the source address, it becomes an amplifier: an attacker spoofs the source IP (UDP source IPs are trivially spoofable) and the response datagrams flood the victim. Even small amplification ratios (2:1) make this a meaningful DDoS tool.

**For ollog specifically:**
The planned design is receive-only (no ACK). The risk only exists if a developer adds response datagrams for debugging. This must be explicitly prohibited in the implementation: the `DatagramTransport.sendto()` method must never be called from `datagram_received()`.

**Self-hosted LAN context:**
On a home LAN or VPS with firewall, amplification risk is low but not zero (a compromised LAN host could exploit this). Receive-only is correct regardless.

**Confidence:** HIGH — UDP amplification is a well-established attack vector in the security literature.

---

### Pitfall S-2: Open UDP Port on Internet-Exposed VPS

**What goes wrong:**
Binding to `0.0.0.0` on a VPS exposes the UDP port to the public internet. Even without auth, the cost is: constant malformed datagram noise, potential DoS via high-volume UDP flood filling the receive buffer, and any attacker who guesses the ADIF format can inject QSOs into the log.

**For ollog's deployment model:**
The primary use case is local (loopback) or LAN. For VPS deployments, the correct guidance is: bind to `127.0.0.1` (default), and if LAN access is needed, use firewall rules (`ufw`, `iptables`, or cloud security group) to restrict the UDP port to the operator's LAN subnet, not the general public internet.

**Prevention in config:**
Default `UDP_BIND_HOST=127.0.0.1`. Document that changing to `0.0.0.0` without firewall rules is insecure. The `app/config.py` should not provide a default that opens the port to the internet.

**Confidence:** HIGH — standard network security principle; the loopback default is the concrete prevention.

---

### Pitfall S-3: Rate Limiting Without Connection State

**What goes wrong:**
The REST API can rate-limit by IP using Starlette middleware or per-user with request context. UDP has no equivalent — every datagram is independent. A burst of datagrams from any source (legitimate burst or attack) will launch a corresponding burst of `asyncio.create_task()` calls and Beanie insert operations.

**For ollog's self-hosted use case:**
A legitimate burst from N1MM+ during a contest pile-up could be 5–10 QSOs/minute. A malicious burst from a local attacker could be thousands/second. In a LAN environment, the realistic threat is misconfigured software flooding the port, not a targeted attack.

**Prevention:**
Implement a simple in-memory token bucket or counter per source IP in `datagram_received()` (synchronous, no Beanie needed). If a source IP sends more than N datagrams per second (e.g., 60/sec), drop subsequent datagrams and log at WARNING. This prevents a misconfigured logger from creating thousands of duplicate tasks.

**Confidence:** MEDIUM — the threat model for self-hosted LAN is low; the prevention is straightforward to implement.

---

## ollog-Specific Pitfalls

### Pitfall OL-1: `build_qso_dict()` Requires a `User` Object for Profile Stamping — Not Just a Callsign

**What goes wrong:**
The existing `build_qso_dict(body_dict, operator, profile=None)` in `app/qso/service.py` accepts an optional `profile` argument (a `User` document). When `profile` is not `None`, it stamps `OPERATOR`, `STATION_CALLSIGN`, `MY_GRIDSQUARE`, `MY_RIG`, `MY_ANTENNA`, and `TX_PWR` from the profile. When `profile=None` (as in the ADIF import path), no profile fields are stamped.

For the UDP path, there are two plausible designs:
1. **No profile stamping**: Call `build_qso_dict(record, operator, profile=None)`. QSOs are inserted without profile metadata. Consistent with the ADIF import path.
2. **Profile stamping**: Look up the `User` document in `datagram_received()`'s async handler. QSOs get the same stamp as REST API QSOs.

**The pitfall:**
If design 2 is chosen but the `User.find_one()` call is placed inside `datagram_received()` directly (synchronously), it fails with a Motor coroutine error. It must be inside the `_handle()` coroutine dispatched via `create_task()`. This is the same async boundary pitfall as AS-1, but specifically about the User lookup.

**Additional concern:**
The UDP listener must resolve the operator identity from the IP allowlist configuration — there is no JWT to decode. The mapping from "source IP = 127.0.0.1" to "operator = W1AW" is a configuration concern, not a runtime JWT concern. If multiple operators share a LAN and the listener is on `0.0.0.0`, operator attribution is ambiguous without per-port-or-per-IP assignment.

**Recommendation:**
For a single-operator or single-station UDP listener, configure a `UDP_OPERATOR` setting in `.env` that maps to an operator callsign. The UDP handler looks up that operator's `User` document once at startup (during lifespan) and reuses the cached `User` object for all datagrams. This avoids a MongoDB round-trip per datagram and resolves the identity ambiguity.

**Confidence:** HIGH — confirmed by reading `app/qso/service.py` `build_qso_dict()` signature and `app/qso/router.py` create_qso implementation.

---

### Pitfall OL-2: Duplicate Detection Works Correctly for UDP — But Only If `qso_date_utc` Is Populated

**What goes wrong:**
`find_duplicate()` in `app/qso/service.py` queries `_operator`, `CALL`, `BAND`, `MODE`, `_deleted`, and `qso_date_utc` using a ±2 minute window. This depends entirely on `qso_date_utc` being correctly populated by `build_qso_dict()` → `parse_adif_datetime()`.

ADIF datagrams from logging software include `QSO_DATE` and `TIME_ON` fields set to the time the operator logged the contact. This is correct and the duplicate detection will work as designed. The pitfall occurs if the datagram is missing `QSO_DATE` or `TIME_ON` — `build_qso_dict()` will raise a `KeyError`, which must be caught in the UDP handler and treated as a malformed record (not a crash).

**Verification:**
The existing ADIF import path (`app/adif/router.py`) wraps `build_qso_dict()` in a `try/except (ValueError, KeyError)`. The UDP handler must do the same.

**SSE feed behavior:**
UDP-inserted QSOs will appear in the live SSE feed. The feed watcher (`app/feed/manager.py`) watches MongoDB change events for any insert to the `qsos` collection. Since the UDP handler calls `QSO.insert()` (the same path as the REST API), the change stream fires and the SSE broadcast works without any modification. This is confirmed by reading `app/feed/manager.py` — it watches the collection, not a specific code path.

**Confidence:** HIGH — confirmed by reading `app/qso/service.py` (`find_duplicate` logic), `app/adif/router.py` (error handling pattern), and `app/feed/manager.py` (change stream watches entire collection).

---

### Pitfall OL-3: Operator Isolation — UDP Datagram Can Claim Any Callsign

**What goes wrong:**
The REST API enforces operator isolation strictly: `operator_callsign` is always taken from the JWT (`user.callsign`), never from the request body. The `create_qso()` endpoint ignores any `OPERATOR` field in the request body; it is overwritten by `build_qso_dict()` using the JWT-derived callsign.

For UDP, there is no JWT. If the datagram contains an `OPERATOR` ADIF field, `build_qso_dict()` _does_ write it to the QSO document — but this is the ADIF `OPERATOR` field (the person at the key), not the `_operator` isolation field (set from the UDP configuration). The `_operator` field is set from the `operator` parameter passed to `build_qso_dict()`, which in the UDP design comes from the configured `UDP_OPERATOR` setting, not from the datagram.

**The pitfall:**
If the `_operator` field is taken from the ADIF `OPERATOR` field inside the datagram (a tempting shortcut), an attacker on the LAN who can send UDP datagrams can forge QSOs into any operator's log by spoofing the `OPERATOR` field. The `_operator` must always come from configuration, never from the datagram.

**Confidence:** HIGH — confirmed by reading `build_qso_dict()` in `app/qso/service.py` (the `operator` parameter sets `result["operator_callsign"]` directly, separate from the ADIF `OPERATOR` field).

---

### Pitfall OL-4: `process_import()` in `app/adif/router.py` Is Not Directly Reusable for UDP

**What goes wrong:**
`process_import()` in `app/adif/router.py` contains most of the ADIF-to-QSO insertion logic. It looks like it could be called from a UDP handler. It cannot — it raises `HTTPException` for oversized files, which is a Starlette-specific exception that only makes sense in HTTP request context. Calling it from a UDP handler context would raise `HTTPException` (a class that inherits from `Exception`) which would be caught by the general exception handler in the task, logged, and silently swallowed.

**Additionally:**
`process_import()` does not perform profile stamping (calls `build_qso_dict(record, operator)` with no `profile` argument, consistent with the ADIF import-file path). If UDP QSOs should receive profile stamping, `process_import()` is not the right function to call.

**Correct approach:**
Extract the core per-record insertion logic (`parse_adi` → validate required fields → `build_qso_dict` → `find_duplicate` → `QSO.insert()`) into a shared `insert_qso_from_adif(record, operator, profile)` function in `app/qso/service.py` or `app/adif/service.py`. Both the HTTP import endpoint and the UDP handler call this shared function. The HTTP endpoint adds its own size check and `HTTPException` wrapping on top.

**Confidence:** HIGH — confirmed by reading `app/adif/router.py` (HTTPException raised at line 71 in `process_import()`).

---

## Prevention Strategies

### Which Pitfalls to Explicitly Handle in Implementation

| Pitfall | Required Implementation Action |
|---------|-------------------------------|
| AS-1 (sync/async boundary) | `datagram_received()` must be `def`, not `async def`; all Beanie calls dispatched via `create_task(_handle(...))` with `try/except` inside `_handle` |
| AS-2 (get_event_loop deprecated) | Use `asyncio.get_running_loop()` inside `datagram_received()` |
| AS-3 (unclosed transport) | Store transport in lifespan scope; call `transport.close()` in shutdown path before `close_db()` |
| AS-4 (Windows OSError silent failure) | Implement `error_received(exc)` method with explicit logging |
| A-1 (no JWT in datagrams) | Bind to `127.0.0.1` by default; add `UDP_BIND_HOST` and `UDP_PORT` to `config.py` |
| A-4 (IP allowlist without bind) | Default bind to `127.0.0.1`; add Python-level source IP check when `UDP_BIND_HOST=0.0.0.0` |
| O-2 (Docker UDP /udp annotation) | Add `"<port>:<port>/udp"` to `docker-compose.yml` ports section |
| OL-1 (User lookup and profile stamping) | Cache operator `User` document at startup; add `UDP_OPERATOR` setting to config |
| OL-2 (missing QSO_DATE/TIME_ON) | Wrap `build_qso_dict()` call in `try/except (ValueError, KeyError)` |
| OL-3 (operator isolation) | `_operator` always from `UDP_OPERATOR` config, never from datagram ADIF fields |
| OL-4 (HTTPException in process_import) | Do not reuse `process_import()` from UDP; extract shared insertion logic |
| S-1 (no response datagrams) | Never call `transport.sendto()` from `datagram_received()` |

### Which to Document as Operational Guidance

| Pitfall | Operator Documentation Note |
|---------|----------------------------|
| A-3 (expired token) | Non-issue if JWT is not used in datagrams; document that UDP_OPERATOR must match an enabled account |
| R-1 (datagram drop) | Fire-and-forget: verify QSOs in the log after a session; UDP does not guarantee delivery |
| R-2 (datagram size) | One QSO per datagram; bulk multi-QSO datagrams may be truncated |
| O-1 (port conflict) | Configure `UDP_PORT` to avoid conflicts with WSJT-X (2237) and N1MM+ (12060) |
| O-3 (port scanner noise) | Bind to loopback unless LAN access is needed; do not expose UDP port to internet |
| O-4 (no connection state) | Health check shows last datagram timestamp, not a "connected" status |
| S-2 (open UDP on VPS) | Default bind is loopback; set firewall rules before changing to 0.0.0.0 |

### Which Are Non-Issues for the Self-Hosted LAN Use Case

| Pitfall | Why Non-Issue |
|---------|--------------|
| A-2 (token replay) | Not using JWT in datagrams; loopback bind makes capture impossible |
| R-3 (ACK amplification) | Receive-only design eliminates this entirely |
| S-3 (rate limiting) | Legitimate logging software produces < 5 QSOs/minute; a simple in-memory counter is sufficient; no external attack surface on loopback |
| O-3 (scanner noise) | Non-issue when bound to loopback; low risk on trusted LAN |

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| UDP listener bootstrap (lifespan) | AS-5 (startup failure on port conflict) | Catch `OSError` in lifespan, log descriptive message, re-raise |
| DatagramProtocol implementation | AS-1 (sync/async boundary) | Code review gate: `datagram_received` must be `def`, not `async def`; all awaits in `_handle()` |
| Operator identity resolution | OL-1 (User lookup), OL-3 (isolation) | Cache User at startup; never read operator from datagram |
| ADIF parsing from raw bytes | OL-2 (missing fields) | Wrap in try/except; log at WARNING per malformed record |
| Docker compose configuration | O-2 (/udp annotation) | Test UDP delivery from host before declaring done |
| Config additions | O-1 (port conflict), A-4 (bind host) | UDP_PORT and UDP_BIND_HOST in config.py with explicit defaults |
| Shutdown / cleanup | AS-3 (transport leak) | transport.close() in lifespan shutdown before close_db() |

---

## Sources

- CPython asyncio Transports and Protocols documentation: https://docs.python.org/3/library/asyncio-protocol.html
- CPython issue #88906 (DatagramProtocol stops after OSError on Windows): https://github.com/python/cpython/issues/88906
- CPython issue #81409 (UDP sockets allow multiple processes to bind same port): https://github.com/python/cpython/issues/81409
- CPython issue #93453 (get_event_loop deprecation): https://github.com/python/cpython/issues/93453
- N1MM+ External UDP Broadcasts (no auth, XML format, port 12060): https://n1mmwp.hamdocs.com/appendices/external-udp-broadcasts/
- WSJT-X User Guide (UDP server, port 2237, no auth): https://wsjt.sourceforge.io/wsjtx-doc/wsjtx-main-2.6.1.html
- CQRLOG ADIF UDP logger (UDP format, single QSO records): https://www.cqrlog.com/help/adif.html
- JWT replay attack prevention (jti claim): https://elsyarifx.medium.com/the-hidden-power-of-jti-how-a-single-claim-can-stop-token-replay-attacks-0255fbcf6b9b
- Docker port publishing and UDP: https://docs.docker.com/engine/network/port-publishing/
- Beanie thread safety discussion: https://github.com/BeanieODM/beanie/discussions/345
- Python asyncio policy system deprecation timeline: https://discuss.python.org/t/removing-the-asyncio-policy-system-asyncio-set-event-loop-policy/37553
- FastAPI Lifespan Events documentation: https://fastapi.tiangolo.com/advanced/events/
- Codebase: `app/main.py`, `app/qso/service.py`, `app/qso/router.py`, `app/adif/router.py`, `app/auth/service.py`, `app/auth/dependencies.py`, `app/feed/manager.py`, `app/config.py`, `docker-compose.yml` (direct inspection, HIGH confidence)

---
*Pitfalls research for: adding UDP ADIF ingestion to ollog (FastAPI + Beanie/MongoDB ham radio logbook)*
*Researched: 2026-04-05*
