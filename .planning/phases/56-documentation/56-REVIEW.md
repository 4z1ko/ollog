---
phase: 56-documentation
reviewed: 2026-05-11T00:00:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - docs/admin-guide/account-management.md
  - docs/operator-guide/profile.md
  - mkdocs.yml
findings:
  critical: 0
  warning: 1
  info: 1
  total: 2
status: issues_found
---

# Phase 56: Code Review Report

**Reviewed:** 2026-05-11
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three files were reviewed: two documentation pages (`account-management.md`, `profile.md`) and the MkDocs site configuration (`mkdocs.yml`). The review cross-referenced documentation claims against the actual source code in `app/admin/router.py`, `app/admin/ui_router.py`, `app/qso/service.py`, `app/config.py`, and `docs/reference/environment-variables.md`.

The admin account management page and the mkdocs.yml are accurate. One factual inaccuracy was found in the operator profile page: it references a `STATION_CALLSIGN` environment variable that does not exist in the codebase. One informational note covers a mkdocs plugin declared in configuration whose dependency is not verifiable from in-scope files.

## Warnings

### WR-01: Nonexistent `STATION_CALLSIGN` Environment Variable Referenced

**File:** `docs/operator-guide/profile.md:84-86`

**Issue:** The "STATION_CALLSIGN Environment Variable" section states:

> The `STATION_CALLSIGN` environment variable on the server is not the same as the profile field. The env var is used as a system-level default if the operator's profile has no `station_callsign` set.

No `STATION_CALLSIGN` environment variable exists in `app/config.py` (which defines all recognized env vars via `pydantic_settings.BaseSettings`). The reference document at `docs/reference/environment-variables.md` also has no entry for `STATION_CALLSIGN`. The only system-level station callsign mechanism available is the profile field on each operator's `User` document; there is no server-wide env var fallback.

This section misleads operators into believing they can set a server-wide default station callsign via environment variable when no such mechanism exists. An operator or admin reading this may spend time troubleshooting a nonexistent feature.

**Fix:** Remove the section entirely, or replace it with a note that there is no server-wide `STATION_CALLSIGN` environment variable — the only way to set a default is via the profile `station_callsign` field. Example replacement:

```markdown
## System-Level Default

There is no server-wide `STATION_CALLSIGN` environment variable. The profile
`station_callsign` field is the only way to set a default station callsign.
Each operator configures their own value independently.
```

## Info

### IN-01: `swagger-ui-tag` Plugin Dependency Not Verifiable from In-Scope Files

**File:** `mkdocs.yml:18-20`

**Issue:** The `swagger-ui-tag` MkDocs plugin is declared in `plugins:` but the plugin dependency (`mkdocs-swagger-ui-tag`) is not visible in any in-scope file. If this package is missing from the documentation build dependencies, `uv run mkdocs build --strict` will fail with a plugin-not-found error.

This is low risk if the dependency is declared in `pyproject.toml` (not in review scope), but is worth confirming.

**Fix:** Verify that `mkdocs-swagger-ui-tag` appears in the project's documentation dependencies (e.g., in `pyproject.toml` under `[dependency-groups]` or a `docs` extras group). No change needed if it is already declared there.

---

_Reviewed: 2026-05-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
