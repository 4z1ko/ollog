# Phase 59 Discussion Log

**Date:** 2026-06-07
**Phase:** 59 — Collection Routing Foundation

## User Decisions

- Refactor QSO storage so every user has a dedicated collection.
- Collection naming convention is exactly `<username>_qsos`.
- `<username>` means `User.username`, not callsign.
- Include migration of existing shared `qsos` documents in the milestone.
- Preserve all existing external behavior: authentication, CRUD, QSO logging, ADIF, duplicate handling, stats, admin, live feed, filtering, sorting, and pagination.

## Phase Boundary

Phase 59 is the foundation only: collection-name derivation, access helper, index setup, and tests. Migration and call-site refactors are intentionally deferred to later phases in v3.1.
