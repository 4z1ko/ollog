# Phase 56: Documentation — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-08
**Phase:** 56-documentation
**Areas discussed:** Operator doc location, Admin doc placement, Warning style

---

## Operator doc location

| Option | Description | Selected |
|--------|-------------|----------|
| operator-guide/profile.md | Add Danger Zone section at bottom; no nav change needed | ✓ |
| getting-started/ new step | Add Step 9 to quickstart; matches ROADMAP wording but out of place for new users | |
| New operator-guide/log-management.md | Dedicated page; clean but requires nav entry and extra scope | |

**User's choice:** operator-guide/profile.md
**Notes:** ROADMAP references stale `docs/getting-started.md`; actual target confirmed as `docs/operator-guide/profile.md`.

---

## Admin doc placement

| Option | Description | Selected |
|--------|-------------|----------|
| admin-guide/account-management.md | Append after Reset Password; consistent with Enable/Disable and Reset Password sections on same page | ✓ |
| New admin-guide/log-management.md | Separate page; adds nav entry and scope — overkill for a single section | |

**User's choice:** admin-guide/account-management.md
**Notes:** ROADMAP references stale `docs/admin.md`; actual target confirmed as `docs/admin-guide/account-management.md`.

---

## Warning style

| Option | Description | Selected |
|--------|-------------|----------|
| MkDocs admonition (!!! danger) | First use of admonitions; prominent red panel; sets pattern for destructive-action warnings | ✓ |
| Bold prose paragraph | Consistent with existing docs; less visually prominent | |

**User's choice:** MkDocs admonition — `!!! danger "This cannot be undone"`
**Notes:** First admonition in the docs; applies to both operator and admin sections.

---

## Claude's Discretion

- Exact prose wording for step-by-step instructions
- Numbered steps vs prose paragraphs
- Exact admonition text (must cover: permanent, no UI recovery, backups only)
