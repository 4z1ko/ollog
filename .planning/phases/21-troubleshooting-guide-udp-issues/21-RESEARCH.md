# Phase 21: Troubleshooting Guide — UDP Issues - Research

**Researched:** 2026-04-08
**Domain:** Technical documentation — operator-facing troubleshooting entries for UDP ADIF ingestion
**Confidence:** HIGH (all findings from direct codebase inspection)

## Summary

Phase 21 is a pure documentation task. The output is four new entries appended to `docs/troubleshooting.md`, following the established heading/format pattern already in that file. No code changes are required.

All log messages, env var names, defaults, and error conditions were verified by reading the actual source files. The exact strings below should be quoted verbatim in the troubleshooting entries — operators copy-paste from log output to match the relevant entry.

**Primary recommendation:** Model each new entry exactly on the existing three entries in `docs/troubleshooting.md` — Symptom / Cause / Fix structure with numbered fix steps and inline code blocks for log lines and commands.

---

## Existing Document Structure (HIGH confidence — read from source)

File: `docs/troubleshooting.md`

- Uses `##` for each entry heading (no deeper nesting in current entries)
- Each entry has three bold labels: **Symptom**, **Cause**, **Fix**
- Fix steps use numbered lists; code/log snippets use fenced code blocks (no language tag, just triple backticks)
- Three existing entries: SSE Station Feed Not Updating, Login Fails After Container Restart, ADIF Import Returns All Duplicates
- A new `## UDP` section or four individual entries at `##` level would both be consistent — four individual entries matches current convention

---

## Configuration — Exact Env Vars and Defaults (HIGH confidence — `app/config.py`)

| Env Var | Type | Default | Purpose |
|---|---|---|---|
| `UDP_ENABLED` | bool | `false` | Master on/off switch for UDP listener |
| `UDP_PORT` | int | `2399` | UDP port to bind |
| `UDP_BIND_HOST` | str | `127.0.0.1` | Interface to bind; must be `0.0.0.0` inside Docker |
| `UDP_OPERATOR` | str | `None` | Callsign of the operator account for QSO attribution |

Docker note (from `docker-compose.yml` comments): `UDP_BIND_HOST=0.0.0.0` is required inside Docker because the default `127.0.0.1` blocks datagrams from the host. Port `2399/udp` is published in docker-compose.

---

## Exact Log Messages (HIGH confidence — `app/udp/server.py` and `app/main.py`)

### Startup / healthy path

**Listener bound successfully** (`app/udp/server.py`, `start_udp_listener`):
```
UDP listener bound to {host}:{port}
```
Example: `UDP listener bound to 0.0.0.0:2399`

**Operator callsign not found at startup** (`app/main.py`, lifespan):
```
UDP_OPERATOR callsign {callsign!r} not found in DB — profile stamping disabled
```
Example: `UDP_OPERATOR callsign 'W1AW' not found in DB — profile stamping disabled`
Note: The listener still starts and datagrams are still processed (operator string is passed, profile stamping is just disabled).

### Per-datagram path

**Datagram received** (INFO — `QSODatagramProtocol.datagram_received`):
```
UDP datagram received from {ip}:{port} ({n} bytes)
```

**UDP_OPERATOR not configured — datagram discarded** (WARNING — `_handle_datagram`):
```
UDP_OPERATOR not configured — datagram from {addr} discarded
```

**Parse failure** (WARNING):
```
UDP datagram src={ip}:{port} disposition=rejected reason=parse-failure
```

**Missing required ADIF field** (WARNING):
```
UDP datagram src={ip}:{port} disposition=rejected reason="missing required field: {field}"
```
Required fields: `CALL`, `QSO_DATE`, `TIME_ON`, `BAND`, `MODE` (from `app/qso/service.py`, `_REQUIRED_FIELDS`)

**Duplicate** (INFO):
```
UDP datagram src={ip}:{port} call={callsign} disposition=duplicate
```

**Accepted / inserted** (INFO):
```
UDP datagram src={ip}:{port} call={callsign} disposition=accepted id={mongo_id}
```

**Transport error** (WARNING — `QSODatagramProtocol.error_received`):
```
UDP transport error: {exc}
```

**Multiple records in single datagram** (WARNING — informational, first record processed):
```
UDP datagram src={ip}:{port}: {n} records found, processing first only
```

---

## The Four Required Troubleshooting Entries

### Entry 1: UDP Socket Binding Failures (DOC-08)

**Symptom:** Container fails to start, or UDP datagrams are never received and the startup log does NOT contain `UDP listener bound to`.

**Causes:**
1. Port already in use — another process has bound `UDP_PORT` (default `2399`)
2. `UDP_BIND_HOST` mismatch — default is `127.0.0.1`, which blocks external traffic inside Docker

**Fix (port in use):** Check what is using port 2399 on the host (`lsof -iUDP:2399`) and stop it, or change `UDP_PORT` in `.env`.

**Fix (bind host):** In Docker, set `UDP_BIND_HOST=0.0.0.0` in `.env`. The docker-compose.yml already publishes `2399/udp` but the listener must bind to all interfaces, not loopback.

**Verification log line operators look for:**
```
UDP listener bound to 0.0.0.0:2399
```

### Entry 2: UDP_OPERATOR Callsign Not Found (DOC-09)

**Symptom:** Log at startup contains WARNING about callsign not found; all incoming datagrams are discarded with "UDP_OPERATOR not configured".

There are two distinct sub-cases:
- **A: `UDP_OPERATOR` not set at all** — `_handle_datagram` emits `UDP_OPERATOR not configured — datagram from {addr} discarded` for every datagram.
- **B: `UDP_OPERATOR` is set but callsign doesn't match a user record** — startup warning fires, but datagrams are still accepted (profile stamping just disabled). This is NOT a blocking error.

Wait — re-reading `app/main.py`: when `udp_user is None` (callsign not found), the startup warning fires but `udp_op` (the string) is still passed to `start_udp_listener`. So `operator` is not None inside `_handle_datagram`, and QSOs are still inserted (without profile data). The "datagram discarded" path fires only when `udp_op` itself is None (i.e., `UDP_OPERATOR` was never set).

**Fix for completely missing `UDP_OPERATOR`:** Set `UDP_OPERATOR=<callsign>` in `.env`.

**Fix for callsign not found in DB:** Create the user account first via the admin UI or bootstrap env vars; ensure the callsign matches exactly (case is normalised to uppercase internally, but the account must exist with that uppercase callsign).

**Key log lines:**
```
# Startup — callsign set but user not in DB
UDP_OPERATOR callsign 'W1AW' not found in DB — profile stamping disabled

# Per-datagram — UDP_OPERATOR not configured at all
UDP_OPERATOR not configured — datagram from ('192.168.1.10', 54321) discarded
```

### Entry 3: QSOs Arriving But Not Appearing in Log (DOC-10)

**Symptom:** Log shows `UDP datagram received from ...` but no new QSO appears in the log view.

**Causes:**
1. Missing required ADIF field — record lacks one of `CALL`, `QSO_DATE`, `TIME_ON`, `BAND`, `MODE`
2. Duplicate — same CALL/BAND/MODE within ±2 minutes of an existing QSO

**Log lines for diagnosis:**
```
# Missing required field
UDP datagram src=192.168.1.10:54321 disposition=rejected reason="missing required field: QSO_DATE"

# Duplicate
UDP datagram src=192.168.1.10:54321 call=W1AW disposition=duplicate

# Successful insert (what you want to see)
UDP datagram src=192.168.1.10:54321 call=W1AW disposition=accepted id=...
```

**Fix (missing field):** Ensure the logging software sends all required fields: `CALL`, `QSO_DATE`, `TIME_ON`, `BAND`, `MODE`.

**Fix (duplicate):** Duplicates are intentional behaviour. If a QSO was logged twice within 2 minutes, the second is silently skipped. Check the existing log for the QSO; if it needs updating, delete and re-log.

### Entry 4: No UDP Activity in Logs (DOC-11)

**Symptom:** No `UDP listener bound` line and no `UDP datagram received` lines in container logs.

**Cause:** `UDP_ENABLED` is not set, or is set to `false`. The listener is never started.

**Fix:** Add `UDP_ENABLED=true` to `.env` and restart the container. Also set `UDP_OPERATOR` and (for Docker) `UDP_BIND_HOST=0.0.0.0`.

**Verification:** After restart, look for:
```
UDP listener bound to 0.0.0.0:2399
```

---

## Architecture Patterns

### How to insert the new section

The existing file has no section grouping (three flat `##` entries). Two options:

1. **Flat entries (matches current convention):** Add four `##` entries after the existing three, one per scenario.
2. **Grouped under `## UDP Listener`:** Add a `## UDP Listener` section with `###` sub-entries.

Option 1 is the safer match to existing style. Option 2 is more navigable for operators. Either works — planner should choose and document the decision.

### Log-tailing commands for operators

For the troubleshooting entries, operators will need to know how to see logs:
```bash
docker compose logs -f api | grep -i udp
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---|---|---|
| Log format | Don't invent log format — it's already set by the live code | Quote exact strings from `app/udp/server.py` and `app/main.py` |
| Env var names | Don't guess — they are in `app/config.py` | Copy verbatim: `UDP_ENABLED`, `UDP_PORT`, `UDP_BIND_HOST`, `UDP_OPERATOR` |

---

## Common Pitfalls When Writing Troubleshooting Entries

### Pitfall 1: Quoting Log Messages Approximately
**What goes wrong:** If the doc says `"operator not found"` but the actual log says `"UDP_OPERATOR callsign 'W1AW' not found in DB — profile stamping disabled"`, operators can't grep for it.
**Prevention:** Quote exact strings from source. All messages above are taken directly from the code.

### Pitfall 2: Conflating "callsign not found at startup" with "datagram discarded"
**What goes wrong:** Entry 2 has two distinct sub-cases. The startup WARNING when callsign is absent from DB does NOT prevent QSO insertion — only the missing `UDP_OPERATOR` config does.
**Prevention:** The entry must explain both: missing config = datagrams discarded; callsign not in DB = QSOs inserted without profile stamping.

### Pitfall 3: Wrong bind host instruction
**What goes wrong:** Saying "use `127.0.0.1`" for Docker deployments — it blocks external traffic.
**Prevention:** Explicitly distinguish bare-metal (127.0.0.1 is fine) vs Docker (must be 0.0.0.0).

---

## Sources

### Primary (HIGH confidence — direct codebase read)
- `/Users/royco/ollog/app/udp/server.py` — all per-datagram log messages
- `/Users/royco/ollog/app/main.py` — startup log messages, lifespan UDP startup logic
- `/Users/royco/ollog/app/config.py` — exact env var names and defaults
- `/Users/royco/ollog/app/qso/service.py` — `_REQUIRED_FIELDS = {"CALL", "QSO_DATE", "TIME_ON", "BAND", "MODE"}`
- `/Users/royco/ollog/docs/troubleshooting.md` — existing document structure and format
- `/Users/royco/ollog/docker-compose.yml` — UDP port publishing and comments

### Secondary (MEDIUM confidence)
None needed — all findings are from direct source inspection.

---

## Open Questions

1. **Grouped vs. flat section structure**
   - What we know: Existing file uses flat `##` entries
   - What's unclear: Whether four new UDP entries should be grouped under a `## UDP Listener` heading
   - Recommendation: Planner decides; flat `##` entries are safest match to current style

2. **Log level visibility**
   - What we know: "datagram received" and "accepted/duplicate" are INFO; errors are WARNING
   - What's unclear: What log level is configured by default in the deployed container
   - Recommendation: Troubleshooting entries should note that INFO-level logs must be visible; if not, operators may need `LOG_LEVEL=INFO` (need to verify if this env var exists — not found in `config.py`, may be set via uvicorn CLI args)

---

## Metadata

**Confidence breakdown:**
- Log messages: HIGH — copied verbatim from source
- Env var names/defaults: HIGH — from `app/config.py`
- Document format/structure: HIGH — from reading `docs/troubleshooting.md`
- Required ADIF fields: HIGH — from `app/qso/service.py`

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable — pure documentation over stable code)
