---
phase: 50-sort-ui
verified: 2026-04-23T00:00:00Z
status: human_needed
score: 4/5
overrides_applied: 0
human_verification:
  - test: "Render log table in browser at http://localhost:8000/log/view (default sort -qso_date_utc): confirm DATE text shows solid down-chevron, clock icon shows hollow double-chevron, CALL/BAND/MODE headers each show hollow double-chevron, Freq/RST/Actions have no sort icon"
    expected: "All sortable columns show appropriate active/inactive chevron state; non-sortable columns are bare text"
    why_human: "SVG rendering and CSS opacity in light and dark mode cannot be verified without a browser"
  - test: "Click MODE header — URL changes to ?sort=MODE, MODE shows solid up-chevron, other sortable columns show hollow indicators"
    expected: "MODE ascending-first sort works; visual active state flips to MODE column"
    why_human: "Interaction state and visual rendering require browser"
  - test: "Click MODE again — URL changes to ?sort=-MODE, MODE shows solid down-chevron"
    expected: "Second click toggles to descending"
    why_human: "Toggle behavior must be observed in browser"
  - test: "Click clock icon in DATE header — URL changes to ?sort=-_created_at, clock icon shows solid down-chevron, DATE text shows hollow indicator"
    expected: "Clock sorts newest-entered first; clock icon becomes active indicator"
    why_human: "Visual rendering and URL navigation require browser"
  - test: "Apply a band filter, then click any sort header — verify all filter params remain in the resulting URL"
    expected: "call, band, mode, date_from, date_to params preserved after sort click"
    why_human: "Filter preservation through HTMX navigation requires browser observation"
  - test: "Toggle dark mode and inspect hollow chevron visibility — should be faint but visible (opacity-30 light / opacity-25 dark)"
    expected: "Inactive indicators are visually distinct and appropriately subdued in both modes"
    why_human: "CSS opacity rendering in dark mode requires browser"
---

# Phase 50: Sort UI — Verification Report

**Phase Goal:** Every visible log table column header is clickable to sort, a clock icon in the DATE header provides access to entry-timestamp sort, and all sortable columns display appropriate chevron icons indicating their sort state.
**Verified:** 2026-04-23
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Clicking MODE column header sorts by MODE ascending; clicking again sorts descending | VERIFIED | `{% if sort == 'MODE' %}-MODE{% else %}MODE{% endif %}` at line 94; ascending-first confirmed. Service `_ALLOWED_SORT_FIELDS` includes `MODE` and `-MODE`. |
| 2 | A clock icon is visible inside DATE header; clicking it sorts by `_created_at` descending; clicking again sorts ascending; no new `<td>` appears in QSO rows | VERIFIED | Clock SVG at line 47-49 (Heroicons clock outline, `viewBox="0 0 24 24"`); toggle `{% if sort == '-_created_at' %}_created_at{% else %}-_created_at{% endif %}` at line 43; tbody contains no new cells. |
| 3 | All inactive sortable columns show a faint hollow double-chevron icon | VERIFIED (code) / human_needed (visual) | Exactly 5 occurrences of `opacity-30 dark:opacity-25` in template — one per sortable element (DATE text, clock icon, CALL, BAND, MODE). CSS compiled: `dark\:opacity-25` confirmed in output.css. Visual rendering needs browser check. |
| 4 | Active sort column shows solid directional chevron (up for asc, down for desc) | VERIFIED (code) / human_needed (visual) | Each sortable `<th>` has three branches: `-FIELD` (desc solid SVG), `FIELD` (asc solid SVG), else (hollow SVG). Code structure is correct; visual rendering needs browser. |
| 5 | Clicking any sort header preserves all active filter parameters in the URL | VERIFIED | All 5 sort `hx-get` URLs carry `&call=...&band=...&mode=...&date_from=...&date_to=...`. Verified via grep lines 29, 43, 62, 78, 94. |

**Score:** 4/5 truths fully programmatically verified; all 5 truths verified at code level. Human needed for visual rendering confirmation.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `templates/log/log_table.html` | MODE sort header, DATE flex restructure with clock icon, inactive indicators on all sortable columns | VERIFIED | All 4 task changes present: DATE flex wrapper (line 27), clock icon (line 47), CALL/BAND `{% else %}` branches (lines 71, 87), MODE sort header (lines 92-107). File is 167 lines, substantive. |
| `static/css/output.css` | Compiled Tailwind CSS with `dark:opacity-25` class | VERIFIED | `grep -q "dark\\\\:opacity-25" static/css/output.css` exits 0. `npm run verify` exits 0. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `templates/log/log_table.html` | `/log/view?sort=...` | `hx-get` on sort `<a>` elements | WIRED | 5 sort links + 2 pagination = 7 `hx-push-url` occurrences. All sort links use `hx-get="/log/view?sort=..."`. |
| `templates/log/log_table.html` | `app/qso/service.py _ALLOWED_SORT_FIELDS` | sort parameter in URL query string | WIRED | `MODE`, `-MODE`, `_created_at`, `-_created_at` all present in `_ALLOWED_SORT_FIELDS` frozenset (service.py lines 19-25). Template passes these exact strings via Jinja2 conditionals. |

### Data-Flow Trace (Level 4)

Template is a Jinja2 rendering artifact — data flow originates in `app/qso/service.py::get_qso_page()`. Phase 49 (service layer) established that flow; this phase adds UI only. No new data sources introduced. Level 4 not applicable to this template-only phase.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| MODE ascending-first toggle present | `grep -c "{% if sort == 'MODE' %}-MODE{% else %}MODE{% endif %}" templates/log/log_table.html` | 1 | PASS |
| Clock icon toggle present | `grep -c "{% if sort == '-_created_at' %}_created_at{% else %}-_created_at{% endif %}" templates/log/log_table.html` | 1 | PASS |
| DATE flex wrapper present | `grep -c 'class="inline-flex items-center gap-2"' templates/log/log_table.html` | 1 | PASS |
| Inactive indicator count | `grep -c "opacity-30 dark:opacity-25" templates/log/log_table.html` | 5 | PASS |
| Clock SVG path | `grep -c "M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" templates/log/log_table.html` | 1 | PASS |
| Line 1 sentinel intact | `head -1 templates/log/log_table.html \| grep -q "sort == '-_created_at'"` | SENTINEL OK | PASS |
| Static columns unchanged | `grep -c "Freq (MHz)\|RST S / R\|Actions" templates/log/log_table.html` | 3 | PASS |
| dark:opacity-25 compiled | `grep -q "dark\\\\:opacity-25" static/css/output.css` | FOUND | PASS |
| npm run verify | `npm run verify` | exits 0 | PASS |
| hx-push-url count (>=7) | `grep -c "hx-push-url" templates/log/log_table.html` | 7 | PASS |
| Clock SVG viewBox 24px | `grep -n 'viewBox="0 0 24 24"' templates/log/log_table.html \| grep "line 47"` | line 47 confirmed | PASS |
| Service allows MODE/_created_at sorts | `grep "_ALLOWED_SORT_FIELDS" app/qso/service.py` | MODE, -MODE, _created_at, -_created_at all present | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|------------|-------------|--------|---------|
| SORT-01 | 50-01-PLAN.md | Operator can sort log table by MODE via column header click | SATISFIED | MODE `<th>` with ascending-first hx-get toggle at lines 92-107; `MODE` in `_ALLOWED_SORT_FIELDS` |
| SORT-02 | 50-01-PLAN.md | Operator can sort by `_created_at` via clock icon in DATE header; no new `<td>` | SATISFIED | Clock SVG at line 47; toggle at line 43; tbody uses `{% include "log/qso_row.html" %}` unchanged |
| UX-01 | 50-01-PLAN.md | Inactive sortable columns show faint hollow double-chevron | SATISFIED (code) | 5 `{% else %}` branches each with `opacity-30 dark:opacity-25` hollow SVG; CSS compiled |
| UX-02 | 50-01-PLAN.md | Active sort column shows solid directional chevron | SATISFIED (code) | All 5 sortable `<th>` blocks have `{% if active_desc %}` solid-down and `{% elif active_asc %}` solid-up SVG branches |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | Template contains no TODOs, placeholders, empty returns, or stub patterns. All conditional branches are substantive. |

### Human Verification Required

#### 1. Default sort state — all column icons render correctly

**Test:** Start the app, navigate to `http://localhost:8000/log/view` (default sort is `-qso_date_utc`).
**Expected:**
- "Date / Time UTC" text shows a solid down-chevron (active descending)
- Clock icon to its right shows a faint hollow double-chevron
- CALL, BAND, MODE headers each show a faint hollow double-chevron
- Freq (MHz), RST S / R, Actions have no sort icon whatsoever
**Why human:** SVG rendering and CSS opacity values cannot be verified without a browser.

#### 2. MODE sort — ascending-first, then descending

**Test:** Click the MODE column header once, then again.
**Expected:**
- First click: URL contains `?sort=MODE`; MODE header shows solid up-chevron; all other sortable columns show hollow indicators
- Second click: URL contains `?sort=-MODE`; MODE header shows solid down-chevron
**Why human:** Interaction state and visual toggle require browser observation.

#### 3. Clock icon sort — descending-first, then ascending

**Test:** Click the clock icon in the DATE column header once, then again.
**Expected:**
- First click: URL contains `?sort=-_created_at`; clock icon shows solid down-chevron; "Date / Time UTC" text shows hollow indicator
- Second click: URL contains `?sort=_created_at`; clock icon shows solid up-chevron
**Why human:** Visual active/inactive state flips require browser.

#### 4. Filter preservation through sort click

**Test:** Apply a band filter (e.g., select "20m"), then click any sort header.
**Expected:** The resulting URL contains both `?sort=...` and `&band=20m` — no filter is dropped.
**Why human:** HTMX URL push-state behavior requires browser observation.

#### 5. Dark mode — hollow chevrons appropriately subdued

**Test:** Toggle dark mode and inspect inactive sort indicators on any sortable column.
**Expected:** Hollow double-chevrons are visible but clearly faint (not invisible, not full-brightness) at `dark:opacity-25`.
**Why human:** CSS opacity rendering in dark mode requires browser.

### Gaps Summary

No code-level gaps found. All 10 PLAN acceptance criteria verified programmatically:
- MODE ascending-first toggle: confirmed
- Clock icon toggle (`-_created_at` default): confirmed
- DATE flex wrapper with two `<a>` elements: confirmed
- Exactly 5 inactive indicator branches: confirmed
- Heroicons clock outline SVG with correct path: confirmed
- Line 1 sentinel not regressed: confirmed
- Static columns unchanged: confirmed
- `dark:opacity-25` compiled in output.css: confirmed
- `npm run verify` passes: confirmed
- All sort links carry full filter params: confirmed

Status is `human_needed` solely because visual rendering of SVG chevrons in light/dark mode cannot be verified without a browser.

---

_Verified: 2026-04-23_
_Verifier: Claude (gsd-verifier)_
