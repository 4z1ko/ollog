---
phase: 43-stats-ui
reviewed: 2026-04-16T13:48:09Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - templates/base.html
  - templates/base_app.html
  - templates/log/stats.html
  - static/css/output.css
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 43: Code Review Report

**Reviewed:** 2026-04-16T13:48:09Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

This review covers the Stats UI additions from phase 43: a new `{% block extra_scripts %}` slot in the base template, a new Stats nav entry in the app shell, and the stats page itself with three Chart.js pie charts rendered from server-side JSON. The `static/css/output.css` is a Tailwind-compiled artifact and was reviewed to confirm that classes used by the new templates are present.

The two warnings are both in `templates/log/stats.html`. One is a correctness bug (Jinja2 block-inside-if does not suppress block rendering), the other is a missing guard on a variable that is present in the header even when `total_qsos == 0`. No security issues were found; `| tojson` is used for all server-side data injected into JavaScript, which is the correct escaping strategy.

---

## Warnings

### WR-01: `{% block extra_scripts %}` inside `{% if total_qsos > 0 %}` — block is always rendered

**File:** `templates/log/stats.html:70-133`

**Issue:** In Jinja2 template inheritance, `{% block %}` definitions are resolved at compile time, not at render time. The surrounding `{% if total_qsos > 0 %}` conditional is ignored when the engine processes block inheritance — the block override takes effect unconditionally, regardless of the `if` branch. This means the Chart.js `<script>` tag and all three `makeChart` calls are injected into the page even when the user has zero QSOs and the canvas elements do not exist.

Confirmed by running Jinja2 directly: rendering the child template with `total_qsos=0` still produces `<script>SCRIPTS</script>` in the output.

The practical consequence: when `total_qsos == 0`, `Chart` is loaded over the network (unnecessary bandwidth), and `makeChart` is called. `makeChart` guards on `if (!canvas) return` so there is no JS crash — but `Chart.getChart(canvas)` is never reached, so the dead script path could confuse future maintainers or cause breakage if the guard is ever removed.

**Fix:** Move the `{% if %}` guard inside the block, not outside it:

```jinja2
{% block extra_scripts %}
{% if total_qsos > 0 %}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
<script>
  /* ... chart code unchanged ... */
</script>
{% endif %}
{% endblock %}
```

With this structure the block always overrides its parent, but its rendered content is empty when `total_qsos == 0`. The block must remain outside `{% block content %}` (its current position, after `{% endblock %}` for content) so it renders in `<body>` after the main content — that placement is correct; only the if-guard needs to be moved inward.

---

### WR-02: `unique_entity_count` rendered in card header when `total_qsos == 0` is guarded, but the variable is not supplied in the empty-log return path — confirm service contract

**File:** `templates/log/stats.html:58`

**Issue:** The card header reads:

```html
<h2 class="card-title">By DXCC Entity &middot; {{ unique_entity_count }} entities</h2>
```

This line is inside the `{% else %}` branch of `{% if total_qsos == 0 %}`, so it only renders when there are QSOs. The service layer's early-return path for an empty log does return `unique_entity_count: 0`, so the variable is always present in the template context regardless of which branch is taken. The guard is correct and there is no crash risk.

However, the Summary card only shows `Total QSOs` and does not show `Unique DXCC entities` in the summary block — that count appears only in the DXCC card header. If a user glances at the Summary card expecting a complete overview, the entity count is not visible there. This is a design inconsistency: the old template (pre-phase-43) showed both metrics in the summary block. This may be intentional per the UI-SPEC, but is noted because it diverges from the previous behavior and could be a regression.

**Fix (if regression):** Add the entity count line back to the Summary card body:

```html
<div class="card-body">
  <p class="text-gray-700 dark:text-gray-300">Total QSOs: {{ total_qsos }}</p>
  <p class="text-gray-700 dark:text-gray-300">Unique DXCC entities: {{ unique_entity_count }}</p>
</div>
```

If the UI-SPEC explicitly calls for entity count only in the DXCC chart header, this finding can be closed as-designed.

---

## Info

### IN-01: No `integrity` / `crossorigin` attributes on CDN script tags

**File:** `templates/base.html:35-36`, `templates/log/stats.html:72`

**Issue:** The three CDN-loaded scripts (htmx, htmx-ext-sse, chart.js) are loaded without Subresource Integrity (SRI) hashes. If the CDN is compromised or the URL is hijacked, arbitrary JavaScript can run in every operator's browser session (which holds a live auth cookie).

```html
<!-- base.html — no integrity= attributes -->
<script src="https://unpkg.com/htmx.org@2.0.4"></script>
<script src="https://cdn.jsdelivr.net/npm/htmx-ext-sse@2.2.4/dist/sse.js"></script>

<!-- stats.html — no integrity= attribute -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
```

This is a self-hosted application; the operator is responsible for their own threat model. For a LAN-only deployment the risk is low. Flagged as Info because SRI is best practice and the fix is straightforward.

**Fix:** Generate SRI hashes (e.g. `openssl dgst -sha384 -binary chart.umd.min.js | openssl base64 -A`) and add `integrity="sha384-..."  crossorigin="anonymous"` to each `<script>` tag. Alternatively, vendor the scripts into `static/js/`.

---

### IN-02: `reinitCharts` is an unnecessary indirection

**File:** `templates/log/stats.html:128`

**Issue:** `reinitCharts` is defined as a one-line wrapper that calls `initCharts` with no additional logic:

```javascript
function reinitCharts() { initCharts(); }
```

It is referenced once, as the `themechange` event handler. There is no reason for the wrapper to exist; the handler can reference `initCharts` directly.

**Fix:**

```javascript
window.addEventListener('themechange', initCharts);
```

---

_Reviewed: 2026-04-16T13:48:09Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
