# Project Research Summary

**Project:** ollog — v1.6 Live Log Table
**Domain:** HTMX SSE-triggered auto-refresh for operator-scoped paginated QSO log table
**Researched:** 2026-04-08
**Confidence:** HIGH

## Executive Summary

This milestone adds live auto-refresh to the `/log/view` paginated QSO table so operators see new QSOs appear without a manual page reload. The stack to implement this already exists in full: HTMX 2.0.4, htmx-ext-sse 2.2.4, a live `/feed/station` SSE endpoint broadcasting `new_qso` events, and a `/log/view` endpoint that already returns HTMX partials on `HX-Request`. No new dependencies are required. The correct implementation attaches `hx-ext="sse"`, `sse-connect="/feed/station"`, `hx-get="/log/view"`, and `hx-trigger="sse:new_qso [condition]"` to the stable `#log-table` container div in `log.html`. When a `new_qso` SSE event arrives and the guard condition passes, HTMX fires a GET to `/log/view`, and the response replaces `#log-table`'s innerHTML with a freshly server-rendered, operator-scoped, paginated partial.

The key architectural decision — resolved across STACK and ARCHITECTURE research — is to use **SSE-triggered re-fetch** rather than polling or direct SSE row injection. Direct row injection via `sse-swap afterbegin` is wrong for this view: it bypasses operator scoping, ignores active filters, injects rows from the wrong template (`feed_row.html` rather than `qso_row.html`), and produces stale pagination counts. Polling was the ARCHITECTURE researcher's fallback recommendation, citing concern that SSE attributes would be destroyed on navigation. That concern is eliminated by a structural insight: `#log-table` is the HTMX swap *target* — filter, sort, and pagination actions all replace its innerHTML but never the container div itself. SSE attributes on `#log-table` survive every navigation. This resolves the STACK/ARCHITECTURE divergence in favor of the SSE-triggered re-fetch.

The primary risks are operator isolation and the inline-edit interaction. The guard condition on `hx-trigger` prevents refresh when filters are active or on page > 1 — both correct UX behaviors. Inline edit rows must be protected from auto-refresh by a JS condition that checks for an `.editing` class before firing. JWT session expiry at 60 minutes is a silent failure mode that should be mitigated by raising `jwt_expire_minutes` to 480. No backend changes are required for the core feature.

---

## Key Findings

### Recommended Stack

No new dependencies. The existing stack handles everything:

**Core technologies:**
- **HTMX 2.0.4** — `hx-trigger="sse:new_qso [condition]"` is supported natively; conditional filter `[expression]` syntax confirmed in official docs
- **htmx-ext-sse 2.2.4** — already loaded in `base.html`; supports "SSE-triggered HTTP request" mode (`hx-trigger="sse:<name>"` fires a GET) distinct from "direct content swap" mode (`sse-swap="<name>"`); both modes available on the same connection
- **`/feed/station` SSE endpoint** — already exists; `watch_qsos()` MongoDB change stream already broadcasts `event="new_qso"` on every QSO insert; the SSE event is the trigger signal only — no data payload needed for re-fetch
- **`/log/view` partial endpoint** — already returns `log_table.html` fragment on `HX-Request`; operator isolation already enforced via JWT cookie; no backend changes required

**Critical version note:** `hx-trigger="sse:<event-name>"` is htmx-ext-sse 2.x syntax; incompatible with 1.x extension API.

### Expected Features

**Must have (table stakes):**
- Auto-refresh on page 1 with no active filters — new QSOs appear at the top without manual reload
- Operator scoping enforced via re-fetch — `/log/view` always filters by JWT callsign; no per-operator SSE queue needed
- Suspend auto-refresh on page > 1 — historical browsing must not be disrupted
- Suspend auto-refresh when any filter is active — filter contract must not be violated; new rows may not match the active filter
- "Live" connection indicator — small dot showing SSE connection status via `htmx:sseOpen` / `htmx:sseClose` events
- Inline edit rows protected from auto-refresh — unsaved edits must not be silently destroyed

**Should have (differentiators, post-v1.6):**
- Animated row highlight on new row appearing — brief CSS fade-in to identify the new row
- "N new QSOs" notification banner when filters are active — passive count of suppressed events with a clear-filters link

**Defer (v2+):**
- Per-operator SSE queues in `ConnectionManager` — cleaner isolation but unnecessary when re-fetch handles operator scoping via JWT
- Tombstone row for deleted QSOs — high complexity, rare case
- MongoDB change stream resume token hardening — correctness improvement for high-volume deployments

### Architecture Approach

The `#log-table` div in `log.html` is the SSE anchor and HTMX trigger host. It carries `hx-ext="sse"`, `sse-connect="/feed/station"`, `hx-get="/log/view"`, `hx-trigger="sse:new_qso [condition]"`, `hx-target="#log-table"`, and `hx-swap="innerHTML"`. This div is never replaced by any HTMX swap — all filter, sort, and pagination actions target its innerHTML, leaving the container itself (and its SSE connection) intact. Inside `log_table.html`, the server conditionally renders `<span id="auto-refresh-ok" hidden>` only when the view is at defaults (page=1, no filters, default sort). The JS expression in the trigger reads that marker to decide whether to fire.

**Major components:**
1. **`#log-table` div (`log.html`)** — SSE anchor and HTMX trigger host; stable across all inner swaps; never replaced by any HTMX action
2. **`log_table.html` partial** — server-rendered fragment returned by `/log/view`; includes conditional `#auto-refresh-ok` marker; replaces `#log-table` innerHTML on every navigation and on every SSE-triggered re-fetch
3. **`/feed/station` SSE endpoint** — existing; `new_qso` event is the trigger signal; already deployed and broadcasting
4. **`/log/view` route** — existing; handles HTMX partial response; enforces operator isolation via JWT; no changes required

### Critical Pitfalls

1. **SSE anchor inside the swap target** — if `hx-ext="sse"` is placed inside `log_table.html` (the swapped content), every pagination click destroys the SSE parent element and silently drops the connection. Prevention: `hx-ext="sse"` must live on `#log-table` itself — the target div, not its innerHTML. This is the structural insight that resolves the STACK/ARCHITECTURE divergence.

2. **Auto-refresh firing with active filters or on page > 1** — would reset the user to a re-fetched page-1 view unexpectedly. Prevention: the `#auto-refresh-ok` hidden marker is only server-rendered at defaults; the JS trigger condition gates the re-fetch.

3. **Inline edit row destroyed by auto-refresh** — `hx-swap="innerHTML"` on `#log-table` replaces the entire table including any open edit row. Prevention: add `.editing` class to `#log-table` when an edit row is open; condition the trigger to also check `!document.querySelector('#log-table.editing')`.

4. **Wrong-operator rows if direct SSE row injection is used** — `/feed/station` broadcasts all operators' inserts. The re-fetch approach sidesteps this entirely: `/log/view` enforces operator isolation via JWT on every re-fetch request. This is one reason the re-fetch approach is superior to direct row injection.

5. **JWT session expiry mid-SSE** — the SSE connection authenticates at connection time only. After 60 minutes the JWT expires; the next regular HTMX request (filter, pagination, QSO submit) gets a 401 and redirects to login while the SSE feed appears active. Prevention: raise `jwt_expire_minutes` to 480 in config — a single environment variable change.

---

## Implications for Roadmap

This milestone fits cleanly into two implementation plans with no backend changes required.

### Plan 1: SSE-triggered table reload

**Rationale:** All infrastructure exists. This is pure template work — two files, no new files, no backend changes. The `#log-table` structural insight makes SSE anchor placement safe and straightforward.

**Delivers:** Auto-refresh on page 1 with no active filters; operator isolation via re-fetch (no extra logic required); accurate pagination counts on every refresh; "Live" indicator in the table header

**Template changes:**
- `templates/log/log.html` — add SSE and re-fetch attributes to `#log-table` div; add "Live" indicator element wired to `htmx:sseOpen` / `htmx:sseClose`
- `templates/log/log_table.html` — add server-conditional `<span id="auto-refresh-ok" hidden>` rendered only at page defaults

**Backend changes:** None

**Pitfalls addressed:**
- SSE anchor placement (Pitfall 4) — resolved by putting attributes on `#log-table`, not inside its innerHTML
- Wrong-operator rows (Pitfall 1) — eliminated by re-fetch pattern; JWT always scopes the response
- Auto-refresh on wrong state — resolved by `#auto-refresh-ok` server-side marker

**Research flag:** Standard patterns — no deeper research needed. Exact attribute syntax is confirmed at HIGH confidence.

---

### Plan 2: Inline edit guard and session hardening

**Rationale:** Auto-refresh and inline editing interact. A refresh that destroys an open edit form causes silent data loss — operators will distrust the feature immediately. Session expiry is a parallel one-line config fix that prevents confusing mid-session logouts.

**Delivers:** Auto-refresh suppressed while an edit row is open; JWT session duration appropriate for a logging session (8 hours)

**Changes:**
- Inline edit HTMX actions in `qso_row.html` — add/remove `.editing` class on `#log-table` using `hx-on` attributes or `htmx:beforeRequest` / `htmx:afterSettle` events when edit row opens and closes
- `hx-trigger` condition in `log.html` updated to include `!document.querySelector('#log-table.editing')`
- Config: `JWT_EXPIRE_MINUTES=480` in `.env`

**Pitfalls addressed:**
- Edit row destroyed by refresh (Pitfall 9)
- JWT expiry mid-session (Pitfall 8)

**Research flag:** Standard patterns — no research needed. The `.editing` mechanism depends on the existing edit flow in `qso_row.html` and should be confirmed at plan-writing time.

---

### Phase Ordering Rationale

- Plan 1 first because it delivers the core feature and is entirely self-contained; the SSE-triggered re-fetch has no side effects on existing flows
- Plan 2 is a guard layer — correctness work that ships in the same milestone but is logically separable for review
- The "N new QSOs" banner and animated row highlight are intentionally excluded from both plans; they are post-v1.6 polish and require additional state management (suppressed-event counter)
- MongoDB change stream resume token hardening is a separate infrastructure milestone; it does not block v1.6
- No `/gsd:research-phase` needed during planning — all implementation decisions are resolved by this research

### Research Flags

Phases with standard patterns (skip additional research):
- **Plan 1:** `hx-trigger="sse:<name>"` pattern is fully documented; exact attribute syntax confirmed at HIGH confidence in official docs and verified against the existing codebase station feed implementation
- **Plan 2:** Inline edit guard is a conditional expression addition; session config is a one-line change. The exact HTMX events to use for `.editing` class management should be confirmed by reading `qso_row.html` at plan-writing time — not a research question, a code reading task.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | `hx-trigger="sse:<name>"` syntax confirmed against htmx.org official docs and htmx-ext-sse 2.2.4 source; existing codebase patterns verified by direct inspection |
| Features | HIGH | Based on direct codebase inspection; UX reasoning is logical derivation from existing pagination/filter model; existing station feed demonstrates silent prepend is accepted UX for this user population |
| Architecture | HIGH | Divergence between STACK and ARCHITECTURE researchers resolved by structural insight; both researchers' concerns satisfied by same design; `#log-table` as stable SSE anchor is confirmed by reading the template structure |
| Pitfalls | HIGH | Derived from direct codebase reading; HTMX SSE extension behavior confirmed against official docs and GitHub source including `nodeReplaced` / `htmx:sseClose` event on element destruction |

**Overall confidence:** HIGH

### Gaps to Address

- **`.editing` class mechanism:** The inline edit flow must reliably add `.editing` to `#log-table` when an edit row is open and remove it on save/cancel. Confirm the exact HTMX event hooks available in `qso_row.html` at plan-writing time.

- **`show:no-change` scroll preservation in HTMX 2.0.4:** PITFALLS.md flags scroll-position reset on full table reload as a UX concern. The `show:no-change` modifier needs verification against HTMX 2.0.4 before including it in the implementation. If unsupported, the idiomorph morphing swap extension is the alternative — but it adds a new dependency and is out of scope for v1.6.

- **`hx-include` during SSE-triggered re-fetch:** Not needed for this design (the guard condition prevents re-fetch when filters are active, so the request correctly fires as a plain `/log/view` returning page-1 defaults). No gap in practice, but worth noting if the design ever changes to allow filtered refreshes.

---

## Researcher Divergence Note

STACK recommended `hx-trigger="sse:new_qso"` on `#log-table`. ARCHITECTURE recommended polling (`every 30s`), citing concern that SSE attributes on an element inside the swap target would be destroyed on navigation.

Both researchers were reading the same codebase. The divergence was a misread of the template structure. `#log-table` is the HTMX swap *target* — filter, sort, and pagination actions all do `hx-swap="innerHTML"` on `#log-table`, replacing only its content. The `#log-table` div itself is never replaced. SSE attributes placed on `#log-table` survive every navigation.

PITFALLS P4 ("SSE anchor inside swap target — connection silently drops") explicitly confirms this: the fix is to place `hx-ext="sse"` outside the swapped content. `#log-table` is outside its own innerHTML — it satisfies this requirement exactly. The reconciled design satisfies both researchers' structural concerns while avoiding polling's downsides (timer resets on filter submit, wasteful queries when nothing changed, filter param persistence complexity).

---

## Sources

### Primary (HIGH confidence)
- [HTMX hx-trigger Attribute](https://htmx.org/attributes/hx-trigger/) — `sse:<name>` trigger syntax; conditional filter `[expression]` syntax; `every Ns [condition]` pattern
- [htmx-ext-sse Extension](https://htmx.org/extensions/sse/) — `sse-connect`, `sse-swap`, `hx-trigger="sse:"` HTTP request mode vs direct swap mode distinction
- [htmx-ext-sse GitHub source](https://github.com/bigskysoftware/htmx/blob/master/www/content/extensions/sse.md) — `nodeReplaced` / `htmx:sseClose` event on element destruction; two-mode distinction confirmed
- [WHATWG SSE spec](https://html.spec.whatwg.org/multipage/server-sent-events.html) — EventSource failure on non-200; 401 permanently fails the connection with no retry
- Codebase direct inspection — `templates/log/form.html`, `templates/log/log.html`, `templates/log/log_table.html`, `app/feed/manager.py`, `app/feed/router.py`, `app/qso/ui_router.py`, `app/qso/service.py`, `app/config.py`, `app/auth/dependencies.py`

### Secondary (MEDIUM confidence)
- [Django Forum: Polling with active filters](https://forum.djangoproject.com/t/how-can-i-implement-polling-the-table-and-keep-the-filter-applied-to-it-django-filter-htmx/18465) — URL-baking approach for polling; `hx-include` not sufficient for filter persistence with polling
- [HTMX issue #1198](https://github.com/bigskysoftware/htmx/issues/1198) — `<tr>` DOM parsing constraints; `htmx.config.useTemplateFragments` for OOB swaps
- [htmx-ext-sse error handling issue #134](https://github.com/bigskysoftware/htmx-extensions/issues/134) — SSE connection close behavior on element replacement
- [Real-time Notification Streaming using SSE and HTMX (Medium)](https://medium.com/@soverignchriss/real-time-notification-streaming-using-sse-and-htmx-32798b5b2247) — confirms `hx-swap="afterbegin"` on SSE container for prepend

---

*Research completed: 2026-04-08*
*Ready for roadmap: yes*
