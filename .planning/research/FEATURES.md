# Feature Research

**Domain:** Ham radio QSO log view — live auto-refresh for paginated, filterable operator log table
**Researched:** 2026-04-08
**Confidence:** HIGH (based on direct codebase inspection; UX reasoning grounded in existing SSE/HTMX architecture)

---

## Context and Constraints

This research answers the question: what is the right feature set for auto-refreshing the paginated QSO log view at `/log/view`?

**What already exists:**

- `/log/view` — paginated log (50/page), filterable by call/band/mode/date range, sortable columns, HTMX partial swaps for filter/sort/page changes. Scoped to the current operator's QSOs only (`_operator` field).
- `form.html` station feed — SSE-connected `#station-feed` tbody that receives ALL operators' QSOs via `ConnectionManager.broadcast()`. No operator filtering. Rows prepend instantly.
- `ConnectionManager` + `watch_qsos()` — MongoDB change stream on the `qsos` collection, renders `feed_row.html`, broadcasts to every connected SSE queue. No per-operator queues exist.
- QSOs can arrive via web form, REST API, or UDP listener.

**The core tension:** The station feed model (broadcast everything, no filters) is simple and works for the "all operators, no pagination" case. The log view is the opposite: operator-scoped, paginated, filtered, sortable. These require different strategies.

---

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| New QSOs appear in log view without manual refresh | Core value of live logging — operator just logged a contact and expects to see it | MEDIUM | The log view currently has zero auto-refresh. A QSO logged via the web form appears in the feed but not in the log table. |
| Auto-refresh scoped to the current operator only | Log view already shows only the current operator's QSOs — live updates must match this contract | LOW | Filter on `_operator == callsign` in the SSE handler or polling query. Do not show other operators' QSOs here. |
| Auto-refresh only active on page 1 | Page 1 is the "most recent" view. Page 2+ is historical browsing — injecting rows there would corrupt the user's position in the log | LOW | Read the page query param; only connect SSE or poll when `page == 1`. |
| Auto-refresh suspended when filters are active | If the user is viewing "all FT8 on 20m", prepending a new CW contact on 40m would be wrong. The new row may not match the filter. | LOW | Read current filter state; disable auto-refresh if any filter param is non-empty. Show a static "Filters active — auto-refresh paused" note. |
| New row appears at the top of the table | QSOs are sorted newest-first by default (`-qso_date_utc`). New rows belong at the top. | LOW | HTMX `afterbegin` on the tbody, same as the existing station feed. |
| Auto-refresh does not disrupt rows being edited | Log view has inline edit rows. Prepending a new row while the user is editing a different row should not close the edit. | LOW | The prepend is `afterbegin` on tbody, not a full table replace. In-progress edits in mid-table rows are unaffected. |
| Visual indicator that auto-refresh is active/connected | Operator needs to know if live updates are working, especially since the listener may be silently disconnected | LOW | A small "Live" badge or dot in the table header area. Green = connected. Grey/red = disconnected/reconnecting. CSS-only state change on SSE connect/disconnect events. |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| "N new QSOs" notification banner when filters are active | User with active filters sees a non-intrusive banner: "3 new QSOs logged — clear filters to see them". Lets them stay in context without missing activity. | MEDIUM | Requires tracking a count of incoming events that were suppressed because filters were active. Dismiss on click. |
| Animated row highlight on new prepend | New row fades in with a brief green highlight, then settles. Confirms which row is new at a glance. | LOW | Pure CSS: add a class on SSE insert, remove after animation completes. `@keyframes` flash from highlight color to transparent. |
| Per-page QSO count update without full table refresh | When on page 1 (no filters), auto-update the "Showing X–50 of N" count as new QSOs arrive | LOW | Increment a counter in JS when a new row is prepended. Avoids re-fetching the total. |
| Tombstone row when a QSO visible on page 1 is deleted | If another session soft-deletes a QSO currently visible on the same user's page 1, that row could go stale | HIGH | Requires a separate change stream event type for updates/deletes, a per-row `data-qso-id` attribute, and client-side row lookup. Significant complexity for a rare case. Defer. |
| SSE reconnection with exponential backoff | If the SSE connection drops (server restart, timeout), the client should reconnect silently. HTMX SSE extension handles this by default, but the backoff behavior is configurable. | LOW | HTMX SSE extension reconnects automatically. No extra code needed unless custom backoff is required. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-refresh on all pages | "Keep everything live" sounds good | Page 2+ is historical browsing. Inserting a new row on page 2 shifts the visible rows, breaks scroll position, and confuses the user who is looking at old QSOs — not the live log. | Refresh only on page 1. Add a subtle "new QSOs available" badge on page 2+ if needed. |
| Auto-refresh with active filters silently inserting rows | "Always show new QSOs" | A new CW contact appears at the top of the user's "FT8 only" filtered view. This is wrong — it violates the filter contract. Even if the row technically matches the filter, the client cannot verify this without a round trip. | Pause auto-refresh when filters are active. Show a notification instead. |
| Full page polling every N seconds | "Simpler than SSE" | Polling re-fetches the entire table, which resets scroll position, flickers all rows, and loses any in-progress inline edits. At 50 rows per poll, this is also 50x the data transfer of a single prepended row. For a self-hosted system this is wasteful but tolerable — the real damage is the UX regression. | Use SSE + row prepend. The infrastructure already exists in the codebase. |
| Broadcast all operators' new QSOs to the log view | "More data is better" | The log view is explicitly scoped to the current operator. Receiving someone else's QSO in your personal log view is confusing and potentially alarming. The station feed on form.html already serves the "all operators" use case. | Filter SSE events on the server side: only push to the operator's own queue. |
| Polling fallback for non-SSE clients | "Broader compatibility" | Modern browsers all support SSE. The existing station feed already uses SSE with no fallback and it works. Adding polling fallback doubles the server-side implementation and the complexity for negligible gain on a self-hosted app. | SSE only. The target audience (ham radio operators running ollog on a home server) uses modern browsers. |
| WebSocket upgrade | "More bidirectional" | WebSockets are bidirectional — the log view has no need to send data back on the same channel. SSE is the right primitive for server-push-only. WebSocket adds handshake complexity, requires a different server-side pattern, and provides no benefit here. | SSE via the existing `ConnectionManager` pattern. |
| Infinite scroll auto-loading on scroll | "No pagination" | The log view already has pagination, which users have formed habits around. Infinite scroll breaks the URL-based state model (page= in the query string), breaks direct-link sharing of a page position, and is harder to implement correctly with HTMX. | Keep pagination. Auto-refresh on page 1 only. |

---

## Feature Dependencies

```
Per-operator SSE queue (new)
    requires: ConnectionManager change to support per-operator queues
              OR: client-side filtering of broadcast events (simpler, no server change)
    required by: auto-refresh scoped to current operator

Auto-refresh on page 1 only (new)
    requires: per-operator SSE queue (or client-side filter)
    requires: page state readable in the template (already available as {{ page }})
    required by: all auto-refresh features

Suspend auto-refresh when filters active (new)
    requires: filter state readable in the template (already available as {{ filters }})
    required by: "N new QSOs" notification banner (only fires when refresh is suspended)

"N new QSOs" notification banner (differentiator)
    requires: suspend-when-filters logic
    requires: client-side counter of suppressed SSE events

Animated row highlight on prepend (differentiator)
    requires: auto-refresh on page 1 (must have rows being prepended)
    requires: CSS animation (no JS dependency)

Per-page count update (differentiator)
    requires: auto-refresh on page 1
    requires: JS access to the "Showing X-Y of N" element
```

### Dependency Notes

- **Per-operator SSE queue vs client-side filter:** The simplest implementation broadcasts to all connected operators and filters on the client (JS checks `data-operator` attribute on the SSE event). This requires zero changes to `ConnectionManager`. The cleaner approach (per-operator queues) requires modifying `manager.py` but eliminates unnecessary broadcast traffic. For a self-hosted single-operator or few-operator deployment, client-side filtering is acceptable. Recommend client-side filter for v1, per-operator queues as a follow-on.

- **Suspend-when-filters conflicts with silent-insert:** These are mutually exclusive choices. Picking one means rejecting the other. This document recommends suspend-when-filters as the table stakes behavior; silent-insert-when-filters is explicitly an anti-feature.

---

## Answering the Specific Questions

### 1. SSE push vs periodic polling

**Recommendation: SSE push.**

The SSE infrastructure (`ConnectionManager`, `watch_qsos`, `/feed/station`) already exists and works. Adapting it to push operator-scoped events to the log view is the natural extension. Polling every N seconds would require a new background loop, causes visible flicker on table reload, resets scroll position, and destroys in-progress inline edits. There is no motivation to choose polling given the existing SSE stack.

**Confidence: HIGH** — based on codebase inspection. The SSE pattern is proven in production.

### 2. Auto-refresh on all pages vs page 1 only

**Recommendation: page 1 only.**

The log view's default sort is `-qso_date_utc` (newest first). Page 1 is the live view. Page 2+ is historical. Prepending to page 2 would push existing visible rows off the bottom of the page (now page 3 has one QSO that was on page 2) and confuse the user who is browsing history. Page 1 only. Disable the SSE connection (or ignore events) when `page > 1`.

**Confidence: HIGH** — pagination UX is well-understood and the existing code makes the page number trivially available to the template.

### 3. Auto-refresh with active filters

**Recommendation: suspend auto-refresh when any filter is active.**

When filters are active, a new QSO arriving via SSE may or may not match the filter. The client cannot evaluate filter predicates (especially date range) without a server round trip. Inserting it unconditionally violates the filter contract. Silently dropping it leaves the user uncertain. The right answer is: pause auto-refresh, show a passive indicator ("auto-refresh paused — filters active"), and let the user decide to clear filters.

**Confidence: HIGH** — this is a logical constraint, not an empirical question.

### 4. New QSO arrives while user is on page 2 with filters

**Recommendation: do nothing visible except a passive badge.**

The user is in historical browse mode with active filters. No rows should change. A small badge on the "Log View" nav item or at the top of the filters card — "N new QSOs logged" — is optional (differentiator) and lets them know activity occurred without disrupting their current view. Clicking it clears filters and returns to page 1.

**Confidence: HIGH** — derived from combining the page 1 rule and the filter suspension rule.

### 5. Notification banner vs silent auto-prepend vs periodic silent refresh

**Recommendation: silent auto-prepend on page 1 with no filters, with a visual "Live" indicator. Notification banner only when filters are active.**

Silent auto-prepend is the right default. It requires no user action and matches the behavior they've already seen in the station feed on form.html. A "Live" dot (green = connected, grey = not connected) provides enough feedback that the system is working without being intrusive. The notification banner is only needed when auto-refresh is paused, to avoid the user thinking nothing is happening.

Periodic silent refresh is an anti-feature (see above).

**Confidence: HIGH** — the existing station feed demonstrates that silent prepend is acceptable UX for this user population.

### 6. Operator scoping

**Recommendation: log view auto-refresh shows only the current operator's new QSOs.**

The log view is already scoped to `_operator == callsign`. The auto-refresh must maintain this invariant. The station feed on form.html handles the "all operators" use case. These are different views for different purposes.

Implementation path: add `operator` as a field in the SSE event payload (the `watch_qsos` change event already has `doc.get("_operator", "")`). In the client, check whether the incoming event's operator matches the logged-in callsign before prepending the row. This requires no changes to `ConnectionManager` and no additional SSE endpoints. The operator callsign is available in the rendered page as `{{ callsign }}`.

**Confidence: HIGH** — architectural constraint derived from existing scoping model.

---

## MVP Definition

### Launch With (v1)

- [ ] SSE connection to an operator-scoped event stream — only the current operator's QSOs trigger updates
- [ ] Auto-prepend new row on page 1 with no filters active
- [ ] Suspend SSE connection (or ignore events) on page > 1
- [ ] Suspend auto-refresh (with static indicator) when any filter is active
- [ ] "Live" connection indicator dot in the table header row

### Add After Validation (v1.x)

- [ ] Animated row highlight on prepend — only add once the basic prepend is working and tested
- [ ] "N new QSOs" notification banner when filters are active — needs the suppressed-event counter

### Future Consideration (v2+)

- [ ] Per-operator SSE queues in `ConnectionManager` — eliminates unnecessary broadcast traffic; worth it only when the operator count is large enough to matter
- [ ] Tombstone row for deleted QSOs — high complexity for a rare case

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| SSE push new row on page 1, no filters | HIGH | MEDIUM | P1 |
| Operator scoping of SSE events | HIGH | LOW | P1 |
| Suspend on page > 1 | HIGH | LOW | P1 |
| Suspend when filters active | HIGH | LOW | P1 |
| "Live" connection indicator | MEDIUM | LOW | P1 |
| Animated row highlight | MEDIUM | LOW | P2 |
| "N new QSOs" banner when filters active | MEDIUM | MEDIUM | P2 |
| Per-operator SSE queues (server-side) | LOW | MEDIUM | P3 |
| Tombstone for deleted rows | LOW | HIGH | P3 |

---

## Implementation Notes for Planner

### Where the work lives

- `app/feed/router.py` — add a new `/feed/log` endpoint that yields events filtered by `_operator`. Or: reuse `/feed/station` and filter client-side using a `data-operator` attribute on the SSE event.
- `templates/log/log.html` — add SSE connection (`hx-ext="sse"`, `sse-connect`), conditional on `page == 1 and not any active filter`. Add the "Live" indicator element.
- `templates/log/log_table.html` — add `sse-swap="new_qso"` and `hx-swap="afterbegin"` on tbody, conditional on page 1 / no filters.
- `templates/log/qso_row.html` or a new `log_row_sse.html` — the SSE event must render a row partial compatible with the log table's columns (Date/Time, Call, Band, Mode, Freq, RST S/R, Actions). This is different from `feed_row.html` (which lacks edit/delete actions and RST columns).
- `app/feed/manager.py` — `watch_qsos` already has `_operator` in the document. No structural change needed if client-side filtering is used. If server-side operator queues are added, this is where the change goes.

### Key constraint: row partial must match the log table schema

The existing `feed_row.html` renders 6 columns (Time, Call, Band, Mode, Freq, Operator). The log table (`log_table.html`) renders 7 columns (Date/Time UTC, Callsign, Band, Mode, Freq, RST S/R, Actions). A new SSE row partial that matches the log table schema is required. It must include edit/delete action buttons and a `data-qso-id` attribute for the edit flow to work correctly on newly prepended rows.

### Key constraint: inline edit actions must work on prepended rows

The log table's edit/delete actions use HTMX `hx-get`, `hx-patch`, `hx-delete` with the QSO's `id` in the URL. These are rendered server-side. A prepended SSE row needs the same attributes rendered correctly, which means the SSE event must include a fully rendered row partial (not raw data), rendered by the server with the correct QSO id. This is consistent with how `feed_row.html` already works — `watch_qsos` renders HTML on the server and broadcasts it. The new SSE row partial must be rendered the same way.

---

## Sources

- Direct codebase inspection: `app/feed/manager.py`, `app/feed/router.py`, `app/qso/ui_router.py`, `templates/log/log.html`, `templates/log/log_table.html`, `templates/log/form.html`, `templates/log/feed_row.html`, `app/qso/models.py`
- HTMX SSE extension behavior: documented in htmx.org/extensions/sse (SSE extension reconnects automatically; `sse-swap` attribute maps event names to swap targets)
- Pagination UX: standard web application pattern — page 1 = live view, page N = historical navigation

---

*Feature research for: ollog — live auto-refresh for paginated QSO log view*
*Researched: 2026-04-08*
