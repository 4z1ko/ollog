# Requirements: v1.5 Documentation Update

## Milestone Goal

Update the MkDocs documentation site to cover the v1.4 UDP Interface: new environment variables, how operators send QSOs via UDP (nc, WSJT-X, N1MM+, Log4OM), and troubleshooting UDP-specific issues. Rebuild and commit the static site.

## Scope

- `docs/deployment.md` — new UDP env vars + Docker Compose port mapping example
- `docs/getting-started.md` — new "Sending QSOs via UDP" section with tool configs
- `docs/troubleshooting.md` — new UDP troubleshooting section
- `site/` — rebuilt static output from mkdocs build

## Requirements

### Deployment Guide

| ID | Requirement |
|----|-------------|
| DOC-01 | Add `UDP_ENABLED`, `UDP_PORT`, `UDP_BIND_HOST`, `UDP_OPERATOR` to the Environment Variables table with their types, defaults (`false` / `2237` / `127.0.0.1` / none), and descriptions |
| DOC-02 | Add a Docker Compose example snippet showing how to enable UDP: set env vars and expose the UDP port mapping (`- "2237:2237/udp"`) |

### Operator Getting-Started Guide

| ID | Requirement |
|----|-------------|
| DOC-03 | Add a "Sending QSOs via UDP" section explaining the feature: ADIF datagrams sent to the configured UDP port are logged under the `UDP_OPERATOR` callsign |
| DOC-04 | Include a `nc` one-liner example that sends a minimal ADIF datagram for manual testing |
| DOC-05 | Include WSJT-X configuration steps: Settings → Reporting → UDP Server, set host/port to match deployment |
| DOC-06 | Include N1MM+ configuration steps: Config → Configure Ports → UDP ADIF broadcast, set host/port |
| DOC-07 | Include Log4OM configuration steps for sending ADIF messages to ollog over UDP |

### Troubleshooting Guide

| ID | Requirement |
|----|-------------|
| DOC-08 | Add troubleshooting entry: UDP socket not binding — causes (port in use, `UDP_BIND_HOST` mismatch with container network), fixes |
| DOC-09 | Add troubleshooting entry: `UDP_OPERATOR` callsign not found — symptom (WARNING log), fix (ensure operator account exists and callsign matches exactly) |
| DOC-10 | Add troubleshooting entry: QSOs arrive but don't appear in the log — causes (required ADIF field missing, duplicate detected within ±2 min), how to diagnose from logs |
| DOC-11 | Add troubleshooting entry: No UDP activity in logs — cause (`UDP_ENABLED` not set or `false`), fix |

### Static Site

| ID | Requirement |
|----|-------------|
| DOC-12 | Run `mkdocs build` and commit the updated `site/` output alongside the doc source changes |
