# Phase 56: Documentation - Pattern Map

**Mapped:** 2026-05-10
**Files analyzed:** 3 (2 Markdown docs modified, 1 YAML config modified)
**Analogs found:** 3 / 3

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `docs/operator-guide/profile.md` | docs | append/transform | `docs/getting-started/first-qso.md` | role-match (same numbered-step style, same prose+no-curl pattern) |
| `docs/admin-guide/account-management.md` | docs | append/transform | `docs/admin-guide/account-management.md` existing sections (Enable/Disable, Reset Password) | exact (same file, same action-section pattern) |
| `mkdocs.yml` | config | transform | `mkdocs.yml` existing `plugins:` block | partial (same file, adding a parallel top-level block) |

## Pattern Assignments

### `docs/operator-guide/profile.md` (docs, append)

**Analog:** `docs/getting-started/first-qso.md` (numbered-step UI walkthrough)
**Append point:** End of file, after the `## STATION_CALLSIGN Environment Variable` section (line 87).

**Numbered-step pattern** (`docs/getting-started/first-qso.md` lines 33-42):
```markdown
1. Click **Log QSO** in the navigation bar.
2. Fill in the form:
   - **Callsign** — the station you worked (e.g., `DL1ABC`)
   - **Band** — e.g., `20m`
   - **Mode** — e.g., `SSB`
   - **RST Sent / Received** — signal reports
3. Date and time default to now (UTC). Adjust if logging a past QSO.
4. Click **Submit**.
```

**Section heading style** (`docs/operator-guide/profile.md` line 7, 16, 45, 73, 84):
```markdown
## Auto-Stamping Behavior
## Get Profile
## Update Profile
### Clearing a Field
## STATION_CALLSIGN Environment Variable
```

**Full section to append** (sourced from RESEARCH.md Code Examples, refined against template evidence):

The operator modal (`templates/log/clear_log_modal.html`) confirms:
- Button label is "Clear my log" (line 235 of `templates/log/profile.html`)
- Modal shows QSO count (line 9 of clear_log_modal.html: "{{ count }} QSO(s)")
- Password field label is "Your password" (line 18 of clear_log_modal.html)
- Confirm button reads "Delete N QSOs" (line 25 of clear_log_modal.html)
- Cancel button reads "Keep my log" (line 28 of clear_log_modal.html)

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
    Clearing your log permanently deletes all your QSOs. There is no undo and no
    recovery from the UI. If you need to recover deleted QSOs, restore from a backup.
```

---

### `docs/admin-guide/account-management.md` (docs, append)

**Analog:** Same file — existing `## Enable / Disable an Account` and `## Reset a User's Password` sections (lines 54-78). These are the closest pattern because they document UI-available actions on the operators page using prose + code blocks.

**Action-section pattern** (`docs/admin-guide/account-management.md` lines 69-78):
```markdown
## Reset a User's Password

```bash
curl -X POST http://localhost:8000/admin/users/op1/reset-password \
  ...
```

Returns `200 OK` with `{"username": "op1", "password_reset": true}`. The new password takes
effect immediately. The user's existing tokens remain valid until they expire — a password reset
does not immediately revoke active sessions.
```

**Append point:** After line 78 (end of `## Reset a User's Password` section).

**Note:** The new section has NO curl example — it is UI-only per CONTEXT.md `code_context`. The existing Reset Password section has a curl block because Reset Password has a REST endpoint; Clear Operator Log does not.

The admin modal (`templates/admin/clear_log_modal.html`) confirms:
- Modal title is "Clear {{ callsign }}'s Log" (line 3)
- Shows operator callsign (line 9: "for {{ callsign }}")
- Password field label is "Your admin password" (line 20)
- Confirm button reads "Delete N QSOs" (line 28)
- Cancel button reads "Keep log" (line 31)

The users table (`templates/admin/users_table.html`) confirms:
- "Clear log" button is in the per-operator row actions column (lines 80-93)
- Button triggers HTMX GET to `/admin/ui/users/{username}/clear-log/modal`

**Full section to append:**
```markdown
## Clear Operator Log

Admins can permanently delete all QSOs for any operator from the operators management page.
This action is available in the admin web UI only — there is no REST API endpoint for it.

1. In the admin web UI, navigate to the **Operators** management page.
2. Find the operator whose log you want to clear.
3. Click the **Clear log** button (trash icon) in that operator's row.
4. A confirmation modal opens showing the operator's callsign and the number of QSOs
   that will be deleted.
5. Enter your admin password and click **Delete N QSOs** to confirm.

!!! danger "This cannot be undone"
    Clearing an operator's log permanently deletes all their QSOs. There is no undo and
    no recovery from the UI. If you need to recover deleted QSOs, restore from a backup.
```

---

### `mkdocs.yml` (config, add block)

**Analog:** `mkdocs.yml` existing `plugins:` block (lines 16-19) — same top-level YAML key pattern.

**Existing plugins block** (`mkdocs.yml` lines 16-19):
```yaml
plugins:
  - search
  - swagger-ui-tag:
      docExpansion: none
      syntaxHighlightTheme: monokai
```

**Block to add** — place after the `plugins:` block (after line 19), before `nav:`:
```yaml
markdown_extensions:
  - admonition
```

**Constraint:** Do NOT touch the `not_in_nav:` block (lines 5-6). It excludes legacy stub files from the `--strict` build. Removing or modifying it will cause `uv run mkdocs build --strict` to fail.

**Full target placement in file:**
```yaml
plugins:
  - search
  - swagger-ui-tag:
      docExpansion: none
      syntaxHighlightTheme: monokai

markdown_extensions:
  - admonition

nav:
  ...
```

---

## Shared Patterns

### Prose section structure (no curl blocks)
**Source:** `docs/operator-guide/profile.md` section "## Clearing a Field" (line 73) and the Enable/Disable section in `docs/admin-guide/account-management.md` (lines 54-67)
**Apply to:** Both new sections (Danger Zone and Clear Operator Log)
**Pattern:** Short one-sentence description of what the feature does, followed by the numbered steps, followed by any warning. No code blocks because these are UI-only flows.

### Bold UI element names
**Source:** `docs/getting-started/first-qso.md` lines 33-40 and `docs/admin-guide/account-management.md` line 57
**Apply to:** Both new sections
**Pattern:** UI button labels, section names, and nav items are wrapped in `**bold**`:
```markdown
Click **Log QSO** in the navigation bar.
Navigate to **Profile** in the navigation bar.
Click the **Clear log** button.
```

### Danger admonition (new pattern, first use in project)
**Source:** RESEARCH.md Pattern 1; verified with local build test
**Apply to:** Both new sections
**Required mkdocs.yml prerequisite:** `markdown_extensions: [admonition]` must be present before the build, or `!!!` renders as plain text with no build warning.
```markdown
!!! danger "This cannot be undone"
    Body text indented by 4 spaces.
    Second sentence on a new line (same indent level).
```

## No Analog Found

None. All three files have close analogs in the codebase.

## Build Verification

After all edits, run:
```bash
uv run mkdocs build --strict
```
Then verify admonitions rendered as HTML (not plain text):
```bash
grep -r 'class="admonition danger"' /Users/royco/ollog/site/operator-guide/profile/
grep -r 'class="admonition danger"' /Users/royco/ollog/site/admin-guide/account-management/
```
Both greps must return a match. If either returns nothing, `markdown_extensions: admonition` was not saved correctly in `mkdocs.yml`.

## Metadata

**Analog search scope:** `docs/`, `mkdocs.yml`, `templates/log/`, `templates/admin/`
**Files scanned:** `docs/operator-guide/profile.md`, `docs/admin-guide/account-management.md`, `docs/getting-started/first-qso.md`, `mkdocs.yml`, `templates/log/clear_log_modal.html`, `templates/admin/clear_log_modal.html`, `templates/admin/users_table.html`, `templates/log/profile.html`
**Pattern extraction date:** 2026-05-10
