# Phase 20: Getting-Started Guide — Sending QSOs via UDP - Research

**Researched:** 2026-04-08
**Domain:** Technical documentation — ADIF UDP protocol, ham radio logging software configuration
**Confidence:** MEDIUM (internal facts HIGH; external logging software UI paths MEDIUM/LOW)

---

## Summary

This phase adds a "Sending QSOs via UDP" section to `docs/getting-started.md`. The task is primarily documentation, but it requires accurate information about three distinct concerns: (1) what ollog's UDP listener actually expects, (2) how to construct a valid `nc` test one-liner, and (3) how to configure each third-party logging program.

The internal facts (ollog's required fields, port, bind host) are fully known from source files with HIGH confidence. The `nc` one-liner can be written with certainty. The external software UI paths are MEDIUM confidence based on WebSearch findings from multiple sources; the actual field labels have been consistent across multiple sources.

**Critical finding:** WSJT-X and N1MM+ do NOT send raw ADIF text over UDP. WSJT-X sends a binary-framed protocol; N1MM+ sends XML. Neither is directly compatible with ollog's UDP listener, which expects raw ADIF text. Log4OM CAN send raw ADIF text outbound via UDP. The documentation must be honest about what each program actually sends and must not falsely imply WSJT-X/N1MM+ send to ollog directly.

**Primary recommendation:** Document the nc one-liner and Log4OM (direct ADIF UDP). For WSJT-X and N1MM+, document the correct menu paths but explicitly note the format mismatch and recommend using ADIF file import as the integration path for those programs.

---

## Confirmed Facts from Source Files (HIGH confidence)

All values read directly from `/Users/royco/ollog/app/config.py` and `/Users/royco/ollog/app/udp/server.py`.

### Required ADIF Fields

From `app/qso/service.py` line 12:

```python
_REQUIRED_FIELDS = {"CALL", "QSO_DATE", "TIME_ON", "BAND", "MODE"}
```

A UDP datagram is rejected if any of these five fields is missing. No other fields are required for acceptance.

### UDP Configuration Defaults

| Setting | Default | Env var |
|---------|---------|---------|
| Port | `2399` | `UDP_PORT` |
| Bind host | `127.0.0.1` | `UDP_BIND_HOST` |
| Enabled | `false` | `UDP_ENABLED` |
| Operator | (none) | `UDP_OPERATOR` |

The port is **2399** — the requirements document cited 2237 (the WSJT-X default), which is wrong. Use 2399 confirmed by `app/config.py` and confirmed in Phase 19 research.

### What the Listener Accepts

- Raw ADIF ADI text, UTF-8 encoded, sent as a single UDP datagram.
- Parser: `parse_adi()` in `app/adif/parser.py` — pure ADIF text scanner.
- Multiple records in one datagram: only the first is processed; the rest are discarded with a warning log.
- OPERATOR callsign is stamped from `UDP_OPERATOR` env var — NOT from the datagram.
- Duplicate detection: same CALL/BAND/MODE within ±2 minutes of the same operator is silently skipped.

### Existing Getting-Started.md Structure

The file is at `docs/getting-started.md`. Current sections:
1. Step 1: Log In
2. Step 2: Set Up Your Profile
3. Step 3: Log a QSO via the Web UI
4. Step 4: Log a QSO via the API
5. Step 5: Import QSOs from an ADIF File
6. Step 6: Export Your Log as ADIF
7. Step 7: Watch the Station Feed
8. Next Steps

**New section placement:** Insert as **Step 8** after "Watch the Station Feed" and before "Next Steps". The document uses `## Step N: Title` heading format with `---` separators between sections. The section must include a brief conceptual intro, the `nc` one-liner, and subsections for each logging program.

---

## ADIF Format for the nc One-Liner

### Minimal Valid ADIF Datagram

ADIF ADI format uses `<FIELDNAME:N>value` tags terminated with `<EOR>`. The five required fields are CALL, QSO_DATE, TIME_ON, BAND, MODE.

```bash
echo -n '<CALL:6>DL1ABC<BAND:3>20m<MODE:2>FT8<QSO_DATE:8>20240415<TIME_ON:4>1430<EOR>' \
  | nc -u -w1 127.0.0.1 2399
```

Field format rules (from ADIF spec, confirmed by parser source):
- `<FIELDNAME:N>` — N is the **byte count** of the value that follows (UTF-8 bytes)
- `<EOR>` — ends the record; no trailing newline required
- Field names are case-insensitive (parser normalizes to uppercase)
- No header (`<EOH>`) is required when there is no header section

**Important nc flags:**
- `-u` — UDP mode (not TCP)
- `-w1` — timeout after 1 second (UDP is connectionless, nc needs a timeout to exit)
- Some systems use `nc -u -q1` instead of `-w1` (GNU netcat variant)

### ADIF Field Byte Count Table

| Field | Example value | Byte count | Tag |
|-------|---------------|------------|-----|
| CALL | `DL1ABC` | 6 | `<CALL:6>DL1ABC` |
| BAND | `20m` | 3 | `<BAND:3>20m` |
| MODE | `FT8` | 3 | `<MODE:3>FT8` |
| MODE | `SSB` | 3 | `<MODE:3>SSB` |
| QSO_DATE | `20240415` | 8 | `<QSO_DATE:8>20240415` |
| TIME_ON | `1430` | 4 | `<TIME_ON:4>1430` |

---

## Logging Software Compatibility Analysis

### WSJT-X

**UDP output format:** Binary-framed protocol. Messages have a 4-byte magic number header (0xADBCCBDA), schema version, message type, and application ID encoded in binary, followed by the ADIF text payload. This is NOT raw ADIF text.

**Compatibility with ollog:** NOT directly compatible. The `parse_adi()` function receives the raw bytes decoded as UTF-8 (with replacement characters for non-UTF-8 bytes). The binary header may accidentally be skipped since the parser scans for `<` characters — but this is undefined behavior and must not be relied upon. Direct WSJT-X → ollog UDP connection should NOT be documented as working.

**Correct integration path:** Use ollog's ADIF file import (`Step 5`). WSJT-X writes `WSJTX_LOG.ADI` in its data directory. The operator imports this periodically via the API or web UI.

**What to document:** The Settings → Reporting → UDP Server menu path is worth documenting for context, but must clearly state this is NOT for ollog direct connection. Alternatively, skip WSJT-X UDP configuration entirely and note the file import workaround. (See Open Questions below.)

**UI path (MEDIUM confidence — consistent across multiple sources):**
- Menu: `File > Settings` (or `F2` on Windows, `Cmd+,` on macOS)
- Tab: `Reporting`
- Section: `UDP Server`
- Field 1: `Server name` — hostname or IP address (default: `localhost`/`127.0.0.1`)
- Field 2: `Server port` — port number (default: `2237`)
- Checkbox: `Accept UDP requests` — must be checked for WSJT-X to respond to queries from other software; does not affect outbound broadcast

**WSJT-X default port 2237** is the source of confusion with ollog port 2399. The documentation must call this out.

### N1MM+ (N1MM Logger Plus)

**UDP output format:** XML. Contact broadcasts are XML-formatted packets, not ADIF. The `contactinfo` packet contains structured XML fields.

**Compatibility with ollog:** NOT compatible. The XML format is completely different from ADIF text. The parser will fail to find ADIF `<FIELDNAME:N>` tags in XML.

**Correct integration path:** Export to ADIF from N1MM+ and import via the ADIF import endpoint. N1MM+ supports ADIF export through `File > Export to ADIF`.

**What to document:** Document the menu path for reference but state clearly it sends XML, not ADIF, and is not directly usable with ollog's UDP listener. Recommend ADIF file export/import.

**UI path (MEDIUM confidence — from official N1MM+ docs):**
- Menu: `Config > Config Ports, Mode Control, Audio, Other`
- Tab: `Broadcast Data`
- Check the `Contacts` checkbox to enable contact broadcasts
- Enter destination in format `IP:PORT` (e.g., `127.0.0.1:12060`)
- Default port: `12060`
- Format: XML (not ADIF)

### Log4OM 2

**UDP output format:** Log4OM's outbound UDP broadcast can send ADIF text. The Log4OM documentation explicitly states it "can be configured to send ADIF messages to other application" and its inbound ADIF service accepts "a UDP packet containing an ADIF string." The outbound uses the same ADIF string format.

**Compatibility with ollog:** Potentially compatible if Log4OM's outbound ADIF broadcast sends raw ADIF text. However, the exact byte-for-byte format of the outbound packet has not been verified against ollog's parser in testing. The documentation should note this is the best candidate for direct UDP integration but recommend testing.

**Configuration path (MEDIUM confidence — multiple forum sources agree on path):**
- Menu: `Setup > Connections` (sometimes labeled `Configuration > Software Integration > Connections`)
- Panel: Right panel (Outbound/Broadcast connections)
- Fields: Port number, connection name, enable "Broadcast" flag
- Add with green `+` button
- The outbound ADIF broadcast sends a QSO as an ADIF string each time a QSO is saved

**Specific steps for ollog integration:**
1. In Log4OM, go to `Setup > Connections`
2. In the right panel (Outbound), enter:
   - Port: `2399` (ollog's UDP port)
   - IP: `127.0.0.1` (or the IP of the machine running ollog)
   - Name: `ollog` (or any label)
3. Enable the `Broadcast` flag / check ADIF as the message type
4. Click the green `+` to save

**Note on confidence:** The exact field labels in Log4OM's UI have varied slightly across versions. The path `Setup > Connections` is the most consistently documented. Field labels may differ in current versions.

---

## Architecture Patterns

### Document Section Structure

Insert as `## Step 8: Send QSOs via UDP` after Step 7 (Station Feed), before `## Next Steps`. Use the same format as existing steps:

```markdown
---

## Step 8: Send QSOs via UDP

[intro paragraph]

### Testing with nc

[nc one-liner, explanation]

### Log4OM

[steps]

### WSJT-X

[note about format mismatch + file import workaround]

### N1MM+ (N1MM Logger Plus)

[note about format mismatch + ADIF export workaround]

---
```

### Heading Level Convention

Existing document uses `## Step N: Title` for top-level steps and implicitly uses bold text or direct prose for sub-items. No `###` subheadings currently exist. The new section may introduce `###` subheadings for each logging program — this is a small style extension that is consistent with Markdown best practices.

### Information to Cover in the Intro Paragraph

1. ADIF datagrams are sent over UDP to ollog's configured port
2. QSOs are logged under the `UDP_OPERATOR` callsign (set in `.env`)
3. The UDP listener must be enabled (`UDP_ENABLED=true`) — see deployment guide
4. Prerequisites: UDP must be configured by the administrator

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| ADIF field byte counts | Don't manually count bytes for examples | Use Python: `len("DL1ABC".encode("utf-8"))` to verify |
| WSJT-X binary protocol parser | Don't suggest building one | Recommend ADIF file import instead |
| N1MM+ XML-to-ADIF bridge | Don't suggest building one | Recommend ADIF file export/import |

---

## Common Pitfalls

### Pitfall 1: Wrong byte count in ADIF tags
**What goes wrong:** `<CALL:5>DL1ABC` — value is 6 bytes but tag says 5. Parser reads 5 bytes and gets `DL1AB` as the call, leaving `C` in the stream.
**Why it happens:** Easy to miscount.
**How to avoid:** Always count the actual byte length of the value string. For ASCII-only values (callsigns, bands, modes, dates), byte count equals character count.
**Warning signs:** Parser returns a record with truncated values or parse errors.

### Pitfall 2: Using TCP nc instead of UDP nc
**What goes wrong:** nc without `-u` uses TCP; ollog's listener is UDP-only. The packet is never received.
**Why it happens:** `-u` flag is easily forgotten.
**How to avoid:** Always include `-u` flag in the nc command.

### Pitfall 3: nc hangs waiting for response
**What goes wrong:** `echo "..." | nc -u 127.0.0.1 2399` — nc sends the datagram but waits indefinitely because UDP has no connection close signal.
**Why it happens:** UDP is connectionless; nc doesn't know when to exit.
**How to avoid:** Always use `-w1` (BSD/macOS nc) or `-q1` (GNU nc) to exit after 1 second.

### Pitfall 4: Missing UDP_OPERATOR configuration
**What goes wrong:** Datagrams arrive but are silently discarded with log message `UDP_OPERATOR not configured`.
**Why it happens:** `UDP_OPERATOR` env var is not set.
**How to avoid:** The getting-started section must note this is required. Readers should check deployment guide.

### Pitfall 5: WSJT-X/N1MM+ pointed directly at ollog
**What goes wrong:** Operator configures WSJT-X or N1MM+ to send to port 2399. No QSOs arrive because the formats are incompatible.
**Why it happens:** Phase requirements listed WSJT-X and N1MM+ as if they support direct connection. They do not send raw ADIF text.
**How to avoid:** Documentation must clearly state format compatibility for each program. Do not imply WSJT-X or N1MM+ work directly.

### Pitfall 6: Port number confusion (2237 vs 2399)
**What goes wrong:** Operator uses WSJT-X's default port 2237 when configuring nc or a logging program.
**Why it happens:** WSJT-X's default UDP port is 2237; ollog's default is 2399. They're different.
**How to avoid:** All examples must use ollog's port 2399 consistently. A note explaining the difference prevents confusion.

---

## Code Examples

### Minimal Valid nc One-Liner

```bash
echo -n '<CALL:6>DL1ABC<BAND:3>20m<MODE:3>FT8<QSO_DATE:8>20240415<TIME_ON:4>1430<EOR>' \
  | nc -u -w1 127.0.0.1 2399
```

For GNU netcat (Linux), `-w1` may need to be replaced with `-q1`:

```bash
echo -n '<CALL:6>DL1ABC<BAND:3>20m<MODE:3>FT8<QSO_DATE:8>20240415<TIME_ON:4>1430<EOR>' \
  | nc -u -q1 127.0.0.1 2399
```

### With Optional Fields (More Realistic Example)

```bash
echo -n '<CALL:6>DL1ABC<BAND:3>20m<MODE:3>FT8<QSO_DATE:8>20240415<TIME_ON:4>1430<RST_SENT:2>59<RST_RCVD:2>59<EOR>' \
  | nc -u -w1 127.0.0.1 2399
```

---

## State of the Art

| Topic | Current State |
|-------|--------------|
| WSJT-X UDP protocol | Binary-framed, not raw ADIF text — has been this way since WSJT-X 2.0 |
| N1MM+ UDP broadcasts | XML format — not ADIF |
| Log4OM outbound UDP | Can send raw ADIF text (most directly compatible with ollog) |
| ADIF format | ADI (tag-based `.adi`) is what ollog uses; ADX (XML-based) is not supported |

---

## Open Questions

1. **Whether to document WSJT-X/N1MM+ at all, or only "workaround" note**
   - What we know: Phase requirements (DOC-05, DOC-06) specify WSJT-X and N1MM+ steps. But these programs cannot directly feed ollog's UDP listener.
   - What's unclear: Should the doc provide menu paths for WSJT-X/N1MM+ anyway (for operators who might write their own bridge), or just say "not directly compatible, use ADIF import"?
   - Recommendation: Document the menu paths for completeness per the requirements, but prominently note the format incompatibility and recommend the file import path. This fulfills DOC-05/DOC-06 while being technically honest.

2. **Log4OM exact outbound UI field labels in current version**
   - What we know: Path is `Setup > Connections`, right panel, port + broadcast flag + green `+`.
   - What's unclear: Exact field labels in current Log4OM 2 release (version 2.27+). Sources are MEDIUM confidence.
   - Recommendation: The planner should document the path with a caveat: "exact field labels may vary by Log4OM version — consult the Log4OM documentation if the steps don't match."

3. **Whether WSJT-X type-12 binary message accidentally parses through ollog's parser**
   - What we know: The parser scans for `<` characters and would skip binary header bytes; the ADIF payload starts with `<adif_ver:...>`.
   - What's unclear: Whether the binary header ever contains 0x3C (`<`) in positions that confuse the parser.
   - Recommendation: Do not document this as working. The behavior is undefined and depends on the binary content of the header. Recommend file import for WSJT-X users.

---

## Sources

### Primary (HIGH confidence)
- `/Users/royco/ollog/app/qso/service.py` line 12 — `_REQUIRED_FIELDS` definition
- `/Users/royco/ollog/app/config.py` — all UDP config defaults
- `/Users/royco/ollog/app/udp/server.py` — listener behavior, operator handling
- `/Users/royco/ollog/app/adif/parser.py` — what the parser accepts
- `/Users/royco/ollog/docs/getting-started.md` — existing document structure

### Secondary (MEDIUM confidence)
- [N1MM+ External UDP Messages](https://n1mmwp.hamdocs.com/appendices/external-udp-broadcasts/) — confirms XML format for N1MM+ contacts broadcast
- [WSJT-X 2.6.1 User Guide](https://wsjt.sourceforge.io/wsjtx-doc/wsjtx-main-2.6.1.html) — Reporting tab, UDP Server settings
- [WSJT-X developer mailing list thread](https://sourceforge.net/p/wsjt/mailman/wsjt-devel/thread/7222E288-611F-4D3B-9627-D4BEA773472B@comcast.net/) — confirms binary protocol + ADIF payload structure
- [Log4OM integrated page](https://www.log4om.com/integrated/) — confirms outbound ADIF capability
- Multiple Log4OM forum threads confirming `Setup > Connections` path and broadcast flag

### Tertiary (LOW confidence)
- WSJT-X UI field labels (`Server name`, `Server port`) — from multiple secondary sources but not directly confirmed from official doc screenshots
- Log4OM exact field labels in current version — forum posts from various versions, may differ in 2.27+

---

## Metadata

**Confidence breakdown:**
- ollog internal facts (port, fields, parser): HIGH — read from source files
- nc one-liner format: HIGH — ADIF spec + parser source code
- WSJT-X format is binary (not raw ADIF): HIGH — multiple sources confirm
- N1MM+ format is XML (not raw ADIF): HIGH — official N1MM+ docs confirm
- Log4OM outbound sends ADIF: MEDIUM — multiple sources, not verified by packet capture
- WSJT-X Settings > Reporting > UDP Server UI path: MEDIUM — multiple consistent sources
- N1MM+ Config > Config Ports > Broadcast Data UI path: MEDIUM — official docs
- Log4OM Setup > Connections UI path: MEDIUM — multiple consistent forum sources
- Log4OM exact field labels: LOW — varies by version

**Research date:** 2026-04-08
**Valid until:** Stable for ollog internals; external software UI paths valid ~90 days (software versions change slowly)
