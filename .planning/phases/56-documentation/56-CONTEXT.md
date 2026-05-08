# Phase 56: Documentation — Context

**Gathered:** 2026-05-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Document the clear-log features shipped in Phases 54 and 55. Two docs updates, one MkDocs rebuild with `site/` committed. No new features, no nav restructuring, no new pages.

</domain>

<decisions>
## Implementation Decisions

### Operator "Clear my log" doc location
- **D-01:** Add a `## Danger Zone` section at the bottom of `docs/operator-guide/profile.md`. No nav change required. Content: where to find it (profile page), what it does (permanently deletes all your QSOs), the password confirmation step, and the permanence warning.

### Admin "Clear operator log" doc location
- **D-02:** Append a `## Clear Operator Log` section to `docs/admin-guide/account-management.md`, after the existing `## Reset a User's Password` section. Consistent with Enable/Disable and Reset Password which are all actions on the same admin operators page.

### Warning style
- **D-03:** Use MkDocs Material admonition blocks for permanence warnings — `!!! danger "This cannot be undone"`. This is the first use of admonitions in the docs and sets a pattern for future destructive-action warnings. Both sections (operator and admin) should use this style.

### ROADMAP file path correction
- **D-04:** The ROADMAP success criteria references `docs/getting-started.md` and `docs/admin.md` — both are stale empty files not in the mkdocs nav. The actual targets are `docs/operator-guide/profile.md` (DOC-01) and `docs/admin-guide/account-management.md` (DOC-02). Downstream agents should use these paths, not the ROADMAP paths.

### Claude's Discretion
- Exact prose wording for the step-by-step instructions in each section
- Whether to use numbered steps or prose paragraphs (numbered steps match the existing getting-started style)
- Exact admonition wording (must convey: permanent deletion, no UI recovery, backups are the only recovery path)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing docs to modify
- `docs/operator-guide/profile.md` — Add `## Danger Zone` section at bottom (DOC-01)
- `docs/admin-guide/account-management.md` — Append `## Clear Operator Log` section after Reset Password (DOC-02)

### MkDocs configuration
- `mkdocs.yml` — No nav changes needed (no new pages). MkDocs Material admonition syntax requires no plugin beyond the theme.

### Feature implementation (read to understand what to document)
- `templates/log/clear_log_modal.html` — Operator-facing modal (Phase 54): what the user sees
- `templates/admin/clear_log_modal.html` — Admin-facing modal (Phase 55): what the admin sees
- `app/qso/ui_router.py` — Operator route: GET modal, POST confirm, GET cancel
- `app/admin/ui_router.py` — Admin routes: same pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Established doc patterns
- All existing operator-guide and admin-guide docs use prose + code blocks (curl examples for REST API sections)
- The clear-log sections are UI-only — no curl examples needed, just prose steps
- MkDocs Material admonitions are supported by the theme but unused in current docs — `!!! danger`, `!!! warning`, `!!! note` are all valid

### Integration points
- `docs/operator-guide/profile.md` — append at end of file
- `docs/admin-guide/account-management.md` — append at end of file
- `site/` — rebuilt by `uv run mkdocs build --strict`; committed to repo so `/guide` in the running app serves updated content

</code_context>

<specifics>
## Specific Requirements

- ROADMAP success criteria 1 (`docs/getting-started.md`) → resolved to `docs/operator-guide/profile.md` per D-04
- ROADMAP success criteria 2 (`docs/admin.md`) → resolved to `docs/admin-guide/account-management.md` per D-04
- Both sections must explicitly state deletion is permanent and cannot be recovered from the UI

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 56-documentation*
*Context gathered: 2026-05-08*
