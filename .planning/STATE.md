---
gsd_state_version: 1.0
milestone: v3.3
milestone_name: ACLog QSO Sync
status: planning
stopped_at: Phase 64 UI-SPEC approved
last_updated: "2026-06-12T20:36:00Z"
last_activity: 2026-06-12
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 1
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-12 after starting v3.3 milestone)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** v3.3 ACLog QSO Sync — manual bridge sync from remote ACLog into the operator's local username-derived QSO collection.

## Current Position

Milestone: v3.3 ACLog QSO Sync
Phase: 64 — ACLog Bridge Manual Sync
Plan: Not started
Status: UI design contract approved; ready for final phase planning
Last activity: 2026-06-12

```
v3.3 Progress: [--------------------] 0% (0/1 phases)
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
| v3.1 | 59–62 | 4 |
| v3.2 | 63 | 1 |

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
- Phase 60 executed: added copy-only shared QSO migration module, CLI/report support, startup wiring, unresolved/ambiguous ownership reporting, insert-only target writes, and focused tests; verification passed with 33 tests (2026-06-07)
- Phase 60 UAT verified: 5/5 acceptance checkpoints passed with no gaps; Phase 61 workflow refactor planning is next (2026-06-07)
- Phase 61 planned: one high-complexity implementation plan to route REST, browser, ADIF, API-token, UDP, duplicate handling, rowHash, custom defaults, and clear-log through authenticated username-derived collections while preserving public behavior (2026-06-07)
- Phase 61 executed: direct QSO workflows now route through authenticated/resolved user collections for REST, browser UI, ADIF, API-token, UDP, ACLog, custom defaults, and operator clear-log; verification passed with focused and workflow tests, with Mongo-backed integration checks skipped where local MongoDB is unavailable (2026-06-08)
- Phase 61 UAT verified: 5/5 acceptance checkpoints passed with no gaps; Phase 62 cross-feature integration planning is next (2026-06-08)
- Phase 62 context gathered: use app-level live feed broadcasts from write paths, keep backup/restore full-database scoped, add small shared helpers for stats/admin routing, and use layered verification with live-Mongo checks only for highest-risk paths (2026-06-08)
- Phase 62 planned: one implementation plan for stats/admin dynamic collection routing, app-level live feed broadcasts, backup/restore dynamic collection tests, and layered cross-feature isolation/regression verification (2026-06-08)
- Phase 62 executed: stats and admin clear-log now use per-user collections, app-created inserts broadcast live feed rows from write paths, startup no longer watches shared `qsos`, backup/restore dynamic collection round-trip coverage was added, and layered verification passed with Mongo-dependent tests skipped where unavailable (2026-06-08)
- Phase 62 UAT verified: 6/6 acceptance checkpoints passed with no gaps; v3.1 is ready for milestone completion (2026-06-08)
- v3.1 milestone archived: roadmap and requirements copied to `.planning/milestones/`, active roadmap collapsed, active requirements removed for the next milestone cycle, and PROJECT.md moved to between-milestones state (2026-06-08)
- v3.2 milestone started: improve ACLog bridge imports by using ACLog `INCLUDEALL` full-record responses so imported QSOs can include all exposed fields and user-customized Other fields (2026-06-08)
- Phase 63 added: ACLog Full-Record Import via INCLUDEALL (2026-06-08)
- Phase 63 planned: one implementation plan for parser full-record support, event/full/state merge logic, bridge INCLUDEALL enrichment, Other field mapping, docs, and deterministic tests (2026-06-08)
- Phase 63 executed: ACLog parser now converts INCLUDEALL full-record responses, the bridge requests `LIST INCLUDEALL` after `ENTEREVENT` and ingests matched enriched records, Other fields are preserved/mapped, docs were updated, and focused tests were added; local pytest execution is blocked because pytest is not installed in this shell, while Python syntax compilation passed (2026-06-08)
- Phase 63 UAT verified: 5/5 acceptance checkpoints passed with no gaps; v3.2 is ready for milestone completion (2026-06-09)
- v3.2 milestone archived: roadmap and requirements copied to `.planning/milestones/`, active roadmap collapsed, active requirements removed for the next milestone cycle, and PROJECT.md moved to between-milestones state (2026-06-09)
- v3.3 milestone started: add manual ACLog bridge synchronization from Profile Settings using `<CMD><LIST><INCLUDEALL></CMD>`, insert only remote QSOs missing from the operator's local collection, and show an inline sync report (2026-06-12)

### v3.3 Phase Structure

- **Phase 64** — ACLog Bridge Manual Sync: add per-bridge Sync action on Profile Settings, all-record `LIST INCLUDEALL` client flow, additive-only import with duplicate/rowHash preservation, inline report, tests, and docs. Planned 2026-06-12.
- Phase 64 context gathered: Sync applies only to saved bridges, reports via existing `#profile-result`, runs synchronously with fixed timeout and no app-side cap, uses "Missing QSOs imported" report wording, and prefers exact rowHash pre-check while preserving existing duplicate blocking (2026-06-12)
- Phase 64 research and validation strategy completed: reuse `app/aclog/parser.py` multi-record LIST parsing, add separate manual sync helper/route, keep live bridge behavior unchanged, and verify with parser/client/profile UI tests; PLAN.md is blocked by missing UI-SPEC per GSD UI safety gate (2026-06-12)
- Phase 64 UI-SPEC approved: reuse existing Profile Settings design system, render Sync only for saved bridge rows, target `#profile-result`, use compact report copy, and avoid new UI libraries or broad redesign (2026-06-12)

### v3.1 Phase Structure

- **Phase 59** — Collection Routing Foundation: shared collection-name helper, per-user raw collection access, index setup, and tests. Completed 2026-06-07.
- **Phase 60** — Existing Data Migration: idempotently migrate shared `qsos` data into `<username>_qsos`, report unresolved operators, and preserve rowHash/ADIF extras. Completed 2026-06-07.
- **Phase 61** — QSO CRUD and Import/Export Routing: refactor REST/UI/service/ADIF/API-token/UDP write paths to use authenticated username-derived collections. Completed 2026-06-08.
- **Phase 62** — Cross-Feature Integration and Verification: stats, admin clear-log, live feed/SSE, backup/restore, isolation tests, and compatibility verification. Completed 2026-06-08.

### v3.2 Phase Structure

- **Phase 63** — ACLog Full-Record Import via INCLUDEALL: request/parse full ACLog records after saved-QSO events, preserve non-empty fields, map Other fields, and keep current live-update behavior as fallback. Completed 2026-06-09.

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

- Run `/gsd-plan-phase 64` to create the executable plan.

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

Last session: 2026-06-12 (Phase 64 UI-SPEC approved)
Stopped at: Phase 64 ready for PLAN.md; `gsd-sdk` is not on PATH, so state bookkeeping was applied manually
Resume file: `.planning/phases/64-aclog-bridge-manual-sync/64-UI-SPEC.md`
Next: run `/gsd-plan-phase 64`
