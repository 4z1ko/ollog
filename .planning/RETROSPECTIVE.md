# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

---

## Milestone: v2.3 — Operator Statistics

**Shipped:** 2026-04-16
**Phases:** 2 (42–43) | **Plans:** 2 | **Sessions:** 1

### What Was Built

- `app/stats/service.py` — `get_stats()` with 3 JWT-isolated MongoDB aggregation pipelines (band, mode, CALL-level); Python-side DXCC rollup; top-8 entity truncation with "Other" guard; empty-state shape
- `app/stats/router.py` — `GET /log/stats` with cookie-auth enforcement, registered in main.py with `include_in_schema=False`
- `templates/log/stats.html` — Full Chart.js 4.5.1 stats page: 3 pie charts, responsive 2-col grid, dark/light palette switching via `themechange` CustomEvent, empty-state card, `| tojson` XSS-safe data injection
- `{% block extra_scripts %}` extension point in `base.html` — reusable pattern for any future page-specific CDN scripts
- `themechange` CustomEvent broadcast pattern in `toggleTheme()` — zero-coupling chart palette re-init
- 7 integration tests: operator isolation, soft-delete exclusion, DXCC resolution, empty-state, auth enforcement

### What Worked

- **Parallel research → plan → execute pipeline**: The existing phase workflow (research → context → plan → execute) fit a UI-heavy stats feature cleanly — no process friction
- **Motor EOL discovery**: Research surfaced that Motor was EOL'd May 2025 before execution began; `get_pymongo_collection()` was known ahead of time, avoiding mid-execution surprise
- **`themechange` CustomEvent pattern**: Broadcast pattern completely decoupled the stats chart from `toggleTheme()` — clean, zero-friction, and reusable for any future chart page
- **`| tojson` safety discipline**: Entity names (with commas, quotes, apostrophes) exercised the XSS guard immediately; the discipline is now established as a pattern

### What Was Inefficient

- **VALIDATION.md not updated post-execution (Phase 42)**: The draft VALIDATION.md was created at plan time and never updated after execution. This caused stale `nyquist_compliant: false` artifact and required a separate validation-fix phase (43 Nyquist fix). A post-execution VALIDATION.md update should be part of the standard execution checklist.
- **WR-01 Jinja2 block/if nesting bug**: The `{% if total_qsos > 0 %}{% block extra_scripts %}` ordering was wrong initially — Jinja2 evaluates block declarations at parse time, not render time. Required a separate fix commit. This is a non-obvious Jinja2 behavior; should be documented in CLAUDE.md as a build rule.

### Patterns Established

- **`{% block extra_scripts %}`**: Child templates override `{% block extra_scripts %}` in `base.html` for page-specific scripts loaded before `</body>` — avoids penalizing all pages with heavy CDN bundles
- **`themechange` CustomEvent**: `window.addEventListener('themechange', ...)` pattern for any future chart or animation needing theme awareness — zero coupling to `toggleTheme()`
- **`Chart.getChart(canvas)?.destroy()` stale-canvas guard**: Required before every `new Chart()` call — bfcache restores and theme re-inits both hit this path
- **`get_pymongo_collection()` for Beanie raw aggregation**: The correct accessor post-Motor-EOL (May 2025); `get_motor_collection()` no longer exists

### Key Lessons

1. **Update VALIDATION.md after execution, not just at plan time.** A draft VALIDATION.md created at plan time with `nyquist_compliant: false` becomes a stale artifact if not updated after the phase passes. The update should happen atomically with the phase completion commit.
2. **`{% block %}` inside `{% if %}` in Jinja2 is safe; `{% if %}` inside `{% block %}` is required for conditional rendering.** The conditional must wrap the block override, not be inside it — Jinja2 resolves block declarations at parse time.
3. **Research Beanie's raw collection accessor before writing aggregation code.** The `get_motor_collection()` → `get_pymongo_collection()` rename is not obvious from Beanie docs; checking `app/feed/manager.py` (the existing aggregation pattern) would have surfaced this at research time.

### Cost Observations

- Model: claude-sonnet-4-6 throughout
- Sessions: 1 (Phase 42) + 1 (Phase 43) = 2 execution sessions
- Notable: Phase 43 executed in 2 minutes — the backend data pipeline (Phase 42) completely eliminated frontend ambiguity; the UI phase was essentially copy-paste-and-wire

---

## Milestone: v2.4 — Live Log & Sound Alerts

**Shipped:** 2026-04-20
**Phases:** 4 (44–47) | **Plans:** 5 | **Sessions:** ~4

### What Was Built

- `app/feed/manager.py` — `try/except Exception` in `watch_qsos` inner loop; watcher continues on any per-event failure
- `app/main.py` — `app.state.watcher_task` strong reference; GC-safe task lifetime for Python 3.12+
- `templates/log/log.html` — `eventsFlowing` sentinel state machine (LIVE indicator message-first); Web Audio IIFE (440 Hz sine tone, 120ms, lazy `AudioContext` on first user gesture, webkitAudioContext fallback); `#new-qso-badge` sibling div with counter, click-dismiss, and htmx:afterSettle auto-dismiss
- `app/auth/models.py` + `app/auth/schemas.py` — `notify_sound: bool = False` on User model; no migration needed
- `app/qso/ui_router.py` — `log_view()` dependency swap from callsign string to full User object; `NOTIFY_SOUND` Jinja2 constant injection
- `tests/test_watcher.py` — 3 tests: exception isolation, strong reference, null-date handling
- `tests/test_log_view_notify_sound.py` — 2 tests: NOTIFY_SOUND false/true injection

### What Worked

- **Research-driven architecture decisions**: All v2.4 arch decisions (strong reference, message-first state machine, hidden-input checkbox pattern, badge sibling placement) were captured in STATE.md before any code was written — zero mid-execution surprises
- **Plan 44-02 auto-detection**: The executor detected that phases 46 and 47 had already implemented the LIVE indicator fix before plan 44-02 ran; correctly verified acceptance criteria without overwriting existing work
- **Web Audio zero-dependency**: Native browser Web Audio API eliminated any npm install friction; the tone synthesis (OscillatorNode + GainNode + ramp envelope) is ~20 lines and fully self-contained
- **badge DOM sibling pattern**: Placing `#new-qso-badge` as a sibling of `#log-table` (not inside it) is a generalizable pattern for any persistent UI element that coexists with HTMX SSE swap targets

### What Was Inefficient

- **Phase execution order confusion**: Phases 45, 46, 47 were executed before phase 44-02 was formally completed, causing the plan to find its target already implemented. The execution order was correct for the code but required careful deviation handling in the SUMMARY.
- **REQUIREMENTS.md traceability not updated post-execution**: All 9 requirements validated in PROJECT.md but traceability table left as "Pending" throughout the milestone. Required manual update at archival time.
- **STATE.md front matter stale**: Front matter still showed `milestone: v1.7` throughout v2.4 execution — only fixed at milestone close.

### Patterns Established

- **`app.state.<task>` for all long-running asyncio tasks**: Any task that must survive for the app lifetime should be stored on `app.state`, not in a local variable. Prevents Python 3.12+ GC reclamation.
- **Message-first SSE indicator**: Set indicator green only on first confirmed event message, not on connection open. Generic pattern for any SSE health indicator.
- **Hidden input before checkbox**: `<input type="hidden" name="field" value="false">` before `<input type="checkbox" name="field" value="true">` — ensures unchecked checkbox sends `false` instead of nothing. Required any time a checkbox submits to a server-side form handler.
- **SSE-safe persistent UI elements**: Any element that must survive HTMX SSE innerHTML swaps must be a DOM sibling of the swap target, never a child.
- **`classList.remove('hidden')` before `classList.add('flex')`**: Tailwind `hidden` compiles to `display: none !important`; always remove it before adding a display class.

### Key Lessons

1. **Strong references are required for any asyncio task that must outlive a function scope.** Local variables are GC candidates in Python 3.12+. `app.state` is the correct lifetime anchor for app-scoped tasks.
2. **SSE event detail shape matters.** `htmx:sseMessage` `e.detail` is the raw `MessageEvent`; `e.detail.type` is the SSE event type string. `e.target` gives the listening element. Confirmed and saved to memory.
3. **Update REQUIREMENTS.md traceability table at phase completion, not milestone close.** Leaving all rows as "Pending" until archival requires manual bulk-update and creates misleading stale state during the milestone.

### Cost Observations

- Model: claude-sonnet-4-6 throughout
- Sessions: 4 execution sessions across 4 phases (some phases had prior-session pre-commits)
- Notable: Phase 44-01 code was already committed from a prior session — the execution session only produced SUMMARY.md; demonstrates value of atomic commits at plan completion

---

## Milestone: v2.5 — QSO Sorting & Entry Timestamp

**Shipped:** 2026-04-23
**Phases:** 3 (48–50) | **Plans:** 3 | **Sessions:** ~3

### What Was Built

- `app/qso/models.py` — `_created_at: datetime` field with `default_factory=lambda: datetime.now(timezone.utc)`; all 4 insert paths (REST, UDP, ADIF import, admin) stamped automatically without touching each path individually; compound index on `(_operator, _created_at)`; protected field stripping ensures `_created_at` cannot be overwritten via API
- `app/qso/service.py` — `_ALLOWED_SORT_FIELDS` allowlist (CALL, BAND, MODE, qso_date_utc, _created_at); view dict enrichment adds `_created_at` ISO string for template; SSE sentinel extended to `-_created_at` (prevents auto-refresh when user is browsing by entry timestamp)
- `templates/log/log_table.html` — Sort UI: MODE clickable header (ascending-first toggle); clock icon link in DATE header for `_created_at` (descending-first); hollow/solid chevron indicator system across all 5 sortable elements (DATE text, clock, CALL, BAND, MODE)
- `static/css/output.css` — rebuilt with `dark:opacity-25` compiled for inactive chevron indicators

### What Worked

- **`default_factory` on model field**: Stamping `_created_at` at the Beanie model level covered all 4 insert paths (REST, UDP, ADIF import, admin) without modifying each individually — confirmed as the right pattern over service-layer stamping
- **Backend-first phase ordering**: Phases 48+49 defined exact field names, allowlist keys, and API contract before Phase 50's UI work began — zero blocked decisions during template edits
- **Hollow/solid chevron system**: `opacity-30 dark:opacity-25` inactive indicators with solid directional chevrons on active column is a clean, composable pattern applicable to any sortable table

### What Was Inefficient

- **STATE.md front matter stale `milestone: v1.7`**: Same recurring issue from v2.4 — front matter was never updated mid-milestone; only fixed at close. Needs to be updated at milestone start, not end.
- **`gsd-tools milestone complete` bad MILESTONES.md output**: CLI extracted garbage accomplishment text ("One-liner:", "[Rule 1 - Bug]...") from SUMMARY.md instead of meaningful entries — required full manual rewrite of MILESTONES.md v2.5 entry.
- **`audit-open` CLI crash**: `gsd-tools audit-open` threw `ReferenceError: output is not defined` at milestone open step — worked around by manual artifact assessment. Tool bug needs fixing upstream.
- **`roadmap analyze` silent failure**: Returned `phases: [], phase_count: 0` — could not parse this project's ROADMAP.md format. Manual ROADMAP.md read was required as fallback.

### Patterns Established

- **Multi-link `<th>` with `inline-flex` wrapper**: When a single column header needs multiple sort targets (e.g., DATE text + clock icon), wrap both `<a>` elements in `<span class="inline-flex items-center gap-2">` inside the `<th>`. Established for any future multi-sort column.
- **MODE ascending-first sort toggle**: `{% if sort == 'MODE' %}-MODE{% else %}MODE{% endif %}` — MODE sorts ascending on first click (A→Z), then descending. All other fields default descending-first. Documented in STATE.md key decisions.
- **`_ALLOWED_SORT_FIELDS` allowlist pattern**: Allowlist in service layer prevents arbitrary MongoDB field injection via sort parameter. FREQ and RST intentionally excluded (non-meaningful sort axes).

### Key Lessons

1. **Use `default_factory` on the model field for auto-stamped internal fields, not service-layer stamping.** Model-level defaults apply to every insert path (REST, UDP, ADIF import, admin CRUD) without requiring each path to be updated. Service-layer stamping only covers paths that explicitly call the service.
2. **`dark:opacity-25` compiles to `dark\:opacity-25` in CSS (standard CSS colon escape).** `grep -q "dark:opacity-25" output.css` will exit 1 even when the class is present. Use `grep -q 'dark\\:opacity-25'` or verify with `npm run verify` instead.
3. **gsd-tools `audit-open` and `roadmap analyze` are unreliable for this project.** Both crash or return empty results — the ROADMAP.md format is not parsed correctly. Always fall back to reading files directly; do not block milestone progression on CLI tool output.

### Cost Observations

- Model: claude-sonnet-4-6 throughout
- Sessions: ~3 execution sessions across 3 phases
- Notable: Phase 50 was `autonomous: false` with a `checkpoint:human-verify` task — the only human browser-verification gate in the milestone; all other phases ran fully autonomously

---

## Milestone: v2.7 — UTC Date/Time Entry

**Shipped:** 2026-05-02
**Phases:** 2 (52–53) | **Plans:** 3 | **Sessions:** ~3

### What Was Built

- `app/main.py` — `normalize_time_on()` idempotent startup migration: anchored regex `^\d{4}$` filter + aggregation pipeline `$concat ["00"]`; called after `backfill_created_at()` in lifespan; INFO log on both outcomes (updated / already done)
- `tests/test_migration.py` — 5 tests: DB-01 padding, idempotency, 6-digit skip (integration); DB-02 HHMM/HHMMSS parse acceptance (unit)
- `templates/log/form.html` — padlock-wrapped QSO_DATE/TIME_ON inputs (`readonly` not `disabled`; Heroicons 24px SVG swap); `initDateTime()` with `getUTC*` clock; `htmx:beforeRequest` HHMM→HHMM00 normalization; range-checking validation regex; `localStorage`-backed reset-mode toggle; Clear button `setTimeout(0)` defer pattern; 166 lines of JS added

### What Worked

- **Backend-first two-phase split (again)**: Phase 52 locked the DB contract (HHMM vs HHMMSS precision) before any frontend work began. Phase 53 had zero ambiguity about what format to send.
- **`readonly` vs `disabled` research upfront**: The CONTEXT.md explicitly documented the pitfall before execution — `disabled` silently drops field from POST body. Zero mid-execution surprises.
- **TDD gate compliance**: Phase 52 executed clean RED→GREEN cycle; all 5 tests existed before implementation, all passed after.
- **HTMX scope clarity**: The key insight that `hx-target="#qso-result"` points at a sibling div — so form DOM, event listeners, and `setInterval` all survive every submit — was captured in research before planning. No post-submit re-initialization was needed.

### What Was Inefficient

- **REQUIREMENTS.md traceability never updated**: All 14 requirements showed "Pending" throughout the entire milestone — only updated at archive time. This is the same recurring issue from v2.4 and v2.5. The VERIFICATION.md is the correct authority, but the traceability table should match.
- **Two gap fixes required post-verification**: The verifier found that `initDateTime()` did not reset padlock icons to closed state on the reset path (Gap 1) and that the TIME_ON regex accepted impossible values like `9999` (Gap 2). Both were simple fixes (~5 lines each) but required a second verification pass.
- **`aria-label` inversion shipped as tech debt**: The padlock buttons describe current state ("Lock field") instead of the action they will take ("Unlock field"). This was caught by the integration checker but accepted as tech debt rather than fixed before close.

### Patterns Established

- **`readonly` on locked form fields (not `disabled`)**: `readonly` fields submit their value in the POST body; `disabled` fields are silently excluded. Critical whenever a field should be pre-filled by JS and also included in form submission.
- **`getUTC*` discipline for live clocks**: All UTC accessors must use `Date.prototype.getUTCFullYear/Month/Date/Hours/Minutes/Seconds` — never the local-time equivalents. Checked programmatically with `grep -cE '\.getHours\(\)|\.getMinutes\(\)'`.
- **`setTimeout(fn, 0)` deferral for form reset**: `form.reset()` fires synchronously before any post-reset listener can repopulate fields. `setTimeout(0)` yields control to the browser, allowing `form.reset()` to complete before `initDateTime()` re-populates fields.
- **Idempotent startup migration pattern**: `anchored regex filter` + `aggregation pipeline $set` is the established pattern for MongoDB field normalization at startup. Previous: `backfill_created_at()` (ObjectId→datetime). Now: `normalize_time_on()` (HHMM→HHMM00).

### Key Lessons

1. **Update REQUIREMENTS.md traceability at phase completion, not milestone close.** The recurring lesson: leaving all rows as "Pending" until archival creates misleading state. The VERIFICATION.md covers this, but the traceability table should stay in sync.
2. **Range-checking regexes are worth the extra complexity for time inputs.** A simple `/^\d{6}$/` accepted `999900` (impossible time). The range-checking regex `/^([01]\d|2[0-3])([0-5]\d)([0-5]\d)$/` rejects it. For ADIF time fields specifically, range validation catches `9999→999900` which digit-only patterns miss.
3. **`initDateTime()` as the canonical reset entrypoint is load-bearing.** Any code path that needs to restore locked live-clock state (page load, post-submit reset, Clear button) should call `initDateTime()` — and `initDateTime()` must fully restore icons, aria-labels, readOnly, locked styling, and the interval. Partial resets (only some of these) create inconsistent UI state.

### Cost Observations

- Model: claude-sonnet-4-6 throughout
- Sessions: ~3 execution sessions (Phase 52 research/plan/execute + Phase 53 plan 01 + Phase 53 plan 02 + verification)
- Notable: Phase 52 executed in ~15 min (TDD pipeline), Phase 53 plan 01 in ~15 min (HTML-only), Phase 53 plan 02 in ~20 min (JS-only) — clean phase boundary enabled parallel mental tracks

---

## Milestone: v2.8 — Clear Log

**Shipped:** 2026-05-18
**Phases:** 3 (54–56) | **Plans:** 6 | **Commits:** 49 | **Source lines:** +685 / −1

### What Was Built

- `app/qso/service.py` — `clear_operator_log(operator: str) -> int` async service; single Beanie `delete_many({_operator, _deleted: False})` filter centralized for both flows
- `app/qso/ui_router.py` — `GET /log/profile/clear/modal` + `POST /log/profile/clear` operator routes (cookie auth, password gate against operator's own hash, HTMX outerHTML swap)
- `app/admin/ui_router.py` — 3 admin routes (modal GET, confirm POST, cancel GET) all under `require_admin_cookie`; password verified against `current_user.hashed_password` (admin's OWN, NOT `target_user.hashed_password`)
- `templates/log/{clear_log_modal,clear_log_success}.html` + `templates/admin/{clear_log_modal,clear_log_success}.html` — 4 HTMX fragments with distinct outer IDs (`#clear-log-modal` vs `#admin-clear-log-modal`)
- `templates/log/profile.html` Danger Zone card + `templates/admin/users_table.html` per-row "Clear log" button + `templates/admin/users.html` modal target div
- `mkdocs.yml` admonition extension; `docs/operator-guide/profile.md` Danger Zone section; `docs/admin-guide/account-management.md` Clear Operator Log section; rebuilt `site/`
- `tests/test_clear_log.py` (6 async tests) + `tests/test_admin_clear_log.py` (6 async tests) — full integration coverage of CLR-01..05 and ACLR-01..05

### What Worked

- **Single shared service across two phases.** Phase 54 owned `clear_operator_log()`; Phase 55 consumed it with one import line. The integration checker verified zero logic duplication and a single Beanie filter — exactly the design payoff of locking the service contract first.
- **Distinct modal target IDs caught proactively.** `#clear-log-modal` (operator) vs `#admin-clear-log-modal` (admin) was decided in PATTERNS.md before either template was written. No DOM-collision bug to find later.
- **D-04 stale-path resolution + override mechanism.** ROADMAP success criteria referenced `docs/getting-started.md` and `docs/admin.md` (legacy stubs excluded from MkDocs nav). Phase 56 CONTEXT.md decision D-04 resolved these to actual paths upfront; verification used the override system rather than fighting the spec drift.
- **Admin password semantics gate.** Plan + research explicitly flagged "verify admin's OWN password, NOT target_user's" before any admin route was wired. Integration check confirmed zero references to `target_user.hashed_password` in any `verify_password` call site.

### What Was Inefficient

- **Three retroactive validation audits required at milestone close.** All 3 phases shipped with `nyquist_compliant: false` in their VALIDATION.md frontmatter despite passing integration tests existing during execution. `/gsd-validate-phase 54`, `55`, `56` were each mechanical sign-off passes — no new test code needed. Should have been flipped during execute-phase, not at milestone audit.
- **Phase 54 VALIDATION.md referenced `tests/test_qso.py::test_clear_operator_log`, but actual tests landed in `tests/test_clear_log.py`.** Drafted test paths drifted from the executed file location. Validation audit had to remap each row to the real test name.
- **REQUIREMENTS.md traceability stayed `[ ]` for all 13 rows through the entire milestone.** Same pattern as v2.4/v2.5/v2.7 — the traceability table is updated at archive time, not phase completion. Recurring debt.
- **Two `Edit`-tool retry loops on the read-before-edit hook.** Each turn-fresh edit triggered a "READ-BEFORE-EDIT" reminder despite the file having been read earlier in the same turn. Cost ~3 extra round-trips per multi-edit pass on STATE.md / VALIDATION.md / PROJECT.md.

### Patterns Established

- **Single-service-two-callers for destructive ops with different auth contexts.** Operator + admin clear-log share `clear_operator_log()`; password verification is the caller's responsibility. Pattern: put the data-mutation in the service, the identity check in the route. Apply to any future "admin can do X on behalf of operator" feature.
- **Modal target ID prefix discipline.** `#clear-log-modal` vs `#admin-clear-log-modal` — when the same UI pattern serves operator and admin sub-apps, prefix admin DOM IDs with `admin-` to prevent collision if pages are ever co-rendered.
- **`!!! danger "This cannot be undone"` admonition for destructive UI documentation.** Established convention: every destructive UI surface gets a permanence callout in the docs site using the MkDocs Material `!!! danger` block. Requires `markdown_extensions: [admonition]` in `mkdocs.yml` (silent failure mode without it).
- **Override + decision artifact for stale ROADMAP paths.** When a phase's success criteria reference paths that no longer exist (legacy stubs excluded from nav), use a CONTEXT.md decision (D-04 pattern) to declare the resolved actual paths up front, then claim verification overrides rather than failing on the literal path mismatch.

### Key Lessons

1. **Flip `nyquist_compliant: true` at end of execute-phase, not at milestone close.** Phase verification confirms tests pass; validation audit should be triggered (or skipped as compliant) immediately, not deferred. Three retroactive audits per milestone is debt that piles up linearly with milestone size.
2. **VALIDATION.md test paths drift if drafted before execute-phase.** When `gsd-plan-phase` outputs draft test paths (`tests/test_qso.py::test_X`), they're guesses. The actual test file is decided during execute-phase. Either re-anchor VALIDATION.md at end of execute, or treat draft paths as suggestions and let the validation audit be the source of truth.
3. **Service contract is the cross-phase boundary; the caller's auth context is per-phase.** Phase 54 shipped a service with one input (`operator: str`) and one output (`int`). Phase 55 didn't extend, wrap, or modify it — just gated the same call behind a different auth dependency. Future cross-phase reuse should follow this exact shape: one service signature, multiple callers, each with their own auth.
4. **Documentation phases need a build verification, not just content checks.** Phase 56 split a build (`mkdocs --strict`) AND a render check (`grep class="admonition danger" site/...`) into separate tasks. Without the render check, the silent-failure mode of missing `markdown_extensions: [admonition]` would have shipped raw `!!! danger` text. Build success ≠ content rendered as intended.

### Cost Observations

- Model: claude-sonnet-4-6 throughout execution; claude-opus-4-7 (1M) for retroactive validation audits, milestone audit, and close
- Sessions: ~5 (Phase 54, Phase 55, Phase 56, validation backfill, milestone close)
- Notable: ~13 days elapsed but only ~5 active sessions — most of the calendar gap was between Phase 56 completion (2026-05-10) and milestone close (2026-05-18). The actual implementation work was compressed.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 6 | 19 | Initial multi-phase foundation build |
| v1.7 | 4 | 4 | First milestone with token auth + UDP integration |
| v1.9 | 5 | 8 | UI redesign milestone — CSS component system established |
| v2.2 | 1 | 2 | Single-phase milestone — narrow well-scoped feature |
| v2.3 | 2 | 2 | Two-phase data+UI split — backend first, frontend second |
| v2.4 | 4 | 5 | Hardening + new UX features; arch decisions pre-loaded in STATE.md |
| v2.5 | 3 | 3 | Model-level `default_factory` stamp + allowlist sort + 5-column sort UI |
| v2.6 | 1 | 3 | Minimal single-phase content milestone; pure routing + static files, zero new deps |
| v2.7 | 2 | 3 | Backend-first migration (Phase 52) + frontend-only JS (Phase 53); two-phase split worked cleanly |
| v2.8 | 3 | 6 | Service-first three-phase split (Phase 54 service + ops UI, Phase 55 admin UI reusing service, Phase 56 docs); single shared `clear_operator_log()` consumed by both auth contexts |

### Cumulative Quality

| Milestone | Tests Added | Zero New Prod Deps |
|-----------|-------------|-------------------|
| v2.8 | 12 new tests (test_clear_log.py + test_admin_clear_log.py) | ✓ (no new dependencies) |
| v2.7 | 5 new tests (test_migration.py) | ✓ (no new dependencies) |
| v2.6 | 3 new tests (test_llms.py) | ✓ (no new dependencies) |
| v2.5 | 0 new tests | ✓ (no new dependencies) |
| v2.4 | 5 integration tests | ✓ (Web Audio native browser) |
| v2.3 | 7 integration tests | ✓ (Chart.js CDN only) |
| v2.2 | 12 integration tests | ✓ |
| v2.1 | 8 integration tests | ✓ |

### Top Lessons (Verified Across Milestones)

1. **Backend-first two-phase split works well for data+UI features.** v2.3, v2.5, and v2.7 all proved this: defining the exact field/format contract in Phase N makes Phase N+1 a nearly mechanical implementation.
2. **Jinja2 template bugs surface at render time, not compile time.** Both WR-01 (stats block/if nesting) and earlier template issues required a live render to catch — invest in a quick browser smoke-test step.
3. **In-memory caches (token_cache, operator_cache, now chart data via JSON) eliminate per-request DB round-trips for read-heavy UI endpoints.**
4. **Pre-loading arch decisions into STATE.md before execution eliminates mid-execution surprises.** v2.4 and v2.7 had zero blocked decisions during execution — all tricky patterns were decided at research/context time.
5. **Update REQUIREMENTS.md traceability at phase completion, not milestone close.** This lesson has appeared in v2.4, v2.5, and v2.7 retrospectives — it is a recurring pattern that has not been fixed. Consider adding it to the execution checklist.
