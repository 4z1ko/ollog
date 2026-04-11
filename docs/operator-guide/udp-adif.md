# UDP ADIF

ollog includes a UDP listener that accepts raw ADIF text datagrams. QSOs sent over UDP are logged immediately without requiring an HTTP request from the sender.

## Enabling the UDP Listener

The UDP listener is disabled by default. To enable it, set `UDP_ENABLED=true` in your `.env` file along with the other required variables:

```
UDP_ENABLED=true
UDP_PORT=2237
UDP_BIND_HOST=0.0.0.0
UDP_OPERATOR=W1AW
```

`UDP_OPERATOR` must be set to a callsign that has an existing operator account in ollog. QSOs received via UDP are logged under that callsign.

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
      - UDP_OPERATOR=W1AW
```

## ADIF Datagram Format

Each UDP datagram must be a raw ADIF text string. Required fields: `CALL`, `QSO_DATE`, `TIME_ON`, `BAND`, `MODE`.

Each field tag is `<FIELDNAME:N>value` where `N` is the byte count of `value`. For ASCII callsigns, bands, modes, and dates, byte count equals character count.

Example datagram:

```
<CALL:6>DL1ABC<BAND:3>20m<MODE:3>FT8<QSO_DATE:8>20240415<TIME_ON:4>1430<EOR>
```

## Per-Datagram Authentication

By default, the UDP listener accepts all datagrams from any sender (authentication is implicit in UDP_OPERATOR). For per-datagram authentication using API tokens, include the `APP_OLLOG_TOKEN` ADIF field in the datagram.

`APP_OLLOG_TOKEN` is an **ADIF field name** (using the ADIF `APP_` prefix convention for application-specific fields). It is **not an environment variable**. When present, ollog validates the field value against the API token store. Datagrams with an invalid or missing token value (if a token is required) are rejected.

Example ADIF datagram with token:

```
<APP_OLLOG_TOKEN:20>ollog_abc123...<CALL:6>DL1ABC<BAND:3>20m<MODE:3>FT8<QSO_DATE:8>20240415<TIME_ON:4>1430<EOR>
```

To create API tokens for use with UDP datagrams, see [API Tokens](api-tokens.md).

## Testing the Listener

The fastest way to verify the UDP listener is working:

```bash
echo -n '<CALL:6>DL1ABC<BAND:3>20m<MODE:3>FT8<QSO_DATE:8>20240415<TIME_ON:4>1430<EOR>' \
  | nc -u -w1 127.0.0.1 2237
```

Replace `127.0.0.1` with the hostname of your ollog instance if remote. The `-u` flag selects UDP; `-w1` exits after 1 second (required since UDP is connectionless). On Linux with GNU netcat, use `-q1` instead of `-w1`.

After sending, check your log — a new QSO from `DL1ABC` should appear under the `UDP_OPERATOR` callsign.

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
