# UDP ADIF

ollog includes a UDP listener that accepts raw ADIF text datagrams. QSOs sent over UDP are logged immediately without requiring an HTTP request from the sender.

## Enabling the UDP Listener

The UDP listener is disabled by default. To enable it, set `UDP_ENABLED=true` in your `.env` file:

```
UDP_ENABLED=true
UDP_PORT=2237
UDP_BIND_HOST=0.0.0.0
```

Optionally, set `UDP_OPERATOR` as a fallback callsign for datagrams that do not include an `OPERATOR` field:

```
UDP_OPERATOR=W1AW
```

If every datagram includes an `OPERATOR` field, `UDP_OPERATOR` is not needed.

If you change `UDP_PORT` from the default, update the Docker Compose port mapping to match (e.g., `2237:2237/udp`).

After changing environment variables, restart the stack:

```bash
docker compose down && docker compose up -d
```

## Docker Compose Port Mapping

The `docker-compose.yml` includes a UDP port mapping for the api service. Uncomment or add:

```yaml
services:
  api:
    ports:
      - "2237:2237/udp"
    environment:
      - UDP_ENABLED=true
      - UDP_BIND_HOST=0.0.0.0
      # Optional: fallback operator when datagrams omit the OPERATOR field
      # - UDP_OPERATOR=W1AW
```

## ADIF Datagram Format

Each UDP datagram must be a raw ADIF text string. Required fields: `CALL`, `QSO_DATE`, `TIME_ON`, `BAND`, `MODE`.

Each field tag is `<FIELDNAME:N>value` where `N` is the byte count of `value`. For ASCII callsigns, bands, modes, and dates, byte count equals character count.

Example datagram:

```
<CALL:6>DL1ABC<BAND:3>20m<MODE:3>FT8<QSO_DATE:8>20240415<TIME_ON:4>1430<EOR>
```

## Per-Datagram Authentication

By default, the UDP listener accepts all datagrams from any sender. For per-datagram authentication using API tokens, include the `APP_OLLOG_TOKEN` ADIF field in the datagram.

`APP_OLLOG_TOKEN` is an **ADIF field name** (using the ADIF `APP_` prefix convention for application-specific fields). It is **not an environment variable**. When present, ollog validates the field value against the API token store. Datagrams with an invalid or missing token value (if a token is required) are rejected.

Example ADIF datagram with token:

```
<APP_OLLOG_TOKEN:20>ollog_abc123...<CALL:6>DL1ABC<BAND:3>20m<MODE:3>FT8<QSO_DATE:8>20240415<TIME_ON:4>1430<EOR>
```

To create API tokens for use with UDP datagrams, see [API Tokens](api-tokens.md).

## Multi-Operator Routing

When multiple operators share a single ollog instance, each can receive QSOs over UDP by including their callsign in the `OPERATOR` ADIF field. The callsign must match an existing, enabled operator account in ollog.

Example datagram with OPERATOR field:

```
<OPERATOR:4>W1AW<CALL:6>DL1ABC<BAND:3>20m<MODE:3>FT8<QSO_DATE:8>20240415<TIME_ON:4>1430<EOR>
```

This QSO is logged to the `W1AW` operator's personal log, regardless of the `UDP_OPERATOR` setting.

**Routing order:**

1. If `APP_OLLOG_TOKEN` is present, the token determines the operator (see [Per-Datagram Authentication](#per-datagram-authentication)).
2. If `OPERATOR` is present, the callsign is looked up in the operator cache. If the callsign is not found or the operator is disabled, the datagram is dropped.
3. If neither field is present and `UDP_OPERATOR` is set, the fallback operator is used.
4. If none of the above apply, the datagram is dropped.

Changes to operator accounts (create, enable, disable) take effect within one datagram — no restart required.

## Testing the Listener

The fastest way to verify the UDP listener is working:

```bash
echo -n '<CALL:6>DL1ABC<BAND:3>20m<MODE:3>FT8<QSO_DATE:8>20240415<TIME_ON:4>1430<EOR>' \
  | nc -u -w1 127.0.0.1 2237
```

Replace `127.0.0.1` with the hostname of your ollog instance if remote. The `-u` flag selects UDP; `-w1` exits after 1 second (required since UDP is connectionless). On Linux with GNU netcat, use `-q1` instead of `-w1`.

After sending, check your log — a new QSO from `DL1ABC` should appear. If the datagram includes an `OPERATOR` field, the QSO is logged under that operator; otherwise it uses the `UDP_OPERATOR` fallback.

## Log4OM

Log4OM 2 can broadcast QSOs as raw ADIF text over UDP, which is directly compatible with ollog's UDP listener.

1. In Log4OM, go to **Setup > Connections**.
2. In the right panel (Outbound/Broadcast connections), add a new entry:
   - **Port:** `2237`
   - **IP:** `127.0.0.1` (or the IP address of the machine running ollog)
   - **Name:** `ollog` (or any label you prefer)
3. Enable the **Broadcast** checkbox and confirm ADIF is selected as the message type.
4. Click the green **+** button to save the connection.

From this point, each QSO you save in Log4OM is broadcast to ollog over UDP. Consult the Log4OM documentation if the steps above do not match your installed version.

## WSJT-X

WSJT-X's UDP output uses a **binary-framed protocol**, not raw ADIF text. It is not directly compatible with ollog's UDP listener. Do not point WSJT-X's UDP Server setting at ollog's port.

For WSJT-X, use the [ADIF file import path](adif-import-export.md) instead. WSJT-X writes a running log to `WSJTX_LOG.ADI` in its data directory.

## N1MM+ (N1MM Logger Plus)

N1MM+ broadcasts contact data as **XML**, not ADIF text. It is not directly compatible with ollog's UDP listener.

For N1MM+, export to ADIF via **File > Export to ADIF** and use the [ADIF file import path](adif-import-export.md).
