---
phase: 68
slug: admin-log-configuration-and-viewer
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-19
verified: 2026-06-19
---

# Phase 68 — Security

> Per-phase security verification for the admin application log viewer reconciliation.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Admin browser ↔ admin UI routes | Authenticated admin interacts with `/admin/ui/logs`, `/admin/ui/logs/settings`, and `/admin/ui/logs/events`. | Admin cookie, filter/query values, rendered internal log records, SSE log events |
| Internal logger ↔ MongoDB | Sanitized log records are stored and queried through Beanie/MongoDB. | Operational log metadata/error objects, timestamps, source names, event details |
| Server-rendered templates ↔ browser DOM | Jinja renders log rows and details; client JavaScript inserts live rows. | Escaped text, formatted JSON strings, SSE payload fields |
| HTMX pagination/filter swaps ↔ live SSE updates | HTMX replaces the logs table while the SSE stream remains open. | Current filter state, page links, live row insertions |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-68-01 | Spoofing / Information Disclosure | `/admin/ui/logs` and `/admin/ui/logs/events` | mitigate | Both the Logs page and SSE stream keep `admin: User = Depends(require_admin_cookie)` / `_admin: User = Depends(require_admin_cookie)`, preserving server-side admin auth on full, HTMX, and live routes. | closed |
| T-68-02 | Information Disclosure | Formatted metadata/error details | mitigate | Phase 68 formats the already-sanitized `log.metadata` and `log.error` values via `_log_row_context()` and `format_log_detail()`; it does not query raw source records or bypass `sanitize_metadata()` / `error_details()` from the logger. | closed |
| T-68-03 | Tampering / XSS | Server-rendered and live metadata/error rows | mitigate | Server rows render `{{ log.metadata_json }}` / `{{ log.error_json }}` without `safe`; live rows pass message, context, metadata, and error strings through `escapeHtml()` before `insertAdjacentHTML()`. | closed |
| T-68-04 | Information Disclosure | Pagination links and HTMX requests | mitigate | `_logs_query()` preserves only active `level`, `source`, `search`, `date_from`, and `date_to` filters, uses `urlencode()`, and pagination links reuse those query strings for `href` and `hx-get`. | closed |
| T-68-05 | Information Disclosure | Live SSE row insertion | mitigate | `matchesFilters(log)` still checks level/source/search/date filters before insertion; UAT fixes added `currentLogTableBody()` and `parseLogEventData()` so live rows render into the current HTMX table with real event data. | closed |

---

## Verification Evidence

| Threat | Evidence |
|--------|----------|
| T-68-01 | `app/admin/ui_router.py` keeps `require_admin_cookie` on `logs_page()` and `logs_events()`; no unauthenticated log-view or live-stream route was added. |
| T-68-02 | `app/internal_logs/service.py` keeps `sanitize_metadata()`, `error_details()`, and `log_to_dict()` as the data path; `format_log_detail()` only serializes provided sanitized values with `json.dumps(..., default=str)`. |
| T-68-03 | `templates/admin/log_row.html` uses normal Jinja escaping for JSON details; `templates/admin/logs.html` uses `escapeHtml()` for all live row text inserted through HTML strings. |
| T-68-04 | `app/admin/ui_router.py` builds `previous_query` and `next_query` with `urlencode()` from the known filter allowlist; `tests/test_internal_logs.py` verifies active filters persist in pagination context. |
| T-68-05 | `templates/admin/logs.html` applies `matchesFilters(log)` before live insertion; UAT found and fixed stale-table/payload parsing bugs in commits `42d84df` and `1723d35`; `tests/test_internal_logs.py` now checks current table-body lookup and string-wrapped payload parsing. |

---

## Accepted Risks Log

No accepted risks.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-19 | 5 | 5 | 0 | Codex inline security audit |

## Notes

- Phase 68 did not expand log access beyond existing admin-only routes.
- The UAT-discovered live-update bugs were reliability issues with security relevance because stale or malformed live rendering could undermine filter expectations; both were fixed and retested before this audit was finalized.
- No `safe` template rendering or raw metadata source re-fetch was introduced.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-19
