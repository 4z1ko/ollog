# Feature Landscape

**Domain:** Ham Radio Online QSO Logbook (multi-operator, ADIF-native)
**Researched:** 2026-04-03
**Confidence note:** WebSearch and WebFetch tools were unavailable for this session.
All findings are drawn from training knowledge of the ham radio software ecosystem
(ADIF specification, LoTW documentation, QRZ logbook, CloudLog, HRDLogbook, Log4OM,
N1MM+, DXKeeper). The ADIF standard and LoTW API are stable and well-documented.
Confidence levels reflect this constraint honestly.

---

## Table Stakes

Features users expect in any online logbook. Missing = product feels incomplete or
untrustworthy. These are baseline requirements drawn from what every established
logbook (QRZ Logbook, CloudLog, HRDLogbook, Log4OM) provides.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| QSO entry (manual web form) | Primary daily use — operators must be able to log a contact directly | Low | Fields: callsign, date/time UTC, band/frequency, mode, RST sent/received, operator (own callsign). All are ADIF fields. |
| Per-operator logbook (by callsign) | Ham radio identity is the callsign; every operator expects their log to be separate | Low | Already in project scope. Callsign = logbook owner. |
| QSO list / log view with pagination | Operators need to review past contacts | Low | Sortable by date, callsign, band, mode. Paginate — logs can reach 100k+ QSOs. |
| Search / filter log entries | Operators look up specific QSOs constantly (confirming a contact, checking dupe) | Low-Med | Filter by callsign, date range, band, mode at minimum. Full-text is nice but not required. |
| ADIF import (.adi / .adif) | All operators have existing logs from desktop software (WSJT-X, N1MM+, DXKeeper, etc.) | Med | Must handle large files gracefully. Duplicate detection on import is expected. |
| ADIF export (.adi / .adif) | Operators routinely export to submit to LoTW, eQSL, contest sites | Low | Full ADIF field passthrough required — no field loss on round-trip. |
| Duplicate QSO detection | Logging the same contact twice is a known workflow problem | Med | On manual entry and import. Same callsign + band + mode + time window = probable dupe. |
| UTC date/time handling | Ham radio operates on UTC by convention; local time display is a source of errors | Low | Store in UTC always. Display in UTC by default. |
| Band and mode fields | Core QSO metadata. Every log UI shows these. | Low | Use ADIF enumerated values for BAND and MODE. |
| Frequency field | More precise than band; required for certain awards and contest logs | Low | Store in MHz as per ADIF spec (FREQ field). |
| RST sent / received | Standard signal report; expected on every QSO form | Low | ADIF: RST_SENT, RST_RCVD. |
| DXCC entity lookup / display | Operators constantly think in terms of DXCC entity, not just callsign | Med | Callsign → DXCC entity derivation is expected. Can use cty.dat (Country Files by AD1C) or clublog API. |
| QSO count / basic statistics | Users want to see "N QSOs in log" at a glance | Low | Count per operator logbook, total. |
| Data integrity on delete | Accidental deletion is catastrophic; confirmation required | Low | Soft-delete or confirmation dialog at minimum. |
| Responsive web UI | Operators log from shack PCs, laptops, tablets | Low-Med | Mobile-optimized is differentiating; basic responsive is table stakes. |

---

## Differentiators

Features that set a logbook apart. Not universally expected, but valued by serious
operators. These are the features where CloudLog, QRZ Logbook, and modern tools
distinguish themselves.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Real-time multi-operator visibility | See other operators logging simultaneously — eliminates duplicate contacts on a club station | Med-High | In scope for this project. WebSocket or SSE for live updates across operators. This is the primary differentiator over single-user logbooks. |
| LoTW upload integration | Direct upload to ARRL Logbook of the World — saves a multi-step export/upload workflow | High | Requires TQSL signing. Each operator needs their own TQSL cert. Complex but high value. Defer to v2. |
| QSO confirmation status display | Showing LoTW / eQSL / direct QSL status on each QSO is very useful | Med | Requires syncing back confirmation data from LoTW/eQSL. Can start with a manual QSL_SENT / QSL_RCVD field display (ADIF-native) before adding live sync. |
| Callsign lookup on entry | Auto-populate operator name, QTH, DXCC from callsign databases (QRZ.com XML API or HamQTH) | Med | Reduces data entry error. QRZ XML requires subscription; HamQTH is free. |
| Band / mode statistics dashboard | Charts of QSOs by band, mode, time — operators love seeing their activity patterns | Med | QSOs per band, per mode, per time-of-day. Easy win with charting library. |
| Worked/confirmed grid squares | Grid square (Maidenhead) tracking per operator — used for VHF/UHF awards and casual tracking | Med | MY_GRIDSQUARE and GRIDSQUARE are ADIF fields. Map visualization is a further differentiator. |
| Per-operator activity log / audit trail | Who logged what and when — important for club stations with multiple operators | Med | Timestamps with operator ID on all mutations. Valuable for dispute resolution. |
| Admin user management UI | Ability to create/disable operator accounts without touching a CLI or database | Low | In scope per project context (admin-managed accounts). Makes the system operable without developer access. |
| Flexible QSO editing | Fix errors after the fact — wrong callsign, wrong band, wrong time | Low | Basic CRUD. Many logbooks make this awkward; clean editing is valued. |
| CSV export (in addition to ADIF) | Some users want to analyze their log in a spreadsheet | Low | Straightforward given the ADIF field-per-column structure. |
| N+1 ADIF field passthrough | Preserve all ADIF fields on import even if the UI doesn't show them | Low | Critical for lossless round-trips. Store unknown fields in a catch-all sub-document. |
| QSO notes / comment field | Operators annotate contacts with propagation notes, antenna used, contest exchange | Low | ADIF COMMENT and NOTES fields. Low complexity, high daily value. |
| Contest exchange fields | CONTEST_ID, SRX/STX fields for contest logging | Low | ADIF-native. Not full contest logging, but preserving the fields is important for import/export fidelity. |

---

## Anti-Features

Features to explicitly NOT build in v1. Scope control is critical; each of these
carries significant complexity that would delay shipping a trustworthy core.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Award tracking (DXCC, WAS, VUCC, etc.) | Complex rule sets, entity lists, exception handling, credit sync with ARRL. A full product in itself. | Project scope explicitly excludes this. Store ADIF fields that would support it later (DXCC, STATE, etc.) so the data is there when ready. |
| LoTW automatic sync / TQSL integration | TQSL certificate management per-operator is operationally complex; LoTW API is underdocumented and brittle | Support ADIF export so users can do manual LoTW upload via TQSL. Revisit in v2. |
| Self-registration / public sign-up | Admin-managed accounts is a deliberate project requirement | Keep admin-only account creation. Do not add a registration flow. |
| Real-time DX cluster integration | Spot feeds (DX cluster, RBN, PSK Reporter) are a separate product concern; adds WebSocket complexity to the wrong layer | Out of scope. Operators use dedicated cluster clients. |
| Contest mode / rate meter | Full contest logging (rate, multiplier tracking, dupe checking per exchange) is a specialized product. N1MM+ and Win-Test own this. | Store contest exchange fields passively; do not build contest-specific UI. |
| QSL card design / printing | Physical and digital QSL card management is unrelated to the logbook's core job | Operators use dedicated QSL services (OQRS, QRZ QSL). |
| Propagation prediction / DX prediction tools | Valuable but orthogonal; would require integrating solar index APIs, VOACAP, etc. | Out of scope. Operators use dedicated propagation tools. |
| Integrated SDR / radio control (CAT) | Radio control (Hamlib, OmniRig) belongs in desktop clients, not a web logbook | Log submission via REST API is the right integration point. |
| Social / feed features | Activity feeds, "likes", following other operators — not what serious operators want from a logbook | Focus on the log. Trust and accuracy are the brand. |
| Mobile native app | Adds a separate release and review cycle | Responsive web UI covers mobile use. Revisit only if there is strong demand. |

---

## Feature Dependencies

```
ADIF import → Duplicate detection (import triggers dupe check)
ADIF import → N+1 field passthrough (import must not drop unknown fields)
ADIF export → QSO data model completeness (can only export what is stored)
Manual QSO entry → Duplicate detection (entry triggers dupe check)
Manual QSO entry → DXCC entity lookup (optional enhancement on callsign field)
Callsign lookup → QRZ XML API or HamQTH API account (external dependency)
Multi-operator logging → Per-operator logbook (prerequisite)
Multi-operator logging → Real-time visibility (builds on top of per-operator model)
LoTW upload (future) → ADIF export (LoTW upload = signed ADIF)
Award tracking (future) → DXCC entity on every QSO (data must be stored now)
Admin user management UI → Account model (prerequisite)
QSO confirmation status display → QSL_SENT / QSL_RCVD ADIF fields (already in model)
Statistics dashboard → QSO storage (reads from existing data, no new model needed)
```

---

## MVP Recommendation

The MVP must be trustworthy above all else. Operators will not migrate their log to a
system they cannot trust. Trust = data fidelity, no silent field loss, reliable duplicate
detection, and a clean import/export round-trip.

**Prioritize for v1:**

1. Per-operator logbook identified by callsign (core model)
2. Manual QSO entry form (callsign, date/time UTC, band, frequency, mode, RST sent/received, operator callsign)
3. ADIF import with duplicate detection and N+1 field passthrough
4. ADIF export (lossless round-trip)
5. QSO list view with search and filter (callsign, date range, band, mode)
6. DXCC entity derivation on stored callsigns (using cty.dat — no external API dependency)
7. QSO count and basic per-operator statistics
8. Admin account management UI
9. Multi-operator simultaneous logging (core project requirement)
10. QSO editing and soft-delete with confirmation

**Defer to v2 or later:**

- Callsign lookup via QRZ XML / HamQTH (external API dependency; adds signup friction)
- Real-time multi-operator visibility (WebSocket layer — high value, but v1 can use page refresh)
- LoTW upload integration (TQSL complexity)
- Statistics dashboard with charts (low-risk addition after core is stable)
- CSV export (easy addition, not urgent)

**Note on "real-time" multi-operator logging:** The project requirement for simultaneous
multi-operator logging means concurrent writes must be safe (no data corruption). The
REST API + MongoDB model handles this. Real-time *visibility* (seeing others' QSOs appear
without refresh) is a differentiator that can be phased in after the write path is solid.

---

## Competitive Landscape Notes

**QRZ Logbook** (HIGH confidence — stable product, widely used)
- Online log tied to QRZ.com callsign profile
- ADIF import/export, LoTW sync, eQSL sync
- Basic award tracking, DXCC counter
- Single-operator only
- Gated behind QRZ subscription for full features

**ARRL LoTW** (HIGH confidence)
- Not a logbook — a QSO confirmation system
- ADIF upload via TQSL (signing tool), not a logging interface
- Gold standard for award credit confirmation
- Integration is the goal, not competition

**CloudLog** (HIGH confidence — open source, well-documented)
- Self-hosted PHP/MySQL web logbook
- Multi-operator aware (station profiles)
- ADIF import/export, LoTW sync, clublog sync, eQSL sync
- API available
- Closest open-source analog to this project
- Weakness: dated UI, complex self-hosting, PHP stack

**HRD Logbook / Ham Radio Deluxe** (MEDIUM confidence)
- Desktop-primary with cloud sync
- Deep radio control integration (CAT)
- Strong contest and award tracking
- Windows-only; subscription required
- Not an online-first logbook

**Log4OM** (MEDIUM confidence)
- Desktop application, Windows
- Strong ADIF support, LoTW integration
- Club/multi-operator features
- Not a web product

**N1MM+** (HIGH confidence)
- Contest logging only, desktop, Windows-only, free
- Exports ADIF; not a general logbook

**DXKeeper** (MEDIUM confidence)
- Desktop, Windows, part of DXLab Suite
- Extremely comprehensive ADIF support
- Single-operator focused

**Gap this project fills:** There is no well-supported, modern, web-native, multi-operator
logbook with a clean REST API and ADIF-native data model that is not self-hosted PHP
(CloudLog) or tightly coupled to a callsign registry (QRZ). This project occupies that gap.

---

## Sources

**Confidence levels:**

- ADIF specification (fields, enumerations, format): HIGH — based on ADIF 3.x spec which is
  stable and widely implemented. Fields used (BAND, MODE, FREQ, RST_SENT, RST_RCVD,
  QSL_SENT, QSL_RCVD, DXCC, GRIDSQUARE, COMMENT, NOTES, CONTEST_ID, SRX, STX) are
  long-established ADIF fields. Source: https://www.adif.org/adif.htm
- QRZ Logbook features: HIGH — product has been stable and documented for years
- LoTW behavior (upload-only, TQSL requirement): HIGH — core architectural fact of LoTW
- CloudLog feature set: HIGH — open source, GitHub-documented, widely discussed in community
- HRDLogbook and Log4OM feature sets: MEDIUM — training knowledge, not directly verified
  in this session due to tool unavailability
- Market gap analysis: MEDIUM — based on community discussion patterns in training data;
  should be verified with current ham radio forums (QRZ forums, /r/amateurradio) before
  treating as definitive

**Note on tool availability:** WebSearch, WebFetch, and Bash tools were all denied in this
session. All findings are from training knowledge. The ham radio logbook ecosystem is
stable enough that ADIF fields, LoTW architecture, and CloudLog feature sets are unlikely
to have changed materially since training cutoff. The competitive landscape section
should be spot-checked against current product pages before finalizing roadmap decisions.
