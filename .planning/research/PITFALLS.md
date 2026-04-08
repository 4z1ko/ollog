# Pitfalls Research

**Domain:** Live auto-refresh on a paginated, filterable HTMX table (ham radio QSO log)
**Researched:** 2026-04-08
**Confidence:** HIGH (codebase read directly; HTMX/SSE behavior verified against official docs and spec)

---

## Critical Pitfalls

### Pitfall 1: SSE push rows ignore active filters — wrong-operator or wrong-filter QSOs appear

**What goes wrong:**
`watch_qsos` in `app/feed/manager.py` broadcasts every insert to all connected SSE clients via `manager.broadcast(html)`. There is no operator scoping. If the log view subscribes to the station feed, any QSO logged by any operator (or via UDP for a different operator) is prepended into every user's log table regardless of whose QSOs are displayed.

Additionally, `sse-swap="new_qso" hx-swap="afterbegin"` prepends raw HTML rows without checking the active filter state. A row for band=80M will be prepended even if the user is currently filtered to band=20M.

**Why it happens:**
The existing `/feed/station` endpoint is designed for a shared all-operators display (the QSO entry form). It intentionally shows every operator. Reusing it for a per-operator log view is the path of least resistance but violates operator isolation, which is a core system invariant enforced everywhere else (JWT → callsign → DB query).

**How to avoid:**
Create a separate per-operator SSE endpoint (e.g., `/feed/my-qsos`) that only emits events for the authenticated operator's callsign. The server checks `doc.get("_operator") == callsign` before putting to a client queue. The `get_current_operator_callsign_cookie` dependency already handles the auth; the filter is a single `if` statement in the broadcast loop.

For the filter mismatch: do not use `sse-swap afterbegin` to inject individual rows. Use SSE as a trigger for a full table reload (`hx-get="/log/view"` with current filter params). The server re-renders the filtered, sorted page — a new row that does not match the active filter simply does not appear.

**Warning signs:**
- QSOs from other operators appear in your filtered log view
- A filtered-to-80M view shows a 20M QSO after a UDP insert
- Row count in "Showing X–Y of N" does not match visible rows

**Phase to address:** First plan of the live-refresh milestone — before any SSE wiring in the log view template

**Severity:** BLOCKING — breaks operator isolation, the most fundamental system invariant

---

### Pitfall 2: Polling with hx-trigger="every Ns" loses active filter params

**What goes wrong:**
If the log table refreshes via `hx-get="/log/view" hx-trigger="every 10s"`, the GET request only includes params that are embedded in the URL or gathered via `hx-include`. Without `hx-include` pointing at the filter form, the poll fires with a bare `/log/view` — returning the unfiltered page-1 view and overwriting the user's current filtered or paginated state.

The current `log.html` renders the table inside `<div id="log-table">`. A polling trigger on that div has no natural access to the filter form values in `#filter-form`.

**Why it happens:**
Polling fires from the element carrying `hx-trigger="every Ns"` and collects params only from itself and any `hx-include` selectors. No `hx-include` means the URL built is `/log/view` with no page, sort, call, band, mode, date_from, date_to.

**How to avoid:**
Add `hx-include="#filter-form"` to the polling element. Also include a hidden `<input name="page">` that tracks the current page number, or accept that polling always resets to page 1 (which is correct behavior if the goal is "new rows arrive at the top").

**Warning signs:**
- Polling request in browser DevTools shows `/log/view` with no query params
- User is on page 3 with a filter, polling sends them back to page 1 unfiltered

**Phase to address:** Polling implementation plan (if polling is chosen over SSE)

**Severity:** BLOCKING for correctness; non-blocking for app stability

---

### Pitfall 3: Polling element destroyed by filter submit or pagination — interval resets

**What goes wrong:**
If the polling trigger lives on `<div id="log-table">` or any element inside it, and the filter form submit replaces `#log-table` via `hx-target="#log-table" hx-swap="innerHTML"`, the polling element is destroyed and re-created. The new element starts a fresh polling interval. This causes:
- A gap where no polling is active between the submit and when the new content settles
- An interval reset (submit at second 8 of a 10s cycle → next poll is 10s later, not 2s later)

**Why it happens:**
HTMX attaches polling timers to DOM elements. When an element is swapped out its timer is not transferred to the replacement. The replacement has to set up its own timer from scratch.

**How to avoid:**
Place the polling trigger on an element **outside** the swap target — e.g., a `<span id="log-poll-trigger">` outside `#log-table`, with `hx-target="#log-table"` and `hx-include="#filter-form"`. This element survives filter form submits and pagination clicks.

Alternatively, use SSE-triggered reload (see Pitfall 1 prevention), which avoids this problem entirely — the SSE anchor lives outside the table and is never destroyed by inner swaps.

**Warning signs:**
- After a filter submit, polling pauses noticeably longer than the configured interval
- DevTools shows two rapid poll requests immediately after a filter submit

**Phase to address:** Same plan as Pitfall 2

**Severity:** Non-blocking (polling resumes, just delayed) but creates a perceptible UX gap

---

### Pitfall 4: SSE parent element destroyed by pagination swap — connection silently drops

**What goes wrong:**
If the `hx-ext="sse"` element is placed inside `#log-table`, then every pagination click (`hx-target="#log-table" hx-swap="innerHTML"`) destroys the SSE parent element.

When the parent element is replaced, htmx-ext-sse 2.2.4 dispatches `htmx:sseClose` with `detail.type="nodeReplaced"` and terminates the `EventSource`. The browser does **not** auto-reconnect because the element no longer exists. The feed goes silent until the user reloads the page.

**Why it happens:**
SSE connections are scoped to their host element in htmx-ext-sse. The extension explicitly monitors for DOM replacement and closes gracefully. Placing `hx-ext="sse"` inside a swap target is structurally incorrect.

**How to avoid:**
The `hx-ext="sse"` anchor must be outside `#log-table`. Pattern:
```html
<div id="sse-anchor" hx-ext="sse" sse-connect="/feed/my-qsos">
  <div id="log-table" ...>
    {% include "log/log_table.html" %}
  </div>
</div>
```
The `sse-swap` target points to an element inside `#log-table` by id. The outer `#sse-anchor` survives all inner swaps.

**Warning signs:**
- DevTools Network tab shows the EventSource connection closing on every pagination click
- No new rows appear after the first page navigation even with active QSO inserts

**Phase to address:** Log view template design plan — structural decision must be made before writing any template code

**Severity:** BLOCKING — live refresh completely stops after first pagination click

---

### Pitfall 5: Double-display when QSO is submitted via the web form

**What goes wrong:**
If `sse-swap afterbegin` is used to inject individual rows directly into `tbody`, a QSO submitted via the form at `/log/` will appear twice:
1. Immediately via SSE row injection into the top of the table
2. Again in its sorted position when the next full table reload runs

The SSE-injected row and the reload-rendered row are both present in the DOM simultaneously.

**Why it happens:**
Two update pathways insert the same data into the DOM: the SSE push (immediate row prepend) and the full-page reload (sorted server-rendered list). They are not coordinated.

**How to avoid:**
Do not use `sse-swap afterbegin` for individual row injection into the paginated table. Instead, use SSE as a signal only: emit an event with no (or minimal) data and have the log table listen with `hx-trigger="sse:new_qso"` to fire a full `hx-get="/log/view"` reload. The reload returns the entire correct sorted, filtered, paginated table — one source of truth, no duplication.

Note: the form (`/log/`) and the log view (`/log/view`) are separate pages in the current design. If they remain separate, there is no cross-page duplication risk. The risk only exists if both are combined onto a single page with the same DOM.

**Warning signs:**
- Same callsign row appears twice — once at the top (SSE-injected) and once in the sorted position
- Duplicate rows share the same `id` attribute value from the QSO ObjectId

**Phase to address:** SSE event payload design plan — row-inject vs reload-trigger decision

**Severity:** Non-blocking for correctness (no data lost) but creates visible duplication that erodes operator trust

---

### Pitfall 6: Stale "Showing X–Y of N" total count after SSE row injection

**What goes wrong:**
If a row is injected via SSE `afterbegin`, the pagination footer ("Showing 1–50 of 847") is not updated. The server-rendered count from the last GET is stale. After 5 new QSOs via SSE, the count still reads "847" when the real total is "852". The table also visually shows 51+ rows while the footer says "1–50."

**Why it happens:**
SSE `afterbegin` injects HTML fragments directly into the DOM without a server round-trip. The `total`, `page`, and `total_pages` values embedded in `log_table.html` are frozen at the time of the last full GET.

**How to avoid:**
Same as Pitfall 5 prevention. A full table reload returns freshly-calculated `total`, `page`, `total_pages` from the server. The pagination footer is automatically correct after every refresh because it is part of the same `log_table.html` partial that gets replaced.

**Warning signs:**
- "Showing 1–50 of 847" says 847 but the table visually has 52 rows
- "Page 1 of 17" indicator does not update after new QSOs arrive

**Phase to address:** Same plan as Pitfall 5

**Severity:** Non-blocking but creates data integrity appearance issues; operators will distrust the count

---

### Pitfall 7: MongoDB change stream reconnect drops inserts during the gap

**What goes wrong:**
`watch_qsos` in `app/feed/manager.py` catches `PyMongoError`, logs a warning, and restarts `collection.watch()` after a 1-second sleep. The new `watch()` call opens a fresh stream from the current oplog position — it does not resume from where it left off. Any `insert` events that occurred during the gap (between the error and the reconnect) are permanently missed.

In a high-activity scenario (FT8 overnight, UDP batch ingestion), the oplog can advance significantly during a 1-second gap. These inserts never reach SSE clients.

**Why it happens:**
MongoDB change streams support resumption via `resume_after` (using the `_id` resume token from the last received change event). The current code discards this token on error and opens a fresh stream. This is the simplest implementation but silently loses events during reconnects.

**How to avoid:**
Store the last seen resume token. On reconnect, pass `resume_after=last_token` to `collection.watch()`. If the token has expired from the oplog, fall back to a fresh stream and log a clear warning that events were missed.

```python
last_token = None
while True:
    try:
        kwargs = {"resume_after": last_token} if last_token else {}
        async with await collection.watch(pipeline, full_document="updateLookup", **kwargs) as stream:
            async for change in stream:
                last_token = change["_id"]
                ...
    except PyMongoError as e:
        logger.warning("Change stream error, reconnecting: %s", e)
        await asyncio.sleep(1)
```

**Warning signs:**
- Log view misses bursts of UDP-ingested QSOs that arrived during a brief MongoDB restart
- `PyMongoError` appears in logs followed by a visible gap in the live feed

**Phase to address:** Change stream hardening plan (standalone plan or part of the SSE infrastructure plan)

**Severity:** Non-blocking for data correctness (DB has all data) but HIGH for UX fidelity during UDP batch operations or container restarts

---

### Pitfall 8: JWT cookie expires during long-lived SSE connection — partial session failure

**What goes wrong:**
`jwt_expire_minutes: int = 60` is the default. The SSE endpoint authenticates via `get_current_operator_callsign_cookie` at **connection time only**. Once the `EventSource` is established, the server holds the connection open with no re-authentication. After 60 minutes the JWT has expired, but the SSE stream continues — no 401 is sent because HTTP response headers were already committed.

The problem surfaces on the next regular HTMX request (filter, pagination, QSO submit) which re-runs the auth dependency. That request gets a 401, the app exception handler fires, and the user is redirected to `/log/login`. The operator is logged out mid-session while the SSE feed was still delivering rows.

**Why it happens:**
FastAPI dependency injection validates the cookie once at request start. A long-held streaming response does not re-validate mid-stream. The mismatch between "SSE still open" and "all other requests now fail" creates a confusing partial-session state.

**How to avoid:**
Increase `jwt_expire_minutes` to cover a typical operating session (480 minutes / 8 hours recommended). This is a single config change with no code impact. The env var `JWT_EXPIRE_MINUTES` is already supported by pydantic-settings.

A more robust approach: add a periodic SSE heartbeat event that the client uses to verify session health. On receiving a heartbeat, fire `hx-get="/log/ping"` (lightweight 200/401 endpoint); on 401, redirect to login. This is significantly more complex and unnecessary if the simple config fix is applied.

**Warning signs:**
- Operator reports "it stopped working after an hour" — SSE shows new rows but clicking any link redirects to login
- 401 appears on HTMX filter/pagination requests in DevTools while the SSE EventSource remains open in the Network tab

**Phase to address:** Session management review (config note in the auto-refresh implementation plan; not a separate phase unless heartbeat approach is chosen)

**Severity:** Non-blocking (no data lost; user just has to re-login) but HIGH for UX — unexpected session loss during active logging is jarring

---

### Pitfall 9: Auto-refresh overwrites open inline edit row — unsaved data silently lost

**What goes wrong:**
The log view supports inline editing: clicking Edit on a row swaps it to an editable form via HTMX. If auto-refresh fires while the edit row is open, the refresh replaces `#log-table` with a server-rendered table containing the original unedited row. The user's partially-filled edit form is silently destroyed with no warning.

Polling and row-level edit requests are on different HTMX elements with no shared sync group. By default, HTMX 2.x drops a new trigger on an element if a request is already in-flight **on that same element** — but a polling trigger on `#log-table` and an edit action on `<tr id="qso-...">` are different elements and do not block each other.

**Why it happens:**
The `hx-target="#log-table"` on the polling/SSE trigger overwrites the entire table including any edit row variant currently in the DOM. There is no mechanism to detect "user is actively editing" before firing the refresh.

**How to avoid:**
Add a CSS class `.editing` to the table (or a data attribute) when any inline edit row is open. Condition the auto-refresh trigger to not fire while editing is active:
- For polling: `hx-trigger="every 10s [!document.querySelector('#log-table .editing')]"`
- For SSE reload: `hx-trigger="sse:new_qso [!document.querySelector('#log-table .editing')]"`

Alternatively, use `hx-sync="#log-table:drop"` on the auto-refresh element so it drops the refresh if any request targeting `#log-table` is in-flight. This covers the save action but not the pre-save idle time when the edit form is just open.

**Warning signs:**
- Inline edit form disappears mid-typing (auto-refresh fires during the edit)
- User clicks Save and the row is already back to the original view-mode version

**Phase to address:** Auto-refresh implementation plan — must explicitly account for the existing inline edit feature

**Severity:** BLOCKING for usability — causes silent data loss (unsaved edits) on every auto-refresh that fires during an edit session

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Reuse `/feed/station` (all-operators feed) for log view | No new endpoint | Breaks operator isolation — all operators' QSOs appear in every user's view | Never |
| `sse-swap afterbegin` for individual row injection | Rows appear instantly | Stale pagination counts; duplicate rows; filter bypass | Never for paginated+filtered table |
| Place SSE anchor inside `#log-table` | Simpler single-div HTML | SSE connection drops on every pagination click | Never |
| Skip resume token on change stream reconnect | Simpler code (~5 lines saved) | Missed inserts during reconnect gap | Acceptable for MVP if gap is logged as a warning |
| Keep jwt_expire_minutes=60 | Secure default | Session loss mid-SSE stream confuses active operators | Increase to 480 for operator sessions |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| htmx-ext-sse 2.2.4 + pagination | Placing `hx-ext="sse"` inside the swap target `#log-table` | SSE anchor must be outside `#log-table`; it must survive inner swaps |
| htmx-ext-sse 2.2.4 + operator scoping | Broadcasting all inserts to all SSE clients | Per-operator endpoint or server-side `_operator` check before broadcast |
| Browser EventSource + 401 response | Expecting EventSource to retry after cookie refresh | Per WHATWG spec, 401 permanently fails the connection with no retry — feed freezes silently |
| MongoDB change stream + reconnect | Fresh `watch()` without `resume_after` | Store `change["_id"]` as resume token; pass to next `watch()` call |
| Polling + inline edit rows | Polling overwrites open edit form | Condition trigger with `[!document.querySelector('.editing')]` |
| Polling + filter form submit | Poll fires without filter params | `hx-include="#filter-form"` required on the polling element |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Full table re-render on every SSE event from any source | DB query + Jinja2 render on every FT8 QSO insert | Filter: only trigger reload on the operator's own inserts | FT8 overnight: 240 renders/hour per connected client |
| `afterbegin` row injection + full reload on same event | Double render per insert | Pick one strategy — SSE as trigger for reload only | Any non-trivial insert rate |
| Polling at 5s with page_size=200 | 200 × `_qso_to_view_dict` per 5s per client | Use 15–30s intervals; SSE-triggered reload is more efficient | Noticeable in contest logging with multiple operators |
| Unbounded `asyncio.Queue` in ConnectionManager | Memory growth with slow SSE clients | Consider `asyncio.Queue(maxsize=50)` with discard-on-full | Dozens of concurrent operators |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Reusing all-operators SSE feed for per-operator log view | Operator A sees Operator B's callsigns and contacts | Filter before broadcast: `_operator == callsign` in `watch_qsos` |
| Including `callsign` as URL param in polling/SSE reload URL | URL manipulation lets user request another operator's data | Already protected: `/log/view` uses `callsign = Depends(get_current_operator_callsign_cookie)` — callsign always from JWT. Maintain this invariant in auto-refresh URLs; never add `?callsign=` param |
| SSE stays alive after account disable | Disabled operator continues receiving live feed | Accept the gap: next reconnect attempt hits 401 (per WHATWG spec, no retry after 401) |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Full table reload resets scroll position | User reading rows 45–50 gets snapped to top | Add `show:no-change` to `hx-swap` modifier — verify this is supported in HTMX 2.0.4 |
| Auto-refresh fires while user has text selected (copying a callsign) | Text selection cleared on DOM replacement | Check `document.getSelection().toString()` in trigger condition, or use morphing swap (idiomorph extension) |
| No visual indication that auto-refresh is active | User unsure if table is live | Add a small "Live" indicator that toggles on `htmx:sseOpen` / `htmx:sseClose` events |
| Auto-refresh fires during inline edit | Edit form destroyed without warning (see Pitfall 9) | Disable refresh while `.editing` class is present in table |
| 60-minute cookie expiry forces re-login with no warning | Operator loses context mid-session | Show a session-expiry warning banner using a JS timer seeded from the JWT `exp` claim |

---

## "Looks Done But Isn't" Checklist

- [ ] **Operator isolation in SSE:** With two logged-in operators, confirm operator A's QSOs do NOT appear in operator B's log view after a QSO insert
- [ ] **Filter params on refresh:** After setting a band filter, auto-refresh respects that filter — DevTools shows `band=20M` in the reload GET query string
- [ ] **SSE survives pagination:** After clicking "Next" to page 2, the SSE EventSource is still open — DevTools Network tab shows the connection is not closed
- [ ] **Edit row survives polling cycle:** Open an inline edit row, wait for one polling interval — verify the edit form is still present and untouched
- [ ] **Resume token on reconnect:** Restart the MongoDB container briefly — verify `watch_qsos` reconnects and subsequent inserts still appear in the feed
- [ ] **Cookie expiry behavior:** With `jwt_expire_minutes=1` in test, verify the app handles expiry gracefully (no silent SSE freeze; clear redirect or warning on next navigation)
- [ ] **Pagination count accuracy:** After auto-refresh delivers a new QSO, verify "Showing X–Y of N" reflects the updated total, not the stale count from before the insert

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong-operator rows in log view (P1) | HIGH | New per-operator SSE endpoint + broadcast filter + template change; DB data unaffected |
| SSE drops on pagination (P4) | LOW | Move SSE anchor element outside `#log-table` in one template file |
| Stale pagination count (P6) | LOW | Switch from row-injection SSE to reload-trigger SSE; event name change only |
| Edit row overwritten by refresh (P9) | MEDIUM | Add `.editing` state + conditional trigger; 2–3 template changes |
| Change stream gap on reconnect (P7) | LOW | Add resume token tracking to `watch_qsos`; ~10 lines of Python |
| Cookie expiry session loss (P8) | LOW | Increase `jwt_expire_minutes` in config or `.env`; no code change |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Wrong-operator SSE broadcast (P1) | SSE endpoint design plan — before any log view wiring | Two-operator test: confirm isolation |
| Filter params lost on poll (P2) | Polling implementation plan — `hx-include` in first template PR | DevTools: check GET query string on poll |
| Polling resets after filter submit (P3) | Polling implementation plan — trigger placement decision | Observe timing gap after filter submit |
| SSE anchor inside swap target (P4) | Log view template design plan — structural decision before writing any HTML | DevTools: confirm EventSource survives page nav |
| Double-display after form submit (P5) | SSE event strategy plan — row-inject vs reload-trigger | Submit QSO, count table rows, check for duplicates |
| Stale pagination count (P6) | Same plan as P5 | Check footer count vs visible rows after SSE event |
| Change stream gap on reconnect (P7) | Change stream hardening plan | MongoDB container restart test |
| JWT expiry mid-SSE (P8) | Config review in auto-refresh plan | `jwt_expire_minutes=1` expiry test |
| Edit row destroyed by refresh (P9) | Auto-refresh + inline-edit integration plan — explicit test case | Open edit row, wait one refresh cycle |

---

## Sources

- HTMX 2.0.4 docs, hx-trigger polling: https://htmx.org/attributes/hx-trigger/
- HTMX 2.0.4 docs, hx-sync: https://htmx.org/attributes/hx-sync/
- htmx-ext-sse 2.2.4 docs: https://htmx.org/extensions/sse/
- htmx-ext-sse GitHub source (nodeReplaced / sseClose event): https://github.com/bigskysoftware/htmx/blob/master/www/content/extensions/sse.md
- htmx-ext-sse error handling issue #134: https://github.com/bigskysoftware/htmx-extensions/issues/134
- WHATWG SSE spec, EventSource failure on non-200: https://html.spec.whatwg.org/multipage/server-sent-events.html
- MongoDB change streams, resume tokens: https://www.mongodb.com/docs/manual/changestreams/
- Codebase direct reading: `app/feed/manager.py`, `app/feed/router.py`, `app/qso/ui_router.py`, `templates/log/log.html`, `templates/log/log_table.html`, `templates/log/form.html`, `app/config.py`, `app/auth/dependencies.py`, `app/main.py`

---
*Pitfalls research for: live auto-refresh on paginated filterable HTMX QSO log table*
*Researched: 2026-04-08*
