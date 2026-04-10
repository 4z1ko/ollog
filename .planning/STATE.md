# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-09)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v1.8 Admin Isolation, Backup & Docs — defining requirements

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements for v1.8
Last activity: 2026-04-09 — Milestone v1.8 started; v1.7 complete (Phases 25–28)

Progress: [█████████████████████░░░░░░░░░] ~67% (28/~40 estimated phases)

## Performance Metrics

**Velocity (historical):**
- Total plans completed: 46+ (v1.0: 19, v1.1: 7, v1.2: 2, v1.3: 8, v1.4: 4, v1.5: 4, v1.6: 2, v1.7: 4)
- Average duration: ~5–20 min/plan

**By Milestone:**

| Milestone | Phases | Plans |
|-----------|--------|-------|
| v1.0 | 1–6 | 19 |
| v1.1 | 7–10 | 7 |
| v1.2 | 11–12 | 2 |
| v1.3 | 13–15 | 8 |
| v1.4 | 16–18 | 4 |
| v1.5 | 19–22 | 4 |
| v1.6 | 23–24 | 2 |
| v1.7 | 25–28 | 4 |
| v1.8 | 29–? | TBD |

## Accumulated Context

### v1.8 Milestone Goals

1. **Admin Container** — Separate Docker Compose service (shared codebase), port 8001, admin-only routes (/admin/*, /auth), stoppable independently without affecting operator app
2. **Database Backup** — `python -m app.backup` CLI → mongodump .gz to ./backups/<timestamp>.gz; BACKUP_SCHEDULE cron env var + S3 credentials for automated scheduled uploads
3. **Docs Rewrite** — Full comprehensive rewrite of /guide covering all features from v1.0–v1.8 (deployment, getting-started, API reference, admin guide, troubleshooting)

### Key Decisions (v1.7 — carried forward)

Full decision log in PROJECT.md Key Decisions table.

- HMAC-SHA256 for token hashing (not Argon2 — 200-500ms verify is unacceptable per request)
- Separate `api_tokens` Beanie collection (not embedded in User)
- `X-API-Key` header (not `Authorization: Bearer`) — clean separation from JWT session auth
- `APP_OLLOG_TOKEN` fixed ADIF field name (APP_ prefix per ADIF spec convention)
- `auto_error=False` on both optional schemes; raise HTTP 401 manually
- Lazy cache invalidation with `_dirty=True` flag (UDPTokenCache)

### Known Tech Debt

- `QSO.find_active()` in models.py — dead production code
- `from_mongo_dt()` in utils.py — tested, not called in production
- Docker end-to-end verification pending (requires live Docker environment)

### Pending Todos

None.

## Session Continuity

Last session: 2026-04-09
Stopped at: v1.7 complete; v1.8 milestone started, requirements phase beginning
Resume file: None
