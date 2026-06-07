---
gsd_state_version: 1.0
milestone: v3.1
milestone_name: Per-User QSO Collections
status: planning
stopped_at: Phase 60 planned 2026-06-07 — ready for execution
last_updated: "2026-06-07T00:00:00Z"
last_activity: 2026-06-07
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 2
  completed_plans: 1
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-07 for v3.1 milestone)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v3.1 planning — move QSO storage from one shared collection to per-user `<username>_qsos` collections.

## Current Position

Milestone: v3.1 Per-User QSO Collections
Phase: 60 Shared Collection Migration — planned
Plan: 60-01 Idempotent Shared QSO Collection Migration
Status: Ready to execute Phase 60
Last activity: 2026-06-07

```
v3.1 Progress: [#####---------------] 25% (1/4 phases)
```

## Performance Metrics

**Velocity (historical):**

- Total plans completed: 90 plans across v1.0–v2.7
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
| v1.8 | 29–31 | 3 |
| v1.9 | 32–36 | 5 |
| v2.0 | 37–38 | 2 |
| v2.1 | 39–40 | 2 |
| v2.2 | 41 | 2 |
| v2.3 | 42–43 | 2 |
| v2.4 | 44–47 | 5 |
| v2.5 | 48–50 | 3 |
| v2.6 | 51 | 3 |
| v2.7 | 52–53 | 3 |
| v2.8 | 54–56 | 6 |
| v2.9 | 57 | 1 |
| v3.0 | 58 | 1 |
| v3.1 | 59–62 | TBD |

## Accumulated Context

### Roadmap Evolution

- v2.6 milestone complete: llms.txt Support (Phase 51, 2026-04-25)
- v2.7 milestone complete: UTC Date/Time Entry (Phases 52–53, 2026-05-02)
- v2.8 milestone complete: Clear Log (Phases 54–56, 2026-05-18)
- v2.9 phase complete locally: QSO Deduplication and ADIF Duplicate Review (Phase 57, 2026-06-02)
- v3.0 milestone started: Configurable QSO Log Fields (Phase 58 planned, 2026-06-03)
- Phase 58 context gathered: field catalog limited to known ADIF/common fields, single scrollable checklist, extra selected fields append after defaults, humanized display values, only current sortable fields remain sortable (2026-06-03)
- Phase 58 research completed: official ADIF 3.1.7 confirmed as current external reference; recommended curated server-side known-field catalog, client-side localStorage normalization, generated table headers/cells, and no sort expansion (2026-06-03)
- Phase 58 UI-SPEC approved: keep gear-menu entry point, use one bounded scrollable checklist, preserve default table view and Actions column, reuse existing `data-table`/`btn-ghost` styling, and avoid new UI libraries or broad visual redesign (2026-06-03)
- Phase 58 planned: one vertical implementation plan covering field catalog/value extraction, route context, generated menu/table rendering, localStorage normalization, tests, CSS build, and validation strategy (2026-06-03)
- Phase 58 executed: shared curated QSO field catalog added, Log View menu/table/rows now render from catalog, defaults/localStorage/sort controls/actions preserved, focused tests/build passed with Mongo-backed checks skipped when MongoDB unavailable (2026-06-03)
- Phase 58 UAT verified: automated/source checks passed, manual bounded column-menu viewport check passed, and `58-UAT.md` marked complete with 5/5 tests passing and 0 issues (2026-06-07)
- v3.0 milestone archived: requirements and roadmap copied to `.planning/milestones/`, milestone audit passed, and active `REQUIREMENTS.md` removed for the next milestone cycle (2026-06-07)
- v3.1 milestone started: refactor QSO storage so every user writes to a dedicated MongoDB collection named `<username>_qsos`; include idempotent migration from the shared `qsos` collection and preserve all current QSO workflows (2026-06-07)
- Phase 59 executed: added shared username-derived QSO collection helpers, raw per-user MongoDB collection access, idempotent per-user index setup, and focused tests; verification passed with 40 passed and 16 MongoDB-dependent schema tests skipped (2026-06-07)
- Phase 59 UAT verified: 5/5 acceptance checkpoints passed with no gaps; Phase 60 migration planning is next (2026-06-07)
- Phase 60 planned: one implementation plan for an idempotent copy-only migration from shared `qsos` into `<username>_qsos`, with unresolved/ambiguous ownership reporting, target index setup, startup/CLI integration, and focused tests (2026-06-07)

### v3.1 Phase Structure

- **Phase 59** — Collection Routing Foundation: shared collection-name helper, per-user raw collection access, index setup, and tests. Completed 2026-06-07.
- **Phase 60** — Existing Data Migration: idempotently migrate shared `qsos` data into `<username>_qsos`, report unresolved operators, and preserve rowHash/ADIF extras.
- **Phase 61** — QSO CRUD and Import/Export Routing: refactor REST/UI/service/ADIF/API-token/UDP write paths to use authenticated username-derived collections.
- **Phase 62** — Cross-Feature Integration and Verification: stats, admin clear-log, live feed/SSE, backup/restore, isolation tests, and compatibility verification.

### v3.0 Phase Structure

- **Phase 58** — Configurable QSO Field Catalog and Log View Columns: replace hard-coded Log View column menu/table fields with a shared selectable field catalog, render selected ADIF-native values across headers and rows, preserve current defaults and localStorage persistence, and verify HTMX/SSE/table action behavior.

### v2.9 Phase Structure

- **Phase 57** — QSO RowHash Deduplication and ADIF Duplicate Review: canonical hashing utility, QSO `rowHash` field/index/backfill, explicit duplicate insert handling, soft-delete hash updates, and ADIF duplicate review with selectable import; covers DEDUP-01–06 and ADIF-REVIEW-01–04.

### v2.8 Phase Structure

- **Phase 54** — Operator Clear Log: `clear_operator_log()` service function, `POST /log/profile/clear` HTMX route, Danger Zone section + password-confirmation modal in `templates/log/profile.html`; covers CLR-01–05
- **Phase 55** — Admin Clear Operator Log: `POST /admin/ui/users/<username>/clear-log` HTMX route, "Clear log" button + modal in `templates/admin/users.html`; covers ACLR-01–05
- **Phase 56** — Documentation: `docs/getting-started.md` + `docs/admin.md` updated, `uv run mkdocs build --strict`, `site/` committed; covers DOC-01–03

### Key Decisions for v2.8

- Single shared `clear_operator_log(operator: str) -> int` service in `app/qso/service.py` consumed by both operator (Phase 54) and admin (Phase 55) flows — single Beanie `delete_many({_operator, _deleted: False})` filter, no duplicated delete logic
- Admin clear-log verifies admin's OWN password (`current_user.hashed_password`), NEVER `target_user.hashed_password` — defends the admin account itself, not the target user
- Distinct modal target IDs: `#clear-log-modal` (operator), `#admin-clear-log-modal` (admin) — zero DOM collision risk
- HTMX outerHTML swap pattern: form posts to confirm endpoint, response replaces the entire modal element in place (success or error fragment, both return HTTP 200)
- MkDocs Material `admonition` extension wired in `mkdocs.yml` — without it `!!! danger` blocks render as literal plain text (silent failure, no build warning)
- Documentation paths use `docs/operator-guide/profile.md` + `docs/admin-guide/account-management.md`; ROADMAP referred to stale paths (`docs/getting-started.md`, `docs/admin.md`) excluded from nav — Phase 56 D-04 resolved via override mechanism

### Key Decisions for v2.7

- All changes fit in two existing files: `templates/log/form.html` and `app/main.py`
- No new dependencies — browser-native JS + existing HTMX hooks + existing PyMongo migration pattern
- Phase 52 (backend only): idempotent `normalize_time_on()` startup migration in `app/main.py` pads HHMM → HHMM00 using anchored regex `^\d{4}$` to prevent double-padding
- Phase 53 (frontend only): all form enhancements in `templates/log/form.html`
- `readonly` (not `disabled`) on locked fields — `disabled` silently drops field value from POST body
- Live clock uses `Date.getUTC*()` exclusively — never `getHours()`/`getDate()`/etc. which return local timezone
- HHMM normalization fires in `htmx:beforeRequest` hook (already present in form.html)
- Post-submit behavior toggle reads/writes `localStorage`
- `hx-target="#qso-result"` points at a sibling div — form DOM, event listeners, and setInterval survive every submit; no re-initialization hook needed
- `parse_adif_datetime()` in service.py already handles both HHMM and HHMMSS — DB-02 is a server-side validation confirmation, not a code change

### Critical Build Rules (carried forward)

- **FOUC prevention:** The inline IIFE in `base.html` `<head>` is load-bearing. Never move it, add `defer`/`async`, or extract it to an external file.
- **Tailwind purge:** New `dark:` classes must appear as complete literal strings in scanned template files. Always run `npm run build` + grep verification for new classes before committing templates or `input.css`.
- **Safari backdrop-filter:** Declare `-webkit-backdrop-filter` explicitly in `@layer components` for glass card classes. Use fixed pixel values, not CSS variable references.
- **PostCSS autoprefixer:** Always configure `postcss.config.js` with `autoprefixer({ remove: false })` when writing explicit webkit prefixes in source CSS.
- **FastAPI sub-app StaticFiles:** Every FastAPI sub-app that serves HTML must have its own `StaticFiles` mount for `/static`. The main app mount does not propagate.
- **apscheduler<4 upper bound is load-bearing:** Do not touch `pyproject.toml` APScheduler constraints.
- **HTMX error fragments return HTTP 200:** HTMX 2.x silently drops response body on 4xx — all error HTML fragments must return 200.
- **Password verify pattern:** Use `verify_password(plain, user.hashed_password)` from `app/auth/service.py` (pwdlib Argon2). Admin routes use `require_admin_cookie` dependency; operator routes use `get_current_user_cookie`.

### Known Tech Debt

- `QSO.find_active()` in models.py — dead production code
- `from_mongo_dt()` in utils.py — tested, not called in production
- Docker end-to-end verification pending (requires live Docker environment)
- `aria-label` inversion on padlock buttons in `templates/log/form.html` — reads "Lock field" when locked (should say "Unlock"); screen-reader-only, no functional impact (v2.7)

### Pending Todos

- Run `/gsd-execute-phase 60` to implement the shared collection migration.

### Ship Blockers

- `gh` CLI is not installed, so `$gsd-ship` cannot create a PR from this environment.
- `gsd-sdk` is not on PATH, so the formal automated ship workflow could not be executed end-to-end.
- Full-suite pytest remains noisy from unrelated legacy Mongo fixture URI issues and existing non-phase failures; Phase 57 focused validation is passing.

## Deferred Items

Items acknowledged and deferred at v2.8 milestone close on 2026-05-18:

| Category | Item | Status |
|----------|------|--------|
| human-uat | 54-operator-clear-log/54-HUMAN-UAT.md | partial — visual-only browser checks (card styling order, HTMX innerHTML swap, HTMX outerHTML swap). Behavioral coverage duplicated by `tests/test_clear_log.py` (6 async tests, all green). |
| human-uat | 55-admin-clear-operator-log/55-HUMAN-UAT.md | partial — visual-only browser checks (modal backdrop legibility in dark mode, HTMX cancel-swap behavior). Behavioral coverage duplicated by `tests/test_admin_clear_log.py` (6 async tests, all green). |

## Session Continuity

Last session: 2026-06-07 (v3.1 milestone start)
Stopped at: v3.1 requirements and roadmap created; `gsd-sdk` is not on PATH, so milestone bookkeeping was applied manually
Next: run `/gsd-execute-phase 60`
