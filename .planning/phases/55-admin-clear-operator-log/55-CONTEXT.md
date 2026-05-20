# Phase 55: Admin Clear Operator Log - Context

**Gathered:** 2026-05-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a per-operator "Clear log" action to the admin operators management page. When clicked, a modal opens showing the target operator's callsign, their QSO count, and an admin password field. Correct admin password → permanently delete all the target operator's QSOs + inline success fragment. Wrong password → inline error, modal stays open. Zero-QSO path handled without error.

This phase does NOT touch the operator-facing clear-log flow (Phase 54), the admin backup/restore feature, or any other admin page.

</domain>

<decisions>
## Implementation Decisions

### Row Action Layout
- **D-01:** The "Clear log" button is placed **inline with the existing row actions** — same `flex flex-wrap items-center gap-2` div as Enable/Disable and Reset Password. No separate row or visual section needed.
- **D-02:** Button copy is **"Clear log"** — matches the feature name used in ROADMAP.md and requirements throughout.
- **D-03:** Button style follows the existing row danger action convention: `btn-danger btn-sm` (same as the Disable button).

### Claude's Discretion
- **Cancel mechanism:** Use the admin restore pattern — a server-side cancel endpoint returns an empty `<div id="admin-clear-log-modal"></div>` to clear the modal without a page reload. This is consistent with the established admin modal pattern in `templates/admin/restore/password_modal.html`.
- **Post-success feedback:** After successful deletion, replace the modal with an inline success fragment (same approach as Phase 54 `clear_log_success.html`) — no table reload. The users table does not display QSO counts, so a table refresh adds no value.
- **Duplicate-ID fix:** The admin page uses distinct IDs to avoid the WR-01 pattern from Phase 54. Use `id="admin-clear-log-modal"` for both the placeholder div and the fragment outer wrapper (no separate "placeholder" ID needed — the fragment `outerHTML` swap correctly replaces the placeholder when they share the same ID, as long as the placeholder is OUTSIDE the table so `outerHTML` doesn't disturb the table rows).
- **Username routing:** Pass the target operator username via URL path param — `GET /admin/ui/users/{username}/clear-log/modal` and `POST /admin/ui/users/{username}/clear-log` — consistent with the existing `/toggle` and `/reset-password` route pattern.
- **Service reuse:** Call `clear_operator_log(target_user.callsign)` from `app/qso/service` — already ships from Phase 54. Admin auth uses the admin's own `user.hashed_password` (not the target operator's).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 54 artifacts (reuse and consistency)
- `app/qso/service.py` — `clear_operator_log(operator: str) -> int` already exists; use directly
- `templates/log/clear_log_success.html` — success fragment pattern to mirror for the admin success fragment
- `.planning/phases/54-operator-clear-log/54-01-PLAN.md` — HTMX fragment contracts (id wrappers, status_code=200 rule)
- `.planning/phases/54-operator-clear-log/54-02-PLAN.md` — route handler pattern (password verify gate, service call only after verify)

### Admin existing patterns (modify/extend)
- `app/admin/ui_router.py` — existing route handlers; new routes append at end of file
- `templates/admin/users_table.html` — operator row structure; add "Clear log" button inline in the actions flex div
- `templates/admin/restore/password_modal.html` — modal HTMX structure to mirror (outerHTML swap, server-side cancel)
- `templates/admin/restore/restore_success.html` — success fragment pattern in admin context

### Requirements
- `.planning/REQUIREMENTS.md` — ACLR-01 through ACLR-05

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `clear_operator_log(operator: str) -> int` in `app/qso/service.py` — bulk delete, already handles operator isolation and returns deleted count
- `require_admin_cookie` dependency in `app/admin/ui_router.py` — admin auth gate for all new routes
- `verify_password(password, user.hashed_password)` in `app/auth/service.py` — already imported in admin router
- `.modal-backdrop`, `.modal-box`, `.modal-title`, `.modal-body`, `.modal-actions`, `.btn-danger`, `.btn-secondary`, `.btn-sm`, `.form-control`, `.alert-error`, `.alert-success` — all compiled into `static/css/output.css`, no new CSS needed

### Established Patterns
- Admin routes follow `@ui_router.{method}("/users/{username}/action")` — append new handlers at end of `app/admin/ui_router.py`
- Admin modals use `hx-swap="outerHTML"` on a target div outside the table — prevents swap from disrupting table rows
- All admin HTMX response branches return `status_code=200` — HTMX 2.x drops body on 4xx
- Table partial updates use `hx-target="#users-table-body"` + `hx-swap="innerHTML"` — not needed here (no table refresh on success)

### Integration Points
- New "Clear log" button in `templates/admin/users_table.html` row actions — `hx-get="/admin/ui/users/{{ user.username }}/clear-log/modal"` targeting `#admin-clear-log-modal` with `hx-swap="innerHTML"`
- New `<div id="admin-clear-log-modal"></div>` placeholder in `templates/admin/users.html` — placed OUTSIDE the `<tbody>` element so outerHTML swap doesn't disturb table rows
- New GET + POST handlers in `app/admin/ui_router.py` — import `clear_operator_log` from `app.qso.service` (already there for Phase 54)

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the standard patterns — open to standard HTMX modal approach mirroring the admin restore flow.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 55-admin-clear-operator-log*
*Context gathered: 2026-05-07*
