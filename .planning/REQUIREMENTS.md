# Requirements: ollog — Callsign Entity Lookup & Country Flags

**Defined:** 2026-04-04
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss

## v1.2 Requirements

Requirements for v1.2 Callsign Entity Lookup & Country Flags milestone.

### Prefix Resolver

- [ ] **PRFX-01**: System resolves a callsign to its ITU-allocated country name and ISO 3166-1 alpha-2 code using range-aware longest-prefix-match against the bundled ITU Series Ranges data
- [ ] **PRFX-02**: Resolver strips portable/operational suffixes (`/P`, `/M`, `/QRP`, digit-only area suffixes like `/7`) before prefix matching, using the base callsign
- [ ] **PRFX-03**: Resolver treats `/MM` (maritime mobile) and `/AM` (aeronautical mobile) as unresolvable — returns `None` without attempting country lookup
- [ ] **PRFX-04**: Non-country ITU entities (e.g. C7 → World Meteorological Organization, 4U → UN/ITU) return `None` for ISO code — no flag, no error

### Flag Display

- [ ] **FLAG-01**: Each QSO row in the log table displays a flag `<img>` icon next to the callsign when the prefix resolves to a valid ISO alpha-2 code
- [ ] **FLAG-02**: QSO rows where the prefix does not resolve (unknown prefix, `/MM`, non-country entity) display no flag — no error, no broken image

## Future Requirements

### Feed & Form

- **FEED-01**: Flag icon displayed in the real-time SSE station feed next to callsign
- **FEED-02**: Live flag preview in the QSO entry form as operator types callsign

### Advanced Lookup

- **ADV-01**: Geographic suffix override (e.g. `W1AW/KH6` resolves to Hawaii/USA rather than continental USA)
- **ADV-02**: DXCC entity derivation from callsign (requires cty.dat integration)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Storing ISO code or country in QSO record | Prefix allocations can change; render-time lookup is correct |
| cty.dat-based DXCC entity lookup | Requires cty.dat integration — v2 |
| Geographic suffix override (/KH6 etc.) | Out of scope for v1.2; resolver designed to accept override logic later |
| Callsign lookup (QRZ/HamQTH) | External API dependency — already Out of Scope in PROJECT.md |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PRFX-01 | Phase 11 | Complete |
| PRFX-02 | Phase 11 | Complete |
| PRFX-03 | Phase 11 | Complete |
| PRFX-04 | Phase 11 | Complete |
| FLAG-01 | Phase 12 | Complete |
| FLAG-02 | Phase 12 | Complete |

**Coverage:**
- v1.2 requirements: 6 total
- Mapped to phases: 6
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-04 after initial v1.2 definition*
