# Features Research: UDP ADIF Listener for ollog

**Domain:** Ham radio QSO logging — UDP datagram reception of ADIF-formatted contact records
**Researched:** 2026-04-05
**Overall confidence:** HIGH for N1MM+/WSJT-X protocol formats (multiple corroborating sources); MEDIUM for auth patterns (no established convention — design decision required); HIGH for "what not to build" (consensus from ecosystem observation)

---

## Summary

The ham radio logging ecosystem has two dominant UDP broadcast formats for QSO data: **N1MM Logger+ XML over UDP** and **WSJT-X binary Qt-serialized UDP**. Neither uses raw ADIF as the datagram payload in their native format. However, a third convention exists: **raw ADIF ADI text as the UDP payload**, used by VarAC, Log4OM's inbound ADIF reception, and several bridge scripts that connect WSJT-X to loggers like Cloudlog. This third convention is the simplest to implement on the receiver side and is what ollog should support.

There is **no ADIF specification for UDP transport**. The ADIF spec (currently v3.1.6, adif.org) defines only file and data interchange format — it says nothing about network transport. All UDP conventions in ham radio are application-defined.

Authentication over UDP is an unsolved problem in the ham radio ecosystem. The convention is: **no auth**. All existing UDP logging is designed for localhost or LAN use. ollog is different because it is self-hosted and multi-operator. A pre-shared API key embedded in the ADIF payload as an `APP_` field is the pragmatic, ecosystem-compatible solution. JWTs are not appropriate for UDP.

---

## Existing UDP ADIF Conventions

### What the ADIF Spec Says About Transport

Nothing. ADIF 3.1.6 (adif.org/316) defines only the tag-stream format (`<FIELD:LEN>value<EOR>`) and the ADX XML variant. There is no UDP framing, port number, or transport specification in the ADIF standard. Confidence: HIGH (verified against adif.org).

### The Three Ecosystems

| Logger | Transport | Format | Port | Auth |
|--------|-----------|--------|------|------|
| N1MM Logger+ | UDP | XML (not ADIF) | 12060 (configurable) | None — LAN only |
| WSJT-X | UDP | Binary Qt-serialized with ADIF payload in msg type 12 | 2237 (configurable) | None — localhost default |
| VarAC, Log4OM inbound, bridge scripts | UDP | Raw ADIF ADI text | 12060 (convention) or configurable | None |

---

## N1MM+ Format

### Wire Format

N1MM Logger+ broadcasts **XML** over UDP, not ADIF. This is a critical distinction. The XML is sent as plain UTF-8 bytes with no framing beyond the datagram boundary.

Port: **12060** is the conventional default. Documented as "LookupInfo packets" default port. Configurable in N1MM settings under Config > Config Ports > Broadcast Data. Multiple destination IPs can be configured.

Message types:
- `<contactinfo>` — new QSO logged
- `<contactreplace>` — existing QSO edited
- `<contactdelete>` — QSO deleted
- `<RadioInfo>` — radio state (frequency, mode) — not a QSO record

### ContactInfo XML Structure

```xml
<?xml version="1.0" encoding="utf-8"?>
<contactinfo>
  <app>N1MM</app>
  <contestname>CWOPS</contestname>
  <contestnr>73</contestnr>
  <timestamp>2020-01-17 16:43:38</timestamp>
  <mycall>W2XYZ</mycall>
  <band>3.5</band>
  <rxfreq>352519</rxfreq>
  <txfreq>352519</txfreq>
  <operator></operator>
  <mode>CW</mode>
  <call>W1AW</call>
  <countryprefix>K</countryprefix>
  <wpxprefix>W1</wpxprefix>
  <stationprefix>W2XYZ</stationprefix>
  <continent>NA</continent>
  <snt>599</snt>
  <sntnr>5</sntnr>
  <rcv>599</rcv>
  <rcvnr>0</rcvnr>
  <gridsquare></gridsquare>
  <exchangel></exchangel>
  <section></section>
  <comment></comment>
  <qth></qth>
  <name></name>
  <power></power>
  <misctext></misctext>
  <zone>5</zone>
  <prec></prec>
  <ck>0</ck>
  <ismultiplier1>0</ismultiplier1>
  <ismultiplier2>0</ismultiplier2>
  <ismultiplier3>0</ismultiplier3>
  <points>1</points>
  <radionr>1</radionr>
  <RoverLocation></RoverLocation>
  <RadioInterfaced>0</RadioInterfaced>
  <IsRunQSO>0</IsRunQSO>
  <timestamp>2020-01-17 16:43:38</timestamp>
  <IsClaimedQso>1</IsClaimedQso>
</contactinfo>
```

Note: `<band>` is in MHz (3.5, 7, 14, 21, 28 etc.), not the ADIF band string ("40M", "20M"). `<timestamp>` format is `YYYY-MM-DD HH:MM:SS` UTC — not ADIF's YYYYMMDD/HHMM format.

### Implication for ollog

N1MM+ does **not** send raw ADIF. An ollog UDP listener that accepts N1MM+ datagrams would need an XML parser path. This is worth supporting as a **differentiator** (N1MM+ is the dominant contest logger), but NOT as the primary format for ollog's own simple ADIF-over-UDP interface.

Sources: [N1MM External UDP Messages](https://n1mmwp.hamdocs.com/appendices/external-udp-broadcasts/), [n1kdo/n1mm_view](https://github.com/n1kdo/n1mm_view), [TR4W UDP issue](https://github.com/n4af/TR4W/issues/74)

---

## WSJT-X Format

### Wire Format

WSJT-X uses a **binary, Qt-serialized protocol** over UDP. Port default: **2237**. The protocol is documented in the source file `Network/NetworkMessage.hpp` in the WSJT-X source tree. Every datagram begins with:

```
Bytes 0-3:   Magic number   (0xADBCCBDA, big-endian uint32)
Bytes 4-7:   Schema number  (uint32, currently 2)
Bytes 8-11:  Message type   (uint32, see types below)
Bytes 12-15: Client ID len  (uint32 = N)
Bytes 16...: Client ID      (N bytes, UTF-8)
```

Strings are encoded as `uint32 length` followed by `length` bytes of UTF-8 (Qt's QDataStream convention).

### Relevant Message Types

| Type | Name | Description |
|------|------|-------------|
| 5 | QSO Logged | Sent when user clicks OK in the log QSO dialog. Binary-encoded fields (date, DX call, grid, frequency, mode, RST sent/rcvd, etc.) |
| 12 | Logged ADIF | Also sent at QSO log time. Payload contains a **complete valid ADIF ADI file** as a UTF-8 string (with `<adif_ver:5>3.0.7 <programid:6>WSJT-X <EOH>` header, one record, `<EOR>`). |

### Type 12 (Logged ADIF) — Key Detail

Message type 12 payload after the header section:

```
uint32: length of ADIF text string
bytes:  ADIF ADI text, valid ADIF file, one record
```

Example ADIF content of the string field:
```
<adif_ver:5>3.0.7 <programid:6>WSJT-X <EOH>
<call:5>W1ABC <gridsquare:4>FN42 <mode:4>FT8 <rst_sent:3>-10 <rst_rcvd:3>-12
<qso_date:8>20231015 <time_on:6>143022 <qso_date_off:8>20231015 <time_off:6>143052
<band:3>20m <freq:8>14074000 <station_callsign:5>W2XYZ <my_gridsquare:4>FN20 <EOR>
```

The receiving application (LogbookOfTheWorld, Cloudlog, etc.) that receives WSJT-X UDP typically:
1. Reads the 12-byte binary header to identify message type
2. For type 12, extracts the ADIF string
3. Passes that string to its normal ADIF parser

### Implication for ollog

Supporting WSJT-X type 12 requires a binary header parser before the ADIF content. This is a **differentiator** worth considering — WSJT-X is the dominant FT8/FT4 logger. However, bridge scripts like wsjtx2cloudlog already handle this and relay as HTTP POST. Supporting native WSJT-X UDP in ollog is medium complexity.

Sources: [NetworkMessage.hpp (GitHub mirror)](https://github.com/roelandjansen/wsjt-x/blob/master/NetworkMessage.hpp), [wsjtx-go library](https://pkg.go.dev/github.com/k0swe/wsjtx-go), [wsjtx2cloudlog](https://github.com/int2001/wsjtx2cloudlog), [wsjt-devel mailing list](https://wsjt-devel.narkive.com/y4rTl5y8/udp-protocol-for-wsjt-x)

---

## Raw ADIF-over-UDP Convention

### The Simple Convention

Several ham radio programs and many integration scripts use **raw ADIF ADI text as the entire UDP datagram payload**. No binary header, no XML wrapper, no framing — just the ADIF tag-stream.

Example datagram payload (the entire UDP data field):
```
<CALL:5>W1ABC <BAND:3>20m <MODE:4>FT8 <QSO_DATE:8>20231015 <TIME_ON:6>143022 <RST_SENT:3>-10 <RST_RCVD:3>-12 <EOR>
```

This is a valid ADIF ADI file with zero or one records. ollog's existing `parse_adi()` function handles this format directly — it already handles absent `<EOH>` by treating the entire content as records.

### Port Convention

Port **12060** is the most common convention — it's the N1MM+ broadcast port and has become the informal default for "any ham radio UDP logging." VarAC, Winlog32, and others use 12060 as the default for ADIF-over-UDP reception. ollog should default to **12060** but make it configurable.

### Multi-Record Datagrams

In practice, UDP datagrams for QSO logging are **always single-record**. Each QSO is logged individually as it is completed. No logging application sends multiple `<EOR>`-delimited records in a single UDP datagram. The existing ADIF parser handles multiple records, but ollog should log one QSO per datagram and reject (or iterate and warn on) multi-record datagrams.

### No Established Framing

There is no length prefix, no delimiter, no checksum convention for ADIF-over-UDP. The UDP datagram boundary is the message boundary. Maximum practical datagram size for a single QSO is well under 1500 bytes (Ethernet MTU), so fragmentation is not a concern.

Sources: [Log4OM UDP ADIF](https://forum.log4om.com/viewtopic.php?t=6064), [VarAC integration docs](https://www.varac-hamradio.com/forum/manuals/integrating-varac-with-your-qso-logging-application), [Cloudlog Aurora UDP](https://aurora.cloudlog.org/settings/)

---

## Auth Approaches

### The Ecosystem Convention: No Auth

Every UDP-based ham radio logging protocol assumes **no authentication**. The security model is:
- Default to localhost (127.0.0.1) only
- Optionally allow LAN broadcast to a known IP
- No credentials, no API key, no token

This works for traditional ham radio software because the software runs on a single operator's machine and all components are local. ollog is different: it is a self-hosted multi-operator web application that may be exposed on a home LAN with multiple computers.

### Why JWT Does Not Work Over UDP

JWT tokens are time-limited (ollog default: 60 minutes). A rotating token embedded in a UDP datagram would expire, breaking automated logging from programs like FLdigi that run continuously. UDP is fire-and-forget — there is no handshake to refresh a token. JWTs are the wrong tool.

### Why IP Allowlisting Alone is Insufficient

IP allowlisting (only accept datagrams from a configured list of source IPs) is the correct network-layer control. But on a home LAN, any device can spoof or share the IP of a trusted device. Combined with an API key, it provides defense-in-depth.

### Recommended Auth Pattern: Pre-Shared API Key in ADIF APP_ Field

Use an ADIF `APP_` custom field to carry a pre-shared API key that ollog issues per-user:

```
<APP_OLLOG_APIKEY:32>abc123def456...xyz <CALL:5>W1ABC <BAND:3>20m ... <EOR>
```

This approach:
- Is compatible with all ADIF parsers (APP_ fields are ignored by other loggers — no breakage)
- Is persistent (unlike JWT, an API key does not expire unless revoked)
- Ties the QSO to a specific ollog user account (maps to `_operator` for isolation)
- Requires zero protocol changes — it's a standard ADIF field in the existing tag-stream
- ollog's existing `parse_adi()` preserves APP_ fields verbatim

**API key storage:** A new `api_keys` collection with `{key_hash, user_id, label, created_at, revoked}`. Key is issued via the ollog admin UI/API as a random 32-byte hex string. The plain key is shown once at creation, only the hash is stored (same pattern as GitHub/Cloudlog personal access tokens).

### IP Allowlist as Defense-in-Depth

Optionally configure allowed source IPs in ollog settings. Default: `127.0.0.1` only (local only). This limits blast radius if an API key leaks.

### What NOT to Do for Auth

- Do not put a JWT in the ADIF payload — expires, unparseable by sending programs
- Do not use HMAC signing of the datagram — no ecosystem precedent, complex to configure in logging software
- Do not require a UDP handshake before accepting QSOs — UDP is connectionless by design
- Do not implement no-auth mode as the default — ollog is multi-operator; an anonymous datagram cannot be attributed to an operator

---

## Table Stakes

Features without which the UDP listener is unusable or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Raw ADIF ADI text datagram reception | The simplest format; used by VarAC, Log4OM inbound ADIF, and dozens of bridge scripts | LOW | ollog's `parse_adi()` already handles this; wrap in UDP socket listener |
| Single-record-per-datagram processing | All real-world QSO UDP datagrams are single-record; each datagram = one QSO | LOW | Call `parse_adi()`, take the first record, insert via existing `build_qso_dict()` + `QSO` model |
| Pre-shared API key authentication via APP_OLLOG_APIKEY field | Multi-operator ollog cannot accept anonymous QSOs — must know which user's log to add the QSO to | MEDIUM | Parse APP_OLLOG_APIKEY from the record, look up user by key hash, inject operator from user |
| IP allowlist configuration (default: 127.0.0.1 only) | Prevent unauthorized datagrams from other network hosts | LOW | Configurable via environment variable; drop datagrams from non-allowlisted IPs |
| Configurable UDP port (default 12060) | Port 12060 is the ecosystem convention; but must be configurable to avoid conflicts | LOW | `UDP_PORT=12060` env var |
| Required-field validation before insert | CALL, BAND, MODE, QSO_DATE, TIME_ON are required; silently drop invalid datagrams would be confusing | LOW | Validate same required fields as REST API; log a warning on rejection |
| Duplicate detection (same ±2 min window as REST API) | Consistency with REST API behavior; prevents double-logging from FT8 auto-loggers | LOW | Reuse existing `find_duplicate()` function |
| Logging of accepted/rejected datagrams to stdout | Operators need to know if UDP logging is working; ham radio culture expects log output | LOW | Python logging to stdout: "UDP QSO accepted: W1ABC on 20m FT8", "UDP rejected: missing CALL field" |
| Run as background thread alongside FastAPI | UDP listener must not block the HTTP server; must start with the app | LOW | `asyncio.create_task()` in FastAPI startup event, or `threading.Thread` for `socket.recvfrom` loop |

---

## Differentiators

Features that would make ollog's UDP listener notably more useful or compatible than a minimal implementation.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| N1MM+ XML contactinfo reception | N1MM+ is the most widely used contest logger; this makes ollog usable during contests without a bridge script | MEDIUM | Parse XML `<contactinfo>` datagrams; map fields to ADIF equivalents (band MHz → ADIF string, timestamp format conversion); requires an XML parser |
| WSJT-X type 12 "Logged ADIF" reception | WSJT-X is the dominant FT8/FT4 logger; type 12 contains a complete ADIF string, so only the 12-byte binary header needs parsing before handing off to `parse_adi()` | MEDIUM | Read magic number + schema + type; if type==12, extract the ADIF string field (uint32 len + bytes); pass to existing parser |
| Per-key rate limiting | Prevent a misconfigured station from flooding the log with duplicate datagrams | LOW | Simple token bucket per API key; discard if rate exceeded (e.g., 10/second) |
| Admin UI for API key management | Operators need to generate, label, and revoke UDP API keys without editing config files | MEDIUM | New admin UI section: "UDP API Keys" — generate, name, copy, revoke |
| REST endpoint to generate/revoke API keys | Allows scripted key management without the UI | LOW | `POST /api/udp-keys/`, `DELETE /api/udp-keys/{id}` |
| Startup log showing UDP listener status | Operators should see at startup: "UDP listener active on port 12060" or "UDP listener disabled" | LOW | Single INFO log line; prevents confusion when the listener is not configured |
| WSJT-X type 5 "QSO Logged" reception | Older binary format; less preferred than type 12 but some third-party software emits it | HIGH | Requires decoding QDateTime (Qt binary format), multiple typed fields — significantly more complex than type 12 |

---

## Anti-Features

Features that look appealing but should not be built.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| TCP listener alongside UDP | "More reliable" sounds appealing, but ham radio logging programs do not send QSOs over TCP; zero ecosystem demand | UDP only; if TCP is later needed for a specific integration, add it then |
| JWT in the UDP datagram | JWTs expire; a FT8 station logging overnight would fail at token expiry; no ecosystem precedent | Pre-shared API key via APP_OLLOG_APIKEY — persistent, no expiry, no refresh needed |
| Acknowledgment/response datagrams | UDP is one-way in this ecosystem; sending ACK datagrams back to the sender is not expected and can cause issues with multi-destination broadcast configurations | Log acceptance/rejection locally; expose a `/api/udp-stats` endpoint for tooling instead |
| Binary ADIF framing (length prefix, checksum) | No ecosystem precedent; breaks compatibility with every existing tool that sends raw ADIF text | Raw ADIF ADI text as the entire datagram; UDP boundary is the message boundary |
| Auto-detection of N1MM vs WSJT-X vs raw ADIF format | Trying to detect format by heuristic (starts with `<?xml`? starts with magic bytes?) adds fragility | Accept only one format on one port; configure separate ports for N1MM XML if it's added |
| Guaranteed delivery mechanism (retransmit on failure) | UDP is fire-and-forget by design; all existing ham radio logging tools accept that | Do not implement; operators using critical logging should use the REST API or ADIF import for reliability |
| Storing the raw datagram payload | Tempting for debugging, but adds storage complexity and potential GDPR surface | Log enough to diagnose (call, band, mode, timestamp) but do not store raw UDP bytes |
| WSJT-X type 5 binary QSO Logged as first WSJT-X target | Type 12 carries a ready-parsed ADIF string; type 5 requires full Qt binary deserialization of every field | Implement type 12 first; type 5 only if explicitly requested |
| ADIF-over-UDP as a replacement for the REST API | UDP is supplementary for local/LAN logging tools; it is not suitable for remote or programmatic use | Keep REST API as the primary integration path; UDP is for radio-adjacent programs on the LAN |

---

## Feature Dependencies

```
UDP ADIF listener (table stakes)
    requires: asyncio UDP socket in FastAPI startup event
    requires: parse_adi() — already implemented
    requires: build_qso_dict() + QSO model — already implemented
    requires: find_duplicate() — already implemented
    requires: API key auth system (new)
        requires: api_keys collection (new MongoDB document type)
        requires: key generation endpoint or admin UI section (new)
        requires: key lookup by hash in UDP handler (new, O(1) indexed query)
    requires: IP allowlist check (new, checked before parse_adi())
    requires: UDP_PORT + UDP_ALLOWED_IPS env vars (config.py additions)

N1MM+ XML support (differentiator)
    requires: UDP ADIF listener (table stakes) — shared socket infrastructure
    requires: XML parser (stdlib xml.etree.ElementTree — already available)
    requires: N1MM field mapping table (band MHz → ADIF string, timestamp format)

WSJT-X type 12 support (differentiator)
    requires: UDP ADIF listener (table stakes) — shared socket infrastructure
    requires: Binary header decoder (struct.unpack, 12 bytes) — trivial
    requires: parse_adi() on the extracted ADIF string — already implemented
```

---

## Real-World Message Format Examples

### 1. Raw ADIF ADI (primary format for ollog — table stakes)

Complete UDP payload, no framing:
```
<APP_OLLOG_APIKEY:32>a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5 <CALL:5>W1ABC <BAND:3>20m <MODE:4>FT8 <QSO_DATE:8>20260405 <TIME_ON:6>143022 <RST_SENT:3>-10 <RST_RCVD:3>-12 <EOR>
```

Byte count for this example: ~160 bytes. Well under 1500-byte MTU.

The `APP_OLLOG_APIKEY` field is extracted by `parse_adi()` (which preserves all fields verbatim), used for auth, then stripped from the record before calling `build_qso_dict()`.

### 2. N1MM+ XML contactinfo (differentiator — partial field mapping needed)

Complete UDP payload:
```xml
<?xml version="1.0" encoding="utf-8"?>
<contactinfo>
  <app>N1MM</app>
  <timestamp>2026-04-05 14:30:22</timestamp>
  <mycall>W2XYZ</mycall>
  <band>14</band>
  <mode>CW</mode>
  <call>W1ABC</call>
  <snt>599</snt>
  <rcv>599</rcv>
  <operator>W2XYZ</operator>
  <gridsquare></gridsquare>
</contactinfo>
```

Field mapping required: `band` (14 MHz) → ADIF `BAND` ("20m"), `timestamp` → `QSO_DATE` + `TIME_ON`, `snt`/`rcv` → `RST_SENT`/`RST_RCVD`, `mycall` → `STATION_CALLSIGN`.

### 3. WSJT-X type 12 Logged ADIF (differentiator — binary header + ADIF string)

Hexdump of first 16 bytes (header):
```
AD BC CB DA    <- magic number (big-endian uint32: 0xADBCCBDA)
00 00 00 02    <- schema number (2)
00 00 00 0C    <- message type (12 = Logged ADIF)
00 00 00 06    <- client ID string length (6)
```

Followed by 6 bytes of client ID (e.g., `WSJT-X`), then uint32 ADIF string length, then the ADIF string:
```
<adif_ver:5>3.0.7 <programid:6>WSJT-X <EOH>
<call:5>W1ABC <gridsquare:4>FN42 <mode:4>FT8 <rst_sent:3>-10 <rst_rcvd:3>-12
<qso_date:8>20260405 <time_on:6>143022 <band:3>20m <station_callsign:5>W2XYZ <EOR>
```

The entire ADIF string after the header is passable directly to ollog's `parse_adi()` function.

Note: WSJT-X type 12 does NOT include an auth field. An ollog operator using WSJT-X would need to configure a bridge that appends the `APP_OLLOG_APIKEY` field before forwarding. Alternatively, ollog could associate WSJT-X datagrams by IP allowlist + a configured "WSJT-X user" mapping.

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| N1MM+ UDP format (XML, port 12060, fields) | HIGH | Official docs URL confirmed, multiple implementations (n1mm_view, N1MMlistener) corroborate, community group discussions |
| WSJT-X type 12 binary format | HIGH | Source code (NetworkMessage.hpp) confirmed by multiple independent libraries (wsjtx-go, py-wsjtx, wsjtx-udp Haskell), mailing list discussions |
| Raw ADIF ADI as UDP payload convention | MEDIUM-HIGH | Confirmed by VarAC docs, Log4OM forum threads, Cloudlog Aurora UDP description, Winlog32 behavior; no single authoritative spec |
| Port 12060 as ecosystem default | HIGH | N1MM+ official docs, VarAC docs, Log4OM forum posts all converge on 12060 |
| ADIF spec has no UDP transport section | HIGH | Checked adif.org — no transport specification found |
| Auth: no-auth is the ecosystem convention | HIGH | Consistent across all sources; explicit localhost-only design in N1MM+, WSJT-X |
| APP_OLLOG_APIKEY approach | MEDIUM | ADIF APP_ field format is well-specified (HIGH); this specific auth pattern is original design for ollog (no precedent to verify against) |

---

## Sources

| Source | URL | Confidence |
|--------|-----|------------|
| N1MM+ External UDP Messages (official) | https://n1mmwp.hamdocs.com/appendices/external-udp-broadcasts/ | HIGH |
| n1kdo/n1mm_view (Python UDP receiver implementation) | https://github.com/n1kdo/n1mm_view | HIGH |
| WSJT-X NetworkMessage.hpp (GitHub mirror) | https://github.com/roelandjansen/wsjt-x/blob/master/NetworkMessage.hpp | HIGH |
| wsjtx-go library (Go implementation, all message types) | https://pkg.go.dev/github.com/k0swe/wsjtx-go | HIGH |
| wsjtx2cloudlog (WSJT-X to Cloudlog bridge) | https://github.com/int2001/wsjtx2cloudlog | MEDIUM |
| WSJT-X User Guide 2.6.1 | https://wsjt.sourceforge.io/wsjtx-doc/wsjtx-main-2.6.1.html | HIGH |
| VarAC integration documentation | https://www.varac-hamradio.com/forum/manuals/integrating-varac-with-your-qso-logging-application | MEDIUM |
| Log4OM UDP ADIF reception forum | https://forum.log4om.com/viewtopic.php?t=6064 | MEDIUM |
| Cloudlog Aurora UDP server | https://aurora.cloudlog.org/settings/ | MEDIUM |
| ADIF 3.1.6 specification | https://adif.org/316/ADIF_316.htm | HIGH |
| N1MMLoggerPlus groups.io — "Can N1MM UDP broadcast ADIF?" | https://groups.io/g/N1MMLoggerPlus/topic/can_n1mm_udp_broadcast/76073171 | MEDIUM |
| N1MM-DXKeeper Gateway | https://ny4i.github.io/DxKeeper-UDP-Gateway/ | MEDIUM |

---

*Feature research for: ollog — UDP ADIF listener milestone*
*Researched: 2026-04-05*
