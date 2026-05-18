---
gsd_state_version: 1.0
milestone: v1.7
milestone_name: API Token Auth
status: executing
stopped_at: Phase 56 context gathered
last_updated: "2026-05-18T16:01:10.871Z"
last_activity: 2026-05-18
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 6
  completed_plans: 6
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-06)

**Core value:** Multiple operators can log QSOs simultaneously under their own callsigns without conflicts or data loss
**Current focus:** Phase 56 — documentation

## Current Position

Phase: 56
Plan: Not started
Status: Executing Phase 56
Last activity: 2026-05-18

```
v2.8 Progress: [                    ] 0% (0/3 phases)
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
| v2.8 | 54–56 | TBD |

## Accumulated Context

### Roadmap Evolution

- v2.6 milestone complete: llms.txt Support (Phase 51, 2026-04-25)
- v2.7 milestone complete: UTC Date/Time Entry (Phases 52–53, 2026-05-02)
- v2.8 milestone started: Clear Log (2026-05-06)
- v2.8 roadmap created: Phases 54–56 defined (2026-05-06)

### v2.8 Phase Structure

- **Phase 54** — Operator Clear Log: `clear_operator_log()` service function, `POST /log/profile/clear` HTMX route, Danger Zone section + password-confirmation modal in `templates/log/profile.html`; covers CLR-01–05
- **Phase 55** — Admin Clear Operator Log: `POST /admin/ui/users/<username>/clear-log` HTMX route, "Clear log" button + modal in `templates/admin/users.html`; covers ACLR-01–05
- **Phase 56** — Documentation: `docs/getting-started.md` + `docs/admin.md` updated, `uv run mkdocs build --strict`, `site/` committed; covers DOC-01–03

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

None.

## Deferred Items

Items acknowledged and deferred at v2.8 milestone close on 2026-05-18:

| Category | Item | Status |
|----------|------|--------|
| human-uat | 54-operator-clear-log/54-HUMAN-UAT.md | partial — visual-only browser checks (card styling order, HTMX innerHTML swap, HTMX outerHTML swap). Behavioral coverage duplicated by `tests/test_clear_log.py` (6 async tests, all green). |
| human-uat | 55-admin-clear-operator-log/55-HUMAN-UAT.md | partial — visual-only browser checks (modal backdrop legibility in dark mode, HTMX cancel-swap behavior). Behavioral coverage duplicated by `tests/test_admin_clear_log.py` (6 async tests, all green). |

## Session Continuity

Last session: 2026-05-10T05:54:35.629Z
Stopped at: Phase 56 context gathered
Next: `/gsd-plan-phase 54`
