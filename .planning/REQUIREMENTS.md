# Requirements: ollog

**Defined:** 2026-04-15
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss

## v2.3 Requirements

### Navigation

- [ ] **STATS-01**: Operator can access a statistics page at `/log/stats` via a "Stats" link in the sidebar nav

### Charts

- [ ] **STATS-02**: Stats page displays a pie chart of QSO count by band (all bands present in the operator's log)
- [ ] **STATS-03**: Stats page displays a pie chart of QSO count by mode (all modes present in the operator's log)
- [ ] **STATS-04**: Stats page displays a pie chart of top 8 DXCC entities by QSO count; remaining entities are grouped as a single "Other" slice (only if remainder is non-empty)
- [ ] **STATS-05**: Stats page displays a scalar count of unique DXCC entities worked (e.g. "42 entities")

### Data & Safety

- [ ] **STATS-06**: All statistics are scoped to the authenticated operator's log (JWT-isolated, filtered by `_operator`)
- [ ] **STATS-07**: Stats page shows an empty-state message when the operator has no QSOs logged

### Visual

- [ ] **STATS-08**: Charts adapt to dark/light theme toggle without a page reload (re-initialized on theme change)

## Future Requirements

### Enhanced Statistics

- **STATS-F01**: Filter statistics by year (year selector with all-time option)
- **STATS-F02**: Statistics for continents / CQ zones / ITU zones
- **STATS-F03**: Award tracking overlays (DXCC entity worked/confirmed, WAS, WAZ)
- **STATS-F04**: QSO rate chart (contacts per hour/day)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Date/year range filtering | Scope creep for v2.3 — deferred to future |
| Award tracking (DXCC confirmed, WAS, WAZ) | Explicit PROJECT.md exclusion — requires LoTW integration |
| Continent / CQ zone / ITU zone breakdown | No ISO-to-continent mapping in codebase; cty.dat deferred |
| Per-band DXCC matrix | Award tracking scope, deferred |
| Real-time SSE chart refresh | Aggregation pipelines are expensive under FT8 burst logging |
| External callsign lookup (QRZ/HamQTH) | API dependency with rate-limit friction — out of scope |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| STATS-01 | Phase 43 | Pending |
| STATS-02 | Phase 43 | Pending |
| STATS-03 | Phase 43 | Pending |
| STATS-04 | Phase 43 | Pending |
| STATS-05 | Phase 43 | Pending |
| STATS-06 | Phase 42 | Pending |
| STATS-07 | Phase 42 | Pending |
| STATS-08 | Phase 43 | Pending |

**Coverage:**
- v2.3 requirements: 8 total
- Mapped to phases: 8 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-15*
*Last updated: 2026-04-15 after roadmap creation (Phases 42–43)*
