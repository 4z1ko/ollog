# Phase 50: Sort UI - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a clickable sort header to the MODE column (ascending-first), restructure the DATE header to contain two side-by-side sort triggers (date sort + clock icon for `_created_at`), add a Heroicons `chevrons-up-down` hollow indicator on all inactive sortable columns (UX-01), and extend the solid directional chevron to cover all active sort states including MODE and the clock icon (UX-02).

All changes are in `templates/log/log_table.html`. No new routes, no new Jinja2 context keys, no new CSS files.

</domain>

<decisions>
## Implementation Decisions

### DATE Header Layout

- **D-01:** The DATE `<th>` contains two separate `<a>` elements side by side within a flex container: (1) the "Date / Time UTC" text link that sorts by `qso_date_utc`, and (2) a clock icon link that sorts by `_created_at`. These are two independent clickable elements, not one.
- **D-02:** When `_created_at` is the active sort, the DATE text link displays the hollow inactive indicator (↕). When `qso_date_utc` is the active sort, the clock icon link displays the hollow inactive indicator. When neither is active, both show the hollow indicator.
- **D-03:** Clock icon first-click sort goes to `-_created_at` (descending, newest-entered first) per success criteria — clicking again goes to `_created_at` (ascending). Same toggle logic as existing DATE sort.

### Clock Icon Sort States

- **D-04:** Clock icon inactive state: clock SVG + Heroicons `chevrons-up-down` hollow icon (↕) at `opacity-30`. Visually matches all other inactive sortable column indicators.
- **D-05:** Clock icon active state: clock SVG + solid directional filled chevron at full opacity (↓ for desc, ↑ for asc). Identical pattern to existing DATE/CALL/BAND active sort chevrons.

### Inactive Sort Indicator (UX-01)

- **D-06:** All sortable columns that are NOT the active sort show the Heroicons `chevrons-up-down` outline SVG icon, sized `w-3 h-3`, at `opacity-30`. This applies to: DATE text link, CALL, BAND, MODE, and the clock icon. Dark mode: use `dark:opacity-25` if the standard `opacity-30` is insufficiently faint in dark.
- **D-07:** The icon is inline-appended after the column label (or after the clock SVG), following the existing "text + chevron" pattern.

### MODE Sort Header (SORT-01)

- **D-08:** Add a sort `<a>` link to the MODE `<th>`, matching the HTMX attribute pattern used for CALL and BAND.
- **D-09:** MODE sorts **ascending first** (A→Z) on first click per requirements success criteria. Template toggle logic: `sort={% if sort == 'MODE' %}-MODE{% else %}MODE{% endif %}`. This differs intentionally from CALL/BAND which toggle descending-first — do not update CALL or BAND.

### CALL/BAND — No Change

- **D-10:** CALL and BAND sort direction is left unchanged (descending-first). Only MODE uses ascending-first. Out of Phase 50 scope to change existing behavior.

### Claude's Discretion

- Exact clock SVG path to use (Heroicons `clock` outline, any size consistent with other headers — 20px viewBox preferred for consistency with existing chevrons)
- Whether to wrap the two DATE sort links in an explicit `<span class="inline-flex items-center gap-2">` or rely on the `<th>` own flex context
- The exact `dark:opacity-*` value for the inactive indicator (25 or 30) — choose whichever looks appropriately faint in dark mode

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Template to Modify
- `templates/log/log_table.html` — all sort header changes; existing HTMX sort link patterns to replicate for MODE and clock icon

### Requirements
- `.planning/REQUIREMENTS.md` — SORT-01 (MODE sort), SORT-02 (clock icon / _created_at sort), UX-01 (hollow inactive indicator), UX-02 (solid active chevron)

### Design System and Prior Phase Decisions
- `.planning/phases/49-service-layer/49-UI-SPEC.md` — icon library (Heroicons inline SVG), accent color (indigo-700), design tokens; read before choosing SVG paths or color classes
- `.planning/phases/49-service-layer/49-CONTEXT.md` — `created_at` exposed in view dict as `qso.created_at` (raw datetime); Phase 49 established `_ALLOWED_SORT_FIELDS` includes `-_created_at` and `_created_at`

### Build Verification
- `package.json` — `npm run verify` must pass after adding any new `dark:` Tailwind classes; run after making template changes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Existing HTMX sort `<a>` pattern for CALL header in `log_table.html` — copy this exactly for MODE (same attributes: `hx-get`, `hx-target="#log-table"`, `hx-swap="innerHTML"`, `hx-push-url="true"`)
- Active sort filled chevron SVGs already in `log_table.html` for DATE (down: fill-rule evenodd path) and up variants — reuse the identical SVG blocks for MODE active state
- `<input type="hidden" name="sort" value="{{ sort }}">` already in the filter form — the `sort` param already flows through all existing links correctly

### Established Patterns
- All sort links pass the full filter state: `&call={{ filters.call or '' }}&band={{ filters.band or '' }}&mode={{ filters.mode or '' }}&date_from={{ filters.date_from or '' }}&date_to={{ filters.date_to or '' }}` — MODE and clock links must include these too
- Active sort columns use `fill="currentColor"` chevrons — the color is inherited from the parent `<a>` which uses `hover:text-indigo-400 transition-colors`
- `log_table.html` is a partial rendered by HTMX into `#log-table` — it receives `sort`, `filters`, `qsos`, `page`, `total_pages`, `page_size`, `total` from the Jinja2 context

### Integration Points
- Only `templates/log/log_table.html` needs changes for Phase 50 — no Python files, no new routes
- After adding `dark:opacity-*` classes: run `npm run verify` to confirm they appear in `static/css/output.css` (Tailwind purge safety gate from CLAUDE.md)

</code_context>

<specifics>
## Specific Ideas

- The `chevrons-up-down` Heroicons icon (outline, 20x20) is the standard "sortable but not active" indicator used by many data-table libraries — it is the correct choice here both semantically and visually.
- The inline-flex `gap-2` spacing between the DATE text link and the clock icon link keeps them visually distinct while still clearly grouped in the same cell.

</specifics>

<deferred>
## Deferred Ideas

- `_created_at` tooltip on QSO date cell — explicitly deferred in `.planning/REQUIREMENTS.md` under "Future Requirements". Do not implement in Phase 50.
- CALL/BAND ascending-first sort — discussed but out of scope per user decision (D-10). Could be addressed in a future cleanup phase if consistency matters.

</deferred>

---

*Phase: 50-sort-ui*
*Context gathered: 2026-04-23*
