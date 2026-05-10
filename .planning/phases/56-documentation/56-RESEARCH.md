# Phase 56: Documentation - Research

**Researched:** 2026-05-10
**Domain:** MkDocs Material documentation authoring
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Add `## Danger Zone` section at the bottom of `docs/operator-guide/profile.md`. No nav change. Content: where to find it (profile page), what it does (permanently deletes all your QSOs), the password confirmation step, and the permanence warning.
- **D-02:** Append `## Clear Operator Log` section to `docs/admin-guide/account-management.md`, after the existing `## Reset a User's Password` section.
- **D-03:** Use MkDocs Material admonition blocks for permanence warnings — `!!! danger "This cannot be undone"`. Both operator and admin sections use this style.
- **D-04:** The ROADMAP file paths `docs/getting-started.md` and `docs/admin.md` are stale. Actual targets are `docs/operator-guide/profile.md` (DOC-01) and `docs/admin-guide/account-management.md` (DOC-02).

### Claude's Discretion

- Exact prose wording for the step-by-step instructions in each section
- Whether to use numbered steps or prose paragraphs (numbered steps match the existing getting-started style)
- Exact admonition wording (must convey: permanent deletion, no UI recovery, backups are the only recovery path)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DOC-01 | Operator getting-started guide updated with a "Clear my log" section explaining the Danger Zone flow and password confirmation | Profile template confirms Danger Zone section exists at bottom of profile page; operator modal template confirms password-confirmation step and count display |
| DOC-02 | Admin guide updated with "Clear operator log" instructions including the admin-password confirmation step | Admin users_table template confirms "Clear log" button exists per-operator row; admin modal template confirms admin-password confirmation and operator callsign display |
| DOC-03 | MkDocs site rebuilt and `site/` committed to repo | Build verified: `uv run mkdocs build --strict` completes with zero warnings on current docs; admonition extension must be added to `mkdocs.yml` for `!!!` syntax to render |
</phase_requirements>

## Summary

Phase 56 is a documentation-only phase. Two existing Markdown files get new sections appended; one `mkdocs.yml` configuration change enables admonition rendering; and the `site/` directory is rebuilt and committed.

The most significant technical finding is that MkDocs Material admonitions (`!!! danger`) require the `admonition` entry under `markdown_extensions` in `mkdocs.yml`. The current project `mkdocs.yml` has no `markdown_extensions` block at all. Without this addition, the `!!!` syntax is rendered as literal text, not an admonition block. This is a blocking prerequisite for D-03.

The current docs codebase uses numbered steps as its standard step-by-step pattern (see `docs/getting-started/first-qso.md`). Both new sections should follow the same numbered-step style since they each document a sequential UI flow.

**Primary recommendation:** Add `markdown_extensions: [admonition]` to `mkdocs.yml` before writing the new sections, verify with a build, then append sections to the two target files.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Operator clear-log documentation | Static docs (MkDocs) | — | UI-only feature; no API endpoint; prose steps are sufficient |
| Admin clear-log documentation | Static docs (MkDocs) | — | UI-only feature on admin web console; prose steps sufficient |
| Site rebuild | Build tool (MkDocs CLI) | — | `uv run mkdocs build --strict` compiles Markdown to `site/` HTML |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mkdocs | 1.6.1 | Static site generator | Project standard [VERIFIED: `uv run mkdocs --version`] |
| mkdocs-material | 9.7.6 | Material theme | Project standard in `pyproject.toml` [VERIFIED: `uv pip show mkdocs-material`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mkdocs-swagger-ui-tag | >=0.8.0 | OpenAPI interactive docs | Already in use; not needed for this phase |

**Key dependency:** The `admonition` markdown extension is part of Python-Markdown (stdlib-equivalent for MkDocs). It requires no new package install — only a `mkdocs.yml` configuration entry. [VERIFIED: tested locally]

**Installation:** No new packages required.

## Architecture Patterns

### System Architecture Diagram

```
docs/operator-guide/profile.md   ─────┐
docs/admin-guide/account-management.md ─┤
mkdocs.yml (admonition extension)   ──┤── uv run mkdocs build --strict ──► site/ (committed)
(existing docs unchanged)           ──┘
```

### Recommended Project Structure

No structural changes. Two existing files are appended; `mkdocs.yml` gains one block; `site/` is regenerated.

```
docs/
├── operator-guide/
│   └── profile.md          # Append ## Danger Zone section (DOC-01)
└── admin-guide/
    └── account-management.md  # Append ## Clear Operator Log section (DOC-02)
mkdocs.yml                  # Add markdown_extensions: [admonition]
site/                       # Rebuilt and committed (DOC-03)
```

### Pattern 1: MkDocs Material Admonition (danger type)

**What:** Renders a styled callout block with an icon and title.
**When to use:** Any permanently destructive action warning.

```markdown
!!! danger "This cannot be undone"
    This action permanently deletes all QSOs. There is no undo and no recovery from the UI.
    If you need to recover deleted QSOs, restore from a backup.
```

**Required mkdocs.yml entry (blocking prerequisite):**

```yaml
markdown_extensions:
  - admonition
```

[VERIFIED: tested with mkdocs-material 9.x locally — without this entry `!!!` renders as plain text]

### Pattern 2: Numbered Steps (existing docs style)

**What:** Numbered list for sequential UI flows.
**When to use:** Any walkthrough of a UI interaction (matches `first-qso.md` style).

```markdown
1. Navigate to your profile page.
2. Scroll to the **Danger Zone** section at the bottom.
3. Click **Clear my log**.
4. A confirmation modal appears showing the number of QSOs that will be deleted.
5. Enter your password and click **Delete N QSOs**.
```

[VERIFIED: pattern observed in `docs/getting-started/first-qso.md` lines 33–42]

### Anti-Patterns to Avoid

- **Omitting `markdown_extensions: admonition` from mkdocs.yml:** The `!!!` syntax silently renders as plain text, not a styled block. There is no build warning. The only detection is visual inspection of the built HTML.
- **Adding new nav entries:** No new pages are created; `mkdocs.yml` nav requires no changes (per D-01, D-02).
- **Documenting the REST API:** Both clear-log features are UI-only. No curl examples are needed (per code_context in CONTEXT.md).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Permanence warning callout | Custom HTML/CSS block | MkDocs Material `!!! danger` admonition | Theme handles styling, dark mode, icon — consistent with Material design system |

## Common Pitfalls

### Pitfall 1: Admonition Not Rendering

**What goes wrong:** `!!! danger` appears as literal text in the rendered HTML.
**Why it happens:** `admonition` must be listed under `markdown_extensions` in `mkdocs.yml`. The current project `mkdocs.yml` has no `markdown_extensions` block.
**How to avoid:** Add the block before writing the new doc sections. Verify by building and grepping the HTML output for `class="admonition danger"`.
**Warning signs:** Built HTML contains `!!! danger` as a paragraph instead of a div with class `admonition`.

### Pitfall 2: mkdocs build --strict failing on existing not_in_nav pages

**What goes wrong:** Build exits non-zero due to pages present in `docs/` but absent from nav.
**Why it happens:** `--strict` promotes all warnings to errors. The current project has legacy stub files (`admin-guide.md`, `getting-started.md`, etc.) that exist in the docs directory but are excluded via `not_in_nav` in `mkdocs.yml`.
**How to avoid:** Do not remove or modify the existing `not_in_nav` block in `mkdocs.yml`. Verified current build is clean (zero warnings on `--strict`).
**Warning signs:** `WARNING - Doc file ... is not found in the docs directory` or similar.

### Pitfall 3: Appending in the Wrong Location

**What goes wrong:** `## Clear Operator Log` section is added somewhere other than after `## Reset a User's Password` in `account-management.md`.
**Why it happens:** D-02 specifies explicit placement to maintain consistent action grouping on the admin operators page.
**How to avoid:** Append after the Reset Password section's closing content (the paragraph ending "...a password reset does not immediately revoke active sessions.").

## Code Examples

### Operator Profile: Danger Zone Section

Full section to append to `docs/operator-guide/profile.md`:

```markdown
## Danger Zone

The **Danger Zone** section appears at the bottom of your profile page.

To clear your log:

1. Navigate to **Profile** in the navigation bar.
2. Scroll to the **Danger Zone** section at the bottom of the page.
3. Click **Clear my log**.
4. A confirmation modal opens showing the number of QSOs that will be deleted.
5. Enter your password and click **Delete N QSOs** to confirm.

!!! danger "This cannot be undone"
    Clearing your log permanently deletes all your QSOs. There is no undo and no recovery from the UI. If you need to recover deleted QSOs, restore from a backup.
```

Note: Exact prose wording is Claude's discretion per CONTEXT.md. The above is illustrative; the planner may refine it.

### Admin Guide: Clear Operator Log Section

Full section to append to `docs/admin-guide/account-management.md` (after Reset a User's Password):

```markdown
## Clear Operator Log

Admins can permanently delete all QSOs for any operator from the operators management page.

1. In the admin web UI, navigate to the **Operators** management page.
2. Find the operator whose log you want to clear.
3. Click the **Clear log** button (trash icon) in that operator's row.
4. A confirmation modal opens showing the operator's callsign and QSO count.
5. Enter your admin password and click **Delete N QSOs** to confirm.

!!! danger "This cannot be undone"
    Clearing an operator's log permanently deletes all their QSOs. There is no undo and no recovery from the UI. If you need to recover deleted QSOs, restore from a backup.
```

Note: Exact prose wording is Claude's discretion per CONTEXT.md. The above is illustrative.

### mkdocs.yml: Add admonition Extension

```yaml
markdown_extensions:
  - admonition
```

This block is added to `mkdocs.yml` (it has no `markdown_extensions` entry currently). Place it after the `plugins:` block.

[VERIFIED: locally confirmed renders `class="admonition danger"` in built HTML]

### Build and Verify Commands

```bash
# Build with strict mode (zero warnings required by DOC-03)
uv run mkdocs build --strict

# Verify admonition rendered (not plain text)
grep -r 'class="admonition danger"' site/operator-guide/profile/
grep -r 'class="admonition danger"' site/admin-guide/account-management/
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw HTML warning blocks | MkDocs Material `!!! danger` admonitions | This phase (first use in project) | Consistent styled callouts; theme handles dark mode |

**Deprecated/outdated:**

- `docs/getting-started.md` and `docs/admin.md` — stale empty stub files present in `docs/` but NOT in nav (excluded via `not_in_nav`). These are the paths mentioned in the original ROADMAP success criteria. Per D-04, they are NOT the targets for this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Numbered steps match the "existing getting-started style" | Architecture Patterns | Low — verified directly in `docs/getting-started/first-qso.md` lines 33–42; tagged HIGH confidence |

**All other claims in this research were verified via tool calls against the local codebase and build environment.**

## Open Questions

None. All required information was deterministically available in the local codebase.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | Running mkdocs | Yes | (project standard) | — |
| mkdocs | DOC-03 build | Yes | 1.6.1 | — |
| mkdocs-material | DOC-03 admonitions | Yes | 9.7.6 | — |
| Python-Markdown admonition extension | D-03 admonition rendering | Yes (bundled with Python-Markdown) | N/A | — |

**Missing dependencies with no fallback:** None.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` (`[tool.hatch.build.targets.wheel]`) |
| Quick run command | `uv run mkdocs build --strict` (doc build is the test) |
| Full suite command | `uv run pytest tests/` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOC-01 | `docs/operator-guide/profile.md` contains a `## Danger Zone` section with password confirmation and permanence language | Content verification (grep) | `grep -n "Danger Zone" docs/operator-guide/profile.md` | Edit of existing file |
| DOC-02 | `docs/admin-guide/account-management.md` contains a `## Clear Operator Log` section after Reset Password | Content verification (grep) | `grep -n "Clear Operator Log" docs/admin-guide/account-management.md` | Edit of existing file |
| DOC-03 | `uv run mkdocs build --strict` exits 0 with zero warnings; `site/` committed | Build gate | `uv run mkdocs build --strict` | Build artifact |

### Sampling Rate

- **Per task commit:** `uv run mkdocs build --strict`
- **Per wave merge:** `uv run mkdocs build --strict`
- **Phase gate:** `uv run mkdocs build --strict` green before `/gsd-verify-work`

### Wave 0 Gaps

None — no test files to create. The MkDocs build itself is the automated verification. Existing pytest suite does not cover documentation content (intentionally — doc content is verified by human review and build success).

## Security Domain

Not applicable. This phase writes static documentation Markdown files only. No code paths, authentication, input handling, or data access are modified.

## Sources

### Primary (HIGH confidence)

- Local codebase: `mkdocs.yml` — confirmed no `markdown_extensions` block present
- Local codebase: `docs/operator-guide/profile.md` — confirmed current content and append point
- Local codebase: `docs/admin-guide/account-management.md` — confirmed current content and append point
- Local codebase: `templates/log/clear_log_modal.html` — operator modal UX (password field, count display)
- Local codebase: `templates/admin/clear_log_modal.html` — admin modal UX (admin password, callsign display)
- Local codebase: `templates/admin/users_table.html` — confirms "Clear log" button placement in per-operator row
- Local codebase: `templates/log/profile.html` lines 224–244 — confirms Danger Zone section at bottom of profile page
- Local build verification: `uv run mkdocs build --strict` — zero warnings on current docs [VERIFIED]
- Local build verification: admonition extension test — confirmed `admonition` in `markdown_extensions` required for `!!!` syntax [VERIFIED]

### Secondary (MEDIUM confidence)

- `docs/getting-started/first-qso.md` lines 33–42 — numbered step pattern observation

### Tertiary (LOW confidence)

None.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — versions verified via `uv pip show` and `uv run mkdocs --version`
- Architecture: HIGH — all target files and template files read directly
- Pitfalls: HIGH — admonition rendering behavior verified with local build test
- Content patterns: HIGH — existing doc style observed from source files

**Research date:** 2026-05-10
**Valid until:** 2026-06-10 (stable toolchain; docs files won't change before planning)
