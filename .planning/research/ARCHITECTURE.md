# Architecture Research

**Domain:** Live auto-refresh for operator-scoped paginated log table
**Researched:** 2026-04-08
**Confidence:** HIGH — based on direct codebase inspection of all relevant files

---

## Context: Existing Architecture

The existing system is a FastAPI + Beanie/MongoDB stack. Relevant components:

- `app/feed/manager.py` — `ConnectionManager` with a flat `set[asyncio.Queue]`, `watch_qsos()` change stream watcher that broadcasts all inserts to all connected queues
- `app/feed/router.py` — `/feed/station` SSE endpoint, auth via cookie, broadcasts all operator inserts to all connected clients (no per-operator routing)
- `templates/log/form.html` — SSE consumer on `#station-feed tbody` using `sse-swap="new_qso" hx-swap="afterbegin"` — confirmed working in production
- `templates/log/log.html` — log view wrapper with `#log-table` div and `#filter-form`, includes `log_table.html` at load time
- `templates/log/log_table.html` — paginated table fragment rendered by `/log/view`; all navigation (sort, page, filter submit) does `hx-get="/log/view"` → `hx-swap="innerHTML"` on `#log-table`
- `app/qso/ui_router.py` — `/log/view` route, enforces operator isolation via `get_current_operator_callsign_cookie`, returns the fragment for HTMX requests
- `app/qso/service.py` — `get_qso_page()` queries `{_operator: callsign, _deleted: false}` with full filter/sort/page support

The operator isolation key is `_operator` (MongoDB field alias for `operator_callsign`). The `/log/view` route already enforces per-operator scoping.

---

## Approach Comparison

### Approach A: HTMX Polling

Add `hx-trigger="every 30s"` to the `#log-table` div. On each tick, HTMX re-fetches `/log/view` with the current filter form state serialized as query parameters. The response replaces `innerHTML` of `#log-table` with a freshly rendered `log_table.html` fragment.

**How it works:**

```
Browser (every 30s, tab visible)
  → GET /log/view?band=40M&sort=-qso_date_utc&page=2
  ← log_table.html fragment (HX-Request header detected)
  → hx-swap="innerHTML" replaces #log-table
```

**Files changed:**

| File | Change |
|------|--------|
| `templates/log/log.html` | Add `hx-trigger`, `hx-get`, `hx-include` to `#log-table` div |
| `templates/log/log_table.html` | Add hidden `<input name="page">` to carry page state through polls |

No new files. No backend changes.

---

### Approach B: Per-Operator SSE Push

New SSE endpoint `/feed/log` scoped per operator. Change stream pushes rendered row HTML directly into the log table tbody.

**How it would work:**

1. `ConnectionManager` refactored: `set[Queue]` → `dict[str, set[Queue]]`; `connect(operator)`, `broadcast(operator, event)`
2. `watch_qsos()` reads `_operator` from each change event, routes to operator-specific queues only
3. New `/feed/log` endpoint connects authenticated operator to their queue slot
4. `log.html` or `log_table.html` adds SSE connect on tbody with `sse-swap="new_log_row" hx-swap="afterbegin"`

**Files changed:**

| File | Change | New? |
|------|--------|------|
| `app/feed/manager.py` | Replace `set[Queue]` with `dict[str, set[Queue]]`; update all three methods | No |
| `app/feed/router.py` | Add `/feed/log` endpoint, pass operator to `manager.connect(operator)` | No |
| `templates/log/log.html` or `log_table.html` | Add SSE connect block on tbody | No |
| New row template | SSE-pushed row variant with edit/delete buttons | Yes |

---

## Analysis

### Question 1: Files changed per approach

**Approach A** touches 2 template files, no backend files, no new files.

**Approach B** touches 2 backend files, 1-2 template files, creates 1 new template file.

### Question 2: Pagination and filter interaction

**Approach A** handles this correctly. The poll re-fetches with the current page and filters included in the request. The key requirement is that the page number must be passed in the poll request — not just the filter form values. The current `#filter-form` in `log.html` does not contain a `page` input; it only contains filter fields and a hidden `sort` input. The page parameter is embedded in pagination links, not in the form. Without explicit handling, the poll defaults `page` to 1 on every tick, resetting the user.

Fix: add a hidden div inside `#log-table` (re-rendered as part of the fragment on every load) containing `<input type="hidden" name="page" value="{{ page }}">`. Expand `hx-include` to cover both the filter form and this element. Because the fragment always re-renders with the correct page value from the server, the poll always requests the page the user is currently viewing.

**Approach B** does not handle pagination and filters correctly. SSE push prepends a new row to the tbody. The server pushing the row has no knowledge of:
- Which page the user is currently viewing (SSE is a push channel, not a request/response)
- Which filters are active in the user's browser
- Whether the new QSO matches those filters

A new QSO would be prepended regardless of whether the user is on page 1, page 3, or has a band filter active that excludes the new QSO. The injected row is always wrong except in the trivial case: user is on page 1, no filters, sorting newest-first.

### Question 3: Duplicate rows when user submits a QSO via the form

**Approach A:** No duplicate risk. Each poll replaces the entire table fragment with a fresh server query. The submitted QSO is already in the database at submit time (the form POST completes before the poll fires). When the poll fires next, it fetches the authoritative data from the database and replaces the table. No duplicate row can exist.

**Approach B:** Duplicate risk exists. If the user submits from the form on `form.html` (station feed page), the station feed SSE already shows the row there. But for a user on `log.html`, SSE pushes the new row into the tbody. If the user then navigates to page 1 (or the next poll fires), the row appears again via the full table render. The only deduplication mechanism in HTMX is id-based, and `hx-swap="afterbegin"` does not deduplicate by id — it always inserts. The SSE-injected row would need `id="qso-<mongo_id>"` to match the server-rendered row, but HTMX's `afterbegin` does not check for existing matching ids before inserting.

### Question 4: sse-swap + hx-swap="afterbegin" on tbody — does it work?

Yes, confirmed working. The existing `templates/log/form.html` uses this exact pattern on the station feed:

```html
<tbody id="station-feed" sse-swap="new_qso" hx-swap="afterbegin">
```

The HTMX SSE extension reads `hx-swap` on the element bearing `sse-swap` and applies the specified swap strategy when the named event arrives. `afterbegin` on a `tbody` prepends `<tr>` children correctly.

The mechanics work. The problem with Approach B is not HTMX SSE mechanics — it is semantic mismatch with a filtered, paginated view. SSE push into a tbody works correctly for an unscoped append-only feed (which is exactly what `form.html` uses it for). It does not work correctly for a filtered, paginated table.

**Critical structural problem for Approach B:** The `#log-table` div's `innerHTML` is replaced on every sort, filter, and pagination action. If SSE connect attributes are on an element inside `log_table.html` (the fragment), that element is destroyed and recreated on each navigation, dropping the SSE connection. The HTMX SSE extension does not automatically re-establish connections after an `innerHTML` swap destroys the element holding `hx-ext="sse"`. The SSE connect would need to live on the stable `#log-table` div in `log.html`, but the `sse-swap` target (the tbody) is inside the fragment and gets recreated on every table load. This creates an orphaned SSE connection pointing at a non-existent tbody every time the user navigates.

### Question 5: Build order if Approach B is chosen

Not applicable — Approach B is not recommended. See the hybrid note below if sub-second latency is required.

---

## Recommendation: Approach A (HTMX Polling)

**Use polling. Do not push rows via SSE into the log table.**

The fundamental mismatch: SSE push is designed for an append-only feed with no state beyond "prepend this row." The log table is a paginated, filtered, sorted view. SSE push cannot respect the user's current page, active filters, or sort order without the client transmitting that state — which negates the simplicity of push.

The existing station feed on `form.html` works with SSE precisely because it abandons pagination and filters entirely. The log view is the opposite design.

Polling solves every edge case by reusing the existing server-side query unchanged. The 30-second interval is appropriate for a logbook (ham radio QSO entry is not millisecond-critical). With the visibility guard, polling stops when the tab is backgrounded, reducing unnecessary load.

---

## System Overview: Approach A

```
Browser: log.html
    |
    | Initial load: GET /log/view (no HX-Request header)
    |   <- full log.html page with embedded log_table.html fragment
    |
    | [#filter-form submit]
    | GET /log/view?band=40M&mode=FT8&sort=-qso_date_utc
    |   <- log_table.html fragment
    |   -> hx-swap="innerHTML" on #log-table
    |
    | [pagination click]
    | GET /log/view?page=2&band=40M&sort=-qso_date_utc
    |   <- log_table.html fragment
    |   -> hx-swap="innerHTML" on #log-table
    |
    | [every 30s, document.visibilityState === 'visible']
    | GET /log/view?band=40M&sort=-qso_date_utc&page=2   <- page from hidden input
    |   <- log_table.html fragment (updated, operator-scoped)
    |   -> hx-swap="innerHTML" on #log-table
    |
    v
FastAPI /log/view
    |
    | get_current_operator_callsign_cookie() <- JWT cookie
    | -> callsign = "W1AW"
    |
    | get_qso_page(operator="W1AW", page=2, band="40M", sort="-qso_date_utc")
    | -> QSO.find({_operator:"W1AW", _deleted:false, BAND:"40M"})
    |    .sort("-qso_date_utc").skip(50).limit(50)
    |
    | render log_table.html with {qsos, total, page, page_size, total_pages, filters, sort}
    |
    v
Browser: #log-table innerHTML replaced with fresh fragment
    -> new QSOs visible if they match filter + are on current page
    -> pagination counts updated
    -> hidden page input re-rendered with current page value
```

---

## Integration Points: Exact Files

### Files to modify

**`templates/log/log.html`**

The `#log-table` div receives polling attributes:

```html
<div id="log-table"
     hx-get="/log/view"
     hx-trigger="every 30s [document.visibilityState === 'visible']"
     hx-include="#filter-form, #log-page-state"
     hx-swap="innerHTML">
  {% include "log/log_table.html" %}
</div>
```

`hx-include="#filter-form, #log-page-state"` serializes all named inputs from both elements. `#log-page-state` is a hidden div inside the fragment (see below).

**`templates/log/log_table.html`**

Add a hidden state carrier after the pagination div:

```html
<div id="log-page-state" style="display:none">
  <input type="hidden" name="page" value="{{ page }}">
</div>
```

This div is inside `#log-table` (via the fragment), so it exists in the DOM after every table load. Because `#log-table` is refreshed on every navigation (filter, sort, pagination), this hidden input always carries the current page value. When the poll fires, `hx-include` picks it up and sends `page=N` with the request.

### Files unchanged

| File | Reason unchanged |
|------|------------------|
| `app/feed/manager.py` | No change needed |
| `app/feed/router.py` | No change needed |
| `app/qso/ui_router.py` | `/log/view` already handles HTMX partial correctly |
| `app/qso/service.py` | No change needed |
| `app/qso/models.py` | No change needed |
| All other templates | No change needed |

### No new files required

---

## Build Order

Approach A is a single-phase implementation:

1. Add `#log-page-state` hidden div to `templates/log/log_table.html`
2. Add polling attributes to `#log-table` in `templates/log/log.html`
3. Smoke test: navigate to page 2 with a filter active, wait 30s, confirm the table refreshes to page 2 with the filter intact
4. Confirm poll does not interfere with filter submit, sort, or pagination
5. Optional: add brief CSS fade animation on `#log-table` `htmx:afterSettle` to signal a background refresh happened

---

## Approach B Hybrid: SSE Notification + Manual Refresh

If sub-30-second latency is a hard requirement for some future milestone, the correct architecture is a hybrid:

1. SSE push delivers a notification badge (count of new QSOs since page load), not rendered rows
2. The badge is driven by per-operator SSE (requires `manager.py` refactor)
3. Clicking the badge triggers `hx-get="/log/view"` to reload page 1 with no filters
4. This keeps SSE in its appropriate role (notification) and polling/manual refresh in its role (data display)

This avoids all filter/pagination/duplicate-row problems while still providing a real-time signal. This is a separate milestone — do not mix with Approach A.

---

## Anti-Patterns

### Anti-Pattern 1: SSE row injection into a paginated tbody

**What people do:** Connect SSE to the same tbody that pagination navigates, push new rows via `afterbegin`.

**Why it's wrong:** (a) The tbody is destroyed and recreated on every pagination/filter/sort action, dropping the SSE connection. (b) New rows are injected regardless of active filters or current page. (c) `afterbegin` does not deduplicate by row id before inserting.

**Do this instead:** Use SSE for append-only feeds only (like the existing station feed on `form.html`). Use polling for paginated, filtered tables.

### Anti-Pattern 2: Polling without page state

**What people do:** Add `hx-trigger="every 30s"` without including the current page number, defaulting the request to `page=1`.

**Why it's wrong:** User is reading page 3. Table resets to page 1 every 30 seconds. Jarring and disruptive.

**Do this instead:** Include a server-rendered hidden `page` input in the fragment so the poll request always carries the correct page.

### Anti-Pattern 3: Polling without visibility guard

**What people do:** Poll unconditionally, including when the tab is backgrounded.

**Why it's wrong:** Wastes server resources and MongoDB queries for idle/background tabs. On a multi-operator deployment, background polling multiplies the query load.

**Do this instead:** `hx-trigger="every 30s [document.visibilityState === 'visible']"` stops polls when the tab is not visible.

### Anti-Pattern 4: Touching feed infrastructure for Approach A

**What people do:** Preemptively refactor `manager.py` to operator-keyed routing when implementing polling.

**Why it's wrong:** Approach A requires zero changes to the feed infrastructure. Any change to `manager.py` adds risk to the existing station feed with no benefit for the polling feature.

**Do this instead:** Leave `manager.py`, `router.py`, and all feed code untouched.

---

## Scalability Considerations

| Scale | Approach |
|-------|----------|
| 1-50 active operators | 30s polling is negligible. MongoDB compound index on `(_operator, _deleted)` makes each poll query fast. |
| 50-500 active operators | Polling remains fine. Staggered poll timing (each browser connects at a random offset) distributes the query load naturally. |
| 500+ active operators | Consider increasing poll interval to 60s or using the SSE notification hybrid to reduce background query load. |

---

## Sources

- Direct codebase inspection (HIGH confidence): `app/feed/manager.py`, `app/feed/router.py`, `app/qso/ui_router.py`, `app/qso/service.py`, `app/qso/models.py`, `templates/log/form.html`, `templates/log/log.html`, `templates/log/log_table.html`, `templates/log/qso_row.html`, `templates/log/feed_row.html`
- [HTMX SSE Extension documentation](https://htmx.org/extensions/sse/) — `sse-swap`, `hx-swap` interaction (MEDIUM confidence — docs are sparse on this interaction; production usage in `form.html` is the authoritative confirmation)
- [HTMX hx-trigger polling documentation](https://htmx.org/attributes/hx-trigger/) — `every <timing>` syntax, conditional triggers with `[expr]` (HIGH confidence — official documentation)
- Existing working pattern in `templates/log/form.html` line 110 — `sse-swap + afterbegin on tbody` confirmed in production (HIGH confidence)

---

*Architecture research for: live auto-refresh on operator-scoped paginated log table*
*Researched: 2026-04-08*
