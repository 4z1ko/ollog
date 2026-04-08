# Phase 23: SSE-Triggered Log Table Reload - Research

**Researched:** 2026-04-08
**Domain:** HTMX SSE extension, Jinja2 template guards, browser EventSource lifecycle
**Confidence:** HIGH

## Summary

This phase is a pure template change — 2 files, no backend work, no new dependencies. The
infrastructure is already in place: `/feed/station` emits `new_qso` events, htmx 2.0.4 and
htmx-ext-sse 2.2.4 are loaded globally in `base.html`, and the `#log-table` div survives all
HTMX swaps (its `innerHTML` is replaced, but the element itself is not).

The implementation hinges on two orthogonal guards: a server-rendered sentinel span that only
appears when the view is in its default state (page 1, no filters, default sort), and an inline
JS filter expression on `hx-trigger` that checks both that sentinel and the absence of an active
edit row. Because the SSE extension delegates trigger processing to htmx's own `htmx.trigger()`
call, htmx's standard `[condition]` filter syntax applies to `sse:` events.

The Live indicator is wired to `htmx:sseOpen` and `htmx:sseError` / `htmx:sseClose` events
dispatched by the extension on the SSE host element (`#log-table` after the change).

**Primary recommendation:** Add SSE attributes directly to `#log-table` in `log.html`, insert
the sentinel span at the top of `log_table.html` under a Jinja2 guard, and add a small Live
indicator badge in `log.html` wired via vanilla JS to `htmx:sseOpen` / `htmx:sseError`.

---

## Existing Code — Exact State

### `log.html` — `#log-table` current form (line 82-84)

```html
<div id="log-table">
  {% include "log/log_table.html" %}
</div>
```

This is the swap TARGET for all pagination/filter/sort HTMX requests. The div itself is never
replaced; only its `innerHTML` changes. Any attributes placed on this div survive those swaps.

### `log_table.html` — default values available in template context

From `ui_router.py` `log_view()`:

| Variable | Default | "Default state" value |
|----------|---------|----------------------|
| `page` | `1` (Query ge=1) | `1` |
| `sort` | `"-qso_date_utc"` (Query default) | `"-qso_date_utc"` |
| `filters.call` | `""` | `""` |
| `filters.band` | `""` | `""` |
| `filters.mode` | `""` | `""` |
| `filters.date_from` | `""` | `""` |
| `filters.date_to` | `""` | `""` |

All filter variables are already present in `log_table.html` (used for pagination links). The
sentinel guard condition in Jinja2 is therefore:

```
page == 1
and sort == '-qso_date_utc'
and not filters.call
and not filters.band
and not filters.mode
and not filters.date_from
and not filters.date_to
```

### `qso_row_edit.html` — edit row class inspection

The edit template renders `<tr id="qso-{{ qso.id }}">` with NO `.editing` class. There is no
`class="editing"` or `class="editing ..."` anywhere in `qso_row_edit.html`. The distinction
between view-mode and edit-mode rows is that the edit row contains `<input>` elements.

**Consequence for the JS guard:** `document.querySelector('tr.editing')` will NEVER match
because no `editing` class is set. The correct selector must target the actual difference:
input elements inside the table body — i.e., `document.querySelector('#log-table input')`.
This detects any open inline edit row without relying on a CSS class.

---

## Architecture Patterns

### Pattern 1: SSE Attributes on the Persistent Container

The `#log-table` div is never destroyed by HTMX swaps (it is the target, not the swapped
content), so SSE attributes placed on it establish one long-lived EventSource connection for
the page lifetime.

```html
<div id="log-table"
     hx-ext="sse"
     sse-connect="/feed/station"
     hx-trigger="sse:new_qso [!!document.getElementById('auto-refresh-ok') && !document.querySelector('#log-table input')]"
     hx-get="/log/view"
     hx-include="#filter-form"
     hx-target="#log-table"
     hx-swap="innerHTML">
  {% include "log/log_table.html" %}
</div>
```

**Why `hx-include="#filter-form"`:** The filter form holds the current filter + sort state in its
input values. Including it ensures the auto-reload re-fetches exactly the same filtered view the
operator is on (though the guard prevents auto-reload when non-default state is active, this is
defence-in-depth and keeps the mechanism correct).

**Why `hx-get="/log/view"` (no params):** With `hx-include="#filter-form"`, HTMX serialises the
form; adding params would conflict. The server sees them as query params either way.

### Pattern 2: Server-Rendered Sentinel Span

Insert at the TOP of `log_table.html` (before the `{% if not qsos %}` block):

```html
{% if page == 1 and sort == '-qso_date_utc' and not filters.call and not filters.band and not filters.mode and not filters.date_from and not filters.date_to %}
<span id="auto-refresh-ok" hidden></span>
{% endif %}
```

This span is present in `#log-table`'s innerHTML only when the view is in its default state. On
pagination, filter, or sort change, the server re-renders `log_table.html` without the span, so
the JS guard `!!document.getElementById('auto-refresh-ok')` evaluates to `false` and auto-
refresh is suppressed.

Because `hx-swap="innerHTML"` replaces the entire innerHTML of `#log-table`, the sentinel span
is atomically present or absent after every swap.

### Pattern 3: Live Indicator with SSE Lifecycle Events

The extension fires these events on the SSE host element (`#log-table` after the change):

| Event | When fired |
|-------|-----------|
| `htmx:sseOpen` | EventSource `onopen` callback — connection established |
| `htmx:sseError` | EventSource `onerror` callback — connection error or drop |
| `htmx:sseClose` | Explicit close (node missing/replaced, or `sse-close` message) |

The Live indicator is a `<span>` in `log.html` (outside `#log-table` so it survives swaps)
wired with vanilla JS:

```html
<!-- place near the "Filters" card heading or in nav -->
<span id="live-indicator" style="display:none;font-size:0.8rem;padding:0.2rem 0.5rem;border-radius:4px;background:#1e8449;color:white;">LIVE</span>

<script>
  document.addEventListener('htmx:sseOpen', function(e) {
    if (e.target.id === 'log-table') {
      document.getElementById('live-indicator').style.display = '';
    }
  });
  document.addEventListener('htmx:sseError', function(e) {
    if (e.target.id === 'log-table') {
      var el = document.getElementById('live-indicator');
      el.style.background = '#c0392b';
      el.textContent = 'OFFLINE';
      el.style.display = '';
    }
  });
  document.addEventListener('htmx:sseClose', function(e) {
    if (e.target.id === 'log-table') {
      document.getElementById('live-indicator').style.display = 'none';
    }
  });
</script>
```

**Placement:** The indicator `<span>` goes in the nav row alongside the callsign display, or in
the Filters card heading row, both of which are outside `#log-table`.

### Reconnection Behaviour (htmx-ext-sse 2.2.4)

The extension implements exponential backoff reconnection on top of browser-native SSE
reconnection:

- On error: `delay = Math.max(Math.min(retryCount * 2, 128), 1) * 500` ms (500 ms to 64 s)
- On successful reconnect: retry counter resets to 0
- Child SSE listeners are re-registered after reconnect

The browser's native `EventSource` also reconnects automatically. The extension's logic
augments this for cases where the source is explicitly closed on error.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reconnection logic | Custom EventSource wrapper | htmx-ext-sse (already loaded) | Exponential backoff already implemented |
| Long-poll fallback | Custom polling endpoint | n/a — SSE is sufficient | EventSource reconnects automatically |
| Guard state machine | JS class toggling | Server-rendered sentinel span + JS filter | Simpler, survives innerHTML swaps atomically |

---

## Common Pitfalls

### Pitfall 1: Using `tr.editing` class selector for edit guard

**What goes wrong:** `document.querySelector('tr.editing')` always returns `null` — the edit
row template (`qso_row_edit.html`) does NOT add any `editing` class to the `<tr>`.

**Why it happens:** The prior milestone research assumed a `.editing` class convention without
verifying the template.

**How to avoid:** Use `document.querySelector('#log-table input')` to detect any open edit row.
An edit row always contains `<input>` elements; a view row never does.

**Warning signs:** Auto-refresh fires while an edit row is open, destroying unsaved data.

### Pitfall 2: JS filter expression not applied for SSE triggers

**What goes wrong:** Developer assumes `sse:new_qso [condition]` silently ignores the condition.

**Reality (verified via source):** The SSE extension calls `htmx.trigger(elt, ts.trigger, event)`,
delegating to htmx's standard trigger machinery, which DOES parse and evaluate `[condition]`
filter expressions via `maybeFilterEvent()`. The filter works correctly.

**Confidence:** MEDIUM — inferred from source code analysis, not an official documented feature.

**Warning signs:** If the condition is never evaluated, try an explicit `htmx:sseMessage`
listener approach as fallback (see Open Questions).

### Pitfall 3: Placing SSE attributes on a child element that gets swapped out

**What goes wrong:** Attributes placed on a `<table>` or any element inside `#log-table` are
destroyed when the innerHTML is replaced, closing the EventSource.

**How to avoid:** SSE attributes MUST be on `#log-table` itself (the swap target div), not on
any of its children.

### Pitfall 4: `hx-include` sending stale filter values during auto-refresh

**What goes wrong:** At the moment the SSE event fires, the `#filter-form` contains the current
filter values. If the operator has typed something in a filter input but not submitted yet, the
auto-refresh will submit those in-progress values.

**Mitigation:** The guard prevents auto-refresh when any filter is active (as reported by the
server). An in-progress filter value that has not yet been submitted does not change the server-
rendered sentinel, so the guard correctly suppresses auto-refresh only after the user submits a
filter. This is acceptable behaviour.

### Pitfall 5: Live indicator lives inside `#log-table`

**What goes wrong:** Placing the indicator inside `#log-table` means it is wiped out on every
auto-refresh and must be re-rendered by the server.

**How to avoid:** Place the `<span id="live-indicator">` outside `#log-table` in `log.html`.

---

## Code Examples

### Full `#log-table` div after changes
```html
<div id="log-table"
     hx-ext="sse"
     sse-connect="/feed/station"
     hx-trigger="sse:new_qso [!!document.getElementById('auto-refresh-ok') && !document.querySelector('#log-table input')]"
     hx-get="/log/view"
     hx-include="#filter-form"
     hx-target="#log-table"
     hx-swap="innerHTML">
  {% include "log/log_table.html" %}
</div>
```

### Sentinel span insertion point in `log_table.html` (insert at line 1, before existing content)
```html
{% if page == 1 and sort == '-qso_date_utc' and not filters.call and not filters.band and not filters.mode and not filters.date_from and not filters.date_to %}
<span id="auto-refresh-ok" hidden></span>
{% endif %}
```

### Live indicator markup for `log.html` (nav area)
```html
<span id="live-indicator" style="display:none;font-size:0.8rem;padding:0.2rem 0.5rem;border-radius:4px;background:#1e8449;color:white;font-weight:600;letter-spacing:0.03em;">LIVE</span>
```

### Live indicator script for `log.html` (after `#log-table` div, before `{% endblock %}`)
```html
<script>
  (function() {
    var indicator = document.getElementById('live-indicator');
    document.addEventListener('htmx:sseOpen', function(e) {
      if (e.target && e.target.id === 'log-table') {
        indicator.style.background = '#1e8449';
        indicator.textContent = 'LIVE';
        indicator.style.display = '';
      }
    });
    document.addEventListener('htmx:sseError', function(e) {
      if (e.target && e.target.id === 'log-table') {
        indicator.style.background = '#c0392b';
        indicator.textContent = 'OFFLINE';
        indicator.style.display = '';
      }
    });
    document.addEventListener('htmx:sseClose', function(e) {
      if (e.target && e.target.id === 'log-table') {
        indicator.style.display = 'none';
      }
    });
  })();
</script>
```

---

## Feed Route Confirmation

`/feed/station` (source: `app/feed/router.py`):

- Event name: `new_qso` (confirmed — `yield ServerSentEvent(data=html, event="new_qso")`)
- Auth: cookie JWT via `get_current_operator_callsign_cookie` — operator-scoped, no QSO data
  leaks across operators
- The endpoint does NOT filter by operator on the emit side; it broadcasts to all connected
  clients. Operator isolation is enforced by the re-fetch to `/log/view` which uses the
  authenticated operator's callsign to filter QSOs.

---

## Open Questions

1. **Does `hx-trigger="sse:new_qso [condition]"` actually evaluate the filter?**
   - What we know: htmx-ext-sse 2.2.4 calls `htmx.trigger(elt, ts.trigger, event)` where
     `ts.trigger` is the raw string `"sse:new_qso"` (the extension strips `[condition]` from
     its own parsing, but passes the trigger name). The filter expression is parsed by
     `getTriggerSpecs()` and stored on the trigger spec before the SSE extension runs.
   - What's unclear: Whether `htmx.trigger()` looks up the stored spec to evaluate the filter,
     or fires unconditionally since the event is already normalised to `"sse:new_qso"` without
     the bracket.
   - Recommendation: Verify empirically during implementation. **Fallback approach** if filter
     does not evaluate: listen to `htmx:sseMessage` in a `<script>` block and call
     `htmx.ajax('GET', '/log/view', {target:'#log-table', swap:'innerHTML', ...})` only when
     guards pass. This is pure JS and avoids the ambiguity entirely.

2. **`htmx:sseOpen` target — is it `#log-table` or `document.body`?**
   - What we know: The extension dispatches `htmx:sseOpen` via `api.triggerEvent(sourceElement, ...)`.
     `sourceElement` is the element that has `hx-ext="sse"` — which will be `#log-table`.
   - Recommendation: Guard the indicator listeners with `e.target.id === 'log-table'` as shown
     above. This is safe even if the event bubbles.

---

## Sources

### Primary (HIGH confidence)
- `app/feed/router.py` — confirmed event name `new_qso`, operator-scoped auth
- `app/qso/ui_router.py` — confirmed default params: `page=1`, `sort="-qso_date_utc"`, all
  filter defaults `None`/`""`
- `templates/log/log.html` — confirmed exact current `#log-table` HTML (lines 82-84)
- `templates/log/log_table.html` — confirmed Jinja2 variables available, no existing sentinel
- `templates/log/qso_row_edit.html` — confirmed NO `.editing` class on edit `<tr>`
- `templates/base.html` — confirmed htmx 2.0.4 and htmx-ext-sse 2.2.4 already loaded globally
- https://cdn.jsdelivr.net/npm/htmx-ext-sse@2.2.4/dist/sse.js — source code analysis:
  confirmed `htmx:sseOpen`, `htmx:sseError`, `htmx:sseClose` event names; confirmed
  `htmx.trigger(elt, ts.trigger, event)` delegation; confirmed exponential backoff reconnection

### Secondary (MEDIUM confidence)
- https://htmx.org/extensions/sse/ — confirmed lifecycle events, reconnection, basic trigger syntax
- https://unpkg.com/htmx.org@2.0.4/dist/htmx.js — confirmed `maybeFilterEvent()` evaluates
  `[condition]` expressions; filter parsing lives in `getTriggerSpecs()` / `maybeGenerateConditional()`

### Tertiary (LOW confidence)
- JS filter expressions working with `sse:` triggers in practice — inferred from code path, not
  an officially documented feature. Treat as needing empirical verification.

---

## Metadata

**Confidence breakdown:**
- Feed route / event name: HIGH — read from source
- Template context variables: HIGH — read from source
- Edit row class: HIGH — read from source (no `.editing` class exists; selector must change)
- SSE lifecycle event names: HIGH — verified from extension source
- JS filter on SSE trigger: MEDIUM — inferred from code path, not official documentation
- Live indicator approach: HIGH — standard DOM event pattern

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (htmx-ext-sse is stable; htmx 2.x API is stable)
