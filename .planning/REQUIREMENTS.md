# Requirements: ollog — v3.4 Responsive Favicon

**Defined:** 2026-06-13
**Core Value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss.

## v3.4 Requirements

### Favicon

- [x] **FAV-01**: Every full-page operator web page includes a favicon link based on `favicon/favicon.ico`.
- [x] **FAV-02**: Every full-page admin web page includes a favicon link based on `favicon/favicon.ico`.
- [x] **FAV-03**: The favicon is served from an app-accessible static URL in both the operator app and admin app.
- [x] **FAV-04**: Shared template wiring adds favicon metadata once without duplicating tags across individual pages.
- [x] **FAV-05**: Partial HTMX templates remain unchanged and do not gain invalid standalone `<head>` favicon markup.
- [x] **FAV-06**: Browser-friendly responsive favicon metadata is available for modern desktop browsers, including `.ico` and the provided PNG/manifest bundle when appropriate.
- [x] **FAV-07**: Existing page behavior, authentication, HTMX swaps, styling, and guide/static serving remain unchanged.

## Future Requirements

### Branding Enhancements

- **FAV-FUT-01**: App can use environment-specific or deployment-specific favicon variants.
- **FAV-FUT-02**: Guide documentation can use a dedicated favicon if the MkDocs build needs separate branding.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Broader UI redesign | User asked only for favicon; prior frontend design changes were explicitly undone. |
| Mobile phone UI changes | User previously specified not to create a mobile phone UI for app design work. |
| Dynamic per-operator favicon | Current need is one responsive favicon for all pages. |
| Rebranding page layout, colors, or typography | Favicon should not alter app functionality or visual layout. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FAV-01 | Phase 65 | Complete |
| FAV-02 | Phase 65 | Complete |
| FAV-03 | Phase 65 | Complete |
| FAV-04 | Phase 65 | Complete |
| FAV-05 | Phase 65 | Complete |
| FAV-06 | Phase 65 | Complete |
| FAV-07 | Phase 65 | Complete |

**Coverage:**
- v3.4 requirements: 7 total
- Mapped to phases: 7
- Unmapped: 0

---
*Requirements defined: 2026-06-13*
*Last updated: 2026-06-13 after Phase 65 execution*
