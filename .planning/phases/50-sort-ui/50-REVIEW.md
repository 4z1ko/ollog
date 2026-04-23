---
phase: 50-sort-ui
reviewed: 2026-04-23T00:00:00Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - templates/log/log_table.html
  - static/css/output.css
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 50: Code Review Report

**Reviewed:** 2026-04-23
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

This review covers `templates/log/log_table.html` after Phase 50 added a sortable
MODE column, restructured the DATE header as a dual-link flex wrapper
(date sort + clock/`_created_at` sort), and added inactive hollow chevron
indicators to CALL and BAND headers. `static/css/output.css` is a
Tailwind-generated build artifact; it is present and noted but not reviewed
line-by-line. The build gate (`npm run verify`) should confirm `dark:opacity-25`
appears in the compiled output — that check is outside the scope of this review.

The sort toggle logic, filter preservation, and HTMX wiring are correct. The MODE
ascending-first toggle, the DATE header restructure, and the inactive chevron
indicators for all four columns all match the phase spec. Two warnings and three
info items are noted below.

---

## Warnings

### WR-01: Unescaped filter values in hx-get URL construction

**File:** `templates/log/log_table.html:29, 43, 62, 78, 94, 135, 152`

Every sort link and pagination link constructs its `hx-get` URL by interpolating
filter values directly from the template context:

```html
hx-get="/log/view?sort=...&call={{ filters.call or '' }}&band={{ filters.band or '' }}&mode={{ filters.mode or '' }}&date_from={{ filters.date_from or '' }}&date_to={{ filters.date_to or '' }}"
```

Jinja2 auto-escape HTML-encodes `<`, `>`, `"`, `&`, and `'` in attribute context,
which prevents XSS attribute breakout. However, Jinja2 does **not** URL-encode
characters such as space, `+`, or `#` that are legal in HTML but alter URL
semantics when the attribute is interpreted as a URL.

The practical consequence: if a filter value (e.g. a callsign fragment) contains
`%` or `+` these are passed through verbatim and may be double-decoded or
mis-parsed by the browser before HTMX builds the XHR. More significantly, a value
containing `&sort=-CALL` renders to the HTML attribute as `&amp;sort=-CALL`,
which the browser's DOM parser decodes back to `&sort=-CALL` — a second sort
parameter — before passing it to HTMX, allowing a user to inject extra query
parameters into the request. The backend allowlist in `service.py:218` validates
`sort` and ignores invalid values, and filter fields use `re.escape()` for the
callsign regex, so there is no server-side exploitation path today. But the
client-side URL construction is incorrect and will cause subtle breakage for any
filter value containing URL-special characters.

**Fix:** Apply `|urlencode` to each filter value at the interpolation site:

```html
hx-get="/log/view?sort={{ next_sort }}&call={{ filters.call|urlencode }}&band={{ filters.band|urlencode }}&mode={{ filters.mode|urlencode }}&date_from={{ filters.date_from|urlencode }}&date_to={{ filters.date_to|urlencode }}"
```

Alternatively, pre-encode a `filter_qs` string in the router and pass it through
the template context:

```python
# In ui_router.py, inside log_view():
from urllib.parse import urlencode
ctx["filter_qs"] = urlencode({k: v for k, v in filters.items() if v})
```

Then in the template:
```html
hx-get="/log/view?sort={{ next_sort }}&{{ filter_qs }}"
```

---

### WR-02: Clock icon sort link has no accessible label

**File:** `templates/log/log_table.html:42–57`

The `_created_at` sort link in the DATE header contains only SVG elements — no
visible text, no `aria-label`, no `title`:

```html
<a class="inline-flex items-center gap-1 hover:text-indigo-400 transition-colors cursor-pointer"
   hx-get="/log/view?sort={% if sort == '-_created_at' %}_created_at{% else %}-_created_at{% endif %}..."
   hx-target="#log-table"
   hx-swap="innerHTML"
   hx-push-url="true">
  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" ...>...</svg>
  {% if sort == '-_created_at' %}
  <svg ...chevron-down.../>
  ...
  {% endif %}
</a>
```

Screen readers announce this as an unlabelled link. Keyboard users tabbing through
the table header receive no context for what this control does. The other sort
links ("Date / Time UTC", "Callsign", "Band", "Mode") are self-describing through
visible text; only the icon-only clock link is affected.

**Fix:** Add `aria-label` to the `<a>` and `aria-hidden="true"` to all decorative
child SVGs:

```html
<a class="inline-flex items-center gap-1 hover:text-indigo-400 transition-colors cursor-pointer"
   aria-label="Sort by log entry time"
   hx-get="..."
   hx-target="#log-table"
   hx-swap="innerHTML"
   hx-push-url="true">
  <svg class="w-4 h-4" aria-hidden="true" fill="none" viewBox="0 0 24 24" ...>...</svg>
  {% if sort == '-_created_at' %}
  <svg class="w-3 h-3" aria-hidden="true" fill="currentColor" ...>...</svg>
  ...
  {% endif %}
</a>
```

---

## Info

### IN-01: Sort `<a>` elements without `href` are not keyboard-focusable

**File:** `templates/log/log_table.html:28, 42, 61, 77, 93`

All five sort link `<a>` elements have no `href` attribute. An `<a>` without
`href` is not in the tab order by default in most browsers and is not announced as
an interactive element by screen readers. HTMX handles click events correctly, but
keyboard-only users cannot reach these controls via Tab.

**Fix:** Add `href="#"` to each sort link. HTMX still intercepts the click before
navigation occurs, and `hx-push-url="true"` updates the address bar as designed.
The `cursor-pointer` class (see IN-02) becomes redundant after this change:

```html
<a href="#"
   class="inline-flex items-center gap-1 hover:text-indigo-400 transition-colors"
   hx-get="..."
   hx-target="#log-table"
   hx-swap="innerHTML"
   hx-push-url="true">
```

---

### IN-02: `cursor-pointer` on sort `<a>` elements is masking a missing `href`

**File:** `templates/log/log_table.html:28, 42, 61, 77, 93`

`cursor-pointer` is applied to all five sort `<a>` elements. Anchor elements
display a pointer cursor automatically when they have an `href`; adding
`cursor-pointer` explicitly is the symptom of `href` being absent (see IN-01).
Resolving IN-01 by adding `href="#"` makes `cursor-pointer` redundant and it can
be removed.

---

### IN-03: Auto-refresh guard is a manual allowlist with no explanatory comment

**File:** `templates/log/log_table.html:1`

```jinja
{% if page == 1 and (sort == '-qso_date_utc' or sort == '-_created_at') and not filters.call and not filters.band and not filters.mode and not filters.date_from and not filters.date_to %}
```

The logic is correct: SSE auto-refresh is gated to newest-first views on page 1
with no active filters, so that new QSOs appear at the top and the live update
makes sense. However, the allowed sort values are a hardcoded list with no
comment explaining the guard's intent. A future developer adding a new
"newest-first" sort field would need to know to update this line.

**Fix:** Add a brief comment before the guard:

```jinja
{# Enable SSE auto-refresh only on newest-first unfiltered page 1 views,
   where new QSOs naturally appear at the top of the table. #}
{% if page == 1 and (sort == '-qso_date_utc' or sort == '-_created_at') and not filters.call ... %}
```

---

_Reviewed: 2026-04-23_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
