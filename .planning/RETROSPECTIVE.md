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

### Cumulative Quality

| Milestone | Tests Added | Zero New Prod Deps |
|-----------|-------------|-------------------|
| v2.5 | 0 new tests | ✓ (no new dependencies) |
| v2.4 | 5 integration tests | ✓ (Web Audio native browser) |
| v2.3 | 7 integration tests | ✓ (Chart.js CDN only) |
| v2.2 | 12 integration tests | ✓ |
| v2.1 | 8 integration tests | ✓ |

### Top Lessons (Verified Across Milestones)

1. **Backend-first two-phase split works well for data+UI features.** v2.3 proved this: Phase 42 defined the exact context dict shape, which made Phase 43 a nearly mechanical implementation.
2. **Jinja2 template bugs surface at render time, not compile time.** Both WR-01 (stats block/if nesting) and earlier template issues required a live render to catch — invest in a quick browser smoke-test step.
3. **In-memory caches (token_cache, operator_cache, now chart data via JSON) eliminate per-request DB round-trips for read-heavy UI endpoints.**
4. **Pre-loading arch decisions into STATE.md before execution eliminates mid-execution surprises.** v2.4 had zero blocked decisions during execution — all tricky patterns (strong reference, message-first indicator, hidden-input checkbox, badge DOM placement) were decided at research/context time.
