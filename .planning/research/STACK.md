# Stack Research: Live QSO Auto-Refresh for Paginated Log Table

**Domain:** HTMX-driven live table refresh — SSE-triggered re-fetch vs polling, pagination-aware
**Researched:** 2026-04-08
**Confidence:** HIGH for core HTMX attribute syntax (verified via official htmx.org docs); HIGH for htmx-ext-sse 2.2.4 patterns (verified via official extension page + GitHub source); MEDIUM for pagination conditional patterns (community-verified, consistent with docs); LOW for hx-include behavior during polling (official docs are silent; behavior inferred from HTMX request mechanics and community reports)

---

## Context: What Already Exists (Do Not Re-Research)

Existing validated stack:
- HTMX 2.0.4 loaded in `templates/base.html` from unpkg CDN
- htmx-ext-sse 2.2.4 loaded in `templates/base.html` from jsDelivr CDN
- SSE endpoint at `/feed/station` — FastAPI `EventSourceResponse`, asyncio.Queue `ConnectionManager`, MongoDB change stream (`watch_qsos()`)
- `/log/view` endpoint: paginated, filterable, sortable — returns full page or HTMX partial based on `HX-Request` header
- `#log-table` div in `templates/log/log.html` holds the `log_table.html` partial
- Filter form (`#filter-form`) uses `hx-get="/log/view"` with `hx-target="#log-table"` and `hx-push-url="true"`
- SSE already used for the station feed in `templates/log/form.html`: `hx-ext="sse"` + `sse-connect="/feed/station"` + `sse-swap="new_qso"` + `hx-swap="afterbegin"` on `<tbody id="station-feed">`
- `watch_qsos()` in `app/feed/manager.py` broadcasts `event="new_qso"` SSE events on each QSO insert

---

## The Recommended Approach: SSE-Triggered Re-Fetch (Not Polling, Not Row Injection)

**Verdict: Use `hx-trigger="sse:new_qso"` on the `#log-table` container to fire an HTTP GET to `/log/view` when a new QSO arrives. Only fire when on page 1 with no active filters. No new dependencies.**

Three approaches were evaluated. The recommendation follows from analyzing how the existing log table works:

| Approach | How It Works | Verdict for This App |
|----------|-------------|----------------------|
| **Polling** (`hx-trigger="every Ns"`) | Element re-fetches `/log/view` on a timer | Viable but wasteful — fires even when nothing changed; parameter persistence requires URL-baking workaround |
| **SSE direct row injection** (`sse-swap` on `tbody`) | SSE event content swapped directly into `<tbody>` `afterbegin` | Wrong for a paginated table — injects a raw row without enrichment (no flag lookup, no proper dict context), breaks page counts, works only on the station feed pattern (already done in `form.html`) |
| **SSE-triggered re-fetch** (`hx-trigger="sse:new_qso"`) | SSE event fires an HTTP GET to re-render the full `log_table.html` partial | **Correct for this use case** — re-renders with full flag enrichment, accurate totals, no raw row injection, uses existing `/log/view` endpoint unchanged |

The SSE-triggered re-fetch is the right approach because:
1. The existing `ConnectionManager` already broadcasts `new_qso` events — no backend changes needed
2. `/log/view` already returns an HTMX partial on `HX-Request` — no endpoint changes needed
3. The re-rendered partial includes flag enrichment (`lookup_prefix()`) that raw SSE row injection cannot provide
4. Pagination state (total count, page numbers) is always accurate after a re-fetch
5. The conditional filter (only refresh on page 1, no active filters) is a single JS expression in the trigger

---

## Specific Question Answers

### Q1: HTMX `hx-trigger="every Ns"` polling — does hx-include work without user interaction?

**Yes, hx-include re-reads the DOM on every poll cycle.** HTMX evaluates `hx-include` selectors at request time, capturing current form field values each time the poll fires. This is confirmed by HTMX's `hx-include` documentation: "values are captured at request time" and "evaluated from the element triggering the request."

However, polling for this use case has a practical problem: form filter params must be embedded in the polling element's `hx-get` URL at render time, not via `hx-include`. The Django community confirmed this pattern (see Sources). When a user changes a filter, the polling div's `hx-get` URL does not automatically update to reflect new filter values — the URL was baked in at server-render time. Using `hx-include="#filter-form"` on a polling element would re-read the form values each cycle, but this is fragile: if the user is mid-edit on a filter field, a poll mid-keystroke would fire with half-typed values.

**Polling is viable but the SSE-triggered re-fetch avoids all of this complexity.**

Polling conditional filter syntax (documented, HIGH confidence):
```html
<div hx-get="/log/view?page=1"
     hx-trigger="every 10s [window.__logAutoRefresh]"
     hx-target="#log-table"
     hx-swap="innerHTML">
</div>
```

Polling can be disabled from the server by responding with HTTP `286` — HTMX will stop the poll on that status code.

### Q2: htmx-ext-sse 2.2.4 `sse-swap` for inserting rows into an existing `tbody`

**This works but is the wrong approach for the log table. Use it only for the station feed (already done).**

The syntax for `sse-swap` direct row injection on a `tbody`:
```html
<div hx-ext="sse" sse-connect="/feed/station">
  <tbody id="log-tbody" sse-swap="new_qso" hx-swap="afterbegin">
  </tbody>
</div>
```

`sse-swap="new_qso"` listens for SSE events named `new_qso`. The event data (HTML) replaces or inserts into the target element using `hx-swap` positioning. `afterbegin` prepends new rows before existing rows (newest first). `beforeend` appends (oldest first).

**Important caveats for the log table:**

1. The SSE event data in `watch_qsos()` is rendered from `log/feed_row.html` — a simplified template with different field names (`call`, `band`, `mode`, `freq`, `operator`) vs the log table's `qso_row.html` (`qso.CALL`, `qso.BAND`, etc. with flag enrichment and action buttons). Injecting feed rows into the log table would produce malformed rows.

2. `<tr>` elements cannot be parsed standalone by the browser's HTML parser outside a table context. HTMX 2.x handles this correctly for `hx-swap-oob` via `htmx.config.useTemplateFragments = true` (wrapping in `<template>` tags), but for `sse-swap` the extension receives the raw SSE event data as HTML and does a direct swap. If the target is already a `<tbody>`, direct `<tr>` injection via `sse-swap="afterbegin"` works correctly in practice because the browser parser sees the `<tbody>` context.

3. The station feed (`form.html`) already uses this pattern correctly — `<tbody id="station-feed" sse-swap="new_qso" hx-swap="afterbegin">` works because it is a display-only feed using `feed_row.html`, not the full `qso_row.html`.

**Do not replicate the station feed pattern into `log_table.html`.** Use the SSE-triggered re-fetch instead.

### Q3: Which approach handles pagination gracefully?

**SSE-triggered re-fetch is the only approach that handles pagination gracefully when the guard condition is applied.**

| Approach | Page 2 behavior | Page 1 behavior | Filter-active behavior |
|----------|----------------|-----------------|------------------------|
| Polling | Refreshes page 2 to page 2 (if URL is baked correctly); disorienting | Refreshes correctly | Refreshes with filter applied |
| SSE row injection | Prepends a row regardless of page — shows QSOs that shouldn't be visible on current view | Adds a row not yet counted in pagination | Breaks filter semantics (shows unfiltered rows in filtered view) |
| SSE re-fetch (recommended) | **Conditional guard prevents firing at all on page > 1** | Re-fetches page 1, accurate counts | **Conditional guard prevents firing when filters active** |

The correct behavior for a live log table:
- **On page 1, no filters, default sort:** auto-refresh when a new QSO arrives
- **On page > 1 or with active filters:** do not auto-refresh (user is navigating/investigating; disrupting this with a reset to page 1 is worse than missing live updates)

### Q4: "Only refresh when on default view" — the conditional guard pattern

**Use a JS expression filter on `hx-trigger` that reads hidden inputs or data attributes rendered server-side.**

The HTMX polling conditional filter syntax is confirmed as working (HIGH confidence — official docs):
```
hx-trigger="sse:new_qso [<javascript expression>]"
```

The JS expression is evaluated in the global scope when the trigger fires. It can reference any DOM query.

**Pattern for "only on default view":**

Server renders a hidden marker in `log_table.html` or `log.html` when the view is at defaults:
```html
<!-- rendered by server only when page=1, no filters, sort=-qso_date_utc -->
<span id="auto-refresh-ok" hidden></span>
```

HTMX trigger on the log table container:
```html
<div id="log-table"
     hx-ext="sse"
     sse-connect="/feed/station"
     hx-get="/log/view"
     hx-trigger="sse:new_qso [!!document.getElementById('auto-refresh-ok')]"
     hx-target="#log-table"
     hx-swap="innerHTML">
  {% include "log/log_table.html" %}
</div>
```

When the server renders `log_table.html` with page=1 and no filters, it includes the `#auto-refresh-ok` marker. When filters are active or page > 1, the marker is absent. The JS expression `!!document.getElementById('auto-refresh-ok')` returns `false` when the marker is absent, suppressing the re-fetch.

**Alternative without a hidden marker:** Read page and filter state from URL params or existing hidden form inputs. But a server-rendered marker is simpler and removes JS logic from the conditional expression.

---

## Implementation Summary

### No New Dependencies

All capability is available in the existing stack:
- HTMX 2.0.4: `hx-trigger="sse:new_qso [condition]"` — built-in
- htmx-ext-sse 2.2.4: `hx-ext="sse"` + `sse-connect` — already loaded
- `/feed/station` SSE endpoint: already exists, already broadcasting `new_qso`
- `/log/view` partial response: already exists (returns `log_table.html` on `HX-Request`)

### Required Template Changes

1. **`templates/log/log.html`** — move `hx-ext="sse"` and `sse-connect` to the `#log-table` container div; add `hx-get`, `hx-trigger`, `hx-target`, `hx-swap` attributes for the re-fetch
2. **`templates/log/log_table.html`** — add server-conditional `<span id="auto-refresh-ok" hidden>` when rendering at defaults (page=1, no filters, sort=-qso_date_utc)

### Required Backend Changes

None. The existing `/feed/station` SSE endpoint and `/log/view` endpoint are fully reusable.

### Attribute Syntax Reference

**On `#log-table` div in `log.html`:**
```html
<div id="log-table"
     hx-ext="sse"
     sse-connect="/feed/station"
     hx-get="/log/view"
     hx-trigger="sse:new_qso [!!document.getElementById('auto-refresh-ok')]"
     hx-target="#log-table"
     hx-swap="innerHTML">
```

**In `log_table.html` (server-conditional):**
```html
{% if page == 1 and not filters.call and not filters.band and not filters.mode and not filters.date_from and not filters.date_to and sort == '-qso_date_utc' %}
<span id="auto-refresh-ok" hidden></span>
{% endif %}
```

**Key attribute notes for HTMX 2.0.4 (HIGH confidence):**
- `hx-trigger="sse:<event-name>"` is the documented SSE trigger syntax for htmx-ext-sse 2.2.4
- The `[condition]` filter after the trigger name is standard HTMX conditional filter syntax — same as `every Ns [condition]`
- `hx-swap="innerHTML"` on `#log-table` replaces the partial content, preserving the container div (which holds the SSE connection)
- `hx-ext="sse"` and `sse-connect` on `#log-table` establishes one SSE connection for the log view page; the station feed on `form.html` has its own separate SSE connection

---

## Alternative: hx-trigger with Named SSE Event (Clarification on Two Modes)

htmx-ext-sse 2.2.4 supports two distinct modes — important to understand both:

| Mode | Attribute pattern | What happens |
|------|------------------|-------------|
| **Direct content swap** | `sse-swap="new_qso"` + `hx-swap="afterbegin"` | SSE event data (HTML) is directly inserted into the DOM. No HTTP request fired. Used for station feed. |
| **SSE-triggered HTTP request** | `hx-trigger="sse:new_qso"` + `hx-get="/log/view"` | SSE event fires an HTMX HTTP GET. Response replaces target. Used for log table re-fetch. |

These two modes are mutually exclusive on the same element. The log table needs the second mode (HTTP request re-fetch). The station feed uses the first mode (direct injection). Both can share the same SSE connection if they are nested under the same `hx-ext="sse"` parent, but for simplicity the log view page should have its own `sse-connect` on `#log-table`.

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `sse-swap="new_qso"` on `<tbody>` in `log_table.html` | Injects raw `feed_row.html` content (wrong template, no flags, no action buttons) directly into the paginated log table | `hx-trigger="sse:new_qso"` triggering a full re-fetch |
| Polling (`hx-trigger="every 10s"`) | Fires even when no new QSOs exist; filter param persistence requires URL-baking at render time; wasteful for a table that can already receive event-driven signals | SSE-triggered re-fetch using the existing `new_qso` event |
| JavaScript WebSocket or EventSource client code | No JS needed — htmx-ext-sse 2.2.4 is already loaded and handles the SSE connection declaratively | `hx-ext="sse"` + `sse-connect` attributes |
| A new SSE endpoint for the log view | `/feed/station` already broadcasts `new_qso` events; no reason to create a second endpoint that broadcasts the same signal | Reuse `/feed/station` — the SSE event is just a trigger signal, not the data payload |
| Auto-refresh on page > 1 or with active filters | Resetting user to page 1 mid-navigation is disorienting and likely unwanted | Conditional guard via `[!!document.getElementById('auto-refresh-ok')]` |

---

## Version Compatibility

| Component | Version | Confirmed Compatible |
|-----------|---------|---------------------|
| htmx | 2.0.4 | YES — `hx-trigger="sse:<name>"` syntax confirmed in official docs for htmx 2.x |
| htmx-ext-sse | 2.2.4 | YES — both `sse-swap` (direct) and `hx-trigger="sse:"` (HTTP request) modes supported |
| FastAPI | 0.135+ | YES — `EventSourceResponse` is built into `fastapi.sse` since FastAPI 0.115 |
| Python | 3.14 | YES — no Python-version-specific concerns; all async patterns are stdlib |

---

## Sources

- [HTMX hx-trigger Attribute (official docs, htmx.org)](https://htmx.org/attributes/hx-trigger/) — `every Ns` syntax, conditional filter `[expression]` after trigger name, `every Ns [condition]` confirmed pattern. HIGH confidence.
- [HTMX hx-include Attribute (official docs, htmx.org)](https://htmx.org/attributes/hx-include/) — "values captured at request time", selector types. HIGH confidence (behavior during polling: MEDIUM, docs silent on this specific question).
- [HTMX hx-swap Attribute (official docs, htmx.org)](https://htmx.org/attributes/hx-swap/) — `afterbegin`, `beforeend`, `innerHTML` swap modes confirmed. HIGH confidence.
- [htmx-ext-sse Extension (official docs, htmx.org)](https://htmx.org/extensions/sse/) — `sse-connect`, `sse-swap`, `hx-trigger="sse:<name>"` syntax, two-mode clarification. HIGH confidence.
- [htmx-ext-sse source (GitHub, bigskysoftware/htmx)](https://github.com/bigskysoftware/htmx/blob/master/www/content/extensions/sse.md) — extension documentation including `sse-swap` vs `hx-trigger sse:` distinction. HIGH confidence.
- [Django Forum: Polling table with active filters](https://forum.djangoproject.com/t/how-can-i-implement-polling-the-table-and-keep-the-filter-applied-to-it-django-filter-htmx/18465) — confirms URL-baking approach for polling with filters; `hx-include` not sufficient for polling filter persistence. MEDIUM confidence (community source verified against HTMX docs).
- [HTMX issue #1198: hx-swap-oob with table row fragments](https://github.com/bigskysoftware/htmx/issues/1198) — `<tr>` DOM parsing constraints, `htmx.config.useTemplateFragments` for OOB swaps. MEDIUM confidence.
- [Real-time Notification Streaming using SSE and HTMX (Medium)](https://medium.com/@soverignchriss/real-time-notification-streaming-using-sse-and-htmx-32798b5b2247) — confirms `hx-swap="afterbegin"` on SSE container for prepend. MEDIUM confidence (community tutorial, consistent with docs).
- Existing codebase (`templates/log/form.html`, `app/feed/router.py`, `app/feed/manager.py`, `app/qso/ui_router.py`) — direct inspection of working SSE implementation and `/log/view` endpoint. HIGH confidence.

---

*Stack research for: Live QSO auto-refresh for paginated log table milestone (ollog)*
*Researched: 2026-04-08*
