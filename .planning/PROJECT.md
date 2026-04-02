# ollog — Ham Radio Online Logbook

## What This Is

A multi-operator online logbook for amateur radio operators. Each operator maintains their own individual logbook identified by their callsign, and can log QSOs in real-time via a REST API or directly through a browser-based web interface. All QSO data is modeled on the ADIF (Amateur Data Interchange Format) specification, enabling seamless import/export with tools like LoTW, QRZ, and eQSL.

## Core Value

Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss — the shared platform stays out of their way and just works.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Operators can be created and managed by an admin (no self-registration)
- [ ] Each operator authenticates with username/password and has their own individual logbook
- [ ] Operators can log QSOs via REST API using ADIF field format in real-time
- [ ] Operators can log QSOs via web UI (callsign, band, mode, RST, date/time, and all ADIF fields)
- [ ] QSOs are stored internally using ADIF field names as the data model (MongoDB)
- [ ] Operators can import existing logbooks via .adi/.adif file upload
- [ ] Operators can export their logbook as an ADIF file
- [ ] Multiple operators can log simultaneously without data conflicts
- [ ] Operators can search and filter their QSO history (by callsign, band, mode, date)
- [ ] Basic duplicate detection (warn if callsign already worked on same band/mode)

### Out of Scope

- Award tracking (DXCC, WAS, WAZ, etc.) — deferred to v2
- Self-registration — admin controls all operator accounts
- Real-time chat or club coordination features — not core to logging
- Mobile native app — web UI is responsive, no native app in v1

## Context

- **ADIF Spec:** https://adif.org/317/ADIF_317.htm — full spec for field names, enumerations, and file format. All QSO fields should conform to ADIF 3.1.7.
- **Domain:** Ham radio operators log "QSOs" (contacts) — each QSO captures the other station's callsign, frequency/band, mode (CW, SSB, FT8, etc.), signal reports (RST), date, time, and many optional fields.
- **ADIF file format:** Uses tag-based encoding like `<CALL:4>W1AW <BAND:3>20M <MODE:3>SSB <EOR>` — import/export must handle this correctly.
- **Simultaneous logging:** A club station or contest team may have multiple operators active at the same time — data integrity under concurrent writes is critical.

## Constraints

- **Tech Stack**: Python backend, MongoDB for storage — chosen by operator
- **ADIF Version**: Conform to ADIF 3.1.7 specification
- **Deployment**: Must run self-hosted (local server) or cloud-deployed without code changes — twelve-factor style configuration
- **Auth**: Admin-managed accounts only — no public self-registration endpoint

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Individual logs per operator | Each ham has their own callsign and logbook identity — merging into a shared log loses attribution | — Pending |
| ADIF field names as internal data model | Eliminates translation layer on import/export; stays spec-compliant by default | — Pending |
| Admin-managed accounts | Prevents unauthorized access; appropriate for club or team deployments | — Pending |
| MongoDB for QSO storage | Flexible schema fits ADIF's large optional field set; good for document-per-QSO model | — Pending |

---
*Last updated: 2026-04-03 after initialization*
